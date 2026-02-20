import asyncio
import io
import os
import re

import aiohttp
from PIL import Image
from telethon import events

import config
from bot import SmartYTUtil
from helpers import LOGGER, SmartButtons, send_message, edit_message, delete_messages, clean_download
from helpers.ythelpers import (
    TEMP_DIR, HEADERS, executor,
    generate_token, youtube_parser, extract_video_id,
    clean_temp_files,
)

prefixes = ''.join(re.escape(p) for p in config.COMMAND_PREFIXES)
thumb_pattern = re.compile(rf'^[{prefixes}]thumb(?:\s+.+)?$', re.IGNORECASE)

pending_thumb: dict = {}

THUMB_RESOLUTIONS = {
    "high": {
        "label": "💫 High Quality",
        "urls": [
            "https://i.ytimg.com/vi/{vid}/maxresdefault.jpg",
            "https://i.ytimg.com/vi/{vid}/sddefault.jpg",
        ],
        "size": (1280, 720),
        "jpeg_quality": 95,
    },
    "medium": {
        "label": "🗯️ Medium",
        "urls": [
            "https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
        ],
        "size": (480, 360),
        "jpeg_quality": 85,
    },
    "small": {
        "label": "🌸 Small",
        "urls": [
            "https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
            "https://i.ytimg.com/vi/{vid}/default.jpg",
        ],
        "size": (320, 180),
        "jpeg_quality": 75,
    },
}


def build_thumb_resolution_markup(token: str):
    sb = SmartButtons()
    sb.button("💫 High Quality", callback_data=f"TH|{token}|high")
    sb.button("🗯️ Medium", callback_data=f"TH|{token}|medium")
    sb.button("🌸 Small", callback_data=f"TH|{token}|small")
    sb.button("❌ Cancel", callback_data=f"THX|{token}", position="footer")
    return sb.build_menu(b_cols=2, f_cols=1)


def _process_thumb(raw_bytes: bytes, out_path: str, size: tuple, jpeg_quality: int):
    try:
        img = Image.open(io.BytesIO(raw_bytes)).convert('RGB')
        img = img.resize(size, Image.LANCZOS)
        img.save(out_path, 'JPEG', quality=jpeg_quality, optimize=True)
        return out_path
    except Exception as e:
        LOGGER.error(f"Thumb process error: {e}")
        return None


async def fetch_thumb_by_resolution(video_id: str, out_path: str, res_key: str):
    res = THUMB_RESOLUTIONS[res_key]
    urls = [u.format(vid=video_id) for u in res["urls"]]
    size = res["size"]
    jpeg_quality = res["jpeg_quality"]

    connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
    timeout = aiohttp.ClientTimeout(total=30, connect=10)

    try:
        async with aiohttp.ClientSession(connector=connector, timeout=timeout, headers=HEADERS) as session:
            for url in urls:
                try:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            raw = await resp.read()
                            loop = asyncio.get_event_loop()
                            result = await loop.run_in_executor(
                                executor,
                                lambda r=raw, p=out_path, s=size, q=jpeg_quality: _process_thumb(r, p, s, q)
                            )
                            if result and os.path.exists(result):
                                LOGGER.info(f"Thumb [{res_key}] saved: {result} ({os.path.getsize(result)} bytes)")
                                return result
                except Exception as e:
                    LOGGER.error(f"Thumb [{res_key}] fetch error from {url}: {e}")
    except Exception as e:
        LOGGER.error(f"Thumb session error: {e}")

    return None


