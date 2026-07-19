import discord
from discord.ext import commands
import json
import os
import asyncio

class LevelBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "level_roles.json"
        self.level_roles = self.load_data()
        
        # Define the level progression
        self.levels = [2, 5, 10, 20, 35, 50, 60, 70, 100]
        # Add 110 to 1000 in steps of 10
        self.levels.extend(range(110, 1001, 10))

    def load_data(self):
        """Load level role data from JSON file"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {}

    def save_data(self):
        """Save level role data to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.level_roles, f, indent=4)

    @commands.command(name="autosetuplevelroles")
    @commands.has_permissions(administrator=True)
    async def auto_setup_level_roles(self, ctx):
        """
        [Admin] Automatically creates level roles for all levels and assigns them to members.
        Usage: !autosetuplevelroles
        """
        guild = ctx.guild
        
        # Check if roles already exist and create missing ones
        created_roles = []
        existing_roles = []
        
        for level in self.levels:
            role_name = f"Level {level}"
            role = discord.utils.get(guild.roles, name=role_name)
            
            if not role:
                # Create the role
                try:
                    new_role = await guild.create_role(
                        name=role_name,
                        color=discord.Color.from_rgb(
                            min(255, level * 2), 
                            min(255, 255 - level), 
                            min(255, level * 3)
                        ),
                        reason="Auto-setup level roles"
                    )
                    created_roles.append(new_role.name)
                except discord.Forbidden:
                    return await ctx.send("❌ I don't have permission to create roles!")
            else:
                existing_roles.append(role.name)
        
        # Store role IDs in the database
        if str(guild.id) not in self.level_roles:
            self.level_roles[str(guild.id)] = {}
        
        for level in self.levels:
            role = discord.utils.get(guild.roles, name=f"Level {level}")
            if role:
                self.level_roles[str(guild.id)][str(level)] = role.id
        
        self.save_data()
        
        # Assign roles to existing members based on their level
        assigned_count = 0
        for member in guild.members:
            if member.bot:
                continue
            member_level = self.get_member_level(member)
            if member_level:
                role_id = self.level_roles[str(guild.id)].get(str(member_level))
                if role_id:
                    role = guild.get_role(role_id)
                    if role and role not in member.roles:
                        try:
                            await member.add_roles(role)
                            assigned_count += 1
                        except discord.Forbidden:
                            pass
        
        embed = discord.Embed(
            title="✅ Level Roles Setup Complete",
            color=discord.Color.green()
        )
        embed.add_field(name="Created Roles", value=str(len(created_roles)), inline=True)
        embed.add_field(name="Existing Roles", value=str(len(existing_roles)), inline=True)
        embed.add_field(name="Members Assigned", value=str(assigned_count), inline=True)
        
        if created_roles:
            embed.add_field(name="New Roles", value=", ".join(created_roles[:10]), inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="removealllevelroles")
    @commands.has_permissions(administrator=True)
    async def remove_all_level_roles(self, ctx):
        """
        [Admin] Deletes ALL level role objects from the server (including any that start with 'Level ').
        Usage: !removealllevelroles
        """
        guild = ctx.guild
        deleted_count = 0
        failed_count = 0
        deleted_roles = []

        # STEP 1: Find ALL roles that start with "Level " in the server
        level_roles = [role for role in guild.roles if role.name.startswith("Level ")]

        if not level_roles:
            return await ctx.send("❌ No roles starting with 'Level ' found in this server.")

        await ctx.send(f"🔍 Found **{len(level_roles)}** level roles. Deleting them now...")

        # STEP 2: Delete them all
        for role in level_roles:
            try:
                await role.delete(reason="Removed all level roles by admin request")
                deleted_count += 1
                deleted_roles.append(role.name)
            except discord.Forbidden:
                failed_count += 1
            except discord.HTTPException:
                failed_count += 1

        # STEP 3: Clear the roles from the database too
        if str(guild.id) in self.level_roles:
            del self.level_roles[str(guild.id)]
            self.save_data()

        embed = discord.Embed(
            title="🗑️ Level Roles Removed",
            color=discord.Color.red()
        )
        embed.add_field(name="✅ Successfully Deleted", value=str(deleted_count), inline=True)
        embed.add_field(name="❌ Failed to Delete", value=str(failed_count), inline=True)
        
        if deleted_roles:
            embed.add_field(name="Deleted Roles", value=", ".join(deleted_roles[:10]), inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="autodeletelevelroles")
    @commands.has_permissions(administrator=True)
    async def auto_delete_level_roles(self, ctx, target=None, *, user_id=None):
        """
        [Admin] Deletes level roles from users.
        Usage: !autodeletelevelroles [user|userid]
        Examples:
            !autodeletelevelroles user @User     - Removes ALL level roles from a specific user
            !autodeletelevelroles userid 123456789 - Removes ALL level roles by user ID
        """
        guild = ctx.guild
        
        if target is None:
            return await ctx.send("❌ Please specify: `user @User` or `userid 123456789`")
        
        target = target.lower()
        
        # Option 1: Remove all level roles from a specific user
        if target == "user":
            if not ctx.message.mentions:
                return await ctx.send("❌ Please mention a user: `!autodeletelevelroles user @User`")
            
            member = ctx.message.mentions[0]
            return await self.remove_user_level_roles(ctx, member)
        
        # Option 2: Remove all level roles from a user by ID
        elif target == "userid":
            if not user_id:
                return await ctx.send("❌ Please provide a user ID: `!autodeletelevelroles userid 123456789`")
            
            try:
                user_id = int(user_id)
                member = guild.get_member(user_id)
                if not member:
                    return await ctx.send("❌ User not found in this server.")
                return await self.remove_user_level_roles(ctx, member)
            except ValueError:
                return await ctx.send("❌ Invalid user ID. Please provide a valid numeric ID.")
        
        else:
            return await ctx.send("❌ Invalid option. Use: `user @User` or `userid 123456789`")

    async def remove_user_level_roles(self, ctx, member):
        """Helper function to remove all level roles from a user"""
        guild = ctx.guild
        
        # Look for roles starting with "Level " on the user
        level_roles_on_user = [role for role in member.roles if role.name.startswith("Level ")]
        
        if not level_roles_on_user:
            return await ctx.send(f"ℹ️ {member.mention} has no level roles to remove.")
        
        removed_count = 0
        for role in level_roles_on_user:
            try:
                await member.remove_roles(role, reason=f"Auto-delete level roles for user")
                removed_count += 1
            except discord.Forbidden:
                pass
        
        await ctx.send(f"✅ Removed {removed_count} level roles from {member.mention}.")

    @commands.command(name="addlevelrole")
    @commands.has_permissions(administrator=True)
    async def add_level_role(self, ctx, level: int, role: discord.Role):
        """
        [Admin] Manually adds a level role mapping.
        Usage: !addlevelrole 5 @Role
        """
        guild = ctx.guild
        
        if str(guild.id) not in self.level_roles:
            self.level_roles[str(guild.id)] = {}
        
        self.level_roles[str(guild.id)][str(level)] = role.id
        self.save_data()
        
        await ctx.send(f"✅ Added Level {level} -> {role.mention}")

    @commands.command(name="removelevelrole")
    @commands.has_permissions(administrator=True)
    async def remove_level_role(self, ctx, level: int):
        """
        [Admin] Removes a level role mapping.
        Usage: !removelevelrole 5
        """
        guild = ctx.guild
        
        if str(guild.id) not in self.level_roles:
            return await ctx.send("❌ No level roles configured for this server.")
        
        if str(level) in self.level_roles[str(guild.id)]:
            del self.level_roles[str(guild.id)][str(level)]
            self.save_data()
            await ctx.send(f"✅ Removed Level {level} mapping.")
        else:
            await ctx.send(f"❌ Level {level} is not configured.")

    @commands.command(name="listlevelroles")
    @commands.has_permissions(administrator=True)
    async def list_level_roles(self, ctx):
        """
        [Admin] Lists all configured level roles.
        Usage: !listlevelroles
        """
        guild = ctx.guild
        
        if str(guild.id) not in self.level_roles or not self.level_roles[str(guild.id)]:
            return await ctx.send("❌ No level roles configured for this server.")
        
        embed = discord.Embed(
            title="📋 Level Roles",
            color=discord.Color.blue()
        )
        
        for level, role_id in sorted(self.level_roles[str(guild.id)].items(), key=lambda x: int(x[0])):
            role = guild.get_role(role_id)
            if role:
                embed.add_field(
                    name=f"Level {level}",
                    value=role.mention,
                    inline=True
                )
        
        await ctx.send(embed=embed)

    def get_member_level(self, member):
        """
        Placeholder for your XP system.
        You need to implement this based on your actual leveling system.
        """
        # Example: Calculate level based on message count, XP, etc.
        # For now, this returns None
        return None

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Automatically assign level roles when a user levels up"""
        # You need to implement this with your XP system
        pass

async def setup(bot):
    await bot.add_cog(LevelBot(bot))
