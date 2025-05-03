import os
import logging
import re
import io
import math
import time
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import Optional, Tuple
from pyrogram import Client, filters
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
from moviepy import VideoFileClip
import yt_dlp
from uuid import uuid4
from config import COMMAND_PREFIX, YT_COOKIES_PATH, MAX_VIDEO_SIZE, VIDEO_QUALITY_OPTIONS, AUDIO_QUALITY_OPTIONS
from utils import progress_bar

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
class Config:
    TEMP_DIR = Path("temp_media")
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }

Config.TEMP_DIR.mkdir(exist_ok=True)
executor = ThreadPoolExecutor(max_workers=6)

# Temporary storage for queries
QUERY_STORAGE = {}

async def create_quality_keyboard(query: str, is_audio: bool) -> InlineKeyboardMarkup:
    # Generate a short key for the query
    query_key = str(uuid4())[:8]  # Use first 8 characters of UUID
    QUERY_STORAGE[query_key] = query  # Store the full query
    
    quality_options = AUDIO_QUALITY_OPTIONS if is_audio else VIDEO_QUALITY_OPTIONS
    buttons = []
    row = []
    for quality in quality_options:
        row.append(
            InlineKeyboardButton(
                text=quality_options[quality]["label"],
                callback_data=f"quality_{quality}_{query_key}_{'audio' if is_audio else 'video'}"
            )
        )
        if len(row) == 2:  # Two buttons per row
            buttons.append(row)
            row = []
    if row:  # Append any remaining buttons
        buttons.append(row)
    
    return InlineKeyboardMarkup(buttons)

def sanitize_filename(title: str) -> str:
    title = re.sub(r'[<>:"/\\|?*]', '', title[:50]).replace(' ', '_')
    return f"{title}_{int(time.time())}"

def format_size(size_bytes: int) -> str:
    if not size_bytes:
        return "0B"
    units = ("B", "KB", "MB", "GB")
    i = int(math.log(size_bytes, 1024))
    return f"{round(size_bytes / (1024 ** i), 2)} {units[i]}"

def format_duration(seconds: int) -> str:
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

async def get_video_duration(video_path: str) -> float:
    try:
        clip = VideoFileClip(video_path)
        duration = clip.duration
        clip.close()
        return duration
    except Exception as e:
        logger.error(f"Duration error: {e}")
        return 0.0

def youtube_parser(url: str) -> Optional[str]:
    reg_exp = r"(?:youtube\.com/(?:[^/]+/.+/|(?:v|e(?:mbed)?)|.*[?&]v=)|youtu\.be/)([^\"&?/ ]{11})"
    match = re.search(reg_exp, url)
    if match:
        video_id = match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"
    return None

def get_ydl_opts(output_path: str, is_audio: bool = False, quality: str = "720p") -> dict:
    base = {
        'outtmpl': output_path + ('.%(ext)s' if is_audio else ''),
        'cookiefile': YT_COOKIES_PATH,
        'quiet': True,
        'noprogress': True,
        'nocheckcertificate': True,
    }
    if is_audio:
        bitrate = AUDIO_QUALITY_OPTIONS[quality]["bitrate"]
        base.update({
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': bitrate}]
        })
    else:
        height = VIDEO_QUALITY_OPTIONS[quality]["height"]
        base.update({
            'format': f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}]
        })
    return base

