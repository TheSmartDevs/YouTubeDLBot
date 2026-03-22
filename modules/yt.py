import asyncio
import os
import re
import time

from telethon import events
from telethon.tl.types import DocumentAttributeAudio, DocumentAttributeVideo

import config
from bot import SmartYTUtil
from helpers import LOGGER, send_message, edit_message, delete_messages, send_file, get_messages, progress_bar, clean_download
from helpers.ythelpers import (
    TEMP_DIR, MAX_FILE_SIZE, MAX_DURATION, executor,
    VIDEO_QUALITY_OPTIONS, AUDIO_QUALITY_OPTIONS,
    generate_token, youtube_parser, extract_video_id,
    fetch_thumbnail, fetch_metadata_from_url, search_youtube_metadata, search_youtube_url,
    extract_meta_fields, build_user_info, find_downloaded_file,
    _get_available_formats, _run_ydl,
    get_video_ydl_opts, get_audio_ydl_opts,
    resolve_video_qualities, resolve_audio_qualities,
    build_video_quality_markup, build_audio_quality_markup,
    format_views, format_dur, clean_temp_files,
    split_file_ffmpeg, compute_segment_duration,
)
from helpers.buttons import SmartButtons

prefixes = ''.join(re.escape(p) for p in config.COMMAND_PREFIXES)
yt_video_pattern = re.compile(rf'^[{prefixes}](yt|video|mp4|dl)(?:\s+.+)?$', re.IGNORECASE)
yt_audio_pattern = re.compile(rf'^[{prefixes}](mp3|song|aud)(?:\s+.+)?$', re.IGNORECASE)

pending_downloads: dict = {}


def _build_split_prompt_markup(token: str, yes_cb: str) -> object:
    sb = SmartButtons()
    sb.button("✅ Yes, Split It", callback_data=f"{yes_cb}|{token}")
    sb.button("❌ Cancel", callback_data=f"YX|{token}")
    return sb.build_menu(b_cols=2)


SPLIT_PROMPT_TEXT = (
    "**Bro File Size Exceeds 2 GB Limit❌**\n"
    "**Do You Want Spilted Downloader⬇️?**\n"
    "**Click Below Buttons For Navigation**"
)


async def do_split_upload_video(token: str):
    data = pending_downloads.get(token)
    if not data:
        return

    file_path = data.get('file_path')
    temp_id = data.get('temp_id')
    chat_id = data['chat_id']
    msg_id = data['msg_id']
    thumb_path = data.get('thumb_path')
    user_info = data.get('user_info', 'Unknown')
    title = data.get('split_title', 'Unknown')
    url = data['url']
    view_count = data.get('split_view_count', 0)
    duration = data.get('media_duration', 0)
    height = data.get('split_height', 720)

    await edit_message(
        chat_id, msg_id,
        f"**✂️ Splitting Video Into Parts...**\n"
        f"**Title:** `{title}`\n"
        f"**━━━━━━━━━━━━━━━━━━━━━**\n"
        f"**Please wait...**"
    )

    file_size = os.path.getsize(file_path)
    segment_dur = compute_segment_duration(file_size, duration)
    ext = os.path.splitext(file_path)[1] or '.mp4'
    split_dir = str(TEMP_DIR / temp_id / "splits")

    loop = asyncio.get_event_loop()
    try:
        parts = await loop.run_in_executor(executor, split_file_ffmpeg, file_path, split_dir, segment_dur, ext)
    except Exception as e:
        LOGGER.error(f"FFmpeg split failed: {e}")
        await edit_message(chat_id, msg_id, "**❌ Split Failed. Please try again.**")
        clean_temp_files(TEMP_DIR / temp_id)
        pending_downloads.pop(token, None)
        return

    total_parts = len(parts)
    LOGGER.info(f"Splitting video into {total_parts} parts for {title}")

    thumb_data = None
    if thumb_path and os.path.exists(thumb_path):
        with open(thumb_path, 'rb') as tf:
            thumb_data = tf.read()

    status_msg = await get_messages(chat_id, msg_id)

    for i, part_path in enumerate(parts, 1):
        start_time = time.time()
        last_update_time = [0]

        await edit_message(
            chat_id, msg_id,
            f"**📤 Uploading Part {i}/{total_parts}...**\n"
            f"**Title:** `{title}`\n"
            f"**━━━━━━━━━━━━━━━━━━━━━**\n"
            f"**Please wait...**"
        )

        part_caption = (
            f"🎬 **Title:** `{title}` — Part {i}/{total_parts}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👁️‍🗨️ **Views:** {format_views(view_count)}\n"
            f"**🔗 Url:** [Watch On YouTube]({url})\n"
            f"⏱️ **Part Duration:** {format_dur(segment_dur)} | **Total:** {format_dur(duration)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Downloaded By** {user_info}"
        )

        sent = await send_file(
            chat_id,
            file=part_path,
            caption=part_caption,
            parse_mode='markdown',
            thumb=thumb_data,
            attributes=[
                DocumentAttributeVideo(
                    duration=segment_dur,
                    w=1280,
                    h=height,
                    supports_streaming=True,
                )
            ],
            progress_callback=lambda c, t: asyncio.ensure_future(
                progress_bar(c, t, status_msg, start_time, last_update_time)
            ),
        )

        if not sent:
            await edit_message(chat_id, msg_id, f"**❌ Upload Failed on Part {i}. Please try again.**")
            clean_temp_files(TEMP_DIR / temp_id)
            if thumb_path:
                clean_download(thumb_path)
            pending_downloads.pop(token, None)
            return

    await delete_messages(chat_id, msg_id)
    LOGGER.info(f"Delivered split video ({total_parts} parts): {title} → {chat_id}")
    clean_temp_files(TEMP_DIR / temp_id)
    if thumb_path:
        clean_download(thumb_path)
    pending_downloads.pop(token, None)


