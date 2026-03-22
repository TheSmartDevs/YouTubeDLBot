import asyncio
import re
import time

from telethon import events

import config
from bot import SmartYTUtil
from helpers import LOGGER, send_message, edit_message, SmartButtons
from helpers.ythelpers import generate_token, search_youtube_results

prefixes = ''.join(re.escape(p) for p in config.COMMAND_PREFIXES)
search_pattern = re.compile(rf'^[{prefixes}]search(?:\s+.+)?$', re.IGNORECASE)

RESULTS_PER_PAGE = 5
MAX_RESULTS = 50

pending_searches: dict = {}
SESSION_TTL = 15 * 60
MAX_PENDING_SEARCHES = 250
SEARCH_CLEANUP_INTERVAL = 60
_search_cleanup_task = None


async def fetch_all_results(query: str) -> list:
    try:
        return await search_youtube_results(query, limit=MAX_RESULTS)
    except Exception as e:
        LOGGER.error(f"Search fetch error: {e}")
        return []


def _prune_pending_searches():
    now = time.time()
    expired = [
        token for token, data in pending_searches.items()
        if now - float(data.get('created_at', now)) > SESSION_TTL
    ]
    for token in expired:
        pending_searches.pop(token, None)
    overflow = len(pending_searches) - MAX_PENDING_SEARCHES
    if overflow > 0:
        for token, _ in sorted(
            pending_searches.items(),
            key=lambda item: float(item[1].get('created_at', 0))
        )[:overflow]:
            pending_searches.pop(token, None)


async def _search_cleanup_loop():
    while True:
        _prune_pending_searches()
        await asyncio.sleep(SEARCH_CLEANUP_INTERVAL)


def _ensure_search_cleanup():
    global _search_cleanup_task
    if _search_cleanup_task is None or _search_cleanup_task.done():
        _search_cleanup_task = asyncio.create_task(_search_cleanup_loop())


def _set_pending_search(token: str, data: dict):
    data['created_at'] = time.time()
    pending_searches[token] = data
    _prune_pending_searches()


def _get_pending_search(token: str):
    _prune_pending_searches()
    return pending_searches.get(token)


