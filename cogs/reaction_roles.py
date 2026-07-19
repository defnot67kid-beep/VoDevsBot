import discord
from discord.ext import commands
import json
import os

# ============================================
# DATABASE SETUP (JSON File)
# ============================================
DB_FILE = "reaction_roles_data.json"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ============================================
# REACTION ROLE COG (ADVANCED UI)
# ============================================
class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()

    # ============================================
    # ADMIN SETUP COMMAND
    # ============================================
    @commands.command(name="rr-setup")
    @commands.has_permissions(manage_roles=True)
    async def rr_setup(self, ctx, title: str, color: discord.Color = discord.Color.blue(), *, description: str = "React below to get roles!"):
        """[Admin] Creates a new Reaction Role Menu."""
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        embed.set_footer(text="React to this message to receive roles!")

        msg = await ctx.send(embed=embed)
        
        menu_id = str(msg.id)
        self.data[menu_id] = {
            "channel_id": ctx.channel.id,
            "title": title,
            "description": description,
            "color": color.value,
            "roles": {} 
        }
        save_data(self.data)

        await ctx.send(f"✅ Reaction Role Menu created! ID: `{menu_id}`", delete_after=10)

    # ============================================
    # ADMIN ADD COMMAND
    # ============================================
    @commands.command(name="rr-add")
    @commands.has_permissions(manage_roles=True)
    async def rr_add(self, ctx, menu_id: str, emoji: str, role: discord.Role, *, description: str = None):
        """[Admin] Adds a role + emoji pair to an existing Reaction Role menu."""
        
        if menu_id not in self.data:
            return await ctx.send("❌ Invalid Menu ID.")

        try:
            channel = self.bot.get_channel(self.data[menu_id]["channel_id"])
            msg = await channel.fetch_message(int(menu_id))
        except:
            return await ctx.send("❌ Could not find the menu message.")

        try:
            await msg.add_reaction(emoji)
        except:
            return await ctx.send("❌ Invalid Emoji! Please provide a standard emoji (e.g., ✅, 🔥, or custom server emoji).")

        # Auto-generate a description if user didn't provide one
        if description is None:
            description = f"Grants the {role.name} role."

        self.data[menu_id]["roles"][emoji] = {
            "role_id": role.id,
            "description": description
        }
        save_data(self.data)

        await self.update_menu_embed(msg, menu_id)
        await ctx.send(f"✅ Added {emoji} -> {role.mention} to the menu!", delete_after=10)

    # ============================================
    # REMOVE / DESC / ROLE COMMANDS
    # ============================================
    @commands.command(name="rr-remove")
    @commands.has_permissions(manage_roles=True)
    async def rr_remove(self, ctx, menu_id: str, emoji: str):
        if menu_id not in self.data: return await ctx.send("❌ Invalid Menu ID.")
        if emoji not in self.data[menu_id]["roles"]: return await ctx.send("❌ That emoji is not on this menu.")
        try:
            channel = self.bot.get_channel(self.data[menu_id]["channel_id"])
            msg = await channel.fetch_message(int(menu_id))
            await msg.clear_reaction(emoji)
        except: pass
        del self.data[menu_id]["roles"][emoji]
        save_data(self.data)
        try: await self.update_menu_embed(msg, menu_id)
        except: pass
        await ctx.send(f"✅ Removed {emoji} from the menu.", delete_after=10)

    @commands.command(name="rr-desc")
    @commands.has_permissions(manage_roles=True)
    async def rr_desc(self, ctx, menu_id: str, emoji: str, *, new_description: str):
        if menu_id not in self.data: return await ctx.send("❌ Invalid Menu ID.")
        if emoji not in self.data[menu_id]["roles"]: return await ctx.send("❌ That emoji is not on this menu.")
        self.data[menu_id]["roles"][emoji]["description"] = new_description
        save_data(self.data)
        try:
            channel = self.bot.get_channel(self.data[menu_id]["channel_id"])
            msg = await channel.fetch_message(int(menu_id))
            await self.update_menu_embed(msg, menu_id)
        except: pass
        await ctx.send(f"✅ Updated description for {emoji}.", delete_after=10)

    @commands.command(name="rr-role")
    @commands.has_permissions(manage_roles=True)
    async def rr_role(self, ctx, menu_id: str, emoji: str, new_role: discord.Role):
        if menu_id not in self.data: return await ctx.send("❌ Invalid Menu ID.")
        if emoji not in self.data[menu_id]["roles"]: return await ctx.send("❌ That emoji is not on this menu.")
        self.data[menu_id]["roles"][emoji]["role_id"] = new_role.id
        save_data(self.data)
        try:
            channel = self.bot.get_channel(self.data[menu_id]["channel_id"])
            msg = await channel.fetch_message(int(menu_id))
            await self.update_menu_embed(msg, menu_id)
        except: pass
        await ctx.send(f"✅ Updated role for {emoji} to {new_role.mention}", delete_after=10)

    # ============================================
    # ADVANCED UI HELPER (The Cleaner Layout)
    # ============================================
    async def update_menu_embed(self, msg: discord.Message, menu_id: str):
        data = self.data[menu_id]
        
        embed = discord.Embed(
            title=data["title"],
            description=data["description"],
            color=discord.Color(data["color"])
        )
        
        # Sort roles alphabetically by role name
        sorted_items = sorted(data["roles"].items(), key=lambda x: msg.guild.get_role(x[1]["role_id"]).name if msg.guild.get_role(x[1]["role_id"]) else "ZZZ")

        # If there are 3 or fewer roles, make them their own dedicated fields (Looks larger and cleaner)
        if len(sorted_items) <= 3:
            for emoji, role_info in sorted_items:
                role = msg.guild.get_role(role_info["role_id"])
                role_name = role.mention if role else "**Deleted Role**"
                embed.add_field(
                    name=f"{emoji} {role_name}",
                    value=f"*{role_info['description']}*",
                    inline=False
                )
        else:
            # If there are more than 3 roles, split them into two clean columns
            field_value = ""
            for emoji, role_info in sorted_items:
                role = msg.guild.get_role(role_info["role_id"])
                role_name = role.mention if role else "**Deleted Role**"
                field_value += f"{emoji} {role_name} — *{role_info['description']}*\n"
            
            embed.add_field(name="Available Roles", value=field_value, inline=False)

        embed.set_footer(text="React to this message to receive roles!")
        await msg.edit(embed=embed)

    # ============================================
    # REACTION EVENT LISTENERS
    # ============================================
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id: return
        menu_id = str(payload.message_id)
        if menu_id not in self.data: return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        member = guild.get_member(payload.user_id)
        if not member: return
        emoji_str = str(payload.emoji)
        if emoji_str in self.data[menu_id]["roles"]:
            role_id = self.data[menu_id]["roles"][emoji_str]["role_id"]
            role = guild.get_role(role_id)
            if role and role not in member.roles:
                try: await member.add_roles(role, reason=f"Reaction Role: {emoji_str}")
                except: pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id: return
        menu_id = str(payload.message_id)
        if menu_id not in self.data: return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        member = guild.get_member(payload.user_id)
        if not member: return
        emoji_str = str(payload.emoji)
        if emoji_str in self.data[menu_id]["roles"]:
            role_id = self.data[menu_id]["roles"][emoji_str]["role_id"]
            role = guild.get_role(role_id)
            if role and role in member.roles:
                try: await member.remove_roles(role, reason=f"Reaction Role Removed: {emoji_str}")
                except: pass

# ============================================
# SETUP FUNCTION
# ============================================
async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
