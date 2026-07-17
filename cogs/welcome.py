import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
import re
from datetime import datetime
from typing import Optional, List

class WelcomeSystem(commands.Cog):
    """Advanced Welcome System with auto-role, custom messages, and more"""
    
    def __init__(self, bot):
        self.bot = bot
        self.welcome_settings = {}
        self.welcome_messages = {}
        self.load_data()
    
    def load_data(self):
        """Load welcome settings from JSON file"""
        if os.path.exists("welcome_data.json"):
            try:
                with open("welcome_data.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.welcome_settings = data.get("settings", {})
                    self.welcome_messages = data.get("messages", {})
            except:
                self.welcome_settings = {}
                self.welcome_messages = {}
    
    def save_data(self):
        """Save welcome settings to JSON file"""
        data = {
            "settings": self.welcome_settings,
            "messages": self.welcome_messages
        }
        with open("welcome_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    
    def get_welcome_config(self, guild_id: int) -> dict:
        """Get or create welcome config for a guild"""
        guild_id = str(guild_id)
        if guild_id not in self.welcome_settings:
            self.welcome_settings[guild_id] = {
                "enabled": False,
                "channel_id": None,
                "message_type": "embed",
                "message_text": "🎉 Welcome {user_mention} to **{server_name}**! We're glad to have you here!",
                "embed_title": "🎉 Welcome {user_name}!",
                "embed_description": "Welcome to **{server_name}**! We're thrilled to have you join our community.",
                "embed_color": "#00FF00",
                "embed_footer": "We hope you enjoy your stay!",
                "auto_delete": 0,
                "dm_welcome": False,
                "dm_message": "Welcome to **{server_name}**! Thank you for joining us! 🎉",
                "auto_roles": [],
                "mention_role": None,
                "welcome_channel_name": "welcome",
                "welcome_category_name": "Welcome",
                "welcome_logs": False,
                "log_channel_id": None,
                "goodbye_enabled": False,
                "goodbye_channel_id": None,
                "goodbye_message": "😢 {user_name} has left the server. We'll miss you!",
                "goodbye_embed_color": "#FF0000",
                "goodbye_auto_delete": 0,
                "member_count_channel": None,
                "welcome_dm_enabled": False,
                "welcome_dm_message": "🎉 Welcome to {server_name}!\nWe're happy to have you!",
                "goodbye_dm_enabled": False,
                "goodbye_dm_message": "😢 We're sad to see you leave {server_name}. Take care!",
                "welcome_image_url": None,
                "use_custom_image": False,
                "custom_image_path": None,
                "welcome_thumbnail": None,
                "welcome_footer_icon": None,
                "welcome_timestamp": True,
                "show_member_count": True,
                "show_join_position": True
            }
            self.save_data()
        return self.welcome_settings[guild_id]
    
    # ============================================
    # HELPER FUNCTIONS FOR ROLE PARSING
    # ============================================
    
    def parse_roles(self, guild: discord.Guild, role_input: str) -> List[discord.Role]:
        """Parse role input and return a list of role objects"""
        roles = []
        role_input = role_input.strip()
        
        # If input is empty or "none" or "clear", return empty list
        if not role_input or role_input.lower() in ["none", "clear", "remove"]:
            return []
        
        # Split by spaces, commas, or semicolons
        # Handle multiple separators
        for sep in [';', ',', ' ']:
            if sep in role_input:
                parts = role_input.split(sep)
                break
        else:
            parts = [role_input]
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            role = None
            
            # Try role mention
            if part.startswith('<@&') and part.endswith('>'):
                try:
                    role_id = int(part.replace('<@&', '').replace('>', ''))
                    role = guild.get_role(role_id)
                except:
                    pass
            
            # Try role ID
            if not role and part.isdigit():
                role = guild.get_role(int(part))
            
            # Try exact role name
            if not role:
                for r in guild.roles:
                    if r.name.lower() == part.lower():
                        role = r
                        break
            
            # Try partial role name match
            if not role:
                for r in guild.roles:
                    if part.lower() in r.name.lower():
                        role = r
                        break
            
            if role:
                roles.append(role)
        
        return roles
    
    # ============================================
    # SLASH COMMANDS
    # ============================================
    
    @app_commands.command(
        name="welcome_setup",
        description="[Admin] Set up the welcome system"
    )
    @app_commands.default_permissions(administrator=True)
    async def welcome_setup_slash(self, interaction: discord.Interaction):
        """Interactive setup for the welcome system"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        config = self.get_welcome_config(interaction.guild.id)
        
        embed = discord.Embed(
            title="🎉 Welcome System Setup",
            description="Welcome to the interactive welcome system setup!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📋 Step 1",
            value="Use `/welcome_channel #channel` to set the welcome channel",
            inline=False
        )
        embed.add_field(
            name="📋 Step 2",
            value="Use `/welcome_message` to set the welcome message",
            inline=False
        )
        embed.add_field(
            name="📋 Step 3",
            value="Use `/welcome_roles @role1 @role2` to set auto-roles\n**Example:** `/welcome_roles Member` or `/welcome_roles @Member`",
            inline=False
        )
        embed.add_field(
            name="📋 Step 4",
            value="Use `/welcome_enable` to turn the system ON",
            inline=False
        )
        embed.add_field(
            name="📋 Optional",
            value="Use `/welcome_preview` to see what new members will see",
            inline=False
        )
        embed.set_footer(text="Need help? Use /help")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="welcome_enable",
        description="[Admin] Enable or disable the welcome system"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        enabled="True to enable, False to disable"
    )
    async def welcome_enable_slash(
        self,
        interaction: discord.Interaction,
        enabled: bool
    ):
        """Enable or disable the welcome system"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return
        
        config = self.get_welcome_config(interaction.guild.id)
        config["enabled"] = enabled
        self.save_data()
        
        status = "✅ **Enabled**" if enabled else "❌ **Disabled**"
        
        embed = discord.Embed(
            title="🎉 Welcome System Status",
            description=f"Welcome system is now {status}",
            color=discord.Color.green() if enabled else discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="welcome_channel",
        description="[Admin] Set the welcome channel"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        channel="The channel where welcome messages will be sent"
    )
    async def welcome_channel_slash(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        """Set the welcome channel"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return
        
        config = self.get_welcome_config(interaction.guild.id)
        config["channel_id"] = str(channel.id)
        self.save_data()
        
        embed = discord.Embed(
            title="✅ Welcome Channel Set",
            description=f"Welcome messages will be sent to {channel.mention}",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="welcome_message",
        description="[Admin] Set the welcome message"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        message_type="'embed' or 'text'",
        title="Title for the embed (embed only)",
        description="Description/content of the welcome message",
        color="Hex color for embed (e.g. #00FF00)",
        footer="Footer text (embed only)"
    )
    async def welcome_message_slash(
        self,
        interaction: discord.Interaction,
        message_type: str = "embed",
        title: str = None,
        description: str = None,
        color: str = "#00FF00",
        footer: str = None
    ):
        """Set the welcome message format"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return
        
        config = self.get_welcome_config(interaction.guild.id)
        
        if message_type.lower() not in ["embed", "text"]:
            await interaction.response.send_message("❌ message_type must be 'embed' or 'text'", ephemeral=True)
            return
        
        config["message_type"] = message_type.lower()
        
        if description:
            if message_type.lower() == "embed":
                config["embed_description"] = description
            else:
                config["message_text"] = description
        
        if title and message_type.lower() == "embed":
            config["embed_title"] = title
        
        if color and message_type.lower() == "embed":
            # Validate color
            try:
                if color.startswith("#"):
                    int(color.replace("#", ""), 16)
                config["embed_color"] = color
            except:
                pass
        
        if footer and message_type.lower() == "embed":
            config["embed_footer"] = footer
        
        self.save_data()
        
        embed = discord.Embed(
            title="✅ Welcome Message Updated",
            description="Welcome message has been updated!",
            color=discord.Color.green()
        )
        
        # Show preview
        preview_title = (config.get("embed_title", "Welcome!") if message_type.lower() == "embed" else "Text Message")
        preview_content = config.get("embed_description" if message_type.lower() == "embed" else "message_text", "Welcome to the server!")
        
        embed.add_field(
            name="📋 Preview",
            value=f"**Type:** {message_type}\n\n" + preview_content[:500],
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="welcome_roles",
        description="[Admin] Set auto-roles for new members"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        roles="Roles to give to new members (name, mention, or ID) - use 'none' to clear"
    )
    async def welcome_roles_slash(
        self,
        interaction: discord.Interaction,
        roles: str
    ):
        """Set roles to automatically assign to new members"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return
        
        config = self.get_welcome_config(interaction.guild.id)
        
        # Parse roles using the helper function
        role_list = self.parse_roles(interaction.guild, roles)
        
        # Store role IDs
        role_ids = [role.id for role in role_list]
        config["auto_roles"] = role_ids
        self.save_data()
        
        if role_ids:
            role_mentions = [f"<@&{role_id}>" for role_id in role_ids]
            embed = discord.Embed(
                title="✅ Auto-Roles Set",
                description=f"New members will receive: {', '.join(role_mentions)}",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="✅ Auto-Roles Cleared",
                description="No roles will be auto-assigned to new members.",
                color=discord.Color.orange()
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="welcome_auto_assign_member_role",
        description="[Admin] Automatically find and assign the @Member role to new members"
    )
    @app_commands.default_permissions(administrator=True)
    async def welcome_auto_assign_member_role_slash(
        self,
        interaction: discord.Interaction
    ):
        """Automatically find the @Member role and assign it to new members"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return
        
        config = self.get_welcome_config(interaction.guild.id)
        
        # Look for a role named "Member"
        member_role = None
        for role in interaction.guild.roles:
            if role.name.lower() == "member":
                member_role = role
                break
        
        if not member_role:
            await interaction.response.send_message(
                "❌ Could not find a role named 'Member' in this server. Please create one first or use `/welcome_roles` to specify a role.",
                ephemeral=True
            )
            return
        
        # Set the auto-role
        config["auto_roles"] = [member_role.id]
        self.save_data()
        
        embed = discord.Embed(
            title="✅ Auto-Role Set",
            description=f"New members will now automatically receive the **{member_role.name}** role!",
            color=discord.Color.green()
        )
        embed.add_field(name="Role", value=member_role.mention, inline=True)
        embed.add_field(name="Role ID", value=f"`{member_role.id}`", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="welcome_preview",
        description="[Admin] Preview the welcome message"
    )
    @app_commands.default_permissions(administrator=True)
    async def welcome_preview_slash(self, interaction: discord.Interaction):
        """Preview what new members will see"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return
        
        config = self.get_welcome_config(interaction.guild.id)
        
        if not config.get("enabled", False):
            await interaction.response.send_message("⚠️ Welcome system is currently **disabled**. Use `/welcome_enable` to enable it.", ephemeral=True)
            return
        
        # Build the welcome message
        embed, content, file = await self.build_welcome_message(interaction.user, preview=True)
        
        if content:
            await interaction.response.send_message(content=content, embed=embed, file=file, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, file=file, ephemeral=True)
    
    @app_commands.command(
        name="welcome_dm",
        description="[Admin] Set up DM welcome messages"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        enabled="True to send DMs to new members",
        message="The DM message to send"
    )
    async def welcome_dm_slash(
        self,
        interaction: discord.Interaction,
        enabled: bool,
        message: str = None
    ):
        """Set up DM welcome messages for new members"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return
        
        config = self.get_welcome_config(interaction.guild.id)
        config["welcome_dm_enabled"] = enabled
        
        if message:
            config["welcome_dm_message"] = message
        
        self.save_data()
        
        embed = discord.Embed(
            title="✅ DM Welcome Settings Updated",
            description=f"DM welcome is now {'✅ Enabled' if enabled else '❌ Disabled'}",
            color=discord.Color.green() if enabled else discord.Color.orange()
        )
        
        if enabled and message:
            embed.add_field(
                name="📋 Preview",
                value=message.replace('{user_name}', interaction.user.display_name).replace('{server_name}', interaction.guild.name),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="welcome_logs",
        description="[Admin] Set up a log channel for welcome events"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        channel="The channel to send welcome logs to (leave empty to disable)"
    )
    async def welcome_logs_slash(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None
    ):
        """Set up a log channel for welcome events"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return
        
        config = self.get_welcome_config(interaction.guild.id)
        
        if channel:
            config["welcome_logs"] = True
            config["log_channel_id"] = str(channel.id)
            embed = discord.Embed(
                title="✅ Welcome Logs Enabled",
                description=f"Welcome logs will be sent to {channel.mention}",
                color=discord.Color.green()
            )
        else:
            config["welcome_logs"] = False
            config["log_channel_id"] = None
            embed = discord.Embed(
                title="✅ Welcome Logs Disabled",
                description="Welcome logs have been turned off.",
                color=discord.Color.orange()
            )
        
        self.save_data()
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="welcome_image",
        description="[Admin] Set a custom welcome image"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        image_url="URL of the image to use (leave empty to disable)"
    )
    async def welcome_image_slash(
        self,
        interaction: discord.Interaction,
        image_url: str = None
    ):
        """Set a custom image for welcome messages"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return
        
        config = self.get_welcome_config(interaction.guild.id)
        
        if image_url:
            config["use_custom_image"] = True
            config["welcome_image_url"] = image_url
            embed = discord.Embed(
                title="✅ Custom Image Set",
                description="A custom image will be displayed in welcome messages.",
                color=discord.Color.green()
            )
            embed.set_image(url=image_url)
        else:
            config["use_custom_image"] = False
            config["welcome_image_url"] = None
            embed = discord.Embed(
                title="✅ Custom Image Removed",
                description="Default welcome image will be used.",
                color=discord.Color.orange()
            )
        
        self.save_data()
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # ============================================
    # PREFIX COMMANDS
    # ============================================
    
    @commands.command(name="wsetup")
    @commands.has_permissions(administrator=True)
    async def wsetup(self, ctx):
        """Interactive setup for the welcome system"""
        
        embed = discord.Embed(
            title="🎉 Welcome System Setup",
            description="Welcome to the interactive welcome system setup!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📋 Step 1",
            value="Use `!wchannel #channel` to set the welcome channel",
            inline=False
        )
        embed.add_field(
            name="📋 Step 2",
            value="Use `!wmessage` to set the welcome message",
            inline=False
        )
        embed.add_field(
            name="📋 Step 3",
            value="Use `!wroles @role1 @role2` to set auto-roles\n**Example:** `!wroles Member` or `!wroles @Member`",
            inline=False
        )
        embed.add_field(
            name="📋 Step 4",
            value="Use `!wenable` to turn the system ON",
            inline=False
        )
        embed.add_field(
            name="📋 Step 5",
            value="Use `!wpreview` to see what new members will see",
            inline=False
        )
        embed.set_footer(text="Need help? Use !help")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="wenable")
    @commands.has_permissions(administrator=True)
    async def wenable(self, ctx, status: str = None):
        """Enable or disable the welcome system"""
        
        config = self.get_welcome_config(ctx.guild.id)
        
        if status is None:
            config["enabled"] = not config.get("enabled", False)
        else:
            config["enabled"] = status.lower() in ["true", "on", "enable", "yes", "1"]
        
        self.save_data()
        
        status_text = "✅ **Enabled**" if config["enabled"] else "❌ **Disabled**"
        await ctx.send(f"🎉 Welcome system is now {status_text}")
    
    @commands.command(name="wchannel")
    @commands.has_permissions(administrator=True)
    async def wchannel(self, ctx, channel: discord.TextChannel):
        """Set the welcome channel"""
        
        config = self.get_welcome_config(ctx.guild.id)
        config["channel_id"] = str(channel.id)
        self.save_data()
        
        await ctx.send(f"✅ Welcome channel set to {channel.mention}")
    
    @commands.command(name="wmessage")
    @commands.has_permissions(administrator=True)
    async def wmessage(self, ctx, *, message: str):
        """Set the welcome message (text only)"""
        
        config = self.get_welcome_config(ctx.guild.id)
        config["message_type"] = "text"
        config["message_text"] = message
        self.save_data()
        
        preview = message.replace('{user_name}', ctx.author.display_name).replace('{server_name}', ctx.guild.name)
        await ctx.send(f"✅ Welcome message updated!\n\n📋 Preview: {preview}")
    
    @commands.command(name="wembed")
    @commands.has_permissions(administrator=True)
    async def wembed(self, ctx, title: str, description: str, color: str = "#00FF00"):
        """Set the welcome embed message"""
        
        config = self.get_welcome_config(ctx.guild.id)
        config["message_type"] = "embed"
        config["embed_title"] = title
        config["embed_description"] = description
        config["embed_color"] = color
        self.save_data()
        
        embed_color = discord.Color.green()
        try:
            if color.startswith("#"):
                embed_color = discord.Color(int(color.replace("#", ""), 16))
        except:
            pass
        
        embed = discord.Embed(
            title=title.replace('{user_name}', ctx.author.display_name).replace('{server_name}', ctx.guild.name),
            description=description.replace('{user_name}', ctx.author.display_name).replace('{server_name}', ctx.guild.name),
            color=embed_color
        )
        embed.set_footer(text="✅ Welcome embed updated!")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="wroles")
    @commands.has_permissions(administrator=True)
    async def wroles(self, ctx, *, roles: str):
        """Set auto-roles for new members"""
        
        config = self.get_welcome_config(ctx.guild.id)
        
        # Parse roles using the helper function
        role_list = self.parse_roles(ctx.guild, roles)
        
        # Store role IDs
        role_ids = [role.id for role in role_list]
        config["auto_roles"] = role_ids
        self.save_data()
        
        if role_ids:
            role_mentions = [f"<@&{role_id}>" for role_id in role_ids]
            await ctx.send(f"✅ New members will receive: {', '.join(role_mentions)}")
        else:
            await ctx.send("✅ Auto-roles cleared. No roles will be assigned.")
    
    @commands.command(name="wmemberrole")
    @commands.has_permissions(administrator=True)
    async def wmemberrole(self, ctx):
        """Automatically find and assign the @Member role to new members"""
        
        config = self.get_welcome_config(ctx.guild.id)
        
        # Look for a role named "Member"
        member_role = None
        for role in ctx.guild.roles:
            if role.name.lower() == "member":
                member_role = role
                break
        
        if not member_role:
            await ctx.send("❌ Could not find a role named 'Member' in this server. Please create one first or use `!wroles` to specify a role.")
            return
        
        # Set the auto-role
        config["auto_roles"] = [member_role.id]
        self.save_data()
        
        await ctx.send(f"✅ New members will now automatically receive the **{member_role.name}** role!")
    
    @commands.command(name="wpreview")
    @commands.has_permissions(administrator=True)
    async def wpreview(self, ctx):
        """Preview the welcome message"""
        
        config = self.get_welcome_config(ctx.guild.id)
        
        if not config.get("enabled", False):
            await ctx.send("⚠️ Welcome system is currently **disabled**. Use `!wenable` to enable it.")
            return
        
        # Build the welcome message
        embed, content, file = await self.build_welcome_message(ctx.author, preview=True)
        
        if content:
            await ctx.send(content=content, embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)
    
    @commands.command(name="wremove")
    @commands.has_permissions(administrator=True)
    async def wremove(self, ctx):
        """Remove all welcome settings for this server"""
        
        guild_id = str(ctx.guild.id)
        
        if guild_id in self.welcome_settings:
            del self.welcome_settings[guild_id]
            self.save_data()
            await ctx.send("🗑️ All welcome settings have been removed for this server.")
        else:
            await ctx.send("❌ No welcome settings found for this server.")
    
    # ============================================
    # BUILD WELCOME MESSAGE
    # ============================================
    
    async def build_welcome_message(self, member: discord.Member, preview: bool = False):
        """Build the welcome message embed/content"""
        
        guild = member.guild
        guild_id = str(guild.id)
        config = self.welcome_settings.get(guild_id, {})
        
        # Get member count
        member_count = guild.member_count
        
        # Prepare replacements
        replacements = {
            "{user_name}": member.display_name,
            "{user_mention}": member.mention,
            "{user_id}": str(member.id),
            "{user_tag}": str(member),
            "{server_name}": guild.name,
            "{server_id}": str(guild.id),
            "{member_count}": str(member_count),
            "{join_position}": str(member_count),
            "{created_at}": member.created_at.strftime("%B %d, %Y"),
            "{joined_at}": member.joined_at.strftime("%B %d, %Y") if member.joined_at else "Unknown"
        }
        
        embed = None
        content = None
        file = None
        
        message_type = config.get("message_type", "embed")
        
        if message_type == "embed":
            # Build embed
            title = config.get("embed_title", "🎉 Welcome {user_name}!")
            description = config.get("embed_description", "Welcome to **{server_name}**!")
            color_str = config.get("embed_color", "#00FF00")
            footer = config.get("embed_footer", "We hope you enjoy your stay!")
            
            # Apply replacements
            for key, value in replacements.items():
                title = title.replace(key, value)
                description = description.replace(key, value)
                if footer:
                    footer = footer.replace(key, value)
            
            # Parse color
            embed_color = discord.Color.green()
            try:
                if color_str.startswith("#"):
                    embed_color = discord.Color(int(color_str.replace("#", ""), 16))
                else:
                    color_map = {
                        "red": discord.Color.red(),
                        "green": discord.Color.green(),
                        "blue": discord.Color.blue(),
                        "yellow": discord.Color.yellow(),
                        "orange": discord.Color.orange(),
                        "purple": discord.Color.purple(),
                        "pink": discord.Color.pink(),
                        "gold": discord.Color.gold(),
                        "teal": discord.Color.teal(),
                        "default": discord.Color.default()
                    }
                    if color_str.lower() in color_map:
                        embed_color = color_map[color_str.lower()]
            except:
                pass
            
            embed = discord.Embed(
                title=title,
                description=description,
                color=embed_color,
                timestamp=datetime.utcnow() if config.get("welcome_timestamp", True) else None
            )
            
            # Set thumbnail (user avatar)
            embed.set_thumbnail(url=member.display_avatar.url)
            
            # Set footer
            if footer:
                embed.set_footer(text=footer)
            
            # Add fields
            if config.get("show_member_count", True):
                embed.add_field(name="📊 Member Count", value=str(member_count), inline=True)
            
            if config.get("show_join_position", True):
                embed.add_field(name="📌 Join Position", value=f"#{member_count}", inline=True)
            
            # Mention role
            mention_role_id = config.get("mention_role")
            if mention_role_id:
                role = guild.get_role(mention_role_id)
                if role:
                    embed.add_field(name="📢", value=f"{role.mention} welcome the new member!", inline=False)
            
            # Custom image
            if config.get("use_custom_image", False):
                image_url = config.get("welcome_image_url")
                if image_url:
                    embed.set_image(url=image_url)
            else:
                # Try to use a default banner
                try:
                    file = discord.File("welcome_banner.png", filename="welcome_banner.png")
                    embed.set_image(url="attachment://welcome_banner.png")
                except:
                    pass
        
        else:
            # Text message
            content = config.get("message_text", "🎉 Welcome {user_mention} to **{server_name}**!")
            for key, value in replacements.items():
                content = content.replace(key, value)
            
            # Mention role
            mention_role_id = config.get("mention_role")
            if mention_role_id:
                role = guild.get_role(mention_role_id)
                if role:
                    content = f"{role.mention} {content}"
        
        return embed, content, file
    
    # ============================================
    # EVENT HANDLERS
    # ============================================
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Send welcome message when a member joins"""
        
        guild = member.guild
        guild_id = str(guild.id)
        
        # Check if welcome system is enabled
        if guild_id not in self.welcome_settings:
            return
        
        config = self.welcome_settings[guild_id]
        
        if not config.get("enabled", False):
            return
        
        # Assign auto-roles
        auto_roles = config.get("auto_roles", [])
        for role_id in auto_roles:
            role = guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role, reason="Auto-role on join")
                except:
                    pass
        
        # Send welcome message to channel
        channel_id = config.get("channel_id")
        if channel_id:
            channel = guild.get_channel(int(channel_id))
            if channel:
                embed, content, file = await self.build_welcome_message(member)
                
                try:
                    if content:
                        await channel.send(content=content, embed=embed, file=file)
                    else:
                        await channel.send(embed=embed, file=file)
                except Exception as e:
                    print(f"❌ Failed to send welcome message: {e}")
        
        # Send DM welcome
        if config.get("welcome_dm_enabled", False):
            dm_message = config.get("welcome_dm_message", "🎉 Welcome to {server_name}!")
            for key, value in {
                "{user_name}": member.display_name,
                "{server_name}": guild.name
            }.items():
                dm_message = dm_message.replace(key, value)
            
            try:
                await member.send(dm_message)
            except:
                pass
        
        # Log the join
        if config.get("welcome_logs", False):
            log_channel_id = config.get("log_channel_id")
            if log_channel_id:
                log_channel = guild.get_channel(int(log_channel_id))
                if log_channel:
                    log_embed = discord.Embed(
                        title="📥 Member Joined",
                        description=f"{member.mention} joined the server",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    log_embed.add_field(name="User", value=str(member), inline=True)
                    log_embed.add_field(name="User ID", value=member.id, inline=True)
                    log_embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M"), inline=True)
                    log_embed.add_field(name="Server Members", value=guild.member_count, inline=True)
                    log_embed.set_thumbnail(url=member.display_avatar.url)
                    
                    await log_channel.send(embed=log_embed)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Send goodbye message when a member leaves"""
        
        guild = member.guild
        guild_id = str(guild.id)
        
        if guild_id not in self.welcome_settings:
            return
        
        config = self.welcome_settings[guild_id]
        
        if not config.get("goodbye_enabled", False):
            return
        
        channel_id = config.get("goodbye_channel_id")
        if not channel_id:
            return
        
        channel = guild.get_channel(int(channel_id))
        if not channel:
            return
        
        # Build goodbye message
        goodbye_message = config.get(
            "goodbye_message",
            "😢 {user_name} has left the server. We'll miss you!"
        )
        
        replacements = {
            "{user_name}": member.display_name,
            "{user_mention}": member.mention,
            "{user_tag}": str(member),
            "{server_name}": guild.name,
            "{member_count}": str(guild.member_count)
        }
        
        for key, value in replacements.items():
            goodbye_message = goodbye_message.replace(key, value)
        
        # Send goodbye embed
        color_str = config.get("goodbye_embed_color", "#FF0000")
        embed_color = discord.Color.red()
        try:
            if color_str.startswith("#"):
                embed_color = discord.Color(int(color_str.replace("#", ""), 16))
        except:
            pass
        
        embed = discord.Embed(
            title="👋 Goodbye",
            description=goodbye_message,
            color=embed_color,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="📊 Member Count", value=str(guild.member_count), inline=True)
        
        await channel.send(embed=embed)
    
    # ============================================
    # ERROR HANDLERS
    # ============================================
    
    @wsetup.error
    @wenable.error
    @wchannel.error
    @wmessage.error
    @wembed.error
    @wroles.error
    @wpreview.error
    @wremove.error
    @wmemberrole.error
    async def welcome_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need Administrator permissions to use this command!")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument. Please check the command usage.")
        else:
            await ctx.send(f"❌ An error occurred: {str(error)}")

# ============================================
# SETUP
# ============================================

async def setup(bot):
    await bot.add_cog(WelcomeSystem(bot))