def get_page(all_results: list, page: int) -> tuple:
    start = (page - 1) * RESULTS_PER_PAGE
    end = start + RESULTS_PER_PAGE
    page_results = all_results[start:end]
    has_prev = page > 1
    has_next = end < len(all_results)
    total_pages = (len(all_results) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
    return page_results, has_prev, has_next, total_pages


def build_result_text(results: list, page: int, total_pages: int) -> str:
    lines = [
        "**🔍Smart YouTube Search Results...🎵**",
        "**━━━━━━━━━━━━━━━━━━━━━**",
    ]
    start_num = (page - 1) * RESULTS_PER_PAGE + 1
    for i, result in enumerate(results):
        num = start_num + i
        title = result.get('title', 'Unknown')
        channel_raw = result.get('channel', {})
        channel = channel_raw.get('name', 'Unknown') if isinstance(channel_raw, dict) else str(channel_raw)
        link = result.get('link', '#')
        video_id = result.get('id', '')
        thumb_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else '#'
        thumbnails = result.get('thumbnails', [])
        if thumbnails and isinstance(thumbnails, list):
            best = thumbnails[-1]
            if isinstance(best, dict) and best.get('url'):
                thumb_url = best['url']
        lines.append(
            f"\n**{num}. 🎵Title :** `{title}`\n"
            f"**📢 Channel:** `{channel}`\n"
            f"**🖼Thumbnail :** [Click Here]({thumb_url})\n"
            f"**🔗 Url :** [Watch On YouTube]({link})"
        )
    lines.append(f"\n**━━━━━━━━━━━━━━━━━━━━━**")
    lines.append(f"**Page {page}/{total_pages} • Click Below Buttons For Navigating Pages 📄**")
    return "\n".join(lines)


def build_nav_markup(token: str, page: int, has_prev: bool, has_next: bool):
    sb = SmartButtons()
    if has_prev:
        sb.button("◀️ Prev", callback_data=f"SR|{token}|{page - 1}")
    if has_next:
        sb.button("Next ▶️", callback_data=f"SR|{token}|{page + 1}")
    sb.button("❌ Close", callback_data=f"SX|{token}", position="footer")
    return sb.build_menu(b_cols=2, f_cols=1)


@SmartYTUtil.on(events.NewMessage(pattern=search_pattern))
async def search_command(event):
    if not event.is_private:
        await send_message(event.chat_id, "**❌ This command works only in private chat.**")
        return
    _ensure_search_cleanup()
    text = event.message.text.strip()
    query = re.sub(rf'^[{prefixes}]search\s*', '', text, flags=re.IGNORECASE).strip()

    if not query:
        await send_message(
            event.chat_id,
            "**Please Provide A Query After The Command**\n"
            "**Usage:** `/search <your query>`"
        )
        return

    sender = await event.get_sender()
    LOGGER.info(f"Search | User: {sender.id} | Query: {query}")

    status = await send_message(event.chat_id, "**🔍 Searching Your Query...**")
    if not status:
        return

    all_results = await fetch_all_results(query)

    if not all_results:
        await edit_message(event.chat_id, status.id, "**Sorry Failed To Search**")
        return

    token = generate_token(sender.id)
    _set_pending_search(token, {
        'query': query,
        'results': all_results,
        'user_id': sender.id,
        'chat_id': event.chat_id,
    })

    page_results, has_prev, has_next, total_pages = get_page(all_results, 1)
    result_text = build_result_text(page_results, 1, total_pages)
    markup = build_nav_markup(token, 1, has_prev, has_next)

    await edit_message(event.chat_id, status.id, result_text, buttons=markup, link_preview=False)


@SmartYTUtil.on(events.CallbackQuery(pattern=rb'^SR\|'))
async def search_nav_cb(event):
    _ensure_search_cleanup()
    raw = event.data.decode()
    parts = raw.split('|')
    if len(parts) != 3:
        return

    token = parts[1]
    try:
        page = int(parts[2])
    except ValueError:
        return

    data = _get_pending_search(token)
    if not data:
        await event.answer("❌ Session expired. Please search again.", alert=True)
        try:
            await event.edit("**❌ Session expired. Please search again.**", buttons=None)
        except Exception:
            pass
        return

    if data['user_id'] != event.sender_id:
        await event.answer("❌ This is not your search session.", alert=True)
        return

    all_results = data['results']
    page_results, has_prev, has_next, total_pages = get_page(all_results, page)

    if not page_results:
        await event.answer("❌ No results on this page.", alert=True)
        return

    await event.answer(f"📄 Page {page}/{total_pages}", alert=False)

    result_text = build_result_text(page_results, page, total_pages)
    markup = build_nav_markup(token, page, has_prev, has_next)

    try:
        await event.edit(result_text, buttons=markup, link_preview=False)
    except Exception as e:
        LOGGER.error(f"Search nav edit error: {e}")
        await event.answer("❌ Failed to load page.", alert=True)


@SmartYTUtil.on(events.CallbackQuery(pattern=rb'^SX\|'))
async def search_close_cb(event):
    _ensure_search_cleanup()
    raw = event.data.decode()
    parts = raw.split('|')
    if len(parts) != 2:
        return

    token = parts[1]
    data = _get_pending_search(token)

    if data and data['user_id'] != event.sender_id:
        await event.answer("❌ This is not your search session.", alert=True)
        return

    pending_searches.pop(token, None)

    try:
        await event.delete()
    except Exception:
        try:
            await event.edit("**🔍 Search closed.**", buttons=None)
        except Exception:
            pass

    await event.answer("✅ Closed", alert=False)
