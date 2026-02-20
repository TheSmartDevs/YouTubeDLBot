import re

from telethon import events

import config
from bot import SmartYTUtil
from helpers import LOGGER, send_message, SmartButtons

prefixes = ''.join(re.escape(p) for p in config.COMMAND_PREFIXES)
help_pattern = re.compile(rf'^[{prefixes}](help|cmds)(?:\s+.+)?$', re.IGNORECASE)


def build_help_markup():
    sb = SmartButtons()
    sb.button("⚙ Main Menu", callback_data="main_menu", position="header")
    sb.button("ℹ️ About Me", callback_data="about")
    sb.button("📄 Policy & Terms", callback_data="policy")
    return sb.build_menu(b_cols=2, h_cols=1)


@SmartYTUtil.on(events.NewMessage(pattern=help_pattern))
async def help_handler(event):
    sender = await event.get_sender()
    first_name = sender.first_name or ''
    last_name = sender.last_name or ''
    name = f"{first_name} {last_name}".strip() or "User"
    LOGGER.info(f"Help command | User: {name} ({sender.id})")

    text = (
        f"**Hi {name}! Welcome To SmartYTUtil**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"**SmartYTUtil ⚙️** is your ultimate YouTube toolkit on Telegram — download videos, audio, thumbnails, search & more with ease!\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Don't forget to [join](https://{config.UPDATE_CHANNEL_URL}) for updates!"
    )

    await send_message(event.chat_id, text, link_preview=False, buttons=build_help_markup())
