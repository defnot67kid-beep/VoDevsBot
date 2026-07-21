import discord
from discord.ext import commands
import sqlite3
import os
import asyncio
import json
import math
import random
import aiohttp
import io

# ==========================================
# DATABASE SETUP (SQLITE)
# ==========================================
DB_FILE = "level_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Create table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS levels
                 (guild_id TEXT, user_id TEXT, xp INTEGER, PRIMARY KEY (guild_id, user_id))''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# SMART BUTTON VIEW (Never disabled, works for everyone)
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

class LevelBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_file = DB_FILE
        self.role_data_file = "level_roles.json"
        self.level_roles = self.load_role_data()
        
        self.xp_cooldowns = {}
        self.COOLDOWN_SECONDS = 45
        self.bypass_users = set()
        self.bypass_roles = set()
        self.level_channel_id = 1526989768595083384
        
        self.load_config()
        self.levels = [2, 5, 10, 20, 35, 50, 60, 70, 100]

    def load_role_data(self):
        if os.path.exists(self.role_data_file):
            with open(self.role_data_file, 'r') as f:
                return json.load(f)
        return {}
            
    def save_role_data(self):
        with open(self.role_data_file, 'w') as f:
            json.dump(self.level_roles, f, indent=4)
            
    def load_config(self):
        config_file = "level_config.json"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.COOLDOWN_SECONDS = config.get("cooldown_seconds", 45)
                self.bypass_users = set(config.get("bypass_users", []))
                self.bypass_roles = set(config.get("bypass_roles", []))
                self.level_channel_id = config.get("level_channel_id", 1526989768595083384)
        else:
            self.save_config()
            
    def save_config(self):
        config_file = "level_config.json"
        config = {
            "cooldown_seconds": self.COOLDOWN_SECONDS,
            "bypass_users": list(self.bypass_users),
            "bypass_roles": list(self.bypass_roles),
            "level_channel_id": self.level_channel_id
        }
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)

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
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT user_id, xp FROM levels WHERE guild_id = ? ORDER BY xp DESC", (guild_id,))
        results = c.fetchall()
        conn.close()
        
        for i, (uid, xp) in enumerate(results, 1):
            if uid == user_id:
                return i
        return 0

    # ==========================================
    # FINAL !LEVEL COMMAND (Sends RAW Image + Button)
    # ==========================================

    @commands.command(name="level", aliases=["lvl"])
    async def level(self, ctx, *, member: discord.Member = None):
        if member is None:
            member = ctx.author
        
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        
        raw_name = member.display_name
        clean_name = ''.join(c for c in raw_name if c.isalnum() or c in (' ', '-', '_', '.', '#'))
        
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT xp FROM levels WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        result = c.fetchone()
        
        if not result:
            conn.close()
            return await ctx.send(f"❌ {member.mention} hasn't chatted enough to have a rank yet!")
        
        current_xp = result[0]
        conn.close()
        
        current_level = self.get_level_from_xp(current_xp)
        
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

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):
        guild_id = str(ctx.guild.id)
        dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:8000")
        
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM levels WHERE guild_id = ?", (guild_id,))
        count = c.fetchone()[0]
        if count == 0:
            conn.close()
            return await ctx.send("❌ No level data for this server yet!")
        
        c.execute("SELECT user_id, xp FROM levels WHERE guild_id = ? ORDER BY xp DESC LIMIT 10", (guild_id,))
        sorted_users = c.fetchall()
        conn.close()
        
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="View leaderboard",
                style=discord.ButtonStyle.link,
                url=f"{dashboard_url}/leaderboard/VoDevs",
                emoji="📊"
            )
        )
        
        embed = discord.Embed(title=f"{ctx.guild.name}", color=discord.Color.dark_embed())
        leaderboard_text = ""
        for i, (user_id, xp) in enumerate(sorted_users, 1):
            member = ctx.guild.get_member(int(user_id))
            if member:
                level = self.get_level_from_xp(xp)
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
                leaderboard_text += f"**{medal}** • `@{member.display_name}` • **LVL: {level}**\n"
        
        embed.description = leaderboard_text
        embed.set_footer(text=f"{count} members • Overall XP")
        
        await ctx.send(embed=embed, view=view)

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
        if str(guild.id) not in self.level_roles: self.level_roles[str(guild.id)] = {}
        for level in self.levels:
            role = discord.utils.get(guild.roles, name=f"Level {level}")
            if role: self.level_roles[str(guild.id)][str(level)] = role.id
        self.save_role_data()
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
        if str(guild.id) in self.level_roles: del self.level_roles[str(guild.id)]
        self.save_role_data()
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
        guild = ctx.guild
        if str(guild.id) not in self.level_roles: self.level_roles[str(guild.id)] = {}
        self.level_roles[str(guild.id)][str(level)] = role.id
        self.save_role_data()
        await ctx.send(f"✅ Added Level {level} -> {role.mention}")

    @commands.command(name="removelevelrole")
    @commands.has_permissions(administrator=True)
    async def remove_level_role(self, ctx, level: int):
        guild = ctx.guild
        if str(guild.id) not in self.level_roles: return await ctx.send("❌ No level roles configured.")
        if str(level) in self.level_roles[str(guild.id)]:
            del self.level_roles[str(guild.id)][str(level)]
            self.save_role_data()
            await ctx.send(f"✅ Removed Level {level} mapping.")
        else: await ctx.send(f"❌ Level {level} not configured.")

    @commands.command(name="listlevelroles")
    @commands.has_permissions(administrator=True)
    async def list_level_roles(self, ctx):
        guild = ctx.guild
        if str(guild.id) not in self.level_roles or not self.level_roles[str(guild.id)]:
            return await ctx.send("❌ No level roles configured.")
        embed = discord.Embed(title="📋 Level Roles", color=discord.Color.blue())
        for level, role_id in sorted(self.level_roles[str(guild.id)].items(), key=lambda x: int(x[0])):
            role = guild.get_role(role_id)
            if role:
                perms = self.get_role_permissions(int(level))
                perm_list = []
                if perms.attach_files: perm_list.append("📎 Files")
                if perms.embed_links: perm_list.append("🔗 Embeds")
                embed.add_field(name=f"Level {level}", value=f"{role.mention}\n*{', '.join(perm_list) if perm_list else 'Base'}*", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="addxp")
    @commands.has_permissions(administrator=True)
    async def add_xp(self, ctx, member: discord.Member, amount: float):
        if amount <= 0: return await ctx.send("❌ Must add positive amount.")
        guild_id = str(ctx.guild.id); user_id = str(member.id)
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT xp FROM levels WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        result = c.fetchone()
        if not result:
            c.execute("INSERT INTO levels (guild_id, user_id, xp) VALUES (?, ?, ?)", (guild_id, user_id, 0))
            current_xp = 0
        else:
            current_xp = result[0]
        
        new_xp = round(current_xp + amount)
        c.execute("UPDATE levels SET xp = ? WHERE guild_id = ? AND user_id = ?", (new_xp, guild_id, user_id))
        conn.commit()
        conn.close()
        new_level = self.get_level_from_xp(new_xp)
        if new_level in self.levels:
            role_name = f"Level {new_level}"
            role = discord.utils.get(ctx.guild.roles, name=role_name)
            if role:
                try:
                    await member.add_roles(role)
                    await ctx.send(f"🎉 {member.mention} leveled up to Level {new_level}!")
                except: await ctx.send(f"✅ Added {amount} XP.")
            return
        await ctx.send(f"✅ Added {amount} XP to {member.mention}.")

    @commands.command(name="removexp")
    @commands.has_permissions(administrator=True)
    async def remove_xp(self, ctx, member: discord.Member, amount: float):
        if amount <= 0: return await ctx.send("❌ Must remove positive amount.")
        guild_id = str(ctx.guild.id); user_id = str(member.id)
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT xp FROM levels WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        result = c.fetchone()
        if not result:
            conn.close()
            return await ctx.send(f"❌ {member.mention} has no XP.")
        current_xp = result[0]
        if current_xp < amount:
            conn.close()
            return await ctx.send(f"❌ {member.mention} only has {current_xp} XP.")
        new_xp = round(current_xp - amount)
        if new_xp < 0: new_xp = 0
        c.execute("UPDATE levels SET xp = ? WHERE guild_id = ? AND user_id = ?", (new_xp, guild_id, user_id))
        conn.commit()
        conn.close()
        await ctx.send(f"✅ Removed {amount} XP from {member.mention}.")

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
        
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT xp FROM levels WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        result = c.fetchone()
        if not result:
            c.execute("INSERT INTO levels (guild_id, user_id, xp) VALUES (?, ?, ?)", (guild_id, user_id, 0))
            old_xp = 0
        else:
            old_xp = result[0]
        
        old_level = self.get_level_from_xp(old_xp)
        xp_gained = self.calculate_xp_gain(message)
        new_xp = round(old_xp + xp_gained)
        c.execute("UPDATE levels SET xp = ? WHERE guild_id = ? AND user_id = ?", (new_xp, guild_id, user_id))
        conn.commit()
        conn.close()
        
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

async def setup(bot):
    await bot.add_cog(LevelBot(bot))
