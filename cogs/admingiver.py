import discord
from discord.ext import commands
import pymongo
import os
import secrets
import hashlib

# ==========================================
# MONGODB SETUP
# ==========================================
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI environment variable is not set!")

client = pymongo.MongoClient(MONGO_URI)
db = client["vodevs_bot_data"]
invites_collection = db["admin_invites"]
admins_collection = db["admins"]
owner_secrets_collection = db["owner_secrets"]
# Note: server_meta is used by the server_cache.py cog to store roles/channels

class AdminGiver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==========================================
    # COMMAND: !generatelink
    # ==========================================
    @commands.command(name="generatelink")
    @commands.has_permissions(administrator=True)
    async def generate_link(self, ctx, *, target: str):
        """
        [Admin] Generates a secure admin invite link for a user.
        Usage: !generatelink @User
        """
        try:
            converter = commands.MemberConverter()
            member = await converter.convert(ctx, target)
        except:
            try:
                user_id = int(target)
                member = ctx.guild.get_member(user_id)
                if not member:
                    try:
                        member = await self.bot.fetch_user(user_id)
                    except:
                        return await ctx.send("❌ Could not find that user.")
            except:
                return await ctx.send("❌ Invalid target. Please mention a user or provide a User ID.")

        invite_token = secrets.token_urlsafe(32)
        invites_collection.update_one(
            {"token": invite_token},
            {"$set": {"discord_id": str(member.id), "used": False}},
            upsert=True
        )

        dashboard_url = os.getenv("DASHBOARD_URL", "https://vodevs-dashboard-production.up.railway.app")
        invite_link = f"{dashboard_url}/admin/signup/{invite_token}"

        try:
            await member.send(
                f"🔐 **You have been invited to become an Admin!**\n\n"
                f"Click the link below to verify your identity and create your admin account:\n"
                f"{invite_link}\n\n"
                f"*This link is one-time use and secure.*"
            )
            await ctx.send(f"✅ Invite link successfully sent to **{member.display_name}**!")
        except discord.Forbidden:
            await ctx.send(f"❌ Could not DM {member.display_name}. Link: {invite_link}")

    # ==========================================
    # COMMAND: !ownerlink (Owner Only)
    # ==========================================
    @commands.command(name="ownerlink")
    async def owner_link(self, ctx):
        # Hardcoded Owner ID Check
        if str(ctx.author.id) != "1516568962966753291":
            return await ctx.send("❌ You are not the owner of this bot.")

        # Generate the secure token
        raw_token = secrets.token_urlsafe(64)
        owner_token = hashlib.sha256(f"{raw_token}-1516568962966753291".encode()).hexdigest()

        # Save to Database (NOW INCLUDING THE GUILD ID)
        owner_secrets_collection.update_one(
            {"owner_id": "1516568962966753291"}, 
            {"$set": {
                "token": owner_token,
                "guild_id": str(ctx.guild.id)  # <--- SAVE THE SERVER ID HERE
            }}, 
            upsert=True
        )

        dashboard_url = os.getenv("DASHBOARD_URL", "https://vodevs-dashboard-production.up.railway.app")
        invite_link = f"{dashboard_url}/owner/{owner_token}"

        await ctx.send(
            f"🛡️ **Bot Owner Control Panel Generated!**\n\n"
            f"🔗 `{invite_link}`\n\n"
            f"*Keep this link extremely secret. This token is a 64-byte SHA256 hash.*"
        )

async def setup(bot):
    await bot.add_cog(AdminGiver(bot))
