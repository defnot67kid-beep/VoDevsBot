import discord
from discord.ext import commands
import asyncio  # FIXED: Added missing import
import datetime

class ModerationElite(commands.Cog):
    """Elite moderation tools - Warnings, mutes, bans, and channel management"""
    
    def __init__(self, bot):
        self.bot = bot
        self.warnings = {}  # guild_id -> {user_id: [warnings]}

    @commands.command(name="warn")
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Warn a user"""
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        
        if guild_id not in self.warnings:
            self.warnings[guild_id] = {}
        if user_id not in self.warnings[guild_id]:
            self.warnings[guild_id][user_id] = []
        
        self.warnings[guild_id][user_id].append({
            "reason": reason,
            "moderator": ctx.author.name,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        await ctx.send(f"⚠️ {member.mention} has been warned. Reason: **{reason}**")
        try:
            await member.send(f"You have been warned in **{ctx.guild.name}**. Reason: {reason}")
        except:
            pass

    @commands.command(name="warnings")
    @commands.has_permissions(kick_members=True)
    async def warnings(self, ctx, member: discord.Member):
        """View a user's warnings"""
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        
        if guild_id not in self.warnings or user_id not in self.warnings[guild_id]:
            await ctx.send(f"✅ {member.mention} has no warnings.")
            return
        
        warning_list = self.warnings[guild_id][user_id]
        embed = discord.Embed(title=f"⚠️ Warnings for {member.display_name}", color=discord.Color.orange())
        for i, warn in enumerate(warning_list, 1):
            embed.add_field(
                name=f"Warning #{i}",
                value=f"Reason: {warn['reason']}\nMod: {warn['moderator']}",
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.command(name="clear-warnings")
    @commands.has_permissions(kick_members=True)
    async def clear_warnings(self, ctx, member: discord.Member):
        """Clear a user's warnings"""
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        
        if guild_id in self.warnings and user_id in self.warnings[guild_id]:
            del self.warnings[guild_id][user_id]
            await ctx.send(f"✅ All warnings cleared for {member.mention}.")
        else:
            await ctx.send(f"❌ {member.mention} has no warnings to clear.")

    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, duration: str = "5m", *, reason: str = "No reason"):
        """Mute a user"""
        # Parse duration
        seconds = 0
        if duration.endswith("s"):
            seconds = int(duration[:-1])
        elif duration.endswith("m"):
            seconds = int(duration[:-1]) * 60
        elif duration.endswith("h"):
            seconds = int(duration[:-1]) * 3600
        else:
            seconds = 300  # Default 5 minutes
        
        await member.timeout(datetime.timedelta(seconds=seconds), reason=reason)
        await ctx.send(f"🔇 {member.mention} has been muted for **{duration}**. Reason: {reason}")

    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        """Unmute a user"""
        await member.timeout(None)
        await ctx.send(f"🔊 {member.mention} has been unmuted.")

    @commands.command(name="mkick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason"):
        """Kick a user"""
        await member.kick(reason=reason)
        await ctx.send(f"👢 {member.mention} has been kicked. Reason: **{reason}**")

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason"):
        """Ban a user"""
        await member.ban(reason=reason)
        await ctx.send(f"🔨 {member.mention} has been banned. Reason: **{reason}**")

    @commands.command(name="softban")
    @commands.has_permissions(ban_members=True)
    async def softban(self, ctx, member: discord.Member, *, reason: str = "No reason"):
        """Softban a user (ban + delete messages)"""
        await member.ban(reason=reason, delete_message_days=1)
        await member.unban(reason="Softban completed")
        await ctx.send(f"🧹 {member.mention} has been softbanned. Reason: **{reason}**")

    @commands.command(name="temp-ban")
    @commands.has_permissions(ban_members=True)
    async def temp_ban(self, ctx, member: discord.Member, duration: str, *, reason: str = "No reason"):
        """Temporarily ban a user"""
        # Parse duration
        seconds = 0
        if duration.endswith("h"):
            seconds = int(duration[:-1]) * 3600
        elif duration.endswith("d"):
            seconds = int(duration[:-1]) * 86400
        else:
            seconds = 86400  # Default 1 day
        
        await member.ban(reason=reason)
        await ctx.send(f"🔨 {member.mention} has been banned for **{duration}**. Reason: **{reason}**")
        
        await asyncio.sleep(seconds)
        
        try:
            await member.unban(reason="Temp ban expired")
            await ctx.send(f"✅ {member.mention} has been unbanned (temp ban expired).")
        except:
            pass

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int):
        """Unban a user by ID"""
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"✅ Unbanned **{user.name}**.")

    @commands.command(name="lockdown")
    @commands.has_permissions(manage_channels=True)
    async def lockdown(self, ctx):
        """Lock a channel"""
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(f"🔒 {ctx.channel.mention} has been locked.")

    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        """Unlock a channel"""
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
        await ctx.send(f"🔓 {ctx.channel.mention} has been unlocked.")

    @commands.command(name="slowmode")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int):
        """Set slowmode in a channel"""
        if seconds > 21600:
            await ctx.send("❌ Maximum slowmode is 6 hours (21600 seconds).")
            return
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.send(f"🐢 Slowmode set to **{seconds}** seconds in {ctx.channel.mention}.")

    @commands.command(name="clear")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = 10):
        """Clear messages in the channel"""
        if amount > 100:
            await ctx.send("❌ You can only delete up to 100 messages at a time.")
            return
        await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"🗑️ Deleted **{amount}** messages.")
        await asyncio.sleep(3)
        await msg.delete()

    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        """Purge messages"""
        await self.clear(ctx, amount)

    @commands.command(name="announce")
    @commands.has_permissions(mention_everyone=True)
    async def announce(self, ctx, *, message: str):
        """Make an announcement"""
        embed = discord.Embed(title="📢 Announcement", description=message, color=discord.Color.blue())
        embed.set_footer(text=f"Announced by {ctx.author}")
        await ctx.send("@everyone", embed=embed)

    @commands.command(name="ticket")
    async def ticket(self, ctx):
        """Open a support ticket"""
        await ctx.send("🎫 Support ticket system coming soon!")

async def setup(bot):
    await bot.add_cog(ModerationElite(bot))