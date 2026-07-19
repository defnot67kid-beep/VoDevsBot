import discord
from discord.ext import commands
import json
import os
import asyncio
import math
import random

class LevelBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "level_data.json"
        self.role_data_file = "level_roles.json"
        self.level_data = self.load_data()
        self.level_roles = self.load_role_data()
        
        # Cooldown dictionary to prevent spam (user_id -> last_message_time)
        self.xp_cooldowns = {}
        self.COOLDOWN_SECONDS = 60  # Can only earn XP once per minute
        
        # Define the level progression (STOPS AT 100)
        self.levels = [2, 5, 10, 20, 35, 50, 60, 70, 100]

    def load_data(self):
        """Load level XP data from JSON file"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {}

    def save_data(self):
        """Save level XP data to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.level_data, f, indent=4)

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
    # XP CALCULATION (Hard to get XP)
    # ==========================================
    
    def calculate_xp_gain(self, message):
        """Calculate XP based on message length, with a hard cap"""
        content = message.content
        length = len(content)
        
        # Base XP for just sending a message (low)
        base_xp = random.randint(10, 15)
        
        # Length bonus: 1 extra XP for every 10 characters, but capped at 30 extra XP
        length_bonus = min(length // 10, 30)
        
        # Total XP gained (Hard to get: max ~45 XP per minute)
        total_xp = base_xp + length_bonus
        
        return total_xp

    def get_xp_needed(self, level):
        """Calculate XP needed to reach the next level (Exponential scaling)"""
        # Level 1 needs 100 XP. Level 100 needs 100,000 XP.
        # Formula: 100 * (level ^ 1.5)
        return int(100 * (level ** 1.5))

    def get_level_from_xp(self, xp):
        """Calculate what level a user is based on total XP"""
        level = 1
        while self.get_xp_needed(level) <= xp:
            level += 1
        return level - 1

    # ==========================================
    # COMMANDS
    # ==========================================

    @commands.command(name="rank")
    async def rank(self, ctx, member: discord.Member = None):
        """Check your current level and XP progress"""
        if member is None:
            member = ctx.author
            
        user_id = str(member.id)
        guild_id = str(ctx.guild.id)
        
        # Check if user has data
        if guild_id not in self.level_data or user_id not in self.level_data[guild_id]:
            return await ctx.send(f"❌ {member.mention} hasn't chatted enough to have a rank yet!")
        
        user_data = self.level_data[guild_id][user_id]
        current_xp = user_data["xp"]
        current_level = self.get_level_from_xp(current_xp)
        
        # Calculate progress to next level
        next_level_xp = self.get_xp_needed(current_level + 1)
        prev_level_xp = self.get_xp_needed(current_level)
        xp_in_level = current_xp - prev_level_xp
        xp_needed_for_next = next_level_xp - prev_level_xp
        
        # Progress bar (10 blocks)
        progress = (xp_in_level / xp_needed_for_next) * 10
        bar = "█" * int(progress) + "░" * (10 - int(progress))
        
        embed = discord.Embed(
            title=f"🏆 {member.display_name}'s Rank",
            color=self.get_role_color(current_level) if current_level in self.levels else discord.Color.blue()
        )
        embed.add_field(name="Level", value=f"**{current_level}**", inline=True)
        embed.add_field(name="Total XP", value=f"{current_xp:,}", inline=True)
        embed.add_field(name="Progress", value=f"`[{bar}]` {xp_in_level}/{xp_needed_for_next:,} XP", inline=False)
        
        # Get current highest level role they have
        role_names = [f"Level {l}" for l in self.levels]
        user_roles = [role.name for role in member.roles]
        highest_role = None
        for role_name in reversed(role_names):
            if role_name in user_roles:
                highest_role = role_name
                break
        
        if highest_role:
            embed.add_field(name="Current Rank Role", value=highest_role, inline=False)
        
        embed.set_footer(text=f"Next level at {next_level_xp:,} XP")
        
        await ctx.send(embed=embed)

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):
        """Show the top 10 levelers in the server"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.level_data or not self.level_data[guild_id]:
            return await ctx.send("❌ No level data for this server yet!")
        
        # Sort users by XP
        sorted_users = sorted(self.level_data[guild_id].items(), key=lambda x: x[1]["xp"], reverse=True)[:10]
        
        embed = discord.Embed(
            title="🏆 Server Leaderboard",
            color=discord.Color.gold()
        )
        
        for i, (user_id, data) in enumerate(sorted_users, 1):
            member = ctx.guild.get_member(int(user_id))
            if member:
                level = self.get_level_from_xp(data["xp"])
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
                embed.add_field(
                    name=f"{medal} {member.display_name}",
                    value=f"Level {level} • {data['xp']:,} XP",
                    inline=False
                )
        
        await ctx.send(embed=embed)

    # ==========================================
    # ADMIN SETUP COMMANDS
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

    # ==========================================
    # XP LISTENER (The Core System)
    # ==========================================

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        guild_id = str(message.guild.id)
        user_id = str(message.author.id)
        
        # 1. Check cooldown (1 minute)
        now = asyncio.get_event_loop().time()
        if user_id in self.xp_cooldowns:
            last_time = self.xp_cooldowns[user_id]
            if now - last_time < self.COOLDOWN_SECONDS:
                return  # Still on cooldown
        
        # 2. Update cooldown
        self.xp_cooldowns[user_id] = now
        
        # 3. Initialize user data if not exists
        if guild_id not in self.level_data:
            self.level_data[guild_id] = {}
        if user_id not in self.level_data[guild_id]:
            self.level_data[guild_id][user_id] = {"xp": 0}
        
        # 4. Calculate XP gained
        xp_gained = self.calculate_xp_gain(message)
        self.level_data[guild_id][user_id]["xp"] += xp_gained
        
        # 5. Save data
        self.save_data()
        
        # 6. Check for level up
        current_xp = self.level_data[guild_id][user_id]["xp"]
        new_level = self.get_level_from_xp(current_xp)
        
        # Check if they crossed a milestone level (2, 5, 10, 20, etc.)
        if new_level in self.levels:
            # Assign the role
            guild = message.guild
            role_name = f"Level {new_level}"
            role = discord.utils.get(guild.roles, name=role_name)
            
            if role:
                try:
                    await message.author.add_roles(role)
                    # Send a level-up message
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
                    
                    await message.channel.send(embed=embed)
                except discord.Forbidden:
                    pass  # Bot doesn't have perms to add roles

# ==========================================
# SETUP FUNCTION (FIXED)
# ==========================================
async def setup(bot):
    await bot.add_cog(LevelBot(bot))
