from utils import LOGGER
from app import app  
from dlxutils import setup_dl_handler
from sudo import setup_sudo_handlers
from core import setup_start_handler

#Connect Modules
setup_dl_handler(app)
setup_sudo_handlers(app)
setup_start_handler(app)

LOGGER.info("Bot Successfully Started! 💥")
app.run()
