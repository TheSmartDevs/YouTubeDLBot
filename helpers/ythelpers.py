import asyncio
import hashlib
import io
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, List

import aiohttp
import yt_dlp
from PIL import Image

from config import VIDEO_QUALITY_OPTIONS, AUDIO_QUALITY_OPTIONS
from helpers.logger import LOGGER
from helpers.utils import clean_download, clean_temp_files
from helpers.buttons import SmartButtons

TEMP_DIR = Path("./downloads")
TEMP_DIR.mkdir(exist_ok=True)

YT_COOKIES_PATH = str(Path(__file__).resolve().parent.parent / "cookies" / "SmartYTUtil.txt")

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
MAX_DURATION = 10800
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

_DENO_BIN = os.path.expanduser("~/.deno/bin")
if _DENO_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _DENO_BIN + os.pathsep + os.environ.get("PATH", "")

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


def _ydl_search_info(query: str) -> Optional[dict]:
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'nocheckcertificate': True,
        'socket_timeout': SOCKET_TIMEOUT,
        'extract_flat': False,
        'noplaylist': True,
        'remote_components': 'ejs:github',
    }
    opts.update(get_cookies_opt())
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if info and info.get('entries'):
                entry = info['entries'][0]
                return {
                    'title': entry.get('title', 'Unknown'),
                    'channel': entry.get('uploader') or entry.get('channel', 'Unknown'),
                    'duration': entry.get('duration', 0),
                    'viewCount': entry.get('view_count', 0),
                    'link': entry.get('webpage_url') or entry.get('url', ''),
                    'id': entry.get('id', ''),
                }
    except Exception as e:
        LOGGER.error(f"yt-dlp search error: {e}")
    return None


async def search_youtube_metadata(query: str) -> Optional[dict]:
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _ydl_search_info, query)
    except Exception as e:
        LOGGER.error(f"search_youtube_metadata error: {e}")
    return None


async def search_youtube_url(query: str) -> Optional[str]:
    for attempt in range(2):
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(executor, _ydl_search_info, query)
            if info and info.get('link'):
                return info['link']
            simplified = re.sub(r'[^\w\s]', '', query).strip()
            if simplified and simplified != query:
                info2 = await loop.run_in_executor(executor, _ydl_search_info, simplified)
                if info2 and info2.get('link'):
                    return info2['link']
        except Exception as e:
            LOGGER.error(f"Search attempt {attempt + 1} error: {e}")
            if attempt < 1:
                await asyncio.sleep(1)
    return None


def _ydl_extract_url_info(video_url: str) -> Optional[dict]:
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'nocheckcertificate': True,
        'socket_timeout': SOCKET_TIMEOUT,
        'noplaylist': True,
        'remote_components': 'ejs:github',
    }
    opts.update(get_cookies_opt())
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            if not info:
                return None
            return {
                'title': info.get('title', 'Unknown'),
                'channel': info.get('uploader') or info.get('channel', 'Unknown'),
                'duration': info.get('duration', 0),
                'viewCount': info.get('view_count', 0),
                'link': info.get('webpage_url', video_url),
                'id': info.get('id', ''),
            }
    except Exception as e:
        LOGGER.error(f"yt-dlp URL extract error: {e}")
    return None


async def fetch_metadata_from_url(video_url: str) -> Optional[dict]:
    if not video_url:
        return None
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _ydl_extract_url_info, video_url)
    except Exception as e:
        LOGGER.error(f"fetch_metadata_from_url error: {e}")
    return None


def _get_available_formats(url: str) -> dict:
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'nocheckcertificate': True,
        'socket_timeout': SOCKET_TIMEOUT,
        'ignoreerrors': True,
        'ignore_no_formats_error': True,
        'extractor_args': {'youtube': {'skip': ['hls', 'dash']}},
        'remote_components': 'ejs:github',
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
                if not abr:
                    abr = f.get('tbr')
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
        'ignoreerrors': False,
        'ignore_no_formats_error': True,
        'remote_components': 'ejs:github',
        'format': (
            f'bestvideo[height<={height}][vcodec^=avc]+bestaudio[acodec^=mp4a]'
            f'/bestvideo[height<={height}][vcodec^=avc]+bestaudio'
            f'/bestvideo[height<={height}]+bestaudio'
            f'/bestvideo[height<={height}]'
            f'/best[height<={height}]'
            f'/bestvideo+bestaudio'
            f'/best'
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
        'ignoreerrors': False,
        'ignore_no_formats_error': True,
        'remote_components': 'ejs:github',
        'format': (
            'bestaudio[acodec^=mp4a]/bestaudio[ext=m4a]'
            '/bestaudio[ext=webm]/bestaudio/best'
        ),
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
    duration_raw = meta.get('duration', 0)
    duration = duration_raw if isinstance(duration_raw, int) else parse_duration_to_seconds(str(duration_raw))
    view_count_raw = meta.get('viewCount', 0)
    if isinstance(view_count_raw, int):
        view_count = view_count_raw
    elif isinstance(view_count_raw, dict):
        view_count = parse_view_count(view_count_raw.get('short', '0'))
    else:
        view_count = parse_view_count(str(view_count_raw))
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


def split_file_ffmpeg(file_path: str, output_dir: str, segment_duration: int, ext: str) -> List[str]:
    os.makedirs(output_dir, exist_ok=True)
    output_pattern = os.path.join(output_dir, f"part_%03d{ext}")
    cmd = [
        'ffmpeg', '-y', '-i', file_path,
        '-f', 'segment',
        '-segment_time', str(segment_duration),
        '-c', 'copy',
        '-reset_timestamps', '1',
        '-avoid_negative_ts', 'make_zero',
        output_pattern
    ]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg split failed: {result.stderr.decode()}")
    parts = sorted([
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.startswith('part_') and f.endswith(ext)
    ])
    return parts


def compute_segment_duration(file_size: int, duration: int) -> int:
    if duration <= 0:
        return MAX_DURATION
    bps = file_size / duration
    if bps <= 0:
        return MAX_DURATION
    max_secs_for_2gb = int((MAX_FILE_SIZE * 0.92) / bps)
    return max(60, min(MAX_DURATION, max_secs_for_2gb))