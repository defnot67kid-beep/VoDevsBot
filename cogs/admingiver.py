import discord
from discord.ext import commands
import pymongo
import os
import secrets
import asyncio

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
        Usage: !generatelink @User  OR  !generatelink UserID  OR  !generatelink username
        """
        # 1. Resolve the target to a Member object
        try:
            converter = commands.MemberConverter()
            member = await converter.convert(ctx, target)
        except:
            # Try as User ID
            try:
                user_id = int(target)
                member = ctx.guild.get_member(user_id)
                if not member:
                    # Fetch the user from Discord API
                    try:
                        member = await self.bot.fetch_user(user_id)
                    except:
                        return await ctx.send("❌ Could not find that user.")
            except:
                return await ctx.send("❌ Invalid target. Please mention a user, provide a User ID, or type a username.")

        # 2. Generate a secure, cryptographically random token
        invite_token = secrets.token_urlsafe(32)

        # 3. Save to MongoDB
        invites_collection.update_one(
            {"token": invite_token},
            {"$set": {
                "discord_id": str(member.id),
                "used": False
            }},
            upsert=True
        )

        # 4. Build the link
        dashboard_url = os.getenv("DASHBOARD_URL", "https://vodevs-dashboard-production.up.railway.app")
        invite_link = f"{dashboard_url}/admin/signup/{invite_token}"

        # 5. DM the user
        try:
            await member.send(
                f"🔐 **You have been invited to become an Admin!**\n\n"
                f"Click the link below to verify your identity and create your admin account:\n"
                f"{invite_link}\n\n"
                f"*This link is one-time use and secure.*"
            )
            await ctx.send(f"✅ Invite link successfully sent to **{member.display_name}**!")
        except discord.Forbidden:
            await ctx.send(f"❌ Could not DM {member.display_name}. They have DMs disabled. Here is the link:\n{invite_link}")

    # ==========================================
    # CLEANUP: Remove expired invites (Optional, run periodically)
    # ==========================================
    @commands.command(name="cleaninvites")
    @commands.has_permissions(administrator=True)
    async def clean_invites(self, ctx):
        """Deletes all used invites from the database."""
        result = invites_collection.delete_many({"used": True})
        await ctx.send(f"✅ Cleaned up {result.deleted_count} used invite links.")

async def setup(bot):
    await bot.add_cog(AdminGiver(bot))
