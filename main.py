import discord
from discord.ext import commands
import os
import asyncio
import json
import logging
import sys
import io
from dotenv import load_dotenv
from datetime import datetime, timezone

# ============================================
# FIX: Force UTF-8 for Windows Terminals
# ============================================
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0))
OWNER_IDS = [int(id.strip()) for id in os.getenv("OWNER_IDS", "").split(",") if id.strip()]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Global cooldown system
cooldowns = {}

# ============================================
# COMMANDS
# ============================================

@bot.command()
async def whoami(ctx):
    """Get your Discord user ID"""
    await ctx.send(f"Your User ID is: `{ctx.author.id}`")

@bot.command(name="sync")
@commands.is_owner()
async def sync_commands(ctx):
    """[Owner] Sync slash commands manually"""
    
    if not ctx.guild:
        await ctx.send("❌ This command must be used in a server!")
        return
    
    await ctx.send("🔄 Attempting to sync slash commands...")
    await ctx.send("⏳ This may take a moment...")
    
    try:
        if GUILD_ID:
            try:
                guild = discord.Object(id=GUILD_ID)
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
                await ctx.send(f"✅ Commands synced to guild: {GUILD_ID}")
                return
            except discord.Forbidden:
                await ctx.send("⚠️ Cannot sync to specific guild. Trying global sync...")
        
        try:
            await bot.tree.sync()
            await ctx.send("✅ Commands synced globally! (May take up to 1 hour to appear in Discord)")
        except discord.Forbidden:
            await ctx.send("❌ Bot doesn't have the required permissions!")
            await ctx.send("📌 Please re-invite the bot with the correct scopes:")
            await ctx.send(f"🔗 https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot+applications.commands")
            
    except Exception as e:
        await ctx.send(f"❌ Failed to sync commands: {e}")

@bot.command(name="syncglobal")
@commands.is_owner()
async def sync_global(ctx):
    """[Owner] Sync slash commands globally"""
    try:
        await bot.tree.sync()
        await ctx.send("✅ Commands synced globally! (May take up to 1 hour to appear)")
    except discord.Forbidden:
        await ctx.send("❌ Bot doesn't have the `applications.commands` scope!")
        await ctx.send(f"🔗 Re-invite: https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot+applications.commands")
    except Exception as e:
        await ctx.send(f"❌ Failed to sync commands: {e}")

