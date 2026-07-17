import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional

class AFKSystem(commands.Cog):
    """Advanced AFK System - Auto detects AFK users and assigns roles"""
    
    def __init__(self, bot):
        self.bot = bot
        self.afk_settings = {}
        self.afk_users = {}  # user_id -> {timestamp, role_id, reason}
        self.load_data()
        self.monitoring_task = None
        self.start_monitoring()
    
    def load_data(self):
        """Load AFK settings from JSON file"""
        if os.path.exists("afk_data.json"):
            try:
                with open("afk_data.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.afk_settings = data.get("settings", {})
                    self.afk_users = data.get("afk_users", {})
            except:
                self.afk_settings = {}
                self.afk_users = {}
    
    def save_data(self):
        """Save AFK settings to JSON file"""
        data = {
            "settings": self.afk_settings,
            "afk_users": self.afk_users
        }
        with open("afk_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    
    def get_afk_config(self, guild_id: int) -> dict:
        """Get or create AFK config for a guild"""
        guild_id = str(guild_id)
        if guild_id not in self.afk_settings:
            self.afk_settings[guild_id] = {
                "enabled": False,
                "afk_role_id": None,
                "monitor_channel_ids": [],
                "afk_timeout": 300,  # 5 minutes default
                "afk_message": "{user} is currently AFK! 🛑",
                "return_message": "Welcome back {user}! 👋",
                "dm_on_afk": False,
                "dm_afk_message": "You have been marked as AFK in {server}.",
                "dm_on_return": False,
                "dm_return_message": "Welcome back to {server}!",
                "log_channel_id": None,
                "exempt_roles": [],
                "exempt_users": [],
                "afk_auto_message": True,
                "afk_channel_message": "📌 {user} is AFK until {time}",
                "show_afk_reason": True,
                "reason_max_length": 100,
                "notify_when_pinged": True,
                "ping_response": "⚠️ {user} is currently AFK: {reason}",
                "auto_remove_afk_on_activity": True,
                "afk_check_interval": 60,  # Check every 60 seconds
                "afk_timeout_minutes": 5,
                "afk_timeout_enabled": True
            }
            self.save_data()
        return self.afk_settings[guild_id]
    
    def start_monitoring(self):
        """Start the AFK monitoring loop"""
        if self.monitoring_task is None:
            self.monitoring_task = self.bot.loop.create_task(self.monitor_afk_users())
    
    async def monitor_afk_users(self):
        """Monitor users for AFK status changes"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                for guild in self.bot.guilds:
                    guild_id = str(guild.id)
                    
                    if guild_id not in self.afk_settings:
                        continue
                    
                    config = self.afk_settings[guild_id]
                    
                    if not config.get("enabled", False):
                        continue
                    
                    afk_role_id = config.get("afk_role_id")
                    if not afk_role_id:
                        continue
                    
                    afk_role = guild.get_role(afk_role_id)
                    if not afk_role:
                        continue
                    
                    # Check all members with AFK role
                    for member in guild.members:
                        if afk_role in member.roles:
                            # Check if user is actually active (has recent activity)
                            user_id = str(member.id)
                            
                            # Check if user is in a voice channel
                            if member.voice and member.voice.channel:
                                # User is in voice, might not be AFK
                                if not member.voice.is_afk:
                                    # User is active in voice
                                    if config.get("auto_remove_afk_on_activity", True):
                                        await self.remove_afk(member)
                                continue
                            
                            # Check if user has been AFK for too long
                            if user_id in self.afk_users:
                                afk_data = self.afk_users[user_id]
                                afk_time = datetime.fromisoformat(afk_data.get("timestamp", datetime.now().isoformat()))
                                timeout_minutes = config.get("afk_timeout_minutes", 5)
                                
                                if config.get("afk_timeout_enabled", True):
                                    if datetime.now() - afk_time > timedelta(minutes=timeout_minutes):
                                        # User has been AFK for too long, keep them AFK
                                        pass
                
                await asyncio.sleep(config.get("afk_check_interval", 60))
                
            except Exception as e:
                print(f"❌ AFK Monitor Error: {e}")
                await asyncio.sleep(10)
    
    # ============================================
    # SLASH COMMANDS
    # ============================================
    
    @app_commands.command(
        name="afk_setup",
        description="[Admin] Set up the AFK system"
    )
    @app_commands.default_permissions(administrator=True)
    async def afk_setup_slash(self, interaction: discord.Interaction):
        """Interactive setup for the AFK system"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        config = self.get_afk_config(interaction.guild.id)
        
        embed = discord.Embed(
            title="🛑 AFK System Setup",
            description="Welcome to the AFK system setup!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📋 Step 1",
            value="Use `/afk_role @role` to set the AFK role",
            inline=False
        )
        embed.add_field(
            name="📋 Step 2",
            value="Use `/afk_channel #channel` to add a monitored channel",
            inline=False
        )
        embed.add_field(
            name="📋 Step 3",
            value="Use `/afk_timeout 5` to set AFK timeout (minutes)",
            inline=False
        )
        embed.add_field(
            name="📋 Step 4",
            value="Use `/afk_enable true` to turn the system ON",
            inline=False
        )
        embed.add_field(
            name="📋 Optional",
            value="Use `/afk_message` to customize messages",
            inline=False
        )
        embed.set_footer(text="Need help? Use /help")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="afk_enable",
        description="[Admin] Enable or disable the AFK system"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        enabled="True to enable, False to disable"
    )
    async def afk_enable_slash(
        self,
        interaction: discord.Interaction,
        enabled: bool
    ):
        """Enable or disable the AFK system"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return
        
        config = self.get_afk_config(interaction.guild.id)
        config["enabled"] = enabled
        self.save_data()
        
        status = "✅ **Enabled**" if enabled else "❌ **Disabled**"
        
        embed = discord.Embed(
            title="🛑 AFK System Status",
            description=f"AFK system is now {status}",
            color=discord.Color.green() if enabled else discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="afk_role",
        description="[Admin] Set the role to assign to AFK users"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        role="The role to assign to AFK users"
    )
    async def afk_role_slash(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        """Set the role to assign to AFK users"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return
        
        config = self.get_afk_config(interaction.guild.id)
        config["afk_role_id"] = role.id
        self.save_data()
        
        embed = discord.Embed(
            title="✅ AFK Role Set",
            description=f"AFK role set to {role.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Role", value=role.mention, inline=True)
        embed.add_field(name="Role ID", value=f"`{role.id}`", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="afk_channel",
        description="[Admin] Add or remove a monitored channel"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        channel="The channel to monitor",
        add="True to add, False to remove"
    )
    async def afk_channel_slash(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        add: bool = True
    ):
        """Add or remove a monitored channel"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return
        
        config = self.get_afk_config(interaction.guild.id)
        
        if "monitor_channel_ids" not in config:
            config["monitor_channel_ids"] = []
        
        if add:
            if str(channel.id) not in config["monitor_channel_ids"]:
                config["monitor_channel_ids"].append(str(channel.id))
                self.save_data()
                embed = discord.Embed(
                    title="✅ Channel Added",
                    description=f"Now monitoring {channel.mention} for AFK users",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="⚠️ Already Monitored",
                    description=f"{channel.mention} is already being monitored",
                    color=discord.Color.orange()
                )
        else:
            if str(channel.id) in config["monitor_channel_ids"]:
                config["monitor_channel_ids"].remove(str(channel.id))
                self.save_data()
                embed = discord.Embed(
                    title="✅ Channel Removed",
                    description=f"No longer monitoring {channel.mention}",
                    color=discord.Color.orange()
                )
            else:
                embed = discord.Embed(
                    title="⚠️ Not Monitored",
                    description=f"{channel.mention} is not being monitored",
                    color=discord.Color.orange()
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="afk_timeout",
        description="[Admin] Set the AFK timeout in minutes"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        minutes="Minutes of inactivity before marking as AFK (default: 5)"
    )
    async def afk_timeout_slash(
        self,
        interaction: discord.Interaction,
        minutes: int
    ):
        """Set the AFK timeout in minutes"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return
        
        if minutes < 1:
            await interaction.response.send_message("❌ Timeout must be at least 1 minute!", ephemeral=True)
            return
        
        config = self.get_afk_config(interaction.guild.id)
        config["afk_timeout_minutes"] = minutes
        self.save_data()
        
        embed = discord.Embed(
            title="✅ AFK Timeout Set",
            description=f"Users will be marked as AFK after **{minutes}** minutes of inactivity",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="afk_message",
        description="[Admin] Customize AFK messages"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        afk_message="Message shown when user goes AFK",
        return_message="Message shown when user returns",
        ping_response="Message shown when AFK user is pinged"
    )
    async def afk_message_slash(
        self,
        interaction: discord.Interaction,
        afk_message: str = None,
        return_message: str = None,
        ping_response: str = None
    ):
        """Customize AFK messages"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return
        
        config = self.get_afk_config(interaction.guild.id)
        
        if afk_message:
            config["afk_message"] = afk_message
        
        if return_message:
            config["return_message"] = return_message
        
        if ping_response:
            config["ping_response"] = ping_response
        
        self.save_data()
        
        embed = discord.Embed(
            title="✅ AFK Messages Updated",
            description="AFK messages have been customized!",
            color=discord.Color.green()
        )
        
        if afk_message:
            embed.add_field(
                name="📋 AFK Message",
                value=afk_message.replace('{user}', '@User').replace('{server}', interaction.guild.name),
                inline=False
            )
        
        if return_message:
            embed.add_field(
                name="📋 Return Message",
                value=return_message.replace('{user}', '@User').replace('{server}', interaction.guild.name),
                inline=False
            )
        
        if ping_response:
            embed.add_field(
                name="📋 Ping Response",
                value=ping_response.replace('{user}', '@User').replace('{reason}', 'Example reason'),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="afk_logs",
        description="[Admin] Set up a log channel for AFK events"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        channel="The channel to send AFK logs to (leave empty to disable)"
    )
    async def afk_logs_slash(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None
    ):
        """Set up a log channel for AFK events"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return
        
        config = self.get_afk_config(interaction.guild.id)
        
        if channel:
            config["log_channel_id"] = str(channel.id)
            embed = discord.Embed(
                title="✅ AFK Logs Enabled",
                description=f"AFK logs will be sent to {channel.mention}",
                color=discord.Color.green()
            )
        else:
            config["log_channel_id"] = None
            embed = discord.Embed(
                title="✅ AFK Logs Disabled",
                description="AFK logs have been turned off.",
                color=discord.Color.orange()
            )
        
        self.save_data()
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="afk_dm",
        description="[Admin] Set up DM notifications for AFK"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        enabled="True to enable DMs",
        dm_afk_message="DM message when marked AFK",
        dm_return_message="DM message when returning from AFK"
    )
    async def afk_dm_slash(
        self,
        interaction: discord.Interaction,
        enabled: bool,
        dm_afk_message: str = None,
        dm_return_message: str = None
    ):
        """Set up DM notifications for AFK"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return
        
        config = self.get_afk_config(interaction.guild.id)
        config["dm_on_afk"] = enabled
        config["dm_on_return"] = enabled
        
        if dm_afk_message:
            config["dm_afk_message"] = dm_afk_message
        
        if dm_return_message:
            config["dm_return_message"] = dm_return_message
        
        self.save_data()
        
        embed = discord.Embed(
            title="✅ AFK DM Settings Updated",
            description=f"DM notifications are now {'✅ Enabled' if enabled else '❌ Disabled'}",
            color=discord.Color.green() if enabled else discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # ============================================
    # PREFIX COMMANDS
    # ============================================
    
    @commands.command(name="afksetup")
    @commands.has_permissions(administrator=True)
    async def afk_setup(self, ctx):
        """Interactive setup for the AFK system"""
        
        embed = discord.Embed(
            title="🛑 AFK System Setup",
            description="Welcome to the AFK system setup!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📋 Step 1",
            value="Use `!afkrole @role` to set the AFK role",
            inline=False
        )
        embed.add_field(
            name="📋 Step 2",
            value="Use `!afkchannel #channel` to add a monitored channel",
            inline=False
        )
        embed.add_field(
            name="📋 Step 3",
            value="Use `!afktimeout 5` to set AFK timeout (minutes)",
            inline=False
        )
        embed.add_field(
            name="📋 Step 4",
            value="Use `!afkenable true` to turn the system ON",
            inline=False
        )
        embed.add_field(
            name="📋 Step 5",
            value="Use `!afkpreview` to see what users will see",
            inline=False
        )
        embed.set_footer(text="Need help? Use !help")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="afkenable")
    @commands.has_permissions(administrator=True)
    async def afk_enable(self, ctx, status: str = None):
        """Enable or disable the AFK system"""
        
        config = self.get_afk_config(ctx.guild.id)
        
        if status is None:
            config["enabled"] = not config.get("enabled", False)
        else:
            config["enabled"] = status.lower() in ["true", "on", "enable", "yes", "1"]
        
        self.save_data()
        
        status_text = "✅ **Enabled**" if config["enabled"] else "❌ **Disabled**"
        await ctx.send(f"🛑 AFK system is now {status_text}")
    
    @commands.command(name="afkrole")
    @commands.has_permissions(administrator=True)
    async def afk_role(self, ctx, role: discord.Role):
        """Set the role to assign to AFK users"""
        
        config = self.get_afk_config(ctx.guild.id)
        config["afk_role_id"] = role.id
        self.save_data()
        
        await ctx.send(f"✅ AFK role set to {role.mention}")
    
    @commands.command(name="afkchannel")
    @commands.has_permissions(administrator=True)
    async def afk_channel(self, ctx, channel: discord.TextChannel):
        """Add a monitored channel"""
        
        config = self.get_afk_config(ctx.guild.id)
        
        if "monitor_channel_ids" not in config:
            config["monitor_channel_ids"] = []
        
        if str(channel.id) not in config["monitor_channel_ids"]:
            config["monitor_channel_ids"].append(str(channel.id))
            self.save_data()
            await ctx.send(f"✅ Now monitoring {channel.mention} for AFK users")
        else:
            await ctx.send(f"⚠️ {channel.mention} is already being monitored")
    
    @commands.command(name="afkremovechannel")
    @commands.has_permissions(administrator=True)
    async def afk_remove_channel(self, ctx, channel: discord.TextChannel):
        """Remove a monitored channel"""
        
        config = self.get_afk_config(ctx.guild.id)
        
        if "monitor_channel_ids" in config and str(channel.id) in config["monitor_channel_ids"]:
            config["monitor_channel_ids"].remove(str(channel.id))
            self.save_data()
            await ctx.send(f"✅ No longer monitoring {channel.mention}")
        else:
            await ctx.send(f"⚠️ {channel.mention} is not being monitored")
    
    @commands.command(name="afktimeout")
    @commands.has_permissions(administrator=True)
    async def afk_timeout(self, ctx, minutes: int):
        """Set the AFK timeout in minutes"""
        
        if minutes < 1:
            await ctx.send("❌ Timeout must be at least 1 minute!")
            return
        
        config = self.get_afk_config(ctx.guild.id)
        config["afk_timeout_minutes"] = minutes
        self.save_data()
        
        await ctx.send(f"✅ Users will be marked as AFK after **{minutes}** minutes of inactivity")
    
    @commands.command(name="afkmessage")
    @commands.has_permissions(administrator=True)
    async def afk_message(self, ctx, *, message: str):
        """Set the AFK message shown to users"""
        
        config = self.get_afk_config(ctx.guild.id)
        config["afk_message"] = message
        self.save_data()
        
        preview = message.replace('{user}', ctx.author.display_name).replace('{server}', ctx.guild.name)
        await ctx.send(f"✅ AFK message updated!\n\n📋 Preview: {preview}")
    
    @commands.command(name="afkreturnmessage")
    @commands.has_permissions(administrator=True)
    async def afk_return_message(self, ctx, *, message: str):
        """Set the return message shown to users"""
        
        config = self.get_afk_config(ctx.guild.id)
        config["return_message"] = message
        self.save_data()
        
        preview = message.replace('{user}', ctx.author.display_name).replace('{server}', ctx.guild.name)
        await ctx.send(f"✅ Return message updated!\n\n📋 Preview: {preview}")
    
    @commands.command(name="afkpreview")
    @commands.has_permissions(administrator=True)
    async def afk_preview(self, ctx):
        """Preview what AFK users will see"""
        
        config = self.get_afk_config(ctx.guild.id)
        
        if not config.get("enabled", False):
            await ctx.send("⚠️ AFK system is currently **disabled**. Use `!afkenable` to enable it.")
            return
        
        afk_role_id = config.get("afk_role_id")
        if not afk_role_id:
            await ctx.send("❌ No AFK role set! Use `!afkrole @role` to set one.")
            return
        
        afk_role = ctx.guild.get_role(afk_role_id)
        if not afk_role:
            await ctx.send("❌ AFK role not found! Please set a valid role.")
            return
        
        embed = discord.Embed(
            title="🛑 AFK System Preview",
            description="This is what will happen when a user is marked as AFK:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📋 AFK Role",
            value=f"{afk_role.mention} will be assigned",
            inline=False
        )
        embed.add_field(
            name="📋 AFK Message",
            value=config.get("afk_message", "{user} is currently AFK! 🛑").replace('{user}', ctx.author.display_name).replace('{server}', ctx.guild.name),
            inline=False
        )
        embed.add_field(
            name="📋 Return Message",
            value=config.get("return_message", "Welcome back {user}! 👋").replace('{user}', ctx.author.display_name).replace('{server}', ctx.guild.name),
            inline=False
        )
        embed.add_field(
            name="⏱️ Timeout",
            value=f"{config.get('afk_timeout_minutes', 5)} minutes of inactivity",
            inline=False
        )
        
        if config.get("monitor_channel_ids", []):
            channels = []
            for channel_id in config["monitor_channel_ids"]:
                channel = ctx.guild.get_channel(int(channel_id))
                if channel:
                    channels.append(channel.mention)
            if channels:
                embed.add_field(
                    name="📋 Monitored Channels",
                    value=", ".join(channels),
                    inline=False
                )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="afkremove")
    @commands.has_permissions(administrator=True)
    async def afk_remove(self, ctx):
        """Remove all AFK settings for this server"""
        
        guild_id = str(ctx.guild.id)
        
        if guild_id in self.afk_settings:
            del self.afk_settings[guild_id]
            self.save_data()
            await ctx.send("🗑️ All AFK settings have been removed for this server.")
        else:
            await ctx.send("❌ No AFK settings found for this server.")
    
    # ============================================
    # AFK MANUAL COMMANDS FOR USERS
    # ============================================
    
    @commands.command(name="afk")
    async def afk_manual(self, ctx, *, reason: str = None):
        """Manually set yourself as AFK"""
        
        config = self.get_afk_config(ctx.guild.id)
        
        if not config.get("enabled", False):
            await ctx.send("⚠️ AFK system is not enabled in this server.")
            return
        
        afk_role_id = config.get("afk_role_id")
        if not afk_role_id:
            await ctx.send("❌ AFK role not set up. Please contact an admin.")
            return
        
        afk_role = ctx.guild.get_role(afk_role_id)
        if not afk_role:
            await ctx.send("❌ AFK role not found. Please contact an admin.")
            return
        
        if afk_role in ctx.author.roles:
            await ctx.send("✅ You are already AFK!")
            return
        
        await ctx.author.add_roles(afk_role, reason="Manual AFK")
        
        user_id = str(ctx.author.id)
        self.afk_users[user_id] = {
            "timestamp": datetime.now().isoformat(),
            "role_id": afk_role_id,
            "reason": reason or "No reason provided"
        }
        self.save_data()
        
        # Send AFK message
        afk_message = config.get("afk_message", "{user} is currently AFK! 🛑")
        afk_message = afk_message.replace('{user}', ctx.author.display_name).replace('{server}', ctx.guild.name)
        if reason:
            afk_message += f"\n📝 Reason: {reason}"
        
        await ctx.send(afk_message)
        
        # Send DM if enabled
        if config.get("dm_on_afk", False):
            try:
                dm_message = config.get("dm_afk_message", "You have been marked as AFK in {server}.")
                dm_message = dm_message.replace('{user}', ctx.author.display_name).replace('{server}', ctx.guild.name)
                await ctx.author.send(dm_message)
            except:
                pass
    
    @commands.command(name="unafk")
    async def unafk_manual(self, ctx):
        """Manually remove your AFK status"""
        await self.remove_afk(ctx.author)
        await ctx.send("✅ You are no longer AFK! Welcome back!")
    
    # ============================================
    # CORE AFK FUNCTIONS
    # ============================================
    
    async def mark_afk(self, member: discord.Member, reason: str = None):
        """Mark a user as AFK"""
        
        guild = member.guild
        guild_id = str(guild.id)
        
        if guild_id not in self.afk_settings:
            return
        
        config = self.afk_settings[guild_id]
        
        if not config.get("enabled", False):
            return
        
        afk_role_id = config.get("afk_role_id")
        if not afk_role_id:
            return
        
        afk_role = guild.get_role(afk_role_id)
        if not afk_role:
            return
        
        # Check if user is exempt
        exempt_roles = config.get("exempt_roles", [])
        for role_id in exempt_roles:
            role = guild.get_role(role_id)
            if role and role in member.roles:
                return
        
        if str(member.id) in config.get("exempt_users", []):
            return
        
        # Check if already AFK
        if afk_role in member.roles:
            return
        
        # Add AFK role
        try:
            await member.add_roles(afk_role, reason="Auto-AFK detection")
        except:
            return
        
        # Store AFK data
        user_id = str(member.id)
        self.afk_users[user_id] = {
            "timestamp": datetime.now().isoformat(),
            "role_id": afk_role_id,
            "reason": reason or "No reason provided"
        }
        self.save_data()
        
        # Send AFK message in channel
        afk_message = config.get("afk_message", "{user} is currently AFK! 🛑")
        afk_message = afk_message.replace('{user}', member.display_name).replace('{server}', guild.name)
        
        # Find a channel to send the message
        monitor_channels = config.get("monitor_channel_ids", [])
        for channel_id in monitor_channels:
            channel = guild.get_channel(int(channel_id))
            if channel:
                await channel.send(afk_message)
                break
        
        # Send DM if enabled
        if config.get("dm_on_afk", False):
            try:
                dm_message = config.get("dm_afk_message", "You have been marked as AFK in {server}.")
                dm_message = dm_message.replace('{user}', member.display_name).replace('{server}', guild.name)
                await member.send(dm_message)
            except:
                pass
        
        # Log AFK event
        await self.log_afk_event(guild, f"🛑 {member.mention} has been marked as AFK", discord.Color.orange())
    
    async def remove_afk(self, member: discord.Member):
        """Remove AFK status from a user"""
        
        guild = member.guild
        guild_id = str(guild.id)
        
        if guild_id not in self.afk_settings:
            return
        
        config = self.afk_settings[guild_id]
        
        if not config.get("enabled", False):
            return
        
        afk_role_id = config.get("afk_role_id")
        if not afk_role_id:
            return
        
        afk_role = guild.get_role(afk_role_id)
        if not afk_role:
            return
        
        # Check if user has AFK role
        if afk_role not in member.roles:
            # User might not have AFK role, but check if they're in the AFK list
            user_id = str(member.id)
            if user_id in self.afk_users:
                del self.afk_users[user_id]
                self.save_data()
            return
        
        # Remove AFK role
        try:
            await member.remove_roles(afk_role, reason="Returned from AFK")
        except:
            return
        
        # Remove from AFK list
        user_id = str(member.id)
        if user_id in self.afk_users:
            del self.afk_users[user_id]
            self.save_data()
        
        # Send return message
        return_message = config.get("return_message", "Welcome back {user}! 👋")
        return_message = return_message.replace('{user}', member.display_name).replace('{server}', guild.name)
        
        # Find a channel to send the message
        monitor_channels = config.get("monitor_channel_ids", [])
        for channel_id in monitor_channels:
            channel = guild.get_channel(int(channel_id))
            if channel:
                await channel.send(return_message)
                break
        
        # Send DM if enabled
        if config.get("dm_on_return", False):
            try:
                dm_message = config.get("dm_return_message", "Welcome back to {server}!")
                dm_message = dm_message.replace('{user}', member.display_name).replace('{server}', guild.name)
                await member.send(dm_message)
            except:
                pass
        
        # Log return event
        await self.log_afk_event(guild, f"✅ {member.mention} has returned from AFK", discord.Color.green())
    
    async def log_afk_event(self, guild: discord.Guild, message: str, color: discord.Color):
        """Log AFK events to the log channel"""
        
        guild_id = str(guild.id)
        
        if guild_id not in self.afk_settings:
            return
        
        config = self.afk_settings[guild_id]
        log_channel_id = config.get("log_channel_id")
        
        if not log_channel_id:
            return
        
        log_channel = guild.get_channel(int(log_channel_id))
        if not log_channel:
            return
        
        embed = discord.Embed(
            description=message,
            color=color,
            timestamp=datetime.utcnow()
        )
        
        await log_channel.send(embed=embed)
    
    # ============================================
    # EVENT HANDLERS
    # ============================================
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Detect user activity and remove AFK status"""
        
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        guild = message.guild
        guild_id = str(guild.id)
        
        if guild_id not in self.afk_settings:
            return
        
        config = self.afk_settings[guild_id]
        
        if not config.get("enabled", False):
            return
        
        # Check if message is in a monitored channel
        monitor_channels = config.get("monitor_channel_ids", [])
        if str(message.channel.id) not in monitor_channels:
            return
        
        # Check if user has AFK role
        afk_role_id = config.get("afk_role_id")
        if not afk_role_id:
            return
        
        afk_role = guild.get_role(afk_role_id)
        if not afk_role:
            return
        
        if afk_role in message.author.roles:
            # Check if user is exempt (voice activity)
            if message.author.voice and message.author.voice.channel:
                if not message.author.voice.is_afk:
                    # User is active in voice, remove AFK
                    if config.get("auto_remove_afk_on_activity", True):
                        await self.remove_afk(message.author)
                return
            
            # User sent a message, remove AFK
            if config.get("auto_remove_afk_on_activity", True):
                await self.remove_afk(message.author)
        
        # Check if someone pinged an AFK user
        if message.mentions:
            for mentioned in message.mentions:
                if afk_role in mentioned.roles:
                    user_id = str(mentioned.id)
                    if user_id in self.afk_users:
                        afk_data = self.afk_users[user_id]
                        reason = afk_data.get("reason", "No reason provided")
                        
                        if config.get("notify_when_pinged", True):
                            ping_response = config.get("ping_response", "⚠️ {user} is currently AFK: {reason}")
                            ping_response = ping_response.replace('{user}', mentioned.display_name).replace('{reason}', reason)
                            await message.channel.send(f"{message.author.mention} {ping_response}")
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before, after):
        """Detect voice state changes"""
        
        if not member.guild:
            return
        
        guild = member.guild
        guild_id = str(guild.id)
        
        if guild_id not in self.afk_settings:
            return
        
        config = self.afk_settings[guild_id]
        
        if not config.get("enabled", False):
            return
        
        afk_role_id = config.get("afk_role_id")
        if not afk_role_id:
            return
        
        afk_role = guild.get_role(afk_role_id)
        if not afk_role:
            return
        
        # Check if user moved from voice to AFK
        if before.channel and not after.channel:
            # User left voice, check if they should be AFK
            if afk_role not in member.roles:
                await self.mark_afk(member, "Left voice channel")
        
        # Check if user moved to a voice channel
        if after.channel and not before.channel:
            # User joined voice, remove AFK
            if afk_role in member.roles:
                if config.get("auto_remove_afk_on_activity", True):
                    await self.remove_afk(member)
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Detect when a user's status changes"""
        
        if not before.guild:
            return
        
        guild = before.guild
        guild_id = str(guild.id)
        
        if guild_id not in self.afk_settings:
            return
        
        config = self.afk_settings[guild_id]
        
        if not config.get("enabled", False):
            return
        
        afk_role_id = config.get("afk_role_id")
        if not afk_role_id:
            return
        
        afk_role = guild.get_role(afk_role_id)
        if not afk_role:
            return
        
        # Check if status changed from offline to online/active
        if before.status == discord.Status.offline and after.status != discord.Status.offline:
            if afk_role in after.roles:
                if config.get("auto_remove_afk_on_activity", True):
                    await self.remove_afk(after)
        
        # Check if status changed from any to offline
        if before.status != discord.Status.offline and after.status == discord.Status.offline:
            timeout_minutes = config.get("afk_timeout_minutes", 5)
            if config.get("afk_timeout_enabled", True):
                # Wait for timeout before marking as AFK
                await asyncio.sleep(timeout_minutes * 60)
                
                # Check if user is still offline
                member = guild.get_member(after.id)
                if member and member.status == discord.Status.offline:
                    if afk_role not in member.roles:
                        await self.mark_afk(member, "Offline for too long")
    
    # ============================================
    # ERROR HANDLERS
    # ============================================
    
    @afk_setup.error
    @afk_enable.error
    @afk_role.error
    @afk_channel.error
    @afk_timeout.error
    @afk_message.error
    @afk_return_message.error
    @afk_preview.error
    @afk_remove.error
    async def afk_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need Administrator permissions to use this command!")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument. Please check the command usage.")
        else:
            await ctx.send(f"❌ An error occurred: {str(error)}")
    
    @commands.command(name="afklist")
    @commands.has_permissions(kick_members=True)
    async def afk_list(self, ctx):
        """List all users currently AFK"""
        
        config = self.get_afk_config(ctx.guild.id)
        afk_role_id = config.get("afk_role_id")
        
        if not afk_role_id:
            await ctx.send("❌ No AFK role set up.")
            return
        
        afk_role = ctx.guild.get_role(afk_role_id)
        if not afk_role:
            await ctx.send("❌ AFK role not found.")
            return
        
        afk_members = [m for m in ctx.guild.members if afk_role in m.roles]
        
        if not afk_members:
            await ctx.send("✅ No users are currently AFK.")
            return
        
        embed = discord.Embed(
            title="🛑 AFK Users",
            color=discord.Color.orange()
        )
        
        for member in afk_members[:25]:
            user_id = str(member.id)
            if user_id in self.afk_users:
                reason = self.afk_users[user_id].get("reason", "No reason")
                embed.add_field(
                    name=member.display_name,
                    value=f"📝 {reason[:50]}",
                    inline=False
                )
            else:
                embed.add_field(
                    name=member.display_name,
                    value="No reason provided",
                    inline=False
                )
        
        if len(afk_members) > 25:
            embed.set_footer(text=f"And {len(afk_members) - 25} more...")
        
        await ctx.send(embed=embed)

# ============================================
# SETUP
# ============================================

async def setup(bot):
    await bot.add_cog(AFKSystem(bot))