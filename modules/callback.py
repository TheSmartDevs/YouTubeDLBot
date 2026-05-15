import re

from telethon import events

import config
from helpers import LOGGER, edit_message, SmartButtons
from helpers.notify import handle_traceback_callback, handle_back_callback


def build_back_markup():
    sb = SmartButtons()
    sb.button("◀️ Back", callback_data="back_to_start")
    return sb.build_menu(b_cols=1)


def build_start_markup():
    sb = SmartButtons()
    sb.button("⚙ Main Menu", callback_data="main_menu", position="header")
    sb.button("ℹ️ About Me", callback_data="about")
    sb.button("📄 Policy & Terms", callback_data="policy")
    return sb.build_menu(b_cols=2, h_cols=1)


async def callback_handler(event):
    data = event.data

    if data == b"about":
        text = (
            "**ℹ️ About SmartYTUtil**\n"
            "**━━━━━━━━━━━━━━━━━**\n"
            "**Name:** SmartYTUtil ⚙️\n"
            "**Version:** v1.0 (Beta) 🛠\n\n"
            "**Development Team:**\n"
            "• Creator: [Abir Arafat Chawdhury 🇧🇩](https://t.me/ISmartCoder)\n\n"
            "**Technical Stack:**\n"
            "• Language: Python 🐍\n"
            "• Libraries: Telethon, yt-dlp 📚\n"
            "• Downloader: yt-dlp 🎬\n\n"
            "**About:** A powerful YouTube utility bot for Telegram — download, convert, search & more!"
        )
        await event.edit(text, link_preview=False, buttons=build_back_markup())

    elif data == b"policy":
        text = (
            "**📜 Privacy Policy for SmartYTUtil**\n\n"
            "Welcome to **SmartYTUtil** Bot. By using our services, you agree to this privacy policy.\n\n"
            "**1. Information We Collect:**\n"
            "   • **Personal Information:** User ID and username for personalization.\n"
            "   • **Usage Data:** Information on how you use the bot to improve our services.\n\n"
            "**2. Usage of Information:**\n"
            "   • **Service Enhancement:** To provide and improve **SmartYTUtil.**\n"
            "   • **Communication:** Updates and new features.\n"
            "   • **Security:** To prevent unauthorized access.\n\n"
            "**3. Data Security:**\n"
            "   • This bot does not permanently store any media or personal data.\n"
            "   • Temporary files are cleaned up after each task automatically.\n"
            "   • We use strong security measures, although no system is 100% secure.\n\n"
            "Thank you for using **SmartYTUtil**. We prioritize your privacy and security."
        )
        await event.edit(text, link_preview=False, buttons=build_back_markup())

    elif data == b"main_menu":
        text = (
            "**SmartYTUtil ⚙️ — Command List**\n\n"
            "**🔰 General Commands:**\n"
            "• /start — Show welcome message\n"
            "• /help  — Show all available commands\n\n"
            "**🎬 Download Commands:**\n"
            "• /dl    — Download a specific video only\n"
            "• /mp4   — Download a YouTube video\n"
            "• /yt    — Download a YouTube video\n"
            "• /video — Download a YouTube video\n"
            "• /mp3   — Download a song as audio\n"
            "• /aud   — Convert video to audio\n"
            "• /song  — Download a song as audio\n\n"
            "**🔍 Search & Info:**\n"
            "• /search — Search for audio or video\n"
            "• /info   — Get detailed info about a video\n"
            "• /thumb  — Download a video thumbnail\n\n"
            "**🍪 Cookie Management:**\n"
            "• /adc — Add cookies in Netscape format\n"
            "• /rmc — Remove cookies from host\n\n"
            "**📌 Note:** All commands work only in private chat."
        )
        await event.edit(text, link_preview=False, buttons=build_back_markup())

    elif data == b"back_to_start":
        sender = await event.get_sender()
        first_name = sender.first_name or ''
        last_name = sender.last_name or ''
        name = f"{first_name} {last_name}".strip() or "User"
        text = (
            f"**Hi {name}! Welcome To SmartYTUtil**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"**SmartYTUtil ⚙️** is your ultimate YouTube toolkit on Telegram — download videos, audio, thumbnails, search & more with ease!\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Don't forget to [join](https://{config.UPDATE_CHANNEL_URL}) for updates!"
        )
        await event.edit(text, link_preview=False, buttons=build_start_markup())


async def traceback_cb(event):
    await handle_traceback_callback(event)


async def back_summary_cb(event):
    await handle_back_callback(event)


def register_handlers(client):
    client.on(events.CallbackQuery(data=re.compile(rb'^(about|policy|main_menu|back_to_start)$')))(callback_handler)
    client.on(events.CallbackQuery(pattern=re.compile(rb'^viewtrcbc')))(traceback_cb)
    client.on(events.CallbackQuery(pattern=re.compile(rb'^backtosummary')))(back_summary_cb)
