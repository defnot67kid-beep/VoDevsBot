import discord
from discord.ext import commands
import pymongo
import os

# ============================================
# MONGODB SETUP
# ============================================
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI environment variable is not set!")

client = pymongo.MongoClient(MONGO_URI)
db = client["vodevs_bot_data"]
rr_collection = db["reaction_roles"]
rr_menu_ids_collection = db["reaction_menu_ids"]

# ============================================
# REACTION ROLE COG
# ============================================
class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ============================================
    # CREATE MENU
    # ============================================
    @commands.command(name="rr-create")
    @commands.has_permissions(manage_roles=True)
    async def rr_create(self, ctx, title: str, color: discord.Color = discord.Color.blue(), *, description: str = "React below to get roles!"):
        """[Admin] Creates a new Reaction Role Menu."""
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        embed.set_footer(text="React to this message to receive roles!")
        embed.add_field(name="Available Roles", value="No roles added yet. Use `!rr-add` to add them!", inline=False)

        msg = await ctx.send(embed=embed)
        
        # Save to MongoDB
        rr_collection.insert_one({
            "message_id": str(msg.id),
            "channel_id": ctx.channel.id,
            "guild_id": ctx.guild.id,
            "title": title,
            "description": description,
            "color": color.value,
            "roles": {}
        })

        rr_menu_ids_collection.insert_one({
            "guild_id": str(ctx.guild.id),
            "message_id": str(msg.id)
        })

        embed = discord.Embed(
            title="✅ Reaction Role Menu Created!",
            description=f"Menu ID: `{msg.id}`\nChannel: {ctx.channel.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Next Steps", value=f"Use `!rr-add {msg.id} :emoji: @Role <description>` to add roles.", inline=False)
        
        await ctx.send(embed=embed, delete_after=15)

    # ============================================
    # ADD ROLE TO MENU
    # ============================================
    @commands.command(name="rr-add")
    @commands.has_permissions(manage_roles=True)
    async def rr_add(self, ctx, menu_id: str, emoji: str, role: discord.Role, *, description: str = "No description provided."):
        """[Admin] Adds a role + emoji pair to an existing Reaction Role menu."""
        
        data = rr_collection.find_one({"message_id": menu_id})
        if not data:
            embed = discord.Embed(
                title="❌ Invalid Menu ID",
                description=f"Menu ID `{menu_id}` not found.\nUse `!rr-list` to see all menus.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed, delete_after=10)

        try:
            channel = self.bot.get_channel(data["channel_id"])
            msg = await channel.fetch_message(int(menu_id))
        except:
            embed = discord.Embed(
                title="❌ Menu Not Found",
                description="The menu message might have been deleted.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed, delete_after=10)

        try:
            await msg.add_reaction(emoji)
        except:
            embed = discord.Embed(
                title="❌ Invalid Emoji",
                description="Please provide a standard emoji (e.g., ✅, 🔥, or custom server emoji).",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed, delete_after=10)

        # Update MongoDB
        rr_collection.update_one(
            {"message_id": menu_id},
            {"$set": {f"roles.{emoji}": {"role_id": role.id, "description": description}}}
        )

        await self.update_menu_embed(msg, menu_id)
        
        embed = discord.Embed(
            title="✅ Role Added to Menu",
            description=f"{emoji} → {role.mention}\nDescription: {description}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed, delete_after=10)

    # ============================================
    # REMOVE ROLE FROM MENU
    # ============================================
    @commands.command(name="rr-remove")
    @commands.has_permissions(manage_roles=True)
    async def rr_remove(self, ctx, menu_id: str, emoji: str):
        """[Admin] Removes a role+emoji pair from a menu."""
        
        data = rr_collection.find_one({"message_id": menu_id})
        if not data:
            embed = discord.Embed(
                title="❌ Invalid Menu ID",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed, delete_after=10)
        
        if emoji not in data.get("roles", {}):
            embed = discord.Embed(
                title="❌ Emoji Not Found",
                description=f"Emoji `{emoji}` is not in this menu.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed, delete_after=10)
        
        rr_collection.update_one({"message_id": menu_id}, {"$unset": {f"roles.{emoji}": ""}})
        
        # Update embed
        channel = self.bot.get_channel(data["channel_id"])
        msg = await channel.fetch_message(int(menu_id))
        await self.update_menu_embed(msg, menu_id)
        
        embed = discord.Embed(
            title="✅ Role Removed",
            description=f"Removed `{emoji}` from the menu.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed, delete_after=10)

    # ============================================
    # UPDATE ROLE DESCRIPTION
    # ============================================
    @commands.command(name="rr-desc")
    @commands.has_permissions(manage_roles=True)
    async def rr_desc(self, ctx, menu_id: str, emoji: str, *, new_description: str):
        """[Admin] Updates the description for a role+emoji pair."""
        
        data = rr_collection.find_one({"message_id": menu_id})
        if not data:
            embed = discord.Embed(
                title="❌ Invalid Menu ID",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed, delete_after=10)
        
        if emoji not in data.get("roles", {}):
            embed = discord.Embed(
                title="❌ Emoji Not Found",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed, delete_after=10)
        
        rr_collection.update_one(
            {"message_id": menu_id}, 
            {"$set": {f"roles.{emoji}.description": new_description}}
        )
        
        # Update embed
        channel = self.bot.get_channel(data["channel_id"])
        msg = await channel.fetch_message(int(menu_id))
        await self.update_menu_embed(msg, menu_id)
        
        embed = discord.Embed(
            title="✅ Description Updated",
            description=f"Updated description for {emoji} to:\n> {new_description}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, delete_after=10)

    # ============================================
    # UPDATE ROLE
    # ============================================
    @commands.command(name="rr-role")
    @commands.has_permissions(manage_roles=True)
    async def rr_role(self, ctx, menu_id: str, emoji: str, new_role: discord.Role):
        """[Admin] Updates the role for a specific emoji."""
        
        data = rr_collection.find_one({"message_id": menu_id})
        if not data:
            embed = discord.Embed(
                title="❌ Invalid Menu ID",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed, delete_after=10)
        
        if emoji not in data.get("roles", {}):
            embed = discord.Embed(
                title="❌ Emoji Not Found",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed, delete_after=10)
        
        rr_collection.update_one(
            {"message_id": menu_id}, 
            {"$set": {f"roles.{emoji}.role_id": new_role.id}}
        )
        
        # Update embed
        channel = self.bot.get_channel(data["channel_id"])
        msg = await channel.fetch_message(int(menu_id))
        await self.update_menu_embed(msg, menu_id)
        
        embed = discord.Embed(
            title="✅ Role Updated",
            description=f"Updated role for {emoji} to {new_role.mention}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, delete_after=10)

    # ============================================
    # LIST ALL MENUS
    # ============================================
    @commands.command(name="rr-list")
    @commands.has_permissions(manage_roles=True)
    async def rr_list(self, ctx):
        """[Admin] Lists all reaction role menus in this server."""
        
        menus = list(rr_collection.find({"guild_id": ctx.guild.id}))
        
        if not menus:
            embed = discord.Embed(
                title="📋 Reaction Role Menus",
                description="No menus found in this server.",
                color=discord.Color.orange()
            )
            return await ctx.send(embed=embed, delete_after=10)
        
        embed = discord.Embed(
            title="📋 Reaction Role Menus",
            description=f"Found **{len(menus)}** menu(s) in this server.",
            color=discord.Color.blue()
        )
        
        for menu in menus[:10]:  # Limit to 10
            role_count = len(menu.get("roles", {}))
            embed.add_field(
                name=f"ID: `{menu['message_id']}`",
                value=f"Roles: {role_count}\nChannel: <#{menu['channel_id']}>\nTitle: {menu['title']}",
                inline=False
            )
        
        if len(menus) > 10:
            embed.set_footer(text=f"And {len(menus) - 10} more menus...")
        
        await ctx.send(embed=embed, delete_after=30)

    # ============================================
    # DELETE MENU
    # ============================================
    @commands.command(name="rr-delete")
    @commands.has_permissions(manage_roles=True)
    async def rr_delete(self, ctx, menu_id: str):
        """[Admin] Deletes a reaction role menu permanently."""
        
        data = rr_collection.find_one({"message_id": menu_id})
        if not data:
            embed = discord.Embed(
                title="❌ Invalid Menu ID",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed, delete_after=10)
        
        # Delete the message
        try:
            channel = self.bot.get_channel(data["channel_id"])
            msg = await channel.fetch_message(int(menu_id))
            await msg.delete()
        except:
            pass
        
        # Delete from database
        rr_collection.delete_one({"message_id": menu_id})
        rr_menu_ids_collection.delete_one({"message_id": menu_id})
        
        embed = discord.Embed(
            title="🗑️ Menu Deleted",
            description=f"Menu ID `{menu_id}` has been permanently deleted.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=10)

    # ============================================
    # MENU INFO
    # ============================================
    @commands.command(name="rr-info")
    @commands.has_permissions(manage_roles=True)
    async def rr_info(self, ctx, menu_id: str):
        """[Admin] Shows detailed information about a menu."""
        
        data = rr_collection.find_one({"message_id": menu_id})
        if not data:
            embed = discord.Embed(
                title="❌ Invalid Menu ID",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed, delete_after=10)
        
        embed = discord.Embed(
            title=f"📋 Menu Info: {data['title']}",
            color=discord.Color(data.get("color", 0x5865F2))
        )
        embed.add_field(name="Menu ID", value=f"`{menu_id}`", inline=True)
        embed.add_field(name="Channel", value=f"<#{data['channel_id']}>", inline=True)
        embed.add_field(name="Description", value=data['description'][:100], inline=False)
        
        roles = data.get("roles", {})
        if roles:
            role_text = ""
            for emoji, role_info in list(roles.items())[:10]:
                role = ctx.guild.get_role(role_info["role_id"])
                role_name = role.mention if role else "**Deleted Role**"
                role_text += f"{emoji} {role_name} — {role_info['description'][:50]}\n"
            
            if len(roles) > 10:
                role_text += f"\n... and {len(roles) - 10} more"
            
            embed.add_field(name=f"Roles ({len(roles)})", value=role_text or "No roles", inline=False)
        else:
            embed.add_field(name="Roles", value="No roles added yet.", inline=False)
        
        await ctx.send(embed=embed, delete_after=30)

    # ============================================
    # MENU UPDATE HELPER
    # ============================================
    async def update_menu_embed(self, msg: discord.Message, menu_id: str):
        data = rr_collection.find_one({"message_id": menu_id})
        if not data: return
        
        embed = discord.Embed(
            title=data["title"], 
            description=data["description"], 
            color=discord.Color(data.get("color", 0x5865F2))
        )
        
        role_text = ""
        roles = data.get("roles", {})
        for emoji, role_info in roles.items():
            role = msg.guild.get_role(role_info["role_id"])
            role_name = role.mention if role else "**Deleted Role**"
            role_text += f"{emoji} {role_name} — *{role_info['description']}*\n"
        
        embed.add_field(
            name="Available Roles", 
            value=role_text if role_text else "No roles added yet.", 
            inline=False
        )
        embed.set_footer(text="React to this message to receive roles!")
        await msg.edit(embed=embed)

    # ============================================
    # EVENT: ON RAW REACTION ADD/REMOVE
    # ============================================
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id: return
        
        data = rr_collection.find_one({"message_id": str(payload.message_id)})
        if not data: return
        
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if not member: return
        
        emoji_str = str(payload.emoji)
        if emoji_str in data.get("roles", {}):
            role = guild.get_role(data["roles"][emoji_str]["role_id"])
            if role and role not in member.roles:
                try: 
                    await member.add_roles(role, reason=f"Reaction Role: {emoji_str}")
                except: 
                    pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id: return
        
        data = rr_collection.find_one({"message_id": str(payload.message_id)})
        if not data: return
        
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if not member: return
        
        emoji_str = str(payload.emoji)
        if emoji_str in data.get("roles", {}):
            role = guild.get_role(data["roles"][emoji_str]["role_id"])
            if role and role in member.roles:
                try: 
                    await member.remove_roles(role, reason=f"Reaction Role Removed: {emoji_str}")
                except: 
                    pass

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
