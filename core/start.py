from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.enums import ParseMode, ChatType
import asyncio
from config import UPDATE_CHANNEL_URL, COMMAND_PREFIX, DEVELOPER_USER_ID, START_MSG_PHOTO

def setup_start_handler(app: Client):
    @app.on_message(filters.command(["start"], prefixes=COMMAND_PREFIX) & (filters.private | filters.group))
    async def start_message(client: Client, message: Message):
        chat_id = message.chat.id

        # Animation messages
        try:
            animation_message = await client.send_message(chat_id, "<b>Starting YouTube Downloader 📹...</b>", parse_mode=ParseMode.HTML)
            await asyncio.sleep(0.4)
            await client.edit_message_text(chat_id, animation_message.id, "<b>Initializing Download Engine...</b>", parse_mode=ParseMode.HTML)
            await asyncio.sleep(0.4)
            await client.delete_messages(chat_id, animation_message.id)
        except Exception:
            pass

        if message.chat.type == ChatType.PRIVATE:
            # Extract full name in private chat
            full_name = "User"
            if message.from_user:
                first_name = message.from_user.first_name or ""
                last_name = message.from_user.last_name or ""
                full_name = f"{first_name} {last_name}".strip()

            # Private Chat Message
            response_text = (
                f"<b>Hi {full_name}! Welcome to the YouTube Downloader Bot</b>\n"
                "<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                "<b>YouTube Downloader 📥</b>: Download videos and audio from YouTube with ease! Use /yt for videos or /song for music, select quality, and enjoy fast downloads.\n"
                "<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                "<b>Stay updated and contact my developer below!</b>"
            )
        elif message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            # Default to group name if user is anonymous admin
            group_name = message.chat.title if message.chat.title else "this group"

            # Check if user data is available (not anonymous admin)
            if message.from_user:
                first_name = message.from_user.first_name or ""
                last_name = message.from_user.last_name or ""
                full_name = f"{first_name} {last_name}".strip()

                # Personalized response for non-anonymous users
                response_text = (
                    f"<b>Hi {full_name}! Welcome to the YouTube Downloader Bot</b>\n"
                    "<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                    "<b>YouTube Downloader 📥</b>: Download videos and audio from YouTube with ease! Use /yt for videos or /song for music, select quality, and enjoy fast downloads.\n"
                    "<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                    "<b>Stay updated and contact my developer below!</b>"
                )
            else:
                # If user is an anonymous admin, use group name only
                response_text = (
                    f"<b>Hi {group_name}! Welcome to the YouTube Downloader Bot</b>\n"
                    "<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                    "<b>YouTube Downloader 📥</b>: Download videos and audio from YouTube with ease! Use /yt for videos or /song for music, select quality, and enjoy fast downloads.\n"
                    "<b>━━━━━━━━━━━━━━━━━━━━━━</b>\n"
                    "<b>Stay updated and contact my developer below!</b>"
                )

        # Define inline keyboard
        reply_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💥 Bot Updates 💥", url=UPDATE_CHANNEL_URL),
                InlineKeyboardButton("My Dev 💫", user_id=DEVELOPER_USER_ID)
            ]
        ])

        # Send photo with message and buttons as caption
        try:
            await client.send_photo(
                chat_id=message.chat.id,
                photo=START_MSG_PHOTO,
                caption=response_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
        except Exception:
            # Fallback to sending text message if photo fails
            await client.send_message(
                chat_id=message.chat.id,
                text=response_text + "\n\n<b>Note:</b> Could not load welcome image.",
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )

        # Stop propagation to prevent other handlers from processing
        message.stop_propagation()