async def do_split_upload_audio(token: str):
    data = pending_downloads.get(token)
    if not data:
        return

    file_path = data.get('file_path')
    temp_id = data.get('temp_id')
    chat_id = data['chat_id']
    msg_id = data['msg_id']
    thumb_path = data.get('thumb_path')
    user_info = data.get('user_info', 'Unknown')
    title = data.get('split_title', 'Unknown')
    channel = data.get('split_channel', 'Unknown')
    url = data['url']
    view_count = data.get('split_view_count', 0)
    duration = data.get('media_duration', 0)

    await edit_message(
        chat_id, msg_id,
        f"**✂️ Splitting Audio Into Parts...**\n"
        f"**Title:** `{title}`\n"
        f"**━━━━━━━━━━━━━━━━━━━━━**\n"
        f"**Please wait...**"
    )

    file_size = os.path.getsize(file_path)
    segment_dur = compute_segment_duration(file_size, duration)
    ext = os.path.splitext(file_path)[1] or '.mp3'
    split_dir = str(TEMP_DIR / temp_id / "splits")

    loop = asyncio.get_event_loop()
    try:
        parts = await loop.run_in_executor(executor, split_file_ffmpeg, file_path, split_dir, segment_dur, ext)
    except Exception as e:
        LOGGER.error(f"FFmpeg audio split failed: {e}")
        await edit_message(chat_id, msg_id, "**❌ Split Failed. Please try again.**")
        clean_temp_files(TEMP_DIR / temp_id)
        pending_downloads.pop(token, None)
        return

    total_parts = len(parts)
    LOGGER.info(f"Splitting audio into {total_parts} parts for {title}")

    thumb_data = None
    if thumb_path and os.path.exists(thumb_path):
        with open(thumb_path, 'rb') as tf:
            thumb_data = tf.read()

    status_msg = await get_messages(chat_id, msg_id)

    for i, part_path in enumerate(parts, 1):
        start_time = time.time()
        last_update_time = [0]

        await edit_message(
            chat_id, msg_id,
            f"**📤 Uploading Part {i}/{total_parts}...**\n"
            f"**Title:** `{title}`\n"
            f"**━━━━━━━━━━━━━━━━━━━━━**\n"
            f"**Please wait...**"
        )

        part_caption = (
            f"🎵 **Title:** `{title}` — Part {i}/{total_parts}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👁️‍🗨️ **Views:** {format_views(view_count)}\n"
            f"**🔗 Url:** [Listen On YouTube]({url})\n"
            f"⏱️ **Part Duration:** {format_dur(segment_dur)} | **Total:** {format_dur(duration)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Downloaded By** {user_info}"
        )

        sent = await send_file(
            chat_id,
            file=part_path,
            caption=part_caption,
            parse_mode='markdown',
            thumb=thumb_data,
            attributes=[
                DocumentAttributeAudio(
                    duration=segment_dur,
                    title=f"{title} (Part {i}/{total_parts})",
                    performer=channel,
                )
            ],
            progress_callback=lambda c, t: asyncio.ensure_future(
                progress_bar(c, t, status_msg, start_time, last_update_time)
            ),
        )

        if not sent:
            await edit_message(chat_id, msg_id, f"**❌ Upload Failed on Part {i}. Please try again.**")
            clean_temp_files(TEMP_DIR / temp_id)
            if thumb_path:
                clean_download(thumb_path)
            pending_downloads.pop(token, None)
            return

    await delete_messages(chat_id, msg_id)
    LOGGER.info(f"Delivered split audio ({total_parts} parts): {title} → {chat_id}")
    clean_temp_files(TEMP_DIR / temp_id)
    if thumb_path:
        clean_download(thumb_path)
    pending_downloads.pop(token, None)


