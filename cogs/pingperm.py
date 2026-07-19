import discord
from discord.ext import commands
import json
import os

DB_FILE = "ping_perm_data.json"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"allow": [], "disallow": []} # Format: [{"source_id": "123", "target_id": "456", "is_role": False}]

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

class PingPerm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()

    # ==========================================
    # HELPERS
    # ==========================================
    def _get_ids(self, ctx, targets):
        """Converts a mix of mentions and IDs into a list of snowflakes"""
        ids = []
        for t in targets:
            # Check if it's a Role Mention
            if len(ctx.message.role_mentions) > 0:
                for r in ctx.message.role_mentions:
                    if t == r.mention or str(r.id) == t:
                        ids.append({"id": str(r.id), "is_role": True})
                        break
            # Check if it's a User Mention
            elif len(ctx.message.mentions) > 0:
                for u in ctx.message.mentions:
                    if t == u.mention or str(u.id) == t:
                        ids.append({"id": str(u.id), "is_role": False})
                        break
            # It's a raw ID
            else:
                try:
                    int(t)
                    ids.append({"id": t, "is_role": False}) # Assume user ID, admin must type correctly
                except ValueError:
                    pass # Invalid input
        return ids

    def _check_rule(self, source_id, target_id, is_role):
        """Checks the database for a rule"""
        for rule in self.data["disallow"]:
            if rule["source_id"] == source_id and rule["target_id"] == target_id and rule["is_role"] == is_role:
                return True
        return False

    # ==========================================
    # ADD RULES
    # ==========================================
    @commands.command(name="pingallow")
    @commands.has_permissions(administrator=True)
    async def ping_allow(self, ctx, source: str, target: str):
        """[Admin] Allows source to ping target. (Use mentions or IDs)"""
        
        # Parse source and target
        src = self._get_ids(ctx, [source])
        tgt = self._get_ids(ctx, [target])

        if not src or not tgt:
            return await ctx.send("❌ Invalid source or target. Please mention a role/user or provide a valid ID.")

        s = src[0]
        t = tgt[0]

        # Check if there is a disallow rule blocking this
        if self._check_rule(s["id"], t["id"], s["is_role"]):
            return await ctx.send(f"❌ There is already a DISALLOW rule blocking this interaction. Remove it with `!pingdisallow` first.")

        # Add rule
        self.data["allow"].append({
            "source_id": s["id"],
            "target_id": t["id"],
            "is_role": s["is_role"]
        })
        save_data(self.data)
        
        src_name = f"<@&{s['id']}>" if s["is_role"] else f"<@{s['id']}>"
        tgt_name = f"<@&{t['id']}>" if t["is_role"] else f"<@{t['id']}>"
        
        await ctx.send(f"✅ **Allow Rule Added:** `{src_name}` is now allowed to ping `{tgt_name}`.")

    @commands.command(name="pingdisallow")
    @commands.has_permissions(administrator=True)
    async def ping_disallow(self, ctx, source: str, target: str):
        """[Admin] Disallows source from pinging target. (Use mentions or IDs)"""
        
        src = self._get_ids(ctx, [source])
        tgt = self._get_ids(ctx, [target])

        if not src or not tgt:
            return await ctx.send("❌ Invalid source or target.")

        s = src[0]
        t = tgt[0]

        # Check if there is an allow rule trying to override this
        for rule in self.data["allow"]:
            if rule["source_id"] == s["id"] and rule["target_id"] == t["id"] and rule["is_role"] == s["is_role"]:
                self.data["allow"].remove(rule) # Remove conflicting allow rule
                break

        # Add disallow rule
        self.data["disallow"].append({
            "source_id": s["id"],
            "target_id": t["id"],
            "is_role": s["is_role"]
        })
        save_data(self.data)

        src_name = f"<@&{s['id']}>" if s["is_role"] else f"<@{s['id']}>"
        tgt_name = f"<@&{t['id']}>" if t["is_role"] else f"<@{t['id']}>"
        
        await ctx.send(f"✅ **Disallow Rule Added:** `{src_name}` is now **FORBIDDEN** from pinging `{tgt_name}`.")

    # ==========================================
    # REMOVE RULES
    # ==========================================
    @commands.command(name="pingremove")
    @commands.has_permissions(administrator=True)
    async def ping_remove(self, ctx, source: str, target: str):
        """[Admin] Removes any rule between source and target."""
        
        src = self._get_ids(ctx, [source])
        tgt = self._get_ids(ctx, [target])
        if not src or not tgt: return await ctx.send("❌ Invalid input.")

        s = src[0]; t = tgt[0]
        
        removed = False
        # Check Disallow
        for rule in self.data["disallow"]:
            if rule["source_id"] == s["id"] and rule["target_id"] == t["id"] and rule["is_role"] == s["is_role"]:
                self.data["disallow"].remove(rule)
                removed = True
                break
        # Check Allow
        for rule in self.data["allow"]:
            if rule["source_id"] == s["id"] and rule["target_id"] == t["id"] and rule["is_role"] == s["is_role"]:
                self.data["allow"].remove(rule)
                removed = True
                break
                
        if removed:
            save_data(self.data)
            await ctx.send(f"✅ Rule removed between source and target.")
        else:
            await ctx.send("❌ No rule found between those targets.")

    # ==========================================
    # LIST RULES
    # ==========================================
    @commands.command(name="pinglist")
    @commands.has_permissions(administrator=True)
    async def ping_list(self, ctx):
        """[Admin] Lists all current ping rules."""
        
        embed = discord.Embed(title="📋 Ping Permission Rules", color=discord.Color.blue())
        
        allow_list = []
        for rule in self.data["allow"]:
            name = f"<@&{rule['source_id']}>" if rule["is_role"] else f"<@{rule['source_id']}>"
            target = f"<@&{rule['target_id']}>" if rule["is_role"] else f"<@{rule['target_id']}>"
            allow_list.append(f"✅ {name} ➜ {target}")
            
        disallow_list = []
        for rule in self.data["disallow"]:
            name = f"<@&{rule['source_id']}>" if rule["is_role"] else f"<@{rule['source_id']}>"
            target = f"<@&{rule['target_id']}>" if rule["is_role"] else f"<@{rule['target_id']}>"
            disallow_list.append(f"🚫 {name} ➜ {target}")

        embed.add_field(name="Allowed (Whitelist)", value="\n".join(allow_list) if allow_list else "None", inline=False)
        embed.add_field(name="Disallowed (Blacklist)", value="\n".join(disallow_list) if disallow_list else "None", inline=False)
        
        await ctx.send(embed=embed)

    # ==========================================
    # EVENT: ON MESSAGE (Block the ping)
    # ==========================================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        if not message.guild: return
        if message.content == "": return

        # 1. Extract all pings from the message
        pings = []
        pings.extend([u.id for u in message.mentions])
        pings.extend([r.id for r in message.role_mentions])
        
        if not pings: return # No pings in message

        author_id = str(message.author.id)

        # 2. Check Disallow Rules first (Hard Block)
        for target_id in pings:
            target_id_str = str(target_id)

            # Check if Author is blocked from pinging this User ID
            for rule in self.data["disallow"]:
                # Rule matches author id, and target user id
                if rule["source_id"] == author_id and rule["target_id"] == target_id_str and rule["is_role"] == False:
                    await message.delete()
                    await message.channel.send(f"🚫 {message.author.mention}, you are **not allowed** to ping <@{target_id_str}>.", delete_after=5)
                    return
                
                # Rule matches author role, and target user id
                if rule["is_role"]:
                    role = message.guild.get_role(int(rule["source_id"]))
                    if role and role in message.author.roles:
                        if rule["target_id"] == target_id_str and rule["is_role"] == False:
                            await message.delete()
                            await message.channel.send(f"🚫 Your role {role.mention} is **not allowed** to ping <@{target_id_str}>.", delete_after=5)
                            return

            # Check if Author is blocked from pinging this Role ID
            for rule in self.data["disallow"]:
                # Rule matches author id, and target role id
                if rule["source_id"] == author_id and rule["target_id"] == target_id_str and rule["is_role"] == True:
                    await message.delete()
                    await message.channel.send(f"🚫 {message.author.mention}, you are **not allowed** to ping <@&{target_id_str}>.", delete_after=5)
                    return
                
                # Rule matches author role, and target role id
                if rule["is_role"]:
                    role = message.guild.get_role(int(rule["source_id"]))
                    if role and role in message.author.roles:
                        if rule["target_id"] == target_id_str and rule["is_role"] == True:
                            await message.delete()
                            await message.channel.send(f"🚫 Your role {role.mention} is **not allowed** to ping <@&{target_id_str}>.", delete_after=5)
                            return

        # 3. Check Allow Rules (Whitelist)
        # If an Allow rule exists, we let it through. If no allow rule exists, we let it through by default.
        for target_id in pings:
            target_id_str = str(target_id)
            
            # Check if an Allow rule specifically grants this interaction
            allowed = False
            for rule in self.data["allow"]:
                if rule["source_id"] == author_id and rule["target_id"] == target_id_str and rule["is_role"] == False:
                    allowed = True
                    break
                if rule["is_role"]:
                    role = message.guild.get_role(int(rule["source_id"]))
                    if role and role in message.author.roles:
                        if rule["target_id"] == target_id_str and rule["is_role"] == False:
                            allowed = True
                            break

            # If there is an ALLOW rule, we make sure they HAVE the role. If they don't, we delete it.
            if not allowed:
                # Check if a disallow rule was just checking our data
                is_blocked = False
                for disrule in self.data["disallow"]:
                    if disrule["source_id"] == author_id and disrule["target_id"] == target_id_str and disrule["is_role"] == False:
                        is_blocked = True
                        break
                
                # If there's an allow rule defined, and they aren't blocked, BUT they don't match the allow rule, we block them.
                # This makes sure whitelist rules aren't ignored.
                for rule in self.data["allow"]:
                    if rule["target_id"] == target_id_str:
                        if not (rule["source_id"] == author_id or (rule["is_role"] and message.guild.get_role(int(rule["source_id"])) in message.author.roles)):
                            if not is_blocked:
                                await message.delete()
                                await message.channel.send(f"🚫 You must have the appropriate role permissions to ping <@{target_id_str}>.", delete_after=5)
                                return