async def download_media(url: str, is_audio: bool, status: Message, quality: str) -> Tuple[Optional[dict], Optional[str]]:
    parsed_url = youtube_parser(url)
    if not parsed_url:
        await status.edit_text("**Invalid YouTube ID Or URL**")
        return None, "Invalid YouTube URL"
    
    try:
        with yt_dlp.YoutubeDL({'cookiefile': YT_COOKIES_PATH, 'quiet': True}) as ydl:
            info = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(executor, ydl.extract_info, parsed_url, False),
                timeout=30
            )
        
        if not info:
            await status.edit_text(f"**Sorry Bro {'Audio' if is_audio else 'Video'} Not Found**")
            return None, "No media info found"
        
        duration = info.get('duration', 0)
        if duration > 7200:
            await status.edit_text(f"**Sorry Bro {'Audio' if is_audio else 'Video'} Is Over 2hrs**")
            return None, "Media duration exceeds 2 hours"
        
        await status.edit_text("**Found ☑️ Downloading...**")
        
        title = info.get('title', 'Unknown')
        safe_title = sanitize_filename(title)
        output_path = f"{Config.TEMP_DIR}/{safe_title}"
        
        opts = get_ydl_opts(output_path, is_audio, quality)
        with yt_dlp.YoutubeDL(opts) as ydl:
            await asyncio.get_event_loop().run_in_executor(executor, ydl.download, [parsed_url])
        
        file_path = f"{output_path}.mp3" if is_audio else f"{output_path}.mp4"
        if not os.path.exists(file_path):
            await status.edit_text(f"**Sorry Bro {'Audio' if is_audio else 'Video'} Not Found**")
            return None, "Download failed"
        
        file_size = os.path.getsize(file_path)
        if file_size > MAX_VIDEO_SIZE:
            os.remove(file_path)
            await status.edit_text(f"**Sorry Bro {'Audio' if is_audio else 'Video'} Is Over 2GB**")
            return None, "File exceeds 2GB"
        
        thumbnail_path = await prepare_thumbnail(info.get('thumbnail'), output_path)
        duration = await get_video_duration(file_path) if not is_audio else info.get('duration', 0)
        
        metadata = {
            'file_path': file_path,
            'title': title,
            'views': info.get('view_count', 0),
            'duration': format_duration(int(duration)),
            'file_size': format_size(file_size),
            'thumbnail_path': thumbnail_path
        }
        logger.info(f"{'Audio' if is_audio else 'Video'} Metadata: {metadata}")
        
        return metadata, None
    except asyncio.TimeoutError:
        logger.error(f"Timeout fetching metadata for URL: {url}")
        await status.edit_text("**Sorry Bro YouTubeDL API Dead**")
        return None, "Metadata fetch timed out"
    except Exception as e:
        logger.error(f"Download error for URL {url}: {e}")
        await status.edit_text("**Sorry Bro YouTubeDL API Dead**")
        return None, f"Download failed: {str(e)}"

async def prepare_thumbnail(thumbnail_url: str, output_path: str) -> Optional[str]:
    if not thumbnail_url:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail_url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()
        
        thumbnail_path = f"{output_path}_thumb.jpg"
        with Image.open(io.BytesIO(data)) as img:
            img.convert('RGB').save(thumbnail_path, "JPEG", quality=85)
        return thumbnail_path
    except Exception as e:
        logger.error(f"Thumbnail error: {e}")
        return None

