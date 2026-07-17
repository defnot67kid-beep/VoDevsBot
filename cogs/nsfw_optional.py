import discord
from discord.ext import commands
import random

class NSFWOptional(commands.Cog):
    """NSFW commands (Toggleable) - Optional cog"""
    
    def __init__(self, bot):
        self.bot = bot
        self.enabled_guilds = set()

    @commands.command(name="nsfw-toggle")
    @commands.has_permissions(administrator=True)
    async def nsfw_toggle(self, ctx):
        """Enable/disable NSFW commands for this server"""
        if ctx.guild.id in self.enabled_guilds:
            self.enabled_guilds.remove(ctx.guild.id)
            await ctx.send("🔞 NSFW commands have been **disabled** for this server.")
        else:
            self.enabled_guilds.add(ctx.guild.id)
            await ctx.send("🔞 NSFW commands have been **enabled** for this server.")

    @commands.command(name="waifu-nsfw")
    async def waifu_nsfw(self, ctx):
        """NSFW waifu image"""
        if ctx.guild.id not in self.enabled_guilds:
            await ctx.send("❌ NSFW commands are not enabled in this server. Use `!nsfw-toggle` to enable.")
            return
        
        if not ctx.channel.is_nsfw():
            await ctx.send("❌ This command can only be used in NSFW channels!")
            return
        
        # Would call an NSFW API here
        await ctx.send("🔞 NSFW Waifu feature coming soon!")

    @commands.command(name="hentai")
    async def hentai(self, ctx):
        """Random hentai"""
        if ctx.guild.id not in self.enabled_guilds or not ctx.channel.is_nsfw():
            await ctx.send("❌ This command requires NSFW to be enabled and used in an NSFW channel.")
            return
        await ctx.send("🔞 Hentai feature coming soon!")

async def setup(bot):
    await bot.add_cog(NSFWOptional(bot))