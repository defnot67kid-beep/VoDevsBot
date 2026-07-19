import discord
from discord.ext import commands
import json
import os

AUTO_RR_FILE = "autorr_data.json"

def load_autorr():
    if os.path.exists(AUTO_RR_FILE):
        with open(AUTO_RR_FILE, "r") as f:
            return json.load(f)
    return {} # Format: {"guild_id": [{"trigger": "text", "emojis": ["✅", "❌"]}]}

def save_autorr(data):
    with open(AUTO_RR_FILE, "w") as f:
        json.dump(data, f, indent=4)

class AutoRR(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_autorr()

    @commands.command(name="autorr")
    @commands.has_permissions(manage_messages=True)
    async def auto_reaction(self, ctx, emoji1: str, emoji2: str, *, trigger_text: str):
        """
        [Admin] Sets up an auto-reaction. 
        Usage: !autorr :yes: :no: "Trigger Text"
        When a user types the trigger text, the bot reacts with both emojis on their message.
        """
        if not trigger_text:
            return await ctx.send("❌ You must provide trigger text.")
        
        guild_id = str(ctx.guild.id)
        if guild_id not in self.data:
            self.data[guild_id] = []
            
        # Add rule
        self.data[guild_id].append({
            "trigger": trigger_text.lower(),
            "emojis": [emoji1, emoji2]
        })
        save_autorr(self.data)
        
        await ctx.send(f"✅ Auto-Reaction set! When someone says `{trigger_text}`, I'll react to their message.", delete_after=10)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        
        guild_id = str(message.guild.id)
        if guild_id not in self.data:
            return
            
        for rule in self.data[guild_id]:
            # Check if the message content contains the exact trigger text (case insensitive)
            if rule["trigger"] in message.content.lower():
                # React to the user's original message without deleting it!
                for emoji in rule["emojis"]:
                    try:
                        await message.add_reaction(emoji)
                    except:
                        pass # Skip if emoji is invalid

    @commands.command(name="autorrlist")
    @commands.has_permissions(manage_messages=True)
    async def list_autorr(self, ctx):
        """[Admin] Lists all auto-reaction triggers in this server."""
        guild_id = str(ctx.guild.id)
        if guild_id not in self.data or not self.data[guild_id]:
            return await ctx.send("❌ No auto-reactions set up in this server.")
            
        embed = discord.Embed(title="⚡ Auto-Reaction Triggers", color=discord.Color.blue())
        for i, rule in enumerate(self.data[guild_id]):
            embed.add_field(
                name=f"Trigger #{i+1}",
                value=f"**Text:** `{rule['trigger']}`\n**Emojis:** {' '.join(rule['emojis'])}",
                inline=False
            )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AutoRR(bot))
