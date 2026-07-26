import discord
from discord.ext import commands, tasks
import pymongo
import os
from datetime import timedelta, datetime
from bson.objectid import ObjectId

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI environment variable is not set!")

client = pymongo.MongoClient(MONGO_URI)
db = client["vodevs_bot_data"]
admin_actions_collection = db["admin_actions"]
reaction_roles_collection = db["reaction_roles"]
warning_users = db["warning_users"]
server_configs = db["server_configs"]
ban_list_cache = db["ban_list_cache"]

# ==========================================
# HARDCODED CHANNELS & IMMUNITY CONFIG
# ==========================================
ACTION_IMAGE_CHANNEL_ID = 1526989768595083384  # WHERE ALL ACTION IMAGES GO
EMBED_LOG_CHANNEL_ID = 1528431460535500940      # FALLBACK FOR EMBEDS
TEXT_WARN_CHANNEL_ID = 1528330771562106965      # PLAIN TEXT WARNINGS

OWNER_ID = "1516568962966753291"                # ABSOLUTE IMMUNITY
ADMIN_ROLE_ID = 1527642221942276148             # ADMIN ROLE (IMMUNE FROM MODS)
MOD_ROLE_ID = 1526977512654245928               # MOD ROLE (TRIGGERS ACTIONS)

