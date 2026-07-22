import discord
from discord.ext import commands
from discord import app_commands
import pymongo
import os
import json
import asyncio
import math
import random
import aiohttp
import io

# ==========================================
# MONGODB SETUP
# ==========================================
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI environment variable is not set!")

client = pymongo.MongoClient(MONGO_URI)
db = client["vodevs_bot_data"]
levels_collection = db["levels"]
roles_collection = db["roles"]
config_collection = db["config"]

# ==========================================
# CARD BUTTON VIEW
# ==========================================
class CardButton(discord.ui.View):
    def __init__(self, dashboard_url):
        super().__init__(timeout=None)
        self.dashboard_url = dashboard_url

    @discord.ui.button(label="/card", style=discord.ButtonStyle.primary, emoji="🎨")
    async def card_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        clicker_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        specific_url = f"{self.dashboard_url}/dashboard/{guild_id}/{clicker_id}"
        await interaction.response.send_message(
            f"🔗 Click this link to edit **your** rank card:\n{specific_url}",
            ephemeral=True
        )


# ==========================================
# CLASS 1: PREFIX COMMANDS (!level, !lb, etc.)
# ==========================================
class LevelBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_cooldowns = {}
        self.COOLDOWN_SECONDS = 45
        self.bypass_users = set()
        self.bypass_roles = set()
        self.level_channel_id = 1526989768595083384
        self.load_config()
        self.levels = [2, 5, 10, 20, 35, 50, 60, 70, 100]

    def load_config(self):
        doc = config_collection.find_one({"_id": "bot_config"})
        if doc:
            self.COOLDOWN_SECONDS = doc.get("cooldown_seconds", 45)
            self.bypass_users = set(doc.get("bypass_users", []))
            self.bypass_roles = set(doc.get("bypass_roles", []))
            self.level_channel_id = doc.get("level_channel_id", 1526989768595083384)
            
    def save_config(self):
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
        colors = {
            2: discord.Color.from_rgb(46, 204, 113), 5: discord.Color.from_rgb(52, 152, 219),
            10: discord.Color.from_rgb(155, 89, 182), 20: discord.Color.from_rgb(230, 126, 34),
            35: discord.Color.from_rgb(231, 76, 60), 50: discord.Color.from_rgb(241, 196, 15),
            60: discord.Color.from_rgb(26, 188, 156), 70: discord.Color.from_rgb(142, 68, 173),
            100: discord.Color.from_rgb(192, 57, 43)
        }
        return colors.get(level, discord.Color.default())

    def get_role_permissions(self, level):
        perms = discord.Permissions()
        perms.read_messages = True
        perms.send_messages = True
        perms.read_message_history = True
        if level >= 10: perms.attach_files = True
        if level >= 20: perms.embed_links = True
        return perms

    def calculate_xp_gain(self, message):
        content = message.content
        length = len(content)
        base_xp = 5
        total_char_xp = 0
        for _ in range(length):
            total_char_xp += random.randint(1, 5)
        total_xp = base_xp + total_char_xp
        if message.attachments:
            for attachment in message.attachments:
                size_kb = attachment.size / 1024
                file_xp = size_kb * 0.001
                total_xp += file_xp
        if total_xp > 1000: total_xp = 1000
        return round(total_xp)

    def get_xp_needed(self, level):
        if level <= 0: return 0
        return int(1000 * (level ** 1.5))

    def get_level_from_xp(self, xp):
        level = 0
        while self.get_xp_needed(level + 1) <= xp:
            level += 1
        return level

    def get_rank(self, guild_id, user_id):
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

    async def _get_rank_file(self, guild_id, user_id, display_name, avatar_url):
        clean_name = ''.join(c for c in display_name if c.isalnum() or c in (' ', '-', '_', '.', '#'))
        dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:8000")
        
        doc = levels_collection.find_one({"guild_id": guild_id, "user_id": user_id})
        if not doc: return None
        
        current_xp = doc["xp"]
        current_level = self.get_level_from_xp(current_xp)
        rank = self.get_rank(guild_id, user_id)
        
        next_level_xp = self.get_xp_needed(current_level + 1)
        prev_level_xp = self.get_xp_needed(current_level)
        xp_in_level = current_xp - prev_level_xp
        xp_needed_for_next = next_level_xp - prev_level_xp
        
        if xp_needed_for_next == 0: progress = 1.0
        else: progress = xp_in_level / xp_needed_for_next
        
        image_url = f"{dashboard_url}/get_card/{guild_id}/{user_id}?name={clean_name}&xp={int(current_xp)}&next_xp={int(next_level_xp)}&progress={progress:.2f}&avatar={avatar_url}&level={current_level}&rank={rank}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status == 200:
                        image_data = await resp.read()
                        return discord.File(fp=io.BytesIO(image_data), filename="rank.png")
        except Exception as e:
            print(f"❌ Error fetching rank card: {e}")
            return None

    @commands.command(name="level", aliases=["lvl"])
    async def prefix_level(self, ctx, *, member: discord.Member = None):
        if member is None: member = ctx.author
        file = await self._get_rank_file(str(ctx.guild.id), str(member.id), member.display_name, member.display_avatar.with_format("png").replace(size=512).url)
        if file:
            view = CardButton(os.getenv("DASHBOARD_URL", "http://localhost:8000"))
            await ctx.send(file=file, view=view)
        else:
            await ctx.send(f"❌ {member.mention} hasn't chatted enough to have a rank yet!")

    @commands.command(name="leaderboard", aliases=["lb"])
    async def prefix_leaderboard(self, ctx):
        guild_id = str(ctx.guild.id)
        count = levels_collection.count_documents({"guild_id": guild_id})
        if count == 0:
            await ctx.send("❌ No level data for this server yet!")
            return
        
        results = levels_collection.find({"guild_id": guild_id}).sort("xp", pymongo.DESCENDING).limit(10)
        sorted_users = list(results)
        
        dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:8000")
        web_url = f"{dashboard_url.rstrip('/')}/leaderboard/{guild_id}"
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="View leaderboard", style=discord.ButtonStyle.link, url=web_url, emoji="📊"))
        
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

    @commands.command(name="xpslmset")
    @commands.has_permissions(administrator=True)
    async def prefix_xpslmset(self, ctx, seconds: int):
        if seconds < 0: return await ctx.send("❌ Slowmode cannot be negative!")
        self.COOLDOWN_SECONDS = seconds
        self.save_config()
        if seconds == 0: await ctx.send("✅ XP Slowmode **DISABLED**.")
        else: await ctx.send(f"✅ XP Slowmode set to **{seconds}** seconds.")

    @commands.command(name="xpslmby")
    @commands.has_permissions(administrator=True)
    async def prefix_xpslmby(self, ctx, target_type: str, *, target_id: str = None):
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
    async def prefix_xpslmlist(self, ctx):
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
    async def prefix_setlevelchannel(self, ctx, channel: discord.TextChannel):
        self.level_channel_id = channel.id
        self.save_config()
        await ctx.send(f"✅ Level-Up announcements sent to {channel.mention}!")

    @commands.command(name="autosetuplevelroles")
    @commands.has_permissions(administrator=True)
    async def prefix_autosetuplevelroles(self, ctx):
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
                roles_collection.update_one({"guild_id": str(guild.id), "level": level}, {"$set": {"role_id": role.id}}, upsert=True)
        
        embed = discord.Embed(title="✅ Setup Complete", color=discord.Color.green())
        embed.add_field(name="Created", value=str(len(created_roles)), inline=True)
        embed.add_field(name="Updated", value=str(len(existing_roles)), inline=True)
        if created_roles: embed.add_field(name="New Roles", value=", ".join(created_roles), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="removealllevelroles")
    @commands.has_permissions(administrator=True)
    async def prefix_removealllevelroles(self, ctx):
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
    async def prefix_autodeletelevelroles(self, ctx, target=None, *, user_id=None):
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
    async def prefix_addlevelrole(self, ctx, level: int, role: discord.Role):
        if level not in self.levels: return await ctx.send("❌ Invalid level.")
        roles_collection.update_one({"guild_id": str(ctx.guild.id), "level": level}, {"$set": {"role_id": role.id}}, upsert=True)
        await ctx.send(f"✅ Added Level {level} -> {role.mention}")

    @commands.command(name="removelevelrole")
    @commands.has_permissions(administrator=True)
    async def prefix_removelevelrole(self, ctx, level: int):
        roles_collection.delete_one({"guild_id": str(ctx.guild.id), "level": level})
        await ctx.send(f"✅ Removed Level {level} mapping.")

    @commands.command(name="listlevelroles")
    @commands.has_permissions(administrator=True)
    async def prefix_listlevelroles(self, ctx):
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

    @commands.command(name="addxp")
    @commands.has_permissions(administrator=True)
    async def prefix_addxp(self, ctx, member_or_json: str = None, amount: float = None):
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

    @commands.command(name="removexp")
    @commands.has_permissions(administrator=True)
    async def prefix_removexp(self, ctx, member: discord.Member, amount: float):
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
        levels_collection.update_one({"guild_id": guild_id, "user_id": user_id}, {"$set": {"xp": new_xp}})
        new_level = self.get_level_from_xp(new_xp)
        await ctx.send(f"✅ Successfully removed **{amount} XP** from `{member.display_name}`. (No ping sent)\nThey are now at Level {new_level} with {new_xp:,} total XP.")

    @commands.command(name="deletejson")
    @commands.has_permissions(administrator=True)
    async def prefix_deletejson(self, ctx):
        json_file = "level_data.json"
        if not os.path.exists(json_file):
            return await ctx.send("✅ `level_data.json` does not exist. The bot is already using MongoDB correctly!")
        
        await ctx.send("⚠️ **WARNING:** This will permanently delete `level_data.json`. Your XP is currently stored in MongoDB. Are you sure?\n\nType `yes` to confirm, or `no` to cancel.")
        def check(m): return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['yes', 'no']
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

    async def _add_xp_to_db(self, guild_id, user_id, amount):
        levels_collection.update_one({"guild_id": guild_id, "user_id": user_id}, {"$inc": {"xp": amount}}, upsert=True)

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
        levels_collection.update_one({"guild_id": guild_id, "user_id": user_id}, {"$set": {"xp": new_xp}})
        
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
# CLASS 2: SLASH COMMANDS (/level, /leaderboard, etc.)
# ==========================================
class LevelSlashCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_cog(self):
        return self.bot.get_cog("LevelBot")

    @app_commands.command(name="level", description="Check your current level and XP progress")
    @app_commands.guild_only()
    async def slash_level(self, interaction: discord.Interaction, member: discord.Member = None):
        if member is None: member = interaction.user
        cog = self.get_cog()
        if not cog: return await interaction.response.send_message("❌ Cog not loaded.", ephemeral=True)
        file = await cog._get_rank_file(str(interaction.guild.id), str(member.id), member.display_name, member.display_avatar.with_format("png").replace(size=512).url)
        if file:
            view = CardButton(os.getenv("DASHBOARD_URL", "http://localhost:8000"))
            await interaction.response.send_message(file=file, view=view)
        else:
            await interaction.response.send_message(f"❌ {member.mention} hasn't chatted enough to have a rank yet!", ephemeral=True)

    @app_commands.command(name="leaderboard", description="Show the top 10 levelers in the server")
    @app_commands.guild_only()
    async def slash_leaderboard(self, interaction: discord.Interaction):
        cog = self.get_cog()
        if not cog: return await interaction.response.send_message("❌ Cog not loaded.", ephemeral=True)
        
        guild_id = str(interaction.guild.id)
        count = levels_collection.count_documents({"guild_id": guild_id})
        if count == 0:
            return await interaction.response.send_message("❌ No level data for this server yet!", ephemeral=True)

        results = levels_collection.find({"guild_id": guild_id}).sort("xp", pymongo.DESCENDING).limit(10)
        sorted_users = list(results)
        dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:8000")
        web_url = f"{dashboard_url.rstrip('/')}/leaderboard/{guild_id}"
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="View leaderboard", style=discord.ButtonStyle.link, url=web_url, emoji="📊"))
        
        embed = discord.Embed(title=f"{interaction.guild.name}", color=discord.Color.dark_embed())
        leaderboard_text = ""
        for i, doc in enumerate(sorted_users, 1):
            member = interaction.guild.get_member(int(doc["user_id"]))
            if member:
                level = cog.get_level_from_xp(doc["xp"])
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
                leaderboard_text += f"**{medal}** • `@{member.display_name}` • **LVL: {level}**\n"
        embed.description = leaderboard_text
        embed.set_footer(text=f"{count} members • Overall XP")
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="xpslowmode", description="[Admin] Set the global XP cooldown in seconds")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_xpslowmode(self, interaction: discord.Interaction, seconds: int):
        cog = self.get_cog()
        if not cog: return await interaction.response.send_message("❌ Cog not loaded.", ephemeral=True)
        cog.COOLDOWN_SECONDS = seconds
        cog.save_config()
        msg = "**DISABLED** (0 seconds). Users can gain XP instantly!" if seconds == 0 else f"set to **{seconds}** seconds."
        await interaction.response.send_message(f"✅ XP Slowmode {msg}", ephemeral=True)

    @app_commands.command(name="xpslowbypass", description="[Admin] Toggle XP cooldown bypass for a User or Role")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_xpslowbypass(self, interaction: discord.Interaction, target_type: str, target: str):
        cog = self.get_cog()
        if not cog: return await interaction.response.send_message("❌ Cog not loaded.", ephemeral=True)

        target_type = target_type.lower()
        if target_type == "user":
            try:
                converter = commands.MemberConverter()
                member = await converter.convert(interaction, target)
                user_id = str(member.id)
            except:
                return await interaction.response.send_message("❌ Invalid user. Mention a valid user.", ephemeral=True)
            if user_id in cog.bypass_users:
                cog.bypass_users.remove(user_id); cog.save_config()
                await interaction.response.send_message(f"✅ Removed {member.mention} from bypass.", ephemeral=True)
            else:
                cog.bypass_users.add(user_id); cog.save_config()
                await interaction.response.send_message(f"✅ Added {member.mention} to bypass.", ephemeral=True)
        elif target_type == "role":
            try:
                converter = commands.RoleConverter()
                role = await converter.convert(interaction, target)
                role_id = str(role.id)
            except:
                return await interaction.response.send_message("❌ Invalid role. Mention a valid role.", ephemeral=True)
            if role_id in cog.bypass_roles:
                cog.bypass_roles.remove(role_id); cog.save_config()
                await interaction.response.send_message(f"✅ Removed {role.mention} from bypass.", ephemeral=True)
            else:
                cog.bypass_roles.add(role_id); cog.save_config()
                await interaction.response.send_message(f"✅ Added {role.mention} to bypass.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Invalid target type! Use `user` or `role`.", ephemeral=True)

    @app_commands.command(name="xpslowlist", description="[Admin] List users and roles that bypass the XP cooldown")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_xpslowlist(self, interaction: discord.Interaction):
        cog = self.get_cog()
        if not cog: return await interaction.response.send_message("❌ Cog not loaded.", ephemeral=True)
        embed = discord.Embed(title="⚡ XP Slowmode Bypass List", color=discord.Color.blue())
        embed.add_field(name="⏱️ Current Slowmode", value=f"{cog.COOLDOWN_SECONDS} seconds", inline=False)
        if cog.bypass_users:
            bypass_members = []
            for user_id in cog.bypass_users:
                member = interaction.guild.get_member(int(user_id))
                bypass_members.append(member.mention if member else f"User ID: `{user_id}`")
            embed.add_field(name="👤 Bypass Users", value="\n".join(bypass_members), inline=False)
        else: embed.add_field(name="👤 Bypass Users", value="None", inline=False)
        if cog.bypass_roles:
            bypass_roles = []
            for role_id in cog.bypass_roles:
                role = interaction.guild.get_role(int(role_id))
                bypass_roles.append(role.mention if role else f"Role ID: `{role_id}`")
            embed.add_field(name="👥 Bypass Roles", value="\n".join(bypass_roles), inline=False)
        else: embed.add_field(name="👥 Bypass Roles", value="None", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setlevelchannel", description="[Admin] Set the channel where Level-Up announcements are sent")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_setlevelchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        cog = self.get_cog()
        if not cog: return await interaction.response.send_message("❌ Cog not loaded.", ephemeral=True)
        cog.level_channel_id = channel.id
        cog.save_config()
        await interaction.response.send_message(f"✅ Level-Up announcements will now be sent to {channel.mention}!", ephemeral=True)

    @app_commands.command(name="addxp", description="[Admin] Manually add XP to a user")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_addxp(self, interaction: discord.Interaction, member: discord.Member, amount: float):
        cog = self.get_cog()
        if not cog: return await interaction.response.send_message("❌ Cog not loaded.", ephemeral=True)
        if amount > 10000000:
            return await interaction.response.send_message("❌ You cannot add more than 10,000,000 XP at once!", ephemeral=True)
        await cog._add_xp_to_db(str(interaction.guild.id), str(member.id), amount)
        await interaction.response.send_message(f"✅ Successfully added **{amount} XP** to `{member.display_name}`.", ephemeral=True)

    @app_commands.command(name="removexp", description="[Admin] Manually remove XP from a user")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_removexp(self, interaction: discord.Interaction, member: discord.Member, amount: float):
        cog = self.get_cog()
        if not cog: return await interaction.response.send_message("❌ Cog not loaded.", ephemeral=True)
        guild_id = str(interaction.guild.id)
        user_id = str(member.id)
        doc = levels_collection.find_one({"guild_id": guild_id, "user_id": user_id})
        if not doc:
            return await interaction.response.send_message("❌ User doesn't have any XP to remove!", ephemeral=True)
        current_xp = doc["xp"]
        if current_xp < amount:
            return await interaction.response.send_message(f"❌ User only has {current_xp:,} XP. You cannot remove {amount} XP!", ephemeral=True)
        new_xp = round(current_xp - amount)
        if new_xp < 0: new_xp = 0
        levels_collection.update_one({"guild_id": guild_id, "user_id": user_id}, {"$set": {"xp": new_xp}})
        new_level = cog.get_level_from_xp(new_xp)
        await interaction.response.send_message(f"✅ Removed **{amount} XP** from `{member.display_name}`.\nThey are now at Level {new_level}.", ephemeral=True)

    @app_commands.command(name="autosetuplevelroles", description="[Admin] Automatically creates level roles up to Level 100")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_autosetuplevelroles(self, interaction: discord.Interaction):
        cog = self.get_cog()
        if not cog: return await interaction.response.send_message("❌ Cog not loaded.", ephemeral=True)
        guild = interaction.guild
        created_roles, existing_roles = [], []
        for level in cog.levels:
            role_name = f"Level {level}"
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                try:
                    new_role = await guild.create_role(name=role_name, color=cog.get_role_color(level), permissions=cog.get_role_permissions(level))
                    created_roles.append(new_role.name)
                except:
                    return await interaction.response.send_message("❌ Missing perms to create roles.", ephemeral=True)
            else:
                try:
                    await role.edit(color=cog.get_role_color(level), permissions=cog.get_role_permissions(level))
                    existing_roles.append(role.name)
                except:
                    await interaction.response.send_message(f"⚠️ Could not update {role.name}", ephemeral=True)
        
        for level in cog.levels:
            role = discord.utils.get(guild.roles, name=f"Level {level}")
            if role:
                roles_collection.update_one({"guild_id": str(guild.id), "level": level}, {"$set": {"role_id": role.id}}, upsert=True)
        
        embed = discord.Embed(title="✅ Setup Complete", color=discord.Color.green())
        embed.add_field(name="Created", value=str(len(created_roles)), inline=True)
        embed.add_field(name="Updated", value=str(len(existing_roles)), inline=True)
        if created_roles: embed.add_field(name="New Roles", value=", ".join(created_roles), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="removealllevelroles", description="[Admin] Deletes ALL level roles")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_removealllevelroles(self, interaction: discord.Interaction):
        cog = self.get_cog()
        if not cog: return await interaction.response.send_message("❌ Cog not loaded.", ephemeral=True)
        guild = interaction.guild
        level_roles = [role for role in guild.roles if role.name in [f"Level {l}" for l in cog.levels]]
        if not level_roles:
            return await interaction.response.send_message("❌ No level roles found.", ephemeral=True)
        deleted = 0
        for role in level_roles:
            try: await role.delete(); deleted += 1
            except: pass
        roles_collection.delete_many({"guild_id": str(guild.id)})
        await interaction.response.send_message(f"✅ Deleted {deleted} level roles.", ephemeral=True)

    @app_commands.command(name="addlevelrole", description="[Admin] Manually map a level to an existing role")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_addlevelrole(self, interaction: discord.Interaction, level: int, role: discord.Role):
        cog = self.get_cog()
        if not cog: return await interaction.response.send_message("❌ Cog not loaded.", ephemeral=True)
        if level not in cog.levels:
            return await interaction.response.send_message(f"❌ Invalid level! Choose from: {', '.join(map(str, cog.levels))}", ephemeral=True)
        roles_collection.update_one({"guild_id": str(interaction.guild.id), "level": level}, {"$set": {"role_id": role.id}}, upsert=True)
        await interaction.response.send_message(f"✅ Added Level {level} -> {role.mention}", ephemeral=True)

    @app_commands.command(name="removelevelrole", description="[Admin] Remove a level role mapping")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_removelevelrole(self, interaction: discord.Interaction, level: int):
        cog = self.get_cog()
        if not cog: return await interaction.response.send_message("❌ Cog not loaded.", ephemeral=True)
        roles_collection.delete_one({"guild_id": str(interaction.guild.id), "level": level})
        await interaction.response.send_message(f"✅ Removed Level {level} mapping.", ephemeral=True)

    @app_commands.command(name="listlevelroles", description="[Admin] List all mapped level roles")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_listlevelroles(self, interaction: discord.Interaction):
        cog = self.get_cog()
        if not cog: return await interaction.response.send_message("❌ Cog not loaded.", ephemeral=True)
        results = roles_collection.find({"guild_id": str(interaction.guild.id)}).sort("level", 1)
        embed = discord.Embed(title="📋 Level Roles", color=discord.Color.blue())
        for doc in results:
            level = doc["level"]
            role_id = doc["role_id"]
            role = interaction.guild.get_role(role_id)
            if role:
                perms = cog.get_role_permissions(level)
                perm_list = []
                if perms.attach_files: perm_list.append("📎 Files")
                if perms.embed_links: perm_list.append("🔗 Embeds")
                embed.add_field(name=f"Level {level}", value=f"{role.mention}\n*{', '.join(perm_list) if perm_list else 'Base'}*", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ==========================================
# SETUP FUNCTION (Fixes the "no setup function" error)
# ==========================================
async def setup(bot):
    await bot.add_cog(LevelBot(bot))
    await bot.add_cog(LevelSlashCommands(bot))
