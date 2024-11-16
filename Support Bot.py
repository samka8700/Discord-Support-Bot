import disnake
from disnake.ext import commands
import sqlite3
import os
import asyncio

intents = disnake.Intents.default()
intents.message_content = True
bot = commands.InteractionBot(intents=intents)

bot_token = "Your Bot Token" 
guild_id = Your Server ID
category_id = Your category ID
log_channel_id = Your Log channel ID
owners_id = Admin(Owner) ID

@bot.event
async def on_ready():
    print("Bot is ready.")

def create_table():
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS blacklist (user_id INTEGER PRIMARY KEY);''')
    cur.execute('''CREATE TABLE IF NOT EXISTS ticket_channels (user_id INTEGER PRIMARY KEY, channel_id INTEGER);''')
    con.commit()
    con.close()

create_table()

def get_db_connection():
    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    return con

def save_ticket_channel(user_id, channel_id):
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("INSERT OR REPLACE INTO ticket_channels (user_id, channel_id) VALUES (?, ?);", (user_id, channel_id))
    con.commit()
    con.close()

def load_ticket_channel(user_id):
    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM ticket_channels WHERE user_id = ?;", (user_id,))
    channel = cur.fetchone()
    con.close()
    return channel

async def create_ticket_channel(guild, user):
    category = None
    for cat in guild.categories:
        if cat.name == "Inquiry":
            category = cat
            break
    if not category:
        category = await guild.create_category("Inquiry", position=len(guild.categories))

    try:
        overwrites = {
            guild.default_role: disnake.PermissionOverwrite(read_messages=False, send_messages=False),
        }
        ticket_channel = await guild.create_text_channel(
            name=f"Ticket-{user.name}",
            overwrites=overwrites,
            category=category
        )

        print(f"A new ticket channel {ticket_channel.name} has been created.")
        await ticket_channel.send(f"Your inquiry has been received, {user.mention}.")
        return ticket_channel
    except Exception as e:
        print(f"Error occurred while creating the channel: {e}")
        return None

@bot.event
async def on_message(message):
    if message.author.bot: 
        return

    if isinstance(message.channel, disnake.DMChannel) and message.author.id in owners_id:
        return

    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("SELECT * FROM blacklist WHERE user_id == ?;", (message.author.id,))
    exist = cur.fetchone()
    con.close()

    if exist:
        await message.author.send(f"You are blacklisted and cannot send inquiries.")
        return

    if isinstance(message.channel, disnake.DMChannel):
        category = bot.get_channel(category_id)
        guild = bot.get_guild(guild_id)
        ticket_channel = None

        for channel in category.channels:
            if isinstance(channel, disnake.TextChannel):
                tmp_channel = channel.name
                if f"Ticket-{message.author.id}" in str(tmp_channel):
                    ticket_channel = channel
                    await message.add_reaction("✅")
                    await message.add_reaction("👉")
                    await message.add_reaction("⭕")
                    await message.add_reaction("👶")
                    await message.add_reaction("🪦")
                    break

        if not ticket_channel:
            overwrites = {
                guild.default_role: disnake.PermissionOverwrite(read_messages=False, send_messages=False),
            }
            ticket_channel = await guild.create_text_channel(
                name=f"Ticket-{message.author.id}",
                category=category,
                overwrites=overwrites,
            )
            embed = disnake.Embed(title="Customer Service", description=f"{message.author.mention} Your inquiry has been received. Please wait for a response from customer service.\n\nInquiry content: {message.content}", timestamp=message.created_at)
            await message.channel.send(embed=embed)
            await ticket_channel.send(f"Your inquiry has been received, {message.author.mention}.")
        embed = disnake.Embed(title="Customer Service", description=message.content)
        embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url if message.author.display_avatar else 'https://logodownload.org/wp-content/uploads/2017/11/discord-logo-1-1.png')
        if message.attachments:
            embed.add_field(name="Attachment", value="\n".join([att.url for att in message.attachments]))
        await ticket_channel.send(embed=embed)
        for owner_id in owners_id:
            owner = await bot.fetch_user(owner_id)
            if owner:
                await owner.send(embed=embed)
            else:
                print(f"Owner with ID {owner_id} not found.")
        with open(f"log/ticket_{message.author.id}.txt", "a", encoding="utf-8") as file:
            file.write(f"{message.author.name}: {message.content}\n")
            if message.attachments:
                file.write("Attachment:\n")
                for att in message.attachments:
                    file.write(f"{att.url}\n")
    else:
        if message.channel.category_id == category_id and not message.author.bot:
            if message.channel.name.startswith("Ticket-"):
                user_id = int(message.channel.name.split("-")[1])
                try:
                    user = await bot.fetch_user(user_id)
                    if user:
                        embed = disnake.Embed(title=f"{bot.user.name}", description=message.content)
                        embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url if message.author.display_avatar else 'https://logodownload.org/wp-content/uploads/2017/11/discord-logo-1-1.png')
                        if message.attachments:
                            embed.add_field(name="Attachment", value="\n".join([att.url for att in message.attachments]))
                        await user.send(embed=embed)
                        await message.channel.send(f"The reply has been forwarded to {user.mention}.")
                        with open(f"log/ticket_{user_id}.txt", "a", encoding="utf-8") as file:
                            file.write(f"{message.author.name}: {message.content}\n")
                            if message.attachments:
                                file.write("Attachment:\n")
                                for att in message.attachments:
                                    file.write(f"{att.url}\n")
                    else:
                        error_message = f"Unable to retrieve user for this inquiry. (Channel name: {message.channel.name}, User ID: {user_id})"
                        await message.channel.send(error_message)
                        print(f"Error: {error_message}")
                except disnake.NotFound:
                    error_message = f"The user was not found. (User ID: {user_id})"
                    await message.channel.send(error_message)
                    print(f"Error: {error_message}")


@bot.slash_command(default_member_permissions=disnake.Permissions(administrator=True), guild_ids=[guild_id])
async def close(ctx):
    try:
        ticket_user_id = int(ctx.channel.name.split("-")[1])
        print(f"Extracted User ID: {ticket_user_id}")
        ticket_user = bot.get_user(ticket_user_id)
        if not ticket_user:
            ticket_user = await bot.fetch_user(ticket_user_id)
            print(f"Retrieved user information from the API: {ticket_user}") 
    except Exception as e:
        await ctx.send(f"Unable to retrieve user for this inquiry. Error: {str(e)}")
        return
    if ticket_user is None:
        await ctx.send("Unable to find the user for this inquiry.", ephemeral=True)
        return
    base_filename = f"log/ticket_{ticket_user_id}.txt"
    filename = base_filename
    counter = 1
    while os.path.exists(filename):
        filename = f"log/ticket_{ticket_user_id}_{counter}.txt"
        counter += 1
    if os.path.exists(base_filename):
        os.rename(base_filename, filename)
        try:
            await ticket_user.send(f"Your inquiry has been closed.")
        except Exception as e:
            await ctx.send(f"Unable to send a message to the user. Error: {str(e)}")
        await bot.get_channel(log_channel_id).send(file=disnake.File(filename))
        await ctx.send("The inquiry will be closed in 3 seconds.", ephemeral=True)
        await asyncio.sleep(3)
        await ctx.channel.delete()
    else:
        await ctx.send("Unable to find the log file for this ticket.", ephemeral=True)

@bot.slash_command(default_member_permissions=disnake.Permissions(administrator=True), guild_ids=[guild_id])
async def blacklist(ctx, user: disnake.User, reason: str = None, action: str = commands.Param(name="Action", choices=["Add", "Remove"])):
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("SELECT * FROM blacklist WHERE user_id == ?;", (user.id,))
    result = cur.fetchone()
    if result:
        if action == "Remove":
            cur.execute("DELETE FROM blacklist WHERE user_id == ?;", (user.id,))
            con.commit()
            if cur.rowcount > 0:
                await ctx.send(f"{user} has been removed from the blacklist.")
            else:
                await ctx.send(f"Failed to remove from the blacklist. Please try again.")
        else:
            await ctx.send(f"{user} is already on the blacklist.")
    else:
        if action == "Add":
            cur.execute("INSERT INTO blacklist (user_id) VALUES (?);", (user.id,))
            con.commit()
            if cur.rowcount > 0:
                await ctx.send(f"{user} has been added to the blacklist.")
                if reason:
                    await user.send(f"You have been added to the blacklist. Reason: {reason}")
                else:
                    await user.send(f"You have been added to the blacklist.")
            else:
                await ctx.send(f"Failed to add to the blacklist. Please try again.")
        else: 
            await ctx.send(f"{user} is not on the blacklist.")
    con.close()

@bot.slash_command(default_member_permissions=disnake.Permissions(administrator=True), guild_ids=[guild_id])
async def history(ctx, user: disnake.User):
    files = [f for f in os.listdir('log') if f.startswith(f'ticket_{user.id}')]
    if not files:
        await ctx.send(f"{user} has no inquiry history.")
        return
    class LogSelect(disnake.ui.Select):
        def __init__(self):
            options = [
                disnake.SelectOption(label=file, value=file) for file in files
            ]
            super().__init__(placeholder="Select a history...", options=options)

        async def callback(self, interaction: disnake.Interaction):
            await interaction.response.send_message(file=disnake.File(f"log/{self.values[0]}"), ephemeral=True)
    view = disnake.ui.View()
    view.add_item(LogSelect())
    await ctx.send(f"Select the inquiry history for {user}:", view=view)

@bot.slash_command(default_member_permissions=disnake.Permissions(administrator=True), guild_ids=[guild_id])
async def clean_dm(ctx, user: disnake.User):
    await ctx.response.defer()
    dm_channel = await user.create_dm()
    deleted_count = 0
    async for message in dm_channel.history(limit=1000):
        if message.author == bot.user:
            await message.delete()
            deleted_count += 1
    if deleted_count > 0:
        await ctx.send("Deleted all bot messages.", ephemeral=True)
    else:
        await ctx.edit_original_response(content=f"No bot messages found for {user}.")

bot.run(bot_token)