@bot.command(name="botstatus")
@commands.is_owner()
async def bot_status(ctx):
    """[Owner] Check bot permissions and status"""
    
    embed = discord.Embed(
        title="🤖 Bot Status",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    
    # Basic info
    embed.add_field(
        name="📊 Server Info",
        value=f"Server: {ctx.guild.name}\nMembers: {ctx.guild.member_count}\nBot Name: {ctx.guild.me.display_name}",
        inline=False
    )
    
    # Check permissions
    perms = ctx.guild.me.guild_permissions
    
    perm_list = [
        ("Administrator", perms.administrator),
        ("Manage Channels", perms.manage_channels),
        ("Manage Roles", perms.manage_roles),
        ("Manage Messages", perms.manage_messages),
        ("Kick Members", perms.kick_members),
        ("Ban Members", perms.ban_members),
        ("Moderate Members", perms.moderate_members),
        ("Use Slash Commands", perms.use_application_commands),
        ("Manage Webhooks", perms.manage_webhooks),
        ("View Channel", perms.view_channel),
        ("Send Messages", perms.send_messages),
        ("Read Message History", perms.read_message_history),
    ]
    
    perm_text = "\n".join([f"{'✅' if p else '❌'} {name}" for name, p in perm_list])
    embed.add_field(name="🔑 Permissions", value=perm_text, inline=False)
    
    # Slash command status
    try:
        # Try to sync to check if we have permission
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            embed.add_field(name="🔄 Slash Commands", value="✅ Synced to guild", inline=False)
        else:
            await bot.tree.sync()
            embed.add_field(name="🔄 Slash Commands", value="✅ Synced globally", inline=False)
    except discord.Forbidden:
        embed.add_field(
            name="🔄 Slash Commands",
            value="❌ Missing `applications.commands` scope!\nRe-invite the bot with the correct scopes.",
            inline=False
        )
    except Exception as e:
        embed.add_field(name="🔄 Slash Commands", value=f"❌ {str(e)[:100]}", inline=False)
    
    # Invite link
    embed.add_field(
        name="🔗 Invite Link",
        value=f"[Click to re-invite with correct permissions](https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot+applications.commands)",
        inline=False
    )
    
    embed.set_footer(text=f"Bot ID: {bot.user.id}")
    
    await ctx.send(embed=embed)

@bot.command(name="load")
@commands.is_owner()
async def load_cog(ctx, cog: str):
    """[Owner] Load a cog"""
    try:
        await bot.load_extension(f"cogs.{cog}")
        await ctx.send(f"✅ Loaded cog: {cog}")
    except Exception as e:
        await ctx.send(f"❌ Failed to load cog: {e}")

@bot.command(name="unload")
@commands.is_owner()
async def unload_cog(ctx, cog: str):
    """[Owner] Unload a cog"""
    try:
        await bot.unload_extension(f"cogs.{cog}")
        await ctx.send(f"✅ Unloaded cog: {cog}")
    except Exception as e:
        await ctx.send(f"❌ Failed to unload cog: {e}")

@bot.command(name="reload")
@commands.is_owner()
async def reload_cog(ctx, cog: str):
    """[Owner] Reload a cog"""
    try:
        await bot.reload_extension(f"cogs.{cog}")
        await ctx.send(f"✅ Reloaded cog: {cog}")
    except Exception as e:
        await ctx.send(f"❌ Failed to reload cog: {e}")

@bot.command(name="listcogs")
@commands.is_owner()
async def list_cogs(ctx):
    """[Owner] List all loaded cogs"""
    loaded = list(bot.extensions.keys())
    if loaded:
        embed = discord.Embed(
            title="📦 Loaded Cogs",
            color=discord.Color.blue()
        )
        for cog in sorted(loaded):
            embed.add_field(name=cog, value="✅ Loaded", inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ No cogs loaded.")

# ============================================
# Load cogs
# ============================================
async def load_cogs():
    try:
        # Core cogs
        await bot.load_extension("cogs.admin_core")
        await bot.load_extension("cogs.moderation_elite")
        await bot.load_extension("cogs.utility_mega")
        
        # Fun & Games
        await bot.load_extension("cogs.game_engine")
        await bot.load_extension("cogs.fun_explosion")
        await bot.load_extension("cogs.social_interaction")
        
        # Economy & Leveling
        await bot.load_extension("cogs.economy_ultra")
        await bot.load_extension("cogs.levelbot")    # <--- YOUR NEW LEVELBOT
        
        # Media & Entertainment
        await bot.load_extension("cogs.music_ultimate")
        await bot.load_extension("cogs.anime_weeb")
        
        # --- SETTINGS BACKUP COG ---
        await bot.load_extension("cogs.settings")    # <--- BACKUP MANAGER
        
        # Features
        await bot.load_extension("cogs.giveaway_raffle")
        await bot.load_extension("cogs.voice_channel")
        await bot.load_extension("cogs.reaction_roles")
        await bot.load_extension("cogs.pingperm")
        await bot.load_extension("cogs.poll")
        await bot.load_extension("cogs.autorr")        # <--- YOUR AUTORR
        await bot.load_extension("cogs.giverole")      # <--- NEW GIVEROLE COG ADDED HERE
        await bot.load_extension("cogs.logging_audit")
        
        # Optional cogs (can be disabled if needed)
        try:
            await bot.load_extension("cogs.nsfw_optional")
        except Exception as e:
            logging.warning(f"⚠️ NSFW cog not loaded: {e}")
        
        try:
            await bot.load_extension("cogs.ai_integration")
        except Exception as e:
            logging.warning(f"⚠️ AI cog not loaded: {e}")
        
        # Ticket system
        await bot.load_extension("cogs.ticket")
        
        # Chat commands (deletemsg, sendmsgforuser)
        await bot.load_extension("cogs.chatcmds")
        
        # Welcome System
        await bot.load_extension("cogs.welcome")
        
        logging.info("✅ All cogs loaded successfully")
    except Exception as e:
        logging.error(f"❌ Failed to load cogs: {e}")
        raise e

# ============================================
# EVENT HANDLERS
# ============================================

@bot.event
async def on_ready():
    logging.info(f"✅ Logged in as {bot.user}")
    logging.info(f"📊 Serving {len(bot.guilds)} guilds")
    logging.info(f"👥 Watching {len(bot.users)} users")
    logging.info(f"👑 Owners: {OWNER_IDS}")
    
    # Set presence
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(bot.guilds)} servers | /help"
        )
    )
    
    # Sync slash commands - IMPROVED ERROR HANDLING
    try:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            try:
                # Check if we have permission to sync
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
                logging.info(f"✅ Commands synced to guild: {GUILD_ID}")
            except discord.Forbidden:
                logging.warning("⚠️ Cannot sync to specific guild (missing permissions). Syncing globally instead.")
                try:
                    await bot.tree.sync()
                    logging.info("✅ Commands synced globally")
                except discord.Forbidden:
                    logging.error("❌ Bot doesn't have applications.commands scope!")
                    logging.info(f"📌 Re-invite the bot with: https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot+applications.commands")
        else:
            try:
                await bot.tree.sync()
                logging.info("✅ Commands synced globally")
            except discord.Forbidden:
                logging.error("❌ Bot doesn't have applications.commands scope!")
                logging.info(f"📌 Re-invite the bot with: https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot+applications.commands")
                
    except discord.Forbidden as e:
        logging.error(f"❌ Failed to sync commands: {e}")
        logging.info(f"📌 Re-invite the bot with: https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot+applications.commands")
    except Exception as e:
        logging.error(f"❌ Failed to sync commands: {e}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ This command is on cooldown. Try again in {error.retry_after:.1f}s.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ I don't have permission to do that.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: `{error.param.name}`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument: {error}")
    elif isinstance(error, commands.CommandNotFound):
        # Silently ignore command not found errors (prevents spam)
        pass
    else:
        logging.error(f"❌ Command error: {error}")
        await ctx.send(f"❌ An error occurred: {str(error)[:100]}")

