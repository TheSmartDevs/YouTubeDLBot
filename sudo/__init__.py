#Copyright @ISmartDevs
#Channel t.me/TheSmartDev
#Connect All Sub Modules With __init__.py Method By @abirxdhackz And @ISmartDevs
from .broadcast.broadcast import setup_admin_handler
from .logs.logs import setup_logs_handler
from .restart.restart import setup_restart_handler
from .speedtest.speedtest import setup_speed_handler

def setup_sudo_handlers(app):
    setup_admin_handler(app)
    setup_logs_handler(app)
    setup_restart_handler(app)
    setup_speed_handler(app)