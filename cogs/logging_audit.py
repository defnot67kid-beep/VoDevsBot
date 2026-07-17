import discord
from discord.ext import commands
import datetime

class LoggingAudit(commands.Cog):
    """Advanced logging and audit system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.log_channels = {}

    @commands.command(name="set-logging")
    @commands.has_permissions(administrator=True)
    async def set_logging(self, ctx, channel: discord.TextChannel):
        """Set the logging channel for this server"""
        self.log_channels[ctx.guild.id] = channel.id
        await ctx.send(f"✅ Logging channel set to {channel.mention}")

    @commands.command(name="audit")
    @commands.has_permissions(view_audit_log=True)
    async def audit(self, ctx, limit: int = 5):
        """View recent audit log entries"""
        async for entry in ctx.guild.audit_logs(limit=limit):
            await ctx.send(f"**{entry.action.name}** by {entry.user.mention}\nTarget: {entry.target}\nReason: {entry.reason or 'No reason'}")

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild and message.guild.id in self.log_channels:
            channel = self.bot.get_channel(self.log_channels[message.guild.id])
            if channel:
                embed = discord.Embed(
                    title="🗑️ Message Deleted",
                    description=f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}\n**Content:** {message.content or 'Empty'}",
                    color=discord.Color.red()
                )
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.guild and before.guild.id in self.log_channels:
            channel = self.bot.get_channel(self.log_channels[before.guild.id])
            if channel:
                embed = discord.Embed(
                    title="✏️ Message Edited",
                    description=f"**Author:** {before.author.mention}\n**Channel:** {before.channel.mention}",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Before", value=before.content or "Empty", inline=False)
                embed.add_field(name="After", value=after.content or "Empty", inline=False)
                await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LoggingAudit(bot))