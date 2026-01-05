import logging
import os
import platform
import random
import shutil
import string
import time
import urllib
from pathlib import Path

import telebot
import yt_dlp
from dotenv import load_dotenv
from telebot.types import InputMediaPhoto, InputMediaVideo, Message

import dbtools
import toolbox as util

# --- Setup ---

logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PRIVATE_CHANNEL_ID = os.getenv("PRIVATE_CHANNEL_ID")
TEMP_DIR = Path("media-downloads")
IMG_DIR = Path("img")

bot = telebot.TeleBot(BOT_TOKEN)

dbtools.prepare_db()  # Creates the DB if not present


def get_photo_file_id(file_path: str) -> str:
    """Uploads a photo file to the private channel to get a Telegram File ID."""
    with open(file_path, "rb") as f:
        return bot.send_photo(PRIVATE_CHANNEL_ID, f).photo[-1].file_id

def get_document_file_id(file_path: str) -> str:
    """Uploads a photo file to the private channel to get a Telegram File ID."""
    with open(file_path, "rb") as f:
        return bot.send_document(PRIVATE_CHANNEL_ID, f).document.file_id

BIGRAT_FILE_ID = get_photo_file_id("img/bigrat.jpg")
DOWNLOADING_GIF_FILE_ID = get_document_file_id("img/toro-animated-256.gif")


def cleanup_temp_mp4():
    """Safely removes mp4 files in the current directory."""
    for file in Path(".").glob("*.mp4"):
        try:
            file.unlink()
        except OSError as e:
            logger.error(f"Error deleting {file}: {e}")


cleanup_temp_mp4()


def chunk_list(data: list, size: int):
    """Yield successive n-sized chunks from a list."""
    for i in range(0, len(data), size):
        yield data[i:i + size]


def send_status_message(chat_id: int, text: str, reply_to: int = None) -> Message:
    return bot.send_message(
        chat_id, text,
        reply_to_message_id=reply_to,
        parse_mode="Markdown"
    )


def safe_delete(message: Message, delay: int = 0):
    if delay:
        time.sleep(delay)
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception as e:
        logger.debug(f"Failed to delete message: {e}")


# --- Handlers ---

@bot.message_handler(commands=['start'])
def start(message: Message):
    huh_toro = IMG_DIR / "huh-toro.jpg"
    if huh_toro.exists():
        with huh_toro.open("rb") as f:
            bot.send_photo(message.chat.id, f, reply_to_message_id=message.message_id)


@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    text = message.text or ""

    # That absolutely huge rat
    if "bigrat.monster" in text:
        if BIGRAT_FILE_ID:
            bot.send_photo(message.chat.id, BIGRAT_FILE_ID, reply_to_message_id=message.message_id)
        return

    if "https://" not in text:
        return

    url = util.extract_https_url(text)
    if not url:
        return

    # Separate handling for direct mp4 file URLs
    if util.check_if_mp4_url(url):
        process_direct_mp4(message, url)
        return

    if not util.validate_url(url):
        return

    platform_id = util.get_platform_video_id(url)
    media_count = dbtools.get_number_of_media_by_platform_id(platform_id)

    if media_count > 0:
        send_media_from_cache(message, url, platform_id, media_count)
        return

    if "youtube.com" in url or "youtu.be" in url:
        try:
            yt_url = util.get_yt_video_url(util.get_yt_video_id(url))
            if util.is_video_longer_than(yt_url, 600):  # 10 mins
                return
        except Exception:
            return

    process_new_download(message, url)


# --- CORE LOGIC ---

def process_new_download(message: Message, url: str):
    """Orchestrates the download of content from supported platforms."""

    is_single_video_platform = any(x in url for x in ["youtube.com", "youtu.be", "reddit.com", "redd.it"])

    status_msg = bot.send_document(chat_id=message.chat.id,
                                   caption=">.< | Downloading...",
                                   reply_to_message_id=message.message_id,
                                   document=DOWNLOADING_GIF_FILE_ID)

    if is_single_video_platform:
        filename = util.get_filename(url, "mp4")
        if filename == "-1":
            safe_delete(status_msg)
            return

        file_path = Path(filename)

        try:
            # YouTube specific logic to avoid issues with additional data in the url (like playlist info)
            if "youtu" in url:
                if util.is_video_longer_than(url, 150):
                    util.download_video_720(util.get_yt_video_url(util.get_yt_video_id(url)), filename)
                else:
                    util.download_video(util.get_yt_video_url(util.get_yt_video_id(url)), filename)
            else:
                util.download_video(url, filename)

            # Upload
            if file_path.exists():
                if util.is_file_smaller_than_50mb(str(file_path)):
                    with file_path.open('rb') as video_file:
                        resp = bot.send_video(
                            chat_id=message.chat.id,
                            video=video_file,
                            supports_streaming=True,
                            caption=f"Here's your [video]({url}) >w<",
                            parse_mode="Markdown",
                            reply_to_message_id=message.message_id
                        )
                    # Save to DB
                    dbtools.add_video(resp.video.file_id, util.get_platform_video_id(url), util.get_platform(url))
                    safe_delete(status_msg)
                else:
                    bot.edit_message_text("*O.O | Too big!*", chat_id=message.chat.id,
                                          message_id=status_msg.message_id, parse_mode="Markdown")
                    safe_delete(status_msg, 3)
            else:
                raise FileNotFoundError("Download failed, file not found.")

        except Exception as e:
            logger.error(f"Single video error: {e}")
            bot.edit_message_text("*ᇂ_ᇂ | Error downloading!*", chat_id=message.chat.id,
                                  message_id=status_msg.message_id,
                                  parse_mode="Markdown")
            safe_delete(status_msg, 3)
        finally:
            if file_path.exists():
                file_path.unlink()
    else:
        try:
            process_gallery_download(message, url)
        except Exception as e:
            logger.error(f"Gallery routine error: {e}")
        safe_delete(status_msg)


