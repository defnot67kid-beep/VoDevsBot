import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select, Modal, TextInput
import pymongo
import os
import asyncio
from datetime import datetime, timedelta

# ==========================================
# MONGODB SETUP
# ==========================================
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI environment variable is not set!")

client = pymongo.MongoClient(MONGO_URI)
db = client["vodevs_bot_data"]
admin_actions_collection = db["admin_actions"]

# ==========================================
# HELPER: Parse Human Duration (e.g. "15m", "1h", "30s")
# ==========================================
def parse_duration(text):
    text = text.lower().strip()
    if text.endswith("s"):
        return int(text[:-1])
    elif text.endswith("m"):
        return int(text[:-1]) * 60
    elif text.endswith("h"):
        return int(text[:-1]) * 3600
    elif text.endswith("d"):
        return int(text[:-1]) * 86400
    else:
        try:
            return int(text)
        except ValueError:
            return 600  # Default to 10 minutes

# ==========================================
# POLL CONSUMER LOOP (MongoDB to Discord)
# ==========================================
class PollConsumer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.consume_polls.start()

    def cog_unload(self):
        self.consume_polls.cancel()

    @tasks.loop(seconds=5)
    async def consume_polls(self):
        # Atomically claim a pending poll action
        action = admin_actions_collection.find_one_and_update(
            {"type": "poll", "status": "pending"},
            {"$set": {"status": "processing"}}
        )
        if not action:
            return

        print(f"⚠️ [BOT] Processing Poll Action: {action.get('question', 'No Question')}")

        try:
            guild_id = int(action.get('guild_id'))
            guild = self.bot.get_guild(guild_id)
            if not guild:
                admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "failed", "error": "Guild not found"}})
                return

            channel_id = int(action.get('channel_id', 0))
            channel = guild.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.TextChannel):
                admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "failed", "error": "Invalid Text Channel"}})
                return

            question = action.get('question', 'Poll')
            options = action.get('options', [])
            duration_seconds = parse_duration(action.get('duration', '10m'))
            poll_type = action.get('poll_type', 'single')

            if len(options) < 2:
                admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "failed", "error": "At least 2 options required"}})
                return

            # ==========================================
            # BUILD AND SEND THE EMBED
            # ==========================================
            embed = discord.Embed(
                title=f"📊 {question}",
                description="\n".join([f"**{i+1}.** {opt}" for i, opt in enumerate(options)]),
                color=discord.Color.blurple()
            )
            end_time = datetime.now() + timedelta(seconds=duration_seconds)
            embed.add_field(name="⏳ Time Remaining", value=f"<t:{int(end_time.timestamp())}:R>", inline=False)
            embed.add_field(name="📋 Vote Type", value=f"{'Multiple' if poll_type == 'multiple' else 'Single'} Choice", inline=False)
            embed.set_footer(text="React with the numbered emojis to vote!")

            sent_msg = await channel.send(embed=embed)
            
            # ==========================================
            # ADD THE REACTIONS
            # ==========================================
            emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            for i in range(len(options)):
                if i < len(emojis):
                    await sent_msg.add_reaction(emojis[i])
            
            print(f"✅ [BOT] Poll created in {channel.name}. Waiting {duration_seconds}s...")

            # ==========================================
            # WAIT FOR THE DURATION
            # ==========================================
            await asyncio.sleep(duration_seconds)

            # ==========================================
            # AUTO-CLOSE THE POLL
            # ==========================================
            # Re-fetch the message to count reactions
            try:
                fresh_msg = await channel.fetch_message(sent_msg.id)
            except:
                admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "completed"}})
                return

            # Count votes based on reactions
            vote_counts = {i: 0 for i in range(len(options))}
            for reaction in fresh_msg.reactions:
                try:
                    # Get the index of the emoji
                    idx = emojis.index(str(reaction.emoji))
                    # Subtract the bot's own reaction (usually 1)
                    vote_counts[idx] = reaction.count - 1
                except ValueError:
                    continue

            total_votes = sum(vote_counts.values())

            # Build Final Results Embed
            final_embed = discord.Embed(
                title=f"🔒 Poll Ended: {question}",
                color=discord.Color.red()
            )
            
            if total_votes <= 0:
                final_embed.description = "❌ No votes were cast."
            else:
                for i, opt in enumerate(options):
                    count = vote_counts.get(i, 0)
                    percent = (count / total_votes) * 100 if total_votes > 0 else 0
                    final_embed.add_field(
                        name=f"Option {i+1}: {opt}",
                        value=f"**{count}** votes ({percent:.1f}%)",
                        inline=False
                    )
                final_embed.set_footer(text=f"Total Voters: {total_votes}")

            await fresh_msg.edit(embed=final_embed)
            # Clear all reactions to lock the poll
            await fresh_msg.clear_reactions()

            print(f"✅ [BOT] Poll ended in {channel.name}")

            # ==========================================
            # MARK AS COMPLETED
            # ==========================================
            admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "completed"}})

        except Exception as e:
            print(f"❌ [BOT] Poll Action Failed: {e}")
            admin_actions_collection.update_one({"_id": action["_id"]}, {"$set": {"status": "failed", "error": str(e)}})

    @consume_polls.before_loop
    async def before_consume_polls(self):
        await self.bot.wait_until_ready()
        print("🚀 [BOT] Poll Consumer is starting...")

    @consume_polls.after_loop
    async def after_consume_polls(self):
        if self.consume_polls.is_being_cancelled():
            print("⚠️ [BOT] Poll Consumer loop was cancelled.")

