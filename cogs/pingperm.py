import discord
from discord.ext import commands
import json
import os

# ============================================
# DATABASE SETUP
# ============================================
DB_FILE = "ping_perms_data.json"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"allowed": [], "blocked": []}

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ============================================
# PING PERMISSION COG
# ============================================
class PingPerm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()

    # ============================================
    # HELPER FUNCTIONS
    # ============================================
    def is_allowed(self, member: discord.Member):
        """Check if a user is allowed to ping."""
        # 1. Owners are always allowed
        if member.id in self.bot.owner_ids:
            return True
        
        # 2. Check if User ID is explicitly allowed
        if str(member.id) in self.data["allowed"]:
            return True
            
        # 3. Check if User has an Allowed Role
        for role in member.roles:
            if str(role.id) in self.data["allowed"]:
                return True
                
        return False

    def is_blocked(self, member: discord.Member):
        """Check if a user is explicitly blocked from pinging."""
        # 1. Check if User ID is blocked
        if str(member.id) in self.data["blocked"]:
            return True
            
        # 2. Check if User has a Blocked Role
        for role in member.roles:
            if str(role.id) in self.data["blocked"]:
                return True
                
        return False

    # ============================================
    # ADMIN COMMANDS
    # ============================================
    @commands.group(name="pingallow", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def pingallow(self, ctx):
        """[Admin] Manage who is allowed to ping."""
        await ctx.send("❌ Invalid usage. Use `!pingallow role @Role` or `!pingallow user <UserID>`")

    @pingallow.command(name="role")
    async def pingallow_role(self, ctx, role: discord.Role):
        """Allows an entire role to ping."""
        if str(role.id) in self.data["allowed"]:
            return await ctx.send(f"❌ {role.mention} is already allowed to ping.")
            
        self.data["allowed"].append(str(role.id))
        save_data(self.data)
        await ctx.send(f"✅ {role.mention} can now ping.")

    @pingallow.command(name="user")
    async def pingallow_user(self, ctx, user_id: int):
        """Allows a specific User ID to ping."""
        if str(user_id) in self.data["allowed"]:
            return await ctx.send(f"❌ `{user_id}` is already allowed to ping.")
            
        self.data["allowed"].append(str(user_id))
        save_data(self.data)
        await ctx.send(f"✅ User ID `{user_id}` can now ping.")

    # ============================================
    # DISALLOW COMMANDS
    # ============================================
    @commands.group(name="pingdisallow", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def pingdisallow(self, ctx):
        """[Admin] Manage who is NOT allowed to ping."""
        await ctx.send("❌ Invalid usage. Use `!pingdisallow role @Role` or `!pingdisallow user <UserID>`")

    @pingdisallow.command(name="role")
    async def pingdisallow_role(self, ctx, role: discord.Role):
        """Blocks an entire role from pinging (overrides pingallow)."""
        if str(role.id) in self.data["blocked"]:
            return await ctx.send(f"❌ {role.mention} is already blocked from pinging.")
            
        self.data["blocked"].append(str(role.id))
        save_data(self.data)
        await ctx.send(f"✅ {role.mention} is now blocked from pinging.")

    @pingdisallow.command(name="user")
    async def pingdisallow_user(self, ctx, user_id: int):
        """Blocks a specific User ID from pinging (overrides pingallow)."""
        if str(user_id) in self.data["blocked"]:
            return await ctx.send(f"❌ `{user_id}` is already blocked from pinging.")
            
        self.data["blocked"].append(str(user_id))
        save_data(self.data)
        await ctx.send(f"✅ User ID `{user_id}` is now blocked from pinging.")

    # ============================================
    # LIST COMMAND TO SEE CURRENT SETTINGS
    # ============================================
    @commands.command(name="pinglist")
    @commands.has_permissions(administrator=True)
    async def pinglist(self, ctx):
        """[Admin] List all allowed and blocked roles/users."""
        embed = discord.Embed(title="📋 Ping Permission List", color=discord.Color.blue())

        allowed_text = ""
        for item in self.data["allowed"]:
            # Try to find it as a role or user
            role = ctx.guild.get_role(int(item))
            if role:
                allowed_text += f"• {role.mention} (Role)\n"
            else:
                allowed_text += f"• `{item}` (User ID)\n"
                
        if not allowed_text: allowed_text = "None"

        blocked_text = ""
        for item in self.data["blocked"]:
            role = ctx.guild.get_role(int(item))
            if role:
                blocked_text += f"• {role.mention} (Role)\n"
            else:
                blocked_text += f"• `{item}` (User ID)\n"
                
        if not blocked_text: blocked_text = "None"

        embed.add_field(name="✅ Allowed to Ping", value=allowed_text, inline=False)
        embed.add_field(name="❌ Blocked from Pinging", value=blocked_text, inline=False)
        embed.set_footer(text="Blocked overrides Allowed.")

        await ctx.send(embed=embed)

    # ============================================
    # GLOBAL CHECK: Intercept any !ping command
    # ============================================
    @commands.Cog.listener()
    async def on_command(self, ctx):
        # Intercept ONLY commands that start with "ping"
        if ctx.command and ctx.command.name == "ping":
            
            # 1. Bot admins (Owners) bypass everything
            if ctx.author.id in self.bot.owner_ids:
                return

            # 2. Check Blocklist first (Blocked overrides allowed)
            if self.is_blocked(ctx.author):
                await ctx.send(f"❌ {ctx.author.mention}, you are banned from pinging anyone.", delete_after=5)
                raise commands.CommandError(f"{ctx.author} tried to ping but is blocked.")
            
            # 3. Check Allowlist
            if not self.is_allowed(ctx.author):
                await ctx.send(f"❌ {ctx.author.mention}, you do not have permission to ping. Please ask an admin for `pingallow`.", delete_after=5)
                raise commands.CommandError(f"{ctx.author} tried to ping but is not allowed.")
                
            # If we reach here, they are allowed!
            await ctx.send(f"✅ {ctx.author.mention}, you have permission to ping!", delete_after=3)

# ============================================
# SETUP FUNCTION
# ============================================
async def setup(bot):
    await bot.add_cog(PingPerm(bot))