async def search_youtube(query: str, retries: int = 2) -> Optional[str]:
    opts = {
        'default_search': 'ytsearch1',
        'cookiefile': YT_COOKIES_PATH,
        'quiet': True,
        'simulate': True,
    }
    
    for attempt in range(retries):
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = await asyncio.get_event_loop().run_in_executor(executor, ydl.extract_info, query, False)
                if info.get('entries'):
                    return info['entries'][0]['webpage_url']
                
                simplified_query = re.sub(r'[^\w\s]', '', query).strip()
                if simplified_query != query:
                    info = await asyncio.get_event_loop().run_in_executor(executor, ydl.extract_info, simplified_query, False)
                    if info.get('entries'):
                        return info['entries'][0]['webpage_url']
        except Exception as e:
            logger.error(f"Search error (attempt {attempt + 1}) for query {query}: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(1)
    return None

async def handle_media_request(client: Client, message: Message, query: str, is_audio: bool, quality: str):
    status = await client.send_message(
        message.chat.id,
        f"**Thanks Bro! {(AUDIO_QUALITY_OPTIONS if is_audio else VIDEO_QUALITY_OPTIONS)[quality]['label']} Selected. Downloading...**",
        parse_mode=ParseMode.MARKDOWN
    )
    
    video_url = youtube_parser(query) if youtube_parser(query) else await search_youtube(query)
    if not video_url:
        await status.edit_text(f"**Sorry Bro {'Audio' if is_audio else 'Video'} Not Found**")
        return
    
    result, error = await download_media(video_url, is_audio, status, quality)
    if error:
        return
    
    user_info = (
        f"[{message.from_user.first_name}](tg://user?id={message.from_user.id})" if message.from_user else
        f"[{message.chat.title}](https://t.me/{message.chat.username or 'this group'})"
    )
    caption = (
        f"🎵 **Title:** `{result['title']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👁️‍🗨️ **Views:** {result['views']}\n"
        f"**🔗 Url:** [Watch On YouTube]({video_url})\n"
        f"⏱️ **Duration:** {result['duration']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Downloaded By** {user_info}"
    )
    
    last_update_time = [0]
    start_time = time.time()
    send_func = client.send_audio if is_audio else client.send_video
    kwargs = {
        'chat_id': message.chat.id,
        'caption': caption,
        'parse_mode': ParseMode.MARKDOWN,
        'thumb': result['thumbnail_path'],
        'progress': progress_bar,
        'progress_args': (status, start_time, last_update_time)
    }
    if is_audio:
        kwargs.update({'audio': result['file_path'], 'title': result['title'], 'performer': "Smart Tools ❄️"})
    else:
        kwargs.update({
            'video': result['file_path'],
            'supports_streaming': True,
            'height': VIDEO_QUALITY_OPTIONS[quality]["height"],
            'width': int(VIDEO_QUALITY_OPTIONS[quality]["height"] * 16 / 9),
            'duration': int(await get_video_duration(result['file_path']))
        })
    
    try:
        await send_func(**kwargs)
    except Exception as e:
        logger.error(f"Upload error: {e}")
        await status.edit_text("**Sorry Bro YouTubeDL API Dead**")
        return
    
    for path in (result['file_path'], result['thumbnail_path']):
        if path and os.path.exists(path):
            os.remove(path)
    await status.delete()

async def video_command(client: Client, message: Message):
    query = message.text.split(maxsplit=1)[1] if len(message.text.split(maxsplit=1)) > 1 else None
    if not query:
        await message.reply_text("**Please provide a video name or link ❌**", parse_mode=ParseMode.MARKDOWN)
        return
    
    status = await message.reply_text("**Please select video quality:**", parse_mode=ParseMode.MARKDOWN)
    await status.edit_text(
        "**Please select video quality:**",
        reply_markup=await create_quality_keyboard(query, is_audio=False),
        parse_mode=ParseMode.MARKDOWN
    )

async def song_command(client: Client, message: Message):
    query = message.text.split(maxsplit=1)[1] if len(message.text.split(maxsplit=1)) > 1 else None
    if not query:
        await message.reply_text("**Please provide a music name or link ❌**", parse_mode=ParseMode.MARKDOWN)
        return
    
    status = await message.reply_text("**Please select audio quality:**", parse_mode=ParseMode.MARKDOWN)
    await status.edit_text(
        "**Please select audio quality:**",
        reply_markup=await create_quality_keyboard(query, is_audio=True),
        parse_mode=ParseMode.MARKDOWN
    )

async def quality_callback(client: Client, callback_query: CallbackQuery):
    try:
        data = callback_query.data.split("_")
        quality, query_key, media_type = data[1], data[2], data[3]
        query = QUERY_STORAGE.pop(query_key, None)  # Retrieve and remove query
        if not query:
            await callback_query.message.edit_text("**Sorry YouTubeDL Not Found The Media**", parse_mode=ParseMode.MARKDOWN)
            await callback_query.answer("Query expired!")
            return
        
        is_audio = media_type == "audio"
        
        # Answer the callback query first to avoid QUERY_ID_INVALID
        await callback_query.answer(f"{(AUDIO_QUALITY_OPTIONS if is_audio else VIDEO_QUALITY_OPTIONS)[quality]['label']} selected!")
        
        await callback_query.message.delete()
        await handle_media_request(
            client,
            callback_query.message,
            query,
            is_audio,
            quality
        )
    except pyrogram.errors.exceptions.bad_request_400.QueryIdInvalid:
        logger.warning("Callback query ID invalid, likely already processed or expired")
        await callback_query.message.edit_text("**Sorry YouTubeDL API Dead**", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Callback error: {e}")
        await callback_query.message.edit_text("**Sorry YouTubeDL API Dead**", parse_mode=ParseMode.MARKDOWN)
        await callback_query.answer("An error occurred!")

def setup_dl_handler(app: Client):
    app.add_handler(MessageHandler(video_command, filters.command(["yt", "video"], prefixes=COMMAND_PREFIX)))
    app.add_handler(MessageHandler(song_command, filters.command(["song"], prefixes=COMMAND_PREFIX)))
    app.add_handler(CallbackQueryHandler(quality_callback, filters.regex(r"^quality_")))