import discord
from discord.ext import commands
from discord.ui import Select, View, Modal, TextInput
import asyncio
import secrets
import string
from datetime import datetime, timedelta

# ============================================
# 1. THE POPUP FORM (MODAL)
# ============================================
class TicketModal(Modal, title="Create a Ticket"):
    def __init__(self, category_name, ping_role):
        super().__init__()
        self.category_name = category_name
        self.ping_role = ping_role

    help_input = TextInput(
        label="What do you need help with?",
        style=discord.TextStyle.paragraph,
        placeholder="Describe your issue in detail...",
        required=True,
        min_length=20,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        member = interaction.user
        category_name = self.category_name
        issue_description = self.help_input.value
        ping_role = self.ping_role

        # 1. Check if the user already has an open ticket
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel) and channel.name.startswith("ticket-"):
                if member in channel.members:
                    await interaction.followup.send("❌ You already have an open ticket! Please close it before opening a new one.", ephemeral=True)
                    return

        # 2. GENERATE A UNIQUE RANDOM CODE
        alphabet = string.ascii_lowercase + string.digits
        while True:
            ticket_code = ''.join(secrets.choice(alphabet) for _ in range(5))
            channel_name = f"ticket-{ticket_code}"
            
            if not discord.utils.get(guild.channels, name=channel_name):
                break 

        # 3. Create the ticket channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            member: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                read_message_history=True
            )
        }

        # Add the ticket roles to the channel overwrites so they can see it
        ticket_role = discord.utils.get(guild.roles, name="Ticket Support")
        report_role = discord.utils.get(guild.roles, name="Report Player Staff")
        suggest_role = discord.utils.get(guild.roles, name="Suggestion & Report Staff")

        if ticket_role:
            overwrites[ticket_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        if report_role:
            overwrites[report_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        if suggest_role:
            overwrites[suggest_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            reason=f"New ticket opened by {member} for {category_name}"
        )

        # 4. Send the initial message in the new ticket channel with the role ping
        embed = discord.Embed(
            title="🎫 Ticket Opened",
            description=(
                f"Hello {member.mention},\n"
                f"Thank you for contacting support!\n"
                f"**Category:** {category_name}\n"
                f"**Reason:** {issue_description}\n\n"
                f"Please wait patiently, a staff member will be with you shortly.\n\n"
                f"🕒 **Auto-Close:** This ticket will automatically close in 24 hours if inactive."
            ),
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        # CLOSE BUTTONS
        close_button = discord.ui.Button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_user")
        view = discord.ui.View()
        view.add_item(close_button)

        await ticket_channel.send(content=ping_role.mention if ping_role else None, embed=embed, view=view)

        # 5. Notify the user in the original channel
        await interaction.followup.send(f"✅ Ticket created! Please go to {ticket_channel.mention}", ephemeral=True)

        # 6. SCHEDULE AUTO-CLOSE IN 24 HOURS
        async def auto_close():
            await asyncio.sleep(86400) # 24 hours
            try:
                # Check if the channel still exists before deleting
                if ticket_channel and ticket_channel.guild:
                    await ticket_channel.send("⏰ **Auto-Closing:** This ticket has been inactive for 24 hours and is now being deleted.")
                    await asyncio.sleep(5)
                    await ticket_channel.delete(reason="Auto-closed after 24 hours of inactivity.")
            except:
                pass # Channel already deleted manually

        # Start the background task
        asyncio.create_task(auto_close())


# ============================================
# 2. THE DROPDOWN MENU (NOW IN A VIEW)
# ============================================
class TicketSelect(Select):
    def __init__(self, ticket_role, report_role, suggest_role):
        self.ticket_role = ticket_role
        self.report_role = report_role
        self.suggest_role = suggest_role

        options = [
            discord.SelectOption(label="Need Help With Smth", description="General questions or assistance", emoji="❔"),
            discord.SelectOption(label="Report a Player", description="Report rule-breaking or bad behavior", emoji="🚨"),
            discord.SelectOption(label="Suggestion", description="Suggest a new feature or improvement", emoji="💡"),
            discord.SelectOption(label="Report a Staff", description="File a complaint against a staff member", emoji="👮"),
            discord.SelectOption(label="Other", description="Anything else not covered above", emoji="📝"),
        ]
        super().__init__(placeholder="Make a selection", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_category = self.values[0]
        
        ping_role = None
        if selected_category in ["Need Help With Smth", "Other"]:
            ping_role = self.ticket_role
        elif selected_category == "Report a Player":
            ping_role = self.report_role
        elif selected_category in ["Suggestion", "Report a Staff"]:
            ping_role = self.suggest_role

        await interaction.response.send_modal(TicketModal(selected_category, ping_role))


class TicketView(View):
    def __init__(self, ticket_role, report_role, suggest_role):
        super().__init__(timeout=None)
        self.add_item(TicketSelect(ticket_role, report_role, suggest_role))


# ============================================
# 3. THE MAIN COG
# ============================================
class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ticketsetup")
    @commands.has_permissions(administrator=True)
    async def ticket_setup(self, ctx):
        """[Admin] Creates 3 roles and deploys the ticket panel."""
        
        # 👇 DELETE THE COMMAND MESSAGE IMMEDIATELY
        try:
            await ctx.message.delete()
        except:
            pass

        guild = ctx.guild

        # Send initial setup message
        setup_msg = await ctx.send("⏳ Setting up roles...")

        async def get_or_create_role(name, color):
            role = discord.utils.get(guild.roles, name=name)
            if not role:
                role = await guild.create_role(name=name, color=color)
                return role, True
            return role, False

        ticket_role, ticket_created = await get_or_create_role("Ticket Support", discord.Color.blue())
        report_role, report_created = await get_or_create_role("Report Player Staff", discord.Color.red())
        suggest_role, suggest_created = await get_or_create_role("Suggestion & Report Staff", discord.Color.purple())

        await asyncio.sleep(1)
        await setup_msg.delete() # Delete the "Setting up roles..." message

        try:
            file = discord.File("ticket_banner.png", filename="banner.png")
        except FileNotFoundError:
            file = None

        embed = discord.Embed(color=discord.Color.blue())
        if file:
            embed.set_image(url="attachment://banner.png")

        embed.description = (
            "**Welcome!**\n\n"
            "To contact Vortex support, please select the appropriate category below.\n"
            "It's important that you select the most accurate category, this helps us better assist you!\n\n"
            "Please fill out the form to the best of your ability.\n"
            "Server Invite: https://discord.gg/HpGFYthxDR"
        )

        # 👇 CREATE THE VIEW THAT CONTAINS THE DROPDOWN INSIDE THE BOX
        view = TicketView(ticket_role, report_role, suggest_role)

        # 👇 SEND THE MESSAGE WITH THE EMBED AND THE VIEW ATTACHED
        await ctx.send(embed=embed, file=file, view=view)


    # ============================================
    # 4. CLOSE TICKET BUTTON HANDLER
    # ============================================
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        # ----------------------------------------------------------------
        # NORMAL USER CLOSES THE TICKET (Instantly deletes)
        # ----------------------------------------------------------------
        if interaction.data.get("custom_id") == "close_ticket_user":
            await interaction.response.defer()
            channel = interaction.channel
            
            await interaction.followup.send("🗑️ Closing ticket and deleting channel in 5 seconds...", ephemeral=True)
            await asyncio.sleep(5)
            try:
                await channel.delete()
            except:
                pass

        # ----------------------------------------------------------------
        # ADMIN BUTTONS (Only visible to CloseTicketsRoles)
        # ----------------------------------------------------------------
        elif interaction.data.get("custom_id") == "close_ticket_admin":
            await interaction.response.defer()

            close_role = discord.utils.get(interaction.guild.roles, name="CloseTicketsRoles")
            if not close_role or close_role not in interaction.user.roles:
                await interaction.followup.send("❌ You do not have the **CloseTicketsRoles** role to use this.", ephemeral=True)
                return

            embed = discord.Embed(
                title="🛠️ Admin Ticket Controls",
                description="You have the CloseTicketsRoles. Please select how you want to handle this ticket:",
                color=discord.Color.blue()
            )
            
            request_button = discord.ui.Button(label="📅 Request to Close", style=discord.ButtonStyle.primary, custom_id="admin_request_close")
            force_button = discord.ui.Button(label="❌ Force Close Now", style=discord.ButtonStyle.danger, custom_id="admin_force_close")
            
            view = discord.ui.View()
            view.add_item(request_button)
            view.add_item(force_button)
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        # ----------------------------------------------------------------
        # ADMIN: Request to Close (24h)
        # ----------------------------------------------------------------
        elif interaction.data.get("custom_id") == "admin_request_close":
            await interaction.response.defer()
            channel = interaction.channel
            
            await channel.send(
                f"⚠️ **Admin {interaction.user.mention} has requested to close this ticket.**\n"
                f"This channel will be automatically deleted in **24 hours**.\n"
                f"Click the **Close Ticket** button below if you wish to close it immediately."
            )
            await interaction.followup.send("✅ Request to close has been sent. The channel will auto-delete in 24 hours.", ephemeral=True)

        # ----------------------------------------------------------------
        # ADMIN: Force Close Now (Instant)
        # ----------------------------------------------------------------
        elif interaction.data.get("custom_id") == "admin_force_close":
            await interaction.response.defer()
            channel = interaction.channel
            
            await interaction.followup.send("🗑️ Force closing ticket and deleting channel in 5 seconds...", ephemeral=True)
            await asyncio.sleep(5)
            try:
                await channel.delete()
            except:
                pass

async def setup(bot):
    await bot.add_cog(Ticket(bot))