BAD_WORDS = ["nigger", "nigga", "faggot", "retard", "kike", "chink", "spic", "gook", "cunt", "whore", "slut", "rape", "pedophile"]

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

    # ==========================================
    # 1. CONSUME DASHBOARD ACTIONS
    # ==========================================
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

            if action['type'] == 'mod_action':
                user_id = int(action.get('user_id'))
                moderator_name = action.get('moderator_name', 'Dashboard')
                
                # =======================================================
                # 🛡️ IMMUNITY & HIERARCHY CHECKS
                # =======================================================
                
                # 1. Absolute Owner Immunity
                if str(user_id) == OWNER_ID:
                    print(f"🛡️ [BOT] Action skipped: Owner ({user_id}) is immune.")
                    admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "completed", "error": "Owner immunity triggered."}})
                    return

                member = guild.get_member(user_id)
                if member is None:
                    try: member = await guild.fetch_member(user_id)
                    except discord.NotFound:
                        admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "failed", "error": "Member not found"}})
                        return

                # 2. Role Hierarchy Immunity
                if ADMIN_ROLE_ID in [r.id for r in member.roles]:
                    if moderator_name == "Dashboard" or moderator_name == "Auto-Mod":
                        pass
                    else:
                        print(f"🛡️ [BOT] Action blocked: Mod ({moderator_name}) tried to act on Admin ({member.display_name}).")
                        admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "completed", "error": "Admin immune from Mod actions."}})
                        return

                action_type = action.get('action')
                reason = action.get('reason', 'No reason provided.')
                duration = int(action.get('duration', 60))

                try:
                    if action_type == 'kick': 
                        await member.kick(reason=reason)
                    elif action_type == 'ban': 
                        await member.ban(reason=reason)
                    elif action_type == 'unban':
                        try: await guild.unban(discord.Object(id=user_id), reason=reason)
                        except discord.NotFound: raise Exception("User is not banned.")
                    elif action_type == 'timeout':
                        await member.timeout(discord.utils.utcnow() + timedelta(seconds=duration), reason=reason)
                    elif action_type == 'mute':
                        await member.timeout(discord.utils.utcnow() + timedelta(seconds=duration), reason=reason)
                    elif action_type == 'remove_timeout':
                        await member.timeout(None, reason=reason)
                    elif action_type == 'warn':
                        await self.handle_warning(guild, member, reason, moderator_name)
                    elif action_type == 'clear_warnings':
                        warning_users.delete_one({"guild_id": str(guild.id), "user_id": str(member.id)})
                        await self.send_log_embed(guild, member, "All warnings cleared", "No warnings remain.", moderator_name, "✅")
                    elif action_type == 'delete_single_warning':
                        warning_id = action.get('warning_id')
                        if warning_id:
                            warning_users.update_one(
                                {"guild_id": str(guild.id), "user_id": str(member.id)},
                                {"$pull": {"warnings": {"_id": ObjectId(warning_id)}}}
                            )
                            await self.send_log_embed(guild, member, "Warning deleted", f"Deleted a specific warning.", moderator_name, "🗑️")
                except discord.Forbidden: raise Exception("Bot missing permissions.")
                except discord.NotFound: raise Exception("User/Role not found.")
                
                if action_type not in ['warn', 'clear_warnings', 'delete_single_warning']:
                    print(f"✅ [BOT] Executed {action_type.upper()} on {member.display_name}")

            elif action['type'] == 'announcement':
                channel_id = int(action.get('channel_id', 0))
                channel = guild.get_channel(channel_id)
                if not channel or not isinstance(channel, discord.TextChannel): raise Exception("Invalid text channel.")
                await channel.send(action.get('content', ''))
                print(f"✅ [BOT] Sent announcement to {channel.name}")

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

            elif action['type'] == 'save_welcome_config':
                from cogs.welcome import WelcomeSystem
                welcome_cog = self.bot.get_cog("WelcomeSystem")
                if welcome_cog:
                    guild_id_str = str(guild.id)
                    if guild_id_str not in welcome_cog.welcome_settings:
                        welcome_cog.welcome_settings[guild_id_str] = {}
                    
                    welcome_cog.welcome_settings[guild_id_str]["welcome_text"] = action.get('welcome_text', "Welcome to VoDevs!")
                    welcome_cog.welcome_settings[guild_id_str]["circle_color"] = action.get('welcome_circle_color', "#d1a3ff")
                    welcome_cog.welcome_settings[guild_id_str]["user_name_color"] = action.get('welcome_name_color', "#a1b0d6")
                    welcome_cog.welcome_settings[guild_id_str]["welcome_text_color"] = action.get('welcome_msg_color', "#a1b0d6")
                    welcome_cog.save_data()
                    print(f"✅ [BOT] Welcome config saved for guild {guild.name}")

            elif action['type'] == 'get_ban_list':
                print(f"📋 [BOT] Fetching ban list for guild {guild.name}")
                try:
                    ban_list = []
                    async for ban_entry in guild.bans():
                        ban_list.append({
                            "user_id": str(ban_entry.user.id),
                            "username": ban_entry.user.name,
                            "reason": ban_entry.reason
                        })
                    # Save to MongoDB cache for the dashboard
                    ban_list_cache.update_one(
                        {"guild_id": str(guild.id)},
                        {"$set": {"bans": ban_list}},
                        upsert=True
                    )
                    print(f"✅ [BOT] Cached {len(ban_list)} banned users.")
                except discord.Forbidden:
                    print(f"❌ [BOT] Missing permissions to view bans.")
                except Exception as e:
                    print(f"❌ [BOT] Error fetching ban list: {e}")

            admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "completed"}})

        except Exception as e:
            print(f"❌ [BOT] Action Failed: {e}")
            admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "failed", "error": str(e)}})

    @consume_actions.before_loop
    async def before_consume_actions(self):
        await self.bot.wait_until_ready()
        print("🚀 [BOT] Admin Action Consumer is starting...")

    # ==========================================
    # 2. AUTO-WARNING LISTENER (MONITORS ALL MESSAGES)
    # ==========================================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        if not message.guild: return
        
        # 🛡️ Skip owner from auto-moderation
        if str(message.author.id) == OWNER_ID:
            return

        lower_content = message.content.lower()
        for word in BAD_WORDS:
            if word in lower_content:
                try: await message.delete()
                except: pass

                # Generate a safe reason (DO NOT REPEAT THE BAD WORD)
                safe_reason = "Auto-Mod: Used inappropriate language"

                await self.handle_warning(
                    guild=message.guild,
                    member=message.author,
                    reason=safe_reason,
                    moderator_name="Auto-Mod"
                )
                
                # Send the warning message to the TEXT CHANNEL (1528330771562106965)
                text_chat = message.guild.get_channel(TEXT_WARN_CHANNEL_ID)
                if text_chat and isinstance(text_chat, discord.TextChannel):
                    await text_chat.send(f"⚠️ {message.author.mention}, your message was deleted for containing inappropriate language. You have been automatically warned.")
                break

    # ==========================================
    # 3. SHARED WARNING HANDLER
    # ==========================================
    async def handle_warning(self, guild, member, reason, moderator_name):
        # Save warning to MongoDB
        warning_users.update_one(
            {"guild_id": str(guild.id), "user_id": str(member.id)},
            {"$push": {"warnings": {
                "reason": reason,
                "moderator": moderator_name,
                "timestamp": datetime.utcnow().isoformat()
            }}},
            upsert=True
        )
        print(f"✅ [BOT] Warning saved for {member.display_name}")

        # Get total warning count
        user_data = warning_users.find_one({"guild_id": str(guild.id), "user_id": str(member.id)})
        warn_count = len(user_data["warnings"]) if user_data else 0
        print(f"⚖️ {member.display_name} now has {warn_count} warnings.")

        # Check thresholds & apply punishment
        if warn_count >= 7:
            await member.ban(reason="7 warnings reached (5-day ban).")
            print(f"🔨 {member.display_name} was BANNED for 5 days (7 warnings).")
        elif warn_count == 6:
            await member.ban(reason="6 warnings reached (5-day ban).")
            print(f"🔨 {member.display_name} was BANNED for 5 days (6 warnings).")
        elif warn_count == 5:
            await member.timeout(discord.utils.utcnow() + timedelta(days=7), reason="5 warnings reached (7-day mute).")
            print(f"🔇 {member.display_name} was MUTED for 7 days (5 warnings).")
        elif warn_count == 4:
            await member.timeout(discord.utils.utcnow() + timedelta(days=1), reason="4 warnings reached (1-day mute).")
            print(f"🔇 {member.display_name} was MUTED for 1 day (4 warnings).")
        elif warn_count == 3:
            await member.timeout(discord.utils.utcnow() + timedelta(hours=1), reason="3 warnings reached (1-hour mute).")
            print(f"🔇 {member.display_name} was MUTED for 1 hour (3 warnings).")

        # Send WARNING IMAGE to specified channel (1526989768595083384)
        from cogs.welcome import WelcomeSystem
        welcome_cog = self.bot.get_cog("WelcomeSystem")
        if welcome_cog:
            try:
                warn_channel = guild.get_channel(ACTION_IMAGE_CHANNEL_ID)
                if warn_channel and isinstance(warn_channel, discord.TextChannel):
                    file = await welcome_cog.build_action_card(guild, member, "warn", reason, moderator_name, warn_count)
                    await warn_channel.send(file=file)
            except Exception as e:
                print(f"❌ Failed to send warning image card: {e}")

        # Fallback: send embed to original log channel
        await self.send_log_embed(guild, member, reason, f"Total Warnings: {warn_count}", moderator_name, "⚠️")

    async def send_log_embed(self, guild, member, title, description, moderator_name, emoji):
        # Always send embeds to the Embed Log Channel
        warn_channel = guild.get_channel(EMBED_LOG_CHANNEL_ID)
        
        if warn_channel and isinstance(warn_channel, discord.TextChannel):
            embed = discord.Embed(
                title=f"{emoji} {title}",
                description=f"**User:** {member.mention}\n**Details:** {description}",
                color=discord.Color.orange()
            )
            embed.set_footer(text=f"Moderator: {moderator_name}")
            await warn_channel.send(embed=embed)

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
