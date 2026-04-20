import logging
import os
import platform
import random
import shutil
import string
import urllib
import urllib.request
from pathlib import Path

import telebot
import yt_dlp
from dotenv import load_dotenv
from telebot.types import InputMediaPhoto, InputMediaVideo, Message

import botTools
import dbtools
import exceptions
import toolbox as util

# --- Setup ---

logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()

util.cleanup()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PRIVATE_CHANNEL_ID = os.getenv("PRIVATE_CHANNEL_ID")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
TEMP_DIR = Path("media-downloads")
IMG_DIR = Path("img")

bot = telebot.TeleBot(BOT_TOKEN)

dbtools.prepare_db()  # Creates the DB if not present

BIGRAT_FILE_ID = botTools.get_photo_file_id(bot, "img/bigrat.jpg", PRIVATE_CHANNEL_ID)
DOWNLOADING_GIF_FILE_ID = botTools.get_document_file_id(bot, "img/toro-animated-256.gif", PRIVATE_CHANNEL_ID)
SAD_TORO_FILE_ID = botTools.get_photo_file_id(bot, "img/toro-sad-256.png", PRIVATE_CHANNEL_ID)


# --- Handlers ---

@bot.message_handler(commands=['start'])
def start(message: Message):
    huh_toro = IMG_DIR / "huh-toro.jpg"
    if huh_toro.exists():
        with huh_toro.open("rb") as f:
            bot.send_photo(message.chat.id, f, reply_to_message_id=message.message_id)


@bot.message_handler(commands=['cat'])
def send_random_cat_pic(message: Message):
    """Sends a random cat picture using cataas.com"""

    urllib.request.urlretrieve("https://cataas.com/cat", "catpic.cat")
    with open("catpic.cat", "rb") as f:
        bot.send_photo(message.chat.id, f, reply_to_message_id=message.message_id)

    os.remove("catpic.cat")


@bot.message_handler(commands=['httpcat'])
def send_httpcat_pic(message: Message):
    notfound = False

    try:
        code = message.text.split()[1:][0]
    except IndexError:
        return

    if not code.isdigit():
        return

    if len(code) != 3:
        return

    url = "https://http.cat/" + code
    try:
        urllib.request.urlretrieve(url, "httpcat.tmp")
    except urllib.error.HTTPError:
        urllib.request.urlretrieve("https://http.cat/404", "httpcat.tmp")
        notfound = True

    if not notfound:
        with open("httpcat.tmp", "rb") as f:
            bot.send_photo(message.chat.id, f, reply_to_message_id=message.message_id)
    else:
        with open("httpcat.tmp", "rb") as f:
            bot.send_photo(message.chat.id, f, reply_to_message_id=message.message_id,
                           caption="Unknown HTTP error code...")

    os.remove("httpcat.tmp")


@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    text = message.text or ""

    # That absolutely huge rat
    if "bigrat.monster" in text.lower():
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
    status_msg = botTools.send_status_msg(bot, message, DOWNLOADING_GIF_FILE_ID)

    if is_single_video_platform:
        filename = util.get_filename(url, "mp4")
        if filename == "-1":
            botTools.safe_delete(bot, status_msg)
            return

        file_path = Path("yt-dlp-downloads/" + filename)

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
                    botTools.safe_delete(bot, status_msg)
                else:
                    botTools.safe_delete(bot, status_msg)
                    error_msg = botTools.send_too_big_msg(bot, message, SAD_TORO_FILE_ID)
                    botTools.safe_delete(bot, error_msg, 3)
            else:
                raise FileNotFoundError("Download failed, file not found.")

        except Exception as e:
            logger.error(f"Single video error: {e}")
            botTools.safe_delete(bot, status_msg)
            error_msg = botTools.send_error_msg(bot, message, SAD_TORO_FILE_ID)

            botTools.safe_delete(bot, error_msg, 3)
            botTools.send_message_to_admin(bot, ADMIN_USER_ID, "i messed up\n\n" + e.__str__() + "\n\nURL: " + url)

        finally:
            if file_path.exists():
                file_path.unlink()
    else:
        try:
            process_gallery_download(message, url)
        except exceptions.FileTooBigException:
            botTools.safe_delete(bot, status_msg)
            error_msg = botTools.send_too_big_msg(bot, message, SAD_TORO_FILE_ID)
            botTools.safe_delete(bot, error_msg, 3)
        except Exception as e:
            logger.error(f"Gallery routine error: {e}")
            botTools.send_message_to_admin(bot, ADMIN_USER_ID, "i messed up\n\n" + e.__str__() + "\n\nURL: " + url)

        botTools.safe_delete(bot, status_msg)


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
        for chunk in util.chunk_list(input_media_list, 10):
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
        error_msg = botTools.send_too_big_msg(bot, message, SAD_TORO_FILE_ID)

        botTools.safe_delete(bot, error_msg, 3)
        return

    status_msg = botTools.send_status_msg(bot, message, DOWNLOADING_GIF_FILE_ID)

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
        botTools.safe_delete(bot, status_msg)

    except Exception as e:
        logger.error(f"Direct download error: {e}")
        botTools.safe_delete(bot, status_msg)
        error_msg = botTools.send_error_msg(bot, message, SAD_TORO_FILE_ID)
        botTools.safe_delete(bot, error_msg, 3)
        botTools.send_message_to_admin(bot, ADMIN_USER_ID, "i messed up\n\n" + e.__str__() + "\n\nURL: " + url)
    finally:
        if file_path.exists():
            file_path.unlink()


