import discord
from discord.ext import commands
import asyncio
import re
from datetime import datetime, timedelta

class ChatCmds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="deletemsg")
    @commands.has_permissions(manage_messages=True)
    async def deletemsg(self, ctx, target: str, time_str: str = None):
        """
        Delete messages by amount, message link, channel, category, user, or time.
        Usage:
        !deletemsg 100                - Deletes the last 100 messages
        !deletemsg all                - Deletes all messages in this channel
        !deletemsg https://...        - Deletes up to a specific message link
        !deletemsg 10s                - Deletes the command message after 10 seconds
        !deletemsg #channel           - Deletes ALL messages in that specific channel
        !deletemsg "Category Name"    - Deletes ALL messages in ALL channels inside that category
        !deletemsg @user              - Deletes ALL messages sent by that user in this channel
        !deletemsg @user 10s          - Deletes ALL messages by that user after 10 seconds
        !deletemsg 1234567890         - Deletes ALL messages by that User ID in this channel
        !deletemsg 1234567890 5m      - Deletes ALL messages by that User ID after 5 minutes
        """

        # --- 1. CHECK IF IT IS A TIME-BASED SELF-DELETE (e.g., !deletemsg 10s) ---
        time_match = re.match(r'^(\d+)([smh])$', target.lower())
        if time_match and not time_str:
            amount = int(time_match.group(1))
            unit = time_match.group(2)
            
            seconds = 0
            if unit == 's': seconds = amount
            elif unit == 'm': seconds = amount * 60
            elif unit == 'h': seconds = amount * 3600

            if seconds > 86400:
                await ctx.send("❌ Maximum time is 24 hours (24h).", delete_after=5)
                return

            await ctx.send(f"⏳ Deleting command message in **{target}**...")
            await asyncio.sleep(seconds)
            
            try:
                await ctx.message.delete()
                confirm = await ctx.send(f"✅ Command deleted after {target}.", delete_after=5)
            except:
                pass
            return

        # --- 2. CHECK IF IT IS A MESSAGE LINK ---
        if "discord.com/channels/" in target or "discordapp.com/channels/" in target:
            await self.delete_until_message(ctx, target)
            return

        # --- 3. PARSE THE TARGET ---
        target_obj = None
        delete_scope = "channel" # Default to current channel
        wait_seconds = 0

        # Parse time string if provided (for user deletion)
        if time_str:
            time_match = re.match(r'^(\d+)([smh])$', time_str.lower())
            if time_match:
                amount = int(time_match.group(1))
                unit = time_match.group(2)
                if unit == 's': wait_seconds = amount
                elif unit == 'm': wait_seconds = amount * 60
                elif unit == 'h': wait_seconds = amount * 3600
                
                if wait_seconds > 86400:
                    await ctx.send("❌ Maximum wait time is 24 hours.", delete_after=5)
                    return
            else:
                await ctx.send("❌ Invalid time format. Use like `10s`, `5m`, `1h`.", delete_after=5)
                return

        # Channel Mention (#channel)
        if target.startswith('<#') and target.endswith('>'):
            channel_id = int(target[2:-1])
            target_obj = ctx.guild.get_channel(channel_id)
            delete_scope = "channel"

        # Category Name (must be in quotes if spaces)
        elif target.startswith('"') and target.endswith('"'):
            cat_name = target.strip('"')
            target_obj = discord.utils.get(ctx.guild.categories, name=cat_name)
            delete_scope = "category"

        # User Mention
        elif target.startswith('<@') and target.endswith('>'):
            user_id = int(target.replace('<@', '').replace('>', '').replace('!', ''))
            target_obj = ctx.guild.get_member(user_id)
            delete_scope = "user"

        # Numeric User ID
        elif target.isdigit() and len(target) >= 17:
            target_obj = ctx.guild.get_member(int(target))
            delete_scope = "user"
        
        # "all" (current channel)
        elif target.lower() == "all":
            target_obj = ctx.channel
            delete_scope = "channel"

        # Number (Bulk amount)
        else:
            try:
                amount = int(target)
                if amount <= 0:
                    await ctx.send("❌ Please specify a positive number.", delete_after=5)
                    return
                await self.delete_amount_messages(ctx, amount)
                return
            except ValueError:
                pass

        # --- 4. VALIDATION AND EXECUTION ---
        if not target_obj:
            await ctx.send("❌ Invalid target. Use a number, channel mention, category name (in quotes), user mention, user ID, or message link.", delete_after=5)
            return

        if delete_scope == "channel" and isinstance(target_obj, discord.TextChannel):
            if wait_seconds > 0:
                await ctx.send(f"⏳ Preparing to delete ALL messages in {target_obj.mention} in **{time_str}**...")
                await asyncio.sleep(wait_seconds)
            await self.wipe_entire_channel(ctx, target_obj)

        elif delete_scope == "category" and isinstance(target_obj, discord.CategoryChannel):
            if wait_seconds > 0:
                await ctx.send(f"⏳ Preparing to delete ALL messages in the **{target_obj.name}** category in **{time_str}**...")
                await asyncio.sleep(wait_seconds)
            await self.wipe_category(ctx, target_obj)

        elif delete_scope == "user" and isinstance(target_obj, discord.Member):
            if wait_seconds > 0:
                await ctx.send(f"⏳ Preparing to delete ALL messages from {target_obj.mention} in **{time_str}**...")
                await asyncio.sleep(wait_seconds)
            await self.delete_user_messages(ctx, target_obj)

        else:
            await ctx.send("❌ Target not found or invalid type.", delete_after=5)

    # =========================================================
    # HELPER FUNCTIONS FOR LARGE SCALE DELETIONS
    # =========================================================

    async def wipe_entire_channel(self, ctx, channel: discord.TextChannel):
        """Deletes EVERY message in a specific text channel."""
        msg = await ctx.send(f"⚠️ **WARNING**: You are about to delete **ALL** messages in {channel.mention}.\nType `confirm` within 10 seconds.")
        if not await self.confirm_action(ctx, 10):
            return

        # Delete command and warning
        try:
            await ctx.message.delete()
            await msg.delete()
        except: pass

        deleted = 0
        progress = await ctx.send(f"🔄 Deleting ALL messages in {channel.mention}...", delete_after=5)

        while True:
            messages = []
            async for msg in channel.history(limit=100):
                messages.append(msg)
            
            if not messages:
                break
            await channel.delete_messages(messages)
            deleted += len(messages)

            if deleted % 500 == 0:
                try:
                    await progress.edit(content=f"🔄 Deleted {deleted} messages so far...")
                except: pass
            await asyncio.sleep(0.5)

        final = await ctx.send(f"✅ Deleted **{deleted}** messages from {channel.mention}.")
        await asyncio.sleep(5)
        await final.delete()

    async def wipe_category(self, ctx, category: discord.CategoryChannel):
        """Deletes EVERY message in all text channels inside a category."""
        text_channels = [ch for ch in category.channels if isinstance(ch, discord.TextChannel)]
        if not text_channels:
            await ctx.send("❌ No text channels found in this category.", delete_after=5)
            return

        msg = await ctx.send(f"⚠️ **WARNING**: You are about to delete ALL messages in **{len(text_channels)}** channels inside the **{category.name}** category.\nType `confirm` within 10 seconds.")
        if not await self.confirm_action(ctx, 10):
            return

        try:
            await ctx.message.delete()
            await msg.delete()
        except: pass

        total_deleted = 0
        progress = await ctx.send(f"🔄 Deleting ALL messages in {len(text_channels)} channels...", delete_after=5)

        for channel in text_channels:
            deleted = 0
            while True:
                messages = []
                async for msg in channel.history(limit=100):
                    messages.append(msg)
                if not messages:
                    break
                await channel.delete_messages(messages)
                deleted += len(messages)
                total_deleted += len(messages)
                await asyncio.sleep(0.5)
            await progress.edit(content=f"🔄 Cleaned `{channel.name}` ({deleted} msgs)... Total: {total_deleted}")

        final = await ctx.send(f"✅ Deleted **{total_deleted}** messages across **{len(text_channels)}** channels.")
        await asyncio.sleep(5)
        await final.delete()

    async def delete_user_messages(self, ctx, user: discord.Member):
        """Deletes ALL messages sent by a specific user in the current channel."""
        msg = await ctx.send(f"⚠️ **WARNING**: You are about to delete **ALL** messages sent by {user.mention} in this channel.\nType `confirm` within 10 seconds.")
        if not await self.confirm_action(ctx, 10):
            return

        try:
            await ctx.message.delete()
            await msg.delete()
        except: pass

        deleted = 0
        progress = await ctx.send(f"🔄 Deleting {user.mention}'s messages...", delete_after=5)

        while True:
            messages = []
            async for msg in ctx.channel.history(limit=100):
                if msg.author.id == user.id:
                    messages.append(msg)
            
            if not messages:
                break
            await ctx.channel.delete_messages(messages)
            deleted += len(messages)
            
            if deleted % 500 == 0:
                try:
                    await progress.edit(content=f"🔄 Deleted {deleted} of {user.mention}'s messages...")
                except: pass
            await asyncio.sleep(0.5)

        final = await ctx.send(f"✅ Deleted **{deleted}** messages from {user.mention}.")
        await asyncio.sleep(5)
        await final.delete()

    async def delete_amount_messages(self, ctx, amount):
        """Delete a specific number of messages"""
        if amount > 2000:
            await ctx.send("⚠️ Bulk deletion is limited to 2000 messages per command for stability.", delete_after=5)
            amount = 2000

        # Purge is more reliable than manual loops for small amounts
        deleted = await ctx.channel.purge(limit=amount + 1) # +1 to delete command too
        confirm = await ctx.send(f"✅ Deleted {len(deleted) - 1} messages.", delete_after=5)

    async def delete_until_message(self, ctx, message_link):
        """Delete all messages up to and including the specified message"""
        try:
            match = re.search(r'/channels/\d+/(\d+)/(\d+)$', message_link)
            if not match:
                match = re.search(r'/channels/@me/(\d+)/(\d+)$', message_link)
            
            if not match:
                await ctx.send("❌ Invalid message link.", delete_after=5)
                return
            
            message_id = int(match.group(2))
            try:
                target_message = await ctx.channel.fetch_message(message_id)
            except:
                await ctx.send("❌ Message not found in this channel.", delete_after=5)
                return
            
            # Count how many messages will be deleted
            msg_count = 0
            async for _ in ctx.channel.history(after=target_message, limit=None):
                msg_count += 1
            
            msg = await ctx.send(f"⚠️ This will delete **{msg_count}** messages (up to the linked message).\nType `confirm` within 10 seconds.")
            if not await self.confirm_action(ctx, 10):
                return
            
            try:
                await ctx.message.delete()
                await msg.delete()
            except: pass

            deleted = 0
            progress = await ctx.send(f"🔄 Deleting {msg_count} messages...", delete_after=5)
            
            messages_to_delete = []
            async for msg in ctx.channel.history(after=target_message, limit=None):
                messages_to_delete.append(msg)
            messages_to_delete.append(target_message)
            
            for i in range(0, len(messages_to_delete), 100):
                chunk = messages_to_delete[i:i+100]
                await ctx.channel.delete_messages(chunk)
                deleted += len(chunk)
                await asyncio.sleep(0.5)
            
            final = await ctx.send(f"✅ Deleted **{deleted}** messages (up to the linked message).")
            await asyncio.sleep(5)
            await final.delete()

        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}", delete_after=5)

    # =========================================================
    # UTILITY FUNCTIONS
    # =========================================================

    async def confirm_action(self, ctx, timeout=10):
        """Waits for the user to type 'confirm'. Returns True if they did."""
        def check(m):
            return m.author == ctx.author and m.content.lower() == "confirm" and m.channel == ctx.channel
        try:
            await self.bot.wait_for('message', timeout=timeout, check=check)
            return True
        except asyncio.TimeoutError:
            await ctx.send("❌ Action cancelled. No messages were deleted.", delete_after=5)
            return False

    # =========================================================
    # EXISTING COMMAND: sendmsgforuser
    # =========================================================

    @commands.command(name="sendmsgforuser")
    @commands.has_permissions(administrator=True)
    async def sendmsgforuser(self, ctx, user_id: int, *, message: str):
        """
        Send a message as if it came from a specific user using their User ID.
        Usage: !sendmsgforuser 123456789012345678 Your message here
        Optional: !sendmsgforuser 123456789012345678 987654321098765432 Your message here (to send in a specific channel)
        """
        
        # Check if there's a channel ID specified (format: user_id channel_id message)
        args = message.split()
        channel_id = None
        actual_message = message
        
        # Check if the first argument is a channel ID (numeric and long enough)
        if args and len(args) > 0 and args[0].isdigit() and len(args[0]) >= 17:
            potential_channel_id = int(args[0])
            try:
                test_channel = self.bot.get_channel(potential_channel_id)
                if test_channel:
                    channel_id = potential_channel_id
                    actual_message = ' '.join(args[1:]) 
                else:
                    actual_message = message
            except:
                actual_message = message
        else:
            actual_message = message
        
        # Get the target user
        try:
            user = await self.bot.fetch_user(user_id)
        except discord.NotFound:
            await ctx.send(f"❌ User with ID `{user_id}` not found.", delete_after=10)
            return
        except discord.HTTPException:
            await ctx.send(f"❌ Failed to fetch user with ID `{user_id}`.", delete_after=10)
            return
        
        # Determine which channel to send to
        target_channel = ctx.channel
        if channel_id:
            target_channel = self.bot.get_channel(channel_id)
            if not target_channel:
                await ctx.send(f"❌ Channel with ID `{channel_id}` not found.", delete_after=10)
                return
            if not isinstance(target_channel, discord.TextChannel):
                await ctx.send(f"❌ The specified channel is not a text channel.", delete_after=10)
                return
        
        # Check if the bot has permission to manage webhooks
        if not target_channel.permissions_for(ctx.guild.me).manage_webhooks:
            await ctx.send(f"❌ I don't have the `Manage Webhooks` permission in {target_channel.mention}.", delete_after=10)
            return
        
        # Create a webhook in the channel
        webhook = None
        try:
            existing_webhooks = await target_channel.webhooks()
            for wh in existing_webhooks:
                if wh.name == "MessageSenderBot":
                    webhook = wh
                    break
            
            if not webhook:
                webhook = await target_channel.create_webhook(name="MessageSenderBot")
                
        except discord.Forbidden:
            await ctx.send(f"❌ I don't have permission to create webhooks in {target_channel.mention}.", delete_after=10)
            return
        except Exception as e:
            await ctx.send(f"❌ Failed to create webhook: {str(e)}", delete_after=10)
            return
        
        try:
            if user.bot:
                display_name = user.name
            else:
                display_name = user.display_name or user.name
            
            await webhook.send(
                content=actual_message,
                username=display_name,
                avatar_url=user.display_avatar.url
            )
            
            try:
                await ctx.message.delete()
            except:
                pass
                
        except discord.Forbidden:
            await ctx.send(f"❌ I don't have permission to send messages through the webhook in {target_channel.mention}.", delete_after=10)
        except Exception as e:
            await ctx.send(f"❌ Failed to send message: {str(e)}", delete_after=10)

    # =========================================================
    # ERROR HANDLERS
    # =========================================================

    @sendmsgforuser.error
    async def sendmsgforuser_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need `Administrator` permission to use this command.", delete_after=5)
        elif isinstance(error, commands.MissingRequiredArgument):
            if "user_id" in str(error):
                await ctx.send("❌ Provide a user ID. Use `!whoami` to get yours.", delete_after=15)
            elif "message" in str(error):
                await ctx.send("❌ Provide a message to send.", delete_after=15)
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid user ID. Use `!whoami` to get yours.", delete_after=10)
        else:
            await ctx.send(f"❌ An error occurred: {str(error)}", delete_after=5)

    @deletemsg.error
    async def deletemsg_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need `Manage Messages` permission to use this command.", delete_after=5)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Missing argument. Use `!help deletemsg` for usage.", delete_after=10)
        else:
            await ctx.send(f"❌ An error occurred: {str(error)}", delete_after=5)


async def setup(bot):
    await bot.add_cog(ChatCmds(bot))