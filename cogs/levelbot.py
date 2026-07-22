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
# SLASH COMMAND GROUP (Allows grouping like /level ...)
# ==========================================
class LevelGroup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==========================================
    # HELPER: Permission Check for Admins
    # ==========================================
    async def admin_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions!", ephemeral=True)
            return False
        return True

    # ==========================================
    # HELPER: Build the Image URL
    # ==========================================
    async def _build_rank_image(self, interaction, user_id, current_xp, current_level, rank):
        clean_name = ''.join(c for c in interaction.user.display_name if c.isalnum() or c in (' ', '-', '_', '.', '#'))
        dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:8000")
        avatar_url = interaction.user.display_avatar.with_format("png").replace(size=512).url
        
        next_level_xp = self.get_xp_needed(current_level + 1)
        prev_level_xp = self.get_xp_needed(current_level)
        xp_in_level = current_xp - prev_level_xp
        xp_needed_for_next = next_level_xp - prev_level_xp
        
        if xp_needed_for_next == 0: progress = 1.0
        else: progress = xp_in_level / xp_needed_for_next
        
        image_url = f"{dashboard_url}/get_card/{interaction.guild.id}/{user_id}?name={clean_name}&xp={int(current_xp)}&next_xp={int(next_level_xp)}&progress={progress:.2f}&avatar={avatar_url}&level={current_level}&rank={rank}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status == 200:
                        image_data = await resp.read()
                        return discord.File(fp=io.BytesIO(image_data), filename="rank.png")
        except Exception as e:
            print(f"❌ Error fetching rank card: {e}")
            return None
        return None

    # ==========================================
    # SLASH COMMANDS
    # ==========================================

    @app_commands.command(name="level", description="Check your current level and XP progress")
    @app_commands.guild_only()
    async def slash_level(self, interaction: discord.Interaction, member: discord.Member = None):
        if member is None:
            member = interaction.user

        guild_id = str(interaction.guild.id)
        user_id = str(member.id)

        doc = levels_collection.find_one({"guild_id": guild_id, "user_id": user_id})
        if not doc:
            await interaction.response.send_message(f"❌ {member.mention} hasn't chatted enough to have a rank yet!", ephemeral=True)
            return

        current_xp = doc["xp"]
        current_level = self.get_level_from_xp(current_xp)
        rank = self.get_rank(guild_id, user_id)

        await interaction.response.defer()
        
        file = await self._build_rank_image(interaction, user_id, current_xp, current_level, rank)
        if file:
            view = CardButton(os.getenv("DASHBOARD_URL", "http://localhost:8000"))
            await interaction.followup.send(file=file, view=view)
        else:
            await interaction.followup.send("❌ Failed to generate rank card. Check dashboard logs.")

    @app_commands.command(name="leaderboard", description="Show the top 10 levelers in the server")
    @app_commands.guild_only()
    async def slash_leaderboard(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        
        count = levels_collection.count_documents({"guild_id": guild_id})
        if count == 0:
            await interaction.response.send_message("❌ No level data for this server yet!", ephemeral=True)
            return

        results = levels_collection.find({"guild_id": guild_id}).sort("xp", pymongo.DESCENDING).limit(10)
        sorted_users = list(results)
        
        dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:8000")
        web_url = f"{dashboard_url.rstrip('/')}/leaderboard/{guild_id}"
        
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(label="View leaderboard", style=discord.ButtonStyle.link, url=web_url, emoji="📊")
        )
        
        embed = discord.Embed(title=f"{interaction.guild.name}", color=discord.Color.dark_embed())
        leaderboard_text = ""
        for i, doc in enumerate(sorted_users, 1):
            member = interaction.guild.get_member(int(doc["user_id"]))
            if member:
                level = self.get_level_from_xp(doc["xp"])
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
                leaderboard_text += f"**{medal}** • `@{member.display_name}` • **LVL: {level}**\n"
        
        embed.description = leaderboard_text
        embed.set_footer(text=f"{count} members • Overall XP")
        
        await interaction.response.send_message(embed=embed, view=view)

    # ==========================================
    # ADMIN SLASH COMMANDS
    # ==========================================

    @app_commands.command(name="xpslowmode", description="[Admin] Set the global XP cooldown in seconds")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_xpslowmode(self, interaction: discord.Interaction, seconds: int):
        if not await self.admin_check(interaction): return
        self.COOLDOWN_SECONDS = seconds
        self.save_config()
        msg = "**DISABLED** (0 seconds). Users can gain XP instantly!" if seconds == 0 else f"set to **{seconds}** seconds."
        await interaction.response.send_message(f"✅ XP Slowmode {msg}", ephemeral=True)

    @app_commands.command(name="xpslowbypass", description="[Admin] Toggle XP cooldown bypass for a User or Role")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        target_type="'user' or 'role'",
        target="The user or role to bypass"
    )
    async def slash_xpslowbypass(self, interaction: discord.Interaction, target_type: str, target: str):
        if not await self.admin_check(interaction): return
        target_type = target_type.lower()
        guild_id = str(interaction.guild.id)

        if target_type == "user":
            # Convert the string target to a Member
            try:
                converter = commands.MemberConverter()
                member = await converter.convert(interaction, target)
                user_id = str(member.id)
            except:
                await interaction.response.send_message("❌ Invalid user. Please mention a valid user.", ephemeral=True)
                return

            if user_id in self.bypass_users:
                self.bypass_users.remove(user_id); self.save_config()
                await interaction.response.send_message(f"✅ Removed {member.mention} from bypass.", ephemeral=True)
            else:
                self.bypass_users.add(user_id); self.save_config()
                await interaction.response.send_message(f"✅ Added {member.mention} to bypass.", ephemeral=True)

        elif target_type == "role":
            # Convert the string target to a Role
            try:
                converter = commands.RoleConverter()
                role = await converter.convert(interaction, target)
                role_id = str(role.id)
            except:
                await interaction.response.send_message("❌ Invalid role. Please mention a valid role.", ephemeral=True)
                return

            if role_id in self.bypass_roles:
                self.bypass_roles.remove(role_id); self.save_config()
                await interaction.response.send_message(f"✅ Removed {role.mention} from bypass.", ephemeral=True)
            else:
                self.bypass_roles.add(role_id); self.save_config()
                await interaction.response.send_message(f"✅ Added {role.mention} to bypass.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Invalid target type! Use `user` or `role`.", ephemeral=True)

    @app_commands.command(name="xpslowlist", description="[Admin] List users and roles that bypass the XP cooldown")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_xpslowlist(self, interaction: discord.Interaction):
        if not await self.admin_check(interaction): return
        embed = discord.Embed(title="⚡ XP Slowmode Bypass List", color=discord.Color.blue())
        embed.add_field(name="⏱️ Current Slowmode", value=f"{self.COOLDOWN_SECONDS} seconds", inline=False)
        if self.bypass_users:
            bypass_members = []
            for user_id in self.bypass_users:
                member = interaction.guild.get_member(int(user_id))
                bypass_members.append(member.mention if member else f"User ID: `{user_id}`")
            embed.add_field(name="👤 Bypass Users", value="\n".join(bypass_members), inline=False)
        else:
            embed.add_field(name="👤 Bypass Users", value="None", inline=False)
        if self.bypass_roles:
            bypass_roles = []
            for role_id in self.bypass_roles:
                role = interaction.guild.get_role(int(role_id))
                bypass_roles.append(role.mention if role else f"Role ID: `{role_id}`")
            embed.add_field(name="👥 Bypass Roles", value="\n".join(bypass_roles), inline=False)
        else:
            embed.add_field(name="👥 Bypass Roles", value="None", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setlevelchannel", description="[Admin] Set the channel where Level-Up announcements are sent")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_setlevelchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await self.admin_check(interaction): return
        self.level_channel_id = channel.id
        self.save_config()
        await interaction.response.send_message(f"✅ Level-Up announcements will now be sent to {channel.mention}!", ephemeral=True)

    @app_commands.command(name="addxp", description="[Admin] Manually add XP to a user (uses a number)")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_addxp(self, interaction: discord.Interaction, member: discord.Member, amount: float):
        if not await self.admin_check(interaction): return
        if amount > 10000000:
            await interaction.response.send_message("❌ You cannot add more than 10,000,000 XP at once!", ephemeral=True)
            return

        await self._add_xp_to_db(str(interaction.guild.id), str(member.id), amount)
        await interaction.response.send_message(f"✅ Successfully added **{amount} XP** to `{member.display_name}`. (No ping sent)", ephemeral=True)

    @app_commands.command(name="removexp", description="[Admin] Manually remove XP from a user")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_removexp(self, interaction: discord.Interaction, member: discord.Member, amount: float):
        if not await self.admin_check(interaction): return
        guild_id = str(interaction.guild.id)
        user_id = str(member.id)
        
        doc = levels_collection.find_one({"guild_id": guild_id, "user_id": user_id})
        if not doc:
            await interaction.response.send_message("❌ User doesn't have any XP to remove!", ephemeral=True)
            return
        
        current_xp = doc["xp"]
        if current_xp < amount:
            await interaction.response.send_message(f"❌ User only has {current_xp:,} XP. You cannot remove {amount} XP!", ephemeral=True)
            return

        new_xp = round(current_xp - amount)
        if new_xp < 0: new_xp = 0
        levels_collection.update_one({"guild_id": guild_id, "user_id": user_id}, {"$set": {"xp": new_xp}})
        
        new_level = self.get_level_from_xp(new_xp)
        await interaction.response.send_message(f"✅ Removed **{amount} XP** from `{member.display_name}`.\nThey are now at Level {new_level}.", ephemeral=True)

    @app_commands.command(name="autosetuplevelroles", description="[Admin] Automatically creates level roles up to Level 100")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_autosetuplevelroles(self, interaction: discord.Interaction):
        if not await self.admin_check(interaction): return
        guild = interaction.guild
        created_roles, existing_roles = [], []
        for level in self.levels:
            role_name = f"Level {level}"
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                try:
                    new_role = await guild.create_role(name=role_name, color=self.get_role_color(level), permissions=self.get_role_permissions(level))
                    created_roles.append(new_role.name)
                except:
                    await interaction.response.send_message("❌ Missing perms to create roles.", ephemeral=True)
                    return
            else:
                try:
                    await role.edit(color=self.get_role_color(level), permissions=self.get_role_permissions(level))
                    existing_roles.append(role.name)
                except:
                    await interaction.response.send_message(f"⚠️ Could not update {role.name}", ephemeral=True)
        
        for level in self.levels:
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
        if not await self.admin_check(interaction): return
        guild = interaction.guild
        level_roles = [role for role in guild.roles if role.name in [f"Level {l}" for l in self.levels]]
        if not level_roles:
            await interaction.response.send_message("❌ No level roles found.", ephemeral=True)
            return
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
        if not await self.admin_check(interaction): return
        if level not in self.levels:
            await interaction.response.send_message(f"❌ Invalid level! Choose from: {', '.join(map(str, self.levels))}", ephemeral=True)
            return
        roles_collection.update_one({"guild_id": str(interaction.guild.id), "level": level}, {"$set": {"role_id": role.id}}, upsert=True)
        await interaction.response.send_message(f"✅ Added Level {level} -> {role.mention}", ephemeral=True)

    @app_commands.command(name="removelevelrole", description="[Admin] Remove a level role mapping")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_removelevelrole(self, interaction: discord.Interaction, level: int):
        if not await self.admin_check(interaction): return
        roles_collection.delete_one({"guild_id": str(interaction.guild.id), "level": level})
        await interaction.response.send_message(f"✅ Removed Level {level} mapping.", ephemeral=True)

    @app_commands.command(name="listlevelroles", description="[Admin] List all mapped level roles")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def slash_listlevelroles(self, interaction: discord.Interaction):
        if not await self.admin_check(interaction): return
        results = roles_collection.find({"guild_id": str(interaction.guild.id)}).sort("level", 1)
        embed = discord.Embed(title="📋 Level Roles", color=discord.Color.blue())
        for doc in results:
            level = doc["level"]
            role_id = doc["role_id"]
            role = interaction.guild.get_role(role_id)
            if role:
                perms = self.get_role_permissions(level)
                perm_list = []
                if perms.attach_files: perm_list.append("📎 Files")
                if perms.embed_links: perm_list.append("🔗 Embeds")
                embed.add_field(name=f"Level {level}", value=f"{role.mention}\n*{', '.join(perm_list) if perm_list else 'Base'}*", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================
# KEEP YOUR EXISTING NON-SLASH COMMANDS FOR BACKUP (Optional)
# ==========================================
# You can copy your original !level, !leaderboard, etc., from your old file here
# so the bot supports BOTH prefix and slash commands!
# (If you want to keep prefix support, uncomment the code below)

"""
    @commands.command(name="level", aliases=["lvl"])
    async def level(self, ctx, *, member: discord.Member = None):
        ... (your original prefix logic here) ...
"""

async def setup(bot):
    await bot.add_cog(LevelBot(bot))
