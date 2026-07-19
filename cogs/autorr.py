import discord
from discord.ext import commands
import re

class AutoRR(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="autorr")
    @commands.has_permissions(manage_messages=True)
    async def auto_reaction(self, ctx, trigger_emoji: str, add_emoji: str, *, trigger_text: str):
        """
        [Admin] Sets up an auto-reaction. 
        Usage: !autorr :emoji1: :emoji2: "Trigger Text"
        When a user types exactly "Trigger Text", the bot will delete their message and react with both emojis.
        """
        # Simple validation
        if not trigger_text:
            return await ctx.send("❌ You must provide trigger text.")
        
        # Store it in a simple dictionary (in memory). 
        # For persistence across restarts, use JSON like the other cogs.
        # Since we don't have a central JSON file for this, we'll just store it in the bot memory.
        
        if not hasattr(self.bot, 'auto_reactions'):
            self.bot.auto_reactions = []
            
        self.bot.auto_reactions.append({
            "guild_id": ctx.guild.id,
            "trigger_text": trigger_text.lower(),
            "emojis": [trigger_emoji, add_emoji]
        })
        
        await ctx.send(f"✅ Auto-Reaction set! When someone says `{trigger_text}`, I'll react and delete their message.", delete_after=10)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        
        if not hasattr(self.bot, 'auto_reactions'):
            return
            
        for rule in self.bot.auto_reactions:
            if rule["guild_id"] == message.guild.id:
                # Check if the message content contains the exact trigger text (case insensitive)
                if rule["trigger_text"] in message.content.lower():
                    # Delete the user's message
                    try:
                        await message.delete()
                        # React to the message with the emojis (Note: since we deleted it, we react to a sent message)
                        # Actually, it's better to send a secret ephemeral-like response
                        await message.channel.send(f"⚡ Triggered autoreturn for `{rule['trigger_text']}`", delete_after=5)
                        # Since the message is deleted, we actually just silently log it.
                        # To actually react, we need the message to exist. 
                        # How about: We delete the message, and the bot sends a new one with reactions?
                        new_msg = await message.channel.send(f"{message.author.mention} triggered an auto-response.")
                        for emoji in rule["emojis"]:
                            try:
                                await new_msg.add_reaction(emoji)
                            except:
                                pass
                        await asyncio.sleep(3)
                        await new_msg.delete()
                    except discord.Forbidden:
                        pass # Bot doesn't have permissions to delete

async def setup(bot):
    await bot.add_cog(AutoRR(bot))
