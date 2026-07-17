import discord
from discord.ext import commands
import random
import aiohttp
import json

class FunExplosion(commands.Cog):
    """Fun commands - Memes, jokes, facts, and text manipulation"""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="meme")
    async def meme(self, ctx):
        """Get a random meme"""
        # Using a free meme API
        async with aiohttp.ClientSession() as session:
            async with session.get("https://meme-api.com/gimme") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    embed = discord.Embed(title=data["title"], color=discord.Color.blue())
                    embed.set_image(url=data["url"])
                    embed.set_footer(text=f"Subreddit: r/{data['subreddit']}")
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ Failed to fetch meme!")

    @commands.command(name="joke")
    async def joke(self, ctx):
        """Get a random joke"""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://v2.jokeapi.dev/joke/Any?type=twopart") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data["type"] == "twopart":
                        await ctx.send(f"**{data['setup']}**\n\n{data['delivery']}")
                    else:
                        await ctx.send(data["joke"])
                else:
                    await ctx.send("❌ Failed to fetch joke!")

    @commands.command(name="dad-joke")
    async def dad_joke(self, ctx):
        """Get a dad joke"""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://icanhazdadjoke.com/", headers={"Accept": "application/json"}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    await ctx.send(f"👨 {data['joke']}")
                else:
                    await ctx.send("❌ Failed to fetch dad joke!")

    @commands.command(name="fact")
    async def fact(self, ctx):
        """Get a random fact"""
        facts = [
            "🐘 Elephants are the only mammals that can't jump.",
            "🦒 Giraffes have no vocal cords.",
            "🌊 The Pacific Ocean is the largest ocean on Earth.",
            "🌍 Antarctica is the driest continent on Earth.",
            "🦷 Human teeth are as hard as diamonds."
        ]
        await ctx.send(f"💡 {random.choice(facts)}")

    @commands.command(name="urban")
    async def urban(self, ctx, *, word: str):
        """Urban Dictionary definition"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.urbandictionary.com/v0/define?term={word}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data["list"]:
                        definition = data["list"][0]["definition"]
                        example = data["list"][0]["example"]
                        embed = discord.Embed(title=f"📖 {word}", description=definition[:2000], color=discord.Color.blue())
                        embed.add_field(name="Example", value=example[:1000], inline=False)
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(f"❌ No definition found for **{word}**")
                else:
                    await ctx.send("❌ Failed to fetch definition!")

    @commands.command(name="reverse-text")
    async def reverse_text(self, ctx, *, text: str):
        """Reverse a text string"""
        await ctx.send(text[::-1])

    @commands.command(name="mock-text")
    async def mock_text(self, ctx, *, text: str):
        """Mocking text format"""
        mocked = "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text))
        await ctx.send(mocked)

    @commands.command(name="clap-text")
    async def clap_text(self, ctx, *, text: str):
        """Clap format text"""
        await ctx.send("👏 " + " 👏 ".join(text.split()))

    @commands.command(name="emojify")
    async def emojify(self, ctx, *, text: str):
        """Emojify text"""
        emoji_map = {
            'a': '🇦', 'b': '🇧', 'c': '🇨', 'd': '🇩', 'e': '🇪',
            'f': '🇫', 'g': '🇬', 'h': '🇭', 'i': '🇮', 'j': '🇯',
            'k': '🇰', 'l': '🇱', 'm': '🇲', 'n': '🇳', 'o': '🇴',
            'p': '🇵', 'q': '🇶', 'r': '🇷', 's': '🇸', 't': '🇹',
            'u': '🇺', 'v': '🇻', 'w': '🇼', 'x': '🇽', 'y': '🇾', 'z': '🇿',
            ' ': '   '
        }
        result = "".join(emoji_map.get(c.lower(), c) for c in text)
        await ctx.send(result)

    @commands.command(name="spoiler")
    async def spoiler(self, ctx, *, text: str):
        """Make text a spoiler"""
        await ctx.send("||" + text + "||")

    @commands.command(name="binary")
    async def binary(self, ctx, *, text: str):
        """Convert text to binary"""
        binary_str = " ".join(format(ord(c), '08b') for c in text)
        await ctx.send(f"🔢 `{binary_str}`")

    @commands.command(name="morse")
    async def morse(self, ctx, *, text: str):
        """Convert text to Morse code"""
        morse_map = {
            'a': '.-', 'b': '-...', 'c': '-.-.', 'd': '-..', 'e': '.',
            'f': '..-.', 'g': '--.', 'h': '....', 'i': '..', 'j': '.---',
            'k': '-.-', 'l': '.-..', 'm': '--', 'n': '-.', 'o': '---',
            'p': '.--.', 'q': '--.-', 'r': '.-.', 's': '...', 't': '-',
            'u': '..-', 'v': '...-', 'w': '.--', 'x': '-..-', 'y': '-.--', 'z': '--..',
            '0': '-----', '1': '.----', '2': '..---', '3': '...--', '4': '....-',
            '5': '.....', '6': '-....', '7': '--...', '8': '---..', '9': '----.',
            ' ': '/'
        }
        result = " ".join(morse_map.get(c.lower(), c) for c in text)
        await ctx.send(f"📡 `{result}`")

    @commands.command(name="qrcode")
    async def qrcode(self, ctx, *, text: str):
        """Generate a QR code"""
        await ctx.send(f"📱 QR Code generated for: **{text}**\nhttps://api.qrserver.com/v1/create-qr-code/?size=300x300&data={text.replace(' ', '%20')}")

    @commands.command(name="random-number")
    async def random_number(self, ctx, min_num: int, max_num: int):
        """Generate a random number"""
        if min_num > max_num:
            min_num, max_num = max_num, min_num
        await ctx.send(f"🎲 Random number: **{random.randint(min_num, max_num)}**")

    @commands.command(name="random-color")
    async def random_color(self, ctx):
        """Generate a random hex color"""
        color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        await ctx.send(f"🎨 Random Hex Color: **{color}**")

    @commands.command(name="random-emoji")
    async def random_emoji(self, ctx):
        """Get a random emoji"""
        emojis = ["😂", "❤️", "😍", "🤣", "😊", "💕", "✨", "🔥", "😎", "💀"]
        await ctx.send(random.choice(emojis))

    @commands.command(name="random-pick")
    async def random_pick(self, ctx, *options):
        """Pick a random option from a list"""
        if len(options) < 2:
            await ctx.send("❌ Please provide at least 2 options!")
            return
        await ctx.send(f"🎯 I pick: **{random.choice(options)}**")

    @commands.command(name="decision")
    async def decision(self, ctx):
        """Yes/No decision helper"""
        result = random.choice(["Yes", "No", "Maybe", "Absolutely!", "Definitely not!", "Ask again later"])
        await ctx.send(f"❓ {result}")

    @commands.command(name="fortune")
    async def fortune(self, ctx):
        """Get a fortune cookie message"""
        fortunes = [
            "You will find great success in the near future.",
            "A pleasant surprise is waiting for you.",
            "Your hard work will soon pay off.",
            "A journey of a thousand miles begins with a single step.",
            "The best time to plant a tree was 20 years ago."
        ]
        await ctx.send(f"🥠 {random.choice(fortunes)}")

    @commands.command(name="horoscope")
    async def horoscope(self, ctx, *, sign: str):
        """Get your daily horoscope"""
        # Simplified mock horoscope
        messages = [
            "Today is a great day for taking risks.",
            "Focus on your inner peace today.",
            "Communication is key to your success.",
            "A financial opportunity is coming your way.",
            "Take a break and relax today."
        ]
        await ctx.send(f"♈ **{sign.title()}** Horoscope:\n{random.choice(messages)}")

async def setup(bot):
    await bot.add_cog(FunExplosion(bot))