import discord
from discord.ext import commands
import random
import aiohttp

class AnimeWeeb(commands.Cog):
    """Anime and weeb commands - Anime info, waifus, and quotes"""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="waifu")
    async def waifu(self, ctx):
        """Get a random waifu"""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.waifu.pics/sfw/waifu") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embed = discord.Embed(title="🌸 Waifu", color=discord.Color.pink())
                    embed.set_image(url=data["url"])
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ Failed to fetch waifu!")

    @commands.command(name="husbando")
    async def husbando(self, ctx):
        """Get a random husbando"""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.waifu.pics/sfw/husbando") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embed = discord.Embed(title="🌟 Husbando", color=discord.Color.blue())
                    embed.set_image(url=data["url"])
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ Failed to fetch husbando!")

    @commands.command(name="anime-quote")
    async def anime_quote(self, ctx):
        """Get a random anime quote"""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://anime-quotes-api.vercel.app/api/random") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    await ctx.send(f"**{data['quote']}**\n- {data['character']} ({data['anime']})")
                else:
                    await ctx.send("❌ Failed to fetch quote!")

    @commands.command(name="anime")
    async def anime(self, ctx, *, anime_name: str):
        """Search for anime info"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.jikan.moe/v4/anime?q={anime_name}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data["data"]:
                        anime = data["data"][0]
                        embed = discord.Embed(title=anime["title"], description=anime["synopsis"][:2000], color=discord.Color.red())
                        embed.set_thumbnail(url=anime["images"]["jpg"]["image_url"])
                        embed.add_field(name="Score", value=anime["score"], inline=True)
                        embed.add_field(name="Episodes", value=anime["episodes"], inline=True)
                        embed.add_field(name="Status", value=anime["status"], inline=True)
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(f"❌ No anime found for **{anime_name}**")
                else:
                    await ctx.send("❌ Failed to fetch anime data!")

    @commands.command(name="character")
    async def character(self, ctx, *, character_name: str):
        """Search for anime character"""
        await ctx.send(f"👤 Character information for **{character_name}** coming soon!")

async def setup(bot):
    await bot.add_cog(AnimeWeeb(bot))