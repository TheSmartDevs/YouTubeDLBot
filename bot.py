from telethon import TelegramClient

import config
from helpers.logger import LOGGER

SmartYTUtil = TelegramClient(
    session='smartytutil',
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    connection_retries=None,
    retry_delay=1,
)


async def start_bot():
    LOGGER.info("Creating Telethon Client From BOT_TOKEN")
    await SmartYTUtil.start(bot_token=config.BOT_TOKEN)
    LOGGER.info("Telethon Client Created Successfully!")
