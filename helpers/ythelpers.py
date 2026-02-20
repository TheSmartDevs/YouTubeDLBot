import asyncio
import hashlib
import io
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import aiohttp
import yt_dlp
from PIL import Image
from py_yt import VideosSearch, Search

from config import VIDEO_QUALITY_OPTIONS, AUDIO_QUALITY_OPTIONS
from helpers.logger import LOGGER
from helpers.utils import clean_download, clean_temp_files
from helpers.buttons import SmartButtons

TEMP_DIR = Path("./downloads")
TEMP_DIR.mkdir(exist_ok=True)

YT_COOKIES_PATH = str(Path(__file__).resolve().parent.parent / "cookies" / "SmartYTUtil.txt")

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
MAX_DURATION = 7200
SOCKET_TIMEOUT = 60
RETRIES = 3
EXECUTOR_WORKERS = 8

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
}

executor = ThreadPoolExecutor(max_workers=EXECUTOR_WORKERS)

LOGGER.info(f"YT Cookies path: {YT_COOKIES_PATH}")
LOGGER.info(f"YT Cookies exists: {os.path.exists(YT_COOKIES_PATH)}")


def get_cookies_opt() -> dict:
    if os.path.exists(YT_COOKIES_PATH):
        return {'cookiefile': YT_COOKIES_PATH}
    LOGGER.warning(f"Cookies NOT found at {YT_COOKIES_PATH}")
    return {}


def generate_token(user_id: int = 0) -> str:
    raw = f"{time.time()}{os.getpid()}{user_id}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def sanitize_filename(title: str) -> str:
    title = re.sub(r'[<>:"/\\|?*]', '', title[:80])
    title = re.sub(r'\s+', '_', title.strip())
    return title or "media"


def parse_duration_to_seconds(duration_str: str) -> int:
    try:
        parts = str(duration_str).split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 1:
            return int(parts[0])
        return 0
    except Exception:
        return 0


def parse_view_count(view_text: str) -> int:
    try:
        v = str(view_text).replace(',', '').replace(' views', '').replace(' view', '').strip()
        if 'M' in v:
            return int(float(v.replace('M', '')) * 1_000_000)
        elif 'K' in v:
            return int(float(v.replace('K', '')) * 1_000)
        return int(v)
    except Exception:
        return 0


def format_views(n: int) -> str:
    return f"{n:,}"


def format_dur(seconds: int) -> str:
    hours, rem = divmod(int(seconds), 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def youtube_parser(url: str) -> Optional[str]:
    patterns = [
        r"(?:youtube\.com/shorts/)([^\"&?/ ]{11})(\?.*)?",
        r"(?:youtube\.com/(?:[^/]+/.+/|(?:v|e(?:mbed)?)|.*[?&]v=)|youtu\.be/)([^\"&?/ ]{11})",
        r"(?:youtube\.com/watch\?v=)([^\"&?/ ]{11})",
        r"(?:m\.youtube\.com/watch\?v=)([^\"&?/ ]{11})",
        r"(?:youtube\.com/embed/)([^\"&?/ ]{11})",
        r"(?:youtube\.com/v/)([^\"&?/ ]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            vid = match.group(1)
            if "shorts" in url.lower():
                return f"https://www.youtube.com/shorts/{vid}"
            return f"https://www.youtube.com/watch?v={vid}"
    return None


def extract_video_id(url: str) -> Optional[str]:
    for pat in [r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", r"youtu\.be\/([0-9A-Za-z_-]{11})"]:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return url if len(url) == 11 else None


def _save_thumb(raw_bytes: bytes, out_path: str) -> Optional[str]:
    try:
        img = Image.open(io.BytesIO(raw_bytes)).convert('RGB')
        img.thumbnail((320, 320), Image.LANCZOS)
        for quality in [85, 60, 40]:
            buf = io.BytesIO()
            img.save(buf, 'JPEG', quality=quality, optimize=True)
            if buf.tell() <= 20 * 1024:
                with open(out_path, 'wb') as f:
                    f.write(buf.getvalue())
                return out_path
        buf.seek(0)
        with open(out_path, 'wb') as f:
            f.write(buf.getvalue())
        return out_path
    except Exception as e:
        LOGGER.error(f"Thumb save error: {e}")
        return None


async def fetch_thumbnail(video_id: str, out_path: str) -> Optional[str]:
    if not video_id:
        return None
    urls = [
        f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
        f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
    ]
    try:
        connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout, headers=HEADERS) as session:
            for url in urls:
                try:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            raw = await resp.read()
                            loop = asyncio.get_event_loop()
                            result = await loop.run_in_executor(
                                executor, lambda r=raw, p=out_path: _save_thumb(r, p)
                            )
                            if result and os.path.exists(result):
                                LOGGER.info(f"Thumbnail saved: {result} ({os.path.getsize(result)} bytes)")
                                return result
                except Exception as e:
                    LOGGER.error(f"Thumb URL error: {e}")
    except Exception as e:
        LOGGER.error(f"Thumbnail session error: {e}")
    return None


async def search_youtube_metadata(query: str) -> Optional[dict]:
    try:
        src = VideosSearch(query, limit=1, language="en", region="US")
        data = await src.next()
        if data and data.get('result') and len(data['result']) > 0:
            return data['result'][0]
    except Exception as e:
        LOGGER.error(f"VideosSearch error: {e}")
    return None


async def search_youtube_url(query: str) -> Optional[str]:
    for attempt in range(2):
        try:
            src = Search(query, limit=1, language="en", region="US")
            data = await src.next()
            if data and data.get('result') and len(data['result']) > 0:
                result = data['result'][0]
                if result.get('type') == 'video':
                    return result.get('link')
            simplified = re.sub(r'[^\w\s]', '', query).strip()
            if simplified and simplified != query:
                src2 = Search(simplified, limit=1, language="en", region="US")
                data2 = await src2.next()
                if data2 and data2.get('result') and len(data2['result']) > 0:
                    r2 = data2['result'][0]
                    if r2.get('type') == 'video':
                        return r2.get('link')
        except Exception as e:
            LOGGER.error(f"Search attempt {attempt + 1} error: {e}")
            if attempt < 1:
                await asyncio.sleep(1)
    return None


async def fetch_metadata_from_url(video_url: str) -> Optional[dict]:
    video_id = extract_video_id(video_url)
    if not video_id:
        return None
    return await search_youtube_metadata(video_id)


def _get_available_formats(url: str) -> dict:
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'nocheckcertificate': True,
        'socket_timeout': SOCKET_TIMEOUT,
    }
    opts.update(get_cookies_opt())
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return {'video_heights': [], 'audio_abrs': []}
            formats = info.get('formats', [])
            video_heights = set()
            audio_abrs = set()
            for f in formats:
                h = f.get('height')
                vcodec = f.get('vcodec', 'none') or 'none'
                acodec = f.get('acodec', 'none') or 'none'
                if h and vcodec != 'none':
                    video_heights.add(int(h))
                abr = f.get('abr')
                if abr and acodec != 'none' and vcodec == 'none':
                    audio_abrs.add(int(abr))
            return {
                'video_heights': sorted(list(video_heights), reverse=True),
                'audio_abrs': sorted(list(audio_abrs), reverse=True),
            }
    except Exception as e:
        LOGGER.error(f"Formats fetch error: {e}")
        return {'video_heights': [], 'audio_abrs': []}


def _run_ydl(opts: dict, url: str):
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])


