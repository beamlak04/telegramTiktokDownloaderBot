import os
import asyncio
import yt_dlp
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.request import HTTPXRequest
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

# --- CLEAN, DECOUPLED HEALTH CHECK SERVER ---
def run_health_check():
    """A simple server running in a dedicated background thread to handle health checks."""
    port = int(os.getenv("PORT", "8080").strip())
    
    # We use a custom, minimal handler so it responds instantly to Hugging Face
    from http.server import BaseHTTPRequestHandler
    class MinimalHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Bot is active")
            
        def log_message(self, format, *args):
            return # Quiet down the logs so they don't spam your screen

    server = HTTPServer(('0.0.0.0', port), MinimalHandler)
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
    file_path = None  # Track the file path so we can clean it up later

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        # Run download in a separate thread to keep bot responsive
        file_path = await asyncio.to_thread(download_tiktok, url)
        
        # Send the video
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_VIDEO)
        with open(file_path, 'rb') as video:
            await update.message.reply_video(video=video, caption="Here is your video! 🚀", read_timeout=120, write_timeout=120)
        
        await status_msg.delete()

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        
    finally:
        # --- GUARANTEED CLEANUP ---
        # This block ALWAYS runs, even if the try block threw an exception midway.
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"🧹 Successfully cleaned up and removed: {file_path}")
            except Exception as cleanup_error:
                print(f"⚠️ Failed to delete file: {cleanup_error}")

if __name__ == '__main__':
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    # Start the dummy health-check web server in a background thread
    health_thread = threading.Thread(target=run_health_check, daemon=True)
    health_thread.start()
    print("✅ Background health check listener successfully initiated.")
    # threading.Thread(target=run_health_check, daemon=True).start()
    print("🚀 Starting Telegram Bot polling loop...")

    print("Bot is running...")
    
    # --- ULTRA-RESILIENT DATA CENTER NETWORK CONFIGURATION ---
    # We expand the pool size and give the network maximum breathing room
    custom_request = HTTPXRequest(
        connect_timeout=120.0,  # 120 seconds to establish the initial handshake
        read_timeout=120.0,     # 120 seconds to read data streams
        write_timeout=120.0,    # 120 seconds to write data streams
        pool_timeout=120.0      # Time to wait for an available connection slot
    )
    
    # Build the application using our custom high-timeout client
    app = Application.builder().token(TOKEN).request(custom_request).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Tell the polling loop to retry infinitely if the data center network drops
    # instead of letting the script crash out completely.
    app.run_polling(
        bootstrap_retries=-1,   # Keep retrying startup handshakes infinitely
        timeout=120
    )