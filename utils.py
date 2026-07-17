import discord
from discord.ext import commands
import asyncio
import time
import random
import logging
from typing import Optional, Union, List

# ============================================
# LOGGING SETUP
# ============================================

logger = logging.getLogger(__name__)

# ============================================
# EMBED HELPERS
# ============================================

def create_embed(
    title: str = None,
    description: str = None,
    color: discord.Color = discord.Color.blue(),
    author: discord.User = None,
    footer: str = None,
    thumbnail: str = None,
    image: str = None,
    fields: list = None
) -> discord.Embed:
    """Create a standardized embed with consistent formatting."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=discord.utils.utcnow()
    )
    
    if author:
        embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
    
    if footer:
        embed.set_footer(text=footer)
    elif author:
        embed.set_footer(text=f"Requested by {author.display_name}", icon_url=author.display_avatar.url)
    
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    
    if image:
        embed.set_image(url=image)
    
    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
    
    return embed

def error_embed(description: str, author: discord.User = None) -> discord.Embed:
    """Quick error embed."""
    return create_embed(
        title="❌ Error",
        description=description,
        color=discord.Color.red(),
        author=author
    )

def success_embed(description: str, author: discord.User = None) -> discord.Embed:
    """Quick success embed."""
    return create_embed(
        title="✅ Success",
        description=description,
        color=discord.Color.green(),
        author=author
    )

def warning_embed(description: str, author: discord.User = None) -> discord.Embed:
    """Quick warning embed."""
    return create_embed(
        title="⚠️ Warning",
        description=description,
        color=discord.Color.orange(),
        author=author
    )

# ============================================
# PERMISSION HELPERS
# ============================================

def is_admin_or_owner(member: discord.Member, owner_ids: list) -> bool:
    """Check if a user is a bot owner or has administrator permissions."""
    if member.id in owner_ids:
        return True
    return member.guild_permissions.administrator

def is_mod_or_owner(member: discord.Member, owner_ids: list) -> bool:
    """Check if a user is a bot owner, admin, or has moderation permissions."""
    if is_admin_or_owner(member, owner_ids):
        return True
    return member.guild_permissions.kick_members or member.guild_permissions.ban_members

def has_permissions(member: discord.Member, permissions: list) -> bool:
    """Check if a user has a list of specific permissions."""
    for perm in permissions:
        if not getattr(member.guild_permissions, perm, False):
            return False
    return True

# ============================================
# PAGINATION HELPERS
# ============================================

class PaginatorView(discord.ui.View):
    """Interactive paginator for long lists."""
    
    def __init__(self, pages: List[str], current_page: int = 0):
        super().__init__(timeout=60)
        self.pages = pages
        self.current_page = current_page
        self.total_pages = len(pages)
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        self.children[0].disabled = self.current_page == 0
        self.children[1].disabled = self.current_page == self.total_pages - 1
    
    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(content=self.pages[self.current_page], view=self)
    
    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(content=self.pages[self.current_page], view=self)
    
    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

async def paginate(
    ctx: commands.Context,
    items: List[str],
    title: str = "List",
    items_per_page: int = 10,
    color: discord.Color = discord.Color.blue()
):
    """Paginate a list of items into an interactive embed."""
    if not items:
        await ctx.send("❌ No items to display.")
        return
    
    pages = []
    for i in range(0, len(items), items_per_page):
        chunk = items[i:i + items_per_page]
        content = f"**{title}** (Page {i//items_per_page + 1}/{len(items)//items_per_page + 1})\n\n"
        content += "\n".join(chunk)
        pages.append(content)
    
    if len(pages) == 1:
        await ctx.send(pages[0])
    else:
        view = PaginatorView(pages)
        await ctx.send(pages[0], view=view)

# ============================================
# COOLDOWN HELPERS
# ============================================

class CooldownManager:
    """Advanced cooldown manager with persistent storage."""
    
    def __init__(self):
        self.cooldowns = {}  # {command_name: {user_id: timestamp}}
    
    def is_on_cooldown(self, command_name: str, user_id: int, cooldown_seconds: int) -> bool:
        """Check if a user is on cooldown for a specific command."""
        if command_name not in self.cooldowns:
            return False
        
        user_cooldown = self.cooldowns[command_name].get(user_id)
        if not user_cooldown:
            return False
        
        return time.time() - user_cooldown < cooldown_seconds
    
    def set_cooldown(self, command_name: str, user_id: int):
        """Set a cooldown for a user on a specific command."""
        if command_name not in self.cooldowns:
            self.cooldowns[command_name] = {}
        self.cooldowns[command_name][user_id] = time.time()
    
    def get_remaining_time(self, command_name: str, user_id: int, cooldown_seconds: int) -> float:
        """Get remaining cooldown time in seconds."""
        if not self.is_on_cooldown(command_name, user_id, cooldown_seconds):
            return 0.0
        
        elapsed = time.time() - self.cooldowns[command_name][user_id]
        return max(0.0, cooldown_seconds - elapsed)
    
    def cleanup(self):
        """Remove expired cooldowns to free memory."""
        current_time = time.time()
        for command_name in list(self.cooldowns.keys()):
            for user_id in list(self.cooldowns[command_name].keys()):
                # Remove cooldowns older than 1 hour
                if current_time - self.cooldowns[command_name][user_id] > 3600:
                    del self.cooldowns[command_name][user_id]
            
            if not self.cooldowns[command_name]:
                del self.cooldowns[command_name]

# Global cooldown instance
cooldown_manager = CooldownManager()

# ============================================
# MESSAGE UTILITIES
# ============================================

async def safe_send(ctx: commands.Context, content: str = None, embed: discord.Embed = None, ephemeral: bool = False):
    """Safely send a message, handling both slash and prefix commands."""
    try:
        if ctx.interaction:
            await ctx.send(content=content, embed=embed, ephemeral=ephemeral)
        else:
            await ctx.send(content=content, embed=embed)
    except discord.HTTPException as e:
        logger.error(f"Failed to send message: {e}")

async def delete_message_after_delay(message: discord.Message, delay: int = 5):
    """Delete a message after a specified delay."""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except (discord.NotFound, discord.Forbidden):
        pass

def chunk_text(text: str, limit: int = 2000) -> List[str]:
    """Split text into chunks of a specific limit."""
    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        split_at = text.rfind('\n', 0, limit)
        if split_at == -1:
            split_at = text.rfind(' ', 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()
    return chunks

# ============================================
# TIME & DATE UTILITIES
# ============================================

def parse_duration(duration_str: str) -> Optional[int]:
    """Parse a duration string (e.g., '10s', '5m', '2h', '1d') into seconds."""
    if not duration_str:
        return None
    
    duration_str = duration_str.lower().strip()
    
    if duration_str.endswith('s'):
        return int(duration_str[:-1])
    elif duration_str.endswith('m'):
        return int(duration_str[:-1]) * 60
    elif duration_str.endswith('h'):
        return int(duration_str[:-1]) * 3600
    elif duration_str.endswith('d'):
        return int(duration_str[:-1]) * 86400
    elif duration_str.endswith('w'):
        return int(duration_str[:-1]) * 604800
    else:
        try:
            return int(duration_str)
        except ValueError:
            return None

def format_time(seconds: int) -> str:
    """Format seconds into a human-readable string."""
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    
    return " ".join(parts)

# ============================================
# DISCORD OBJECT FINDERS
# ============================================

def find_role_by_name_or_mention(guild: discord.Guild, role_input: str) -> Optional[discord.Role]:
    """Find a role by name, mention, or ID."""
    # Try mention
    if role_input.startswith('<@&') and role_input.endswith('>'):
        try:
            role_id = int(role_input[3:-1])
            return guild.get_role(role_id)
        except ValueError:
            pass
    
    # Try ID
    if role_input.isdigit():
        role = guild.get_role(int(role_input))
        if role:
            return role
    
    # Try exact name
    for role in guild.roles:
        if role.name.lower() == role_input.lower():
            return role
    
    # Try partial name
    for role in guild.roles:
        if role_input.lower() in role.name.lower():
            return role
    
    return None

def find_channel_by_name_or_mention(guild: discord.Guild, channel_input: str) -> Optional[discord.TextChannel]:
    """Find a text channel by name, mention, or ID."""
    # Try mention
    if channel_input.startswith('<#') and channel_input.endswith('>'):
        try:
            channel_id = int(channel_input[2:-1])
            return guild.get_channel(channel_id)
        except ValueError:
            pass
    
    # Try ID
    if channel_input.isdigit():
        channel = guild.get_channel(int(channel_input))
        if channel:
            return channel
    
    # Try exact name
    for channel in guild.text_channels:
        if channel.name.lower() == channel_input.lower():
            return channel
    
    # Try partial name
    for channel in guild.text_channels:
        if channel_input.lower() in channel.name.lower():
            return channel
    
    return None

def find_member_by_name_or_id(guild: discord.Guild, member_input: str) -> Optional[discord.Member]:
    """Find a member by name, mention, or ID."""
    # Try mention
    if member_input.startswith('<@') and member_input.endswith('>'):
        try:
            member_id = int(member_input[2:-1].replace('!', ''))
            return guild.get_member(member_id)
        except ValueError:
            pass
    
    # Try ID
    if member_input.isdigit():
        return guild.get_member(int(member_input))
    
    # Try exact name
    for member in guild.members:
        if member.name.lower() == member_input.lower() or member.display_name.lower() == member_input.lower():
            return member
    
    # Try partial name
    for member in guild.members:
        if member_input.lower() in member.name.lower() or member_input.lower() in member.display_name.lower():
            return member
    
    return None

# ============================================
# RANDOM UTILITIES
# ============================================

def random_hex_color() -> str:
    """Generate a random hex color."""
    return f"#{random.randint(0, 0xFFFFFF):06x}"

def random_choice_with_weights(items: list, weights: list):
    """Choose a random item with weighted probabilities."""
    return random.choices(items, weights=weights, k=1)[0]

# ============================================
# FILE UTILITIES
# ============================================

import json
import os

def load_json(file_path: str, default: dict = None) -> dict:
    """Load a JSON file with error handling."""
    if default is None:
        default = {}
    
    if not os.path.exists(file_path):
        return default
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load {file_path}: {e}")
        return default

def save_json(file_path: str, data: dict):
    """Save data to a JSON file with error handling."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        logger.error(f"Failed to save {file_path}: {e}")

# ============================================
# CHECKS AND DECORATORS
# ============================================

def is_owner_check(ctx: commands.Context) -> bool:
    """Check if the user is a bot owner."""
    return ctx.author.id in ctx.bot.owner_ids

def is_admin_check(ctx: commands.Context) -> bool:
    """Check if the user is a bot owner or guild admin."""
    return is_owner_check(ctx) or ctx.author.guild_permissions.administrator

def is_mod_check(ctx: commands.Context) -> bool:
    """Check if the user is a bot owner, guild admin, or mod."""
    return is_admin_check(ctx) or ctx.author.guild_permissions.kick_members or ctx.author.guild_permissions.ban_members

# Custom checks
def is_owner():
    async def predicate(ctx: commands.Context):
        return is_owner_check(ctx)
    return commands.check(predicate)

def is_admin():
    async def predicate(ctx: commands.Context):
        return is_admin_check(ctx)
    return commands.check(predicate)

def is_mod():
    async def predicate(ctx: commands.Context):
        return is_mod_check(ctx)
    return commands.check(predicate)