import asyncio
import importlib.util
import sys
from pathlib import Path

import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

from helpers.logger import LOGGER
from bot import SmartYTUtil, start_bot

HANDLER_DIRS = [
    Path(__file__).parent / "core",
    Path(__file__).parent / "modules",
]


def load_handlers():
    loaded_count = 0
    for directory in HANDLER_DIRS:
        if not directory.is_dir():
            LOGGER.warning(f"{directory.name}/ not found, skipping...")
            continue
        LOGGER.info(f"Loading handlers from {directory.name}/")
        for path in sorted(directory.glob("*.py")):
            if path.name == "__init__.py":
                continue
            module_name = f"{directory.name}.{path.stem}"
            if module_name in sys.modules:
                LOGGER.info(f"  Already loaded: {module_name}")
                continue
            try:
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None:
                    LOGGER.warning(f"Could not load spec for {module_name}")
                    continue
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                LOGGER.info(f"  Loaded: {module_name}")
                loaded_count += 1
            except Exception as e:
                LOGGER.exception(f"Failed to load {module_name}: {e}")
    LOGGER.info(f"Total handlers loaded: {loaded_count}")


async def run_bot():
    LOGGER.info("Starting bot initialization...")
    await start_bot()
    LOGGER.info("Loading handler modules...")
    load_handlers()
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
