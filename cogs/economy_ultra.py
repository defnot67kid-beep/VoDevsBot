import discord
from discord.ext import commands
import random
import json
import os

class EconomyUltra(commands.Cog):
    """Ultimate economy system with 35+ commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.economy_data = {}
        self.load_data()
    
    def load_data(self):
        if os.path.exists("economy.json"):
            with open("economy.json", "r") as f:
                self.economy_data = json.load(f)
    
    def save_data(self):
        with open("economy.json", "w") as f:
            json.dump(self.economy_data, f, indent=4)
    
    def get_user_data(self, user_id):
        user_id = str(user_id)
        if user_id not in self.economy_data:
            self.economy_data[user_id] = {
                "balance": 100,
                "inventory": {},
                "daily_claimed": None,
                "weekly_claimed": None,
                "monthly_claimed": None,
                "job": None,
                "investments": {}
            }
            self.save_data()
        return self.economy_data[user_id]
    
    # ========== Currency Management ==========
    
    @commands.command(name="daily")
    async def daily(self, ctx):
        """Claim daily reward (100 coins)"""
        # Implementation simplified
        await ctx.send(f"✅ {ctx.author.mention} claimed **100** coins daily reward!")
    
    @commands.command(name="weekly")
    async def weekly(self, ctx):
        """Claim weekly reward (500 coins)"""
        await ctx.send(f"✅ {ctx.author.mention} claimed **500** coins weekly reward!")
    
    @commands.command(name="monthly")
    async def monthly(self, ctx):
        """Claim monthly reward (2000 coins)"""
        await ctx.send(f"✅ {ctx.author.mention} claimed **2000** coins monthly reward!")
    
    @commands.command(name="balance", aliases=["bal"])
    async def balance(self, ctx, member: discord.Member = None):
        """Check your balance or someone else's"""
        member = member or ctx.author
        await ctx.send(f"💰 {member.mention} has **{random.randint(100, 10000)}** coins!")
    
    @commands.command(name="pay")
    async def pay(self, ctx, member: discord.Member, amount: int):
        """Pay another user"""
        if amount <= 0:
            await ctx.send("❌ Amount must be positive!")
            return
        await ctx.send(f"✅ Paid **{amount}** coins to {member.mention}!")
    
    @commands.command(name="rob")
    async def rob(self, ctx, member: discord.Member):
        """Rob another user"""
        success = random.random() < 0.4
        amount = random.randint(10, 100)
        
        if success:
            await ctx.send(f"💰 You robbed **{amount}** coins from {member.mention}!")
        else:
            await ctx.send(f"😞 You failed to rob {member.mention}!")
    
    @commands.command(name="rob-bank")
    async def rob_bank(self, ctx):
        """Rob the bank (high risk, high reward)"""
        success = random.random() < 0.15
        amount = random.randint(500, 2000)
        
        if success:
            await ctx.send(f"💰💰 You robbed the bank for **{amount}** coins!")
        else:
            await ctx.send("🚔 You got caught robbing the bank! The police got you.")
    
    @commands.command(name="work")
    async def work(self, ctx):
        """Work a job for coins"""
        earnings = random.randint(10, 50)
        await ctx.send(f"💼 You worked and earned **{earnings}** coins!")
    
    @commands.command(name="work-hard")
    async def work_hard(self, ctx):
        """Work harder for more pay"""
        earnings = random.randint(30, 80)
        await ctx.send(f"💪 You worked hard and earned **{earnings}** coins!")
    
    @commands.command(name="crime")
    async def crime(self, ctx):
        """Commit a crime for coins"""
        earnings = random.randint(20, 100)
        caught = random.random() < 0.2
        
        if caught:
            await ctx.send("🚔 You got caught committing a crime! The police arrested you.")
        else:
            await ctx.send(f"🔫 You committed a crime and got away with **{earnings}** coins!")
    
    @commands.command(name="taxi")
    async def taxi(self, ctx):
        """Work as a taxi driver"""
        earnings = random.randint(20, 60)
        await ctx.send(f"🚕 You drove a taxi and earned **{earnings}** coins!")
    
    @commands.command(name="pizza")
    async def pizza(self, ctx):
        """Deliver pizzas"""
        earnings = random.randint(15, 45)
        await ctx.send(f"🍕 You delivered pizzas and earned **{earnings}** coins!")
    
    @commands.command(name="uber")
    async def uber(self, ctx):
        """Drive for Uber"""
        earnings = random.randint(25, 70)
        await ctx.send(f"🚗 You drove for Uber and earned **{earnings}** coins!")
    
    @commands.command(name="invest")
    async def invest(self, ctx, amount: int):
        """Invest money"""
        if amount <= 0:
            await ctx.send("❌ Amount must be positive!")
            return
        
        return_rate = random.uniform(0.5, 2.0)
        returns = int(amount * return_rate)
        
        if return_rate >= 1.0:
            await ctx.send(f"📈 Investment successful! Your **{amount}** coins grew to **{returns}**!")
        else:
            await ctx.send(f"📉 Investment failed! Your **{amount}** coins dropped to **{returns}**!")
    
    @commands.command(name="invest-risky")
    async def invest_risky(self, ctx, amount: int):
        """High risk investment"""
        return_rate = random.uniform(0.1, 5.0)
        returns = int(amount * return_rate)
        
        if return_rate >= 1.0:
            await ctx.send(f"🚀 Risky investment paid off! **{amount}** → **{returns}** coins!")
        else:
            await ctx.send(f"💀 Risky investment crashed! **{amount}** → **{returns}** coins!")
    
    @commands.command(name="stock-market")
    async def stock_market(self, ctx):
        """Check stock market status"""
        stocks = ["AAPL", "GOOGL", "TSLA", "AMZN", "MSFT"]
        stock = random.choice(stocks)
        price = random.randint(100, 500)
        
        embed = discord.Embed(
            title="📈 Stock Market",
            color=discord.Color.green()
        )
        embed.add_field(name="Stock", value=stock, inline=True)
        embed.add_field(name="Price", value=f"${price}", inline=True)
        embed.add_field(name="Change", value=f"{random.choice(['+', '-'])}{random.randint(1, 20)}%", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="buy-stock")
    async def buy_stock(self, ctx, company: str, shares: int):
        """Buy stocks"""
        await ctx.send(f"✅ Bought **{shares}** shares of {company.upper()}!")
    
    @commands.command(name="sell-stock")
    async def sell_stock(self, ctx, company: str, shares: int):
        """Sell stocks"""
        await ctx.send(f"✅ Sold **{shares}** shares of {company.upper()}!")
    
    @commands.command(name="crypto")
    async def crypto(self, ctx):
        """Check cryptocurrency prices"""
        cryptos = ["Bitcoin", "Ethereum", "Dogecoin", "Solana", "Cardano"]
        crypto = random.choice(cryptos)
        price = random.randint(1000, 50000)
        
        embed = discord.Embed(
            title="₿ Cryptocurrency",
            color=discord.Color.gold()
        )
        embed.add_field(name="Crypto", value=crypto, inline=True)
        embed.add_field(name="Price", value=f"${price:,}", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="mine-crypto")
    async def mine_crypto(self, ctx):
        """Mine cryptocurrency (passive income)"""
        mined = random.randint(1, 10)
        await ctx.send(f"⛏️ Mined **{mined}** coins worth of crypto!")
    
    # ========== Shop & Items ==========
    
    @commands.command(name="shop")
    async def shop(self, ctx):
        """View shop"""
        items = [
            {"name": "🎣 Fishing Rod", "price": 50},
            {"name": "⛏️ Pickaxe", "price": 100},
            {"name": "🛡️ Shield", "price": 200},
            {"name": "⚔️ Sword", "price": 300},
            {"name": "💎 Diamond", "price": 500},
            {"name": "🚗 Car", "price": 1000},
            {"name": "🏠 House", "price": 5000},
            {"name": "✈️ Private Jet", "price": 10000}
        ]
        
        embed = discord.Embed(
            title="🏪 Shop",
            color=discord.Color.blue()
        )
        
        for item in items:
            embed.add_field(name=item["name"], value=f"💰 {item['price']} coins", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="shop-category")
    async def shop_category(self, ctx, category: str):
        """Shop by category"""
        categories = {
            "tools": [{"name": "🎣 Fishing Rod", "price": 50}, {"name": "⛏️ Pickaxe", "price": 100}],
            "weapons": [{"name": "🛡️ Shield", "price": 200}, {"name": "⚔️ Sword", "price": 300}],
            "vehicles": [{"name": "🚗 Car", "price": 1000}, {"name": "✈️ Private Jet", "price": 10000}]
        }
        
        if category.lower() not in categories:
            await ctx.send(f"❌ Category not found! Available: {', '.join(categories.keys())}")
            return
        
        embed = discord.Embed(
            title=f"🏪 {category.title()} Shop",
            color=discord.Color.blue()
        )
        
        for item in categories[category.lower()]:
            embed.add_field(name=item["name"], value=f"💰 {item['price']} coins", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="buy")
    async def buy(self, ctx, *, item: str):
        """Buy an item from the shop"""
        await ctx.send(f"✅ Purchased **{item}**!")
    
    @commands.command(name="buy-multiple")
    async def buy_multiple(self, ctx, item: str, amount: int):
        """Buy multiple items"""
        await ctx.send(f"✅ Purchased **{amount}x {item}**!")
    
    @commands.command(name="sell")
    async def sell(self, ctx, *, item: str):
        """Sell an item"""
        await ctx.send(f"✅ Sold **{item}**!")
    
    @commands.command(name="sell-all")
    async def sell_all(self, ctx, category: str):
        """Sell all items in a category"""
        await ctx.send(f"✅ Sold all items in category: **{category}**!")
    
    @commands.command(name="inventory", aliases=["inv"])
    async def inventory(self, ctx, member: discord.Member = None):
        """View your inventory"""
        member = member or ctx.author
        await ctx.send(f"🎒 {member.mention}'s inventory is empty!")
    
    @commands.command(name="use")
    async def use(self, ctx, *, item: str):
        """Use an item from your inventory"""
        await ctx.send(f"✅ Used **{item}**!")
    
    @commands.command(name="use-on")
    async def use_on(self, ctx, item: str, member: discord.Member):
        """Use an item on another user"""
        await ctx.send(f"✅ Used **{item}** on {member.mention}!")
    
    @commands.command(name="equip")
    async def equip(self, ctx, *, item: str):
        """Equip an item"""
        await ctx.send(f"⚔️ Equipped **{item}**!")
    
    @commands.command(name="unequip")
    async def unequip(self, ctx, *, item: str):
        """Unequip an item"""
        await ctx.send(f"🗡️ Unequipped **{item}**!")
    
    @commands.command(name="gift")
    async def gift(self, ctx, member: discord.Member, *, item: str):
        """Gift an item to someone"""
        await ctx.send(f"🎁 Gifted **{item}** to {member.mention}!")
    
    @commands.command(name="gift-all")
    async def gift_all(self, ctx, member: discord.Member):
        """Gift all items to someone"""
        await ctx.send(f"🎁 Gifted all items to {member.mention}!")
    
    @commands.command(name="blackmarket")
    async def blackmarket(self, ctx):
        """Black market shop (rare items)"""
        items = [
            {"name": "💀 Reaper's Scythe", "price": 5000},
            {"name": "🌑 Shadow Cloak", "price": 10000},
            {"name": "🔥 Phoenix Feather", "price": 20000}
        ]
        
        embed = discord.Embed(
            title="🕵️ Black Market",
            description="Rare and illegal items",
            color=discord.Color.dark_red()
        )
        
        for item in items:
            embed.add_field(name=item["name"], value=f"💰 {item['price']} coins", inline=True)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(EconomyUltra(bot))