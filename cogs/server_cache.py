import discord
from discord.ext import commands
import pymongo
import os

# ==========================================
# MONGODB SETUP
# ==========================================
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI environment variable is not set!")

client = pymongo.MongoClient(MONGO_URI)
db = client["vodevs_bot_data"]
server_meta_collection = db["server_meta"]

class ServerCache(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==========================================
    # HELPER: Convert Role Color to Hex
    # ==========================================
    def color_to_hex(self, color):
        return '#{:06x}'.format(color.value)

    # ==========================================
    # HELPER: Save Server Data to MongoDB
    # ==========================================
    async def save_server_data(self, guild):
        """Grabs all Roles, Categories, and Channels and saves them."""
        
        # 1. Grab all Roles (excluding @everyone)
        roles_data = []
        for role in guild.roles:
            if role.name != "@everyone":
                roles_data.append({
                    "name": role.name,
                    "color": self.color_to_hex(role.color),
                    "position": role.position,
                    "id": role.id
                })
        # Sort roles by position (highest first)
        roles_data.sort(key=lambda x: x['position'], reverse=True)

        # 2. Grab Categories and Channels
        categories_data = []
        for category in guild.categories:
            channels_data = []
            for channel in category.channels:
                # Determine type
                c_type = "Text"
                if isinstance(channel, discord.VoiceChannel):
                    c_type = "Voice"
                elif isinstance(channel, discord.ForumChannel):
                    c_type = "Forum"
                
                channels_data.append({
                    "name": channel.name,
                    "type": c_type,
                    "id": channel.id
                })
            
            categories_data.append({
                "name": category.name,
                "id": category.id,
                "channels": channels_data
            })

        # 3. Save to MongoDB (Update if exists, otherwise Insert)
        server_meta_collection.update_one(
            {"guild_id": str(guild.id)},
            {"$set": {
                "guild_name": guild.name,
                "icon_url": str(guild.icon.url) if guild.icon else None,
                "roles": roles_data,
                "categories": categories_data
            }},
            upsert=True
        )
        print(f"✅ Saved server cache for: {guild.name}")

    # ==========================================
    # EVENT: On Bot Ready (Initial Cache)
    # ==========================================
    @commands.Cog.listener()
    async def on_ready(self):
        print("🔄 Caching all guild data...")
        for guild in self.bot.guilds:
            await self.save_server_data(guild)
        print("✅ Server Cache initialized!")

    # ==========================================
    # EVENTS: Update Cache on Changes
    # ==========================================
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        await self.save_server_data(role.guild)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        await self.save_server_data(role.guild)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        if before.name != after.name or before.color != after.color:
            await self.save_server_data(after.guild)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        await self.save_server_data(channel.guild)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        await self.save_server_data(channel.guild)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if before.name != after.name or before.type != after.type:
            await self.save_server_data(after.guild)

async def setup(bot):
    await bot.add_cog(ServerCache(bot))
