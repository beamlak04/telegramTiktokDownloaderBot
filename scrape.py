import os
import asyncio
import logging
import yt_dlp
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.request import HTTPXRequest
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

# --- LOGGING (so errors are visible instead of silently swallowed) ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print(f"Token loaded: {'YES' if TOKEN else 'NO - MISSING'}")

# --- QUICK NETWORK SANITY CHECK ---
# If the container can't reach Telegram's servers at all, everything below
# will just hang silently for up to `connect_timeout` seconds. Fail fast and
# loud here instead, so it's obvious in the logs within a few seconds.
def check_telegram_connectivity():
    import httpx
    try:
        resp = httpx.get("https://api.telegram.org", timeout=10.0)
        logger.info(f"✅ Network check: reached api.telegram.org (status {resp.status_code})")
        return True
    except Exception as e:
        logger.error(f"❌ Network check FAILED: could not reach api.telegram.org -> {e}")
        return False


# --- CLEAN, DECOUPLED HEALTH CHECK SERVER ---
def run_health_check():
    """A simple server running in a dedicated background thread to handle health checks."""
    port = int(os.getenv("PORT", "8080").strip())

    class MinimalHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Bot is active")

        def log_message(self, format, *args):
            return  # Quiet down the logs so they don't spam your screen

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
        # 'best' grabs a pre-merged MP4 stream.
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
            await update.message.reply_video(
                video=video,
                caption="Here is your video! 🚀",
                read_timeout=120,
                write_timeout=120
            )

        await status_msg.delete()

    except Exception as e:
        logger.exception("Error handling message")
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


async def post_init(application: Application):
    """Runs inside the same event loop that run_polling() manages, right before
    polling begins. Telegram won't deliver updates via polling while a webhook
    is registered, so we clear it here instead of driving a separate loop
    manually (which can silently deadlock against run_polling())."""
    await application.bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook cleared (if one was set). Ready to poll.")


if __name__ == '__main__':
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    # Start the health-check web server in a background thread
    health_thread = threading.Thread(target=run_health_check, daemon=True)
    health_thread.start()
    logger.info("✅ Background health check listener successfully initiated.")

    # Run the network sanity check before doing anything else
    check_telegram_connectivity()

    logger.info("🚀 Starting Telegram Bot polling loop...")

    # --- NETWORK CONFIGURATION ---
    # Timeouts kept reasonably short (not 120s) so a real connectivity problem
    # raises a visible error within ~20s instead of looking like a silent hang.
    custom_request = HTTPXRequest(
        connect_timeout=20.0,
        read_timeout=20.0,
        write_timeout=20.0,
        pool_timeout=20.0
    )

    # Build the application using our custom high-timeout client.
    # post_init runs once, inside run_polling()'s own event loop, right before
    # polling starts - this avoids the event-loop conflict/hang you get from
    # manually calling asyncio.get_event_loop().run_until_complete() beforehand.
    app = Application.builder().token(TOKEN).request(custom_request).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Retry infinitely if the data center network drops instead of crashing out
    app.run_polling(
        bootstrap_retries=-1,   # Keep retrying startup handshakes infinitely
        timeout=120,            # Long-poll timeout for getUpdates (seconds)
        drop_pending_updates=True
    )