def process_gallery_download(message: Message, url: str):
    """Handles URLs with multiple photos and videos, uses gallery-dl."""
    util.download_media(url)

    platform_name = util.get_platform(url)
    video_id = util.get_platform_video_id(url)
    download_path = TEMP_DIR / platform_name / video_id

    if not download_path.exists():
        botTools.send_message_to_admin(bot, ADMIN_USER_ID, "i messed up\n\nURL: " + url)
        return

    files = [f for f in download_path.iterdir() if f.name.startswith(video_id)]
    files = util.naturally_sort_filenames(files)

    if not util.is_arr_smaller_than_50mb(files):
        logger.warning(f"Files are bigger than 50mb")
        shutil.rmtree(download_path)
        raise exceptions.FileTooBigException()

    media_items = []

    media_files = [f for f in files if f.suffix in ['.webp', '.jpg', '.png', '.mp4']]

    for f in media_files:
        is_photo = f.suffix in ['.webp', '.jpg', '.png']
        with f.open('rb') as file_obj:
            if is_photo:
                msg = bot.send_photo(PRIVATE_CHANNEL_ID, file_obj)
                file_id = msg.photo[-1].file_id
                dbtools.add_photo(file_id, video_id, platform_name)
                media_items.append(InputMediaPhoto(file_id))
            else:
                msg = bot.send_video(PRIVATE_CHANNEL_ID, file_obj)
                file_id = msg.video.file_id
                dbtools.add_video(file_id, video_id, platform_name)
                media_items.append(InputMediaVideo(file_id, supports_streaming=True))

    # Add caption to first item
    if media_items:
        media_items[0].caption = f"Here's your [media]({url}) >w<"
        media_items[0].parse_mode = "Markdown"

        # Send in groups of 10, since it's the maximum that Telegram allows.
        for chunk in util.chunk_list(media_items, 10):
            bot.send_media_group(message.chat.id, media=chunk, reply_to_message_id=message.message_id)

    audio_files = [f for f in files if f.suffix == '.mp3']
    if audio_files:
        with audio_files[0].open('rb') as f:
            msg = bot.send_audio(PRIVATE_CHANNEL_ID, f)
            file_id = msg.audio.file_id
            dbtools.add_sound(file_id, video_id, platform_name)
            bot.send_audio(message.chat.id, file_id, reply_to_message_id=message.message_id)

    # Delete files
    shutil.rmtree(download_path)


# --- Entry Point ---

if __name__ == '__main__':
    try:
        logger.info("Bot running on " + platform.platform())
        logger.info("Using yt-dlp: " + yt_dlp.version.__version__)
        logger.info("Bot started...")
        botTools.send_message_to_admin(bot, ADMIN_USER_ID, "I'm alive!")
        bot.infinity_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.critical(f"Critical error: {e}")

bot.infinity_polling()
