import discord
from discord.ext import commands, tasks
import pymongo
import os

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

    @tasks.loop(seconds=5)
    async def consume_actions(self):
        action = admin_actions_collection.find_one({"status": "pending"})
        if not action:
            return

        print(f"⚠️ Processing Action: {action['type']}")

        try:
            guild_id = int(action.get('guild_id'))
            guild = self.bot.get_guild(guild_id)
            if not guild:
                admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "failed", "error": "Guild not found"}})
                return

            # ========================================
            # 1. MOD ACTIONS (Kick, Ban, Timeout, Mute)
            # ========================================
            if action['type'] == 'mod_action':
                user_id = int(action.get('user_id'))
                member = guild.get_member(user_id)
                
                if not member:
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
                    # FIX: Correct duration logic
                    await member.timeout(discord.utils.utcnow() + discord.utils.timedelta(seconds=duration), reason=reason)
                elif action_type == 'mute':
                    # FIX: Safe Mute logic
                    muted_role = discord.utils.get(guild.roles, name="Muted")
                    if not muted_role:
                        raise Exception("No 'Muted' role exists. Please create a role named 'Muted' in your server.")
                    await member.add_roles(muted_role, reason=reason)
                
                print(f"✅ Executed {action_type.upper()} on {member.display_name}")

            # ========================================
            # 2. ANNOUNCEMENTS
            # ========================================
            elif action['type'] == 'announcement':
                channel_id = int(action.get('channel_id', '0'))
                channel = guild.get_channel(channel_id)
                if not channel:
                    raise Exception(f"Channel {channel_id} not found.")
                await channel.send(action.get('content', ''))
                print(f"✅ Sent announcement to {channel.name}")

            # ========================================
            # 3. REACTION ROLES (NEW!)
            # ========================================
            elif action['type'] == 'reaction_role':
                channel_id = int(action.get('channel_id'))
                channel = guild.get_channel(channel_id)
                if not channel:
                    raise Exception(f"Channel {channel_id} not found.")

                title = action.get('title', 'Get Roles!')
                description = action.get('description', 'React below to get roles.')
                color = discord.Color.from_str(action.get('color', '#5865F2'))
                roles_list = action.get('roles', [])

                embed = discord.Embed(title=title, description=description, color=color)
                embed.set_footer(text="React to this message to receive roles!")

                role_text = ""
                for item in roles_list:
                    role = guild.get_role(item['role_id'])
                    role_mention = role.mention if role else "**Deleted Role**"
                    role_text += f"{item['emoji']} {role_mention} — *{item['description']}*\n"

                embed.add_field(name="Available Roles", value=role_text if role_text else "No roles added yet.", inline=False)

                # Send the message to Discord
                sent_msg = await channel.send(embed=embed)
                
                # Add the reactions
                for item in roles_list:
                    try:
                        await sent_msg.add_reaction(item['emoji'])
                    except:
                        pass
                
                print(f"✅ Created Reaction Role menu in {channel.name}")

            # ========================================
            # 4. POLLS (NEW!)
            # ========================================
            elif action['type'] == 'poll':
                channel_id = int(action.get('channel_id', '0'))
                channel = guild.get_channel(channel_id)
                if not channel:
                    raise Exception(f"Channel {channel_id} not found.")

                question = action.get('question', 'Poll')
                options = action.get('options', [])
                duration_seconds = int(action.get('duration', 600)) # Default 10 mins
                poll_type = action.get('poll_type', 'single')

                if len(options) < 2:
                    raise Exception("At least 2 options required for a poll.")

                # Formatting the poll embed
                embed = discord.Embed(
                    title=f"📊 {question}",
                    description="\n".join([f"**{i+1}.** {opt}" for i, opt in enumerate(options)]),
                    color=discord.Color.blurple()
                )
                embed.set_footer(text=f"Type: {'Multiple' if poll_type == 'multiple' else 'Single'} Choice")

                # Send the poll 
                sent_msg = await channel.send(embed=embed)
                
                # Add reactions as "votes"
                # (1️⃣, 2️⃣, 3️⃣, etc)
                emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
                for i in range(len(options)):
                    if i < len(emojis):
                        await sent_msg.add_reaction(emojis[i])

                print(f"✅ Created Poll in {channel.name}")

            # ========================================
            # MARK AS COMPLETED
            # ========================================
            admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "completed"}})

        except Exception as e:
            print(f"❌ Action Failed: {e}")
            admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "failed", "error": str(e)}})

    @consume_actions.before_loop
    async def before_consume_actions(self):
        await self.bot.wait_until_ready()
        print("🚀 Admin Action Consumer is starting...")

async def setup(bot):
    await bot.add_cog(AdminActionConsumer(bot))
