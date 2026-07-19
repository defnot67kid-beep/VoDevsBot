import discord
from discord.ext import commands
import datetime
import asyncio

class GiveRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_date(self, date_str):
        """
        Parses dates in DD/MM/YYYY or DD-MM-YYYY format.
        Returns a datetime object or None if invalid.
        """
        try:
            # Try DD/MM/YYYY
            if "/" in date_str:
                day, month, year = map(int, date_str.split("/"))
                return datetime.datetime(year, month, day)
            # Try DD-MM-YYYY
            elif "-" in date_str:
                day, month, year = map(int, date_str.split("-"))
                return datetime.datetime(year, month, day)
        except:
            return None
        return None

    @commands.command(name="giveroletime")
    @commands.has_permissions(administrator=True)
    async def give_role_time(self, ctx, role: discord.Role, start_date: str, end_date: str):
        """
        [Admin] Gives a role to all members who joined between two dates.
        Usage: !giveroletime @Role 01/01/2024 31/12/2024
        """
        start = self.parse_date(start_date)
        end = self.parse_date(end_date)

        if not start or not end:
            return await ctx.send("❌ Invalid date format! Use `DD/MM/YYYY` (e.g., `01/01/2024`).")
        
        if start > end:
            return await ctx.send("❌ Start date must be before end date!")

        await ctx.send(f"⏳ Scanning members who joined between **{start.strftime('%d/%m/%Y')}** and **{end.strftime('%d/%m/%Y')}**...")

        members_added = 0
        members_skipped = 0
        failed_members = 0

        for member in ctx.guild.members:
            if member.bot:
                continue
            
            # Convert join time to date only
            join_date = member.joined_at.replace(tzinfo=None)
            
            if start <= join_date <= end:
                if role not in member.roles:
                    try:
                        await member.add_roles(role, reason=f"Role given via date range {start_date} to {end_date}")
                        members_added += 1
                    except discord.Forbidden:
                        failed_members += 1
                else:
                    members_skipped += 1

            # Small delay to prevent rate limiting
            if members_added % 10 == 0:
                await asyncio.sleep(0.5)

        embed = discord.Embed(
            title="✅ Role Distribution Complete",
            color=discord.Color.green()
        )
        embed.add_field(name="📅 Date Range", value=f"{start.strftime('%d/%m/%Y')} → {end.strftime('%d/%m/%Y')}", inline=False)
        embed.add_field(name="🎯 Role", value=role.mention, inline=True)
        embed.add_field(name="✅ Members Added", value=str(members_added), inline=True)
        embed.add_field(name="⏭️ Already Had Role", value=str(members_skipped), inline=True)
        embed.add_field(name="❌ Failed (Missing Perms)", value=str(failed_members), inline=True)

        await ctx.send(embed=embed)

    @commands.command(name="autogiveroletime")
    @commands.has_permissions(administrator=True)
    async def auto_give_role_time(self, ctx, role: discord.Role, end_date: str):
        """
        [Admin] Gives a role to ALL members who joined BEFORE a specific date.
        Usage: !autogiveroletime @Role 01/01/2024
        """
        end = self.parse_date(end_date)

        if not end:
            return await ctx.send("❌ Invalid date format! Use `DD/MM/YYYY` (e.g., `01/01/2024`).")

        await ctx.send(f"⏳ Scanning members who joined **before {end.strftime('%d/%m/%Y')}**...")

        members_added = 0
        members_skipped = 0
        failed_members = 0

        for member in ctx.guild.members:
            if member.bot:
                continue
            
            join_date = member.joined_at.replace(tzinfo=None)
            
            if join_date <= end:
                if role not in member.roles:
                    try:
                        await member.add_roles(role, reason=f"Auto role given for joining before {end_date}")
                        members_added += 1
                    except discord.Forbidden:
                        failed_members += 1
                else:
                    members_skipped += 1

            # Small delay to prevent rate limiting
            if members_added % 10 == 0:
                await asyncio.sleep(0.5)

        embed = discord.Embed(
            title="✅ Auto Role (End Date) Complete",
            color=discord.Color.green()
        )
        embed.add_field(name="📅 Cutoff Date", value=f"Joined before {end.strftime('%d/%m/%Y')}", inline=False)
        embed.add_field(name="🎯 Role", value=role.mention, inline=True)
        embed.add_field(name="✅ Members Added", value=str(members_added), inline=True)
        embed.add_field(name="⏭️ Already Had Role", value=str(members_skipped), inline=True)
        embed.add_field(name="❌ Failed (Missing Perms)", value=str(failed_members), inline=True)

        await ctx.send(embed=embed)

    @commands.command(name="autogiverolemembs")
    @commands.has_permissions(administrator=True)
    async def auto_give_role_members(self, ctx, role: discord.Role, amount: int):
        """
        [Admin] Gives a role to the FIRST X members who joined the server.
        Usage: !autogiverolemembs @Role 500
        """
        if amount <= 0:
            return await ctx.send("❌ Amount must be greater than 0.")

        await ctx.send(f"⏳ Finding the first **{amount}** members to join and giving them {role.mention}...")

        # Get all members sorted by join date (oldest first)
        sorted_members = sorted(ctx.guild.members, key=lambda m: m.joined_at)

        members_added = 0
        members_skipped = 0
        failed_members = 0

        # Only process up to the requested amount
        for member in sorted_members[:amount]:
            if member.bot:
                continue
            
            if role not in member.roles:
                try:
                    await member.add_roles(role, reason=f"Auto role given to first {amount} members")
                    members_added += 1
                except discord.Forbidden:
                    failed_members += 1
            else:
                members_skipped += 1

            # Small delay to prevent rate limiting
            if members_added % 10 == 0:
                await asyncio.sleep(0.5)

        embed = discord.Embed(
            title="✅ Auto Role (First Members) Complete",
            color=discord.Color.green()
        )
        embed.add_field(name="👥 Target Members", value=f"First {amount} to join", inline=False)
        embed.add_field(name="🎯 Role", value=role.mention, inline=True)
        embed.add_field(name="✅ Members Added", value=str(members_added), inline=True)
        embed.add_field(name="⏭️ Already Had Role", value=str(members_skipped), inline=True)
        embed.add_field(name="❌ Failed (Missing Perms)", value=str(failed_members), inline=True)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(GiveRole(bot))
