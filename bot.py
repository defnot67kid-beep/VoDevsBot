import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
import traceback

load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0))
OWNER_IDS = [int(id.strip()) for id in os.getenv("OWNER_IDS", "").split(",") if id.strip()]
DELETE_COOLDOWN = int(os.getenv("DELETE_COOLDOWN", 5))

if not BOT_TOKEN:
    raise ValueError("❌ DISCORD_TOKEN not found in .env file!")

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Store verification settings per guild
verification_settings = {}
welcome_settings = {}  # guild_id -> { channel_id, message, embed_color, auto_delete, mention_role }

# ============================================
# ROLE PERMISSIONS HELPER
# ============================================

def get_permissions_from_string(perm_string):
    """Convert a permission string like 'kick_members,ban_members' to discord.Permissions"""
    perm_map = {
        'administrator': 'administrator',
        'view_audit_log': 'view_audit_log',
        'view_guild_insights': 'view_guild_insights',
        'manage_guild': 'manage_guild',
        'manage_roles': 'manage_roles',
        'manage_channels': 'manage_channels',
        'manage_messages': 'manage_messages',
        'manage_nicknames': 'manage_nicknames',
        'manage_webhooks': 'manage_webhooks',
        'manage_emojis_and_stickers': 'manage_emojis_and_stickers',
        'manage_events': 'manage_events',
        'manage_threads': 'manage_threads',
        'create_instant_invite': 'create_instant_invite',
        'change_nickname': 'change_nickname',
        'kick_members': 'kick_members',
        'ban_members': 'ban_members',
        'timeout_members': 'moderate_members',
        'send_messages': 'send_messages',
        'send_messages_in_threads': 'send_messages_in_threads',
        'create_public_threads': 'create_public_threads',
        'create_private_threads': 'create_private_threads',
        'embed_links': 'embed_links',
        'attach_files': 'attach_files',
        'add_reactions': 'add_reactions',
        'use_external_emojis': 'use_external_emojis',
        'use_external_stickers': 'use_external_stickers',
        'mention_everyone': 'mention_everyone',
        'read_message_history': 'read_message_history',
        'send_tts_messages': 'send_tts_messages',
        'use_slash_commands': 'use_application_commands',
        'connect': 'connect',
        'speak': 'speak',
        'mute_members': 'mute_members',
        'deafen_members': 'deafen_members',
        'move_members': 'move_members',
        'priority_speaker': 'priority_speaker',
        'stream': 'stream',
        'request_to_speak': 'request_to_speak',
        'create_events': 'create_events',
        'manage_events': 'manage_events',
        'view_channel': 'view_channel',
        'read_messages': 'read_messages',
    }
    
    permissions = discord.Permissions()
    
    if not perm_string or perm_string.lower() == 'none':
        return permissions
    
    for perm in perm_string.split(','):
        perm = perm.strip().lower()
        if perm in perm_map:
            setattr(permissions, perm_map[perm], True)
        else:
            for key, value in perm_map.items():
                if perm in key or key in perm:
                    setattr(permissions, value, True)
                    break
    
    return permissions

def get_color_from_string(color_str):
    """Convert a color string to a discord.Color"""
    if not color_str or color_str.lower() == 'default':
        return discord.Color.default()
    
    if color_str.startswith('#'):
        try:
            hex_color = int(color_str.replace('#', ''), 16)
            return discord.Color(hex_color)
        except ValueError:
            pass
    
    color_map = {
        'red': discord.Color.red(),
        'green': discord.Color.green(),
        'blue': discord.Color.blue(),
        'yellow': discord.Color.yellow(),
        'orange': discord.Color.orange(),
        'purple': discord.Color.purple(),
        'pink': discord.Color.pink(),
        'magenta': discord.Color.magenta(),
        'gold': discord.Color.gold(),
        'teal': discord.Color.teal(),
        'dark_red': discord.Color.dark_red(),
        'dark_green': discord.Color.dark_green(),
        'dark_blue': discord.Color.dark_blue(),
        'dark_gold': discord.Color.dark_gold(),
        'dark_purple': discord.Color.dark_purple(),
        'dark_magenta': discord.Color.dark_magenta(),
        'dark_teal': discord.Color.dark_teal(),
        'blurple': discord.Color.blurple(),
        'fuchsia': discord.Color.fuchsia(),
        'greyple': discord.Color.greyple(),
    }
    
    if color_str.lower() in color_map:
        return color_map[color_str.lower()]
    
    try:
        return discord.Color(int(color_str))
    except ValueError:
        pass
    
    return discord.Color.default()

def find_role_by_name_or_mention(guild, role_input):
    """Find a role by name or mention"""
    if role_input.startswith('<@&') and role_input.endswith('>'):
        role_id = int(role_input.replace('<@&', '').replace('>', ''))
        return guild.get_role(role_id)
    
    for role in guild.roles:
        if role.name.lower() == role_input.lower():
            return role
    
    for role in guild.roles:
        if role_input.lower() in role.name.lower():
            return role
    
    return None

def find_channel_by_name_or_mention(guild, channel_input):
    """Find a channel by name or mention"""
    if channel_input.startswith('<#') and channel_input.endswith('>'):
        channel_id = int(channel_input.replace('<#', '').replace('>', ''))
        return guild.get_channel(channel_id)
    
    for channel in guild.channels:
        if channel.name.lower() == channel_input.lower():
            return channel
    
    for channel in guild.channels:
        if channel_input.lower() in channel.name.lower():
            return channel
    
    return None

def is_owner(user_id):
    """Check if a user is an owner"""
    return user_id in OWNER_IDS

def is_admin_or_owner(member):
    """Check if a user is an admin or owner"""
    if is_owner(member.id):
        return True
    return member.guild_permissions.administrator

async def delete_message_after_delay(message, delay=None):
    """Delete a message after a delay"""
    if delay is None:
        delay = DELETE_COOLDOWN
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass

def parse_roles_and_permissions(guild, roles_input):
    """Parse roles and their permissions from input string"""
    result = {}
    if not roles_input:
        return result
    
    for role_entry in roles_input.split(';'):
        if ':' not in role_entry:
            continue
        role_name, perms = role_entry.split(':', 1)
        role = find_role_by_name_or_mention(guild, role_name.strip())
        if role:
            perm_list = [p.strip() for p in perms.split(',')]
            result[role] = perm_list
    return result

