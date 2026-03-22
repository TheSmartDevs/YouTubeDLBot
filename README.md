<div align="center">

<img src="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Logo_of_YouTube_%282015-2017%29.svg/1280px-Logo_of_YouTube_%282015-2017%29.svg.png" width="128" height="128"/>

# SmartYTUtil — YouTubeDLBot

**A high-performance YouTube downloader bot for Telegram, built with Telethon and yt-dlp.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Telethon](https://img.shields.io/badge/Telethon-Latest-blue)](https://github.com/LonamiWebs/Telethon)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-Latest-red)](https://github.com/yt-dlp/yt-dlp)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Channel](https://img.shields.io/badge/Updates-@abirxdhackz-blue?logo=telegram)](https://t.me/abirxdhackz)

</div>

---

## Features

- Download YouTube videos in **144p → 1080p** quality
- Download audio as **MP3** in **64kbps → 320kbps** quality
- **Parallel MTProto upload** via FastTelethon — up to 20x faster than default Telethon
- Auto-resolves YouTube JS challenges using **Deno + EJS** for age-restricted and signed URLs
- Thumbnail fetching and embedding in every upload
- Real-time progress bar with speed and percentage
- Cookie support (Netscape format) for authenticated downloads
- YouTube search by name or direct URL
- Video info and thumbnail-only commands
- FloodWait handling and automatic temp file cleanup

---

## Requirements

- Python 3.10+
- FFmpeg installed and on PATH
- [Deno](https://deno.land) installed (`~/.deno/bin/deno`)
- Telegram API credentials from [my.telegram.org](https://my.telegram.org)

Install Python dependencies:

```bash
pip install telethon yt-dlp aiohttp Pillow uvloop cryptg
```

Install Deno (required for YouTube JS challenge solving):

```bash
curl -fsSL https://deno.land/install.sh | sh
```

---

## Configuration

Edit `config.py`:

```python
API_ID    = 123456          # From my.telegram.org
API_HASH  = "your_api_hash"
BOT_TOKEN = "your_bot_token"

OWNER_ID           = 123456789
DEVELOPER_USER_ID  = 123456789
LOG_CHANNEL_ID     = -1001234567890
UPDATE_CHANNEL_URL = "t.me/yourchannel"
```

---

## Running

```bash
python3 main.py
```

---

## Commands

| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/help` | All available commands |
| `/yt`, `/video`, `/mp4`, `/dl` | Download YouTube video |
| `/mp3`, `/song`, `/aud` | Download YouTube audio |
| `/search` | Search YouTube |
| `/info` | Get video information |
| `/thumb` | Download video thumbnail |
| `/adc` | Add cookies (Netscape format) |
| `/rmc` | Remove cookies |

---

## Project Structure

```
YouTubeDLBot/
├── bot.py                   # Telethon client init
├── config.py                # API credentials and settings
├── main.py                  # Entry point, module loader
├── cookies/
│   └── SmartYTUtil.txt      # YouTube cookies (Netscape format)
├── core/
│   └── start.py             # /start and /help handlers
├── helpers/
│   ├── fast_telethon.py     # Parallel MTProto transfer engine
│   ├── botutils.py          # Telegram helper wrappers
│   ├── ythelpers.py         # yt-dlp download/search/format logic
│   ├── pgbar.py             # Progress bar
│   ├── buttons.py           # Inline keyboard builder
│   ├── notify.py            # Error reporting to owner
│   ├── logger.py            # Logging setup
│   └── utils.py             # File cleanup utilities
└── modules/
    ├── yt.py                # Video and audio download handlers
    ├── callback.py          # Inline button callbacks
    ├── search.py            # Search command
    ├── info.py              # Info command
    ├── thumb.py             # Thumbnail command
    └── ckies.py             # Cookie management
```

---

## Credits

- [Tulir Asokan](https://github.com/tulir) — parallel file transfer implementation
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — YouTube extraction engine
- **Creator:** [Abir Arafat Chawdhury](https://t.me/ISmartCoder)
- **Updates:** [t.me/abirxdhackz](https://t.me/abirxdhackz)

---

<div align="center">
Made with ❤️ by <a href="https://t.me/ISmartCoder">@ISmartCoder</a>
</div>