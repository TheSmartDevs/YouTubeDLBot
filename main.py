from utils import LOGGER
from app import app  
from dlxutils import setup_dl_handler
from sudo import setup_sudo_handlers

#Connect Modules
setup_dl_handler(app)
setup_sudo_handlers(app)

LOGGER.info("Bot Successfully Started! 💥")
app.run()