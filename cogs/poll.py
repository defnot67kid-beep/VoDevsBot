import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
import json
import os
import asyncio
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import threading

POLL_DATA_FILE = "polls_data.json"
GLOBAL_POLL_CHANNEL = 1526730287378075648

def load_polls():
    if os.path.exists(POLL_DATA_FILE):
        with open(POLL_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_polls(data):
    with open(POLL_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ==========================================
# MODAL FOR !POLLMENU / !GLOBALPOLL
# ==========================================
class PollMenuModal(Modal, title="Create Advanced Poll"):
    question = TextInput(label="Poll Question", placeholder="What is your favorite color?", required=True)
    options = TextInput(label="Options (Separate with | )", placeholder="Red | Blue | Green | Yellow", required=True)
    duration = TextInput(label="Duration (e.g. 5m, 1h, 24h)", placeholder="15m", required=True)
    poll_type = TextInput(label="Type (single or multiple)", placeholder="single", required=True)

    def __init__(self, ctx, is_global: bool = False):
        super().__init__()
        self.ctx = ctx
        self.is_global = is_global

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        q = self.question.value
        opts = [o.strip() for o in self.options.value.split("|")]
        duration_str = self.duration.value.lower()
        p_type = self.poll_type.value.lower()
        
        if len(opts) < 2: return await interaction.followup.send("❌ You need at least 2 options.", ephemeral=True)
        if p_type not in ["single", "multiple"]: return await interaction.followup.send("❌ Type must be 'single' or 'multiple'.", ephemeral=True)
        
        seconds = 0
        if duration_str.endswith("m"):
            try: seconds = int(duration_str[:-1]) * 60
            except: pass
        elif duration_str.endswith("h"):
            try: seconds = int(duration_str[:-1]) * 3600
            except: pass
        elif duration_str.endswith("d"):
            try: seconds = int(duration_str[:-1]) * 86400
            except: pass
        else:
            try: seconds = int(duration_str) * 60
            except: return await interaction.followup.send("❌ Invalid duration. Use: `15m`, `1h`, `2d`.", ephemeral=True)
            
        if seconds <= 0: return await interaction.followup.send("❌ Duration must be greater than 0.", ephemeral=True)

        await create_poll_logic(interaction, q, opts, seconds, p_type, self.is_global)

# ==========================================
# VIEW TO TRIGGER MODAL
# ==========================================
class PollMenuTriggerView(View):
    def __init__(self, ctx, is_global: bool = False):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.is_global = is_global

    @discord.ui.button(label="📝 Click here to open the form", style=discord.ButtonStyle.success)
    async def open_modal(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(PollMenuModal(self.ctx, self.is_global))

# ==========================================
# POLL DROPDOWN & VIEWS
# ==========================================
class PollSelectMenu(Select):
    def __init__(self, poll_id, options, multiple_choice):
        self.poll_id = poll_id
        self.multiple_choice = multiple_choice
        select_options = []
        for i, opt in enumerate(options):
            select_options.append(discord.SelectOption(label=f"Option {i+1}", description=opt[:50], value=str(i)))
        super().__init__(placeholder="Choose your vote...", min_values=1, max_values=1 if not multiple_choice else len(options), options=select_options)

    async def callback(self, interaction: discord.Interaction):
        polls = load_polls()
        if self.poll_id not in polls: return await interaction.response.send_message("❌ Poll not found.", ephemeral=True)
        data = polls[self.poll_id]
        
        # LOCK CHECK
        if data.get("ended", False):
            return await interaction.response.send_message("🔒 This poll has already ended and is locked.", ephemeral=True)
            
        selected_indices = [int(v) for v in self.values]
        user_id = str(interaction.user.id)
        
        if not self.multiple_choice:
            for option_idx in data["votes"]:
                if user_id in data["votes"][option_idx]: data["votes"][option_idx].remove(user_id); break
            data["votes"][str(selected_indices[0])].append(user_id)
            await interaction.response.send_message(f"✅ Voted: **{data['options'][selected_indices[0]]}**", ephemeral=True)
        else:
            for option_idx in data["votes"]:
                if user_id in data["votes"][option_idx]: data["votes"][option_idx].remove(user_id)
            for idx in selected_indices: data["votes"][str(idx)].append(user_id)
            chosen = ", ".join([f"**{data['options'][i]}**" for i in selected_indices])
            await interaction.response.send_message(f"✅ Votes updated: {chosen}", ephemeral=True)
        save_polls(polls)

class PollView(View):
    def __init__(self, poll_id, options, multiple_choice, end_time, is_global, message):
        super().__init__(timeout=None)
        self.poll_id = poll_id
        self.end_time = end_time
        self.is_global = is_global
        self.message = message
        self.add_item(PollSelectMenu(poll_id, options, multiple_choice))

    @discord.ui.button(label="📊 View Results", style=discord.ButtonStyle.secondary)
    async def results_button(self, interaction: discord.Interaction, button: Button):
        polls = load_polls()
        if self.poll_id not in polls: return await interaction.response.send_message("❌ Poll not found.", ephemeral=True)
        data = polls[self.poll_id]
        
        all_voters = set()
        for voters in data["votes"].values(): all_voters.update(voters)
        total = len(all_voters)
        
        if total == 0: return await interaction.response.send_message("📊 No votes have been cast yet.", ephemeral=True)
        
        # === CLEAN, MODERN RESULTS EMBED ===
        embed = discord.Embed(
            title=f"📊 Live Results: {data['question']}",
            color=discord.Color.green()
        )
        
        for i, opt in enumerate(data["options"]):
            count = len(data["votes"].get(str(i), []))
            percent = (count / total) * 100
            embed.add_field(
                name=f"Option {i+1}: {opt}",
                value=f"**{count}** votes ({percent:.1f}%)",
                inline=False
            )
        
        embed.set_footer(text=f"Total Voters: {total} | Type: {'Multiple' if data['multiple_choice'] else 'Single'} Choice")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ==========================================
# CORE LOGIC
# ==========================================
async def create_poll_logic(interaction, question, options, duration_seconds, p_type, is_global):
    poll_id = f"{interaction.id}-{datetime.now().timestamp()}"
    end_time = datetime.now() + timedelta(seconds=duration_seconds)
    
    embed = discord.Embed(
        title=f"📊 {question}",
        description="\n".join([f"**{i+1}.** {opt}" for i, opt in enumerate(options)]),
        color=discord.Color.blurple()
    )
    embed.add_field(name="⏳ Time Remaining", value=f"<t:{int(end_time.timestamp())}:R>", inline=False)
    embed.add_field(name="📋 Vote Type", value=f"{'Multiple' if p_type == 'multiple' else 'Single'} Choice", inline=False)
    embed.set_footer(text="Use the dropdown menu below to vote!")

    polls = load_polls()
    polls[poll_id] = {
        "question": question, "options": options, 
        "votes": {str(i): [] for i in range(len(options))},
        "multiple_choice": p_type == "multiple", 
        "end_time": end_time.timestamp(), 
        "channel_id": interaction.channel.id,
        "is_global": is_global
    }
    save_polls(polls)

    # Determine where to send
    target_channel = interaction.channel
    if is_global:
        global_channel = interaction.guild.get_channel(GLOBAL_POLL_CHANNEL)
        if global_channel:
            target_channel = global_channel
            await interaction.followup.send(f"✅ Global poll successfully sent to {global_channel.mention}!", ephemeral=True)
        else:
            await interaction.followup.send(f"⚠️ Global channel not found. Sending locally.", ephemeral=True)

    # Send the message and save the message object into the view
    sent_msg = await target_channel.send(embed=embed, view=PollView(poll_id, options, p_type == "multiple", end_time, is_global, None))
    
    # Update the view to have the message reference so we can edit it later
    view = PollView(poll_id, options, p_type == "multiple", end_time, is_global, sent_msg)
    await sent_msg.edit(view=view)

    # === AUTO-END TIMER ===
    await asyncio.sleep(duration_seconds)
    
    # Reload data to ensure it's fresh
    polls = load_polls()
    if poll_id in polls:
        data = polls[poll_id]
        data["ended"] = True
        save_polls(polls)
        
        # Build Final Results Embed
        all_voters = set()
        for voters in data["votes"].values(): all_voters.update(voters)
        total = len(all_voters)
        
        final_embed = discord.Embed(
            title=f"🔒 Poll Ended: {data['question']}",
            color=discord.Color.red()
        )
        
        if total == 0:
            final_embed.description = "❌ No votes were cast."
        else:
            for i, opt in enumerate(data["options"]):
                count = len(data["votes"].get(str(i), []))
                percent = (count / total) * 100
                final_embed.add_field(
                    name=f"Option {i+1}: {opt}",
                    value=f"**{count}** votes ({percent:.1f}%)",
                    inline=False
                )
            final_embed.set_footer(text=f"Total Voters: {total}")
        
        # Edit the original message to remove the dropdown and show results
        try:
            await sent_msg.edit(embed=final_embed, view=None) # View=None locks it completely
        except:
            pass # If message was deleted, just ignore

# ==========================================
# MAIN COG
# ==========================================
class Poll(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="pollmenu")
    @commands.has_permissions(manage_messages=True)
    async def poll_menu(self, ctx):
        """[Admin] Opens a pop-up to create an advanced poll."""
        embed = discord.Embed(title="📝 Local Poll Creator", description="Click below for a local channel poll.", color=discord.Color.blurple())
        await ctx.send(embed=embed, view=PollMenuTriggerView(ctx, is_global=False))

    @commands.command(name="globalpoll")
    @commands.has_permissions(manage_messages=True)
    async def global_poll_menu(self, ctx):
        """[Admin] Opens a pop-up to create a poll for the global channel."""
        embed = discord.Embed(title="🌐 Global Poll Creator", description=f"Click below to create a poll that will automatically be sent to <#{GLOBAL_POLL_CHANNEL}>.", color=discord.Color.gold())
        await ctx.send(embed=embed, view=PollMenuTriggerView(ctx, is_global=True))

    @commands.command(name="pollmake")
    @commands.has_permissions(manage_messages=True)
    async def poll_make(self, ctx, duration: str = "15m", p_type: str = "single", *, question_and_options: str):
        """[Admin] Text-based local poll creation."""
        if "|" not in question_and_options:
            return await ctx.send("❌ Format: `!pollmake 5m single \"Question\" | Opt1 | Opt2`")
        parts = [p.strip() for p in question_and_options.split("|")]
        q = parts[0]; opts = parts[1:]
        if len(opts) < 2: return await ctx.send("❌ At least 2 options required.")
        
        seconds = 0
        if duration.endswith("m"): seconds = int(duration[:-1]) * 60
        elif duration.endswith("h"): seconds = int(duration[:-1]) * 3600
        elif duration.endswith("d"): seconds = int(duration[:-1]) * 86400
        else: seconds = int(duration) * 60
        
        class FakeInteraction:
            def __init__(self, ctx):
                self.id = ctx.message.id
                self.channel = ctx.channel
                self.guild = ctx.guild
                self.user = ctx.author
                self.followup = ctx
        fake_interaction = FakeInteraction(ctx)
        await create_poll_logic(fake_interaction, q, opts, seconds, p_type, is_global=False)

# ==========================================
# BOT API RECEIVERS (For Admin Dashboard Actions)
# ==========================================
# Create a simple internal Flask app inside the bot just to listen
api_app = Flask(__name__)

@api_app.route('/api/admin/create_poll', methods=['POST'])
def bot_create_poll():
    data = request.json
    return jsonify({"status": "success", "message": "Poll endpoint received!"})

@api_app.route('/api/admin/mod_action', methods=['POST'])
def bot_mod_action():
    data = request.json
    # Discord logic to handle mod actions goes here.
    return jsonify({"status": "success", "action": data.get('action')})

@api_app.route('/api/admin/send_announcement', methods=['POST'])
def bot_send_announcement():
    data = request.json
    return jsonify({"status": "success", "message": "Announcement endpoint received!"})

# Function to start the API in a background thread
def start_api():
    # If running on Railway, it MUST use the PORT variable assigned to it
    port = int(os.getenv("BOT_API_PORT", 5001)) 
    api_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# Start the background thread only when the bot starts up
def start_api_thread():
    thread = threading.Thread(target=start_api, daemon=True)
    thread.start()

# Attach startup listener manually
@commands.Cog.listener()
async def on_ready(self):
    start_api_thread()
    print("✅ Poll API Background Server Started!")

async def setup(bot): 
    await bot.add_cog(Poll(bot))
    # Manually trigger API start here if on_ready fails to trigger
    start_api_thread()
