import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import json
import os
from datetime import datetime

POLL_DATA_FILE = "polls_data.json"

def load_polls():
    if os.path.exists(POLL_DATA_FILE):
        with open(POLL_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_polls(data):
    with open(POLL_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ==========================================
# DROPDOWN SELECT MENU FOR VOTING
# ==========================================
class PollSelectMenu(Select):
    def __init__(self, poll_id, options, multiple_choice):
        self.poll_id = poll_id
        self.multiple_choice = multiple_choice
        
        # Create dropdown options
        select_options = []
        for i, opt in enumerate(options):
            select_options.append(
                discord.SelectOption(label=f"Option {i+1}", description=opt[:50], value=str(i))
            )
        
        super().__init__(
            placeholder="Choose your vote...",
            min_values=1,
            max_values=1 if not multiple_choice else len(options),
            options=select_options
        )

    async def callback(self, interaction: discord.Interaction):
        polls = load_polls()
        if self.poll_id not in polls:
            return await interaction.response.send_message("❌ This poll is no longer active.", ephemeral=True)
        
        data = polls[self.poll_id]
        selected_indices = [int(v) for v in self.values]
        
        # Check if user already voted
        user_id = str(interaction.user.id)
        
        # Handle Single Choice
        if not self.multiple_choice:
            # Remove previous vote
            for option_idx in data["votes"]:
                if user_id in data["votes"][option_idx]:
                    data["votes"][option_idx].remove(user_id)
                    break
            
            # Add new vote
            data["votes"][str(selected_indices[0])].append(user_id)
            await interaction.response.send_message(f"✅ You voted for: **{data['options'][selected_indices[0]]}**", ephemeral=True)
        
        # Handle Multiple Choice
        else:
            # For multiple choice, we reset and add all their new choices
            for option_idx in data["votes"]:
                if user_id in data["votes"][option_idx]:
                    data["votes"][option_idx].remove(user_id)
            
            for idx in selected_indices:
                data["votes"][str(idx)].append(user_id)
            
            chosen_texts = ", ".join([f"**{data['options'][i]}**" for i in selected_indices])
            await interaction.response.send_message(f"✅ Your votes have been updated: {chosen_texts}", ephemeral=True)
        
        save_polls(polls)

# ==========================================
# BUTTON VIEW (Vote & Results)
# ==========================================
class PollView(View):
    def __init__(self, poll_id, options, multiple_choice):
        super().__init__(timeout=None)
        self.poll_id = poll_id
        self.add_item(PollSelectMenu(poll_id, options, multiple_choice))

    @discord.ui.button(label="📊 View Results", style=discord.ButtonStyle.secondary, custom_id="poll_results_btn")
    async def results_button(self, interaction: discord.Interaction, button: Button):
        polls = load_polls()
        if self.poll_id not in polls:
            return await interaction.response.send_message("❌ Poll data not found.", ephemeral=True)
        
        data = polls[self.poll_id]
        
        # Count total unique voters
        all_voters = set()
        for voters in data["votes"].values():
            all_voters.update(voters)
        total_votes = len(all_voters)
        
        if total_votes == 0:
            return await interaction.response.send_message("📊 No votes have been cast yet.", ephemeral=True)
        
        results = []
        for i, opt in enumerate(data["options"]):
            count = len(data["votes"].get(str(i), []))
            percent = (count / total_votes) * 100
            bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))
            results.append(f"`{i+1}.` {opt}\n{bar} {count} votes ({percent:.1f}%)")
        
        embed = discord.Embed(
            title=f"📊 Poll Results: {data['question']}",
            description="\n\n".join(results),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Total Voters: {total_votes}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ==========================================
# MAIN POLL COG
# ==========================================
class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pollmake")
    @commands.has_permissions(manage_messages=True)
    async def create_poll(self, ctx, size: str = "medium", format: str = "single", *, question_and_options: str):
        """
        [Admin] Creates an advanced poll.
        Format: !pollmake <size> <format> "Question" | "Option1" | "Option2" | ...
        Sizes: small, medium, big
        Formats: single, multiple
        """
        if "|" not in question_and_options:
            return await ctx.send("❌ Please separate the question and options with `|`.\nExample: `!pollmake medium single \"What is your favorite color?\" | Red | Blue | Green`")
        
        parts = [p.strip() for p in question_and_options.split("|")]
        question = parts[0]
        options = parts[1:]
        
        if len(options) < 2:
            return await ctx.send("❌ You must provide at least 2 options.")
        if len(options) > 10:
            return await ctx.send("❌ You cannot have more than 10 options.")

        poll_id = f"{ctx.message.id}-{datetime.now().timestamp()}"
        
        embed = discord.Embed(
            title=f"📊 {question}",
            description="\n".join([f"**{i+1}.** {opt}" for i, opt in enumerate(options)]),
            color=discord.Color.blurple()
        )
        
        if size.lower() == "small":
            embed.set_footer(text=f"Poll by {ctx.author.display_name} | Type: {format.capitalize()}")
        elif size.lower() == "big" or size.lower() == "large":
            embed.add_field(name="📋 Instructions", value=f"Use the dropdown menu below to vote.\n**Type:** {format.capitalize()} choice", inline=False)
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embed.set_footer(text=f"Poll by {ctx.author.display_name}")
        else:
            embed.set_footer(text=f"Type: {format.capitalize()} | Vote using the dropdown!")

        # Save poll data
        polls = load_polls()
        polls[poll_id] = {
            "question": question,
            "options": options,
            "votes": {str(i): [] for i in range(len(options))}, # Stores user IDs now
            "multiple_choice": format.lower() == "multiple"
        }
        save_polls(polls)

        view = PollView(poll_id, options, format.lower() == "multiple")
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Poll(bot))
