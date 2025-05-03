#Copyright @ISmartDevs
#Channel t.me/TheSmartDev
#RESTART PLUGINS METHOD FROM https://github.com/abirxdhackz/RestartModule
import shutil
import os
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_IDS, UPDATE_CHANNEL_URL, COMMAND_PREFIX

def setup_restart_handler(app: Client):
    @app.on_message(filters.command(["restart", "reboot", "reload"], prefixes=COMMAND_PREFIX) & (filters.private | filters.group))
    async def restart(client, message):
        if message.from_user.id not in OWNER_IDS:
            await client.send_message(
                chat_id=message.chat.id,
                text="<b>🚫 Hey Gay 🏳️‍🌈 This Is Not For You This Only For Males👱‍♂️</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("👨🏼‍💻 Developer", url=f"https://t.me/abirxdhackz"),  # Use URL instead of user_id
                            InlineKeyboardButton("🤖 Other Bots", url=UPDATE_CHANNEL_URL)
                        ],
                        [
                            InlineKeyboardButton("🔗 Source Code", url="https://github.com/abirxdhack/RestartModule"),
                            InlineKeyboardButton("🔔 Update News", url=UPDATE_CHANNEL_URL)
                        ]
                    ]
                )
            )
            return

        response = await client.send_message(
            chat_id=message.chat.id,
            text="<b>Restarting Your Bot Sir Please Wait...</b>",
            parse_mode=ParseMode.HTML
        )

        # Directories to be removed
        directories = ["downloads", "temp", "temp_media", "data", "repos"]
        for directory in directories:
            try:
                shutil.rmtree(directory)
            except FileNotFoundError:
                pass

        # Delete the botlogs.txt file if it exists
        if os.path.exists("botlog.txt"):
            os.remove("botlog.txt")

        # Delete session files (assuming session name is "SmartTools"; replace with actual session name or import from config if different)
        session_files = ["SmartTools.session-journal"]
        deleted = []
        not_deleted = []
        for file in session_files:
            try:
                os.remove(file)
                deleted.append(file)
            except FileNotFoundError:
                pass
            except Exception as e:
                not_deleted.append(file)
                print(f"Failed to delete {file}: {e}")

        # Construct status message for session file deletion
        status_parts = []
        if deleted:
            status_parts.append(f"Deleted: {', '.join(deleted)}")
        if not_deleted:
            status_parts.append(f"Failed to delete: {', '.join(not_deleted)}")
        status = "No session files to delete." if not status_parts else " ".join(status_parts)

        await asyncio.sleep(10)

        await client.edit_message_text(
            chat_id=message.chat.id,
            message_id=response.id,
            text=f"<b>Bot Successfully Restarted!</b>",
            parse_mode=ParseMode.HTML
        )
        os.system(f"kill -9 {os.getpid()} && bash start.sh")

    @app.on_message(filters.command(["stop", "kill", "off"], prefixes=COMMAND_PREFIX) & (filters.private | filters.group))
    async def stop(client, message):
        if message.from_user.id not in OWNER_IDS:
            await client.send_message(
                chat_id=message.chat.id,
                text="<b>🚫 Hey Gay 🏳️‍🌈 This Is Not For You This Only For Males👱‍♂️</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("👨🏼‍💻 Developer", url=f"https://t.me/abirxdhackz"),  # Use URL instead of user_id
                            InlineKeyboardButton("🤖 Other Bots", url=UPDATE_CHANNEL_URL)
                        ],
                        [
                            InlineKeyboardButton("🔗 Source Code", url="https://github.com/abirxdhack/RestartModule"),
                            InlineKeyboardButton("🔔 Update News", url=UPDATE_CHANNEL_URL)
                        ]
                    ]
                )
            )
            return

        await client.send_message(
            chat_id=message.chat.id,
            text="<b>Bot Off Successfully All Database Cleared</b>",
            parse_mode=ParseMode.HTML
        )
        os.system("pkill -f main.py")