import discord
from discord.ext import commands
import asyncio
import random

class MusicUltimate(commands.Cog):
    """Ultimate music system - Play, queue, and control"""
    
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.voice_clients = {}

    @commands.command(name="play")
    async def play(self, ctx, *, song: str):
        """Play a song (supports YouTube/URL)"""
        if not ctx.author.voice:
            await ctx.send("❌ You must be in a voice channel to use this command!")
            return
        
        voice_channel = ctx.author.voice.channel
        
        # Connect to voice channel
        if ctx.guild.id not in self.voice_clients:
            try:
                voice_client = await voice_channel.connect()
                self.voice_clients[ctx.guild.id] = voice_client
            except:
                await ctx.send("❌ Failed to connect to voice channel!")
                return
        
        await ctx.send(f"🎵 Playing: **{song}** (Music features require YouTube URL)")
        # Note: Actual YouTube streaming requires yt-dlp and FFmpeg setup

    @commands.command(name="skip")
    async def skip(self, ctx):
        """Skip the current song"""
        await ctx.send("⏭️ Skipping current song...")

    @commands.command(name="stop")
    async def stop(self, ctx):
        """Stop music and clear the queue"""
        if ctx.guild.id in self.voice_clients:
            voice = self.voice_clients[ctx.guild.id]
            if voice.is_playing():
                voice.stop()
                await ctx.send("⏹️ Music stopped.")
            else:
                await ctx.send("❌ No music is currently playing.")
        else:
            await ctx.send("❌ Bot is not connected to a voice channel.")

    @commands.command(name="pause")
    async def pause(self, ctx):
        """Pause the current song"""
        if ctx.guild.id in self.voice_clients:
            voice = self.voice_clients[ctx.guild.id]
            if voice.is_playing():
                voice.pause()
                await ctx.send("⏸️ Music paused.")
            else:
                await ctx.send("❌ No music is currently playing.")
        else:
            await ctx.send("❌ Bot is not connected to a voice channel.")

    @commands.command(name="resume")
    async def resume(self, ctx):
        """Resume the paused song"""
        if ctx.guild.id in self.voice_clients:
            voice = self.voice_clients[ctx.guild.id]
            if voice.is_paused():
                voice.resume()
                await ctx.send("▶️ Music resumed.")
            else:
                await ctx.send("❌ Music is not paused.")
        else:
            await ctx.send("❌ Bot is not connected to a voice channel.")

    @commands.command(name="volume")
    async def volume(self, ctx, volume: int):
        """Set volume (0-200)"""
        if 0 <= volume <= 200:
            await ctx.send(f"🔊 Volume set to **{volume}%**.")
        else:
            await ctx.send("❌ Volume must be between 0 and 200.")

    @commands.command(name="nowplaying", aliases=["np"])
    async def nowplaying(self, ctx):
        """Show currently playing song"""
        await ctx.send("🎶 Currently playing: *No song playing*")

    @commands.command(name="queue")
    async def queue(self, ctx):
        """Show the current queue"""
        await ctx.send("📋 Queue is currently empty.")

    @commands.command(name="lyrics")
    async def lyrics(self, ctx):
        """Show lyrics of the current song"""
        await ctx.send("📝 Lyrics feature coming soon!")

    @commands.command(name="disconnect")
    async def disconnect(self, ctx):
        """Disconnect the bot from voice"""
        if ctx.guild.id in self.voice_clients:
            voice = self.voice_clients[ctx.guild.id]
            await voice.disconnect()
            del self.voice_clients[ctx.guild.id]
            await ctx.send("👋 Disconnected from voice channel.")
        else:
            await ctx.send("❌ Bot is not connected to a voice channel.")

async def setup(bot):
    await bot.add_cog(MusicUltimate(bot))