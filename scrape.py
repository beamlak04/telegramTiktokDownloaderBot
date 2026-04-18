import os
import asyncio
import yt_dlp
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes


load_dotenv()
TOKEN = os.getenv('BOT_TOKEN') or os.getenv('BOT_TOEKN')


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! Send me a TikTok link and I will download the video for you.\n"
        "Use /help to see available commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n\n"
        "Then just send a TikTok URL like:\n"
        "https://www.tiktok.com/@username/video/123456789"
    )


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong! Bot is online.")


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Unknown command. Use /help to see what I can do.")

def download_tiktok(url):
    """Downloads TikTok video and returns the filename."""
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',  # Save in a 'downloads' folder
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
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
        # Run download in a separate thread to keep bot responsive
        file_path = await asyncio.to_thread(download_tiktok, url)
        
        # Send the video
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_VIDEO)
        with open(file_path, 'rb') as video:
            await update.message.reply_video(video=video, caption="Here is your video! 🚀")
        
        # Cleanup: Delete file after sending to save space
        os.remove(file_path)
        await status_msg.delete()

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    # Ensure download directory exists
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    print("Bot is running...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.run_polling()