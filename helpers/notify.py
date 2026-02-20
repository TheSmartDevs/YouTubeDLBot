import html
import traceback
from datetime import datetime
from typing import Optional, Union

from telethon.tl.types import Message
from telethon.tl.functions.channels import GetParticipantRequest

from bot import SmartYTUtil
from helpers.buttons import SmartButtons
from helpers.logger import LOGGER
from config import OWNER_ID, DEVELOPER_USER_ID, LOG_CHANNEL_ID, UPDATE_CHANNEL_URL

TRACEBACK_DATA = {}


async def check_channel_membership(user_id: int) -> tuple:
    try:
        if not LOG_CHANNEL_ID:
            return False, "LOG_CHANNEL_ID is not configured", None
        channel_id = LOG_CHANNEL_ID
        if isinstance(channel_id, str):
            if not channel_id.startswith('@'):
                try:
                    channel_id = int(channel_id)
                except (ValueError, TypeError):
                    return False, f"Invalid LOG_CHANNEL_ID format: {LOG_CHANNEL_ID}", None
        if isinstance(channel_id, int):
            if channel_id > 0:
                channel_id = -channel_id
            if not str(abs(channel_id)).startswith('100'):
                channel_id = int(f"-100{abs(channel_id)}")
        try:
            result = await SmartYTUtil(GetParticipantRequest(channel=channel_id, participant=user_id))
            if result:
                return True, "", channel_id
        except Exception:
            pass
        return False, f"User {user_id} is not a member of the channel", channel_id
    except Exception as e:
        return False, f"Failed to check membership: {str(e)}", None


async def Smart_Notify(command: str, error: Union[Exception, str], message: Optional[Message] = None) -> None:
    try:
        bot_info = await SmartYTUtil.get_me()
        is_member, error_msg, channel_id = await check_channel_membership(bot_info.id)
        if not is_member:
            LOGGER.error(error_msg)

        user_info = {'id': "N/A", 'mention': "Unknown User", 'username': "N/A", 'full_name': "N/A"}
        chat_id_user = "N/A"
        if message and message.sender:
            user = message.sender
            first_name = getattr(user, 'first_name', '') or ''
            last_name = getattr(user, 'last_name', '') or ''
            full_name = f"{first_name} {last_name}".strip()
            full_name_escaped = html.escape(full_name) if full_name else "Unknown"
            username_display = f"@{user.username}" if getattr(user, 'username', None) else "N/A"
            user_info = {
                'id': user.id,
                'mention': f"<a href='tg://user?id={user.id}'>{full_name_escaped}</a>",
                'username': username_display,
                'full_name': full_name_escaped,
            }
            chat_id_user = getattr(message.chat, 'id', "N/A")

        if isinstance(error, str):
            error_type = "StringError"
            error_message = html.escape(error)
            traceback_text = "N/A"
            error_level = "WARNING"
        else:
            error_type = type(error).__name__
            error_message = html.escape(str(error))
            traceback_text = "".join(traceback.format_exception(type(error), error, error.__traceback__)) if error.__traceback__ else "N/A"
            error_level = "WARNING" if isinstance(error, (ValueError, UserWarning)) else "ERROR" if isinstance(error, RuntimeError) else "CRITICAL"

        command_escaped = html.escape(command)
        now = datetime.now()
        full_timestamp = now.strftime('%d-%m-%Y %H:%M:%S %p')
        formatted_date = now.strftime('%d-%m-%Y')
        formatted_time = now.strftime('%H:%M:%S')
        error_id = f"{int(now.timestamp() * 1000000)}"

        TRACEBACK_DATA[error_id] = {
            'error_type': error_type,
            'error_level': error_level,
            'traceback_text': traceback_text,
            'full_timestamp': full_timestamp,
            'command': command_escaped,
            'error_message': error_message,
            'user_info': user_info,
            'chat_id': chat_id_user,
            'formatted_date': formatted_date,
            'formatted_time': formatted_time,
        }

        error_report = (
            "<b>🚨 Smart Util ⚙️ New Bug Report</b>\n"
            "<b>━━━━━━━━━━━━━━━━</b>\n"
            f"<b>🧩 Command:</b> {command_escaped}\n"
            f"<b>👤 User:</b> {user_info['mention']}\n"
            f"<b>⚡️ User ID:</b> <code>{user_info['id']}</code>\n"
            f"<b>📍 Chat:</b> {chat_id_user}\n"
            f"<b>📅 Time:</b> {formatted_time}\n"
            f"<b>❗️ Error:</b> {error_type}\n"
            f"<b>📝 Message:</b> {error_message}\n"
            "<b>━━━━━━━━━━━━━━━━</b>\n"
            "<b>📂 Traceback:</b> Tap below to inspect"
        )

        buttons = SmartButtons()
        if user_info['id'] != "N/A":
            buttons.button(text="👤 View Profile", url=f"tg://user?id={user_info['id']}", position="header")
            buttons.button(text="🛠 Dev", url=f"tg://user?id={DEVELOPER_USER_ID}", position="header")
        buttons.button(text="📄 View Traceback", callback_data=f"viewtrcbc{error_id}$", position="footer")
        reply_markup = buttons.build_menu(b_cols=1, h_cols=2, f_cols=1)

        await SmartYTUtil.send_message(
            entity=OWNER_ID, message=error_report, parse_mode='html',
            buttons=reply_markup, link_preview=False,
            silent=(error_level == "WARNING"),
        )

        if is_member and channel_id:
            minimal_report = (
                "<b>🚨 Smart Util ⚙️ New Bug Report</b>\n"
                "<b>━━━━━━━━━━━━━━━━</b>\n"
                f"<b>🧩 Command:</b> {command_escaped}\n"
                f"<b>👤 User:</b> {user_info['mention']}\n"
                f"<b>⚡️ User ID:</b> <code>{user_info['id']}</code>\n"
                f"<b>📍 Chat:</b> {chat_id_user}\n"
                f"<b>📅 Time:</b> {formatted_time}\n"
                f"<b>❗️ Error:</b> {error_type}\n"
                f"<b>📝 Message:</b> {error_message}\n"
                "<b>━━━━━━━━━━━━━━━━</b>\n"
                "<b>📂 Traceback:</b> Tap below to inspect"
            )
            channel_buttons = SmartButtons()
            channel_buttons.button(text="Updates Channel", url=f"https://{UPDATE_CHANNEL_URL}")
            channel_reply_markup = channel_buttons.build_menu(b_cols=1)
            await SmartYTUtil.send_message(
                entity=channel_id, message=minimal_report, parse_mode='html',
                buttons=channel_reply_markup, link_preview=False,
                silent=(error_level == "WARNING"),
            )

        LOGGER.info(f"Admin notification sent for command: {command} with error_id: {error_id}")

    except Exception as e:
        LOGGER.error(f"Failed to send admin notification: {e}")
        LOGGER.error(traceback.format_exc())


