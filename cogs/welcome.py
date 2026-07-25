import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
import re
from datetime import datetime
from typing import Optional, List
from PIL import Image, ImageDraw, ImageFont, ImageOps
import aiohttp
import io

class WelcomeSystem(commands.Cog):
    """Advanced Welcome System with Custom Image Card"""
    
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
                "auto_roles": [],
                "welcome_background": None,
                "custom_font": None,
                "welcome_text": "Welcome to VoDevs!",
                "welcome_text_color": "#a1b0d6",
                "user_name_color": "#a1b0d6",
                "circle_color": "#d1a3ff"
            }
            self.save_data()
        return self.welcome_settings[guild_id]
    
    # ============================================
    # HELPER FUNCTIONS FOR ROLE PARSING
    # ============================================
    def parse_roles(self, guild: discord.Guild, role_input: str) -> List[discord.Role]:
        roles = []
        role_input = role_input.strip()
        if not role_input or role_input.lower() in ["none", "clear", "remove"]:
            return []
        for sep in [';', ',', ' ']:
            if sep in role_input:
                parts = role_input.split(sep)
                break
        else:
            parts = [role_input]
        for part in parts:
            part = part.strip()
            if not part: continue
            role = None
            if part.startswith('<@&') and part.endswith('>'):
                try:
                    role_id = int(part.replace('<@&', '').replace('>', ''))
                    role = guild.get_role(role_id)
                except: pass
            if not role and part.isdigit():
                role = guild.get_role(int(part))
            if not role:
                for r in guild.roles:
                    if r.name.lower() == part.lower():
                        role = r
                        break
            if not role:
                for r in guild.roles:
                    if part.lower() in r.name.lower():
                        role = r
                        break
            if role: roles.append(role)
        return roles

    # ============================================
    # BUILD WELCOME IMAGE CARD
    # ============================================
    async def build_welcome_card(self, member: discord.Member):
        """Generates a custom image card similar to the screenshot."""
        config = self.get_welcome_config(member.guild.id)
        
        # Define canvas size
        canvas_width = 800
        canvas_height = 350
        
        # Determine the Background
        bg_filename = config.get("welcome_background", None)
        if bg_filename and os.path.exists(os.path.join("welcome_assets", bg_filename)):
            bg_path = os.path.join("welcome_assets", bg_filename)
            bg_img = Image.open(bg_path).convert("RGB").resize((canvas_width, canvas_height), Image.LANCZOS)
        else:
            # Default dark grey background
            bg_img = Image.new('RGB', (canvas_width, canvas_height), color=(54, 57, 63))
        
        img = bg_img.copy()
        draw = ImageDraw.Draw(img)

        # Colors from config
        circle_color = self.hex_to_rgb(config.get("circle_color", "#d1a3ff"))
        name_color = self.hex_to_rgb(config.get("user_name_color", "#a1b0d6"))
        text_color = self.hex_to_rgb(config.get("welcome_text_color", "#a1b0d6"))

        # Determine the Fonts
        font_filename = config.get("custom_font", None)
        font_large = None
        font_medium = None
        
        # Try loading custom font first, then fallback to Inter.ttf, then default
        try:
            if font_filename and os.path.exists(os.path.join("welcome_assets", font_filename)):
                font_path = os.path.join("welcome_assets", font_filename)
                font_large = ImageFont.truetype(font_path, 46)
                font_medium = ImageFont.truetype(font_path, 36)
            else:
                # Fallback to "Inter-SemiBold.ttf" if available
                font_large = ImageFont.truetype("Inter-SemiBold.ttf", 46)
                font_medium = ImageFont.truetype("Inter-SemiBold.ttf", 36)
        except:
            # If both fail, use default
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()

        # Draw the avatar circle border
        avatar_size = 180
        circle_x = (canvas_width - avatar_size) // 2
        circle_y = 30
        draw.ellipse([circle_x - 10, circle_y - 10, circle_x + avatar_size + 10, circle_y + avatar_size + 10], fill=circle_color)

        # Fetch and paste the user's avatar (as a circle)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(member.display_avatar.with_format("png").url) as resp:
                    if resp.status == 200:
                        avatar_data = await resp.read()
                        avatar_img = Image.open(io.BytesIO(avatar_data)).convert("RGBA")
                        avatar_img = avatar_img.resize((avatar_size, avatar_size), Image.LANCZOS)
                        
                        # Create circular mask for avatar
                        mask = Image.new('L', (avatar_size, avatar_size), 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
                        avatar_img.putalpha(mask)
                        
                        # Paste onto canvas
                        img.paste(avatar_img, (circle_x, circle_y), avatar_img)
        except Exception as e:
            print(f"❌ Error fetching avatar: {e}")

        # Draw Username (below avatar)
        user_name = member.display_name
        username_text = user_name
        draw.text((canvas_width / 2, circle_y + avatar_size + 20), username_text, fill=name_color, font=font_large, anchor="mm")

        # Draw Welcome Message
        welcome_text = config.get("welcome_text", "Welcome to VoDevs!")
        draw.text((canvas_width / 2, circle_y + avatar_size + 80), welcome_text, fill=text_color, font=font_medium, anchor="mm")

        # Save to BytesIO
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return discord.File(fp=img_io, filename="welcome.png")

    def hex_to_rgb(self, hex_code: str):
        """Convert hex color to RGB tuple."""
        hex_code = hex_code.lstrip('#')
        return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

    # ============================================
    # SLASH COMMANDS
    # ============================================
    @app_commands.command(name="welcome_setup", description="[Admin] Set up the welcome system")
    @app_commands.default_permissions(administrator=True)
    async def welcome_setup_slash(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🎉 Welcome System Setup", description="Welcome to the welcome system setup!", color=discord.Color.blue())
        embed.add_field(name="📋 Step 1", value="Use `/welcome_channel #channel` to set the welcome channel", inline=False)
        embed.add_field(name="📋 Step 2", value="Use `/welcome_roles @role` to set auto-roles", inline=False)
        embed.add_field(name="📋 Step 3", value="Use `/welcome_enable` to turn the system ON", inline=False)
        embed.set_footer(text="Need help? Use /help")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="welcome_enable", description="[Admin] Enable or disable the welcome system")
    @app_commands.default_permissions(administrator=True)
    async def welcome_enable_slash(self, interaction: discord.Interaction, enabled: bool):
        config = self.get_welcome_config(interaction.guild.id)
        config["enabled"] = enabled
        self.save_data()
        status = "✅ **Enabled**" if enabled else "❌ **Disabled**"
        embed = discord.Embed(title="🎉 Welcome System Status", description=f"Welcome system is now {status}", color=discord.Color.green() if enabled else discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="welcome_channel", description="[Admin] Set the welcome channel")
    @app_commands.default_permissions(administrator=True)
    async def welcome_channel_slash(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config = self.get_welcome_config(interaction.guild.id)
        config["channel_id"] = str(channel.id)
        self.save_data()
        embed = discord.Embed(title="✅ Welcome Channel Set", description=f"Welcome messages will be sent to {channel.mention}", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="welcome_roles", description="[Admin] Set auto-roles for new members")
    @app_commands.default_permissions(administrator=True)
    async def welcome_roles_slash(self, interaction: discord.Interaction, roles: str):
        config = self.get_welcome_config(interaction.guild.id)
        role_list = self.parse_roles(interaction.guild, roles)
        config["auto_roles"] = [role.id for role in role_list]
        self.save_data()
        if role_list:
            role_mentions = [f"<@&{role.id}>" for role in role_list]
            embed = discord.Embed(title="✅ Auto-Roles Set", description=f"New members will receive: {', '.join(role_mentions)}", color=discord.Color.green())
        else:
            embed = discord.Embed(title="✅ Auto-Roles Cleared", description="No roles will be auto-assigned.", color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="welcome_preview", description="[Admin] Preview the welcome image")
    @app_commands.default_permissions(administrator=True)
    async def welcome_preview_slash(self, interaction: discord.Interaction):
        config = self.get_welcome_config(interaction.guild.id)
        if not config.get("enabled", False):
            await interaction.response.send_message("⚠️ Welcome system is currently **disabled**. Use `/welcome_enable` to enable it.", ephemeral=True)
            return
        
        file = await self.build_welcome_card(interaction.user)
        await interaction.response.send_message(file=file, ephemeral=True)

    # ============================================
    # PREFIX COMMANDS
    # ============================================
    @commands.command(name="wsetup")
    @commands.has_permissions(administrator=True)
    async def wsetup(self, ctx):
        embed = discord.Embed(title="🎉 Welcome System Setup", description="Welcome to the welcome system setup!", color=discord.Color.blue())
        embed.add_field(name="📋 Step 1", value="Use `!wchannel #channel` to set the welcome channel", inline=False)
        embed.add_field(name="📋 Step 2", value="Use `!wroles @role` to set auto-roles", inline=False)
        embed.add_field(name="📋 Step 3", value="Use `!wenable` to turn the system ON", inline=False)
        embed.set_footer(text="Need help? Use !help")
        await ctx.send(embed=embed)

    @commands.command(name="wenable")
    @commands.has_permissions(administrator=True)
    async def wenable(self, ctx, status: str = None):
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
        config = self.get_welcome_config(ctx.guild.id)
        config["channel_id"] = str(channel.id)
        self.save_data()
        await ctx.send(f"✅ Welcome channel set to {channel.mention}")

    @commands.command(name="wroles")
    @commands.has_permissions(administrator=True)
    async def wroles(self, ctx, *, roles: str):
        config = self.get_welcome_config(ctx.guild.id)
        role_list = self.parse_roles(ctx.guild, roles)
        config["auto_roles"] = [role.id for role in role_list]
        self.save_data()
        if role_list:
            role_mentions = [f"<@&{role.id}>" for role in role_list]
            await ctx.send(f"✅ New members will receive: {', '.join(role_mentions)}")
        else:
            await ctx.send("✅ Auto-roles cleared.")

    @commands.command(name="wpreview")
    @commands.has_permissions(administrator=True)
    async def wpreview(self, ctx):
        config = self.get_welcome_config(ctx.guild.id)
        if not config.get("enabled", False):
            await ctx.send("⚠️ Welcome system is currently **disabled**. Use `!wenable` to enable it.")
            return
        file = await self.build_welcome_card(ctx.author)
        await ctx.send(file=file)

    @commands.command(name="wremove")
    @commands.has_permissions(administrator=True)
    async def wremove(self, ctx):
        guild_id = str(ctx.guild.id)
        if guild_id in self.welcome_settings:
            del self.welcome_settings[guild_id]
            self.save_data()
            await ctx.send("🗑️ All welcome settings have been removed for this server.")
        else:
            await ctx.send("❌ No welcome settings found for this server.")

    # ==========================================
    # EVENT HANDLERS
    # ==========================================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        guild_id = str(guild.id)
        if guild_id not in self.welcome_settings: return
        config = self.welcome_settings[guild_id]
        if not config.get("enabled", False): return

        # Assign auto-roles
        for role_id in config.get("auto_roles", []):
            role = guild.get_role(role_id)
            if role:
                try: await member.add_roles(role, reason="Auto-role on join")
                except: pass

        # Send welcome image card
        channel_id = config.get("channel_id")
        if channel_id:
            channel = guild.get_channel(int(channel_id))
            if channel:
                try:
                    file = await self.build_welcome_card(member)
                    await channel.send(file=file)
                except Exception as e:
                    print(f"❌ Failed to send welcome card: {e}")

# ==========================================
# SETUP
# ==========================================
async def setup(bot):
    await bot.add_cog(WelcomeSystem(bot))
