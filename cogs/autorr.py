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
            
        # Check if this trigger already exists for this guild
        for rule in self.bot.auto_reactions:
            if rule["guild_id"] == ctx.guild.id and rule["trigger_text"] == trigger_text.lower():
                # Update existing rule instead of adding duplicate
                rule["emojis"] = [trigger_emoji, add_emoji]
                return await ctx.send(f"✅ Updated auto-reaction for `{trigger_text}` to {trigger_emoji} and {add_emoji}.", delete_after=10)
        
        self.bot.auto_reactions.append({
            "guild_id": ctx.guild.id,
            "trigger_text": trigger_text.lower(),
            "emojis": [trigger_emoji, add_emoji]
        })
        
        await ctx.send(f"✅ Auto-Reaction set! When someone says `{trigger_text}`, I'll react with {trigger_emoji} and {add_emoji}.", delete_after=10)

    @commands.command(name="reset")
    @commands.has_permissions(manage_messages=True)
    async def reset_auto_reactions(self, ctx):
        """
        [Admin] Clears ALL auto-reaction rules for this server.
        Usage: !reset
        """
        if not hasattr(self.bot, 'auto_reactions'):
            return await ctx.send("❌ No auto-reactions are set up.", delete_after=10)
        
        # Filter out rules for this guild
        initial_count = len([r for r in self.bot.auto_reactions if r["guild_id"] == ctx.guild.id])
        
        if initial_count == 0:
            return await ctx.send("❌ No auto-reactions are set up for this server.", delete_after=10)
        
        # Keep only rules from other guilds
        self.bot.auto_reactions = [r for r in self.bot.auto_reactions if r["guild_id"] != ctx.guild.id]
        
        await ctx.send(f"✅ Reset complete! Removed {initial_count} auto-reaction rule(s) for this server.", delete_after=10)

    @commands.command(name="listrr")
    @commands.has_permissions(manage_messages=True)
    async def list_auto_reactions(self, ctx):
        """
        [Admin] Lists all active auto-reaction rules for this server.
        Usage: !listrr
        """
        if not hasattr(self.bot, 'auto_reactions'):
            return await ctx.send("❌ No auto-reactions are set up.", delete_after=10)
        
        guild_rules = [r for r in self.bot.auto_reactions if r["guild_id"] == ctx.guild.id]
        
        if not guild_rules:
            return await ctx.send("❌ No auto-reactions are set up for this server.", delete_after=10)
        
        embed = discord.Embed(
            title="📋 Auto-Reaction Rules",
            description="Current auto-reactions set for this server:",
            color=discord.Color.blue()
        )
        
        for i, rule in enumerate(guild_rules, 1):
            emojis_str = " ".join(rule["emojis"])
            embed.add_field(
                name=f"Rule #{i}",
                value=f"**Trigger:** `{rule['trigger_text']}`\n**Reactions:** {emojis_str}",
                inline=False
            )
        
        await ctx.send(embed=embed, delete_after=30)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        if not hasattr(self.bot, 'auto_reactions'):
            return
            
        for rule in self.bot.auto_reactions:
            if rule["guild_id"] == message.guild.id:
                if rule["trigger_text"] in message.content.lower():
                    for emoji in rule["emojis"]:
                        try:
                            await message.add_reaction(emoji)
                        except discord.Forbidden:
                            pass
                        except discord.HTTPException:
                            pass

async def setup(bot):
    await bot.add_cog(AutoRR(bot))