async def handle_traceback_callback(event) -> None:
    try:
        error_id = event.data.decode().replace("viewtrcbc", "").replace("$", "")
        if error_id not in TRACEBACK_DATA:
            await event.answer("❌ Traceback data not found or expired!", show_alert=True)
            return

        data = TRACEBACK_DATA[error_id]
        traceback_text = data['traceback_text']
        if len(traceback_text) > 2000:
            traceback_text = traceback_text[:2000] + "\n... (truncated)"
        traceback_escaped = traceback_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        issue_escaped = data['error_message'][:200].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        traceback_message = (
            "<b>📄 Full Traceback — Smart Util ⚙️</b>\n"
            "<b>━━━━━━━━━━━━━━━━</b>\n"
            f"<b>🧩 Command:</b> {data['command']}\n"
            f"<b>⚠️ Error Type:</b> {data['error_type']}\n"
            f"<b>🧠 Summary:</b> {issue_escaped}\n"
            f"<b>📂 Traceback Dump:</b>\n"
            f"<blockquote expandable=True>{traceback_escaped}</blockquote>\n"
            "<b>━━━━━━━━━━━━━━━━</b>\n"
            "<b>🔙 Return:</b> Tap below to go back"
        )

        back_button = SmartButtons()
        back_button.button(text="🔙 Back To Main", callback_data=f"backtosummary{error_id}$")
        back_reply_markup = back_button.build_menu(b_cols=1)

        await event.edit(traceback_message, parse_mode='html', buttons=back_reply_markup, link_preview=False)
        await event.answer("Here Is The Full Traceback ✅")

    except Exception as e:
        LOGGER.error(f"Error in traceback callback: {e}")
        LOGGER.error(traceback.format_exc())
        try:
            await event.answer("Failed To Show Traceback ❌", alert=True)
        except Exception:
            pass


async def handle_back_callback(event) -> None:
    try:
        error_id = event.data.decode().replace("backtosummary", "").replace("$", "")
        if error_id not in TRACEBACK_DATA:
            await event.answer("Failed To Show Traceback ❌", alert=True)
            return

        data = TRACEBACK_DATA[error_id]
        error_report = (
            "<b>🚨 Smart Util ⚙️ New Bug Report</b>\n"
            "<b>━━━━━━━━━━━━━━━━</b>\n"
            f"<b>🧩 Command:</b> {data['command']}\n"
            f"<b>👤 User:</b> {data['user_info']['mention']}\n"
            f"<b>⚡️ User ID:</b> <code>{data['user_info']['id']}</code>\n"
            f"<b>📍 Chat:</b> {data['chat_id']}\n"
            f"<b>📅 Time:</b> {data['formatted_time']}\n"
            f"<b>❗️ Error:</b> {data['error_type']}\n"
            f"<b>📝 Message:</b> {data['error_message']}\n"
            "<b>━━━━━━━━━━━━━━━━</b>\n"
            "<b>📂 Traceback:</b> Tap below to inspect"
        )

        buttons = SmartButtons()
        if data['user_info']['id'] != "N/A":
            buttons.button(text="👤 View Profile", url=f"tg://user?id={data['user_info']['id']}", position="header")
            buttons.button(text="🛠 Dev", url=f"tg://user?id={DEVELOPER_USER_ID}", position="header")
        buttons.button(text="📄 View Traceback", callback_data=f"viewtrcbc{error_id}$", position="footer")
        reply_markup = buttons.build_menu(b_cols=1, h_cols=2, f_cols=1)

        await event.edit(error_report, parse_mode='html', buttons=reply_markup, link_preview=False)
        await event.answer("Summary Loaded Successful ✅!")

    except Exception as e:
        LOGGER.error(f"Error in back callback: {e}")
        LOGGER.error(traceback.format_exc())
        try:
            await event.answer("Error ❌ Loading Summary", alert=True)
        except Exception:
            pass