def create_overwrites_from_parsed(guild, parsed_roles, default_perms=None):
    """Create overwrites from parsed roles"""
    overwrites = {}
    
    for role, perms in parsed_roles.items():
        perm_obj = discord.PermissionOverwrite()
        for perm in perms:
            perm = perm.lower().strip()
            if perm == 'view' or perm == 'view_channel':
                perm_obj.view_channel = True
            elif perm == 'send' or perm == 'send_messages':
                perm_obj.send_messages = True
            elif perm == 'read' or perm == 'read_messages':
                perm_obj.read_messages = True
            elif perm == 'read_history' or perm == 'read_message_history':
                perm_obj.read_message_history = True
            elif perm == 'embed' or perm == 'embed_links':
                perm_obj.embed_links = True
            elif perm == 'attach' or perm == 'attach_files':
                perm_obj.attach_files = True
            elif perm == 'react' or perm == 'add_reactions':
                perm_obj.add_reactions = True
            elif perm == 'connect':
                perm_obj.connect = True
            elif perm == 'speak':
                perm_obj.speak = True
            elif perm == 'stream':
                perm_obj.stream = True
            elif perm == 'priority' or perm == 'priority_speaker':
                perm_obj.priority_speaker = True
            elif perm == 'mute_members':
                perm_obj.mute_members = True
            elif perm == 'deafen_members':
                perm_obj.deafen_members = True
            elif perm == 'move_members':
                perm_obj.move_members = True
            elif perm == 'use_voice_activity':
                perm_obj.use_voice_activity = True
            elif perm == 'manage_messages':
                perm_obj.manage_messages = True
            elif perm == 'manage_threads':
                perm_obj.manage_threads = True
            elif perm == 'create_public_threads':
                perm_obj.create_public_threads = True
            elif perm == 'create_private_threads':
                perm_obj.create_private_threads = True
            elif perm == 'mention_everyone':
                perm_obj.mention_everyone = True
            elif perm == 'use_external_emojis':
                perm_obj.use_external_emojis = True
            elif perm == 'use_external_stickers':
                perm_obj.use_external_stickers = True
            elif perm == 'send_tts_messages':
                perm_obj.send_tts_messages = True
            elif perm == 'manage_webhooks':
                perm_obj.manage_webhooks = True
            elif perm == 'manage_channels':
                perm_obj.manage_channels = True
            elif perm == 'manage_roles':
                perm_obj.manage_roles = True
            elif perm.startswith('deny_'):
                deny_perm = perm.replace('deny_', '')
                if deny_perm == 'view' or deny_perm == 'view_channel':
                    perm_obj.view_channel = False
                elif deny_perm == 'send' or deny_perm == 'send_messages':
                    perm_obj.send_messages = False
                elif deny_perm == 'read' or deny_perm == 'read_messages':
                    perm_obj.read_messages = False
                elif deny_perm == 'connect':
                    perm_obj.connect = False
                elif deny_perm == 'speak':
                    perm_obj.speak = False
                elif deny_perm == 'embed' or deny_perm == 'embed_links':
                    perm_obj.embed_links = False
                elif deny_perm == 'attach' or deny_perm == 'attach_files':
                    perm_obj.attach_files = False
                elif deny_perm == 'react' or deny_perm == 'add_reactions':
                    perm_obj.add_reactions = False
                elif deny_perm == 'manage_messages':
                    perm_obj.manage_messages = False
        overwrites[role] = perm_obj
    
    return overwrites

# ============================================
# WELCOME SYSTEM
# ============================================

@bot.tree.command(
    name="setwelcomechannel",
    description="[Admin] Set an existing channel as the welcome channel"
)
@app_commands.describe(
    channel="The channel to use as the welcome channel",
    message="The welcome message (use {user} for mention, {name} for username, {server} for server name)",
    color="The color of the embed (hex or name)",
    auto_delete="Auto-delete welcome messages after X seconds (0 = never)",
    mention_role="Role to mention in welcome (name or mention)"
)
async def set_welcome_channel(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    message: str = None,
    color: str = "green",
    auto_delete: int = 0,
    mention_role: str = None
):
    """Set an existing channel as the welcome channel"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild_id = str(interaction.guild.id)
    
    if guild_id not in welcome_settings:
        welcome_settings[guild_id] = {}
    
    # Default welcome message
    if not message:
        message = "🎉 Welcome {user} to **{server}**! We're glad to have you here!"
    
    # Parse mention role
    role_mention = None
    if mention_role:
        role = find_role_by_name_or_mention(interaction.guild, mention_role)
        if role:
            role_mention = role.id
    
    welcome_settings[guild_id] = {
        "channel_id": str(channel.id),
        "message": message,
        "color": color,
        "auto_delete": auto_delete,
        "mention_role": role_mention
    }
    
    embed = discord.Embed(
        title="✅ Welcome Channel Set",
        description=f"Welcome channel set to {channel.mention}",
        color=get_color_from_string(color)
    )
    embed.add_field(name="Channel", value=channel.mention, inline=True)
    embed.add_field(name="Auto-Delete", value=f"{auto_delete}s" if auto_delete > 0 else "Never", inline=True)
    
    if role_mention:
        role = interaction.guild.get_role(role_mention)
        if role:
            embed.add_field(name="Mention Role", value=role.mention, inline=True)
    
    # Show preview
    preview = message.replace('{user}', '@User').replace('{name}', 'Username').replace('{server}', interaction.guild.name)
    embed.add_field(name="📋 Preview", value=preview[:1024], inline=False)
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    
    # Send a test message to the welcome channel
    try:
        test_embed = discord.Embed(
            title="📋 Welcome Channel Test",
            description="This is a test message. New members will see a welcome message here.",
            color=discord.Color.blue()
        )
        await channel.send(embed=test_embed, delete_after=10)
    except:
        pass
    
    log_msg = await interaction.channel.send(f"📋 Welcome channel set to {channel.mention} by {interaction.user.mention}")
    bot.loop.create_task(delete_message_after_delay(log_msg))

@bot.tree.command(
    name="welcomesetup",
    description="[Admin] Set up the welcome channel"
)
@app_commands.describe(
    channel="The channel to send welcome messages to",
    message="The welcome message (use {user} for mention, {name} for username, {server} for server name)",
    color="The color of the embed (hex or name)",
    auto_delete="Auto-delete welcome messages after X seconds (0 = never)",
    mention_role="Role to mention in welcome (name or mention)"
)
async def welcome_setup(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    message: str = None,
    color: str = "green",
    auto_delete: int = 0,
    mention_role: str = None
):
    """Set up the welcome channel"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild_id = str(interaction.guild.id)
    
    if guild_id not in welcome_settings:
        welcome_settings[guild_id] = {}
    
    # Default welcome message
    if not message:
        message = "🎉 Welcome {user} to **{server}**! We're glad to have you here!"
    
    # Parse mention role
    role_mention = None
    if mention_role:
        role = find_role_by_name_or_mention(interaction.guild, mention_role)
        if role:
            role_mention = role.id
    
    welcome_settings[guild_id] = {
        "channel_id": str(channel.id),
        "message": message,
        "color": color,
        "auto_delete": auto_delete,
        "mention_role": role_mention
    }
    
    embed = discord.Embed(
        title="✅ Welcome Channel Set Up",
        description=f"Welcome channel set to {channel.mention}",
        color=get_color_from_string(color)
    )
    embed.add_field(name="Channel", value=channel.mention, inline=True)
    embed.add_field(name="Auto-Delete", value=f"{auto_delete}s" if auto_delete > 0 else "Never", inline=True)
    
    if role_mention:
        role = interaction.guild.get_role(role_mention)
        if role:
            embed.add_field(name="Mention Role", value=role.mention, inline=True)
    
    embed.add_field(name="📋 Preview", value=message.replace('{user}', '@User').replace('{name}', 'Username').replace('{server}', interaction.guild.name), inline=False)
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    
    log_msg = await interaction.channel.send(f"📋 Welcome channel set to {channel.mention} by {interaction.user.mention}")
    bot.loop.create_task(delete_message_after_delay(log_msg))

