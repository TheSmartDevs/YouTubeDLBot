import asyncio
import sys
from pathlib import Path

from helpers.logger import LOGGER
from bot import start_bot
from handler_loader import register_all_handlers

async def run_bot():
    LOGGER.info("Starting bot initialization...")
    SmartYTUtil = await start_bot()
    LOGGER.info("Registering event handlers...")
    await register_all_handlers(SmartYTUtil)
    me = await SmartYTUtil.get_me()
    LOGGER.info(f"Bot Successfully Started | @{me.username}")
    LOGGER.info("Bot is now running and listening for events...")
    await SmartYTUtil.run_until_disconnected()

async def main():
    LOGGER.info("=" * 60)
    LOGGER.info("  SmartYTUtil — Starting Up")
    LOGGER.info("=" * 60)
    await run_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        LOGGER.info("Bot stopped by user (KeyboardInterrupt)")
    except Exception as e:
        LOGGER.exception(f"Fatal error: {e}")
        sys.exit(1)
