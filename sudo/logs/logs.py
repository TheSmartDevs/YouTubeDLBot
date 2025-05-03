import os
import math
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
import logging
from config import OWNER_IDS, COMMAND_PREFIX

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_logs_handler(app: Client):
    logger.info("Setting up logs handler")

    @app.on_message(filters.command(["logs"], prefixes=COMMAND_PREFIX) & (filters.private | filters.group))
    async def logs_command(client, message):
        user_id = message.from_user.id
        logger.info(f"Logs command from user {user_id}")
        if user_id not in OWNER_IDS:
            logger.info("User not admin, sending restricted message")
            await client.send_message(
                chat_id=message.chat.id,
                text="**🚫 Hey Gay 🏳️‍🌈 This Is Not For You This Only For Males👱‍♂️**",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Send a loading message
        loading_message = await client.send_message(
            chat_id=message.chat.id,
            text="**Checking The Logs...💥**",
            parse_mode=ParseMode.MARKDOWN
        )

        # Wait for 2 seconds
        await asyncio.sleep(2)

        # Check if logs exist
        if not os.path.exists("botlog.txt"):
            await loading_message.edit_text(
                text="**📜 No logs available yet.**",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        logger.info("User is admin, sending log document")
        await client.send_document(
            chat_id=message.chat.id,
            document="botlog.txt",
            caption="""**✘ Hey Sir! Here Is Your Order ↯**
**✘━━━━━━━━━━━━━━━━━━━━━━━━━↯**
**✘ All Logs Database Succesfully Exported! ↯**
**↯ Access Granted Only to Authorized Admins ↯**
**✘━━━━━━━━━━━━━━━━━━━━━━━━━↯**
**🖱️ Select an Option Below to View Logs:**
**👁️‍🗨️ Logs Here Offer the Fastest and Clearest Access! ↯**
**✘━━━━━━━━━━━━━━━━━━━━━━━━━↯**
**✘Huge Respect For You My Master↯**""",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([ 
                [InlineKeyboardButton("❄️ Display Logs", callback_data="display_logs&0"), 
                 InlineKeyboardButton("🌐 Web Paste", callback_data="web_paste$")], 
                [InlineKeyboardButton("❌ Close", callback_data="close_doc$")] 
            ])
        )

        # Delete the temporary "Checking The Logs..." message
        await loading_message.delete()

    @app.on_callback_query(filters.regex(r"^(close_doc\$|close_logs\$|web_paste\$|display_logs&(\d+)|nextLogs&(\d+)|previousLogs&(\d+))$"))
    async def handle_callback(client: Client, query: CallbackQuery):
        user_id = query.from_user.id
        data = query.data
        logger.info(f"Callback query from user {user_id}, data: {data}")
        if user_id not in OWNER_IDS:
            logger.info("User not admin, sending callback answer")
            await query.answer(
                text="🚫 This is only for admins!",
                show_alert=True
            )
            return
        logger.info("User is admin, processing callback")
        if data == "close_doc$":
            await query.message.delete()
            await query.answer()
        elif data == "close_logs$":
            await query.message.delete()
            await query.answer()
        elif data == "web_paste$":
            await query.answer("Web Paste feature not implemented yet.")
        elif data.startswith("display_logs&"):
            page = int(data.split("&")[1])
            await send_logs_page(client, query.message.chat.id, page)
            await query.answer()
        elif data.startswith("nextLogs&") or data.startswith("previousLogs&"):
            page = int(data.split("&")[1])
            await edit_logs_page(client, query.message, page)
            await query.answer()

async def send_logs_page(client: Client, chat_id: int, page: int):
    logger.info(f"Sending logs page {page} to chat {chat_id}")
    if not os.path.exists("botlog.txt"):
        await client.send_message(
            chat_id=chat_id,
            text="**📜 No logs available yet.**",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    with open("botlog.txt", "r", encoding="utf-8") as f:
        logs = f.readlines()
    total_lines = len(logs)
    total_pages = math.ceil(total_lines / 28)
    page = max(0, min(page, total_pages - 1))
    start = page * 28
    end = start + 28
    page_lines = logs[start:end]
    text = "".join(page_lines) if page_lines else "No logs available."
    buttons = []
    if total_lines <= 28:
        buttons = [[InlineKeyboardButton("❌ Close", callback_data="close_logs$")]]
    elif page == 0:
        buttons = [
            [InlineKeyboardButton("➡️ Next", callback_data=f"nextLogs&{page+1}"),
             InlineKeyboardButton("❌ Close", callback_data="close_logs$")]
        ]
    elif page == total_pages - 1:
        buttons = [
            [InlineKeyboardButton("⬅️ Previous", callback_data=f"previousLogs&{page-1}"),
             InlineKeyboardButton("❌ Close", callback_data="close_logs$")]
        ]
    else:
        buttons = [
            [InlineKeyboardButton("⬅️ Previous", callback_data=f"previousLogs&{page-1}"),
             InlineKeyboardButton("➡️ Next", callback_data=f"nextLogs&{page+1}")],
            [InlineKeyboardButton("❌ Close", callback_data="close_logs$")]
        ]
    await client.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.DISABLED,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def edit_logs_page(client: Client, message, page: int):
    logger.info(f"Editing logs page to {page}")
    if not os.path.exists("botlog.txt"):
        await message.edit_text(
            text="**📜 No logs available yet.**",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    with open("botlog.txt", "r", encoding="utf-8") as f:
        logs = f.readlines()
    total_lines = len(logs)
    total_pages = math.ceil(total_lines / 28)
    page = max(0, min(page, total_pages - 1))
    start = page * 28
    end = start + 28
    page_lines = logs[start:end]
    text = "".join(page_lines) if page_lines else "No logs available."
    buttons = []
    if total_lines <= 28:
        buttons = [[InlineKeyboardButton("❌ Close", callback_data="close_logs$")]]
    elif page == 0:
        buttons = [
            [InlineKeyboardButton("➡️ Next", callback_data=f"nextLogs&{page+1}"),
             InlineKeyboardButton("❌ Close", callback_data="close_logs$")]
        ]
    elif page == total_pages - 1:
        buttons = [
            [InlineKeyboardButton("⬅️ Previous", callback_data=f"previousLogs&{page-1}"),
             InlineKeyboardButton("❌ Close", callback_data="close_logs$")]
        ]
    else:
        buttons = [
            [InlineKeyboardButton("⬅️ Previous", callback_data=f"previousLogs&{page-1}"),
             InlineKeyboardButton("➡️ Next", callback_data=f"nextLogs&{page+1}")],
            [InlineKeyboardButton("❌ Close", callback_data="close_logs$")]
        ]
    await message.edit_text(
        text=text,
        parse_mode=ParseMode.DISABLED,
        reply_markup=InlineKeyboardMarkup(buttons)
    )