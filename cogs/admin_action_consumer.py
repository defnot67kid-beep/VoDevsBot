import discord
from discord.ext import commands, tasks
import pymongo
import os
from datetime import timedelta

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI environment variable is not set!")

client = pymongo.MongoClient(MONGO_URI)
db = client["vodevs_bot_data"]
admin_actions_collection = db["admin_actions"]
reaction_roles_collection = db["reaction_roles"]
server_configs_collection = db["server_configs"]

def parse_duration(text):
    text = text.lower().strip()
    if text.endswith("s"): return int(text[:-1])
    elif text.endswith("m"): return int(text[:-1]) * 60
    elif text.endswith("h"): return int(text[:-1]) * 3600
    elif text.endswith("d"): return int(text[:-1]) * 86400
    try: return int(text)
    except ValueError: return 600

class AdminActionConsumer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.consume_actions.start()

    def cog_unload(self):
        self.consume_actions.cancel()

    @tasks.loop(seconds=5)
    async def consume_actions(self):
        action = admin_actions_collection.find_one_and_update(
            {"status": "pending"},
            {"$set": {"status": "processing"}}
        )
        if not action: return

        print(f"⚠️ [BOT] Processing Action: {action['type']}")
        try:
            guild_id = int(action.get('guild_id'))
            guild = self.bot.get_guild(guild_id)
            if not guild:
                admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "failed", "error": "Guild not found"}})
                return

            # ==========================================
            # 1. MOD ACTIONS (Kick, Ban, Unban, Timeout, Mute, Warn)
            # ==========================================
            if action['type'] == 'mod_action':
                user_id = int(action.get('user_id'))
                member = guild.get_member(user_id)
                if member is None:
                    try: member = await guild.fetch_member(user_id)
                    except discord.NotFound:
                        admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "failed", "error": "Member not found"}})
                        return

                action_type = action.get('action')
                reason = action.get('reason', 'No reason provided.')
                duration = int(action.get('duration', 60))

                try:
                    if action_type == 'kick': await member.kick(reason=reason)
                    elif action_type == 'ban': await member.ban(reason=reason)
                    elif action_type == 'unban':
                        try: await guild.unban(discord.Object(id=user_id), reason=reason)
                        except discord.NotFound: raise Exception("User is not banned.")
                    elif action_type == 'timeout':
                        await member.timeout(discord.utils.utcnow() + timedelta(seconds=duration), reason=reason)
                    elif action_type == 'mute':
                        await member.timeout(discord.utils.utcnow() + timedelta(seconds=duration), reason=reason)
                    elif action_type == 'warn':
                        # =====================================================
                        # SIMPLE WARNING LOGGING (Does NOT touch moderation_elite)
                        # =====================================================
                        print(f"✅ [BOT] Executed WARN on {member.display_name}")
                        
                        # Get the configured warn channel
                        config = server_configs_collection.find_one({"guild_id": str(guild.id)})
                        warn_channel_id = config.get("warn_channel_id") if config else None
                        
                        if warn_channel_id:
                            warn_channel = guild.get_channel(int(warn_channel_id))
                            if warn_channel and isinstance(warn_channel, discord.TextChannel):
                                embed = discord.Embed(
                                    title="⚠️ User Warned",
                                    description=f"**User:** {member.mention}\n**Reason:** {reason}",
                                    color=discord.Color.orange()
                                )
                                embed.set_footer(text=f"Moderator: Dashboard")
                                await warn_channel.send(embed=embed)
                            else:
                                print(f"⚠️ Warn channel {warn_channel_id} not found or invalid.")
                        else:
                            print("⚠️ No warn channel configured. Go to the Owner Panel to set one.")
                            
                except discord.Forbidden: raise Exception("Bot missing permissions.")
                except discord.NotFound: raise Exception("User/Role not found.")
                
                if action_type != 'warn':
                    print(f"✅ [BOT] Executed {action_type.upper()} on {member.display_name}")

            # ==========================================
            # 2. ANNOUNCEMENTS
            # ==========================================
            elif action['type'] == 'announcement':
                channel_id = int(action.get('channel_id', 0))
                channel = guild.get_channel(channel_id)
                if not channel or not isinstance(channel, discord.TextChannel): raise Exception("Invalid text channel.")
                await channel.send(action.get('content', ''))
                print(f"✅ [BOT] Sent announcement to {channel.name}")

            # ==========================================
            # 3. REACTION ROLES (Create Menu)
            # ==========================================
            elif action['type'] == 'reaction_role':
                channel_id = int(action.get('channel_id'))
                channel = guild.get_channel(channel_id)
                if not channel or not isinstance(channel, discord.TextChannel): raise Exception("Invalid text channel.")
                
                try: color = discord.Color.from_str(action.get('color', '#5865F2'))
                except: color = discord.Color.blurple()
                
                title = action.get('title', 'Get Roles!')
                description = action.get('description', 'React below to get roles.')
                roles_list = action.get('roles', [])

                embed = discord.Embed(title=title, description=description, color=color)
                embed.set_footer(text="React to this message to receive roles!")

                role_text = ""
                for item in roles_list:
                    role = guild.get_role(item['role_id'])
                    role_mention = role.mention if role else "**Deleted Role**"
                    role_text += f"{item['emoji']} {role_mention} — *{item['description']}*\n"
                embed.add_field(name="Available Roles", value=role_text if role_text else "No roles added yet.", inline=False)

                sent_msg = await channel.send(embed=embed)
                for item in roles_list:
                    try: await sent_msg.add_reaction(item['emoji'])
                    except: pass
                
                reaction_roles_collection.insert_one({
                    "guild_id": str(guild.id), "channel_id": str(channel.id),
                    "message_id": str(sent_msg.id), "roles": roles_list
                })
                print(f"✅ [BOT] Created Reaction Role menu in {channel.name}")

            # ==========================================
            # 4. ADD REACTION ROLE (Add to existing menu)
            # ==========================================
            elif action['type'] == 'add_reaction_role':
                message_id = action.get('message_id')
                rr_data = reaction_roles_collection.find_one({"message_id": message_id})
                if not rr_data: raise Exception("Reaction Role menu not found.")
                new_role = {"emoji": action['emoji'], "role_id": action['role_id'], "description": action.get('description', '')}
                reaction_roles_collection.update_one({"message_id": message_id}, {"$push": {"roles": new_role}})
                try:
                    channel = guild.get_channel(int(rr_data['channel_id']))
                    if channel:
                        msg = await channel.fetch_message(int(message_id))
                        await msg.add_reaction(action['emoji'])
                        print(f"✅ Added reaction {action['emoji']} to menu {message_id}")
                except: pass
                print(f"✅ Added role to reaction menu {message_id}")

            # ==========================================
            # 5. POLLS
            # ==========================================
            elif action['type'] == 'poll':
                channel_id = int(action.get('channel_id', 0))
                channel = guild.get_channel(channel_id)
                if not channel or not isinstance(channel, discord.TextChannel): raise Exception("Invalid text channel.")

                question = action.get('question', 'Poll')
                options = action.get('options', [])
                duration_seconds = parse_duration(action.get('duration', '10m'))
                poll_type = action.get('poll_type', 'single')
                if len(options) < 2: raise Exception("At least 2 options required.")

                embed = discord.Embed(
                    title=f"📊 {question}",
                    description="\n".join([f"**{i+1}.** {opt}" for i, opt in enumerate(options)]),
                    color=discord.Color.blurple()
                )
                embed.set_footer(text=f"Type: {'Multiple' if poll_type == 'multiple' else 'Single'} Choice")
                sent_msg = await channel.send(embed=embed)
                emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
                for i in range(len(options)):
                    if i < len(emojis): await sent_msg.add_reaction(emojis[i])
                print(f"✅ [BOT] Created Poll in {channel.name}")

            admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "completed"}})

        except Exception as e:
            print(f"❌ [BOT] Action Failed: {e}")
            admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "failed", "error": str(e)}})

    @consume_actions.before_loop
    async def before_consume_actions(self):
        await self.bot.wait_until_ready()
        print("🚀 [BOT] Admin Action Consumer is starting...")

    @consume_actions.after_loop
    async def after_consume_actions(self):
        if self.consume_actions.is_being_cancelled(): print("⚠️ [BOT] Admin Action Consumer loop was cancelled.")

    # ==========================================
    # REACTION ROLE EVENT LISTENERS
    # ==========================================
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id: return
        rr_data = reaction_roles_collection.find_one({"message_id": str(payload.message_id)})
        if not rr_data: return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        member = guild.get_member(payload.user_id)
        if not member:
            try: member = await guild.fetch_member(payload.user_id)
            except: return
        emoji_str = str(payload.emoji)
        for role_data in rr_data["roles"]:
            if role_data["emoji"] == emoji_str:
                role = guild.get_role(role_data["role_id"])
                if role and role not in member.roles:
                    try: await member.add_roles(role, reason="Reaction Role")
                    except: pass
                break

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id: return
        rr_data = reaction_roles_collection.find_one({"message_id": str(payload.message_id)})
        if not rr_data: return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        member = guild.get_member(payload.user_id)
        if not member:
            try: member = await guild.fetch_member(payload.user_id)
            except: return
        emoji_str = str(payload.emoji)
        for role_data in rr_data["roles"]:
            if role_data["emoji"] == emoji_str:
                role = guild.get_role(role_data["role_id"])
                if role and role in member.roles:
                    try: await member.remove_roles(role, reason="Reaction Role Removed")
                    except: pass
                break

async def setup(bot):
    await bot.add_cog(AdminActionConsumer(bot))
