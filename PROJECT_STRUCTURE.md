# Project Structure

```
tiktok/
├── .git/                      # Git repository
├── .venv/                     # Python virtual environment
├── .dockerignore              # Docker build exclusions
├── .env                       # Environment variables (not committed)
├── .gitignore                 # Git ignore patterns
├── Dockerfile                 # Docker container configuration
├── PROJECT_STRUCTURE.md       # This file
├── README.md                  # Project documentation
├── requirements.txt           # Python dependencies
├── scrape.py                  # Main bot application
├── downloads/                 # Temporary downloaded videos
└── videos/                    # Optional local output folder
```

## File Descriptions

- **scrape.py** - Main Telegram bot entry point with download handlers
- **requirements.txt** - Python package dependencies
- **Dockerfile** - Container configuration for deployment
- **.dockerignore** - Files excluded from Docker build
- **.gitignore** - Files excluded from Git tracking
- **.env** - Environment variables (BOT_TOKEN, PORT)
- **downloads/** - Temporary storage for downloaded TikTok videos
- **videos/** - Optional local output folder for videos
- **README.md** - Project documentation and setup instructions

## Complete Source Code

### scrape.py

```python
import os
import asyncio
import yt_dlp
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

# --- HEALTH CHECK SERVER FOR HOSTING ---
def run_health_check():
    """A simple server to satisfy Render/Koyeb health checks."""
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    print(f"Health check server running on port {port}...")
    server.serve_forever()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Send me a TikTok link and I will download the video for you.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Just send me a TikTok URL and I'll fetch the video!")

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong! Bot is online.")

def download_tiktok(url):
    ydl_opts = {
        # Changed to 'best' so it grabs a pre-merged MP4 stream. 
        # 'bestvideo+bestaudio' requires ffmpeg installed, which can fail on some hosts.
        'format': 'best', 
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'referer': 'https://www.tiktok.com/',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "tiktok.com" not in url:
        await update.message.reply_text("Please send a valid TikTok link!")
        return

    status_msg = await update.message.reply_text("⏳ Processing video... please wait.")
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        file_path = await asyncio.to_thread(download_tiktok, url)
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_VIDEO)
        with open(file_path, 'rb') as video:
            await update.message.reply_video(video=video, caption="Here is your video! 🚀")
        
        os.remove(file_path)
        await status_msg.delete()
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    # Start the dummy health-check web server in a background thread
    threading.Thread(target=run_health_check, daemon=True).start()

    print("Bot is running...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
```

### requirements.txt

```
anyio==4.13.0
certifi==2026.2.25
h11==0.16.0
httpcore==1.0.9
httpx==0.28.1
idna==3.11
python-dotenv==1.2.2
python-telegram-bot==22.7
typing_extensions==4.15.0
yt-dlp==2026.3.17
```

### Dockerfile

```
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including ffmpeg for media merging)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY scrape.py .

# Create downloads directory
RUN mkdir -p downloads

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port (Koyeb and Render will look for traffic here)
EXPOSE 8080

# Run the bot
CMD ["python", "scrape.py"]
```

### .dockerignore

```
.env
.env.*
.git
.gitignore
*.md
.venv
venv
__pycache__
*.pyc
downloads/
videos/
*.log
```

### .gitignore

```
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Logs
*.log

# Unit test / coverage reports
.coverage
.coverage.*
.pytest_cache/
.hypothesis/
.tox/
.nox/
htmlcov/

# Type checkers / linters
.mypy_cache/
.pyre/
.ruff_cache/

# Jupyter
.ipynb_checkpoints/

# Environments
.env
.env.*
.venv/
venv/
env/
ENV/

# IDEs / editors
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Project-generated media/output
videos/
```
