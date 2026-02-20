import asyncio
import os
import re
import time

from telethon import events
from telethon.tl.types import DocumentAttributeAudio, DocumentAttributeVideo

import config
from bot import SmartYTUtil
from helpers import (
    LOGGER, SmartButtons, send_message, edit_message, delete_messages,
    send_file, get_messages, progress_bar, clean_download,
)
from helpers.ythelpers import (
    TEMP_DIR, MAX_FILE_SIZE, executor,
    VIDEO_QUALITY_OPTIONS, AUDIO_QUALITY_OPTIONS,
    generate_token, youtube_parser, extract_video_id,
    fetch_thumbnail, fetch_metadata_from_url, search_youtube_metadata,
    extract_meta_fields, build_user_info, find_downloaded_file,
    _get_available_formats, _run_ydl,
    get_video_ydl_opts, get_audio_ydl_opts,
    resolve_video_qualities, resolve_audio_qualities,
    format_views, format_dur, clean_temp_files,
)

prefixes = ''.join(re.escape(p) for p in config.COMMAND_PREFIXES)
info_pattern = re.compile(rf'^[{prefixes}]info(?:\s+.+)?$', re.IGNORECASE)

pending_info: dict = {}


def build_info_action_markup(token: str, url: str):
    sb = SmartButtons()
    sb.button("▶️ Watch", url=url)
    sb.button("⬇️ Download", callback_data=f"IF|{token}|ask")
    return sb.build_menu(b_cols=2)


def build_info_filetype_markup(token: str):
    sb = SmartButtons()
    sb.button("▶️ Video (Mp4)", callback_data=f"IF|{token}|video")
    sb.button("🎵 Audio (Mp3)", callback_data=f"IF|{token}|audio")
    return sb.build_menu(b_cols=2)


def build_info_video_quality_markup(token: str, qualities: list):
    sb = SmartButtons()
    for key in qualities:
        sb.button(f"{key} 📥", callback_data=f"IFV|{token}|{key}")
    sb.button("❌ Cancel", callback_data=f"IFX|{token}", position="footer")
    return sb.build_menu(b_cols=2, f_cols=1)


def build_info_audio_quality_markup(token: str, qualities: list):
    sb = SmartButtons()
    for key in qualities:
        sb.button(f"{key} 📥", callback_data=f"IFA|{token}|{key}")
    sb.button("❌ Cancel", callback_data=f"IFX|{token}", position="footer")
    return sb.build_menu(b_cols=2, f_cols=1)


@SmartYTUtil.on(events.NewMessage(pattern=info_pattern))
async def info_command(event):
    text = event.message.text.strip()
    query = re.sub(rf'^[{prefixes}]info\s*', '', text, flags=re.IGNORECASE).strip()

    if not query and event.message.reply_to:
        replied = await event.message.get_reply_message()
        if replied and replied.text:
            query = replied.text.strip()

    if not query:
        await send_message(
            event.chat_id,
            "**❌ Please provide a YouTube URL.**\n"
            "**Usage:** `/info <youtube url>`"
        )
        return

    video_url = youtube_parser(query)
    if not video_url:
        await send_message(event.chat_id, "**❌ Invalid YouTube URL. Please provide a valid link.**")
        return

    sender = await event.get_sender()
    LOGGER.info(f"Info command | User: {sender.id} | URL: {video_url}")

    status = await send_message(event.chat_id, "**🔍 Getting The Video Metadata...**")
    if not status:
        return

    meta = await fetch_metadata_from_url(video_url)
    if not meta:
        meta = await search_youtube_metadata(query)
    if not meta:
        await edit_message(event.chat_id, status.id, "**❌ Could not fetch video info. Try again.**")
        return

    title, channel, duration, view_count, safe_title = extract_meta_fields(meta)
    video_id = extract_video_id(video_url)

    token = generate_token(sender.id)
    temp_dir = TEMP_DIR / token
    temp_dir.mkdir(exist_ok=True)
    thumb_out = str(temp_dir / "thumb.jpg")

    thumb_path = await fetch_thumbnail(video_id, thumb_out)

    pending_info[token] = {
        'url': video_url,
        'meta': meta,
        'user_id': sender.id,
        'user_info': build_user_info(event),
        'chat_id': event.chat_id,
        'msg_id': status.id,
        'thumb_path': thumb_path,
    }

    caption = (
        f"🎬 **Title:** `{title}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👁️‍🗨️ **Views:** {format_views(view_count)}\n"
        f"**🔗 Url:** [Watch On YouTube]({video_url})\n"
        f"⏱️ **Duration:** {format_dur(duration)}\n"
        f"👤 **Channel:** {channel}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"**What would you like to do?**"
    )

    markup = build_info_action_markup(token, video_url)

    if thumb_path and os.path.exists(thumb_path):
        await delete_messages(event.chat_id, status.id)
        sent = await SmartYTUtil.send_file(event.chat_id, file=thumb_path, caption=caption, buttons=markup)
        if sent:
            pending_info[token]['msg_id'] = sent.id
    else:
        await edit_message(event.chat_id, status.id, caption, buttons=markup, link_preview=False)


