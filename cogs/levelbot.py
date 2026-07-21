import discord
from discord.ext import commands
import pymongo
import os
import json
import asyncio
import math
import random
import aiohttp
import io

# ==========================================
# MONGODB SETUP (Uses Environment Variable)
# ==========================================
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI environment variable is not set! Please add it in Railway.")

client = pymongo.MongoClient(MONGO_URI)
db = client["vodevs_bot_data"]
levels_collection = db["levels"]
roles_collection = db["roles"]
config_collection = db["config"]

# ==========================================
# SMART BUTTON VIEW (Never disabled, works for everyone)
# ==========================================
class CardButton(discord.ui.View):
    def __init__(self, dashboard_url):
        super().__init__(timeout=None)
        self.dashboard_url = dashboard_url

    @discord.ui.button(label="/card", style=discord.ButtonStyle.primary, emoji="🎨")
    async def card_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Get the ID of whoever clicked the button right now
        clicker_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        
        # Construct the link for THIS SPECIFIC USER, not the original card owner
        specific_url = f"{self.dashboard_url}/dashboard/{guild_id}/{clicker_id}"
        
        # Send the link ephemerally (Only they can see it)
        await interaction.response.send_message(
            f"🔗 Click this link to edit **your** rank card:\n{specific_url}",
            ephemeral=True
        )

class LevelBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Cooldown dictionary (user_id -> last_message_time)
        self.xp_cooldowns = {}
        
        # Default slowmode (45 seconds). Can be changed by admins.
        self.COOLDOWN_SECONDS = 45
        
        # Bypass list (User IDs and Role IDs)
        self.bypass_users = set()
        self.bypass_roles = set()
        
        # Load bypass config & channel config
        self.load_config()
        
        # Define the level progression (STOPS AT 100)
        self.levels = [2, 5, 10, 20, 35, 50, 60, 70, 100]

    def load_config(self):
        """Load cooldown, bypass, and channel config from MongoDB"""
        doc = config_collection.find_one({"_id": "bot_config"})
        if doc:
            self.COOLDOWN_SECONDS = doc.get("cooldown_seconds", 45)
            self.bypass_users = set(doc.get("bypass_users", []))
            self.bypass_roles = set(doc.get("bypass_roles", []))
            self.level_channel_id = doc.get("level_channel_id", 1526989768595083384)
            
    def save_config(self):
        """Save cooldown, bypass, and channel config to MongoDB"""
        config_collection.update_one(
            {"_id": "bot_config"},
            {"$set": {
                "cooldown_seconds": self.COOLDOWN_SECONDS,
                "bypass_users": list(self.bypass_users),
                "bypass_roles": list(self.bypass_roles),
                "level_channel_id": self.level_channel_id
            }},
            upsert=True
        )

    def get_role_color(self, level):
        """Returns a color based on the level"""
        colors = {
            2: discord.Color.from_rgb(46, 204, 113),   # Green
            5: discord.Color.from_rgb(52, 152, 219),   # Blue
            10: discord.Color.from_rgb(155, 89, 182),  # Purple
            20: discord.Color.from_rgb(230, 126, 34),  # Orange
            35: discord.Color.from_rgb(231, 76, 60),   # Red
            50: discord.Color.from_rgb(241, 196, 15),  # Yellow/Gold
            60: discord.Color.from_rgb(26, 188, 156),  # Teal
            70: discord.Color.from_rgb(142, 68, 173),  # Deep Purple
            100: discord.Color.from_rgb(192, 57, 43),  # Dark Red
        }
        return colors.get(level, discord.Color.default())

    def get_role_permissions(self, level):
        """
        Returns permission overwrites based on the level.
        - Level 2 & 5: Base only (Read/Send)
        - Level 10: Can send GIFs, images, files (attach_files) BUT no embed
        - Level 20: Can embed links, which allows GIF embeds + bot commands
        """
        perms = discord.Permissions()
        
        # BASE PERMS FOR ALL (Level 2+)
        perms.read_messages = True
        perms.send_messages = True
        perms.read_message_history = True
        
        # Level 10: Can send images, GIFs, files (as attachments)
        if level >= 10:
            perms.attach_files = True
        
        # Level 20: Can EMBED links (GIFs play inline) + use bot commands
        if level >= 20:
            perms.embed_links = True
        
        return perms

    # ==========================================
    # XP CALCULATION (Text + File Size + ROUNDING)
    # ==========================================
    
    def calculate_xp_gain(self, message):
        """Calculate XP based on text length and attached file sizes. Rounded to nearest integer."""
        
        # 1. XP FROM TEXT (1-5 XP per character, randomized)
        content = message.content
        length = len(content)
        
        # Base XP for just sending a message (small)
        base_xp = 5
        
        # 1-5 XP for EVERY single character in the message!
        total_char_xp = 0
        for _ in range(length):
            total_char_xp += random.randint(1, 5)
            
        total_xp = base_xp + total_char_xp
        
        # 2. XP FROM ATTACHMENTS (0.001 XP per Kilobyte)
        if message.attachments:
            for attachment in message.attachments:
                # Get size in bytes
                size_bytes = attachment.size
                # Convert to Kilobytes (KB)
                size_kb = size_bytes / 1024
                # Award 0.001 XP per KB
                file_xp = size_kb * 0.001
                total_xp += file_xp
        
        # Safety cap: Max 1,000 XP per message (stops massive paste/image exploits)
        if total_xp > 1000:
            total_xp = 1000
            
        # ROUND TO THE NEAREST INTEGER
        return round(total_xp)

    def get_xp_needed(self, level):
        """
        ACCURATE MATH: 
        Level 1 = 1,000 XP
        Level 100 = 1,000,000 XP
        Formula: 1000 * (level ^ 1.5)
        """
        if level <= 0:
            return 0
        return int(1000 * (level ** 1.5))

    def get_level_from_xp(self, xp):
        """Calculate what level a user is based on total XP"""
        level = 0
        while self.get_xp_needed(level + 1) <= xp:
            level += 1
        return level

    def get_rank(self, guild_id, user_id):
        """Helper to get the user's rank on the leaderboard"""
        # MongoDB aggregation to get the user's rank
        pipeline = [
            {"$match": {"guild_id": guild_id}},
            {"$sort": {"xp": -1}},
            {"$group": {"_id": None, "items": {"$push": "$$ROOT"}}},
            {"$unwind": {"path": "$items", "includeArrayIndex": "rank"}},
            {"$match": {"items.user_id": user_id}},
            {"$project": {"rank": {"$add": ["$rank", 1]}}}
        ]
        result = list(levels_collection.aggregate(pipeline))
        if result:
            return result[0]["rank"]
        return 0

    # ==========================================
    # FINAL !LEVEL COMMAND (Sends RAW Image + Button)
    # ==========================================

    @commands.command(name="level", aliases=["lvl"])
    async def level(self, ctx, *, member: discord.Member = None):
        """Check your current level and XP progress. Usage: !level, !level @User, !level Name"""
        if member is None:
            member = ctx.author
        
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        
        # Strip emojis from the display name before sending it!
        raw_name = member.display_name
        clean_name = ''.join(c for c in raw_name if c.isalnum() or c in (' ', '-', '_', '.', '#'))
        
        # Get the XP data from this user (MongoDB)
        doc = levels_collection.find_one({"guild_id": guild_id, "user_id": user_id})
        
        if not doc:
            return await ctx.send(f"❌ {member.mention} hasn't chatted enough to have a rank yet!")
        
        current_xp = doc["xp"]
        current_level = self.get_level_from_xp(current_xp)
        
        # Calculate progress to next level
        next_level_xp = self.get_xp_needed(current_level + 1)
        prev_level_xp = self.get_xp_needed(current_level)
        xp_in_level = current_xp - prev_level_xp
        xp_needed_for_next = next_level_xp - prev_level_xp
        
        if xp_needed_for_next == 0: progress = 1.0
        else: progress = xp_in_level / xp_needed_for_next
        
        rank = self.get_rank(guild_id, user_id)
        avatar_url = member.display_avatar.with_format("png").replace(size=512).url
        dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:8000")
        
        image_url = f"{dashboard_url}/get_card/{guild_id}/{user_id}?name={clean_name}&xp={int(current_xp)}&next_xp={int(next_level_xp)}&progress={progress:.2f}&avatar={avatar_url}&level={current_level}&rank={rank}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status == 200:
                        image_data = await resp.read()
                        file = discord.File(fp=io.BytesIO(image_data), filename="rank.png")
                        view = CardButton(dashboard_url)
                        await ctx.send(file=file, view=view)
                    else:
                        await ctx.send(f"❌ Failed to generate rank card (Dashboard returned {resp.status})")
        except Exception as e:
            await ctx.send(f"❌ Error fetching rank card: {e}")

    # ==========================================
    # BEAUTIFUL LEADERBOARD COMMAND (With Button to Web Leaderboard)
    # ==========================================

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):
        """Show the top 10 levelers in the server with a web button"""
        guild_id = str(ctx.guild.id)
        
        count = levels_collection.count_documents({"guild_id": guild_id})
        if count == 0:
            return await ctx.send("❌ No level data for this server yet!")
        
        results = levels_collection.find({"guild_id": guild_id}).sort("xp", pymongo.DESCENDING).limit(10)
        sorted_users = list(results)
        
        dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:8000")
        clean_dashboard_url = dashboard_url.rstrip('/')
        web_url = f"{clean_dashboard_url}/leaderboard/{guild_id}"
        
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="View leaderboard",
                style=discord.ButtonStyle.link,
                url=web_url,
                emoji="📊"
            )
        )
        
        embed = discord.Embed(title=f"{ctx.guild.name}", color=discord.Color.dark_embed())
        leaderboard_text = ""
        for i, doc in enumerate(sorted_users, 1):
            member = ctx.guild.get_member(int(doc["user_id"]))
            if member:
                level = self.get_level_from_xp(doc["xp"])
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
                leaderboard_text += f"**{medal}** • `@{member.display_name}` • **LVL: {level}**\n"
        
        embed.description = leaderboard_text
        embed.set_footer(text=f"{count} members • Overall XP")
        
        await ctx.send(embed=embed, view=view)

    # ==========================================
    # ADMIN SETTINGS COMMANDS
    # ==========================================

    @commands.command(name="xpslmset")
    @commands.has_permissions(administrator=True)
    async def xp_slowmode_set(self, ctx, seconds: int):
        if seconds < 0: return await ctx.send("❌ Slowmode cannot be negative!")
        self.COOLDOWN_SECONDS = seconds
        self.save_config()
        if seconds == 0: await ctx.send("✅ XP Slowmode **DISABLED**.")
        else: await ctx.send(f"✅ XP Slowmode set to **{seconds}** seconds.")

    @commands.command(name="xpslmby")
    @commands.has_permissions(administrator=True)
    async def xp_slowmode_bypass(self, ctx, target_type: str, *, target_id: str = None):
        guild = ctx.guild
        target_type = target_type.lower()
        if target_type == "user":
            if not ctx.message.mentions: return await ctx.send("❌ Mention a user.")
            member = ctx.message.mentions[0]
            user_id = str(member.id)
            if user_id in self.bypass_users:
                self.bypass_users.remove(user_id); self.save_config()
                await ctx.send(f"✅ Removed {member.mention} from bypass.")
            else:
                self.bypass_users.add(user_id); self.save_config()
                await ctx.send(f"✅ Added {member.mention} to bypass.")
        elif target_type == "userid":
            if not target_id: return await ctx.send("❌ Provide a user ID.")
            try:
                user_id = str(int(target_id))
                if user_id in self.bypass_users:
                    self.bypass_users.remove(user_id); self.save_config()
                    await ctx.send(f"✅ Removed User ID `{user_id}`.")
                else:
                    self.bypass_users.add(user_id); self.save_config()
                    await ctx.send(f"✅ Added User ID `{user_id}`.")
            except: return await ctx.send("❌ Invalid User ID.")
        elif target_type == "role":
            if not ctx.message.role_mentions: return await ctx.send("❌ Mention a role.")
            role = ctx.message.role_mentions[0]
            role_id = str(role.id)
            if role_id in self.bypass_roles:
                self.bypass_roles.remove(role_id); self.save_config()
                await ctx.send(f"✅ Removed {role.mention} from bypass.")
            else:
                self.bypass_roles.add(role_id); self.save_config()
                await ctx.send(f"✅ Added {role.mention} to bypass.")
        else: await ctx.send("❌ Use: `user`, `userid`, or `role`.")

    @commands.command(name="xpslmlist")
    @commands.has_permissions(administrator=True)
    async def xp_slowmode_list(self, ctx):
        embed = discord.Embed(title="⚡ XP Slowmode Bypass List", color=discord.Color.blue())
        embed.add_field(name="⏱️ Current Slowmode", value=f"{self.COOLDOWN_SECONDS} seconds", inline=False)
        if self.bypass_users:
            bypass_members = []
            for user_id in self.bypass_users:
                member = ctx.guild.get_member(int(user_id))
                bypass_members.append(member.mention if member else f"User ID: `{user_id}`")
            embed.add_field(name="👤 Bypass Users", value="\n".join(bypass_members), inline=False)
        else: embed.add_field(name="👤 Bypass Users", value="None", inline=False)
        if self.bypass_roles:
            bypass_roles = []
            for role_id in self.bypass_roles:
                role = ctx.guild.get_role(int(role_id))
                bypass_roles.append(role.mention if role else f"Role ID: `{role_id}`")
            embed.add_field(name="👥 Bypass Roles", value="\n".join(bypass_roles), inline=False)
        else: embed.add_field(name="👥 Bypass Roles", value="None", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="setlevelchannel")
    @commands.has_permissions(administrator=True)
    async def set_level_channel(self, ctx, channel: discord.TextChannel):
        self.level_channel_id = channel.id
        self.save_config()
        await ctx.send(f"✅ Level-Up announcements sent to {channel.mention}!")

    # ==========================================
    # ADMIN ROLE SETUP COMMANDS
    # ==========================================

    @commands.command(name="autosetuplevelroles")
    @commands.has_permissions(administrator=True)
    async def auto_setup_level_roles(self, ctx):
        guild = ctx.guild
        created_roles, existing_roles = [], []
        for level in self.levels:
            role_name = f"Level {level}"
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                try:
                    new_role = await guild.create_role(name=role_name, color=self.get_role_color(level), permissions=self.get_role_permissions(level))
                    created_roles.append(new_role.name)
                except: return await ctx.send("❌ Missing perms to create roles.")
            else:
                try:
                    await role.edit(color=self.get_role_color(level), permissions=self.get_role_permissions(level))
                    existing_roles.append(role.name)
                except: await ctx.send(f"⚠️ Could not update {role.name}")
        
        for level in self.levels:
            role = discord.utils.get(guild.roles, name=f"Level {level}")
            if role:
                roles_collection.update_one(
                    {"guild_id": str(guild.id), "level": level},
                    {"$set": {"role_id": role.id}},
                    upsert=True
                )
        
        embed = discord.Embed(title="✅ Setup Complete", color=discord.Color.green())
        embed.add_field(name="Created", value=str(len(created_roles)), inline=True)
        embed.add_field(name="Updated", value=str(len(existing_roles)), inline=True)
        if created_roles: embed.add_field(name="New Roles", value=", ".join(created_roles), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="removealllevelroles")
    @commands.has_permissions(administrator=True)
    async def remove_all_level_roles(self, ctx):
        guild = ctx.guild
        level_roles = [role for role in guild.roles if role.name in [f"Level {l}" for l in self.levels]]
        if not level_roles: return await ctx.send("❌ No level roles found.")
        deleted_count = 0
        for role in level_roles:
            try: await role.delete(); deleted_count += 1
            except: pass
        roles_collection.delete_many({"guild_id": str(guild.id)})
        await ctx.send(f"✅ Deleted {deleted_count} level roles.")

    @commands.command(name="autodeletelevelroles")
    @commands.has_permissions(administrator=True)
    async def auto_delete_level_roles(self, ctx, target=None, *, user_id=None):
        if target is None: return await ctx.send("❌ Specify: `user @User` or `userid 123`")
        target = target.lower()
        if target == "user":
            if not ctx.message.mentions: return await ctx.send("❌ Mention a user.")
            member = ctx.message.mentions[0]
        elif target == "userid":
            if not user_id: return await ctx.send("❌ Provide a user ID.")
            try: member = ctx.guild.get_member(int(user_id))
            except: return await ctx.send("❌ Invalid user ID.")
            if not member: return await ctx.send("❌ User not found.")
        else: return await ctx.send("❌ Invalid option.")
        
        level_role_names = [f"Level {l}" for l in self.levels]
        roles_to_remove = [r for r in member.roles if r.name in level_role_names]
        removed = 0
        for role in roles_to_remove:
            try: await member.remove_roles(role); removed += 1
            except: pass
        await ctx.send(f"✅ Removed {removed} level roles from {member.mention}.")

    @commands.command(name="addlevelrole")
    @commands.has_permissions(administrator=True)
    async def add_level_role(self, ctx, level: int, role: discord.Role):
        if level not in self.levels: return await ctx.send("❌ Invalid level.")
        roles_collection.update_one(
            {"guild_id": str(ctx.guild.id), "level": level},
            {"$set": {"role_id": role.id}},
            upsert=True
        )
        await ctx.send(f"✅ Added Level {level} -> {role.mention}")

    @commands.command(name="removelevelrole")
    @commands.has_permissions(administrator=True)
    async def remove_level_role(self, ctx, level: int):
        roles_collection.delete_one({"guild_id": str(ctx.guild.id), "level": level})
        await ctx.send(f"✅ Removed Level {level} mapping.")

    @commands.command(name="listlevelroles")
    @commands.has_permissions(administrator=True)
    async def list_level_roles(self, ctx):
        results = roles_collection.find({"guild_id": str(ctx.guild.id)}).sort("level", 1)
        embed = discord.Embed(title="📋 Level Roles", color=discord.Color.blue())
        for doc in results:
            level = doc["level"]
            role_id = doc["role_id"]
            role = ctx.guild.get_role(role_id)
            if role:
                perms = self.get_role_permissions(level)
                perm_list = []
                if perms.attach_files: perm_list.append("📎 Files")
                if perms.embed_links: perm_list.append("🔗 Embeds")
                embed.add_field(name=f"Level {level}", value=f"{role.mention}\n*{', '.join(perm_list) if perm_list else 'Base'}*", inline=False)
        await ctx.send(embed=embed)

    # ==========================================
    # ADDXP JSON + FILE SUPPORT (FULLY UPDATED FOR MONGODB)
    # ==========================================

    @commands.command(name="addxp")
    @commands.has_permissions(administrator=True)
    async def add_xp(self, ctx, member_or_json: str = None, amount: float = None):
        """
        [Admin] Manually adds XP to a user, a JSON list, or a file attachment.
        Usage: 
            !addxp @User 500
            !addxp json {"user_id": 500, "user_id2": 300}
            !addxp file (attach a .txt or .json file)
        """
        # ==========================================
        # OPTION 1: Handle File Attachments
        # ==========================================
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            if attachment.filename.endswith(('.txt', '.json')):
                await ctx.send("⏳ Processing JSON file...")
                file_content = await attachment.read()
                json_text = file_content.decode('utf-8')
                if json_text.startswith("```"):
                    lines = json_text.split("\n")
                    if lines[0].startswith("```"): lines = lines[1:]
                    if lines[-1].strip() == "```": lines = lines[:-1]
                    json_text = "\n".join(lines)
                try:
                    data = json.loads(json_text.strip())
                    if isinstance(data, dict):
                        processed = 0
                        for user_id, xp in data.items():
                            if isinstance(xp, (int, float)) and xp > 0:
                                await self._add_xp_to_db(ctx.guild.id, user_id, xp)
                                processed += 1
                        await ctx.send(f"✅ Processed file. Added XP to **{processed}** users. (No pings sent)")
                    else:
                        await ctx.send("❌ Invalid JSON format. Must be a dictionary of `user_id: xp`.")
                except json.JSONDecodeError:
                    await ctx.send("❌ Failed to parse JSON from the attached file.")
                return
            else:
                return await ctx.send("❌ Please attach a `.txt` or `.json` file.")

        # ==========================================
        # OPTION 2: Handle "json" text command
        # ==========================================
        if member_or_json is not None and member_or_json.lower() == "json":
            if amount is None:
                return await ctx.send("❌ Missing JSON data. Example: `!addxp json {\"123456789\": 500}`")
            json_str = amount
            try:
                data = json.loads(json_str)
                if isinstance(data, dict):
                    processed = 0
                    for user_id, xp in data.items():
                        if isinstance(xp, (int, float)) and xp > 0:
                            await self._add_xp_to_db(ctx.guild.id, user_id, xp)
                            processed += 1
                    await ctx.send(f"✅ Added XP to **{processed}** users from JSON list. (No pings sent)")
                else:
                    await ctx.send("❌ Invalid JSON. Must be a dictionary of `user_id: xp`.")
            except json.JSONDecodeError:
                await ctx.send("❌ Failed to parse JSON.")
            return

        # ==========================================
        # OPTION 3: Single User Addition (No Pings + Safety Cap)
        # ==========================================
        if member_or_json is None or amount is None:
            return await ctx.send("❌ Usage: `!addxp @User 500` or `!addxp json {\"id\": xp}` or attach a file.")
        
        if amount > 10000000:
            return await ctx.send("❌ You cannot add more than 10,000,000 XP at once!")

        try:
            converter = commands.MemberConverter()
            member = await converter.convert(ctx, member_or_json)
        except:
            return await ctx.send("❌ Invalid user. Please mention a user or provide a valid User ID.")

        if amount <= 0:
            return await ctx.send("❌ You must add a positive amount of XP!")

        await self._add_xp_to_db(ctx.guild.id, str(member.id), amount)
        await ctx.send(f"✅ Successfully added **{amount} XP** to `{member.display_name}`. (No ping sent)")

    async def _add_xp_to_db(self, guild_id, user_id, amount):
        """Internal helper to add XP to MongoDB without pinging."""
        levels_collection.update_one(
            {"guild_id": guild_id, "user_id": user_id},
            {"$inc": {"xp": amount}},
            upsert=True
        )

    @commands.command(name="removexp")
    @commands.has_permissions(administrator=True)
    async def remove_xp(self, ctx, member: discord.Member, amount: float):
        if amount <= 0: return await ctx.send("❌ Must remove positive amount.")
        guild_id = str(ctx.guild.id); user_id = str(member.id)
        
        doc = levels_collection.find_one({"guild_id": guild_id, "user_id": user_id})
        if not doc:
            return await ctx.send(f"❌ User doesn't have any XP to remove!")
        
        current_xp = doc["xp"]
        if current_xp < amount:
            return await ctx.send(f"❌ User only has {current_xp:,} XP. You cannot remove {amount} XP!")

        new_xp = round(current_xp - amount)
        if new_xp < 0: new_xp = 0
        
        levels_collection.update_one(
            {"guild_id": guild_id, "user_id": user_id},
            {"$set": {"xp": new_xp}}
        )
        
        new_level = self.get_level_from_xp(new_xp)
        await ctx.send(f"✅ Successfully removed **{amount} XP** from `{member.display_name}`. (No ping sent)\nThey are now at Level {new_level} with {new_xp:,} total XP.")

    @commands.command(name="deletejson")
    @commands.has_permissions(administrator=True)
    async def delete_json_data(self, ctx):
        json_file = "level_data.json"
        if not os.path.exists(json_file):
            return await ctx.send("✅ `level_data.json` does not exist. The bot is already using MongoDB correctly!")
        
        await ctx.send("⚠️ **WARNING:** This will permanently delete `level_data.json`. Your XP is currently stored in MongoDB. Are you sure?\n\nType `yes` to confirm, or `no` to cancel.")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['yes', 'no']
        
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send("⏳ Confirmation timed out. Command cancelled.")
        
        if msg.content.lower() == 'no':
            return await ctx.send("✅ Command cancelled. `level_data.json` was kept.")
        
        try:
            os.remove(json_file)
            await ctx.send(f"✅ Successfully deleted `{json_file}`. The bot will now **only** use MongoDB.")
        except Exception as e:
            await ctx.send(f"❌ Failed to delete the file: {e}")

    # ==========================================
    # XP LISTENER (The Core System - MongoDB version)
    # ==========================================

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        guild_id = str(message.guild.id); user_id = str(message.author.id)
        
        is_bypassed = user_id in self.bypass_users
        if not is_bypassed:
            for role in message.author.roles:
                if str(role.id) in self.bypass_roles: is_bypassed = True; break
        if not is_bypassed:
            now = asyncio.get_event_loop().time()
            if user_id in self.xp_cooldowns and now - self.xp_cooldowns[user_id] < self.COOLDOWN_SECONDS: return
            self.xp_cooldowns[user_id] = now
        
        doc = levels_collection.find_one({"guild_id": guild_id, "user_id": user_id})
        if not doc:
            levels_collection.insert_one({"guild_id": guild_id, "user_id": user_id, "xp": 0})
            old_xp = 0
        else:
            old_xp = doc["xp"]
        
        old_level = self.get_level_from_xp(old_xp)
        xp_gained = self.calculate_xp_gain(message)
        new_xp = round(old_xp + xp_gained)
        
        levels_collection.update_one(
            {"guild_id": guild_id, "user_id": user_id},
            {"$set": {"xp": new_xp}}
        )
        
        new_level = self.get_level_from_xp(new_xp)
        if new_level > old_level and new_level in self.levels:
            guild = message.guild
            role_name = f"Level {new_level}"
            role = discord.utils.get(guild.roles, name=role_name)
            if role and role not in message.author.roles:
                try:
                    await message.author.add_roles(role)
                    level_channel = guild.get_channel(self.level_channel_id) or message.channel
                    embed = discord.Embed(title=f"🎉 Level Up!", description=f"{message.author.mention} reached **Level {new_level}**!", color=self.get_role_color(new_level))
                    await level_channel.send(embed=embed)
                except: pass

# ==========================================
# SETUP FUNCTION
# ==========================================
async def setup(bot):
    await bot.add_cog(LevelBot(bot))
