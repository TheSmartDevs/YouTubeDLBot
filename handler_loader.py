import importlib
import sys
from pathlib import Path

from helpers.logger import LOGGER


async def register_all_handlers(client):
    LOGGER.info("Registering event handlers...")
    
    from core import start
    start.register_handlers(client)
    
    from modules import callback, ckies, help, info, search, thumb, yt
    callback.register_handlers(client)
    ckies.register_handlers(client)
    help.register_handlers(client)
    info.register_handlers(client)
    search.register_handlers(client)
    thumb.register_handlers(client)
    yt.register_handlers(client)
    
    LOGGER.info("All event handlers registered successfully!")
