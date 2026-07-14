#!/usr/bin/env python3
"""
Telegram Media Saver Bot
An asynchronous Telegram bot using aiogram v3.x and yt-dlp to automate saving media
from Instagram (Reels) and YouTube (Shorts/Videos).
"""

import os
import re
import asyncio
import logging
import uuid
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramAPIError
import yt_dlp

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MediaSaverBot")

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.warning("BOT_TOKEN environment variable not set in .env file. Using a dummy token for importing.")
    # Fallback to a dummy token format that passes aiogram's validation
    BOT_TOKEN = "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"

# Check for cookies.txt
COOKIES_FILE = "cookies.txt"
has_cookies = os.path.exists(COOKIES_FILE)
if has_cookies:
    logger.info("Local cookies.txt found. Will use it for yt-dlp authentication.")
else:
    logger.info("No cookies.txt found in the project directory. Continuing without cookies.")


def download_media_sync(url: str, output_path: str) -> str:
    """
    Synchronous download helper to be wrapped inside asyncio.to_thread.
    Downloads the best video and audio streams and merges them into an mp4.
    """
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }

    # Add cookies if cookies.txt is present in the project directory
    if os.path.exists(COOKIES_FILE):
        ydl_opts['cookiefile'] = COOKIES_FILE

    logger.info(f"Starting download sync with yt-dlp for URL: {url}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        base, _ = os.path.splitext(filename)
        actual_filename = base + ".mp4"
        if os.path.exists(actual_filename):
            return actual_filename
        elif os.path.exists(filename):
            return filename
        else:
            raise FileNotFoundError("Downloaded file could not be located on disk.")


async def download_media(url: str) -> str:
    """
    Asynchronously downloads media from a URL using yt-dlp by wrapping
    the synchronous downloader in asyncio.to_thread to make it non-blocking.
    """
    unique_id = str(uuid.uuid4())
    output_tmpl = f"temp_video_{unique_id}.%(ext)s"
    return await asyncio.to_thread(download_media_sync, url, output_tmpl)


# Initialize Bot and Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Regex pattern to match YouTube and Instagram links
LINK_PATTERN = re.compile(
    r'(https?://(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/|v/|embed/|shared\?ci=)|youtu\.be/|instagram\.com/(?:p|reel|reels|tv)/)[^\s]+)',
    re.IGNORECASE
)


async def send_and_delete_error(chat_id: int, text: str, delay: int = 15):
    """
    Sends an error notification to the chat and schedules its automated deletion after the specified delay.
    """
    try:
        err_msg = await bot.send_message(chat_id=chat_id, text=text)
        await asyncio.sleep(delay)
        try:
            await bot.delete_message(chat_id=chat_id, message_id=err_msg.message_id)
        except TelegramAPIError as e:
            logger.warning(f"Failed to delete temporary error message: {e}")
    except TelegramAPIError as e:
        logger.error(f"Failed to send error notification message: {e}")


@dp.channel_post(F.text)
@dp.message(F.text)
async def handle_links(message: types.Message):
    """
    Main handler that intercepts links from YouTube/Instagram, downloads the media,
    uploads it as a native playable Telegram video, and deletes the original message.
    """
    text = message.text or ""
    match = LINK_PATTERN.search(text)
    if not match:
        return

    url = match.group(1)
    chat_id = message.chat.id
    message_id = message.message_id

    logger.info(f"Intercepted supported URL in chat {chat_id}: {url}")

    # Send a status/processing notification
    status_msg = None
    try:
        status_msg = await bot.send_message(
            chat_id=chat_id,
            text="⏳ *Processing media, please wait...*",
            parse_mode=ParseMode.MARKDOWN
        )
    except TelegramAPIError as e:
        logger.warning(f"Could not send processing message: {e}")

    filepath = None
    try:
        # Download the video asynchronously
        filepath = await download_media(url)
        logger.info(f"Successfully downloaded to: {filepath}")

        # Send native video to Telegram
        video_file = FSInputFile(filepath)
        await bot.send_video(
            chat_id=chat_id,
            video=video_file,
            supports_streaming=True
        )
        logger.info(f"Successfully uploaded video {filepath} to chat {chat_id}")

        # Delete the original link post/message to keep the channel clean
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except TelegramAPIError as e:
            logger.warning(f"Could not delete original message with link: {e}. Check if bot has administrative delete permissions.")

    except Exception as exc:
        logger.exception(f"Error handling media URL {url}: {exc}")
        # Send a temporary self-deleting error notification
        asyncio.create_task(
            send_and_delete_error(
                chat_id=chat_id,
                text=f"❌ *Failed to process link:* {url}\n_The error was logged._",
                delay=15
            )
        )
    finally:
        # Cleanup temporary processing message
        if status_msg:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
            except TelegramAPIError:
                pass

        # Cleanup local downloaded temporary file to prevent running out of space
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info(f"Cleaned up temporary file: {filepath}")
            except OSError as e:
                logger.error(f"Error deleting temporary file {filepath}: {e}")


async def main():
    """
    Main runner to start the Telegram bot's polling.
    """
    if os.getenv("BOT_TOKEN") is None:
        logger.critical("BOT_TOKEN is not configured! Please provide a valid token in the .env file.")
        return
    logger.info("Starting Telegram Bot long polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
