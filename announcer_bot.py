# announcer_bot.py

import discord
import os
import sys

# --- LOAD ENVIRONMENT VARIABLES & VALIDATE ---

def get_env_variable(var_name):
    """A helper function to safely get environment variables."""
    value = os.getenv(var_name)
    if value is None:
        print(f"FATAL ERROR: Environment variable '{var_name}' not found.")
        print("Please set it in your system environment variables.")
        sys.exit(1)
    return value


# Load and validate all required variables at startup
BOT_TOKEN = get_env_variable("BOT_TOKEN")
try:
    REVIEWER_CHANNEL_ID = int(get_env_variable("REVIEWER_CHANNEL_ID"))
    ANNOUNCEMENT_CHANNEL_ID = int(get_env_variable("ANNOUNCEMENT_CHANNEL_ID"))
    REQUIRED_ROLE_ID = int(get_env_variable("REQUIRED_ROLE_ID"))
except ValueError:
    print("FATAL ERROR: A channel or role ID environment variable is not a valid number.")
    sys.exit(1)

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    """Runs when the bot logs in and is ready."""
    print(f'Bot is ready and logged in as {client.user}')
    print(f'Monitoring channel ID: {REVIEWER_CHANNEL_ID}')
    print(f'Announcing in channel ID: {ANNOUNCEMENT_CHANNEL_ID}')
    print(f'Required Role ID for trigger: {REQUIRED_ROLE_ID}')
    print('------')


@client.event
async def on_message(message):
    """Runs every time a message is sent in a server the bot is in."""

    # Guard 1: Ignore messages from bots (including itself).
    if message.author.bot:
        return

    # Guard 2: Only process messages in the designated "reviewer" channel.
    if message.channel.id != REVIEWER_CHANNEL_ID:
        return

    # Guard 3: Permission check - required role
    has_permission = any(role.id == REQUIRED_ROLE_ID for role in message.author.roles)
    if not has_permission:
        return

    # Guard 4: Only proceed if the message contains attachments.
    if not message.attachments:
        return

    pdf_attachments = [
        att for att in message.attachments if att.filename.lower().endswith('.pdf')
    ]

    if pdf_attachments:
        num_pdfs = len(pdf_attachments)
        print(f"Authorized user '{message.author.name}' triggered with {num_pdfs} PDF(s).")

        try:
            announcement_channel = client.get_channel(ANNOUNCEMENT_CHANNEL_ID)
            if not announcement_channel:
                print(f"Error: Could not find announcement channel with ID {ANNOUNCEMENT_CHANNEL_ID}")
                return

            original_content = message.content if message.content else "No additional text was provided."

            # --- EMBED CREATION ---
            embed = discord.Embed(color=discord.Color.blurple(), timestamp=message.created_at)
            embed.set_author(
                name=f"New Reviewer from {message.author.display_name}",
                icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url
            )
            quoted_message = "\n".join([f"> {line}" for line in original_content.splitlines()])
            embed.description = (
                f"A new document review has been posted in {message.channel.mention}.\n\n"
                f"**Original Message:**\n{quoted_message}"
            )
            file_list_str = "\n".join(f"📄 `{pdf.filename}`" for pdf in pdf_attachments)
            if len(file_list_str) > 1024:
                file_list_str = file_list_str[:1000] + "\n...and more."
            embed.add_field(
                name=f"Attached Document{'s' if num_pdfs > 1 else ''} ({num_pdfs})",
                value=file_list_str,
                inline=False
            )
            embed.add_field(
                name="➡️ Take Action",
                value=f"[**Click here to view the original post**]({message.jump_url})",
                inline=False
            )
            embed.set_footer(text=f"Sent via Review Announcer Bot")

            await announcement_channel.send(content="@everyone", embed=embed)
            print(f"Announcement sent successfully to #{announcement_channel.name}.")

        except discord.Forbidden:
            print(f"Error: Bot lacks permissions to send messages in channel ID {ANNOUNCEMENT_CHANNEL_ID}.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


# --- RUN THE BOT ---
client.run(BOT_TOKEN)
