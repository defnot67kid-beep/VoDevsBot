import discord
from discord.ext import commands

class ReactionRoles(commands.Cog):
    """Reaction role system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.reaction_roles = {}  # message_id -> {emoji: role_id}

    @commands.command(name="rr-add")
    @commands.has_permissions(manage_roles=True)
    async def rr_add(self, ctx, message_id: int, emoji: str, role: discord.Role):
        """Add a reaction role to a message"""
        if message_id not in self.reaction_roles:
            self.reaction_roles[message_id] = {}
        
        self.reaction_roles[message_id][emoji] = role.id
        
        try:
            msg = await ctx.channel.fetch_message(message_id)
            await msg.add_reaction(emoji)
            await ctx.send(f"✅ Reaction role added: {emoji} → {role.mention}")
        except:
            await ctx.send("❌ Failed to find the message or add the reaction.")

    @commands.command(name="rr-remove")
    @commands.has_permissions(manage_roles=True)
    async def rr_remove(self, ctx, message_id: int, emoji: str):
        """Remove a reaction role"""
        if message_id in self.reaction_roles and emoji in self.reaction_roles[message_id]:
            del self.reaction_roles[message_id][emoji]
            await ctx.send(f"✅ Removed reaction role for {emoji}.")
        else:
            await ctx.send("❌ Reaction role not found.")

    @commands.command(name="rr-list")
    async def rr_list(self, ctx):
        """List all reaction roles in this server"""
        if not self.reaction_roles:
            await ctx.send("❌ No reaction roles set up.")
            return
        
        embed = discord.Embed(title="🎭 Reaction Roles", color=discord.Color.blue())
        for message_id, roles in self.reaction_roles.items():
            embed.add_field(name=f"Message {message_id}", value=str(roles), inline=False)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id in self.reaction_roles:
            guild = self.bot.get_guild(payload.guild_id)
            if guild:
                role_id = self.reaction_roles[payload.message_id].get(str(payload.emoji))
                if role_id:
                    role = guild.get_role(role_id)
                    if role:
                        member = guild.get_member(payload.user_id)
                        if member and role not in member.roles:
                            await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.message_id in self.reaction_roles:
            guild = self.bot.get_guild(payload.guild_id)
            if guild:
                role_id = self.reaction_roles[payload.message_id].get(str(payload.emoji))
                if role_id:
                    role = guild.get_role(role_id)
                    if role:
                        member = guild.get_member(payload.user_id)
                        if member and role in member.roles:
                            await member.remove_roles(role)

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))