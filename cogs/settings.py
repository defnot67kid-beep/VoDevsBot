import discord
from discord.ext import commands
import json
import os
import shutil
import datetime
import asyncio

class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.backup_file = "bot_backup.json"
        
        # List of all JSON files your bot uses
        self.important_files = [
            "level_data.json",
            "level_roles.json",
            "welcome_data.json",
            "ticket_data.json",  # If you have ticket data
            "giveaway_data.json", # If you have giveaway data
            "economy_data.json",  # If you have economy data
            # Add any other JSON files your bot uses here!
        ]

    @commands.command(name="backup")
    @commands.has_permissions(administrator=True)
    async def backup_settings(self, ctx):
        """
        [Admin] Saves ALL bot settings/data into one backup file.
        Usage: !backup
        """
        await ctx.send("⏳ Creating a full backup of all bot data...")
        
        backup_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "server_id": str(ctx.guild.id),
            "files": {}
        }

        found_files = 0
        missing_files = 0

        # Loop through all important JSON files
        for file_name in self.important_files:
            if os.path.exists(file_name):
                try:
                    with open(file_name, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                        backup_data["files"][file_name] = content
                        found_files += 1
                except Exception as e:
                    await ctx.send(f"⚠️ Error reading {file_name}: {e}")
            else:
                missing_files += 1

        if found_files == 0:
            return await ctx.send("❌ No existing data files found to backup!")

        # Save the combined backup
        try:
            with open(self.backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=4)
            
            embed = discord.Embed(
                title="✅ Backup Created Successfully!",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="📁 Files Backed Up", value=str(found_files), inline=True)
            embed.add_field(name="📁 Files Missing/Skipped", value=str(missing_files), inline=True)
            embed.add_field(name="💾 Backup File", value=f"`{self.backup_file}`", inline=False)
            
            # Send the backup file as an attachment so you can download it!
            await ctx.send(embed=embed, file=discord.File(self.backup_file))
            
        except Exception as e:
            await ctx.send(f"❌ Failed to save backup: {e}")

    @commands.command(name="restore")
    @commands.has_permissions(administrator=True)
    async def restore_backup(self, ctx):
        """
        [Admin] Restores ALL bot settings from the backup file.
        Usage: !restore
        """
        if not os.path.exists(self.backup_file):
            return await ctx.send("❌ No backup file found! Run `!backup` first.")

        await ctx.send("⏳ Restoring data from backup...")

        try:
            with open(self.backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

            restored_count = 0
            failed_count = 0

            for file_name, content in backup_data["files"].items():
                try:
                    # Save the restored data back to its original file
                    with open(file_name, 'w', encoding='utf-8') as f:
                        json.dump(content, f, indent=4)
                    restored_count += 1
                except Exception as e:
                    failed_count += 1
                    await ctx.send(f"⚠️ Failed to restore {file_name}: {e}")

            embed = discord.Embed(
                title="✅ Backup Restored Successfully!",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="✅ Files Restored", value=str(restored_count), inline=True)
            embed.add_field(name="❌ Files Failed", value=str(failed_count), inline=True)
            embed.add_field(name="📅 Backup Timestamp", value=backup_data.get("timestamp", "Unknown"), inline=False)
            
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Failed to restore backup: {e}")

    @commands.command(name="listbackup")
    @commands.has_permissions(administrator=True)
    async def list_backup_files(self, ctx):
        """
        [Admin] Shows which files are stored in the current backup.
        Usage: !listbackup
        """
        if not os.path.exists(self.backup_file):
            return await ctx.send("❌ No backup file found! Run `!backup` first.")

        try:
            with open(self.backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

            embed = discord.Embed(
                title="📂 Backup Contents",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            
            files_list = list(backup_data.get("files", {}).keys())
            if files_list:
                embed.add_field(name="📁 Files in Backup", value="\n".join(files_list), inline=False)
            else:
                embed.add_field(name="📁 Files in Backup", value="No files found in backup.", inline=False)
            
            embed.set_footer(text=f"Backup created at: {backup_data.get('timestamp', 'Unknown')}")
            
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Failed to read backup: {e}")

    @commands.command(name="autobackup")
    @commands.has_permissions(administrator=True)
    async def auto_backup_toggle(self, ctx, status: str = None):
        """
        [Admin] Enables or disables automatic hourly backups.
        Usage: !autobackup on / !autobackup off
        """
        if status is None:
            return await ctx.send("❌ Please specify `on` or `off`. Example: `!autobackup on`")

        guild_id = str(ctx.guild.id)
        config_file = "autobackup_config.json"
        
        # Load existing config
        config = {}
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)

        if status.lower() == "on":
            config[guild_id] = True
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
            await ctx.send("✅ **Auto-backup ENABLED**! The bot will automatically backup all data every 1 hour.")
            
            # Start the background task
            self.bot.loop.create_task(self.auto_backup_task(ctx.guild.id))
            
        elif status.lower() == "off":
            if guild_id in config:
                del config[guild_id]
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=4)
            await ctx.send("✅ **Auto-backup DISABLED**.")
            
        else:
            await ctx.send("❌ Invalid option. Use `on` or `off`.")

    async def auto_backup_task(self, guild_id):
        """Background task that automatically backs up data every hour"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            # Check if auto-backup is still enabled
            config_file = "autobackup_config.json"
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                if str(guild_id) not in config or not config[str(guild_id)]:
                    break  # Stop the loop if disabled
            
            # Perform the backup
            backup_data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "server_id": str(guild_id),
                "files": {}
            }
            
            for file_name in self.important_files:
                if os.path.exists(file_name):
                    try:
                        with open(file_name, 'r', encoding='utf-8') as f:
                            content = json.load(f)
                            backup_data["files"][file_name] = content
                    except:
                        pass
            
            try:
                with open(self.backup_file, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=4)
                print(f"[Auto-Backup] Successfully backed up data at {datetime.datetime.now()}")
            except Exception as e:
                print(f"[Auto-Backup] Failed: {e}")
            
            # Wait 1 hour (3600 seconds)
            await asyncio.sleep(3600)

async def setup(bot):
    await bot.add_cog(Settings(bot))
