import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

def get_env_or_default(env_key, default, transform=lambda x: x):
    value = os.getenv(env_key)
    return transform(value) if value is not None else default

# Bot Configuration
API_ID = get_env_or_default("API_ID", Your API_ID Here, int)
API_HASH = get_env_or_default("API_HASH", "Your API_HASH Here")
BOT_TOKEN = get_env_or_default("BOT_TOKEN", "Your BOT_TOKEN Here")
OWNER_IDS = get_env_or_default("OWNER_IDS", "Your OWNER_IDS Here", lambda x: list(map(int, x.split(','))))
MONGO_URL = get_env_or_default("MONGO_URL", "Your MONGO_URL Here")
UPDATE_CHANNEL_URL = get_env_or_default("UPDATE_CHANNEL_URL", "Your UPDATE_CHANNEL_URL Here")
DEVELOPER_USER_ID = get_env_or_default("DEVELOPER_USER_ID", Your DEVELOPER_USER_ID Here, int)
START_MSG_PHOTO = get_env_or_default("START_MSG_PHOTO", "Your START_MSG_PHOTO Here")

# Constants
raw_prefixes = get_env_or_default("COMMAND_PREFIX", "!|.|#|,|/")
COMMAND_PREFIX = [prefix.strip() for prefix in raw_prefixes.split("|") if prefix.strip()]
print("Loaded COMMAND_PREFIX:", COMMAND_PREFIX)  # JUST A KINDA HELPER FUNCTION
if not COMMAND_PREFIX:
    raise ValueError("Sorry Bro No Command Prefix Found First Fix It")
YT_COOKIES_PATH = get_env_or_default("YT_COOKIES_PATH", "./cookies/ItsSmartToolBot.txt")
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