@bot.tree.command(
    name="createwelcomechan",
    description="[Admin] Create a welcome channel with category"
)
@app_commands.describe(
    channel_name="The name of the welcome channel",
    category_name="The name of the category to put it in",
    message="The welcome message (use {user} for mention, {name} for username, {server} for server name)",
    color="The color of the embed (hex or name)",
    auto_delete="Auto-delete welcome messages after X seconds (0 = never)",
    mention_role="Role to mention in welcome (name or mention)",
    private="Make the channel private"
)
async def create_welcome_channel(
    interaction: discord.Interaction,
    channel_name: str = "welcome",
    category_name: str = "Welcome",
    message: str = None,
    color: str = "green",
    auto_delete: int = 0,
    mention_role: str = None,
    private: bool = False
):
    """Create a welcome channel with category"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    guild_id = str(guild.id)
    
    # Create or find category
    category = None
    for cat in guild.categories:
        if cat.name.lower() == category_name.lower():
            category = cat
            break
    
    if not category:
        try:
            category = await guild.create_category(
                name=category_name,
                reason=f"Created by {interaction.user} for welcome channel"
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to create category: {str(e)[:100]}", ephemeral=True)
            return
    
    # Create welcome channel
    try:
        # Set up overwrites
        overwrites = {}
        
        # If private, only allow certain roles
        if private:
            overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
            
            # Allow admins and the bot
            admin_role = None
            for role in guild.roles:
                if role.permissions.administrator:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            topic="Welcome new members!",
            overwrites=overwrites,
            reason=f"Created by {interaction.user} as welcome channel"
        )
        
        # Store welcome settings
        if guild_id not in welcome_settings:
            welcome_settings[guild_id] = {}
        
        # Default welcome message
        if not message:
            message = "🎉 Welcome {user} to **{server}**! We're glad to have you here!"
        
        # Parse mention role
        role_mention = None
        if mention_role:
            role = find_role_by_name_or_mention(guild, mention_role)
            if role:
                role_mention = role.id
        
        welcome_settings[guild_id] = {
            "channel_id": str(channel.id),
            "message": message,
            "color": color,
            "auto_delete": auto_delete,
            "mention_role": role_mention
        }
        
        embed = discord.Embed(
            title="✅ Welcome Channel Created",
            description=f"Created welcome channel: {channel.mention}",
            color=get_color_from_string(color)
        )
        embed.add_field(name="Category", value=category.mention, inline=True)
        embed.add_field(name="Auto-Delete", value=f"{auto_delete}s" if auto_delete > 0 else "Never", inline=True)
        embed.add_field(name="Private", value="✅ Yes" if private else "❌ No", inline=True)
        
        if role_mention:
            role = guild.get_role(role_mention)
            if role:
                embed.add_field(name="Mention Role", value=role.mention, inline=True)
        
        embed.add_field(name="📋 Preview", value=message.replace('{user}', '@User').replace('{name}', 'Username').replace('{server}', guild.name), inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Send a welcome test message
        test_embed = discord.Embed(
            title="🎉 Welcome Channel Created!",
            description=message.replace('{user}', interaction.user.mention).replace('{name}', interaction.user.display_name).replace('{server}', guild.name),
            color=get_color_from_string(color)
        )
        test_embed.set_footer(text="Welcome messages will appear here for new members")
        
        await channel.send(embed=test_embed)
        
        log_msg = await interaction.channel.send(f"📋 Welcome channel {channel.mention} created by {interaction.user.mention}")
        bot.loop.create_task(delete_message_after_delay(log_msg))
        
    except discord.Forbidden:
        await interaction.followup.send("❌ I don't have permission to create channels!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to create welcome channel: {str(e)[:100]}", ephemeral=True)

@bot.tree.command(
    name="welcomemessage",
    description="[Admin] Set the welcome message"
)
@app_commands.describe(
    message="The welcome message (use {user} for mention, {name} for username, {server} for server name)"
)
async def welcome_message(
    interaction: discord.Interaction,
    message: str
):
    """Set the welcome message"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild_id = str(interaction.guild.id)
    
    if guild_id not in welcome_settings:
        await interaction.followup.send("❌ Welcome channel not set up. Use `/setwelcomechannel`, `/welcomesetup` or `/createwelcomechan` first!", ephemeral=True)
        return
    
    welcome_settings[guild_id]["message"] = message
    
    embed = discord.Embed(
        title="✅ Welcome Message Updated",
        description="Welcome message has been updated!",
        color=discord.Color.green()
    )
    embed.add_field(name="📋 Preview", value=message.replace('{user}', '@User').replace('{name}', 'Username').replace('{server}', interaction.guild.name), inline=False)
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    
    log_msg = await interaction.channel.send(f"📋 Welcome message updated by {interaction.user.mention}")
    bot.loop.create_task(delete_message_after_delay(log_msg))

@bot.tree.command(
    name="welcomerole",
    description="[Admin] Set the role to mention in welcome"
)
@app_commands.describe(
    role="The role to mention (name or mention)"
)
async def welcome_role(
    interaction: discord.Interaction,
    role: str
):
    """Set the role to mention in welcome messages"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild_id = str(interaction.guild.id)
    
    if guild_id not in welcome_settings:
        await interaction.followup.send("❌ Welcome channel not set up. Use `/setwelcomechannel`, `/welcomesetup` or `/createwelcomechan` first!", ephemeral=True)
        return
    
    target_role = find_role_by_name_or_mention(interaction.guild, role)
    
    if not target_role:
        await interaction.followup.send(f"❌ Role **{role}** not found!", ephemeral=True)
        return
    
    welcome_settings[guild_id]["mention_role"] = target_role.id
    
    embed = discord.Embed(
        title="✅ Welcome Role Updated",
        description=f"Will mention {target_role.mention} in welcome messages",
        color=discord.Color.green()
    )
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    
    log_msg = await interaction.channel.send(f"📋 Welcome role set to {target_role.mention} by {interaction.user.mention}")
    bot.loop.create_task(delete_message_after_delay(log_msg))

@bot.tree.command(
    name="welcomecolor",
    description="[Admin] Set the welcome embed color"
)
@app_commands.describe(
    color="The color (hex like #FF0000 or name like red, green, etc.)"
)
async def welcome_color(
    interaction: discord.Interaction,
    color: str
):
    """Set the welcome embed color"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild_id = str(interaction.guild.id)
    
    if guild_id not in welcome_settings:
        await interaction.followup.send("❌ Welcome channel not set up. Use `/setwelcomechannel`, `/welcomesetup` or `/createwelcomechan` first!", ephemeral=True)
        return
    
    # Validate color
    try:
        color_obj = get_color_from_string(color)
        if color_obj == discord.Color.default() and color.lower() != 'default':
            # Try hex
            if color.startswith('#'):
                hex_color = int(color.replace('#', ''), 16)
                color_obj = discord.Color(hex_color)
            else:
                await interaction.followup.send(f"❌ Invalid color: **{color}**. Use hex like #FF0000 or color name like red.", ephemeral=True)
                return
    except:
        await interaction.followup.send(f"❌ Invalid color: **{color}**. Use hex like #FF0000 or color name like red.", ephemeral=True)
        return
    
    welcome_settings[guild_id]["color"] = color
    
    embed = discord.Embed(
        title="✅ Welcome Color Updated",
        description=f"Welcome embed color set to **{color}**",
        color=color_obj
    )
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    
    log_msg = await interaction.channel.send(f"📋 Welcome color set to **{color}** by {interaction.user.mention}")
    bot.loop.create_task(delete_message_after_delay(log_msg))

