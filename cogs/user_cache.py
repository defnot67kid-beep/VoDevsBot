import discord
from discord.ext import commands, tasks
import pymongo
import os

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI environment variable is not set!")

client = pymongo.MongoClient(MONGO_URI)
db = client["vodevs_bot_data"]
user_cache_collection = db["user_cache"]

class UserCache(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache_users.start()

    @tasks.loop(minutes=30)
    async def cache_users(self):
        print(f"🔄 Caching members for {len(self.bot.guilds)} guilds...")
        
        for guild in self.bot.guilds:
            members_data = []
            for member in guild.members:
                if member.bot: continue
                
                status_str = "offline"
                if member.status == discord.Status.online: status_str = "online"
                elif member.status == discord.Status.idle: status_str = "idle"
                elif member.status == discord.Status.dnd: status_str = "dnd"

                members_data.append({
                    "id": str(member.id),
                    "name": member.display_name,
                    "avatar_url": str(member.display_avatar.url),
                    "status": status_str
                })
            
            user_cache_collection.update_one(
                {"guild_id": str(guild.id)},
                {"$set": {"members": members_data}},
                upsert=True
            )
            print(f"✅ Saved {len(members_data)} members for {guild.name}")

    @cache_users.before_loop
    async def before_cache_users(self):
        await self.bot.wait_until_ready()
        print("🚀 User Cache loop is starting...")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.cache_users()

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.cache_users()

async def setup(bot):
    await bot.add_cog(UserCache(bot))