@SmartYTUtil.on(events.CallbackQuery(pattern=rb'^IF\|'))
async def info_filetype_cb(event):
    raw = event.data.decode()
    parts = raw.split('|')
    if len(parts) != 3:
        return

    token = parts[1]
    action = parts[2]

    data = pending_info.get(token)
    if not data:
        await event.answer("❌ Session expired. Please run /info again.", alert=True)
        try:
            await event.edit("**❌ Session expired. Please run /info again.**", buttons=None)
        except Exception:
            pass
        return

    if data['user_id'] != event.sender_id:
        await event.answer("❌ This is not your session.", alert=True)
        return

    if action == "ask":
        await event.answer()
        try:
            await event.edit("**Which File Type You Want?**", buttons=build_info_filetype_markup(token))
        except Exception:
            pass

    elif action == "video":
        await event.answer("📡 Fetching Available Qualities...", alert=False)
        loop = asyncio.get_event_loop()
        fmt_data = await loop.run_in_executor(executor, _get_available_formats, data['url'])
        video_qualities = resolve_video_qualities(fmt_data['video_heights'])
        try:
            await event.edit(
                "**📡 Select Video Quality To Download:**",
                buttons=build_info_video_quality_markup(token, video_qualities),
            )
        except Exception:
            pass

    elif action == "audio":
        await event.answer()
        audio_qualities = resolve_audio_qualities([])
        try:
            await event.edit(
                "**🎵 Select Audio Quality To Download:**",
                buttons=build_info_audio_quality_markup(token, audio_qualities),
            )
        except Exception:
            pass


@SmartYTUtil.on(events.CallbackQuery(pattern=rb'^IFV\|'))
async def info_video_quality_cb(event):
    raw = event.data.decode()
    parts = raw.split('|')
    if len(parts) != 3:
        return

    token = parts[1]
    quality_key = parts[2]

    if quality_key not in VIDEO_QUALITY_OPTIONS:
        await event.answer("❌ Invalid quality.", alert=True)
        return

    data = pending_info.get(token)
    if not data:
        await event.answer("❌ Session expired. Please run /info again.", alert=True)
        try:
            await event.edit("**❌ Session expired. Please run /info again.**", buttons=None)
        except Exception:
            pass
        return

    if data['user_id'] != event.sender_id:
        await event.answer("❌ This is not your session.", alert=True)
        return

    await event.answer("⬇️ Download Has Started", alert=True)
    try:
        await event.edit(f"**⬇️ Starting {quality_key} Download...**", buttons=None)
    except Exception:
        pass

    asyncio.create_task(do_info_video_download(token, quality_key))