async def do_video_download(token: str, quality_key: str):
    data = pending_downloads.get(token)
    if not data:
        return

    url = data['url']
    meta = data['meta']
    chat_id = data['chat_id']
    msg_id = data['msg_id']
    thumb_path = data.get('thumb_path')
    user_info = data.get('user_info', 'Unknown')
    do_split = data.get('split', False)

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
        LOGGER.error(f"Video download failed: {e}")
        await edit_message(chat_id, msg_id, "**❌ Download Failed. Please try again.**")
        clean_temp_files(TEMP_DIR / temp_id)
        pending_downloads.pop(token, None)
        return

    file_path = find_downloaded_file(temp_dir, ['.mp4', '.mkv', '.webm'])

    if not file_path:
        await edit_message(chat_id, msg_id, "**❌ File not found after download. Try again.**")
        clean_temp_files(TEMP_DIR / temp_id)
        pending_downloads.pop(token, None)
        return

    file_size = os.path.getsize(file_path)

    if do_split or file_size > MAX_FILE_SIZE:
        pending_downloads[token]['file_path'] = file_path
        pending_downloads[token]['temp_id'] = temp_id
        pending_downloads[token]['media_duration'] = duration
        pending_downloads[token]['split_title'] = title
        pending_downloads[token]['split_channel'] = channel
        pending_downloads[token]['split_view_count'] = view_count
        pending_downloads[token]['split_height'] = height

        if do_split:
            asyncio.create_task(do_split_upload_video(token))
            return

        await edit_message(
            chat_id, msg_id,
            SPLIT_PROMPT_TEXT,
            buttons=_build_split_prompt_markup(token, "YSPF")
        )
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

    LOGGER.info(f"Delivered {quality_key} video: {title} → {chat_id}")
    clean_temp_files(TEMP_DIR / temp_id)
    if thumb_path:
        clean_download(thumb_path)
    pending_downloads.pop(token, None)


async def do_audio_download(token: str, quality_key: str):
    data = pending_downloads.get(token)
    if not data:
        return

    url = data['url']
    meta = data['meta']
    chat_id = data['chat_id']
    msg_id = data['msg_id']
    thumb_path = data.get('thumb_path')
    user_info = data.get('user_info', 'Unknown')
    do_split = data.get('split', False)

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
        LOGGER.error(f"Audio download failed: {e}")
        await edit_message(chat_id, msg_id, "**❌ Download Failed. Please try again.**")
        clean_temp_files(TEMP_DIR / temp_id)
        pending_downloads.pop(token, None)
        return

    file_path = find_downloaded_file(temp_dir, ['.mp3', '.m4a', '.webm', '.ogg'])

    if not file_path:
        await edit_message(chat_id, msg_id, "**❌ File not found after download. Try again.**")
        clean_temp_files(TEMP_DIR / temp_id)
        pending_downloads.pop(token, None)
        return

    file_size = os.path.getsize(file_path)

    if do_split or file_size > MAX_FILE_SIZE:
        pending_downloads[token]['file_path'] = file_path
        pending_downloads[token]['temp_id'] = temp_id
        pending_downloads[token]['media_duration'] = duration
        pending_downloads[token]['split_title'] = title
        pending_downloads[token]['split_channel'] = channel
        pending_downloads[token]['split_view_count'] = view_count

        if do_split:
            asyncio.create_task(do_split_upload_audio(token))
            return

        await edit_message(
            chat_id, msg_id,
            SPLIT_PROMPT_TEXT,
            buttons=_build_split_prompt_markup(token, "YSPFA")
        )
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

    LOGGER.info(f"Delivered {quality_key} audio: {title} → {chat_id}")
    clean_temp_files(TEMP_DIR / temp_id)
    if thumb_path:
        clean_download(thumb_path)
    pending_downloads.pop(token, None)


