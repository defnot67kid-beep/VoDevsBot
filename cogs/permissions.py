import discord
from discord.ext import commands
import pymongo
import os

# ==========================================
# MONGODB SETUP (Uses the same DB as the rest of the bot)
# ==========================================
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI environment variable is not set!")

client = pymongo.MongoClient(MONGO_URI)
db = client["vodevs_bot_data"]
perms_collection = db["bot_permissions"]

class Permissions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==========================================
    # HELPER: Check if a user has a specific permission
    # ==========================================
    def has_permission(self, guild_id, user_id, required_level):
        """
        Checks if a user has a specific permission level.
        Levels: 'admin', 'mod', 'user'
        """
        doc = perms_collection.find_one({"guild_id": guild_id, "user_id": user_id})
        if doc:
            return doc.get("level") == required_level
        return False

    def has_role_permission(self, guild_id, role_id, required_level):
        """
        Checks if a role has a specific permission level.
        """
        doc = perms_collection.find_one({"guild_id": guild_id, "role_id": role_id})
        if doc:
            return doc.get("level") == required_level
        return False

    def check_permission(self, ctx, required_level):
        """
        Global checker for commands. Returns True if the user or their role has the required level.
        """
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)

        # 1. Check if the user explicitly has the level
        if self.has_permission(guild_id, user_id, required_level):
            return True

        # 2. Check if any of the user's roles have the level
        for role in ctx.author.roles:
            if self.has_role_permission(guild_id, str(role.id), required_level):
                return True

        return False

    # ==========================================
    # COMMAND: !botpermsallow
    # ==========================================
    @commands.command(name="botpermsallow")
    @commands.has_permissions(administrator=True)
    async def bot_perms_allow(self, ctx, target_type: str, level: str, *, target_id: str = None):
        """
        [Admin] Grants bot permissions to a User, UserID, or Role.
        Usage:
            !botpermsallow user admin @User
            !botpermsallow userid mod 123456789
            !botpermsallow role admin @Role
        Levels: admin, mod
        """
        guild_id = str(ctx.guild.id)
        target_type = target_type.lower()
        level = level.lower()

        if level not in ['admin', 'mod']:
            return await ctx.send("❌ Invalid level! Choose `admin` or `mod`.")

        if target_type == "user":
            if not ctx.message.mentions:
                return await ctx.send("❌ Please mention a user: `!botpermsallow user admin @User`")
            member = ctx.message.mentions[0]
            user_id = str(member.id)

            perms_collection.update_one(
                {"guild_id": guild_id, "user_id": user_id},
                {"$set": {"level": level}},
                upsert=True
            )
            await ctx.send(f"✅ Granted **{level}** permissions to {member.mention}!")

        elif target_type == "userid":
            if not target_id:
                return await ctx.send("❌ Please provide a user ID: `!botpermsallow userid admin 123456789`")
            try:
                user_id = str(int(target_id))
                perms_collection.update_one(
                    {"guild_id": guild_id, "user_id": user_id},
                    {"$set": {"level": level}},
                    upsert=True
                )
                await ctx.send(f"✅ Granted **{level}** permissions to User ID `{user_id}`!")
            except ValueError:
                return await ctx.send("❌ Invalid User ID. Please provide a valid numeric ID.")

        elif target_type == "role":
            if not ctx.message.role_mentions:
                return await ctx.send("❌ Please mention a role: `!botpermsallow role admin @Role`")
            role = ctx.message.role_mentions[0]
            role_id = str(role.id)

            perms_collection.update_one(
                {"guild_id": guild_id, "role_id": role_id},
                {"$set": {"level": level}},
                upsert=True
            )
            await ctx.send(f"✅ Granted **{level}** permissions to {role.mention}!")

        else:
            await ctx.send("❌ Invalid target type! Use: `user`, `userid`, or `role`.")

    # ==========================================
    # COMMAND: !botpermsremove
    # ==========================================
    @commands.command(name="botpermsremove")
    @commands.has_permissions(administrator=True)
    async def bot_perms_remove(self, ctx, target_type: str, *, target_id: str = None):
        """
        [Admin] Removes bot permissions from a User, UserID, or Role.
        Usage:
            !botpermsremove user @User
            !botpermsremove userid 123456789
            !botpermsremove role @Role
        """
        guild_id = str(ctx.guild.id)
        target_type = target_type.lower()

        if target_type == "user":
            if not ctx.message.mentions:
                return await ctx.send("❌ Please mention a user: `!botpermsremove user @User`")
            member = ctx.message.mentions[0]
            user_id = str(member.id)

            perms_collection.delete_one({"guild_id": guild_id, "user_id": user_id})
            await ctx.send(f"✅ Removed all bot permissions from {member.mention}!")

        elif target_type == "userid":
            if not target_id:
                return await ctx.send("❌ Please provide a user ID: `!botpermsremove userid 123456789`")
            try:
                user_id = str(int(target_id))
                perms_collection.delete_one({"guild_id": guild_id, "user_id": user_id})
                await ctx.send(f"✅ Removed all bot permissions from User ID `{user_id}`!")
            except ValueError:
                return await ctx.send("❌ Invalid User ID. Please provide a valid numeric ID.")

        elif target_type == "role":
            if not ctx.message.role_mentions:
                return await ctx.send("❌ Please mention a role: `!botpermsremove role @Role`")
            role = ctx.message.role_mentions[0]
            role_id = str(role.id)

            perms_collection.delete_one({"guild_id": guild_id, "role_id": role_id})
            await ctx.send(f"✅ Removed all bot permissions from {role.mention}!")

        else:
            await ctx.send("❌ Invalid target type! Use: `user`, `userid`, or `role`.")

    # ==========================================
    # COMMAND: !botpermslist
    # ==========================================
    @commands.command(name="botpermslist")
    @commands.has_permissions(administrator=True)
    async def bot_perms_list(self, ctx):
        """
        [Admin] Lists all users and roles with bot permissions.
        Usage: !botpermslist
        """
        guild_id = str(ctx.guild.id)
        results = perms_collection.find({"guild_id": guild_id})

        embed = discord.Embed(
            title="📋 Bot Permissions List",
            color=discord.Color.blue()
        )

        admins = []
        mods = []

        for doc in results:
            level = doc.get("level")
            if "user_id" in doc:
                user_id = doc["user_id"]
                member = ctx.guild.get_member(int(user_id))
                name = member.mention if member else f"User ID: `{user_id}`"
            elif "role_id" in doc:
                role_id = doc["role_id"]
                role = ctx.guild.get_role(int(role_id))
                name = role.mention if role else f"Role ID: `{role_id}`"
            else:
                continue

            if level == "admin":
                admins.append(name)
            elif level == "mod":
                mods.append(name)

        if admins:
            embed.add_field(name="🛡️ Admins", value="\n".join(admins), inline=False)
        else:
            embed.add_field(name="🛡️ Admins", value="None", inline=False)

        if mods:
            embed.add_field(name="🛠️ Mods", value="\n".join(mods), inline=False)
        else:
            embed.add_field(name="🛠️ Mods", value="None", inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Permissions(bot))
