import discord
from discord.ext import commands
import json
import os
import re

# ============================================
# DATABASE SETUP
# ============================================
DB_FILE = "ping_perms_data.json"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"allowed_targets": [], "blocked_targets": []}

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
    def is_target_blocked(self, target_id: int):
        """Check if a User or Role ID is blocked from being pinged."""
        return str(target_id) in self.data["blocked_targets"]

    def is_target_allowed(self, target_id: int):
        """Check if a User or Role ID is allowed to be pinged."""
        return str(target_id) in self.data["allowed_targets"]

    # ============================================
    # COMMAND: !pingallow @role @role OR @user @user
    # ============================================
    @commands.command(name="pingallow")
    @commands.has_permissions(administrator=True)
    async def pingallow(self, ctx, *targets: discord.Object):
        """[Admin] Allow specific roles/users to be pinged. Use: !pingallow @Role @User"""
        if not targets:
            return await ctx.send("❌ Please provide at least one user or role. Example: `!pingallow @SupportTeam @Mods`")

        added = []
        skipped = []

        for target in targets:
            target_id = str(target.id)
            
            if target_id in self.data["allowed_targets"]:
                skipped.append(f"`{target.id}` (Already allowed)")
            elif target_id in self.data["blocked_targets"]:
                # Remove from blocked if they are explicitly re-allowed
                self.data["blocked_targets"].remove(target_id)
                self.data["allowed_targets"].append(target_id)
                added.append(f"`{target.id}` (Moved from Blocked to Allowed)")
            else:
                self.data["allowed_targets"].append(target_id)
                added.append(f"`{target.id}`")

        save_data(self.data)

        msg = ""
        if added: msg += f"✅ Allowed Targets: {', '.join(added)}\n"
        if skipped: msg += f"⚠️ Skipped: {', '.join(skipped)}"
        
        if not msg: msg = "❌ Nothing was changed."
        await ctx.send(msg)

    # ============================================
    # COMMAND: !pingdisallow @role @role OR @user @user
    # ============================================
    @commands.command(name="pingdisallow")
    @commands.has_permissions(administrator=True)
    async def pingdisallow(self, ctx, *targets: discord.Object):
        """[Admin] Block specific roles/users from being pinged. Use: !pingdisallow @Role @User"""
        if not targets:
            return await ctx.send("❌ Please provide at least one user or role. Example: `!pingdisallow @Muted @User123`")

        added = []
        skipped = []

        for target in targets:
            target_id = str(target.id)
            
            if target_id in self.data["blocked_targets"]:
                skipped.append(f"`{target.id}` (Already blocked)")
            elif target_id in self.data["allowed_targets"]:
                # Remove from allowed if they are explicitly blocked
                self.data["allowed_targets"].remove(target_id)
                self.data["blocked_targets"].append(target_id)
                added.append(f"`{target.id}` (Moved from Allowed to Blocked)")
            else:
                self.data["blocked_targets"].append(target_id)
                added.append(f"`{target.id}`")

        save_data(self.data)

        msg = ""
        if added: msg += f"🚫 Blocked Targets: {', '.join(added)}\n"
        if skipped: msg += f"⚠️ Skipped: {', '.join(skipped)}"
        
        if not msg: msg = "❌ Nothing was changed."
        await ctx.send(msg)

    # ============================================
    # COMMAND: !pinglist
    # ============================================
    @commands.command(name="pinglist")
    @commands.has_permissions(administrator=True)
    async def pinglist(self, ctx):
        """[Admin] List all allowed and blocked ping targets."""
        embed = discord.Embed(title="📋 Ping Target Permission List", color=discord.Color.blue())

        allowed_text = ""
        for tid in self.data["allowed_targets"]:
            # Attempt to resolve to a mention
            member = ctx.guild.get_member(int(tid))
            role = ctx.guild.get_role(int(tid))
            if member: allowed_text += f"• {member.mention} (User)\n"
            elif role: allowed_text += f"• {role.mention} (Role)\n"
            else: allowed_text += f"• `{tid}` (Unknown)\n"
        if not allowed_text: allowed_text = "None"

        blocked_text = ""
        for tid in self.data["blocked_targets"]:
            member = ctx.guild.get_member(int(tid))
            role = ctx.guild.get_role(int(tid))
            if member: blocked_text += f"• {member.mention} (User)\n"
            elif role: blocked_text += f"• {role.mention} (Role)\n"
            else: blocked_text += f"• `{tid}` (Unknown)\n"
        if not blocked_text: blocked_text = "None"

        embed.add_field(name="✅ Allowed Targets", value=allowed_text, inline=False)
        embed.add_field(name="❌ Blocked Targets", value=blocked_text, inline=False)
        embed.set_footer(text="Blocked overrides Allowed.")

        await ctx.send(embed=embed)

    # ============================================
    # COMMAND: !pingclear
    # ============================================
    @commands.command(name="pingclear")
    @commands.has_permissions(administrator=True)
    async def pingclear(self, ctx):
        """[Admin] Clears all Ping Allow/Disallow target data."""
        self.data = {"allowed_targets": [], "blocked_targets": []}
        save_data(self.data)
        await ctx.send("✅ All ping target permission data has been cleared.")

    # ============================================
    # GLOBAL INTERCEPT: Intercept any !ping command
    # ============================================
    @commands.Cog.listener()
    async def on_command(self, ctx):
        # Only intercept commands starting with "ping"
        if ctx.command and ctx.command.name == "ping":
            
            # 1. Check if the command has arguments (the targets)
            if not ctx.message.mentions and not ctx.message.role_mentions:
                return # No one is being pinged, ignore.

            # 2. Check PINGED Users
            for user in ctx.message.mentions:
                if self.is_target_blocked(user.id):
                    await ctx.send(f"❌ You are not allowed to ping {user.mention}. They have been restricted from receiving pings.", delete_after=5)
                    raise commands.CommandError(f"Ping blocked: {user} is blocked from receiving pings.")
            
            # 3. Check PINGED Roles
            for role in ctx.message.role_mentions:
                if self.is_target_blocked(role.id):
                    await ctx.send(f"❌ You are not allowed to ping {role.mention}. This role has been restricted from receiving pings.", delete_after=5)
                    raise commands.CommandError(f"Ping blocked: {role} is blocked from receiving pings.")
 