@bot.event
async def on_application_command_error(interaction, error):
    """Handle slash command errors"""
    if isinstance(error, discord.app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
    elif isinstance(error, discord.app_commands.errors.BotMissingPermissions):
        await interaction.response.send_message("❌ I don't have permission to do that.", ephemeral=True)
    elif isinstance(error, discord.app_commands.errors.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ This command is on cooldown. Try again in {error.retry_after:.1f}s.", ephemeral=True)
    elif isinstance(error, discord.app_commands.errors.MissingRequiredArgument):
        await interaction.response.send_message(f"❌ Missing required argument: `{error.param.name}`", ephemeral=True)
    else:
        logging.error(f"❌ Slash command error: {error}")
        try:
            await interaction.response.send_message(f"❌ An error occurred: {str(error)[:100]}", ephemeral=True)
        except:
            await interaction.followup.send(f"❌ An error occurred: {str(error)[:100]}", ephemeral=True)

# ============================================
# GLOBAL HELPERS
# ============================================

async def delete_message_after_delay(message, delay=5):
    """Delete a message after a delay"""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass

def is_owner(user_id):
    """Check if a user is an owner"""
    return user_id in OWNER_IDS

def is_admin_or_owner(member):
    """Check if a user is an admin or owner"""
    if is_owner(member.id):
        return True
    return member.guild_permissions.administrator

# ============================================
# ERROR HANDLING FOR COG LOADING
# ============================================

class MissingCogError(Exception):
    pass

def ensure_cog_exists(cog_name):
    """Check if a cog file exists"""
    cog_path = os.path.join("cogs", f"{cog_name}.py")
    if not os.path.exists(cog_path):
        raise MissingCogError(f"Cog file not found: {cog_path}")
    return True

# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    # Create cogs directory if it doesn't exist
    if not os.path.exists("cogs"):
        os.makedirs("cogs")
        logging.info("📁 Created cogs directory")
    
    # Create __init__.py in cogs if it doesn't exist
    init_path = os.path.join("cogs", "__init__.py")
    if not os.path.exists(init_path):
        with open(init_path, "w") as f:
            f.write("# This file makes the cogs folder a Python package\n")
        logging.info("📁 Created cogs/__init__.py")
    
    # Check if token exists
    if not BOT_TOKEN:
        logging.error("❌ DISCORD_TOKEN not found in .env file!")
        logging.error("📌 Please create a .env file with DISCORD_TOKEN=your_token_here")
        sys.exit(1)
    
    # Create welcome_data.json if it doesn't exist
    if not os.path.exists("welcome_data.json"):
        with open("welcome_data.json", "w") as f:
            json.dump({"settings": {}, "messages": {}}, f, indent=4)
        logging.info("📁 Created welcome_data.json")
    
    # Run the bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(load_cogs())
    except Exception as e:
        logging.error(f"❌ Failed to load cogs: {e}")
        sys.exit(1)
    
    try:
        bot.run(BOT_TOKEN)
    except discord.LoginFailure:
        logging.error("❌ Invalid bot token! Please check your .env file.")
    except discord.PrivilegedIntentsRequired:
        logging.error("❌ Privileged intents required! Enable them in the Discord Developer Portal.")
        logging.error("📌 Go to: https://discord.com/developers/applications/")
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}")