# ==========================================
# LEGACY DISCORD COMMANDS (Optional)
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
        
        if len(opts) < 2:
            return await interaction.followup.send("❌ You need at least 2 options.", ephemeral=True)
        if p_type not in ["single", "multiple"]:
            return await interaction.followup.send("❌ Type must be 'single' or 'multiple'.", ephemeral=True)
        
        seconds = parse_duration(duration_str)
        if seconds <= 0:
            return await interaction.followup.send("❌ Duration must be greater than 0.", ephemeral=True)

        await self.create_poll_logic(interaction, q, opts, seconds, p_type, self.is_global)

    async def create_poll_logic(self, interaction, question, options, duration_seconds, p_type, is_global):
        # Send poll directly to Discord using the old local logic
        end_time = datetime.now() + timedelta(seconds=duration_seconds)
        embed = discord.Embed(
            title=f"📊 {question}",
            description="\n".join([f"**{i+1}.** {opt}" for i, opt in enumerate(options)]),
            color=discord.Color.blurple()
        )
        embed.add_field(name="⏳ Time Remaining", value=f"<t:{int(end_time.timestamp())}:R>", inline=False)
        embed.add_field(name="📋 Vote Type", value=f"{'Multiple' if p_type == 'multiple' else 'Single'} Choice", inline=False)
        embed.set_footer(text="React with emojis to vote!")

        target_channel = interaction.channel
        # If global, change channel
        # GLOBAL_POLL_CHANNEL_ID can be hardcoded or put in env
        if is_global:
            global_channel = interaction.guild.get_channel(1526730287378075648)
            if global_channel:
                target_channel = global_channel
                await interaction.followup.send(f"✅ Poll sent to {global_channel.mention}!", ephemeral=True)
            else:
                await interaction.followup.send(f"⚠️ Global channel not found. Sending locally.", ephemeral=True)

        sent_msg = await target_channel.send(embed=embed)
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        for i in range(len(options)):
            if i < len(emojis):
                await sent_msg.add_reaction(emojis[i])

        await asyncio.sleep(duration_seconds)
        
        try:
            fresh_msg = await target_channel.fetch_message(sent_msg.id)
            vote_counts = {i: 0 for i in range(len(options))}
            for reaction in fresh_msg.reactions:
                try:
                    idx = emojis.index(str(reaction.emoji))
                    vote_counts[idx] = reaction.count - 1
                except ValueError:
                    continue
            total_votes = sum(vote_counts.values())
            final_embed = discord.Embed(title=f"🔒 Poll Ended: {question}", color=discord.Color.red())
            if total_votes <= 0:
                final_embed.description = "❌ No votes were cast."
            else:
                for i, opt in enumerate(options):
                    count = vote_counts.get(i, 0)
                    percent = (count / total_votes) * 100 if total_votes > 0 else 0
                    final_embed.add_field(
                        name=f"Option {i+1}: {opt}",
                        value=f"**{count}** votes ({percent:.1f}%)",
                        inline=False
                    )
                final_embed.set_footer(text=f"Total Voters: {total_votes}")
            await fresh_msg.edit(embed=final_embed)
            await fresh_msg.clear_reactions()
        except:
            pass

class PollMenuTriggerView(View):
    def __init__(self, ctx, is_global: bool = False):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.is_global = is_global

    @discord.ui.button(label="📝 Click here to open the form", style=discord.ButtonStyle.success)
    async def open_modal(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(PollMenuModal(self.ctx, self.is_global))

class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
        embed = discord.Embed(title="🌐 Global Poll Creator", description=f"Click below to create a poll for the global channel.", color=discord.Color.gold())
        await ctx.send(embed=embed, view=PollMenuTriggerView(ctx, is_global=True))

async def setup(bot):
    await bot.add_cog(Poll(bot))
    await bot.add_cog(PollConsumer(bot))