async def handle_yt_command(event, query: str):
    chat_id = event.chat_id
    sender = await event.get_sender()
    user_info = build_user_info(event)

    status = await send_message(chat_id, "**🔍 Searching YouTube...**")
    if not status:
        return

    video_url = youtube_parser(query)
    if not video_url:
        await edit_message(chat_id, status.id, "**🔍 Processing query...**")
        video_url = await search_youtube_url(query)
        if not video_url:
            await edit_message(chat_id, status.id, "**❌ No results found. Try a different query.**")
            return

    await edit_message(chat_id, status.id, "**📡 Fetching Video Info...**")

    meta = await fetch_metadata_from_url(video_url)
    if not meta:
        meta = await search_youtube_metadata(query)
    if not meta:
        await edit_message(chat_id, status.id, "**❌ Could not fetch video info. Try again.**")
        return

    title, channel, duration, view_count, safe_title = extract_meta_fields(meta)
    video_id = extract_video_id(video_url)

    await edit_message(chat_id, status.id, "**📡 Fetching Available Qualities...**")
    loop = asyncio.get_event_loop()
    fmt_data = await loop.run_in_executor(executor, _get_available_formats, video_url)
    video_qualities = resolve_video_qualities(fmt_data['video_heights'])

    token = generate_token(sender.id)
    temp_dir = TEMP_DIR / token
    temp_dir.mkdir(exist_ok=True)
    thumb_out = str(temp_dir / "thumb.jpg")

    await edit_message(chat_id, status.id, "**🖼️ Fetching Available Thumbnail...**")
    thumb_path = await fetch_thumbnail(video_id, thumb_out)

    if duration > MAX_DURATION:
        pending_downloads[token] = {
            'url': video_url,
            'meta': meta,
            'user_id': sender.id,
            'user_info': user_info,
            'chat_id': chat_id,
            'msg_id': status.id,
            'thumb_path': thumb_path,
            'video_qualities': video_qualities,
            'split': True,
        }

        split_caption = (
            f"🎬 **Title:** `{title}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👁️‍🗨️ **Views:** {format_views(view_count)}\n"
            f"**🔗 Url:** [Watch On YouTube]({video_url})\n"
            f"⏱️ **Duration:** {format_dur(duration)}\n"
            f"👤 **Channel:** {channel}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Bro File Size Exceeds 2 GB Limit❌**\n"
            f"**Do You Want Spilted Downloader⬇️?**\n"
            f"**Click Below Buttons For Navigation**"
        )

        markup = _build_split_prompt_markup(token, "YSPV")

        if thumb_path and os.path.exists(thumb_path):
            await delete_messages(chat_id, status.id)
            sent = await SmartYTUtil.send_file(chat_id, file=thumb_path, caption=split_caption, buttons=markup)
            if sent:
                pending_downloads[token]['msg_id'] = sent.id
        else:
            await edit_message(chat_id, status.id, split_caption, buttons=markup, link_preview=False)
        return

    pending_downloads[token] = {
        'url': video_url,
        'meta': meta,
        'user_id': sender.id,
        'user_info': user_info,
        'chat_id': chat_id,
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
        f"**Select video quality to download:**"
    )

    markup = build_video_quality_markup(token, video_qualities, cb_prefix="YV")

    if thumb_path and os.path.exists(thumb_path):
        await delete_messages(chat_id, status.id)
        sent = await SmartYTUtil.send_file(chat_id, file=thumb_path, caption=caption, buttons=markup)
        if sent:
            pending_downloads[token]['msg_id'] = sent.id
    else:
        await edit_message(chat_id, status.id, caption, buttons=markup, link_preview=False)


