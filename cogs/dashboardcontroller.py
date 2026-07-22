import discord
from discord.ext import commands
import pymongo
import os
import json
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# ==========================================
# MONGODB SETUP
# ==========================================
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI environment variable is not set!")

client = pymongo.MongoClient(MONGO_URI)
db = client["vodevs_bot_data"]
levels_collection = db["levels"]
rr_collection = db["reaction_roles"]
admins_collection = db["admins"]

# ==========================================
# HTTP REQUEST HANDLER (Runs inside Bot)
# ==========================================
class DashboardHandler(BaseHTTPRequestHandler):
    bot = None  # Static reference to the bot

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)
        
        response = {"status": "error", "message": "Invalid endpoint"}
        
        if self.path == "/api/create_reaction_role":
            response = asyncio.run(self.handle_create_reaction_role(data))
        elif self.path == "/api/mod_action":
            response = asyncio.run(self.handle_mod_action(data))
        elif self.path == "/api/get_members":
            response = asyncio.run(self.handle_get_members(data))
            
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    async def handle_create_reaction_role(self, data):
        try:
            guild_id = int(data.get('guild_id'))
            channel_id = int(data.get('channel_id'))
            title = data.get('title')
            description = data.get('description')
            color_hex = data.get('color', '#5865F2')
            roles_list = data.get('roles', [])

            guild = self.bot.get_guild(guild_id)
            if not guild: return {"status": "error", "message": "Guild not found"}

            channel = guild.get_channel(channel_id)
            if not channel: return {"status": "error", "message": "Channel not found"}

            embed = discord.Embed(title=title, description=description, color=discord.Color.from_str(color_hex))
            embed.set_footer(text="React to this message to receive roles!")

            role_text = ""
            for item in roles_list:
                role = guild.get_role(item['role_id'])
                role_mention = role.mention if role else "**Deleted Role**"
                role_text += f"{item['emoji']} {role_mention} — *{item['description']}*\n"

            embed.add_field(name="Available Roles", value=role_text if role_text else "No roles added yet.", inline=False)

            msg = None
            try:
                msg = await channel.send(embed=embed)
                # Add reactions
                for item in roles_list:
                    try: await msg.add_reaction(item['emoji'])
                    except: pass
            except Exception as e:
                return {"status": "error", "message": str(e)}

            # Save to MongoDB
            rr_collection.insert_one({
                "message_id": str(msg.id), "channel_id": channel_id, "guild_id": guild_id,
                "title": title, "description": description, "color": color_hex,
                "roles": {item['emoji']: {"role_id": item['role_id'], "description": item['description']} for item in roles_list}
            })
            return {"status": "success", "message_id": str(msg.id)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def handle_mod_action(self, data):
        try:
            guild_id = int(data.get('guild_id'))
            user_id = int(data.get('user_id'))
            action = data.get('action')
            reason = data.get('reason', 'No reason provided.')
            duration = int(data.get('duration', 60))

            guild = self.bot.get_guild(guild_id)
            if not guild: return {"status": "error", "message": "Guild not found"}

            member = guild.get_member(user_id)
            if not member: return {"status": "error", "message": "User not found in server"}

            if action == 'kick':
                await member.kick(reason=reason)
            elif action == 'ban':
                await member.ban(reason=reason)
            elif action == 'timeout':
                await member.timeout(discord.utils.utcnow() + discord.timedelta(seconds=duration), reason=reason)
            elif action == 'mute':
                muted_role = discord.utils.get(guild.roles, name="Muted")
                if not muted_role: return {"status": "error", "message": "No 'Muted' role exists. Please create one in Discord."}
                await member.add_roles(muted_role, reason=reason)
            
            return {"status": "success", "action": action}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def handle_get_members(self, data):
        try:
            guild_id = int(data.get('guild_id'))
            guild = self.bot.get_guild(guild_id)
            if not guild: return {"status": "error", "message": "Guild not found"}

            members_data = []
            for member in guild.members:
                # Don't include bots in the list
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
            
            return {"status": "success", "members": members_data}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def log_message(self, format, *args):
        return # Silence logging

# ==========================================
# MAIN DASHBOARD CONTROLLER COG
# ==========================================
class DashboardController(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        DashboardHandler.bot = bot
        self.httpd = None
        self.server_thread = None

    @commands.Cog.listener()
    async def on_ready(self):
        print("🚀 Starting Dashboard Controller (Internal API)...")
        def run_server():
            port = int(os.getenv("PORT", 5001))
            self.httpd = HTTPServer(('0.0.0.0', port), DashboardHandler)
            print(f"✅ Dashboard Controller listening on port {port}")
            self.httpd.serve_forever()

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

async def setup(bot):
    await bot.add_cog(DashboardController(bot))
