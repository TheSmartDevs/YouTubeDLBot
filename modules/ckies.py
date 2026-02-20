import hashlib
import os
import re
import shutil
import time
from pathlib import Path

from telethon import events

import config
from bot import SmartYTUtil
from helpers import LOGGER, SmartButtons, send_message, edit_message

prefixes = ''.join(re.escape(p) for p in config.COMMAND_PREFIXES)
adc_pattern = re.compile(rf'^[{prefixes}]adc(?:\s+.+)?$', re.IGNORECASE)
rmc_pattern = re.compile(rf'^[{prefixes}]rmc(?:\s+.+)?$', re.IGNORECASE)

COOKIES_PATH = Path(__file__).resolve().parent.parent / "cookies" / "SmartYTUtil.txt"

pending_rmc: dict = {}


def is_valid_netscape_cookies(content: str) -> bool:
    lines = content.strip().splitlines()
    has_header = False
    has_valid_entry = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            if 'Netscape' in line or 'HTTP Cookie' in line:
                has_header = True
            continue
        parts = line.split('\t')
        if len(parts) >= 6:
            has_valid_entry = True
    return has_header or has_valid_entry


def build_rmc_markup(token: str):
    sb = SmartButtons()
    sb.button("❌ Cancel", callback_data=f"RMC|{token}|cancel")
    sb.button("Delete ⚙️", callback_data=f"RMC|{token}|delete")
    return sb.build_menu(b_cols=2)


@SmartYTUtil.on(events.NewMessage(pattern=adc_pattern))
async def adc_command(event):
    sender = await event.get_sender()
    if sender.id != config.OWNER_ID:
        return

    if not event.message.reply_to:
        await send_message(
            event.chat_id,
            "**❌ Please reply to a Netscape format cookies file.**\n"
            "**Usage:** Reply to a `.txt` cookies file with `/adc`"
        )
        return

    replied = await event.message.get_reply_message()

    if not replied or not replied.document:
        await send_message(event.chat_id, "**❌ Please reply to a valid cookies file document.**")
        return

    doc = replied.document
    file_name = ""
    if doc.attributes:
        for attr in doc.attributes:
            if hasattr(attr, 'file_name') and attr.file_name:
                file_name = attr.file_name
                break

    if not file_name.endswith('.txt'):
        await send_message(event.chat_id, "**❌ File must be a `.txt` Netscape format cookies file.**")
        return

    status = await send_message(event.chat_id, "**Changing Cookies With New...**")
    if not status:
        return

    temp_path = COOKIES_PATH.parent / "cookies_new_temp.txt"

    try:
        await SmartYTUtil.download_media(replied.document, file=str(temp_path))
    except Exception as e:
        LOGGER.error(f"Cookie download error: {e}")
        await edit_message(event.chat_id, status.id, "**Failed To Update Cookies As Not Valid**")
        return

    if not temp_path.exists():
        await edit_message(event.chat_id, status.id, "**Failed To Update Cookies As Not Valid**")
        return

    try:
        content = temp_path.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        LOGGER.error(f"Cookie read error: {e}")
        temp_path.unlink(missing_ok=True)
        await edit_message(event.chat_id, status.id, "**Failed To Update Cookies As Not Valid**")
        return

    if not is_valid_netscape_cookies(content):
        temp_path.unlink(missing_ok=True)
        await edit_message(event.chat_id, status.id, "**Failed To Update Cookies As Not Valid**")
        return

    try:
        if COOKIES_PATH.exists():
            COOKIES_PATH.unlink()
        shutil.move(str(temp_path), str(COOKIES_PATH))
        LOGGER.info(f"Cookies updated successfully by owner {sender.id}")
        await edit_message(event.chat_id, status.id, "**Successfully Changed The Cookies ✅**")
    except Exception as e:
        LOGGER.error(f"Cookie replace error: {e}")
        temp_path.unlink(missing_ok=True)
        await edit_message(event.chat_id, status.id, "**Failed To Update Cookies As Not Valid**")


@SmartYTUtil.on(events.NewMessage(pattern=rmc_pattern))
async def rmc_command(event):
    sender = await event.get_sender()
    if sender.id != config.OWNER_ID:
        return

    LOGGER.info(f"Remove cookies requested by owner {sender.id}")

    raw = f"{time.time()}{sender.id}"
    token = hashlib.md5(raw.encode()).hexdigest()[:12]

    pending_rmc[token] = {
        'user_id': sender.id,
        'chat_id': event.chat_id,
    }

    await send_message(
        event.chat_id,
        "**Do You Want To Cleanup Cookies?**",
        buttons=build_rmc_markup(token),
    )


@SmartYTUtil.on(events.CallbackQuery(pattern=rb'^RMC\|'))
async def rmc_callback(event):
    if event.sender_id != config.OWNER_ID:
        return

    raw = event.data.decode()
    parts = raw.split('|')
    if len(parts) != 3:
        return

    token = parts[1]
    action = parts[2]

    data = pending_rmc.get(token)
    if not data:
        await event.answer("❌ Session expired.", alert=True)
        try:
            await event.edit("**❌ Session expired.**", buttons=None)
        except Exception:
            pass
        return

    if action == "cancel":
        pending_rmc.pop(token, None)
        await event.answer("✅ Cancelled", alert=False)
        try:
            await event.edit("**❌ Cancelled.**", buttons=None)
        except Exception:
            pass

    elif action == "delete":
        try:
            if COOKIES_PATH.exists():
                COOKIES_PATH.unlink()
                LOGGER.info(f"Cookies deleted by owner {event.sender_id}")
                await event.edit("**Successfully Deleted Cookies ❌**", buttons=None)
            else:
                await event.edit("**No Cookies File Found To Delete.**", buttons=None)
            await event.answer("✅ Done", alert=False)
        except Exception as e:
            LOGGER.error(f"Cookie delete error: {e}")
            await event.answer("❌ Failed to delete cookies.", alert=True)
            try:
                await event.edit("**❌ Failed To Delete Cookies.**", buttons=None)
            except Exception:
                pass

        pending_rmc.pop(token, None)
