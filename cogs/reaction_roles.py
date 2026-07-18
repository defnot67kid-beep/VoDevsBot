import discord
from discord.ext import commands
from discord.ui import View, Button
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
# REACTION ROLE COG
# ============================================
class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()

    # ============================================
    # ADMIN SETUP COMMAND (Creates the Menu)
    # ============================================
    @commands.command(name="rr-setup")
    @commands.has_permissions(manage_roles=True)
    async def rr_setup(self, ctx, title: str, color: discord.Color = discord.Color.blue(), *, description: str = "React below to get roles!"):
        """[Admin] Creates a new Reaction Role Menu."""
        
        # Create a simple embed for the menu
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        embed.set_footer(text="React to this message to receive roles!")

        # Send the message
        msg = await ctx.send(embed=embed)
        
        # Save to database
        menu_id = str(msg.id)
        self.data[menu_id] = {
            "channel_id": ctx.channel.id,
            "title": title,
            "description": description,
            "color": color.value,
            "roles": {} # Format: {"emoji": {"role_id": 123, "description": "..."}}
        }
        save_data(self.data)

        await ctx.send(f"✅ Reaction Role Menu created! ID: `{menu_id}`\nUse `{ctx.prefix}rr-add {menu_id} :emoji: @Role <description>` to add roles.", delete_after=15)

    # ============================================
    # ADMIN ADD COMMAND (Adds Role+Emoji to Menu)
    # ============================================
    @commands.command(name="rr-add")
    @commands.has_permissions(manage_roles=True)
    async def rr_add(self, ctx, menu_id: str, emoji: str, role: discord.Role, *, description: str = "No description provided."):
        """[Admin] Adds a role + emoji pair to an existing Reaction Role menu."""
        
        if menu_id not in self.data:
            return await ctx.send("❌ Invalid Menu ID. Please use the ID provided when you ran `!rr-setup`.")

        # Try to get the message
        try:
            channel = self.bot.get_channel(self.data[menu_id]["channel_id"])
            msg = await channel.fetch_message(int(menu_id))
        except:
            return await ctx.send("❌ Could not find the menu message. It might have been deleted.")

        # Add the reaction to the message
        try:
            await msg.add_reaction(emoji)
        except:
            return await ctx.send("❌ Invalid Emoji! Please provide a standard emoji (e.g., ✅, 🔥, or custom server emoji).")

        # Save to database
        self.data[menu_id]["roles"][emoji] = {
            "role_id": role.id,
            "description": description
        }
        save_data(self.data)

        # Update the embed to show the new role
        await self.update_menu_embed(msg, menu_id)

        await ctx.send(f"✅ Added {emoji} -> {role.mention} to the menu!", delete_after=10)

    # ============================================
    # MENU UPDATE HELPER (Refreshes the Embed)
    # ============================================
    async def update_menu_embed(self, msg: discord.Message, menu_id: str):
        data = self.data[menu_id]
        
        embed = discord.Embed(
            title=data["title"],
            description=data["description"],
            color=discord.Color(data["color"])
        )
        
        role_text = ""
        for emoji, role_info in data["roles"].items():
            role = msg.guild.get_role(role_info["role_id"])
            role_name = role.mention if role else "Deleted Role"
            role_text += f"{emoji} {role_name} — *{role_info['description']}*\n"
        
        if role_text:
            embed.add_field(name="Available Roles", value=role_text, inline=False)
        else:
            embed.add_field(name="Available Roles", value="No roles added yet. Use `!rr-add` to add them!", inline=False)
            
        embed.set_footer(text="React to this message to receive roles!")
        await msg.edit(embed=embed)

    # ============================================
    # EVENT: ON RAW REACTION ADD
    # ============================================
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        menu_id = str(payload.message_id)
        if menu_id not in self.data:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        emoji_str = str(payload.emoji)
        if emoji_str in self.data[menu_id]["roles"]:
            role_id = self.data[menu_id]["roles"][emoji_str]["role_id"]
            role = guild.get_role(role_id)
            
            if role and role not in member.roles:
                try:
                    await member.add_roles(role, reason=f"Reaction Role: {emoji_str}")
                except discord.Forbidden:
                    pass # Bot doesn't have permissions

    # ============================================
    # EVENT: ON RAW REACTION REMOVE
    # ============================================
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        menu_id = str(payload.message_id)
        if menu_id not in self.data:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        emoji_str = str(payload.emoji)
        if emoji_str in self.data[menu_id]["roles"]:
            role_id = self.data[menu_id]["roles"][emoji_str]["role_id"]
            role = guild.get_role(role_id)
            
            if role and role in member.roles:
                try:
                    await member.remove_roles(role, reason=f"Reaction Role Removed: {emoji_str}")
                except discord.Forbidden:
                    pass # Bot doesn't have permissions

# ============================================
# SETUP FUNCTION
# ============================================
async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
