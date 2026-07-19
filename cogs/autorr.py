import discord
from discord.ext import commands
import re
import asyncio

class AutoRR(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="autorr")
    @commands.has_permissions(manage_messages=True)
    async def auto_reaction(self, ctx, trigger_emoji: str, add_emoji: str, *, trigger_text: str):
        """
        [Admin] Sets up an auto-reaction.
        Usage: !autorr :emoji1: :emoji2: "Trigger Text"
        When a user types the trigger text, the bot will react with both emojis (no deletion).
        """
        if not trigger_text:
            return await ctx.send("❌ You must provide trigger text.")
        
        if not hasattr(self.bot, 'auto_reactions'):
            self.bot.auto_reactions = []
            
        self.bot.auto_reactions.append({
            "guild_id": ctx.guild.id,
            "trigger_text": trigger_text.lower(),
            "emojis": [trigger_emoji, add_emoji]
        })
        
        await ctx.send(f"✅ Auto-Reaction set! When someone says `{trigger_text}`, I'll react with {trigger_emoji} and {add_emoji}.", delete_after=10)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        if not hasattr(self.bot, 'auto_reactions'):
            return
            
        for rule in self.bot.auto_reactions:
            if rule["guild_id"] == message.guild.id:
                # Check if the message content contains the trigger text (case insensitive)
                if rule["trigger_text"] in message.content.lower():
                    # React to the original message with both emojis
                    for emoji in rule["emojis"]:
                        try:
                            await message.add_reaction(emoji)
                        except discord.Forbidden:
                            pass  # Bot doesn't have permission to react
                        except discord.HTTPException:
                            pass  # Invalid emoji or other error

async def setup(bot):
    await bot.add_cog(AutoRR(bot))