def send_media_from_cache(message: Message, url: str, platform_id: str, count: int):
    """Handles sending media that already exists in the database."""
    caption = f"Here's your [media]({url}) >w<"

    if count == 1:
        media_data = dbtools.get_first_media(platform_id)
        file_id, _, _, media_type = media_data

        if media_type == "photo":
            bot.send_photo(message.chat.id, file_id, caption=caption,
                           parse_mode="Markdown", reply_to_message_id=message.message_id)
        else:
            bot.send_video(message.chat.id, file_id, caption=caption,
                           supports_streaming=True, parse_mode="Markdown",
                           reply_to_message_id=message.message_id)
    else:
        # Multi-media handling (Albums)
        all_media = dbtools.get_all_media(platform_id)
        input_media_list = []

        for index, row in enumerate(all_media):
            file_id, _, _, media_type = row
            # Only the first item gets the caption
            current_caption = caption if index == 0 else None

            if media_type == "photo":
                input_media_list.append(InputMediaPhoto(file_id, caption=current_caption, parse_mode="Markdown"))
            elif media_type == "video":
                input_media_list.append(
                    InputMediaVideo(file_id, caption=current_caption, parse_mode="Markdown", supports_streaming=True))

        # Send in groups of 10, since it's the maximum that Telegram allows.
        for chunk in chunk_list(input_media_list, 10):
            bot.send_media_group(message.chat.id, media=chunk, reply_to_message_id=message.message_id)

        # Send Audio if exists
        audio_data = dbtools.get_first_sound(platform_id)
        if audio_data:
            bot.send_audio(message.chat.id, audio=audio_data[0], reply_to_message_id=message.message_id)


def process_direct_mp4(message: Message, url: str):
    """Downloads and sends a direct MP4 link."""
    filename = ''.join(random.choices(string.ascii_letters + string.digits, k=8)) + '.mp4'
    file_path = Path(filename)

    if util.check_if_mp4_url_is_larger_than_50mb(url):
        status = send_status_message(message.chat.id, "O.O | Too big!", message.message_id)
        safe_delete(status, 3)
        return

    status_msg = send_status_message(message.chat.id, ">.< | Downloading...", message.message_id)

    try:
        urllib.request.urlretrieve(url, filename)

        bot.edit_message_text("=w= | Uploading...", chat_id=message.chat.id, message_id=status_msg.message_id)

        with file_path.open('rb') as video_file:
            bot.send_video(
                chat_id=message.chat.id,
                video=video_file,
                supports_streaming=True,
                caption=f"Here's your [video]({url}) >w<",
                parse_mode="Markdown",
                reply_to_message_id=message.message_id
            )
        safe_delete(status_msg)

    except Exception as e:
        logger.error(f"Direct download error: {e}")
        bot.edit_message_text("*(⋟﹏⋞) | Error processing!*", chat_id=message.chat.id,
                              message_id=status_msg.message_id, parse_mode="Markdown")
        safe_delete(status_msg, 3)
    finally:
        if file_path.exists():
            file_path.unlink()


def process_gallery_download(message: Message, url: str):
    """Handles URLs with multiple photos and videos, uses gallery-dl."""
    util.download_media(url)

    platform = util.get_platform(url)
    video_id = util.get_platform_video_id(url)
    download_path = TEMP_DIR / platform / video_id

    if not download_path.exists():
        return

    files = [f for f in download_path.iterdir() if f.name.startswith(video_id)]
    files = util.naturally_sort_filenames(files)

    media_items = []

    media_files = [f for f in files if f.suffix in ['.webp', '.jpg', '.png', '.mp4']]

    for f in media_files:
        is_photo = f.suffix in ['.webp', '.jpg', '.png']
        with f.open('rb') as file_obj:
            if is_photo:
                msg = bot.send_photo(PRIVATE_CHANNEL_ID, file_obj)
                file_id = msg.photo[-1].file_id
                dbtools.add_photo(file_id, video_id, platform)
                media_items.append(InputMediaPhoto(file_id))
            else:
                msg = bot.send_video(PRIVATE_CHANNEL_ID, file_obj)
                file_id = msg.video.file_id
                dbtools.add_video(file_id, video_id, platform)
                media_items.append(InputMediaVideo(file_id, supports_streaming=True))

    # Add caption to first item
    if media_items:
        media_items[0].caption = f"Here's your [media]({url}) >w<"
        media_items[0].parse_mode = "Markdown"

        # Send in groups of 10, since it's the maximum that Telegram allows.
        for chunk in chunk_list(media_items, 10):
            bot.send_media_group(message.chat.id, media=chunk, reply_to_message_id=message.message_id)

    audio_files = [f for f in files if f.suffix == '.mp3']
    if audio_files:
        with audio_files[0].open('rb') as f:
            msg = bot.send_audio(PRIVATE_CHANNEL_ID, f)
            file_id = msg.audio.file_id
            dbtools.add_sound(file_id, video_id, platform)
            bot.send_audio(message.chat.id, file_id, reply_to_message_id=message.message_id)

    # Delete files
    shutil.rmtree(download_path)


# --- Entry Point ---

if __name__ == '__main__':
    try:
        logger.info("Bot running on " + platform.platform())
        logger.info("Using yt-dlp: " + yt_dlp.version.__version__)
        logger.info("Bot started...")
        bot.infinity_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.critical(f"Critical error: {e}")

bot.infinity_polling()
