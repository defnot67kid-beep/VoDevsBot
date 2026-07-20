import discord
from discord.ext import commands
import json
import os
import asyncio
import math 
import random
import io
from PIL import Image, ImageDraw, ImageFont, ImageOps

class LevelBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "level_data.json"
        self.role_data_file = "level_roles.json"
        
        # FIX: SAFE DATA LOADING (Never resets on crash)
        self.level_data = self.safe_load_data()
        self.level_roles = self.safe_load_role_data()
        
        # Cooldown dictionary
        self.xp_cooldowns = {}
        
        # Default slowmode
        self.COOLDOWN_SECONDS = 45
        
        # Bypass list
        self.bypass_users = set()
        self.bypass_roles = set()
        
        # Level-Up Announcement Channel ID
        self.level_channel_id = 1526989768595083384
        
        # Load bypass config & channel config
        self.load_config()
        
        # Define the level progression
        self.levels = [2, 5, 10, 20, 35, 50, 60, 70, 100]

    def safe_load_data(self):
        """SAFE LOAD: Creates empty dict if file is corrupted, NEVER resets existing data."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
                    else:
                        return {}
            except (json.JSONDecodeError, ValueError):
                # If the file is corrupt, BACK IT UP instead of deleting it!
                if os.path.exists(self.data_file):
                    backup_name = f"level_data_BACKUP_{int(datetime.datetime.now().timestamp())}.json"
                    os.rename(self.data_file, backup_name)
                    print(f"⚠️ Corrupted level_data.json backed up to {backup_name}")
                return {}
        return {}

    def save_data(self):
        """SAVE DATA with safety checks."""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.level_data, f, indent=4)
        except Exception as e:
            print(f"❌ Failed to save level_data.json: {e}")

    def safe_load_role_data(self):
        """SAFE LOAD for role data."""
        if os.path.exists(self.role_data_file):
            try:
                with open(self.role_data_file, 'r') as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
            except:
                return {}
        return {}

    def save_role_data(self):
        try:
            with open(self.role_data_file, 'w') as f:
                json.dump(self.level_roles, f, indent=4)
        except Exception as e:
            print(f"❌ Failed to save level_roles.json: {e}")
            
    def load_config(self):
        config_file = "level_config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.COOLDOWN_SECONDS = config.get("cooldown_seconds", 45)
                    self.bypass_users = set(config.get("bypass_users", []))
                    self.bypass_roles = set(config.get("bypass_roles", []))
                    self.level_channel_id = config.get("level_channel_id", 1526989768595083384)
            except:
                self.save_config()
        else:
            self.save_config()
            
    def save_config(self):
        try:
            config_file = "level_config.json"
            config = {
                "cooldown_seconds": self.COOLDOWN_SECONDS,
                "bypass_users": list(self.bypass_users),
                "bypass_roles": list(self.bypass_roles),
                "level_channel_id": self.level_channel_id
            }
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
        except:
            pass

    def get_role_color(self, level):
        colors = {
            2: discord.Color.from_rgb(46, 204, 113),
            5: discord.Color.from_rgb(52, 152, 219),
            10: discord.Color.from_rgb(155, 89, 182),
            20: discord.Color.from_rgb(230, 126, 34),
            35: discord.Color.from_rgb(231, 76, 60),
            50: discord.Color.from_rgb(241, 196, 15),
            60: discord.Color.from_rgb(26, 188, 156),
            70: discord.Color.from_rgb(142, 68, 173),
            100: discord.Color.from_rgb(192, 57, 43),
        }
        return colors.get(level, discord.Color.default())

    def get_role_permissions(self, level):
        perms = discord.Permissions()
        perms.read_messages = True
        perms.send_messages = True
        perms.read_message_history = True
        
        if level >= 10:
            perms.attach_files = True
        if level >= 20:
            perms.embed_links = True
        
        return perms

    def calculate_xp_gain(self, message):
        content = message.content
        length = len(content)
        if length == 0:
            return 0
            
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
        
        if total_xp > 1000:
            total_xp = 1000
            
        return round(total_xp)

    def get_xp_needed(self, level):
        if level <= 0:
            return 0
        return int(1000 * (level ** 1.5))

    def get_level_from_xp(self, xp):
        level = 0
        while self.get_xp_needed(level + 1) <= xp:
            level += 1
        return level

    # ==========================================
    # NEW: INTERNAL CARD GENERATOR (No external API)
    # ==========================================
    
    async def generate_rank_card(self, member, level, xp_in_level, xp_needed):
        """
        Generates a rank card image using PIL (Pillow).
        This runs INSIDE your bot, so it NEVER goes down.
        """
        # 1. Create a blank canvas (800 x 250)
        img = Image.new('RGB', (800, 250), color=(44, 47, 51))  # Dark grey Discord color
        draw = ImageDraw.Draw(img)
        
        # 2. Draw a background border/glow
        draw.rounded_rectangle([(10, 10), (790, 240)], radius=20, fill=(54, 57, 63), outline=(114, 137, 218), width=4)
        
        # 3. Load fonts (try to use default if custom not found)
        try:
            font_large = ImageFont.truetype("arial.ttf", 36)
            font_small = ImageFont.truetype("arial.ttf", 20)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # 4. Get the user's avatar
        avatar_bytes = await member.display_avatar.read()
        avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        
        # Crop avatar to a circle
        mask = Image.new("L", avatar_img.size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, avatar_img.size[0], avatar_img.size[1]), fill=255)
        
        # Paste avatar onto card
        img.paste(avatar_img, (40, 40), mask)
        
        # 5. Draw Border around avatar
        draw.ellipse([(35, 35), (135, 135)], outline=(114, 137, 218), width=5)
        
        # 6. Draw Username (White)
        draw.text((165, 50), f"{member.display_name}", font=font_large, fill=(255, 255, 255))
        
        # 7. Draw Level & XP text
        draw.text((165, 100), f"Level: {level}    XP: {int(xp_in_level)} / {int(xp_needed)}", font=font_small, fill=(181, 188, 194))
        
        # 8. Draw Progress Bar Background
        bar_x = 165
        bar_y = 145
        bar_w = 550
        bar_h = 30
        draw.rounded_rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)], radius=15, fill=(44, 47, 51), outline=(99, 102, 108), width=2)
        
        # 9. Draw Progress Bar Fill (Purple by default)
        if xp_needed > 0:
            fill_width = int((xp_in_level / xp_needed) * bar_w)
            if fill_width > 0:
                draw.rounded_rectangle([(bar_x, bar_y), (bar_x + fill_width, bar_y + bar_h)], radius=15, fill=(93, 63, 211))
        
        # 10. Save to buffer and return
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        return discord.File(img_buffer, filename="rank.png")

    # ==========================================
    # USER COMMANDS
    # ==========================================

    @commands.command(name="level", aliases=["lvl"])
    async def level(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author
            
        user_id = str(member.id)
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.level_data or user_id not in self.level_data[guild_id]:
            return await ctx.send(f"❌ {member.mention} hasn't chatted enough to have a rank yet!")
        
        user_data = self.level_data[guild_id][user_id]
        current_xp = user_data["xp"]
        current_level = self.get_level_from_xp(current_xp)
        
        next_level_xp = self.get_xp_needed(current_level + 1)
        prev_level_xp = self.get_xp_needed(current_level)
        xp_in_level = current_xp - prev_level_xp
        xp_needed_for_next = next_level_xp - prev_level_xp
        
        # GENERATE THE CARD LOCALLY
        file = await self.generate_rank_card(member, current_level, xp_in_level, xp_needed_for_next)
        
        embed = discord.Embed(
            color=discord.Color.purple()
        )
        embed.set_image(url="attachment://rank.png")
        embed.set_footer(text="Use /card to customize this card! (Coming soon)")
        
        await ctx.send(embed=embed, file=file)

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.level_data or not self.level_data[guild_id]:
            return await ctx.send("❌ No level data for this server yet!")
        
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
    # ADMIN COMMANDS (Unchanged from before)
    # ==========================================

    @commands.command(name="xpslmset")
    @commands.has_permissions(administrator=True)
    async def xp_slowmode_set(self, ctx, seconds: int):
        if seconds < 0:
            return await ctx.send("❌ Slowmode cannot be negative!")
        self.COOLDOWN_SECONDS = seconds
        self.save_config()
        await ctx.send(f"✅ XP Slowmode set to **{seconds}** seconds.")

    @commands.command(name="xpslmby")
    @commands.has_permissions(administrator=True)
    async def xp_slowmode_bypass(self, ctx, target_type: str, *, target_id: str = None):
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
                await ctx.send(f"✅ Removed {member.mention} from bypass.")
            else:
                self.bypass_users.add(user_id)
                self.save_config()
                await ctx.send(f"✅ Added {member.mention} to bypass.")
                
        elif target_type == "userid":
            if not target_id:
                return await ctx.send("❌ Please provide a user ID: `!xpslmby userid 123456789`")
            try:
                user_id = str(int(target_id))
                if user_id in self.bypass_users:
                    self.bypass_users.remove(user_id)
                    self.save_config()
                    await ctx.send(f"✅ Removed User ID `{user_id}` from bypass.")
                else:
                    self.bypass_users.add(user_id)
                    self.save_config()
                    await ctx.send(f"✅ Added User ID `{user_id}` to bypass.")
            except ValueError:
                return await ctx.send("❌ Invalid User ID.")
                
        elif target_type == "role":
            if not ctx.message.role_mentions:
                return await ctx.send("❌ Please mention a role: `!xpslmby role @Role`")
            role = ctx.message.role_mentions[0]
            role_id = str(role.id)
            
            if role_id in self.bypass_roles:
                self.bypass_roles.remove(role_id)
                self.save_config()
                await ctx.send(f"✅ Removed {role.mention} from bypass.")
            else:
                self.bypass_roles.add(role_id)
                self.save_config()
                await ctx.send(f"✅ Added {role.mention} to bypass.")
        else:
            await ctx.send("❌ Invalid target type! Use: `user`, `userid`, or `role`.")

    @commands.command(name="xpslmlist")
    @commands.has_permissions(administrator=True)
    async def xp_slowmode_list(self, ctx):
        embed = discord.Embed(title="⚡ XP Slowmode Bypass List", color=discord.Color.blue())
        embed.add_field(name="⏱️ Current Slowmode", value=f"{self.COOLDOWN_SECONDS} seconds", inline=False)
        
        if self.bypass_users:
            bypass_members = []
            for user_id in self.bypass_users:
                member = ctx.guild.get_member(int(user_id))
                if member:
                    bypass_members.append(member.mention)
                else:
                    bypass_members.append(f"User ID: `{user_id}`")
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
                    bypass_roles.append(f"Role ID: `{role_id}`")
            embed.add_field(name="👥 Bypass Roles", value="\n".join(bypass_roles), inline=False)
        else:
            embed.add_field(name="👥 Bypass Roles", value="None", inline=False)
            
        await ctx.send(embed=embed)

    @commands.command(name="autosetuplevelroles")
    @commands.has_permissions(administrator=True)
    async def auto_setup_level_roles(self, ctx):
        # [Your existing role creation code here - unchanged]
        guild = ctx.guild
        created_roles = []
        existing_roles = []
        for level in self.levels:
            role_name = f"Level {level}"
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                try:
                    new_role = await guild.create_role(
                        name=role_name,
                        color=self.get_role_color(level),
                        permissions=self.get_role_permissions(level),
                        reason=f"Auto-setup level {level} role"
                    )
                    created_roles.append(new_role.name)
                except discord.Forbidden:
                    return await ctx.send("❌ I don't have permission to create roles!")
            else:
                try:
                    await role.edit(
                        color=self.get_role_color(level),
                        permissions=self.get_role_permissions(level)
                    )
                    existing_roles.append(role.name)
                except:
                    existing_roles.append(role.name + " (update failed)")
        
        if str(guild.id) not in self.level_roles:
            self.level_roles[str(guild.id)] = {}
        
        for level in self.levels:
            role = discord.utils.get(guild.roles, name=f"Level {level}")
            if role:
                self.level_roles[str(guild.id)][str(level)] = role.id
        
        self.save_role_data()
        
        embed = discord.Embed(title="✅ Level Roles Setup Complete", color=discord.Color.green())
        embed.add_field(name="Created Roles", value=str(len(created_roles)), inline=True)
        embed.add_field(name="Updated Existing Roles", value=str(len(existing_roles)), inline=True)
        if created_roles:
            embed.add_field(name="New Roles", value=", ".join(created_roles), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="removealllevelroles")
    @commands.has_permissions(administrator=True)
    async def remove_all_level_roles(self, ctx):
        guild = ctx.guild
        level_roles = [role for role in guild.roles if role.name in [f"Level {l}" for l in self.levels]]
        if not level_roles:
            return await ctx.send("❌ No level roles found.")
        
        deleted_count = 0
        for role in level_roles:
            try:
                await role.delete()
                deleted_count += 1
            except:
                pass

        if str(guild.id) in self.level_roles:
            del self.level_roles[str(guild.id)]
            self.save_role_data()

        await ctx.send(f"✅ Deleted {deleted_count} level roles.")

    @commands.command(name="autodeletelevelroles")
    @commands.has_permissions(administrator=True)
    async def auto_delete_level_roles(self, ctx, target=None, *, user_id=None):
        guild = ctx.guild
        if target is None:
            return await ctx.send("❌ Please specify: `user @User` or `userid 123456789`")
        
        target = target.lower()
        if target == "user":
            if not ctx.message.mentions:
                return await ctx.send("❌ Please mention a user.")
            member = ctx.message.mentions[0]
        elif target == "userid":
            if not user_id:
                return await ctx.send("❌ Please provide a user ID.")
            try:
                member = guild.get_member(int(user_id))
                if not member:
                    return await ctx.send("❌ User not found.")
            except:
                return await ctx.send("❌ Invalid user ID.")
        else:
            return await ctx.send("❌ Invalid option.")
        
        level_role_names = [f"Level {l}" for l in self.levels]
        level_roles_on_user = [role for role in member.roles if role.name in level_role_names]
        
        if not level_roles_on_user:
            return await ctx.send(f"ℹ️ {member.mention} has no level roles.")
        
        removed_count = 0
        for role in level_roles_on_user:
            try:
                await member.remove_roles(role)
                removed_count += 1
            except:
                pass
        
        await ctx.send(f"✅ Removed {removed_count} level roles from {member.mention}.")

    @commands.command(name="addlevelrole")
    @commands.has_permissions(administrator=True)
    async def add_level_role(self, ctx, level: int, role: discord.Role):
        if level not in self.levels:
            return await ctx.send(f"❌ Invalid level! Choose from: {', '.join(map(str, self.levels))}")
        if str(ctx.guild.id) not in self.level_roles:
            self.level_roles[str(ctx.guild.id)] = {}
        self.level_roles[str(ctx.guild.id)][str(level)] = role.id
        self.save_role_data()
        await ctx.send(f"✅ Added Level {level} -> {role.mention}")

    @commands.command(name="removelevelrole")
    @commands.has_permissions(administrator=True)
    async def remove_level_role(self, ctx, level: int):
        if str(ctx.guild.id) not in self.level_roles:
            return await ctx.send("❌ No level roles configured.")
        if str(level) in self.level_roles[str(ctx.guild.id)]:
            del self.level_roles[str(ctx.guild.id)][str(level)]
            self.save_role_data()
            await ctx.send(f"✅ Removed Level {level} mapping.")
        else:
            await ctx.send(f"❌ Level {level} is not configured.")

    @commands.command(name="addxp")
    @commands.has_permissions(administrator=True)
    async def add_xp(self, ctx, member: discord.Member, amount: int):
        if amount <= 0:
            return await ctx.send("❌ Must add positive XP.")
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        if guild_id not in self.level_data:
            self.level_data[guild_id] = {}
        if user_id not in self.level_data[guild_id]:
            self.level_data[guild_id][user_id] = {"xp": 0}
        
        self.level_data[guild_id][user_id]["xp"] += amount
        self.save_data()
        
        new_level = self.get_level_from_xp(self.level_data[guild_id][user_id]["xp"])
        await ctx.send(f"✅ Added **{amount} XP** to {member.mention}!\nThey are now Level {new_level}.")

    @commands.command(name="removexp")
    @commands.has_permissions(administrator=True)
    async def remove_xp(self, ctx, member: discord.Member, amount: int):
        if amount <= 0:
            return await ctx.send("❌ Must remove positive XP.")
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        if guild_id not in self.level_data or user_id not in self.level_data[guild_id]:
            return await ctx.send(f"❌ {member.mention} has no XP data.")
        
        current_xp = self.level_data[guild_id][user_id]["xp"]
        if current_xp < amount:
            return await ctx.send(f"❌ {member.mention} only has {current_xp:,} XP.")
        
        self.level_data[guild_id][user_id]["xp"] -= amount
        self.save_data()
        
        new_level = self.get_level_from_xp(self.level_data[guild_id][user_id]["xp"])
        await ctx.send(f"✅ Removed **{amount} XP** from {member.mention}!\nThey are now Level {new_level}.")

    # ==========================================
    # XP LISTENER
    # ==========================================

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        guild_id = str(message.guild.id)
        user_id = str(message.author.id)
        
        is_bypassed = False
        if user_id in self.bypass_users:
            is_bypassed = True
        else:
            for role in message.author.roles:
                if str(role.id) in self.bypass_roles:
                    is_bypassed = True
                    break
        
        if not is_bypassed:
            now = asyncio.get_event_loop().time()
            if user_id in self.xp_cooldowns:
                if now - self.xp_cooldowns[user_id] < self.COOLDOWN_SECONDS:
                    return
            self.xp_cooldowns[user_id] = now
        
        if guild_id not in self.level_data:
            self.level_data[guild_id] = {}
        if user_id not in self.level_data[guild_id]:
            self.level_data[guild_id][user_id] = {"xp": 0}
        
        xp_gained = self.calculate_xp_gain(message)
        old_xp = self.level_data[guild_id][user_id]["xp"]
        old_level = self.get_level_from_xp(old_xp)
        
        self.level_data[guild_id][user_id]["xp"] += xp_gained
        self.save_data()
        
        new_level = self.get_level_from_xp(self.level_data[guild_id][user_id]["xp"])
        
        if new_level > old_level:
            if new_level in self.levels:
                role_name = f"Level {new_level}"
                role = discord.utils.get(message.guild.roles, name=role_name)
                if role and role not in message.author.roles:
                    try:
                        await message.author.add_roles(role)
                        level_channel = message.guild.get_channel(self.level_channel_id) or message.channel
                        
                        embed = discord.Embed(
                            title=f"🎉 Level Up!",
                            description=f"{message.author.mention} reached **Level {new_level}**!",
                            color=self.get_role_color(new_level)
                        )
                        perms = self.get_role_permissions(new_level)
                        perm_list = []
                        if perms.attach_files: perm_list.append("📎 Send Images/GIFs/Files")
                        if perms.embed_links: perm_list.append("🔗 Embed Links")
                        if perm_list:
                            embed.add_field(name="Unlocked Perks", value="\n".join(perm_list), inline=False)
                        
                        await level_channel.send(embed=embed)
                    except:
                        pass

async def setup(bot):
    await bot.add_cog(LevelBot(bot))
