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
import emoji  # <--- Must pip install emoji

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
    # SMART TEXT DRAWER (Handles Emojis + Text)
    # ============================================
    def draw_text_with_emoji(self, draw, position, text, font_text, font_emoji, fill, anchor="mm"):
        """Draws text while switching to emoji font when it detects an emoji."""
        x, y = position
        
        # Parse text into a list of (text, is_emoji)
        parts = []
        for char in text:
            if emoji.is_emoji(char):
                parts.append((char, True))
            else:
                if parts and not parts[-1][1]:
                    parts[-1] = (parts[-1][0] + char, False)
                else:
                    parts.append((char, False))
        
        current_x = x
        
        for part_text, is_em in parts:
            if is_em:
                # Use emoji font
                bbox = draw.textbbox((0, 0), part_text, font=font_emoji)
                width = bbox[2] - bbox[0]
                draw.text((current_x, y), part_text, font=font_emoji, fill=fill, anchor="mm")
                current_x += width - 5 # Slight spacing fix for emojis
            else:
                # Use roboto font
                bbox = draw.textbbox((0, 0), part_text, font=font_text)
                width = bbox[2] - bbox[0]
                draw.text((current_x, y), part_text, font=font_text, fill=fill, anchor="mm")
                current_x += width

    # ============================================
    # BUILD WELCOME IMAGE CARD
    # ============================================
    async def build_welcome_card(self, member: discord.Member):
        """Generates a custom image card similar to the screenshot."""
        config = self.get_welcome_config(member.guild.id)
        
        canvas_width = 800
        canvas_height = 350
        
        # -------------------------------------------------------------
        # LOAD BACKGROUND FROM THE SAME FOLDER AS main.py
        # -------------------------------------------------------------
        bg_img = Image.new('RGB', (canvas_width, canvas_height), color=(54, 57, 63))
        welcome_bg_path = os.path.join(os.path.dirname(__file__), "..", "welcome.png")
        if os.path.exists(welcome_bg_path):
            try:
                bg_img = Image.open(welcome_bg_path).convert("RGB").resize((canvas_width, canvas_height), Image.LANCZOS)
            except:
                pass

        img = bg_img.copy()
        draw = ImageDraw.Draw(img)

        circle_color = self.hex_to_rgb(config.get("circle_color", "#d1a3ff"))
        name_color = self.hex_to_rgb(config.get("user_name_color", "#a1b0d6"))
        text_color = self.hex_to_rgb(config.get("welcome_text_color", "#a1b0d6"))

        # -------------------------------------------------------------
        # LOAD FONTS FROM THE SAME FOLDER AS main.py
        # -------------------------------------------------------------
        font_large_roboto = ImageFont.load_default()
        font_medium_roboto = ImageFont.load_default()
        font_large_emoji = ImageFont.load_default()
        font_medium_emoji = ImageFont.load_default()

        roboto_path = os.path.join(os.path.dirname(__file__), "..", "Roboto_Condensed-SemiBoldItalic.ttf")
        emoji_path = os.path.join(os.path.dirname(__file__), "..", "NotoColorEmoji.ttf")

        if os.path.exists(roboto_path):
            try:
                font_large_roboto = ImageFont.truetype(roboto_path, 46)
                font_medium_roboto = ImageFont.truetype(roboto_path, 36)
            except:
                pass
        if os.path.exists(emoji_path):
            try:
                font_large_emoji = ImageFont.truetype(emoji_path, 46)
                font_medium_emoji = ImageFont.truetype(emoji_path, 36)
            except:
                pass

        avatar_size = 180
        circle_x = (canvas_width - avatar_size) // 2
        circle_y = 30
        draw.ellipse([circle_x - 10, circle_y - 10, circle_x + avatar_size + 10, circle_y + avatar_size + 10], fill=circle_color)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(member.display_avatar.with_format("png").url) as resp:
                    if resp.status == 200:
                        avatar_data = await resp.read()
                        avatar_img = Image.open(io.BytesIO(avatar_data)).convert("RGBA")
                        avatar_img = avatar_img.resize((avatar_size, avatar_size), Image.LANCZOS)
                        mask = Image.new('L', (avatar_size, avatar_size), 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
                        avatar_img.putalpha(mask)
                        img.paste(avatar_img, (circle_x, circle_y), avatar_img)
        except Exception as e:
            print(f"❌ Error fetching avatar: {e}")

        user_name = member.display_name
        self.draw_text_with_emoji(draw, (canvas_width // 2, circle_y + avatar_size + 20), user_name, font_large_roboto, font_large_emoji, name_color)

        welcome_text = config.get("welcome_text", "Welcome to VoDevs!")
        self.draw_text_with_emoji(draw, (canvas_width // 2, circle_y + avatar_size + 80), welcome_text, font_medium_roboto, font_medium_emoji, text_color)

        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return discord.File(fp=img_io, filename="welcome.png")

    # ============================================
    # BUILD MODERATION ACTION CARD (UNIFIED)
    # ============================================
    async def build_action_card(self, guild: discord.Guild, member: discord.Member, action_type: str, reason: str, moderator_name: str, warn_count: int = 0):
        """
        Generates a unified card for ALL Moderation Actions.
        Uses the same style as the Welcome Card, but with dynamic text.
        """
        config = self.get_welcome_config(guild.id)
        
        canvas_width = 800
        canvas_height = 350
        
        # -------------------------------------------------------------
        # LOAD BACKGROUND FROM THE SAME FOLDER AS main.py
        # -------------------------------------------------------------
        bg_img = Image.new('RGB', (canvas_width, canvas_height), color=(54, 57, 63))
        welcome_bg_path = os.path.join(os.path.dirname(__file__), "..", "welcome.png")
        if os.path.exists(welcome_bg_path):
            try:
                bg_img = Image.open(welcome_bg_path).convert("RGB").resize((canvas_width, canvas_height), Image.LANCZOS)
            except:
                pass

        img = bg_img.copy()
        draw = ImageDraw.Draw(img)

        # Colors (Red text for actions, Light blue for names)
        circle_color = self.hex_to_rgb(config.get("circle_color", "#d1a3ff"))
        name_color = self.hex_to_rgb(config.get("user_name_color", "#a1b0d6"))
        action_text_color = self.hex_to_rgb("#ff5555") # Red for the action status
        reason_text_color = self.hex_to_rgb("#ffaaaa") # Lighter red for reason

        # -------------------------------------------------------------
        # LOAD FONTS FROM THE SAME FOLDER AS main.py
        # -------------------------------------------------------------
        font_large_roboto = ImageFont.load_default()
        font_medium_roboto = ImageFont.load_default()
        font_small_roboto = ImageFont.load_default()
        font_large_emoji = ImageFont.load_default()
        font_medium_emoji = ImageFont.load_default()
        font_small_emoji = ImageFont.load_default()

        roboto_path = os.path.join(os.path.dirname(__file__), "..", "Roboto_Condensed-SemiBoldItalic.ttf")
        emoji_path = os.path.join(os.path.dirname(__file__), "..", "NotoColorEmoji.ttf")

        if os.path.exists(roboto_path):
            try:
                font_large_roboto = ImageFont.truetype(roboto_path, 40)
                font_medium_roboto = ImageFont.truetype(roboto_path, 26)
                font_small_roboto = ImageFont.truetype(roboto_path, 20)
            except:
                pass
        if os.path.exists(emoji_path):
            try:
                font_large_emoji = ImageFont.truetype(emoji_path, 40)
                font_medium_emoji = ImageFont.truetype(emoji_path, 26)
                font_small_emoji = ImageFont.truetype(emoji_path, 20)
            except:
                pass

        avatar_size = 160
        circle_x = (canvas_width - avatar_size) // 2
        circle_y = 40
        draw.ellipse([circle_x - 10, circle_y - 10, circle_x + avatar_size + 10, circle_y + avatar_size + 10], fill=circle_color)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(member.display_avatar.with_format("png").url) as resp:
                    if resp.status == 200:
                        avatar_data = await resp.read()
                        avatar_img = Image.open(io.BytesIO(avatar_data)).convert("RGBA")
                        avatar_img = avatar_img.resize((avatar_size, avatar_size), Image.LANCZOS)
                        mask = Image.new('L', (avatar_size, avatar_size), 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
                        avatar_img.putalpha(mask)
                        img.paste(avatar_img, (circle_x, circle_y), avatar_img)
        except Exception as e:
            print(f"❌ Error fetching avatar: {e}")

        # 1. Draw Username
        user_name = member.display_name
        self.draw_text_with_emoji(draw, (canvas_width // 2, circle_y + avatar_size + 12), user_name, font_large_roboto, font_large_emoji, name_color)

        # 2. Draw Action Type (e.g. "has been WARNED")
        action_text = f"has been {action_type.upper()}"
        self.draw_text_with_emoji(draw, (canvas_width // 2, circle_y + avatar_size + 52), action_text, font_medium_roboto, font_medium_emoji, action_text_color)

        # 3. Draw the Reason (handling long text)
        if reason:
            display_reason = reason
            if len(display_reason) > 40:
                split_point = display_reason.rfind(' ', 0, 40)
                if split_point == -1: split_point = 40
                line1 = display_reason[:split_point]
                line2 = display_reason[split_point:].strip()
                
                self.draw_text_with_emoji(draw, (canvas_width // 2, circle_y + avatar_size + 82), f"Reason: {line1}", font_small_roboto, font_small_emoji, reason_text_color)
                self.draw_text_with_emoji(draw, (canvas_width // 2, circle_y + avatar_size + 104), line2, font_small_roboto, font_small_emoji, reason_text_color)
            else:
                self.draw_text_with_emoji(draw, (canvas_width // 2, circle_y + avatar_size + 82), f"Reason: {display_reason}", font_small_roboto, font_small_emoji, reason_text_color)

        # 4. If it's a WARNING, show the warning count
        if action_type.lower() == "warn" and warn_count > 0:
            count_text = f"Total Warnings: {warn_count}"
            if len(reason) > 40:
                self.draw_text_with_emoji(draw, (canvas_width // 2, circle_y + avatar_size + 126), count_text, font_small_roboto, font_small_emoji, reason_text_color)
            else:
                self.draw_text_with_emoji(draw, (canvas_width // 2, circle_y + avatar_size + 104), count_text, font_small_roboto, font_small_emoji, reason_text_color)

        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return discord.File(fp=img_io, filename="action.png")

    # ============================================
    # HELPER: CONVERT HEX TO RGB
    # ============================================
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

async def setup(bot):
    await bot.add_cog(WelcomeSystem(bot))
