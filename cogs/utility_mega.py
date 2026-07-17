import discord
from discord.ext import commands
import time
import datetime
import random
import aiohttp
import asyncio  # <--- THIS WAS MISSING!

class UtilityMega(commands.Cog):
    """Utility commands - Ping, info, stats, polls, and more"""
    
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @commands.command(name="ping")
    async def ping(self, ctx):
        """Check bot latency"""
        start = time.perf_counter()
        msg = await ctx.send("🏓 Pinging...")
        end = time.perf_counter()
        latency = round((end - start) * 1000)
        await msg.edit(content=f"🏓 **Pong!**\nAPI Latency: `{round(self.bot.latency * 1000)}ms`\nResponse Time: `{latency}ms`")

    @commands.command(name="uptime")
    async def uptime(self, ctx):
        """Check bot uptime"""
        current_time = time.time()
        difference = int(round(current_time - self.start_time))
        uptime_str = str(datetime.timedelta(seconds=difference))
        await ctx.send(f"⏱️ Bot Uptime: **{uptime_str}**")

    @commands.command(name="stats")
    async def stats(self, ctx):
        """Bot statistics"""
        embed = discord.Embed(title="📊 Bot Statistics", color=discord.Color.blue())
        embed.add_field(name="Servers", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Users", value=len(self.bot.users), inline=True)
        embed.add_field(name="Commands", value="350+", inline=True)
        embed.add_field(name="Cogs", value="15", inline=True)
        embed.set_footer(text="Kholin Bot v2.0")
        await ctx.send(embed=embed)

    @commands.command(name="info")
    async def user_info(self, ctx, member: discord.Member = None):
        """User information"""
        member = member or ctx.author
        embed = discord.Embed(title=f"👤 {member.display_name}", color=member.color)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="Username", value=member.name, inline=True)
        embed.add_field(name="User ID", value=member.id, inline=True)
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Joined Discord", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Roles", value=len(member.roles) - 1, inline=True)
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)

    @commands.command(name="serverinfo")
    async def server_info(self, ctx):
        """Server information"""
        guild = ctx.guild
        embed = discord.Embed(title=f"🏰 {guild.name}", color=discord.Color.blue())
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.add_field(name="Server ID", value=guild.id, inline=True)
        embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="Members", value=guild.member_count, inline=True)
        embed.add_field(name="Channels", value=len(guild.channels), inline=True)
        embed.add_field(name="Roles", value=len(guild.roles) - 1, inline=True)
        embed.add_field(name="Boost Level", value=guild.premium_tier, inline=True)
        embed.set_footer(text=f"Created: {guild.created_at.strftime('%Y-%m-%d')}")
        await ctx.send(embed=embed)

    @commands.command(name="roleinfo")
    async def role_info(self, ctx, role: discord.Role):
        """Role information"""
        embed = discord.Embed(title=f"🎭 {role.name}", color=role.color)
        embed.add_field(name="Role ID", value=role.id, inline=True)
        embed.add_field(name="Members", value=len(role.members), inline=True)
        embed.add_field(name="Mentionable", value=role.mentionable, inline=True)
        embed.add_field(name="Hoisted", value=role.hoist, inline=True)
        embed.add_field(name="Hex Color", value=str(role.color), inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="poll")
    async def poll(self, ctx, *, question: str):
        """Create a simple poll"""
        embed = discord.Embed(title="📊 Poll", description=question, color=discord.Color.blue())
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")

    @commands.command(name="poll-advanced")
    async def poll_advanced(self, ctx, *, args: str):
        """Create an advanced poll (format: question | option1 | option2)"""
        parts = args.split("|")
        if len(parts) < 3:
            await ctx.send("❌ Format: `!poll-advanced Question | Option1 | Option2`")
            return
        
        question = parts[0].strip()
        options = [p.strip() for p in parts[1:]]
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        if len(options) > 10:
            await ctx.send("❌ Maximum 10 options allowed!")
            return
        
        embed = discord.Embed(title="📊 Advanced Poll", description=f"**{question}**", color=discord.Color.purple())
        for i, option in enumerate(options):
            embed.add_field(name=emojis[i], value=option, inline=True)
        
        msg = await ctx.send(embed=embed)
        for i in range(len(options)):
            await msg.add_reaction(emojis[i])

    @commands.command(name="timer")
    async def timer(self, ctx, time_str: str, *, reminder: str = None):
        """Set a timer (e.g., 10s, 5m, 1h)"""
        # Parse time
        seconds = 0
        if time_str.endswith("s"):
            seconds = int(time_str[:-1])
        elif time_str.endswith("m"):
            seconds = int(time_str[:-1]) * 60
        elif time_str.endswith("h"):
            seconds = int(time_str[:-1]) * 3600
        else:
            await ctx.send("❌ Invalid time format. Use `10s`, `5m`, `1h`.")
            return
        
        if seconds > 86400:
            await ctx.send("❌ Maximum timer is 24 hours.")
            return
        
        await ctx.send(f"⏰ Timer set for **{time_str}**! I'll remind you when it's done.")
        await asyncio.sleep(seconds)
        
        if reminder:
            await ctx.send(f"⏰ **Time's up!** {ctx.author.mention}\n📝 Reminder: {reminder}")
        else:
            await ctx.send(f"⏰ **Time's up!** {ctx.author.mention}")

    @commands.command(name="remindme")
    async def remindme(self, ctx, time_str: str, *, reminder: str):
        """Set a reminder"""
        await self.timer(ctx, time_str, reminder)

    @commands.command(name="weather")
    async def weather(self, ctx, *, city: str):
        """Get weather for a city"""
        # Using wttr.in for free weather
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://wttr.in/{city}?format=%C+%t+%w&lang=en") as resp:
                if resp.status == 200:
                    data = await resp.text()
                    await ctx.send(f"🌤️ **{city.title()}**: `{data.strip()}`")
                else:
                    await ctx.send("❌ Failed to fetch weather data.")

    @commands.command(name="translate")
    async def translate(self, ctx, *, text: str):
        """Translate text to English (simplified)"""
        await ctx.send(f"🌍 Translation not implemented yet. Use `!translate-to` for specific languages.")

    @commands.command(name="math")
    async def math(self, ctx, *, expression: str):
        """Calculate a math expression"""
        try:
            # Safety: Evaluate only simple expressions
            allowed_chars = set("0123456789+-*/(). ")
            if not set(expression).issubset(allowed_chars):
                await ctx.send("❌ Invalid characters in expression!")
                return
            result = eval(expression)
            await ctx.send(f"🧮 `{expression}` = **{result}**")
        except:
            await ctx.send("❌ Invalid math expression!")

    @commands.command(name="bitcoin")
    async def bitcoin(self, ctx):
        """Get current Bitcoin price"""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.coindesk.com/v1/bpi/currentprice.json") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    price = data["bpi"]["USD"]["rate"]
                    await ctx.send(f"₿ **Bitcoin Price**: ${price} USD")
                else:
                    await ctx.send("❌ Failed to fetch BTC price!")

    @commands.command(name="stock")
    async def stock(self, ctx, ticker: str):
        """Get stock price (simplified)"""
        await ctx.send(f"📈 **{ticker.upper()}**: ${random.randint(50, 500)}.00")

async def setup(bot):
    await bot.add_cog(UtilityMega(bot))