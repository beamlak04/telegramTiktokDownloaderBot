# TikTok Telegram Downloader Bot

A simple Telegram bot that accepts a TikTok URL, downloads the video using `yt-dlp`, and sends the video back in chat.

## Features

- `/start` welcome message
- `/help` command guide
- `/ping` health check command
- Unknown command fallback
- TikTok link validation
- Progress indicators (`typing` and `upload_video` actions)
- Auto cleanup of downloaded files after sending

## Project Structure

- `scrape.py` - Bot entry point and handlers
- `downloads/` - Temporary downloaded videos
- `videos/` - Optional local output folder
- `.env` - Environment variables (not committed)

## Requirements

- Python 3.10+
- A Telegram Bot Token from BotFather

## Setup

1. Clone the repository and go into the project folder.
2. Create and activate a virtual environment.
3. Install dependencies.
4. Create a `.env` file with your bot token.

Example:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```env
BOT_TOKEN=your_telegram_bot_token_here
```

Note: the code currently supports both `BOT_TOKEN` and `BOT_TOEKN` (legacy typo fallback), but you should use `BOT_TOKEN`.

## Run

```bash
source .venv/bin/activate
python scrape.py
```

When started, you should see:

```text
Bot is running...
```

## Usage

1. Open your bot in Telegram.
2. Send `/start`.
3. Send a TikTok link, for example:

```text
https://www.tiktok.com/@username/video/123456789
```

4. The bot downloads and sends the video back.

## Commands

- `/start` - Start the bot and show quick usage
- `/help` - Show help text
- `/ping` - Check if bot is alive

## Troubleshooting

- `Unauthorized` or token errors:
  - Verify `.env` exists and `BOT_TOKEN` is correct.
- Bot does not respond:
  - Make sure polling process is running (`python scrape.py`).
- TikTok download fails:
  - URL may be invalid/private/restricted, or `yt-dlp` may need updates.

## Security Notes

- Never commit `.env` or bot tokens.
- Rotate your bot token if it is exposed.

## License

Use freely for personal/educational purposes. Add your preferred license if distributing publicly.