@SmartYTUtil.on(events.CallbackQuery(pattern=rb'^IFA\|'))
async def info_audio_quality_cb(event):
    raw = event.data.decode()
    parts = raw.split('|')
    if len(parts) != 3:
        return

    token = parts[1]
    quality_key = parts[2]

    if quality_key not in AUDIO_QUALITY_OPTIONS:
        await event.answer("❌ Invalid quality.", alert=True)
        return

    data = pending_info.get(token)
    if not data:
        await event.answer("❌ Session expired. Please run /info again.", alert=True)
        try:
            await event.edit("**❌ Session expired. Please run /info again.**", buttons=None)
        except Exception:
            pass
        return

    if data['user_id'] != event.sender_id:
        await event.answer("❌ This is not your session.", alert=True)
        return

    await event.answer("⬇️ Download Has Started", alert=True)
    try:
        await event.edit(f"**🎵 Starting {quality_key} Download...**", buttons=None)
    except Exception:
        pass

    asyncio.create_task(do_info_audio_download(token, quality_key))


@SmartYTUtil.on(events.CallbackQuery(pattern=rb'^IFX\|'))
async def info_cancel_cb(event):
    raw = event.data.decode()
    parts = raw.split('|')
    if len(parts) != 2:
        return

    token = parts[1]
    data = pending_info.get(token)

    if data and data['user_id'] != event.sender_id:
        await event.answer("❌ This is not your session.", alert=True)
        return

    if data:
        thumb_path = data.get('thumb_path')
        if thumb_path:
            clean_download(thumb_path)
        clean_temp_files(TEMP_DIR / token)

    pending_info.pop(token, None)

    try:
        await event.edit("**❌ Cancelled.**", buttons=None)
    except Exception:
        pass

    await event.answer("✅ Cancelled", alert=False)


async def do_info_video_download(token: str, quality_key: str):
    data = pending_info.get(token)
    if not data:
        return

    url = data['url']
    meta = data['meta']
    chat_id = data['chat_id']
    msg_id = data['msg_id']
    thumb_path = data.get('thumb_path')
    user_info = data.get('user_info', 'Unknown')

    title, channel, duration, view_count, safe_title = extract_meta_fields(meta)
    height = VIDEO_QUALITY_OPTIONS[quality_key]["height"]

    temp_id = generate_token()
    temp_dir = TEMP_DIR / temp_id
    temp_dir.mkdir(exist_ok=True)
    output_base = str(temp_dir / "media")

    status_msg = await get_messages(chat_id, msg_id)

    await edit_message(
        chat_id, msg_id,
        f"**⬇️ Downloading {quality_key} Video...**\n"
        f"**Title:** `{title}`\n"
        f"**━━━━━━━━━━━━━━━━━━━━━**\n"
        f"**Please wait...**"
    )

    loop = asyncio.get_event_loop()
    opts = get_video_ydl_opts(output_base, quality_key)

    try:
        await loop.run_in_executor(executor, _run_ydl, opts, url)
    except Exception as e:
        LOGGER.error(f"Info video download failed: {e}")
        await edit_message(chat_id, msg_id, "**❌ Download Failed. Please try again.**")
        clean_temp_files(TEMP_DIR / temp_id)
        pending_info.pop(token, None)
        return

    file_path = find_downloaded_file(temp_dir, ['.mp4', '.mkv', '.webm'])

    if not file_path:
        await edit_message(chat_id, msg_id, "**❌ File not found after download. Try again.**")
        clean_temp_files(TEMP_DIR / temp_id)
        pending_info.pop(token, None)
        return

    if os.path.getsize(file_path) > MAX_FILE_SIZE:
        await edit_message(chat_id, msg_id, "**❌ File exceeds 2GB. Try a lower quality.**")
        clean_temp_files(TEMP_DIR / temp_id)
        pending_info.pop(token, None)
        return

    caption = (
        f"🎵 **Title:** `{title}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👁️‍🗨️ **Views:** {format_views(view_count)}\n"
        f"**🔗 Url:** [Watch On YouTube]({url})\n"
        f"⏱️ **Duration:** {format_dur(duration)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Downloaded By** {user_info}"
    )

    thumb_data = None
    if thumb_path and os.path.exists(thumb_path):
        with open(thumb_path, 'rb') as tf:
            thumb_data = tf.read()

    start_time = time.time()
    last_update_time = [0]

    sent = await send_file(
        chat_id,
        file=file_path,
        caption=caption,
        parse_mode='markdown',
        thumb=thumb_data,
        attributes=[
            DocumentAttributeVideo(
                duration=duration,
                w=1280,
                h=height,
                supports_streaming=True,
            )
        ],
        progress_callback=lambda c, t: asyncio.ensure_future(
            progress_bar(c, t, status_msg, start_time, last_update_time)
        ),
    )

    if sent:
        await delete_messages(chat_id, msg_id)
    else:
        await edit_message(chat_id, msg_id, "**❌ Upload Failed. Please try again.**")

    LOGGER.info(f"Info delivered {quality_key} video: {title} → {chat_id}")
    clean_temp_files(TEMP_DIR / temp_id)
    if thumb_path:
        clean_download(thumb_path)
    pending_info.pop(token, None)


