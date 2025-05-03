import time
import math
import logging

logger = logging.getLogger(__name__)

async def progress_bar(current, total, status_message, start_time, last_update_time):
    elapsed_time = time.time() - start_time
    percentage = (current / total) * 100
    progress = "▓" * int(percentage // 5) + "░" * (20 - int(percentage // 5))
    speed = current / elapsed_time / 1024 / 1024
    uploaded = current / 1024 / 1024
    total_size = total / 1024 / 1024

    if time.time() - last_update_time[0] < 2:
        return
    last_update_time[0] = time.time()

    text = (
        f"**📥Upload Progress 📥**\n\n"
        f"{progress}\n\n"
        f"**🚧 PC:** {percentage:.2f}%\n"
        f"**⚡️ Speed:** {speed:.2f} MB/s\n"
        f"**📶 Uploaded:** {uploaded:.2f} MB of {total_size:.2f} MB"
    )
    try:
        await status_message.edit(text)
    except Exception as e:
        logger.error(f"Error updating progress: {e}")