@bot.tree.command(
    name="welcomeauto",
    description="[Admin] Set auto-delete for welcome messages"
)
@app_commands.describe(
    seconds="Seconds before auto-deleting welcome messages (0 = never)"
)
async def welcome_auto(
    interaction: discord.Interaction,
    seconds: int
):
    """Set auto-delete for welcome messages"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild_id = str(interaction.guild.id)
    
    if guild_id not in welcome_settings:
        await interaction.followup.send("❌ Welcome channel not set up. Use `/setwelcomechannel`, `/welcomesetup` or `/createwelcomechan` first!", ephemeral=True)
        return
    
    welcome_settings[guild_id]["auto_delete"] = seconds
    
    embed = discord.Embed(
        title="✅ Welcome Auto-Delete Updated",
        description=f"Welcome messages will auto-delete after **{seconds}s**" if seconds > 0 else "Welcome messages will **never** auto-delete",
        color=discord.Color.green()
    )
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    
    log_msg = await interaction.channel.send(f"📋 Welcome auto-delete set to **{seconds}s** by {interaction.user.mention}")
    bot.loop.create_task(delete_message_after_delay(log_msg))

@bot.tree.command(
    name="welcomepreview",
    description="[Admin] Preview the welcome message"
)
async def welcome_preview(
    interaction: discord.Interaction
):
    """Preview the welcome message"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild_id = str(interaction.guild.id)
    
    if guild_id not in welcome_settings:
        await interaction.followup.send("❌ Welcome channel not set up. Use `/setwelcomechannel`, `/welcomesetup` or `/createwelcomechan` first!", ephemeral=True)
        return
    
    settings = welcome_settings[guild_id]
    message = settings.get("message", "🎉 Welcome {user} to **{server}**!")
    color = settings.get("color", "green")
    color_obj = get_color_from_string(color)
    
    embed = discord.Embed(
        title="📋 Welcome Message Preview",
        description=message.replace('{user}', interaction.user.mention).replace('{name}', interaction.user.display_name).replace('{server}', interaction.guild.name),
        color=color_obj
    )
    
    # Add mention role if set
    mention_role_id = settings.get("mention_role")
    if mention_role_id:
        role = interaction.guild.get_role(mention_role_id)
        if role:
            embed.add_field(name="Mention Role", value=role.mention, inline=False)
    
    embed.set_footer(text="This is a preview of what new members will see")
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(
    name="removewelcome",
    description="[Admin] Remove the welcome channel settings"
)
async def remove_welcome(
    interaction: discord.Interaction
):
    """Remove the welcome channel settings"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild_id = str(interaction.guild.id)
    
    if guild_id not in welcome_settings:
        await interaction.followup.send("❌ No welcome channel set up!", ephemeral=True)
        return
    
    del welcome_settings[guild_id]
    
    embed = discord.Embed(
        title="🗑️ Welcome Channel Removed",
        description="Welcome channel settings have been removed.",
        color=discord.Color.orange()
    )
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    
    log_msg = await interaction.channel.send(f"🗑️ Welcome channel settings removed by {interaction.user.mention}")
    bot.loop.create_task(delete_message_after_delay(log_msg))

# ============================================
# WELCOME EVENT HANDLER (WITH AVATAR, TEXT & AUTO UNVERIFIED ROLE)
# ============================================

@bot.event
async def on_member_join(member):
    """Send welcome message, and give the Unverified role automatically"""
    guild_id = str(member.guild.id)
    
    # =========================================================
    # 🟢 AUTOMATICALLY GIVE THE UNVERIFIED ROLE ON JOIN
    # =========================================================
    if guild_id in verification_settings:
        # Remove Verified role if they rejoined with it (Prevents bypass)
        verified_role_id = verification_settings[guild_id].get("verify_role_id")
        if verified_role_id:
            verified_role = member.guild.get_role(int(verified_role_id))
            if verified_role and verified_role in member.roles:
                try:
                    await member.remove_roles(verified_role, reason="Rejoining resets verification")
                except:
                    pass  # Bot lacks hierarchy permissions

        # Add Unverified role
        unverified_role_id = verification_settings[guild_id].get("unverified_role_id")
        if unverified_role_id:
            unverified_role = member.guild.get_role(int(unverified_role_id))
            if unverified_role:
                # Only add if they don't already have it
                if unverified_role not in member.roles:
                    try:
                        await member.add_roles(unverified_role, reason="Auto-assigned Unverified role upon join")
                    except:
                        pass  # Bot doesn't have perms to add
    
    # =========================================================
    # 🖼️ SEND THE WELCOME MESSAGE
    # =========================================================
    if guild_id not in welcome_settings:
        return
    
    settings = welcome_settings[guild_id]
    channel_id = settings.get("channel_id")
    
    if not channel_id:
        return
    
    channel = member.guild.get_channel(int(channel_id))
    if not channel:
        return
    
    # Get settings
    message_template = settings.get("message", "🎉 Welcome {user} to **{server}**!")
    color = settings.get("color", "green")
    auto_delete = settings.get("auto_delete", 0)
    mention_role_id = settings.get("mention_role")
    
    # Replace placeholders
    welcome_message = message_template.replace('{user}', member.mention).replace('{name}', member.display_name).replace('{server}', member.guild.name)
    
    # Load your banner image
    file = discord.File("welcome_banner.png", filename="banner.png")
    
    # Create the embed
    embed = discord.Embed(
        color=get_color_from_string(color)
    )
    
    # Put the welcome text right above the image
    embed.description = f"✨ **{welcome_message}**"
    
    # Set the big image banner
    embed.set_image(url="attachment://banner.png")
    
    # PUT THE USER'S AVATAR IN THE TOP RIGHT CORNER
    embed.set_thumbnail(url=member.display_avatar.url)
    
    # SECRET @everyone PING (Hidden in a field)
    mention_content = None
    if mention_role_id:
        role = member.guild.get_role(mention_role_id)
        if role:
            embed.add_field(name="📌", value=f"{role.mention}", inline=False)
    
    try:
        # Send the message with the file and embed
        welcome_msg = await channel.send(
            content=None,
            file=file, 
            embed=embed
        )
        
        if auto_delete > 0:
            bot.loop.create_task(delete_message_after_delay(welcome_msg, auto_delete))
            
    except Exception as e:
        print(f"❌ Error sending welcome message: {e}")

# ============================================
# VERIFICATION BUTTON AND SYSTEM
# ============================================

class VerifyButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="✅ Verify Me",
            custom_id="verify_button",
            emoji="✅"
        )
    
    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        guild_id = str(guild.id)
        
        if guild_id not in verification_settings:
            await interaction.response.send_message(
                "❌ Verification is not set up in this server. Please contact an admin.",
                ephemeral=True
            )
            return
        
        verify_role_id = verification_settings[guild_id].get("verify_role_id")
        if verify_role_id:
            role = guild.get_role(int(verify_role_id))
            if role and role in interaction.user.roles:
                await interaction.response.send_message(
                    "✅ You are already verified!",
                    ephemeral=True
                )
                return
        
        success = await give_verified_role(interaction.user, guild)
        
        if success:
            embed = discord.Embed(
                title="✅ Verification Successful!",
                description=f"You have been verified in **{guild.name}**!",
                color=discord.Color.green()
            )
            embed.add_field(
                name="🎉 Welcome",
                value="You now have access to all verified channels!",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            channel = guild.get_channel(int(verification_settings[guild_id].get("channel_id", 0)))
            if channel:
                log_message = await channel.send(
                    f"✅ {interaction.user.mention} has been verified!"
                )
                bot.loop.create_task(delete_message_after_delay(log_message))
        else:
            await interaction.response.send_message(
                "❌ Failed to verify. Please contact an admin.",
                ephemeral=True
            )

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VerifyButton())

# ============================================
# VERIFICATION SYSTEM COMMANDS
# ============================================

@bot.tree.command(
    name="setupverifychan",
    description="[Admin] Set up the verification channel"
)
@app_commands.describe(
    channel="The channel to use for verification"
)
async def setup_verify_channel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    """Set up the verification channel"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild_id = str(interaction.guild.id)
    
    if guild_id not in verification_settings:
        verification_settings[guild_id] = {}
    
    verification_settings[guild_id]["channel_id"] = str(channel.id)
    
    embed = discord.Embed(
        title="✅ Verification Channel Set",
        description=f"Verification channel set to {channel.mention}",
        color=discord.Color.green()
    )
    embed.add_field(name="Channel", value=channel.mention, inline=True)
    embed.add_field(name="Channel ID", value=f"`{channel.id}`", inline=True)
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(
    name="verifymt",
    description="[Admin] Set the verification method"
)
@app_commands.describe(
    method="The verification method to use"
)
@app_commands.choices(method=[
    app_commands.Choice(name="Button - Click a button to verify", value="button"),
    app_commands.Choice(name="Emoji - React with ✅ to verify", value="emoji"),
])
async def verify_method(
    interaction: discord.Interaction,
    method: app_commands.Choice[str]
):
    """Set the verification method"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild_id = str(interaction.guild.id)
    
    if guild_id not in verification_settings:
        verification_settings[guild_id] = {}
    
    verification_settings[guild_id]["method"] = method.value
    
    embed = discord.Embed(
        title="✅ Verification Method Set",
        description=f"Verification method set to: **{method.name}**",
        color=discord.Color.green()
    )
    
    channel_id = verification_settings[guild_id].get("channel_id")
    if channel_id:
        channel = interaction.guild.get_channel(int(channel_id))
        if channel:
            await send_verification_message(channel, method.value)
            embed.add_field(
                name="📨 Verification Message Sent",
                value=f"Sent verification message to {channel.mention}",
                inline=False
            )
    else:
        embed.add_field(
            name="⚠️ No Channel Set",
            value="Please use `/setupverifychan` first to set a verification channel.",
            inline=False
        )
    
    await interaction.followup.send(embed=embed, ephemeral=True)

async def send_verification_message(channel, method):
    """Send the verification message to the channel"""
    
    embed = discord.Embed(
        title="🔐 Verification Required",
        description="Please verify yourself to access the server!",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="How to Verify",
        value=f"**Click the button below to verify your account**",
        inline=False
    )
    embed.set_footer(text="Kholin Verification System")
    
    if method == "button":
        view = VerifyView()
        message = await channel.send(embed=embed, view=view)
        
        guild_id = str(channel.guild.id)
        if guild_id not in verification_settings:
            verification_settings[guild_id] = {}
        verification_settings[guild_id]["verify_message_id"] = str(message.id)
        verification_settings[guild_id]["verify_channel_id"] = str(channel.id)
        
    elif method == "emoji":
        message = await channel.send(embed=embed)
        await message.add_reaction("✅")
        
        guild_id = str(channel.guild.id)
        if guild_id not in verification_settings:
            verification_settings[guild_id] = {}
        verification_settings[guild_id]["verify_message_id"] = str(message.id)
        verification_settings[guild_id]["verify_channel_id"] = str(channel.id)

@bot.tree.command(
    name="createverifyrole",
    description="[Admin] Create the VERIFIED role (for verified members)"
)
@app_commands.describe(
    role_name="Name of the VERIFIED role (default: Verified)",
    color="Color of the role",
    allowed_channels="Channel mentions or names to allow (comma separated)",
    blocked_channels="Channel mentions or names to block (comma separated)"
)
async def create_verify_role(
    interaction: discord.Interaction,
    role_name: str = "Verified",
    color: str = "green",
    allowed_channels: str = None,
    blocked_channels: str = None
):
    """Create the VERIFIED role - ALWAYS creates a NEW role, never uses existing ones"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    guild_id = str(guild.id)
    
    role_color = get_color_from_string(color)
    role = await guild.create_role(
        name=role_name,
        color=role_color,
        mentionable=True,
        reason=f"Created by {interaction.user} as the VERIFIED role"
    )
    
    if guild_id not in verification_settings:
        verification_settings[guild_id] = {}
    verification_settings[guild_id]["verify_role_id"] = str(role.id)
    
    channels_modified = []
    
    allowed_list = []
    if allowed_channels:
        for ch in allowed_channels.split(','):
            ch = ch.strip()
            channel = find_channel_by_name_or_mention(guild, ch)
            if channel:
                allowed_list.append(channel)
    
    blocked_list = []
    if blocked_channels:
        for ch in blocked_channels.split(','):
            ch = ch.strip()
            channel = find_channel_by_name_or_mention(guild, ch)
            if channel:
                blocked_list.append(channel)
    
    for channel in allowed_list:
        try:
            await channel.set_permissions(
                role,
                view_channel=True,
                send_messages=True,
                read_messages=True,
                read_message_history=True,
                add_reactions=True,
                embed_links=True,
                attach_files=True
            )
            channels_modified.append(f"✅ {channel.mention} (allowed)")
        except Exception as e:
            channels_modified.append(f"❌ {channel.mention} (error: {e})")
    
    for channel in blocked_list:
        try:
            await channel.set_permissions(
                role,
                view_channel=False,
                send_messages=False,
                read_messages=False
            )
            channels_modified.append(f"🚫 {channel.mention} (blocked)")
        except Exception as e:
            channels_modified.append(f"❌ {channel.mention} (error: {e})")
    
    if not allowed_list and not blocked_list:
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                try:
                    await channel.set_permissions(
                        role,
                        view_channel=True,
                        send_messages=True,
                        read_messages=True
                    )
                except:
                    pass
        channels_modified.append("✅ All channels set to default (view and send)")
    
    verification_settings[guild_id]["allowed_channels"] = [str(c.id) for c in allowed_list]
    verification_settings[guild_id]["blocked_channels"] = [str(c.id) for c in blocked_list]
    
    embed = discord.Embed(
        title="✅ VERIFIED Role Created",
        description=f"**VERIFIED Role:** {role.mention}",
        color=role.color if role.color != discord.Color.default() else discord.Color.green()
    )
    embed.add_field(name="Role Name", value=role.name, inline=True)
    embed.add_field(name="Role ID", value=f"`{role.id}`", inline=True)
    embed.add_field(name="Role Type", value="✅ VERIFIED (given to verified members)", inline=True)
    embed.add_field(name="⚠️ Note", value="This is a NEW role, not an existing one!", inline=False)
    
    if channels_modified:
        embed.add_field(
            name="📋 Channel Permissions",
            value="\n".join(channels_modified[:10]) + (f"\n... and {len(channels_modified) - 10} more" if len(channels_modified) > 10 else ""),
            inline=False
        )
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    
    log_msg = await interaction.channel.send(f"✅ VERIFIED role **{role.name}** created by {interaction.user.mention}")
    bot.loop.create_task(delete_message_after_delay(log_msg))

