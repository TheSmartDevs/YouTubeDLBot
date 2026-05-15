from telethon import TelegramClient
import config
from helpers.logger import LOGGER

SmartYTUtil = None

async def init_client():
    global SmartYTUtil
    LOGGER.info("Initializing Telethon Client...")
    SmartYTUtil = TelegramClient(
        session='smartytutil',
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        connection_retries=None,
        retry_delay=1,
    )
    LOGGER.info("Telethon Client Created Successfully!")
    return SmartYTUtil

async def start_bot():
    global SmartYTUtil
    if SmartYTUtil is None:
        await init_client()
    LOGGER.info("Starting Telethon Client From BOT_TOKEN")
    await SmartYTUtil.start(bot_token=config.BOT_TOKEN)
    LOGGER.info("Telethon Client Started Successfully!")
    return SmartYTUtil

def get_client():
    global SmartYTUtil
    if SmartYTUtil is None:
        raise RuntimeError("TelegramClient not initialized. Call start_bot() first.")
    return SmartYTUtil