@SmartYTUtil.on(events.NewMessage(pattern=thumb_pattern))
async def thumb_command(event):
    text = event.message.text.strip()
    query = re.sub(rf'^[{prefixes}]thumb\s*', '', text, flags=re.IGNORECASE).strip()

    if not query and event.message.reply_to:
        replied = await event.message.get_reply_message()
        if replied and replied.text:
            query = replied.text.strip()

    if not query:
        await send_message(
            event.chat_id,
            "**❌ Please provide a YouTube URL.**\n"
            "**Usage:** `/thumb <youtube url>`"
        )
        return

    video_url = youtube_parser(query)
    if not video_url:
        await send_message(event.chat_id, "**❌ Invalid YouTube URL. Please provide a valid link.**")
        return

    video_id = extract_video_id(video_url)
    if not video_id:
        await send_message(event.chat_id, "**❌ Could not extract video ID from URL.**")
        return

    sender = await event.get_sender()
    LOGGER.info(f"Thumb command | User: {sender.id} | Video ID: {video_id}")

    status = await send_message(event.chat_id, "**🖼️ Fetching Video Thumbnail...**")
    if not status:
        return

    token = generate_token(sender.id)

    pending_thumb[token] = {
        'video_id': video_id,
        'video_url': video_url,
        'user_id': sender.id,
        'chat_id': event.chat_id,
        'msg_id': status.id,
    }

    await edit_message(
        event.chat_id,
        status.id,
        "**Please Choose The Resolution From Below**",
        buttons=build_thumb_resolution_markup(token),
    )


@SmartYTUtil.on(events.CallbackQuery(pattern=rb'^TH\|'))
async def thumb_resolution_cb(event):
    raw = event.data.decode()
    parts = raw.split('|')
    if len(parts) != 3:
        return

    token = parts[1]
    res_key = parts[2]

    if res_key not in THUMB_RESOLUTIONS:
        await event.answer("❌ Invalid resolution.", alert=True)
        return

    data = pending_thumb.get(token)
    if not data:
        await event.answer("❌ Session expired. Please run /thumb again.", alert=True)
        try:
            await event.edit("**❌ Session expired. Please run /thumb again.**", buttons=None)
        except Exception:
            pass
        return

    if data['user_id'] != event.sender_id:
        await event.answer("❌ This is not your session.", alert=True)
        return

    res_label = THUMB_RESOLUTIONS[res_key]["label"]
    await event.answer(f"🖼️ Fetching {res_label}...", alert=False)

    try:
        await event.edit(f"**🖼️ Downloading {res_label} Thumbnail...**", buttons=None)
    except Exception:
        pass

    asyncio.create_task(do_thumb_download(token, res_key))


@SmartYTUtil.on(events.CallbackQuery(pattern=rb'^THX\|'))
async def thumb_cancel_cb(event):
    raw = event.data.decode()
    parts = raw.split('|')
    if len(parts) != 2:
        return

    token = parts[1]
    data = pending_thumb.get(token)

    if data and data['user_id'] != event.sender_id:
        await event.answer("❌ This is not your session.", alert=True)
        return

    pending_thumb.pop(token, None)

    try:
        await event.edit("**❌ Cancelled.**", buttons=None)
    except Exception:
        pass

    await event.answer("✅ Cancelled", alert=False)


async def do_thumb_download(token: str, res_key: str):
    data = pending_thumb.get(token)
    if not data:
        return

    video_id = data['video_id']
    video_url = data['video_url']
    chat_id = data['chat_id']
    msg_id = data['msg_id']

    res = THUMB_RESOLUTIONS[res_key]
    res_label = res["label"]

    temp_dir = TEMP_DIR / token
    temp_dir.mkdir(exist_ok=True)
    out_path = str(temp_dir / f"thumb_{res_key}.jpg")

    thumb_path = await fetch_thumb_by_resolution(video_id, out_path, res_key)

    if not thumb_path:
        await edit_message(chat_id, msg_id, "**❌ Failed to fetch thumbnail. Try again.**")
        pending_thumb.pop(token, None)
        return

    try:
        sent = await SmartYTUtil.send_file(
            chat_id,
            file=thumb_path,
            force_document=True,
            caption="**Here Is The Thumbnail Picture**.",
            parse_mode='markdown',
        )
        if sent:
            await delete_messages(chat_id, msg_id)
        else:
            await edit_message(chat_id, msg_id, "**❌ Failed to send thumbnail. Try again.**")
    except Exception as e:
        LOGGER.error(f"Thumb send error: {e}")
        await edit_message(chat_id, msg_id, "**❌ Failed to send thumbnail. Try again.**")

    LOGGER.info(f"Thumb [{res_key}] delivered for video {video_id} → {chat_id}")
    clean_download(thumb_path)
    clean_temp_files(TEMP_DIR / token)
    pending_thumb.pop(token, None)
