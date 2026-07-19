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
    return {"allowed_users": [], "allowed_roles": [], "blocked_users": [], "blocked_roles": []}

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
        # 1. Owners are always allowed
        if member.id in self.bot.owner_ids:
            return True
        
        # 2. Check if User ID is explicitly allowed
        if str(member.id) in self.data["allowed_users"]:
            return True
            
        # 3. Check if User has an Allowed Role
        for role in member.roles:
            if str(role.id) in self.data["allowed_roles"]:
                return True
                
        return False

    def is_blocked(self, member: discord.Member):
        # 1. Check if User ID is blocked
        if str(member.id) in self.data["blocked_users"]:
            return True
            
        # 2. Check if User has a Blocked Role
        for role in member.roles:
            if str(role.id) in self.data["blocked_roles"]:
                return True
                
        return False

    # ============================================
    # COMMAND: !pingallow @role @role OR @user @user
    # ============================================
    @commands.command(name="pingallow")
    @commands.has_permissions(administrator=True)
    async def pingallow(self, ctx, *targets: discord.Object):
        """[Admin] Allow users (or roles) to ping. Use: !pingallow @Role @User"""
        if not targets:
            return await ctx.send("❌ Please provide at least one user or role to allow. Example: `!pingallow @SupportTeam @Mods`")

        added_users = []
        added_roles = []
        skipped = []

        for target in targets:
            # 1. Check if it's a Role
            role = ctx.guild.get_role(target.id)
            if role:
                if str(role.id) in self.data["allowed_roles"]:
                    skipped.append(f"{role.mention} (Already allowed)")
                else:
                    self.data["allowed_roles"].append(str(role.id))
                    added_roles.append(role.mention)
                continue

            # 2. Check if it's a User (Try to fetch member)
            try:
                member = await ctx.guild.fetch_member(target.id)
                if member:
                    if str(member.id) in self.data["allowed_users"]:
                        skipped.append(f"{member.mention} (Already allowed)")
                    else:
                        self.data["allowed_users"].append(str(member.id))
                        added_users.append(member.mention)
                    continue
            except:
                pass

            # 3. If we get here, it's an unknown ID
            skipped.append(f"`{target.id}` (Not a valid Role or User in this server)")

        save_data(self.data)

        msg = ""
        if added_users: msg += f"✅ Allowed Users: {', '.join(added_users)}\n"
        if added_roles: msg += f"✅ Allowed Roles: {', '.join(added_roles)}\n"
        if skipped: msg += f"⚠️ Skipped: {', '.join(skipped)}"
        
        if not msg: msg = "❌ Nothing was changed."
        await ctx.send(msg)

    # ============================================
    # COMMAND: !pingdisallow @role @role OR @user @user
    # ============================================
    @commands.command(name="pingdisallow")
    @commands.has_permissions(administrator=True)
    async def pingdisallow(self, ctx, *targets: discord.Object):
        """[Admin] Block users (or roles) from pinging. Use: !pingdisallow @Role @User"""
        if not targets:
            return await ctx.send("❌ Please provide at least one user or role to block. Example: `!pingdisallow @Muted @PingBanned`")

        added_users = []
        added_roles = []
        skipped = []

        for target in targets:
            role = ctx.guild.get_role(target.id)
            if role:
                if str(role.id) in self.data["blocked_roles"]:
                    skipped.append(f"{role.mention} (Already blocked)")
                else:
                    self.data["blocked_roles"].append(str(role.id))
                    added_roles.append(role.mention)
                continue

            try:
                member = await ctx.guild.fetch_member(target.id)
                if member:
                    if str(member.id) in self.data["blocked_users"]:
                        skipped.append(f"{member.mention} (Already blocked)")
                    else:
                        self.data["blocked_users"].append(str(member.id))
                        added_users.append(member.mention)
                    continue
            except:
                pass

            skipped.append(f"`{target.id}` (Not a valid Role or User)")

        save_data(self.data)

        msg = ""
        if added_users: msg += f"🚫 Blocked Users: {', '.join(added_users)}\n"
        if added_roles: msg += f"🚫 Blocked Roles: {', '.join(added_roles)}\n"
        if skipped: msg += f"⚠️ Skipped: {', '.join(skipped)}"
        
        if not msg: msg = "❌ Nothing was changed."
        await ctx.send(msg)

    # ============================================
    # COMMAND: !pinglist
    # ============================================
    @commands.command(name="pinglist")
    @commands.has_permissions(administrator=True)
    async def pinglist(self, ctx):
        """[Admin] List all allowed and blocked roles/users."""
        embed = discord.Embed(title="📋 Ping Permission List", color=discord.Color.blue())

        allowed_text = ""
        for uid in self.data["allowed_users"]:
            member = ctx.guild.get_member(int(uid))
            allowed_text += f"• {member.mention if member else f'`{uid}`'}\n"
        for rid in self.data["allowed_roles"]:
            role = ctx.guild.get_role(int(rid))
            allowed_text += f"• {role.mention if role else f'`{rid}`'} (Role)\n"
        if not allowed_text: allowed_text = "None"

        blocked_text = ""
        for uid in self.data["blocked_users"]:
            member = ctx.guild.get_member(int(uid))
            blocked_text += f"• {member.mention if member else f'`{uid}`'}\n"
        for rid in self.data["blocked_roles"]:
            role = ctx.guild.get_role(int(rid))
            blocked_text += f"• {role.mention if role else f'`{rid}`'} (Role)\n"
        if not blocked_text: blocked_text = "None"

        embed.add_field(name="✅ Allowed to Ping", value=allowed_text, inline=False)
        embed.add_field(name="❌ Blocked from Pinging", value=blocked_text, inline=False)
        embed.set_footer(text="Blocked overrides Allowed.")

        await ctx.send(embed=embed)

    # ============================================
    # COMMAND: !pingclear
    # ============================================
    @commands.command(name="pingclear")
    @commands.has_permissions(administrator=True)
    async def pingclear(self, ctx):
        """[Admin] Clears all Ping Allow and Disallow permissions."""
        self.data = {"allowed_users": [], "allowed_roles": [], "blocked_users": [], "blocked_roles": []}
        save_data(self.data)
        await ctx.send("✅ All ping permission data has been cleared.")

    # ============================================
    # GLOBAL CHECK: Intercept any !ping command
    # ============================================
    @commands.Cog.listener()
    async def on_command(self, ctx):
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
                await ctx.send(f"❌ {ctx.author.mention}, you do not have permission to ping. Please ask an admin for `!pingallow`.", delete_after=5)
                raise commands.CommandError(f"{ctx.author} tried to ping but is not allowed.")
                
            # If we reach here, they are allowed!
            await ctx.send(f"✅ {ctx.author.mention}, you have permission to ping!", delete_after=3)

# ============================================
# SETUP FUNCTION
# ============================================
async def setup(bot):
    await bot.add_cog(PingPerm(bot))
