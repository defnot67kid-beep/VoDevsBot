import discord
from discord.ext import commands
import random

class VoiceChannel(commands.Cog):
    """Voice channel management commands"""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="vcmove")
    @commands.has_permissions(move_members=True)
    async def vc_move(self, ctx, target: discord.VoiceChannel, *members: discord.Member):
        """Move members to a voice channel"""
        if not members:
            await ctx.send("❌ You must specify members to move!")
            return
        
        moved = 0
        for member in members:
            if member.voice and member.voice.channel:
                await member.move_to(target)
                moved += 1
        
        await ctx.send(f"✅ Moved **{moved}** members to {target.mention}")

    @commands.command(name="vckick")
    @commands.has_permissions(move_members=True)
    async def vc_kick(self, ctx, member: discord.Member):
        """Disconnect a user from voice channel"""
        if member.voice and member.voice.channel:
            await member.move_to(None)
            await ctx.send(f"👢 {member.mention} has been disconnected from voice.")
        else:
            await ctx.send(f"❌ {member.mention} is not in a voice channel.")

    @commands.command(name="vcjoin")
    async def vc_join(self, ctx):
        """Make the bot join your voice channel"""
        if not ctx.author.voice:
            await ctx.send("❌ You are not in a voice channel.")
            return
        
        channel = ctx.author.voice.channel
        try:
            await channel.connect()
            await ctx.send(f"✅ Joined {channel.name}.")
        except:
            await ctx.send("❌ Failed to join voice channel.")

    @commands.command(name="vcleave")
    async def vc_leave(self, ctx):
        """Make the bot leave the voice channel"""
        if ctx.guild.voice_client:
            await ctx.guild.voice_client.disconnect()
            await ctx.send("✅ Left voice channel.")
        else:
            await ctx.send("❌ I am not in a voice channel.")

async def setup(bot):
    await bot.add_cog(VoiceChannel(bot))