async def handle_audio_command(event, query: str):
    chat_id = event.chat_id
    sender = await event.get_sender()
    user_info = build_user_info(event)

    status = await send_message(chat_id, "**🔍 Searching YouTube...**")
    if not status:
        return

    video_url = youtube_parser(query)
    if not video_url:
        await edit_message(chat_id, status.id, "**🔍 Processing query...**")
        video_url = await search_youtube_url(query)
        if not video_url:
            await edit_message(chat_id, status.id, "**❌ No results found. Try a different query.**")
            return

    await edit_message(chat_id, status.id, "**📡 Fetching Audio Info...**")

    meta = await fetch_metadata_from_url(video_url)
    if not meta:
        meta = await search_youtube_metadata(query)
    if not meta:
        await edit_message(chat_id, status.id, "**❌ Could not fetch audio info. Try again.**")
        return

    title, channel, duration, view_count, safe_title = extract_meta_fields(meta)
    video_id = extract_video_id(video_url)

    await edit_message(chat_id, status.id, "**📡 Fetching Available Audio Qualities...**")
    loop = asyncio.get_event_loop()
    fmt_data = await loop.run_in_executor(executor, _get_available_formats, video_url)
    audio_qualities = resolve_audio_qualities(fmt_data['audio_abrs'])

    token = generate_token(sender.id)
    temp_dir = TEMP_DIR / token
    temp_dir.mkdir(exist_ok=True)
    thumb_out = str(temp_dir / "thumb.jpg")

    await edit_message(chat_id, status.id, "**🖼️ Fetching Available Thumbnail...**")
    thumb_path = await fetch_thumbnail(video_id, thumb_out)

    if duration > MAX_DURATION:
        pending_downloads[token] = {
            'url': video_url,
            'meta': meta,
            'user_id': sender.id,
            'user_info': user_info,
            'chat_id': chat_id,
            'msg_id': status.id,
            'thumb_path': thumb_path,
            'audio_qualities': audio_qualities,
            'split': True,
        }

        split_caption = (
            f"🎵 **Title:** `{title}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"👁️‍🗨️ **Views:** {format_views(view_count)}\n"
            f"**🔗 Url:** [Listen On YouTube]({video_url})\n"
            f"⏱️ **Duration:** {format_dur(duration)}\n"
            f"👤 **Channel:** {channel}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Bro File Size Exceeds 2 GB Limit❌**\n"
            f"**Do You Want Spilted Downloader⬇️?**\n"
            f"**Click Below Buttons For Navigation**"
        )

        markup = _build_split_prompt_markup(token, "YSPA")

        if thumb_path and os.path.exists(thumb_path):
            await delete_messages(chat_id, status.id)
            sent = await SmartYTUtil.send_file(chat_id, file=thumb_path, caption=split_caption, buttons=markup)
            if sent:
                pending_downloads[token]['msg_id'] = sent.id
        else:
            await edit_message(chat_id, status.id, split_caption, buttons=markup, link_preview=False)
        return

    pending_downloads[token] = {
        'url': video_url,
        'meta': meta,
        'user_id': sender.id,
        'user_info': user_info,
        'chat_id': chat_id,
        'msg_id': status.id,
        'thumb_path': thumb_path,
    }

    caption = (
        f"🎵 **Title:** `{title}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👁️‍🗨️ **Views:** {format_views(view_count)}\n"
        f"**🔗 Url:** [Listen On YouTube]({video_url})\n"
        f"⏱️ **Duration:** {format_dur(duration)}\n"
        f"👤 **Channel:** {channel}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Select audio quality to download:**"
    )

    markup = build_audio_quality_markup(token, audio_qualities, cb_prefix="YA")

    if thumb_path and os.path.exists(thumb_path):
        await delete_messages(chat_id, status.id)
        sent = await SmartYTUtil.send_file(chat_id, file=thumb_path, caption=caption, buttons=markup)
        if sent:
            pending_downloads[token]['msg_id'] = sent.id
    else:
        await edit_message(chat_id, status.id, caption, buttons=markup, link_preview=False)


@SmartYTUtil.on(events.NewMessage(pattern=yt_video_pattern))
async def yt_video_command(event):
    text = event.message.text.strip()
    query = re.sub(rf'^[{prefixes}](yt|video|mp4|dl)\s*', '', text, flags=re.IGNORECASE).strip()

    if not query and event.message.reply_to:
        replied = await event.message.get_reply_message()
        if replied and replied.text:
            query = replied.text.strip()

    if not query:
        await send_message(
            event.chat_id,
            "**❌ Please provide a video name or URL.**\n"
            "**Usage:** `/yt <name or link>`"
        )
        return

    sender = await event.get_sender()
    LOGGER.info(f"YT video | User: {sender.id} | Query: {query}")
    await handle_yt_command(event, query)


