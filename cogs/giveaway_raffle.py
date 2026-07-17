import discord
from discord.ext import commands
import asyncio
import random
import datetime

class GiveawayRaffle(commands.Cog):
    """Giveaway and raffle system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways = {}

    @commands.command(name="gstart")
    @commands.has_permissions(manage_messages=True)
    async def gstart(self, ctx, duration: str, winners: int, *, prize: str):
        """Start a giveaway"""
        # Parse duration
        seconds = 0
        if duration.endswith("s"):
            seconds = int(duration[:-1])
        elif duration.endswith("m"):
            seconds = int(duration[:-1]) * 60
        elif duration.endswith("h"):
            seconds = int(duration[:-1]) * 3600
        elif duration.endswith("d"):
            seconds = int(duration[:-1]) * 86400
        else:
            seconds = 60  # Default 1 minute
        
        embed = discord.Embed(
            title=f"🎉 Giveaway: {prize}",
            description=f"React with 🎉 to enter!\nEnds in **{duration}**",
            color=discord.Color.gold()
        )
        embed.add_field(name="Host", value=ctx.author.mention, inline=True)
        embed.add_field(name="Winners", value=winners, inline=True)
        
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("🎉")
        
        self.active_giveaways[msg.id] = {
            "end_time": datetime.datetime.now() + datetime.timedelta(seconds=seconds),
            "winners": winners,
            "prize": prize,
            "host": ctx.author.id,
            "channel": ctx.channel.id
        }
        
        await asyncio.sleep(seconds)
        
        # Get reactors
        msg = await ctx.channel.fetch_message(msg.id)
        users = [u for u in await msg.reactions[0].users().flatten() if not u.bot]
        
        if len(users) < winners:
            await ctx.send(f"❌ Not enough participants for the giveaway!")
            return
        
        winners_list = random.sample(users, winners)
        winner_mentions = ", ".join([w.mention for w in winners_list])
        
        end_embed = discord.Embed(
            title=f"🎉 Giveaway Ended!",
            description=f"Prize: **{prize}**\nWinners: {winner_mentions}",
            color=discord.Color.green()
        )
        await ctx.send(embed=end_embed)
        
        del self.active_giveaways[msg.id]

    @commands.command(name="gend")
    @commands.has_permissions(manage_messages=True)
    async def gend(self, ctx, message_id: int):
        """Force end a giveaway"""
        if message_id not in self.active_giveaways:
            await ctx.send("❌ Giveaway not found or already ended.")
            return
        
        giveaway = self.active_giveaways[message_id]
        channel = self.bot.get_channel(giveaway["channel"])
        
        if channel:
            msg = await channel.fetch_message(message_id)
            users = [u for u in await msg.reactions[0].users().flatten() if not u.bot]
            
            if users:
                winners_list = random.sample(users, min(giveaway["winners"], len(users)))
                winner_mentions = ", ".join([w.mention for w in winners_list])
                
                end_embed = discord.Embed(
                    title=f"🎉 Giveaway Ended Early!",
                    description=f"Prize: **{giveaway['prize']}**\nWinners: {winner_mentions}",
                    color=discord.Color.green()
                )
                await ctx.send(embed=end_embed)
            
            del self.active_giveaways[message_id]

async def setup(bot):
    await bot.add_cog(GiveawayRaffle(bot))