@bot.tree.command(
    name="createdefaultunverifiedrole",
    description="[Admin] Create the UNVERIFIED role (for new members)"
)
@app_commands.describe(
    role_name="Name of the UNVERIFIED role (default: Unverified)",
    color="Color of the role"
)
async def create_unverified_role(
    interaction: discord.Interaction,
    role_name: str = "Unverified",
    color: str = "greyple"
):
    """Create the UNVERIFIED role - ALWAYS creates a NEW role, never uses existing ones"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    guild_id = str(guild.id)
    
    role_color = get_color_from_string(color)
    role = await guild.create_role(
        name=role_name,
        color=role_color,
        mentionable=False,
        reason=f"Created by {interaction.user} as the UNVERIFIED role"
    )
    
    if guild_id not in verification_settings:
        verification_settings[guild_id] = {}
    verification_settings[guild_id]["unverified_role_id"] = str(role.id)
    
    channels_modified = []
    
    for channel in guild.channels:
        if isinstance(channel, discord.TextChannel):
            try:
                await channel.set_permissions(
                    role,
                    view_channel=True,
                    send_messages=False,
                    read_messages=True,
                    read_message_history=True,
                    add_reactions=False,
                    embed_links=False,
                    attach_files=False,
                    create_public_threads=False,
                    create_private_threads=False
                )
                channels_modified.append(f"✅ {channel.mention}")
            except:
                pass
    
    embed = discord.Embed(
        title="✅ UNVERIFIED Role Created",
        description=f"**UNVERIFIED Role:** {role.mention}",
        color=role.color if role.color != discord.Color.default() else discord.Color.greyple()
    )
    embed.add_field(name="Role Name", value=role.name, inline=True)
    embed.add_field(name="Role ID", value=f"`{role.id}`", inline=True)
    embed.add_field(name="Role Type", value="🚫 UNVERIFIED (given to new members)", inline=True)
    embed.add_field(name="⚠️ Note", value="This is a NEW role, not an existing one!", inline=False)
    embed.add_field(
        name="📋 Permissions",
        value="Users with this role can view channels but CANNOT send messages",
        inline=False
    )
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    
    log_msg = await interaction.channel.send(f"✅ UNVERIFIED role **{role.name}** created by {interaction.user.mention}")
    bot.loop.create_task(delete_message_after_delay(log_msg))

# ============================================
# NEW COMMANDS: USE EXISTING VERIFY & UNVERIFY ROLES
# ============================================

@bot.tree.command(
    name="setverifyrole",
    description="[Admin] Set your EXISTING role as the Verified role (no new role created)"
)
@app_commands.describe(
    role="The existing verified role (name or mention)"
)
async def set_verify_role(
    interaction: discord.Interaction,
    role: str
):
    """Use an existing role as the VERIFIED role"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    guild_id = str(guild.id)
    
    target_role = find_role_by_name_or_mention(guild, role)
    
    if not target_role:
        await interaction.followup.send(f"❌ Role **{role}** not found!", ephemeral=True)
        return
    
    if guild_id not in verification_settings:
        verification_settings[guild_id] = {}
    
    verification_settings[guild_id]["verify_role_id"] = str(target_role.id)
    
    embed = discord.Embed(
        title="✅ Verified Role Set",
        description=f"Successfully set **{target_role.mention}** as the Verified role.",
        color=discord.Color.green()
    )
    embed.add_field(name="Role Name", value=target_role.name, inline=True)
    embed.add_field(name="Role ID", value=f"`{target_role.id}`", inline=True)
    embed.add_field(name="Type", value="Existing Role (Not Created by Bot)", inline=False)
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    
    log_msg = await interaction.channel.send(f"✅ Verified role set to **{target_role.name}** by {interaction.user.mention}")
    bot.loop.create_task(delete_message_after_delay(log_msg))