@SmartYTUtil.on(events.NewMessage(pattern=yt_audio_pattern))
async def yt_audio_command(event):
    text = event.message.text.strip()
    query = re.sub(rf'^[{prefixes}](mp3|song|aud)\s*', '', text, flags=re.IGNORECASE).strip()

    if not query and event.message.reply_to:
        replied = await event.message.get_reply_message()
        if replied and replied.text:
            query = replied.text.strip()

    if not query:
        await send_message(
            event.chat_id,
            "**❌ Please provide a song name or URL.**\n"
            "**Usage:** `/mp3 <name or link>`"
        )
        return

    sender = await event.get_sender()
    LOGGER.info(f"YT audio | User: {sender.id} | Query: {query}")
    await handle_audio_command(event, query)


@SmartYTUtil.on(events.CallbackQuery(pattern=rb'^YV\|'))
async def yt_video_cb(event):
    raw = event.data.decode()
    parts = raw.split('|')
    if len(parts) != 3:
        return

    token = parts[1]
    quality_key = parts[2]

    if quality_key not in VIDEO_QUALITY_OPTIONS:
        await event.answer("❌ Invalid quality.", alert=True)
        return

    data = pending_downloads.get(token)
    if not data:
        await event.answer("❌ Session expired. Please search again.", alert=True)
        try:
            await event.edit("**❌ Session expired. Please search again.**", buttons=None)
        except Exception:
            pass
        return

    if data['user_id'] != event.sender_id:
        await event.answer("❌ This is not your download session.", alert=True)
        return

    await event.answer("⬇️ Download Has Started", alert=True)
    try:
        await event.edit(f"**⬇️ Starting {quality_key} Download...**", buttons=None)
    except Exception:
        pass

    asyncio.create_task(do_video_download(token, quality_key))


@SmartYTUtil.on(events.CallbackQuery(pattern=rb'^YA\|'))
async def yt_audio_cb(event):
    raw = event.data.decode()
    parts = raw.split('|')
    if len(parts) != 3:
        return

    token = parts[1]
    quality_key = parts[2]

    if quality_key not in AUDIO_QUALITY_OPTIONS:
        await event.answer("❌ Invalid quality.", alert=True)
        return

    data = pending_downloads.get(token)
    if not data:
        await event.answer("❌ Session expired. Please search again.", alert=True)
        try:
            await event.edit("**❌ Session expired. Please search again.**", buttons=None)
        except Exception:
            pass
        return

    if data['user_id'] != event.sender_id:
        await event.answer("❌ This is not your download session.", alert=True)
        return

    await event.answer("⬇️ Download Has Started", alert=True)
    try:
        await event.edit(f"**🎵 Starting {quality_key} Download...**", buttons=None)
    except Exception:
        pass

    asyncio.create_task(do_audio_download(token, quality_key))


@SmartYTUtil.on(events.CallbackQuery(pattern=rb'^YSPV\|'))
async def yt_split_yes_video_cb(event):
    raw = event.data.decode()
    parts = raw.split('|')
    if len(parts) != 2:
        return

    token = parts[1]
    data = pending_downloads.get(token)

    if not data:
        await event.answer("❌ Session expired. Please search again.", alert=True)
        try:
            await event.edit("**❌ Session expired. Please search again.**", buttons=None)
        except Exception:
            pass
        return

    if data['user_id'] != event.sender_id:
        await event.answer("❌ This is not your session.", alert=True)
        return

    video_qualities = data.get('video_qualities', list(VIDEO_QUALITY_OPTIONS.keys()))
    title, channel, duration, view_count, safe_title = extract_meta_fields(data['meta'])
    url = data['url']

    caption = (
        f"🎬 **Title:** `{title}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👁️‍🗨️ **Views:** {format_views(view_count)}\n"
        f"**🔗 Url:** [Watch On YouTube]({url})\n"
        f"⏱️ **Duration:** {format_dur(duration)}\n"
        f"👤 **Channel:** {channel}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Select video quality to download:**"
    )

    markup = build_video_quality_markup(token, video_qualities, cb_prefix="YV")

    await event.answer("✅ Choose Quality To Start Split Download", alert=False)
    try:
        await event.edit(caption, buttons=markup)
    except Exception:
        pass