def get_video_ydl_opts(output_base: str, quality_key: str) -> dict:
    height = VIDEO_QUALITY_OPTIONS[quality_key]["height"]
    opts = {
        'outtmpl': output_base + '.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'nocheckcertificate': True,
        'socket_timeout': SOCKET_TIMEOUT,
        'retries': RETRIES,
        'concurrent_fragment_downloads': 5,
        'format': (
            f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]'
            f'/bestvideo[height<={height}]+bestaudio'
            f'/best[height<={height}]/best'
        ),
        'merge_output_format': 'mp4',
        'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}],
    }
    opts.update(get_cookies_opt())
    return opts


def get_audio_ydl_opts(output_base: str, quality_key: str) -> dict:
    bitrate = AUDIO_QUALITY_OPTIONS[quality_key]["bitrate"]
    opts = {
        'outtmpl': output_base + '.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'nocheckcertificate': True,
        'socket_timeout': SOCKET_TIMEOUT,
        'retries': RETRIES,
        'concurrent_fragment_downloads': 5,
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': bitrate,
        }],
    }
    opts.update(get_cookies_opt())
    return opts


def resolve_video_qualities(available_heights: list) -> list:
    if not available_heights:
        LOGGER.warning("No heights from yt-dlp, showing all quality options")
        return list(VIDEO_QUALITY_OPTIONS.keys())
    result = []
    for key, opt in VIDEO_QUALITY_OPTIONS.items():
        h = opt["height"]
        if any(ah >= int(h * 0.85) for ah in available_heights):
            result.append(key)
    return result if result else list(VIDEO_QUALITY_OPTIONS.keys())


def resolve_audio_qualities(available_abrs: list) -> list:
    return list(AUDIO_QUALITY_OPTIONS.keys())


def extract_meta_fields(meta: dict) -> tuple:
    title = meta.get('title', 'Unknown')
    channel_raw = meta.get('channel', {})
    channel = channel_raw.get('name', 'Unknown') if isinstance(channel_raw, dict) else str(channel_raw)
    duration = parse_duration_to_seconds(meta.get('duration', '0:00'))
    view_count_raw = meta.get('viewCount', {})
    view_count = parse_view_count(
        view_count_raw.get('short', '0') if isinstance(view_count_raw, dict) else str(view_count_raw)
    )
    safe_title = sanitize_filename(title)
    return title, channel, duration, view_count, safe_title


def build_user_info(event) -> str:
    try:
        if event.sender and hasattr(event.sender, 'first_name'):
            name = event.sender.first_name or ''
            if event.sender.last_name:
                name += f" {event.sender.last_name}"
            return f"[{name}](tg://user?id={event.sender_id})"
    except Exception:
        pass
    try:
        if hasattr(event, 'chat') and hasattr(event.chat, 'title'):
            username = getattr(event.chat, 'username', None) or 'this_group'
            return f"[{event.chat.title}](https://t.me/{username})"
    except Exception:
        pass
    return "Unknown"


def find_downloaded_file(temp_dir: Path, exts: list) -> Optional[str]:
    if not temp_dir.exists():
        return None
    for ext in exts:
        for f in temp_dir.iterdir():
            if f.suffix.lower() == ext:
                return str(f)
    return None


def build_video_quality_markup(token: str, qualities: list, cb_prefix: str = "YV"):
    sb = SmartButtons()
    for key in qualities:
        sb.button(f"{key} 📥", callback_data=f"{cb_prefix}|{token}|{key}")
    sb.button("❌ Cancel", callback_data=f"YX|{token}", position="footer")
    return sb.build_menu(b_cols=2, f_cols=1)


def build_audio_quality_markup(token: str, qualities: list, cb_prefix: str = "YA"):
    sb = SmartButtons()
    for key in qualities:
        sb.button(f"{key} 📥", callback_data=f"{cb_prefix}|{token}|{key}")
    sb.button("❌ Cancel", callback_data=f"YX|{token}", position="footer")
    return sb.build_menu(b_cols=2, f_cols=1)