@bot.tree.command(
    name="setunverifiedrole",
    description="[Admin] Set your EXISTING role as the Unverified role (no new role created)"
)
@app_commands.describe(
    role="The existing unverified role (name or mention)"
)
async def set_unverified_role(
    interaction: discord.Interaction,
    role: str
):
    """Use an existing role as the UNVERIFIED role"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    guild_id = str(guild.id)
    
    target_role = find_role_by_name_or_mention(guild, role)
    
    if not target_role:
        await interaction.followup.send(f"❌ Role **{role}** not found!", ephemeral=True)
        return
    
    if guild_id not in verification_settings:
        verification_settings[guild_id] = {}
    
    verification_settings[guild_id]["unverified_role_id"] = str(target_role.id)
    
    embed = discord.Embed(
        title="✅ Unverified Role Set",
        description=f"Successfully set **{target_role.mention}** as the Unverified role.",
        color=discord.Color.greyple()
    )
    embed.add_field(name="Role Name", value=target_role.name, inline=True)
    embed.add_field(name="Role ID", value=f"`{target_role.id}`", inline=True)
    embed.add_field(name="Type", value="Existing Role (Not Created by Bot)", inline=False)
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    
    log_msg = await interaction.channel.send(f"✅ Unverified role set to **{target_role.name}** by {interaction.user.mention}")
    bot.loop.create_task(delete_message_after_delay(log_msg))

@bot.tree.command(
    name="clearallverifythings",
    description="[Owner] Clear ALL verification settings, roles, and messages"
)
async def clear_all_verify_things(
    interaction: discord.Interaction
):
    """Clear all verification settings, delete roles, and remove messages"""
    
    if not is_owner(interaction.user.id):
        await interaction.response.send_message(
            "❌ This command can only be used by the bot owner!",
            ephemeral=True
        )
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    guild_id = str(guild.id)
    
    if guild_id not in verification_settings:
        await interaction.followup.send(
            "❌ No verification settings found in this server.",
            ephemeral=True
        )
        return
    
    settings = verification_settings[guild_id]
    deleted_roles = []
    deleted_messages = []
    errors = []
    
    verify_role_id = settings.get("verify_role_id")
    if verify_role_id:
        role = guild.get_role(int(verify_role_id))
        if role:
            try:
                await role.delete(reason="Clearing all verification things")
                deleted_roles.append(f"✅ VERIFIED role: {role.name}")
            except Exception as e:
                errors.append(f"❌ Failed to delete VERIFIED role: {e}")
    
    unverified_role_id = settings.get("unverified_role_id")
    if unverified_role_id:
        role = guild.get_role(int(unverified_role_id))
        if role:
            try:
                await role.delete(reason="Clearing all verification things")
                deleted_roles.append(f"✅ UNVERIFIED role: {role.name}")
            except Exception as e:
                errors.append(f"❌ Failed to delete UNVERIFIED role: {e}")
    
    verify_message_id = settings.get("verify_message_id")
    verify_channel_id = settings.get("verify_channel_id")
    if verify_message_id and verify_channel_id:
        channel = guild.get_channel(int(verify_channel_id))
        if channel:
            try:
                message = await channel.fetch_message(int(verify_message_id))
                await message.delete()
                deleted_messages.append(f"✅ Verification message in {channel.mention}")
            except discord.NotFound:
                deleted_messages.append(f"⚠️ Verification message not found (already deleted)")
            except Exception as e:
                errors.append(f"❌ Failed to delete verification message: {e}")
    
    del verification_settings[guild_id]
    
    embed = discord.Embed(
        title="🗑️ All Verification Things Cleared",
        description="Successfully cleared all verification settings from this server!",
        color=discord.Color.red()
    )
    
    if deleted_roles:
        embed.add_field(
            name="📋 Deleted Roles",
            value="\n".join(deleted_roles),
            inline=False
        )
    
    if deleted_messages:
        embed.add_field(
            name="📋 Deleted Messages",
            value="\n".join(deleted_messages),
            inline=False
        )
    
    if errors:
        embed.add_field(
            name="⚠️ Errors",
            value="\n".join(errors),
            inline=False
        )
    
    embed.set_footer(text=f"Cleared by {interaction.user}")
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    
    channel_id = settings.get("channel_id")
    if channel_id:
        channel = guild.get_channel(int(channel_id))
        if channel:
            log_msg = await channel.send(
                f"🗑️ All verification settings have been cleared by {interaction.user.mention}!"
            )
            bot.loop.create_task(delete_message_after_delay(log_msg))

async def give_verified_role(member, guild):
    """Give the VERIFIED role to a member and remove UNVERIFIED role"""
    guild_id = str(guild.id)
    
    if guild_id not in verification_settings:
        return False
    
    verify_role_id = verification_settings[guild_id].get("verify_role_id")
    if not verify_role_id:
        return False
    
    verify_role = guild.get_role(int(verify_role_id))
    if not verify_role:
        return False
    
    unverified_role_id = verification_settings[guild_id].get("unverified_role_id")
    if unverified_role_id:
        unverified_role = guild.get_role(int(unverified_role_id))
        if unverified_role and unverified_role in member.roles:
            await member.remove_roles(unverified_role)
    
    await member.add_roles(verify_role)
    return True

# ============================================
# ROLE MANAGEMENT COMMANDS
# ============================================

@bot.tree.command(
    name="createrole",
    description="[Admin] Create a role with specified permissions"
)
@app_commands.describe(
    name="The name of the role",
    color="The color (hex like #FF0000 or name like red, blue, green, etc.)",
    permissions="Comma-separated permissions (e.g., kick_members,ban_members)",
    mentionable="Whether the role is mentionable",
    hoist="Whether the role is displayed separately"
)
async def create_role(
    interaction: discord.Interaction,
    name: str,
    color: str = "Default",
    permissions: str = "None",
    mentionable: bool = False,
    hoist: bool = False
):
    """Create a role with custom permissions"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
        
        role_color = get_color_from_string(color)
        perm_object = get_permissions_from_string(permissions)
        
        role = await interaction.guild.create_role(
            name=name,
            color=role_color,
            permissions=perm_object,
            mentionable=mentionable,
            hoist=hoist,
            reason=f"Created by {interaction.user}"
        )
        
        embed = discord.Embed(
            title="✅ Role Created Successfully!",
            description=f"Created role **{role.name}**",
            color=role_color if role_color != discord.Color.default() else discord.Color.blue()
        )
        embed.add_field(name="🎨 Color", value=f"`{str(role_color)}`" if role_color != discord.Color.default() else "Default", inline=True)
        
        if permissions and permissions.lower() != "none":
            perm_list = []
            for perm, value in perm_object:
                if value:
                    perm_list.append(f"• {perm.replace('_', ' ').title()}")
            if perm_list:
                embed.add_field(
                    name="🔑 Permissions",
                    value="\n".join(perm_list[:10]) + (f"\n... and {len(perm_list) - 10} more" if len(perm_list) > 10 else ""),
                    inline=False
                )
            else:
                embed.add_field(name="🔑 Permissions", value="None", inline=False)
        else:
            embed.add_field(name="🔑 Permissions", value="None", inline=False)
        
        embed.add_field(name="📌 Mentionable", value="✅ Yes" if role.mentionable else "❌ No", inline=True)
        embed.add_field(name="📋 Hoisted", value="✅ Yes" if role.hoist else "❌ No", inline=True)
        embed.add_field(name="🆔 Role ID", value=f"`{role.id}`", inline=True)
        embed.set_footer(text=f"Created by {interaction.user}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        log_msg = await interaction.channel.send(f"🎉 New role created: **{role.mention}** by {interaction.user.mention}")
        bot.loop.create_task(delete_message_after_delay(log_msg))
        
    except discord.Forbidden:
        await interaction.followup.send("❌ I don't have permission to create roles!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred: {str(e)[:100]}", ephemeral=True)

@bot.tree.command(
    name="addrole",
    description="[Admin] Add a role to a user"
)
@app_commands.describe(
    user="The user to add the role to",
    role="The role to add (name or mention)"
)
async def add_role(
    interaction: discord.Interaction,
    user: discord.Member,
    role: str
):
    """Add a role to a user"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
        
        target_role = None
        if role.startswith('<@&') and role.endswith('>'):
            role_id = int(role.replace('<@&', '').replace('>', ''))
            target_role = interaction.guild.get_role(role_id)
        else:
            for r in interaction.guild.roles:
                if r.name == role:
                    target_role = r
                    break
        
        if not target_role:
            embed = discord.Embed(
                title="❌ Role Not Found", 
                description=f"Could not find role: **{role}**\n\nTry using the exact role name or mention it like <@&role_id>",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        if target_role in user.roles:
            embed = discord.Embed(title="⚠️ Already Has Role", description=f"{user.mention} already has the role **{target_role.mention}**", color=discord.Color.orange())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        await user.add_roles(target_role, reason=f"Added by {interaction.user}")
        
        embed = discord.Embed(
            title="✅ Role Added",
            description=f"Added **{target_role.mention}** to {user.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="User", value=user.mention, inline=True)
        embed.add_field(name="Role", value=target_role.mention, inline=True)
        embed.add_field(name="Added By", value=interaction.user.mention, inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        log_msg = await interaction.channel.send(f"📌 {user.mention} was given the role **{target_role.mention}** by {interaction.user.mention}")
        bot.loop.create_task(delete_message_after_delay(log_msg))
        
    except discord.Forbidden:
        await interaction.followup.send("❌ I don't have permission to add roles!\n\nMake sure my role is higher than the role you're trying to add.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred: {str(e)[:100]}", ephemeral=True)

@bot.tree.command(
    name="removerole",
    description="[Admin] Remove a role from a user"
)
@app_commands.describe(
    user="The user to remove the role from",
    role="The role to remove (name or mention)"
)
async def remove_role(
    interaction: discord.Interaction,
    user: discord.Member,
    role: str
):
    """Remove a role from a user"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
        
        target_role = None
        if role.startswith('<@&') and role.endswith('>'):
            role_id = int(role.replace('<@&', '').replace('>', ''))
            target_role = interaction.guild.get_role(role_id)
        else:
            for r in interaction.guild.roles:
                if r.name == role:
                    target_role = r
                    break
        
        if not target_role:
            embed = discord.Embed(
                title="❌ Role Not Found", 
                description=f"Could not find role: **{role}**\n\nTry using the exact role name or mention it like <@&role_id>",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        if target_role not in user.roles:
            embed = discord.Embed(title="⚠️ Doesn't Have Role", description=f"{user.mention} does not have the role **{target_role.mention}**", color=discord.Color.orange())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        await user.remove_roles(target_role, reason=f"Removed by {interaction.user}")
        
        embed = discord.Embed(
            title="✅ Role Removed",
            description=f"Removed **{target_role.mention}** from {user.mention}",
            color=discord.Color.orange()
        )
        embed.add_field(name="User", value=user.mention, inline=True)
        embed.add_field(name="Role", value=target_role.mention, inline=True)
        embed.add_field(name="Removed By", value=interaction.user.mention, inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        log_msg = await interaction.channel.send(f"📌 {user.mention} had the role **{target_role.mention}** removed by {interaction.user.mention}")
        bot.loop.create_task(delete_message_after_delay(log_msg))
        
    except discord.Forbidden:
        await interaction.followup.send("❌ I don't have permission to remove roles!\n\nMake sure my role is higher than the role you're trying to remove.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred: {str(e)[:100]}", ephemeral=True)

@bot.tree.command(
    name="deleterole",
    description="[Admin] Delete a role"
)
@app_commands.describe(
    role="The role to delete (name or mention)"
)
async def delete_role(
    interaction: discord.Interaction,
    role: str
):
    """Delete a role - Owners can delete ANY role, Admins can delete non-protected roles"""
    
    if not is_admin_or_owner(interaction.user):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    
    target_role = None
    if role.startswith('<@&') and role.endswith('>'):
        role_id = int(role.replace('<@&', '').replace('>', ''))
        target_role = guild.get_role(role_id)
    else:
        for r in guild.roles:
            if r.name == role:
                target_role = r
                break
    
    if not target_role:
        embed = discord.Embed(
            title="❌ Role Not Found",
            description=f"Could not find role: **{role}**",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    
    is_owner_user = is_owner(interaction.user.id)
    guild_id = str(guild.id)
    
    if not is_owner_user:
        if guild_id in verification_settings:
            if verification_settings[guild_id].get("verify_role_id") == str(target_role.id):
                embed = discord.Embed(
                    title="⚠️ Protected Role",
                    description=f"**{target_role.name}** is the VERIFIED role and cannot be deleted by admins.\nOnly the bot owner can delete this role.",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            if verification_settings[guild_id].get("unverified_role_id") == str(target_role.id):
                embed = discord.Embed(
                    title="⚠️ Protected Role",
                    description=f"**{target_role.name}** is the UNVERIFIED role and cannot be deleted by admins.\nOnly the bot owner can delete this role.",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
    
    role_name = target_role.name
    role_members = len(target_role.members)
    
    embed = discord.Embed(
        title="⚠️ Confirm Role Deletion",
        description=f"Are you sure you want to delete **{target_role.mention}**?",
        color=discord.Color.orange()
    )
    embed.add_field(name="Role Name", value=target_role.name, inline=True)
    embed.add_field(name="Members with this role", value=str(role_members), inline=True)
    embed.add_field(name="Role ID", value=f"`{target_role.id}`", inline=True)
    embed.set_footer(text="Type 'yes' to confirm")
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    
    def check(msg):
        return msg.author.id == interaction.user.id and msg.content.lower() == "yes"
    
    try:
        reply = await bot.wait_for("message", timeout=30.0, check=check)
        
        await target_role.delete(reason=f"Deleted by {interaction.user}")
        
        embed = discord.Embed(
            title="✅ Role Deleted",
            description=f"Successfully deleted role: **{role_name}**",
            color=discord.Color.green()
        )
        embed.add_field(name="Members affected", value=str(role_members), inline=True)
        embed.set_footer(text=f"Deleted by {interaction.user}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        log_msg = await interaction.channel.send(f"🗑️ Role **{role_name}** was deleted by {interaction.user.mention}")
        bot.loop.create_task(delete_message_after_delay(log_msg))
        
    except asyncio.TimeoutError:
        await interaction.followup.send("⏰ Confirmation timed out. Role not deleted.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("❌ I don't have permission to delete this role!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to delete role: {e}", ephemeral=True)

# ============================================
# MEMBER LEAVE HANDLER (REMOVES THEIR REACTION)
# ============================================

@bot.event
async def on_member_remove(member):
    """When a user leaves, remove their reaction from the verification message"""
    guild_id = str(member.guild.id)
    
    if guild_id not in verification_settings:
        return
    
    settings = verification_settings.get(guild_id)
    if not settings:
        return
    
    # Only do this if the method is emoji
    if settings.get("method") != "emoji":
        return
    
    # Get the stored verification message ID and channel ID
    verify_message_id = settings.get("verify_message_id")
    verify_channel_id = settings.get("verify_channel_id")
    
    if not verify_message_id or not verify_channel_id:
        return
    
    # Get the channel
    channel = member.guild.get_channel(int(verify_channel_id))
    if not channel:
        return
    
    try:
        # Fetch the exact verification message
        message = await channel.fetch_message(int(verify_message_id))
        
        # Iterate through reactions to find the specific checkmark
        for reaction in message.reactions:
            if str(reaction.emoji) == "✅":
                # Use reaction.remove() instead of message.remove_reaction()
                # This works even if the user is no longer in the guild
                try:
                    await reaction.remove(member)
                    print(f"🗑️ Removed ✅ reaction from {member.name} upon leaving.")
                except discord.NotFound:
                    # The user didn't actually have that reaction
                    pass
                except discord.Forbidden:
                    print("❌ Missing Manage Messages or Manage Roles permission to remove reactions!")
                break
                
    except discord.NotFound:
        # Message was already deleted
        pass
    except discord.Forbidden:
        print("❌ Bot lacks permission to fetch the message. Needs 'View Channel' and 'Read Message History'.")
    except Exception as e:
        print(f"❌ Error removing leave reaction: {e}")

# ============================================
# EVENT HANDLERS
# ============================================

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')
    print(f'📊 Serving {len(bot.guilds)} guilds')
    print(f'👥 Watching {len(bot.users)} users')
    print(f'👑 Owners: {OWNER_IDS}')
    print(f'⏰ Delete Cooldown: {DELETE_COOLDOWN}s')
    
    bot.add_view(VerifyView())
    
    try:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            print(f"✅ Commands synced to guild: {GUILD_ID}")
        else:
            await bot.tree.sync()
            print("✅ Commands synced globally")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="/setwelcomechannel | /createwelcomechan"
        )
    )

@bot.event
async def on_raw_reaction_add(payload):
    """Handle emoji verification - PREVENTS STUCK EMOJIS"""
    if payload.user_id == bot.user.id:
        return
    
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    
    guild_id = str(guild.id)
    
    if guild_id not in verification_settings:
        return
    
    verify_message_id = verification_settings[guild_id].get("verify_message_id")
    if str(payload.message_id) != verify_message_id:
        return
    
    if verification_settings[guild_id].get("method") != "emoji":
        return
    
    if str(payload.emoji) != "✅":
        return
    
    # 🛑 FIX: Verify they are still actually a member of the server
    member = guild.get_member(payload.user_id)
    if not member:
        return  # User left the server, ignore the reaction
    
    verify_role_id = verification_settings[guild_id].get("verify_role_id")
    if verify_role_id:
        role = guild.get_role(int(verify_role_id))
        if role and role in member.roles:
            return
    
    success = await give_verified_role(member, guild)
    
    if success:
        try:
            await member.send(f"✅ You have been verified in **{guild.name}**!")
        except:
            pass
        
        channel = guild.get_channel(int(verification_settings[guild_id].get("channel_id", 0)))
        if channel:
            log_msg = await channel.send(f"✅ {member.mention} has been verified!")
            bot.loop.create_task(delete_message_after_delay(log_msg))

# ============================================
# RUN THE BOT
# ============================================

if __name__ == "__main__":
    try:
        bot.run(BOT_TOKEN)
    except discord.LoginFailure:
        print("❌ Invalid bot token! Please check your .env file.")
    except Exception as e:
        print(f"❌ An error occurred: {e}")