import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

def get_env_or_default(env_key, default, transform=lambda x: x):
    value = os.getenv(env_key)
    return transform(value) if value is not None else default

# Bot Configuration
API_ID = get_env_or_default("API_ID", 123456, int)  # Replace with your actual API ID
API_HASH = get_env_or_default("API_HASH", "your_api_hash_here")
BOT_TOKEN = get_env_or_default("BOT_TOKEN", "your_bot_token_here")
OWNER_IDS = get_env_or_default("OWNER_IDS", "123456789", lambda x: list(map(int, x.split(','))))
MONGO_URL = get_env_or_default("MONGO_URL", "mongodb://localhost:27017")
UPDATE_CHANNEL_URL = get_env_or_default("UPDATE_CHANNEL_URL", "https://t.me/your_channel")
DEVELOPER_USER_ID = get_env_or_default("DEVELOPER_USER_ID", 123456789, int)
START_MSG_PHOTO = get_env_or_default("START_MSG_PHOTO", "https://example.com/start.jpg")

# Command Prefixes
raw_prefixes = get_env_or_default("COMMAND_PREFIX", "!|.|#|,|/")
COMMAND_PREFIX = [prefix.strip() for prefix in raw_prefixes.split("|") if prefix.strip()]
print("Loaded COMMAND_PREFIX:", COMMAND_PREFIX)  # Helper Debug
if not COMMAND_PREFIX:
    raise ValueError("Sorry Bro, no command prefix found. Please fix it in your config or .env file.")

# YouTube cookies path
YT_COOKIES_PATH = get_env_or_default("YT_COOKIES_PATH", "./cookies/ItsSmartToolBot.txt")

# Maximum allowed video size in bytes (default: 2GB)
MAX_VIDEO_SIZE = get_env_or_default("MAX_VIDEO_SIZE", 2 * 1024 * 1024 * 1024, int)  # 2GB

# Video Quality Options
VIDEO_QUALITY_OPTIONS = {
    "1080p": {"label": "1080p (Full HD)", "height": 1080},
    "720p": {"label": "720p (HD)", "height": 720},
    "480p": {"label": "480p (SD)", "height": 480},
    "360p": {"label": "360p (Low)", "height": 360},
    "144p": {"label": "144p (Very Low)", "height": 144}
}

# Audio Quality Options
AUDIO_QUALITY_OPTIONS = {
    "256kbps": {"label": "256kbps (High)", "bitrate": "256"},
    "128kbps": {"label": "128kbps (Medium)", "bitrate": "128"}
}