@SmartYTUtil.on(events.CallbackQuery(pattern=rb'^YSPA\|'))
async def yt_split_yes_audio_cb(event):
    raw = event.data.decode()
    parts = raw.split('|')
    if len(parts) != 2:
        return

    token = parts[1]
    data = pending_downloads.get(token)

    if not data:
        await event.answer("❌ Session expired. Please search again.", alert=True)
        try:
            await event.edit("**❌ Session expired. Please search again.**", buttons=None)
        except Exception:
            pass
        return

    if data['user_id'] != event.sender_id:
        await event.answer("❌ This is not your session.", alert=True)
        return

    audio_qualities = data.get('audio_qualities', list(AUDIO_QUALITY_OPTIONS.keys()))
    title, channel, duration, view_count, safe_title = extract_meta_fields(data['meta'])
    url = data['url']

    caption = (
        f"🎵 **Title:** `{title}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👁️‍🗨️ **Views:** {format_views(view_count)}\n"
        f"**🔗 Url:** [Listen On YouTube]({url})\n"
        f"⏱️ **Duration:** {format_dur(duration)}\n"
        f"👤 **Channel:** {channel}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Select audio quality to download:**"
    )

    markup = build_audio_quality_markup(token, audio_qualities, cb_prefix="YA")

    await event.answer("✅ Choose Quality To Start Split Download", alert=False)
    try:
        await event.edit(caption, buttons=markup)
    except Exception:
        pass


@SmartYTUtil.on(events.CallbackQuery(pattern=rb'^YSPF\|'))
async def yt_split_file_video_cb(event):
    raw = event.data.decode()
    parts = raw.split('|')
    if len(parts) != 2:
        return

    token = parts[1]
    data = pending_downloads.get(token)

    if not data:
        await event.answer("❌ Session expired.", alert=True)
        try:
            await event.edit("**❌ Session expired.**", buttons=None)
        except Exception:
            pass
        return

    if data['user_id'] != event.sender_id:
        await event.answer("❌ This is not your session.", alert=True)
        return

    await event.answer("✅ Starting Split Upload...", alert=False)
    try:
        await event.edit("**✂️ Starting Split Upload...**", buttons=None)
    except Exception:
        pass

    asyncio.create_task(do_split_upload_video(token))


@SmartYTUtil.on(events.CallbackQuery(pattern=rb'^YSPFA\|'))
async def yt_split_file_audio_cb(event):
    raw = event.data.decode()
    parts = raw.split('|')
    if len(parts) != 2:
        return

    token = parts[1]
    data = pending_downloads.get(token)

    if not data:
        await event.answer("❌ Session expired.", alert=True)
        try:
            await event.edit("**❌ Session expired.**", buttons=None)
        except Exception:
            pass
        return

    if data['user_id'] != event.sender_id:
        await event.answer("❌ This is not your session.", alert=True)
        return

    await event.answer("✅ Starting Split Upload...", alert=False)
    try:
        await event.edit("**✂️ Starting Split Upload...**", buttons=None)
    except Exception:
        pass

    asyncio.create_task(do_split_upload_audio(token))


@SmartYTUtil.on(events.CallbackQuery(pattern=rb'^YX\|'))
async def yt_cancel_cb(event):
    raw = event.data.decode()
    parts = raw.split('|')
    if len(parts) != 2:
        return

    token = parts[1]
    data = pending_downloads.get(token)

    if data and data['user_id'] != event.sender_id:
        await event.answer("❌ This is not your session.", alert=True)
        return

    if data:
        thumb_path = data.get('thumb_path')
        if thumb_path:
            clean_download(thumb_path)
        temp_id = data.get('temp_id')
        if temp_id:
            clean_temp_files(TEMP_DIR / temp_id)
        clean_temp_files(TEMP_DIR / token)

    pending_downloads.pop(token, None)

    try:
        await event.edit("**Cancelled ❌ download process...**", buttons=None)
    except Exception:
        pass

    await event.answer("✅ Cancelled", alert=False)