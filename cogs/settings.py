import discord
from discord.ext import commands
import json
import os
import shutil
import datetime
import asyncio
import base64

class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.backup_file = "bot_backup.json"
        
        # List of all JSON files your bot uses
        self.important_files = [
            "level_data.json",
            "level_roles.json",
            "welcome_data.json",
            "ticket_data.json",
            "giveaway_data.json",
            "economy_data.json",
        ]
        # Add the SQLite database to the backup list!
        self.important_db_files = ["level_data.db"]

    @commands.command(name="backup")
    @commands.has_permissions(administrator=True)
    async def backup_settings(self, ctx):
        """
        [Admin] Saves ALL bot settings/data into one backup file AND shows you the raw text.
        """
        await ctx.send("⏳ Creating a full backup of all bot data...")
        
        backup_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "server_id": str(ctx.guild.id),
            "files": {},
            "db_files": {}  # New section for SQLite databases
        }

        found_files = 0
        missing_files = 0

        # Loop through important JSON files
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

        # NEW: Loop through SQLite DB files
        for db_name in self.important_db_files:
            if os.path.exists(db_name):
                try:
                    with open(db_name, 'rb') as f:
                        # Encode binary SQLite as base64 to store in JSON
                        content = base64.b64encode(f.read()).decode('utf-8')
                        backup_data["db_files"][db_name] = content
                        found_files += 1
                except Exception as e:
                    await ctx.send(f"⚠️ Error reading {db_name}: {e}")
            else:
                missing_files += 1

        if found_files == 0:
            return await ctx.send("❌ No existing data files found to backup!")

        # Save the combined backup locally
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
            
            backup_json_string = json.dumps(backup_data, indent=4)
            
            await ctx.send(
                embed=embed, 
                file=discord.File(self.backup_file)
            )
            
            await ctx.send(
                "📋 **Copy this text below and save it somewhere safe!**\n" +
                "If you lose all your files, use `!recover` and paste this text back (or attach it as a file!).",
                ephemeral=False
            )
            
            if len(backup_json_string) > 1900:
                for i in range(0, len(backup_json_string), 1900):
                    await ctx.send(f"```json\n{backup_json_string[i:i+1900]}\n```")
            else:
                await ctx.send(f"```json\n{backup_json_string}\n```")
            
        except Exception as e:
            await ctx.send(f"❌ Failed to save backup: {e}")

    @commands.command(name="recover")
    @commands.has_permissions(administrator=True)
    async def recover_from_paste(self, ctx, *, json_text: str = None):
        """
        [Admin] Pastes the JSON text OR attaches the .txt/.json file from !backup to restore EVERYTHING.
        """
        await ctx.send("⏳ Processing recovery data...")

        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            if attachment.filename.endswith(('.txt', '.json')):
                try:
                    file_content = await attachment.read()
                    json_text = file_content.decode('utf-8')
                except Exception as e:
                    return await ctx.send(f"❌ Failed to read the attached file: {e}")
            else:
                return await ctx.send("❌ Please attach a `.txt` or `.json` file from `!backup`.")

        elif json_text is None:
            return await ctx.send("❌ You must either paste the JSON text right after the command, OR attach the `message.txt` file!")

        try:
            if json_text.startswith("```"):
                lines = json_text.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].strip() == "```":
                    lines = lines[:-1]
                json_text = "\n".join(lines)

            backup_data = json.loads(json_text.strip())

            if "files" not in backup_data:
                return await ctx.send("❌ Invalid backup format! Make sure you copied the full output from `!backup`.")

            restored_count = 0
            failed_count = 0

            # Restore JSON Files
            for file_name, content in backup_data["files"].items():
                try:
                    json.dumps(content)
                    with open(file_name, 'w', encoding='utf-8') as f:
                        json.dump(content, f, indent=4)
                    restored_count += 1
                except Exception as e:
                    failed_count += 1
                    await ctx.send(f"⚠️ Failed to restore {file_name}: {e}")

            # NEW: Restore SQLite DB Files
            if "db_files" in backup_data:
                for db_name, encoded_content in backup_data["db_files"].items():
                    try:
                        # Decode base64 back to binary and write it
                        binary_data = base64.b64decode(encoded_content)
                        with open(db_name, 'wb') as f:
                            f.write(binary_data)
                        restored_count += 1
                    except Exception as e:
                        failed_count += 1
                        await ctx.send(f"⚠️ Failed to restore {db_name}: {e}")

            # Recreate the local bot_backup.json file
            try:
                with open(self.backup_file, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=4)
            except:
                pass

            embed = discord.Embed(
                title="✅ Recovery Complete! Everything is restored!",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="✅ Files Restored", value=str(restored_count), inline=True)
            embed.add_field(name="❌ Files Failed", value=str(failed_count), inline=True)
            embed.add_field(name="📅 Backup Timestamp", value=backup_data.get("timestamp", "Unknown"), inline=False)
            embed.set_footer(text="Restart the bot to fully apply all settings to memory.")

            await ctx.send(embed=embed)

            if "level_data.db" in backup_data.get("db_files", {}):
                await ctx.send("💡 **Tip:** SQLite database restored! Run `!level` to check your rank.")

        except json.JSONDecodeError:
            await ctx.send("❌ **Invalid JSON!** Make sure you copied the entire text from the `!backup` command properly.")
        except Exception as e:
            await ctx.send(f"❌ Failed to recover backup: {e}")

    @commands.command(name="listbackup")
    @commands.has_permissions(administrator=True)
    async def list_backup_files(self, ctx):
        """Shows which files are stored in the current backup."""
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
            db_list = list(backup_data.get("db_files", {}).keys())
            
            if files_list:
                embed.add_field(name="📁 JSON Files", value="\n".join(files_list), inline=False)
            if db_list:
                embed.add_field(name="🗄️ SQLite Databases", value="\n".join(db_list), inline=False)
            
            if not files_list and not db_list:
                embed.add_field(name="📁 Files in Backup", value="No files found in backup.", inline=False)
            
            embed.set_footer(text=f"Backup created at: {backup_data.get('timestamp', 'Unknown')}")
            
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Failed to read backup: {e}")

async def setup(bot):
    await bot.add_cog(Settings(bot))
