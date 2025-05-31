
# 🌟 YouTubeDLBot ⭐️

[![GitHub Stars](https://img.shields.io/github/stars/TheSmartDevs/YouTubeDLBot?style=social)](https://github.com/TheSmartDevs/YouTubeDLBot/stargazers) 
[![GitHub Forks](https://img.shields.io/github/forks/TheSmartDevs/YouTubeDLBot?style=social)](https://github.com/TheSmartDevs/YouTubeDLBot/network) 
[![GitHub Issues](https://img.shields.io/github/issues/TheSmartDevs/YouTubeDLBot)](https://github.com/TheSmartDevs/YouTubeDLBot/issues) 
[![License](https://img.shields.io/github/license/TheSmartDevs/YouTubeDLBot)](https://github.com/TheSmartDevs/YouTubeDLBot/blob/main/LICENSE)

🌟 YouTubeDLBot is a powerful Telegram bot designed for downloading YouTube videos and audio with a smooth user experience. 💥 Built with stability and speed in mind, it leverages modern technologies like Pyrogram, aiohttp, and workers for efficient performance. ❄️ The bot supports video quality selection, high-quality audio downloads, and error handling for seamless YouTube content access. ✨

## 🌟 Features 📈

- ⭐️ **Video Quality Selection**: Choose from 1080p, 720p, 480p, 360p, or 144p using interactive buttons. 👀
- 💥 **Audio Quality Options**: Download audio with 256kbps or 128kbps bitrate for high-quality sound. ❄️
- 🌟 **Progress Bar**: Real-time progress bar for a smooth downloading experience. ✨
- 📈 **Message Editing**: Updates messages dynamically for a polished user interface. 💀
- ⭐️ **Pyrogram Stability**: Built with Pyrogram for reliable Telegram bot functionality. 👀
- 💥 **Asynchronous Requests**: Uses aiohttp for fast, non-blocking HTTP requests. ❄️
- 🌟 **Worker Clients**: Enhances download speed with multiple client workers. ✨
- 📈 **Error Handling with Cookies**: Manages YouTube download errors using a cookies file to bypass sign-in requirements. 💀

## 🌟 Bot Commands ⭐️

- `/start` - Start the bot 🌟
- `/yt` - Download a YouTube video 💥
- `/video` - Download a YouTube video ❄️
- `/song` - Download a YouTube song 📈
- `/stats` - View total bot users and groups 👀
- `/send` - Broadcast messages with premium emojis ✨
- `/broadcast` - Broadcast messages with normal emojis 💀
- `/logs` - Retrieve bot logs for error troubleshooting ⭐️
- `/restart` - Restart the bot 🌟
- `/speedtest` - Test your VPS speed 💥

## 🌟 Handling YouTube Download Errors with Cookies ❄️

💥 To avoid errors related to YouTube sign-in requirements, the bot uses a cookie file for seamless content access. Follow these steps to set it up: ✨

### ⭐️ Steps to Export and Use Cookies 👀

1. 🌟 **Create a Dedicated Chrome Profile**:
   - Create a new Chrome profile for managing your bot's cookies to keep things organized. ❄️
2. 💥 **Install a Cookie Management Extension**:
   - Use "Cookie Editor" or a similar extension to manage cookies. 📈
3. ⭐️ **Export Cookies from YouTube**:
   - Log into YouTube in your new browser profile. 💀
   - Use the cookie extension to export cookies in **Netscape format**. ✨
4. 🌟 **Save the Cookies File**:
   - Save the exported cookies as `ItsSmartToolBot.txt` in the `YouTubeDLBot/cookies` directory of your project. 👀

### 📈 Managing Cookies ❄️

- 💥 **Cookie Expiry**:
  - If you encounter download issues, refresh your cookies by exporting a new `ItsSmartToolBot.txt` file. ⭐️
- 🌟 **Cookie Depletion**:
  - Avoid frequent bot restarts and excessive YouTube requests to prevent early cookie expiry. ✨

👀 This setup ensures efficient access to YouTube content without sign-in or bot protection errors. 💀

## 🌟 Deployment 💥

You can deploy YouTubeDLBot using one of the following methods: ❄️

### ⭐️ Option 1: Docker 📈
```bash
git clone https://github.com/TheSmartDevs/YouTubeDLBot
cd YouTubeDLBot
docker compose up --build --remove-orphans
```

### 💥 Option 2: Python 👀
```bash
git clone https://github.com/TheSmartDevs/YouTubeDLBot
cd YouTubeDLBot
pip3 install -r requirements.txt
python3 main.py
```

### 🌟 Option 3: Using Screen ✨
```bash
git clone https://github.com/TheSmartDevs/YouTubeDLBot
cd YouTubeDLBot
pip3 install -r requirements.txt
screen python3 main.py
```

### ⭐️ Option 4: Deploy to Heroku 📈
[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/TheSmartDevs/YouTubeDLBot)

You can deploy YouTubeDLBot to Heroku with a single click using the button above. Ensure you have a Heroku account and have set up the required environment variables as described in the **Environment Variables** section before deploying. ❄️

## 🌟 Environment Variables ❄️

💥 The bot requires certain environment variables to function correctly. You can configure these in one of two ways: ⭐️

1. 📈 **Using a `.env` File**: Create a `.env` file in the project root directory and set the variables there. 👀
2. 🌟 **Editing `config.py`**: Directly modify the default values in the `config.py` file located in the project directory. ✨

### 💥 Mandatory Environment Variables 💀
- `API_ID`: Your Telegram API ID (e.g., Your API_ID Here). ❄️
- `API_HASH`: Your Telegram API Hash (e.g., Your API_HASH Here). ⭐️
- `BOT_TOKEN`: The Telegram bot token obtained from BotFather (e.g., Your BOT_TOKEN Here). 📈
- `OWNER_IDS`: Comma-separated Telegram user IDs of bot owners (e.g., Your OWNER_IDS Here). 👀
- `MONGO_URL`: MongoDB connection URL for storing bot data (e.g., Your MONGO_URL Here). ✨
- `YT_COOKIES_PATH`: Path to the YouTube cookies file (e.g., `./cookies/ItsSmartToolBot.txt`). 💥

### 🌟 Recommended Environment Variables ❄️
- `COMMAND_PREFIX`: Prefixes for bot commands (e.g., Your COMMAND_PREFIX Here). ⭐️
- `MAX_VIDEO_SIZE`: Maximum video size in bytes (e.g., Your MAX_VIDEO_SIZE Here). 📈
- `UPDATE_CHANNEL_URL`: Telegram channel for bot updates (e.g., Your UPDATE_CHANNEL_URL Here). 👀
- `DEVELOPER_USER_ID`: Telegram user ID of the primary developer (e.g., Your DEVELOPER_USER_ID Here). ✨
- `START_MSG_PHOTO`: URL of the photo displayed in the start message (e.g., Your START_MSG_PHOTO Here). 💥

### 💀 Example `.env` File 🌟
```env
# Bot Configuration
API_ID=Your API_ID Here
API_HASH=Your API_HASH Here
BOT_TOKEN=Your BOT_TOKEN Here
OWNER_IDS=Your OWNER_IDS Here
MONGO_URL=Your MONGO_URL Here

# Constants
COMMAND_PREFIX=Your COMMAND_PREFIX Here
YT_COOKIES_PATH=./cookies/ItsSmartToolBot.txt
MAX_VIDEO_SIZE=Your MAX_VIDEO_SIZE Here
UPDATE_CHANNEL_URL=Your UPDATE_CHANNEL_URL Here
DEVELOPER_USER_ID=Your DEVELOPER_USER_ID Here
START_MSG_PHOTO=Your START_MSG_PHOTO Here
```

### ⭐️ Configuring via `config.py` 📈
🌟 Alternatively, you can edit the `config.py` file directly to set the default values for the variables. ❄️ The file uses environment variables if available, but falls back to the defaults specified in `config.py` if the `.env` file is not present or specific variables are unset. 💥 Open `config.py` and modify the default values in the `get_env_or_default` function calls to match your configuration. 👀

**Example `config.py` Snippet**:
```python
API_ID = get_env_or_default("API_ID", Your API_ID Here, int)
API_HASH = get_env_or_default("API_HASH", "Your API_HASH Here")
BOT_TOKEN = get_env_or_default("BOT_TOKEN", "Your BOT_TOKEN Here")
```

## 🌟 Requirements 💥

- Python 3.8+ ❄️
- Docker (for Docker deployment) ⭐️
- Dependencies listed in `requirements.txt` 📈
- A valid `ItsSmartToolBot.txt` file in `YouTubeDLBot/cookies` for YouTube access 👀

## 🌟 Project Author ⭐️

Abir Arafat Chawdhruy ✨

## 🌟 Contributing ❄️

💥 Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes. 📈 To report an issue, contact [@ISmartDevs](t.me/ISmartDevs) on Telegram. 👀