async def do_info_audio_download(token: str, quality_key: str):
    data = pending_info.get(token)
    if not data:
        return

    url = data['url']
    meta = data['meta']
    chat_id = data['chat_id']
    msg_id = data['msg_id']
    thumb_path = data.get('thumb_path')
    user_info = data.get('user_info', 'Unknown')

    title, channel, duration, view_count, safe_title = extract_meta_fields(meta)

    temp_id = generate_token()
    temp_dir = TEMP_DIR / temp_id
    temp_dir.mkdir(exist_ok=True)
    output_base = str(temp_dir / "media")

    status_msg = await get_messages(chat_id, msg_id)

    await edit_message(
        chat_id, msg_id,
        f"**🎵 Downloading {quality_key} Audio...**\n"
        f"**Title:** `{title}`\n"
        f"**━━━━━━━━━━━━━━━━━━━━━**\n"
        f"**Please wait...**"
    )

    loop = asyncio.get_event_loop()
    opts = get_audio_ydl_opts(output_base, quality_key)

    try:
        await loop.run_in_executor(executor, _run_ydl, opts, url)
    except Exception as e:
        LOGGER.error(f"Info audio download failed: {e}")
        await edit_message(chat_id, msg_id, "**❌ Download Failed. Please try again.**")
        clean_temp_files(TEMP_DIR / temp_id)
        pending_info.pop(token, None)
        return

    file_path = find_downloaded_file(temp_dir, ['.mp3', '.m4a', '.webm', '.ogg'])

    if not file_path:
        await edit_message(chat_id, msg_id, "**❌ File not found after download. Try again.**")
        clean_temp_files(TEMP_DIR / temp_id)
        pending_info.pop(token, None)
        return

    if os.path.getsize(file_path) > MAX_FILE_SIZE:
        await edit_message(chat_id, msg_id, "**❌ File exceeds 2GB.**")
        clean_temp_files(TEMP_DIR / temp_id)
        pending_info.pop(token, None)
        return

    caption = (
        f"🎵 **Title:** `{title}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👁️‍🗨️ **Views:** {format_views(view_count)}\n"
        f"**🔗 Url:** [Listen On YouTube]({url})\n"
        f"⏱️ **Duration:** {format_dur(duration)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Downloaded By** {user_info}"
    )

    thumb_data = None
    if thumb_path and os.path.exists(thumb_path):
        with open(thumb_path, 'rb') as tf:
            thumb_data = tf.read()

    start_time = time.time()
    last_update_time = [0]

    sent = await send_file(
        chat_id,
        file=file_path,
        caption=caption,
        parse_mode='markdown',
        thumb=thumb_data,
        attributes=[
            DocumentAttributeAudio(
                duration=duration,
                title=title,
                performer=channel,
            )
        ],
        progress_callback=lambda c, t: asyncio.ensure_future(
            progress_bar(c, t, status_msg, start_time, last_update_time)
        ),
    )

    if sent:
        await delete_messages(chat_id, msg_id)
    else:
        await edit_message(chat_id, msg_id, "**❌ Upload Failed. Please try again.**")

    LOGGER.info(f"Info delivered {quality_key} audio: {title} → {chat_id}")
    clean_temp_files(TEMP_DIR / temp_id)
    if thumb_path:
        clean_download(thumb_path)
    pending_info.pop(token, None)
