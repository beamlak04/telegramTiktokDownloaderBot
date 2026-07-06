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
    # Read the environment port as a string first, falling back safely to "8080"
    port_str = os.getenv("PORT", "8080").strip()
    port = int(port_str)
    
    # Binding to '0.0.0.0' allows external health-check pings to hit the app
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
    threading.Thread(target=run_health_check, daemon=True).start()

    print("Bot is running...")
    custom_request = HTTPXRequest(
        connect_timeout=120.0, 
        read_timeout=120.0,
        write_timeout=120.0
    )
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()