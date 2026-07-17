import discord
from discord.ext import commands
import json
import os

class LevelingPro(commands.Cog):
    """Advanced leveling system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.leveling_data = {}
        self.load_data()
    
    def load_data(self):
        if os.path.exists("leveling.json"):
            with open("leveling.json", "r") as f:
                self.leveling_data = json.load(f)
    
    def save_data(self):
        with open("leveling.json", "w") as f:
            json.dump(self.leveling_data, f, indent=4)
    
    def get_user_xp(self, user_id):
        user_id = str(user_id)
        if user_id not in self.leveling_data:
            self.leveling_data[user_id] = {"xp": 0, "level": 1}
            self.save_data()
        return self.leveling_data[user_id]
    
    def calc_level(self, xp):
        return int((xp / 100) ** 0.5) + 1
    
    @commands.command(name="rank", aliases=["level"])
    async def rank(self, ctx, member: discord.Member = None):
        """Check your rank or someone else's"""
        member = member or ctx.author
        data = self.get_user_xp(member.id)
        level = data["level"]
        xp = data["xp"]
        next_level_xp = (level ** 2) * 100
        
        embed = discord.Embed(
            title=f"📊 {member.display_name}'s Rank",
            color=discord.Color.blue()
        )
        embed.add_field(name="Level", value=f"**{level}**", inline=True)
        embed.add_field(name="XP", value=f"{xp}/{next_level_xp}", inline=True)
        
        # Progress bar
        progress = int((xp / next_level_xp) * 20)
        bar = "█" * progress + "░" * (20 - progress)
        embed.add_field(name="Progress", value=f"`{bar}`", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="leaderboard", aliases=["lb"])
    async def leaderboard(self, ctx):
        """View XP leaderboard"""
        sorted_users = sorted(self.leveling_data.items(), key=lambda x: x[1]["xp"], reverse=True)[:10]
        
        embed = discord.Embed(
            title="🏆 XP Leaderboard",
            color=discord.Color.gold()
        )
        
        for i, (user_id, data) in enumerate(sorted_users, 1):
            try:
                user = await self.bot.fetch_user(int(user_id))
                embed.add_field(
                    name=f"{i}. {user.display_name}",
                    value=f"Level {data['level']} • {data['xp']} XP",
                    inline=False
                )
            except:
                embed.add_field(
                    name=f"{i}. Unknown User",
                    value=f"Level {data['level']} • {data['xp']} XP",
                    inline=False
                )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="lb-global")
    async def lb_global(self, ctx):
        """Global leaderboard"""
        await ctx.send("🌍 Global leaderboard coming soon!")
    
    @commands.command(name="lb-weekly")
    async def lb_weekly(self, ctx):
        """Weekly leaderboard"""
        await ctx.send("📅 Weekly leaderboard coming soon!")
    
    @commands.command(name="lb-monthly")
    async def lb_monthly(self, ctx):
        """Monthly leaderboard"""
        await ctx.send("📅 Monthly leaderboard coming soon!")
    
    @commands.command(name="xp")
    async def xp_check(self, ctx):
        """Check your XP"""
        data = self.get_user_xp(ctx.author.id)
        await ctx.send(f"⚡ You have **{data['xp']}** XP (Level {data['level']})")

async def setup(bot):
    await bot.add_cog(LevelingPro(bot))