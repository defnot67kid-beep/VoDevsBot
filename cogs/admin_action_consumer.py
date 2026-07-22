import discord
from discord.ext import commands, tasks
import pymongo
import os
import asyncio

# ==========================================
# MONGODB SETUP
# ==========================================
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI environment variable is not set!")

client = pymongo.MongoClient(MONGO_URI)
db = client["vodevs_bot_data"]
admin_actions_collection = db["admin_actions"]

class AdminActionConsumer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.consume_actions.start()

    # ==========================================
    # BACKGROUND TASK: Check for actions every 5 seconds
    # ==========================================
    @tasks.loop(seconds=5)
    async def consume_actions(self):
        # Find 1 pending action
        action = admin_actions_collection.find_one({"status": "pending"})
        if not action:
            return

        print(f"⚠️ Processing Action: {action['type']}")

        try:
            guild_id = int(action.get('guild_id'))
            guild = self.bot.get_guild(guild_id)
            if not guild:
                print(f"❌ Guild {guild_id} not found! Marking as failed.")
                admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "failed", "error": "Guild not found"}})
                return

            # ===========================
            # Handle MOD ACTIONS
            # ===========================
            if action['type'] == 'mod_action':
                user_id = int(action.get('user_id'))
                member = guild.get_member(user_id)
                if not member:
                    print(f"❌ Member {user_id} not found! Marking as failed.")
                    admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "failed", "error": "Member not found"}})
                    return

                action_type = action.get('action')
                reason = action.get('reason', 'No reason provided.')
                duration = int(action.get('duration', 60))

                if action_type == 'kick':
                    await member.kick(reason=reason)
                elif action_type == 'ban':
                    await member.ban(reason=reason)
                elif action_type == 'timeout':
                    await member.timeout(discord.utils.utcnow() + discord.timedelta(seconds=duration), reason=reason)
                elif action_type == 'mute':
                    muted_role = discord.utils.get(guild.roles, name="Muted")
                    if not muted_role:
                        raise Exception("No 'Muted' role exists. Please create one in Discord.")
                    await member.add_roles(muted_role, reason=reason)
                
                print(f"✅ Executed {action_type.upper()} on {member.display_name}")
                admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "completed"}})

            # ===========================
            # Handle ANNOUNCEMENTS
            # ===========================
            elif action['type'] == 'announcement':
                channel_id = int(action.get('channel_id', '0'))
                channel = guild.get_channel(channel_id)
                if not channel:
                    raise Exception(f"Channel {channel_id} not found.")

                content = action.get('content', '')
                await channel.send(content)
                print(f"✅ Sent announcement to {channel.name}")
                admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "completed"}})

            # ===========================
            # Handle POLLS 
            # ===========================
            elif action['type'] == 'poll':
                # Implementation for polls goes here
                print("✅ Poll action received (Placeholder)")
                admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "completed"}})

        except Exception as e:
            print(f"❌ Action Failed: {e}")
            admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "failed", "error": str(e)}})

    @consume_actions.before_loop
    async def before_consume_actions(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(AdminActionConsumer(bot))
