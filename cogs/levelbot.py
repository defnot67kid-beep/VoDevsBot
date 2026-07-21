import discord
from discord.ext import commands
import sqlite3
import os
import json
import asyncio
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
        self.db_file = DB_FILE
        self.role_data_file = "level_roles.json"
        self.level_roles = self.load_role_data()
        
        # Cooldown dictionary (user_id -> last_message_time)
        self.xp_cooldowns = {}
        
        # Default slowmode (45 seconds). Can be changed by admins.
        self.COOLDOWN_SECONDS = 45
        
        # Bypass list (User IDs and Role IDs)
        self.bypass_users = set()
        self.bypass_roles = set()
        
        # Level-Up Announcement Channel ID
        self.level_channel_id = 1526989768595083384  # <--- YOUR CHANNEL ID HERE
        
        # Load bypass config & channel config
        self.load_config()
        
        # Define the level progression (STOPS AT 100)
        self.levels = [2, 5, 10, 20, 35, 50, 60, 70, 100]

    def load_role_data(self):
        """Load level role data from JSON file"""
        if os.path.exists(self.role_data_file):
            with open(self.role_data_file, 'r') as f:
                return json.load(f)
        return {}

    def save_role_data(self):
        """Save level role data to JSON file"""
        with open(self.role_data_file, 'w') as f:
            json.dump(self.level_roles, f, indent=4)
            
    def load_config(self):
        """Load cooldown, bypass, and channel config from a config file"""
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
        """Save cooldown, bypass, and channel config to a config file"""
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
        """Check your current level and XP progress. Usage: !level, !level @User, !level Name"""
        if member is None:
            member = ctx.author
        
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        
        # Strip emojis from the display name before sending it!
        raw_name = member.display_name
        clean_name = ''.join(c for c in raw_name if c.isalnum() or c in (' ', '-', '_', '.', '#'))
        
        # Get the XP data from this user (SQLite)
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
        
        # Calculate progress to next level
        next_level_xp = self.get_xp_needed(current_level + 1)
        prev_level_xp = self.get_xp_needed(current_level)
        xp_in_level = current_xp - prev_level_xp
        xp_needed_for_next = next_level_xp - prev_level_xp
        
        # Calculate percentage (0.0 to 1.0) for the progress bar
        if xp_needed_for_next == 0:
            progress = 1.0
        else:
            progress = xp_in_level / xp_needed_for_next
        
        # Calculate Rank
        rank = self.get_rank(guild_id, user_id)
        
        # Get the avatar URL as a PNG (Prevents GIF crashes)
        avatar_url = member.display_avatar.with_format("png").replace(size=512).url
        
        dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:8000")
        
        # Build the URL with GUILD_ID + USER_ID + LEVEL + RANK
        image_url = f"{dashboard_url}/get_card/{guild_id}/{user_id}?name={clean_name}&xp={int(current_xp)}&next_xp={int(next_level_xp)}&progress={progress:.2f}&avatar={avatar_url}&level={current_level}&rank={rank}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status == 200:
                        image_data = await resp.read()
                        file = discord.File(fp=io.BytesIO(image_data), filename="rank.png")
                        
                        # Send as RAW image (No embed) with the button
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
        
        # Check if data exists for this guild
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM levels WHERE guild_id = ?", (guild_id,))
        count = c.fetchone()[0]
        
        if count == 0:
            conn.close()
            return await ctx.send("❌ No level data for this server yet!")
        
        # Fetch top 10
        c.execute("SELECT user_id, xp FROM levels WHERE guild_id = ? ORDER BY xp DESC LIMIT 10", (guild_id,))
        sorted_users = c.fetchall()
        conn.close()
        
        # Get server name, remove spaces for URL
        server_name = ctx.guild.name.replace(" ", "")
        dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:8000")
        
        # Create the "View leaderboard" button
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="View leaderboard",
                style=discord.ButtonStyle.link,
                url=f"{dashboard_url}/leaderboard/{server_name}",
                emoji="📊"
            )
        )
        
        # Build a beautiful embed
        embed = discord.Embed(
            title=f"{ctx.guild.name}",
            color=discord.Color.dark_embed()
        )
        
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

    # ==========================================
    # ADMIN SETTINGS COMMANDS
    # ==========================================

    @commands.command(name="xpslmset")
    @commands.has_permissions(administrator=True)
    async def xp_slowmode_set(self, ctx, seconds: int):
        """
        [Admin] Sets the global XP cooldown (slowmode) in seconds.
        Usage: !xpslmset 30
        """
        if seconds < 0:
            return await ctx.send("❌ Slowmode cannot be negative!")
        
        self.COOLDOWN_SECONDS = seconds
        self.save_config()
        
        if seconds == 0:
            await ctx.send(f"✅ XP Slowmode **DISABLED** (0 seconds). Users can gain XP instantly on every message!")
        else:
            await ctx.send(f"✅ XP Slowmode set to **{seconds}** seconds between XP gains.")

    @commands.command(name="xpslmby")
    @commands.has_permissions(administrator=True)
    async def xp_slowmode_bypass(self, ctx, target_type: str, *, target_id: str = None):
        """
        [Admin] Bypasses the XP cooldown for a User, UserID, or Role.
        Usage: 
            !xpslmby user @User
            !xpslmby userid 123456789
            !xpslmby role @Role
        """
        guild = ctx.guild
        target_type = target_type.lower()
        
        if target_type == "user":
            if not ctx.message.mentions:
                return await ctx.send("❌ Please mention a user: `!xpslmby user @User`")
            member = ctx.message.mentions[0]
            user_id = str(member.id)
            
            if user_id in self.bypass_users:
                self.bypass_users.remove(user_id)
                self.save_config()
                await ctx.send(f"✅ Removed {member.mention} from the XP slowmode bypass list.")
            else:
                self.bypass_users.add(user_id)
                self.save_config()
                await ctx.send(f"✅ Added {member.mention} to the XP slowmode bypass list! They can now gain XP instantly.")
                
        elif target_type == "userid":
            if not target_id:
                return await ctx.send("❌ Please provide a user ID: `!xpslmby userid 123456789`")
            
            try:
                user_id_int = int(target_id)
                user_id = str(user_id_int)
                
                if user_id in self.bypass_users:
                    self.bypass_users.remove(user_id)
                    self.save_config()
                    await ctx.send(f"✅ Removed User ID `{user_id}` from the XP slowmode bypass list.")
                else:
                    self.bypass_users.add(user_id)
                    self.save_config()
                    await ctx.send(f"✅ Added User ID `{user_id}` to the XP slowmode bypass list!")
            except ValueError:
                return await ctx.send("❌ Invalid User ID. Please provide a valid numeric ID.")
                
        elif target_type == "role":
            if not ctx.message.role_mentions:
                return await ctx.send("❌ Please mention a role: `!xpslmby role @Role`")
            role = ctx.message.role_mentions[0]
            role_id = str(role.id)
            
            if role_id in self.bypass_roles:
                self.bypass_roles.remove(role_id)
                self.save_config()
                await ctx.send(f"✅ Removed {role.mention} from the XP slowmode bypass list.")
            else:
                self.bypass_roles.add(role_id)
                self.save_config()
                await ctx.send(f"✅ Added {role.mention} to the XP slowmode bypass list! All members with this role can now gain XP instantly.")
                
        else:
            await ctx.send("❌ Invalid target type! Use: `user`, `userid`, or `role`.")

    @commands.command(name="xpslmlist")
    @commands.has_permissions(administrator=True)
    async def xp_slowmode_list(self, ctx):
        """
        [Admin] Lists all users and roles that bypass the XP cooldown.
        Usage: !xpslmlist
        """
        embed = discord.Embed(
            title="⚡ XP Slowmode Bypass List",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="⏱️ Current Slowmode", value=f"{self.COOLDOWN_SECONDS} seconds", inline=False)
        
        if self.bypass_users:
            bypass_members = []
            for user_id in self.bypass_users:
                member = ctx.guild.get_member(int(user_id))
                if member:
                    bypass_members.append(member.mention)
                else:
                    bypass_members.append(f"User ID: `{user_id}` (Not in server)")
            embed.add_field(name="👤 Bypass Users", value="\n".join(bypass_members), inline=False)
        else:
            embed.add_field(name="👤 Bypass Users", value="None", inline=False)
            
        if self.bypass_roles:
            bypass_roles = []
            for role_id in self.bypass_roles:
                role = ctx.guild.get_role(int(role_id))
                if role:
                    bypass_roles.append(role.mention)
                else:
                    bypass_roles.append(f"Role ID: `{role_id}` (Deleted)")
            embed.add_field(name="👥 Bypass Roles", value="\n".join(bypass_roles), inline=False)
        else:
            embed.add_field(name="👥 Bypass Roles", value="None", inline=False)
            
        await ctx.send(embed=embed)

    @commands.command(name="setlevelchannel")
    @commands.has_permissions(administrator=True)
    async def set_level_channel(self, ctx, channel: discord.TextChannel):
        """
        [Admin] Sets the channel where Level-Up announcements will be sent.
        Usage: !setlevelchannel #channel
        """
        self.level_channel_id = channel.id
        self.save_config()
        await ctx.send(f"✅ Level-Up announcements will now be sent to {channel.mention}!")

    # ==========================================
    # ADMIN ROLE SETUP COMMANDS
    # ==========================================

    @commands.command(name="autosetuplevelroles")
    @commands.has_permissions(administrator=True)
    async def auto_setup_level_roles(self, ctx):
        """
        [Admin] Automatically creates level roles up to Level 100 with colors & permissions.
        Usage: !autosetuplevelroles
        """
        guild = ctx.guild
        created_roles = []
        existing_roles = []
        
        for level in self.levels:
            role_name = f"Level {level}"
            role = discord.utils.get(guild.roles, name=role_name)
            
            if not role:
                color = self.get_role_color(level)
                perms = self.get_role_permissions(level)
                try:
                    new_role = await guild.create_role(
                        name=role_name,
                        color=color,
                        permissions=perms,
                        reason=f"Auto-setup level {level} role"
                    )
                    created_roles.append(new_role.name)
                except discord.Forbidden:
                    return await ctx.send("❌ I don't have permission to create roles!")
            else:
                try:
                    await role.edit(
                        color=self.get_role_color(level),
                        permissions=self.get_role_permissions(level),
                        reason="Updating role to match level requirements"
                    )
                    existing_roles.append(role.name)
                except discord.Forbidden:
                    await ctx.send(f"⚠️ Could not update {role.name} (missing perms)")
                    existing_roles.append(role.name + " (update failed)")
        
        if str(guild.id) not in self.level_roles:
            self.level_roles[str(guild.id)] = {}
        
        for level in self.levels:
            role = discord.utils.get(guild.roles, name=f"Level {level}")
            if role:
                self.level_roles[str(guild.id)][str(level)] = role.id
        
        self.save_role_data()
        
        embed = discord.Embed(
            title="✅ Level Roles Setup Complete (Stops at 100)",
            color=discord.Color.green()
        )
        embed.add_field(name="Created Roles", value=str(len(created_roles)), inline=True)
        embed.add_field(name="Updated Existing Roles", value=str(len(existing_roles)), inline=True)
        
        if created_roles:
            embed.add_field(name="New Roles", value=", ".join(created_roles), inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="removealllevelroles")
    @commands.has_permissions(administrator=True)
    async def remove_all_level_roles(self, ctx):
        """
        [Admin] Deletes ALL level roles (Level 2, 5, 10... 100).
        Usage: !removealllevelroles
        """
        guild = ctx.guild
        deleted_count = 0
        failed_count = 0
        deleted_roles = []

        level_roles = [role for role in guild.roles if role.name in [f"Level {l}" for l in self.levels]]

        if not level_roles:
            return await ctx.send("❌ No level roles found in this server.")

        await ctx.send(f"🔍 Found **{len(level_roles)}** level roles. Deleting them now...")

        for role in level_roles:
            try:
                await role.delete(reason="Removed all level roles by admin request")
                deleted_count += 1
                deleted_roles.append(role.name)
            except discord.Forbidden:
                failed_count += 1
            except discord.HTTPException:
                failed_count += 1

        if str(guild.id) in self.level_roles:
            del self.level_roles[str(guild.id)]
            self.save_role_data()

        embed = discord.Embed(
            title="🗑️ Level Roles Removed (Up to 100)",
            color=discord.Color.red()
        )
        embed.add_field(name="✅ Successfully Deleted", value=str(deleted_count), inline=True)
        embed.add_field(name="❌ Failed to Delete", value=str(failed_count), inline=True)
        
        if deleted_roles:
            embed.add_field(name="Deleted Roles", value=", ".join(deleted_roles), inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="autodeletelevelroles")
    @commands.has_permissions(administrator=True)
    async def auto_delete_level_roles(self, ctx, target=None, *, user_id=None):
        guild = ctx.guild
        
        if target is None:
            return await ctx.send("❌ Please specify: `user @User` or `userid 123456789`")
        
        target = target.lower()
        
        if target == "user":
            if not ctx.message.mentions:
                return await ctx.send("❌ Please mention a user: `!autodeletelevelroles user @User`")
            member = ctx.message.mentions[0]
            return await self.remove_user_level_roles(ctx, member)
        
        elif target == "userid":
            if not user_id:
                return await ctx.send("❌ Please provide a user ID: `!autodeletelevelroles userid 123456789`")
            try:
                user_id = int(user_id)
                member = guild.get_member(user_id)
                if not member:
                    return await ctx.send("❌ User not found in this server.")
                return await self.remove_user_level_roles(ctx, member)
            except ValueError:
                return await ctx.send("❌ Invalid user ID. Please provide a valid numeric ID.")
        
        else:
            return await ctx.send("❌ Invalid option. Use: `user @User` or `userid 123456789`")

    async def remove_user_level_roles(self, ctx, member):
        guild = ctx.guild
        level_role_names = [f"Level {l}" for l in self.levels]
        level_roles_on_user = [role for role in member.roles if role.name in level_role_names]
        
        if not level_roles_on_user:
            return await ctx.send(f"ℹ️ {member.mention} has no level roles to remove.")
        
        removed_count = 0
        for role in level_roles_on_user:
            try:
                await member.remove_roles(role, reason=f"Auto-delete level roles for user")
                removed_count += 1
            except discord.Forbidden:
                pass
        
        await ctx.send(f"✅ Removed {removed_count} level roles from {member.mention}.")

    @commands.command(name="addlevelrole")
    @commands.has_permissions(administrator=True)
    async def add_level_role(self, ctx, level: int, role: discord.Role):
        if level not in self.levels:
            return await ctx.send(f"❌ Invalid level! Choose from: {', '.join(map(str, self.levels))}")
        
        guild = ctx.guild
        
        if str(guild.id) not in self.level_roles:
            self.level_roles[str(guild.id)] = {}
        
        self.level_roles[str(guild.id)][str(level)] = role.id
        self.save_role_data()
        
        await ctx.send(f"✅ Added Level {level} -> {role.mention}")

    @commands.command(name="removelevelrole")
    @commands.has_permissions(administrator=True)
    async def remove_level_role(self, ctx, level: int):
        guild = ctx.guild
        
        if str(guild.id) not in self.level_roles:
            return await ctx.send("❌ No level roles configured for this server.")
        
        if str(level) in self.level_roles[str(guild.id)]:
            del self.level_roles[str(guild.id)][str(level)]
            self.save_role_data()
            await ctx.send(f"✅ Removed Level {level} mapping.")
        else:
            await ctx.send(f"❌ Level {level} is not configured.")

    @commands.command(name="listlevelroles")
    @commands.has_permissions(administrator=True)
    async def list_level_roles(self, ctx):
        guild = ctx.guild
        
        if str(guild.id) not in self.level_roles or not self.level_roles[str(guild.id)]:
            return await ctx.send("❌ No level roles configured for this server.")
        
        embed = discord.Embed(
            title="📋 Level Roles (Up to 100)",
            color=discord.Color.blue()
        )
        
        for level, role_id in sorted(self.level_roles[str(guild.id)].items(), key=lambda x: int(x[0])):
            role = guild.get_role(role_id)
            if role:
                perms = self.get_role_permissions(int(level))
                perm_list = []
                if perms.attach_files: perm_list.append("📎 Send Images/GIFs/Files")
                if perms.embed_links: perm_list.append("🔗 Embed Links (Inline GIFs)")
                
                embed.add_field(
                    name=f"Level {level}",
                    value=f"{role.mention}\n*{', '.join(perm_list) if perm_list else 'Base Chat Perms'}*",
                    inline=False
                )
        
        await ctx.send(embed=embed)

    @commands.command(name="addxp")
    @commands.has_permissions(administrator=True)
    async def add_xp(self, ctx, member: discord.Member, amount: float):
        """
        [Admin] Manually adds XP to a user. Accepts decimals.
        Usage: !addxp @User 500  or  !addxp @User 0.18
        """
        if amount <= 0:
            return await ctx.send("❌ You must add a positive amount of XP!")

        guild_id = str(ctx.guild.id)
        user_id = str(member.id)

        # SQLite logic
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

        # Get new level after adding XP
        new_level = self.get_level_from_xp(new_xp)

        # Check if they leveled up from the manual XP and assign role if needed
        if new_level in self.levels:
            role_name = f"Level {new_level}"
            role = discord.utils.get(ctx.guild.roles, name=role_name)
            if role:
                try:
                    await member.add_roles(role)
                    await ctx.send(f"🎉 {member.mention} received {amount} XP and **Leveled Up to Level {new_level}**! They have been given the {role.mention} role.")
                except discord.Forbidden:
                    await ctx.send(f"✅ Added {amount} XP to {member.mention}. They reached Level {new_level}, but I couldn't assign the role (missing permissions).")
                return

        await ctx.send(f"✅ Successfully added **{amount} XP** to {member.mention}!\nThey are now at Level {new_level} with {new_xp:,} total XP.")

    @commands.command(name="removexp")
    @commands.has_permissions(administrator=True)
    async def remove_xp(self, ctx, member: discord.Member, amount: float):
        """
        [Admin] Manually removes XP from a user. Accepts decimals.
        Usage: !removexp @User 500
        """
        if amount <= 0:
            return await ctx.send("❌ You must remove a positive amount of XP!")

        guild_id = str(ctx.guild.id)
        user_id = str(member.id)

        # SQLite logic
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("SELECT xp FROM levels WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        result = c.fetchone()

        if not result:
            conn.close()
            return await ctx.send(f"❌ {member.mention} doesn't have any XP to remove!")

        current_xp = result[0]

        # Prevent removing more XP than they have (can't go below 0)
        if current_xp < amount:
            conn.close()
            return await ctx.send(f"❌ {member.mention} only has {current_xp:,} XP. You cannot remove {amount} XP!")

        new_xp = round(current_xp - amount)
        if new_xp < 0:
            new_xp = 0

        c.execute("UPDATE levels SET xp = ? WHERE guild_id = ? AND user_id = ?", (new_xp, guild_id, user_id))
        conn.commit()
        conn.close()

        # Get new level after removing XP
        new_level = self.get_level_from_xp(new_xp)
        
        await ctx.send(f"✅ Successfully removed **{amount} XP** from {member.mention}!\nThey are now at Level {new_level} with {new_xp:,} total XP.")

    # ==========================================
    # XP LISTENER (The Core System - SQLite version)
    # ==========================================

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        guild_id = str(message.guild.id)
        user_id = str(message.author.id)
        
        # 1. Check if user or their role bypasses the cooldown
        is_bypassed = False
        if user_id in self.bypass_users:
            is_bypassed = True
        else:
            for role in message.author.roles:
                if str(role.id) in self.bypass_roles:
                    is_bypassed = True
                    break
        
        # 2. If NOT bypassed, check cooldown
        if not is_bypassed:
            now = asyncio.get_event_loop().time()
            if user_id in self.xp_cooldowns:
                last_time = self.xp_cooldowns[user_id]
                if now - last_time < self.COOLDOWN_SECONDS:
                    return  # Still on cooldown
            
            # Update cooldown for non-bypassed users
            self.xp_cooldowns[user_id] = now
        
        # 3. Initialize user data if not exists (SQLite)
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
        
        # 4. Check for level up (Compare NEW level to OLD level)
        current_xp = new_xp
        new_level = self.get_level_from_xp(current_xp)
        
        # ONLY run if the user actually went up a level
        if new_level > old_level:
            # Check if they crossed a milestone level (2, 5, 10, 20, etc.)
            if new_level in self.levels:
                # Assign the role
                guild = message.guild
                role_name = f"Level {new_level}"
                role = discord.utils.get(guild.roles, name=role_name)
                
                if role:
                    try:
                        # Check if they ALREADY have the role. If they do, skip to avoid spam.
                        if role not in message.author.roles:
                            await message.author.add_roles(role)
                            
                            # Send a level-up message to the SPECIFIC CHANNEL
                            level_channel = guild.get_channel(self.level_channel_id)
                            if level_channel is None:
                                # Fallback to the channel the message was sent in if the set channel is deleted
                                level_channel = message.channel
                            
                            embed = discord.Embed(
                                title=f"🎉 Level Up!",
                                description=f"{message.author.mention} reached **Level {new_level}**!",
                                color=self.get_role_color(new_level)
                            )
                            # Get permissions for display
                            perms = self.get_role_permissions(new_level)
                            perm_list = []
                            if perms.attach_files: perm_list.append("📎 Can send Images/GIFs/Files")
                            if perms.embed_links: perm_list.append("🔗 Can embed Links")
                            
                            if perm_list:
                                embed.add_field(name="Unlocked Perks", value="\n".join(perm_list), inline=False)
                            
                            await level_channel.send(embed=embed)
                    except discord.Forbidden:
                        pass  # Bot doesn't have perms to add roles

# ==========================================
# SETUP FUNCTION
# ==========================================
async def setup(bot):
    await bot.add_cog(LevelBot(bot))
