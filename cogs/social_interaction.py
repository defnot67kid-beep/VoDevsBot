import discord
from discord.ext import commands
import random

class SocialInteraction(commands.Cog):
    """Social interaction commands - Hug, kiss, slap, and more!"""
    
    def __init__(self, bot):
        self.bot = bot
        self.marriages = {}
        self.families = {}

    @commands.command(name="hug")
    async def hug(self, ctx, member: discord.Member):
        """Hug a user"""
        responses = [
            f"🤗 {ctx.author.mention} hugs {member.mention} tightly!",
            f"🤗 *Squish!* {ctx.author.mention} gives {member.mention} a big warm hug!",
            f"🤗 {ctx.author.mention} wraps their arms around {member.mention}."
        ]
        await ctx.send(random.choice(responses))

    @commands.command(name="kiss")
    async def kiss(self, ctx, member: discord.Member):
        """Kiss a user"""
        responses = [
            f"💋 {ctx.author.mention} kisses {member.mention}!",
            f"💋 *Mwah!* {ctx.author.mention} plants a kiss on {member.mention}'s cheek!",
            f"💋 {ctx.author.mention} and {member.mention} share a sweet kiss."
        ]
        await ctx.send(random.choice(responses))

    @commands.command(name="slap")
    async def slap(self, ctx, member: discord.Member):
        """Slap a user (joke)"""
        responses = [
            f"👋 {ctx.author.mention} slaps {member.mention}! *Ouch!*",
            f"👋 {ctx.author.mention} gives {member.mention} a good slap!",
            f"👋 *SMACK!* {ctx.author.mention} slaps {member.mention} across the face."
        ]
        await ctx.send(random.choice(responses))

    @commands.command(name="punch")
    async def punch(self, ctx, member: discord.Member):
        """Punch a user (joke)"""
        responses = [
            f"👊 {ctx.author.mention} punches {member.mention}!",
            f"👊 *BAM!* {ctx.author.mention} throws a punch at {member.mention}!",
            f"👊 {ctx.author.mention} winds up and punches {member.mention}!"
        ]
        await ctx.send(random.choice(responses))

    @commands.command(name="kick")
    async def kick_joke(self, ctx, member: discord.Member):
        """Joke kick a user"""
        await ctx.send(f"🦶 {ctx.author.mention} kicks {member.mention} into the shadow realm!")

    @commands.command(name="shoot")
    async def shoot(self, ctx, member: discord.Member):
        """Joke shoot a user"""
        await ctx.send(f"🔫 *Bang bang!* {ctx.author.mention} shoots {member.mention}! You're dead!")

    @commands.command(name="marry")
    async def marry(self, ctx, member: discord.Member):
        """Marry a user"""
        if member == ctx.author:
            await ctx.send("❌ You can't marry yourself!")
            return
        
        pair = tuple(sorted([ctx.author.id, member.id]))
        self.marriages[pair] = True
        await ctx.send(f"💍 Congratulations! {ctx.author.mention} and {member.mention} are now married!")

    @commands.command(name="divorce")
    async def divorce(self, ctx, member: discord.Member):
        """Divorce a user"""
        pair = tuple(sorted([ctx.author.id, member.id]))
        if pair in self.marriages:
            del self.marriages[pair]
            await ctx.send(f"💔 {ctx.author.mention} and {member.mention} are now divorced.")
        else:
            await ctx.send("❌ You aren't married to that user!")

    @commands.command(name="propose")
    async def propose(self, ctx, member: discord.Member):
        """Propose to a user"""
        await ctx.send(f"💍 {ctx.author.mention} gets down on one knee and proposes to {member.mention}!")

    @commands.command(name="adopt")
    async def adopt(self, ctx, member: discord.Member):
        """Adopt a user"""
        await ctx.send(f"👶 {ctx.author.mention} adopts {member.mention} as their child!")

    @commands.command(name="family")
    async def family(self, ctx):
        """View your family tree"""
        await ctx.send(f"🏠 {ctx.author.mention}'s family tree is currently under construction.")

    @commands.command(name="enemy")
    async def enemy(self, ctx, member: discord.Member):
        """Declare someone as your enemy"""
        await ctx.send(f"⚔️ {ctx.author.mention} has declared {member.mention} as their sworn enemy!")

    @commands.command(name="rival")
    async def rival(self, ctx, member: discord.Member):
        """Declare a rivalry"""
        await ctx.send(f"🏁 {ctx.author.mention} and {member.mention} are now eternal rivals!")

    @commands.command(name="pet")
    async def pet(self, ctx, member: discord.Member):
        """Pet a user"""
        await ctx.send(f"🐾 {ctx.author.mention} pets {member.mention} softly.")

    @commands.command(name="pat")
    async def pat(self, ctx, member: discord.Member):
        """Pat a user"""
        await ctx.send(f"✋ {ctx.author.mention} pats {member.mention} on the head. *Good job!*")

    @commands.command(name="boop")
    async def boop(self, ctx, member: discord.Member):
        """Boop a user"""
        await ctx.send(f"👉 *Boop!* {ctx.author.mention} boops {member.mention} on the nose!")

    @commands.command(name="nom")
    async def nom(self, ctx, member: discord.Member):
        """Nom on a user (joke)"""
        await ctx.send(f"🍽️ *Nom nom nom!* {ctx.author.mention} nibbles on {member.mention}!")

    @commands.command(name="bite")
    async def bite(self, ctx, member: discord.Member):
        """Bite a user"""
        await ctx.send(f"🦷 {ctx.author.mention} chomps down on {member.mention}!")

    @commands.command(name="cuddle")
    async def cuddle(self, ctx, member: discord.Member):
        """Cuddle a user"""
        await ctx.send(f"🥰 {ctx.author.mention} cuddles up with {member.mention}.")

    @commands.command(name="headpat")
    async def headpat(self, ctx, member: discord.Member):
        """Headpat a user"""
        await ctx.send(f"🤚 {ctx.author.mention} gives {member.mention} a gentle headpat.")

    @commands.command(name="compliment")
    async def compliment(self, ctx, member: discord.Member):
        """Compliment a user"""
        compliments = [
            f"💖 {member.mention}, you are absolutely wonderful!",
            f"💖 {member.mention}, you're a legend!",
            f"💖 {member.mention}, you're the best thing since sliced bread!"
        ]
        await ctx.send(random.choice(compliments))

    @commands.command(name="roast")
    async def roast(self, ctx, member: discord.Member):
        """Roast a user"""
        roasts = [
            f"🔥 {member.mention}, you're like a broken pencil... pointless.",
            f"🔥 {member.mention} is so short, they can see the bottom of a well.",
            f"🔥 {member.mention}'s brain is like a browser: 18 tabs open and all frozen."
        ]
        await ctx.send(random.choice(roasts))

    @commands.command(name="insult")
    async def insult(self, ctx, member: discord.Member):
        """Insult a user"""
        await ctx.send(f"😤 {ctx.author.mention} insults {member.mention}! How rude!")

    @commands.command(name="rate")
    async def rate(self, ctx, member: discord.Member):
        """Rate a user 1-10"""
        rating = random.randint(1, 10)
        await ctx.send(f"📊 I rate {member.mention} a **{rating}/10**!")

    @commands.command(name="ship")
    async def ship(self, ctx, member1: discord.Member, member2: discord.Member):
        """Ship two users together"""
        love_meter = random.randint(1, 100)
        hearts = "❤️" * (love_meter // 10) + "🖤" * (10 - (love_meter // 10))
        await ctx.send(f"💘 **{member1.display_name}** 💘 **{member2.display_name}**\nLove Meter: **{love_meter}%**\n{hearts}")

async def setup(bot):
    await bot.add_cog(SocialInteraction(bot))