import discord
from discord.ext import commands, tasks  # <--- FIX: Added 'tasks' here!
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
admin_actions_collection = db["admin_actions"]  # Added to check queue
pending_reaction_menus = db["pending_reaction_menus"] # Added for Dashboard feedback

# ============================================
# REACTION ROLE COG
# ============================================
class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_admin_actions.start()

    # ============================================
    # BACKGROUND TASK: Check for Dashboard Actions
    # ============================================
    @tasks.loop(seconds=5)
    async def check_admin_actions(self):
        action = admin_actions_collection.find_one_and_update(
            {"type": "reaction_role", "status": "pending"},
            {"$set": {"status": "processing"}}
        )
        if not action:
            return

        print(f"⚠️ [ReactionRoles] Dashboard requested a new menu!")

        try:
            guild_id = int(action.get('guild_id'))
            guild = self.bot.get_guild(guild_id)
            if not guild:
                admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "failed", "error": "Guild not found"}})
                return

            channel_id = int(action.get('channel_id'))
            channel = guild.get_channel(channel_id)
            if not channel:
                admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "failed", "error": "Channel not found"}})
                return

            title = action.get('title', 'Get Roles!')
            description = action.get('description', 'React below to get roles.')
            color = discord.Color.from_str(action.get('color', '#5865F2'))
            roles = action.get('roles', []) # Dashboard sends empty list for empty menu

            embed = discord.Embed(title=title, description=description, color=color)
            embed.set_footer(text="React to this message to receive roles!")

            role_text = ""
            for item in roles:
                role = guild.get_role(item['role_id'])
                role_mention = role.mention if role else "**Deleted Role**"
                role_text += f"{item['emoji']} {role_mention} — *{item['description']}*\n"

            if role_text:
                embed.add_field(name="Available Roles", value=role_text, inline=False)
            else:
                embed.add_field(name="Available Roles", value="No roles added yet. Use `!rr-add` or Dashboard Step 2 to add them!", inline=False)

            msg = await channel.send(embed=embed)

            # Save to MongoDB
            rr_collection.insert_one({
                "message_id": str(msg.id),
                "channel_id": channel.id,
                "guild_id": guild.id,
                "title": title,
                "description": description,
                "color": color.value,
                "roles": {} 
            })

            # Notify Dashboard via the pending collection
            pending_reaction_menus.insert_one({
                "guild_id": str(guild.id),
                "message_id": str(msg.id)
            })

            print(f"✅ [ReactionRoles] Menu created from Dashboard request! ID: {msg.id}")
            
            admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "completed"}})

        except Exception as e:
            print(f"❌ [ReactionRoles] Failed to process Dashboard request: {e}")
            admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "failed", "error": str(e)}})

    # ============================================
    # ADMIN SETUP COMMAND (Creates the Menu)
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

        await ctx.send(f"✅ Reaction Role Menu created! ID: `{msg.id}`\nUse `{ctx.prefix}rr-add {msg.id} :emoji: @Role <description>` to add roles.", delete_after=15)

    # ============================================
    # ADMIN ADD COMMAND (Adds Role+Emoji to Menu)
    # ============================================
    @commands.command(name="rr-add")
    @commands.has_permissions(manage_roles=True)
    async def rr_add(self, ctx, menu_id: str, emoji: str, role: discord.Role, *, description: str = "No description provided."):
        """[Admin] Adds a role + emoji pair to an existing Reaction Role menu."""
        
        data = rr_collection.find_one({"message_id": menu_id})
        if not data:
            return await ctx.send("❌ Invalid Menu ID. Please use the ID provided when you ran `!rr-setup`.")

        try:
            channel = self.bot.get_channel(data["channel_id"])
            msg = await channel.fetch_message(int(menu_id))
        except:
            return await ctx.send("❌ Could not find the menu message. It might have been deleted.")

        try:
            await msg.add_reaction(emoji)
        except:
            return await ctx.send("❌ Invalid Emoji! Please provide a standard emoji (e.g., ✅, 🔥, or custom server emoji).")

        # Update MongoDB
        rr_collection.update_one(
            {"message_id": menu_id},
            {"$set": {f"roles.{emoji}": {"role_id": role.id, "description": description}}}
        )

        await self.update_menu_embed(msg, menu_id)
        await ctx.send(f"✅ Added {emoji} -> {role.mention} to the menu!", delete_after=10)

    # ============================================
    # OTHER ADMIN COMMANDS (Updated for MongoDB)
    # ============================================
    @commands.command(name="rr-remove")
    @commands.has_permissions(manage_roles=True)
    async def rr_remove(self, ctx, menu_id: str, emoji: str):
        if not rr_collection.find_one({"message_id": menu_id}):
            return await ctx.send("❌ Invalid Menu ID.")
        
        rr_collection.update_one({"message_id": menu_id}, {"$unset": {f"roles.{emoji}": ""}})
        await ctx.send(f"✅ Removed {emoji} from the menu.", delete_after=10)

    @commands.command(name="rr-desc")
    @commands.has_permissions(manage_roles=True)
    async def rr_desc(self, ctx, menu_id: str, emoji: str, *, new_description: str):
        if not rr_collection.find_one({"message_id": menu_id}):
            return await ctx.send("❌ Invalid Menu ID.")
        
        rr_collection.update_one({"message_id": menu_id}, {"$set": {f"roles.{emoji}.description": new_description}})
        await ctx.send(f"✅ Updated description for {emoji} to: `{new_description}`", delete_after=10)

    @commands.command(name="rr-role")
    @commands.has_permissions(manage_roles=True)
    async def rr_role(self, ctx, menu_id: str, emoji: str, new_role: discord.Role):
        if not rr_collection.find_one({"message_id": menu_id}):
            return await ctx.send("❌ Invalid Menu ID.")
        
        rr_collection.update_one({"message_id": menu_id}, {"$set": {f"roles.{emoji}.role_id": new_role.id}})
        await ctx.send(f"✅ Updated role for {emoji} to {new_role.mention}", delete_after=10)

    # ============================================
    # MENU UPDATE HELPER
    # ============================================
    async def update_menu_embed(self, msg: discord.Message, menu_id: str):
        data = rr_collection.find_one({"message_id": menu_id})
        if not data: return
        
        embed = discord.Embed(title=data["title"], description=data["description"], color=discord.Color(data["color"]))
        role_text = ""
        for emoji, role_info in data["roles"].items():
            role = msg.guild.get_role(role_info["role_id"])
            role_name = role.mention if role else "**Deleted Role**"
            role_text += f"{emoji} {role_name} — *{role_info['description']}*\n"
        
        embed.add_field(name="Available Roles", value=role_text if role_text else "No roles added yet.", inline=False)
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
        if emoji_str in data["roles"]:
            role = guild.get_role(data["roles"][emoji_str]["role_id"])
            if role and role not in member.roles:
                try: await member.add_roles(role, reason=f"Reaction Role: {emoji_str}")
                except: pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id: return
        data = rr_collection.find_one({"message_id": str(payload.message_id)})
        if not data: return
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if not member: return
        emoji_str = str(payload.emoji)
        if emoji_str in data["roles"]:
            role = guild.get_role(data["roles"][emoji_str]["role_id"])
            if role and role in member.roles:
                try: await member.remove_roles(role, reason=f"Reaction Role Removed: {emoji_str}")
                except: pass

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
