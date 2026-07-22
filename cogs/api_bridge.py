import discord
from discord.ext import commands
import pymongo
import os
from flask import Flask, request, jsonify
import threading

# ==========================================
# MONGODB SETUP
# ==========================================
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI environment variable is not set!")

client = pymongo.MongoClient(MONGO_URI)
db = client["vodevs_bot_data"]
rr_collection = db["reaction_roles"]

# ==========================================
# INTERNAL FLASK API FOR THE BOT
# ==========================================
api_app = Flask(__name__)

@api_app.route('/api/create_reaction_role', methods=['POST'])
async def api_create_reaction_role():
    data = request.json
    guild_id = int(data.get('guild_id'))
    channel_id = int(data.get('channel_id'))
    title = data.get('title')
    description = data.get('description')
    color_hex = data.get('color', '#5865F2')
    roles_list = data.get('roles', []) # List of {"emoji": "✅", "role_id": 12345, "description": "..."}

    # Get the bot instance from the running thread
    bot_instance = ReactionRoleAPI.bot
    
    guild = bot_instance.get_guild(guild_id)
    if not guild:
        return jsonify({"status": "error", "message": "Guild not found"}), 404

    channel = guild.get_channel(channel_id)
    if not channel:
        return jsonify({"status": "error", "message": "Channel not found"}), 404

    # Create Embed
    color = discord.Color.from_str(color_hex)
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="React to this message to receive roles!")

    role_text = ""
    for item in roles_list:
        role = guild.get_role(item['role_id'])
        role_mention = role.mention if role else "**Deleted Role**"
        role_text += f"{item['emoji']} {role_mention} — *{item['description']}*\n"

    embed.add_field(name="Available Roles", value=role_text if role_text else "No roles added yet.", inline=False)

    # Send the message
    try:
        msg = await channel.send(embed=embed)
        
        # Add reactions
        for item in roles_list:
            try:
                await msg.add_reaction(item['emoji'])
            except:
                pass # Skip invalid emojis

        # Save to MongoDB
        rr_collection.insert_one({
            "message_id": str(msg.id),
            "channel_id": channel_id,
            "guild_id": guild_id,
            "title": title,
            "description": description,
            "color": color.value,
            "roles": {item['emoji']: {"role_id": item['role_id'], "description": item['description']} for item in roles_list}
        })

        return jsonify({"status": "success", "message_id": str(msg.id)}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ==========================================
# COG TO RUN THE API ON BOT STARTUP
# ==========================================
class ReactionRoleAPI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        ReactionRoleAPI.bot = bot # Store bot instance for API access
        
    @commands.Cog.listener()
    async def on_ready(self):
        # Start the internal Flask API in a background thread
        def run_api():
            api_app.run(host='0.0.0.0', port=5001)
        
        threading.Thread(target=run_api, daemon=True).start()
        print("✅ Internal Bot API started on port 5001")

async def setup(bot):
    await bot.add_cog(ReactionRoleAPI(bot))
