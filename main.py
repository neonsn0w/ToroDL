import glob
import logging
import os
import platform
import random
import string
import time
import urllib
import shutil

import telebot
import yt_dlp
from dotenv import load_dotenv
from telebot.types import InputMediaPhoto, InputMediaVideo

import dbtools
import toolbox as util

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PRIVATE_CHANNEL_ID = os.getenv("PRIVATE_CHANNEL_ID")

bot = telebot.TeleBot(BOT_TOKEN)

dbtools.prepare_db()  # Creates the DB if not present

logger.info("Bot running on " + platform.platform())
logger.info("Using yt-dlp: " + yt_dlp.version.__version__)

if platform.system() == "Linux":
    os.system("rm *.mp4")


@bot.message_handler(commands=['start'])
def start(message):
    if os.path.exists("img/huh-toro.jpg"):
        with open("img/huh-toro.jpg", "rb") as f:
            bot.send_photo(message.chat.id, f, reply_to_message_id=message.message_id)


@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    if "bigrat.monster" in message.text:
        if os.path.exists("img/bigrat.jpg"):
            with open("img/bigrat.jpg", "rb") as f:
                bot.send_photo(message.chat.id, f, reply_to_message_id=message.message_id)

        return

    if "https://" in message.text:
        url = util.extract_https_url(message.text)

        if util.check_if_mp4_url(url):
            download_direct_mp4(url, message)
            return

        if util.validate_url(url):
            if dbtools.get_number_of_media_by_platform_id(util.get_platform_video_id(url)) == 1:
                if dbtools.get_first_media(util.get_platform_video_id(url))[3] == "photo":
                    bot.send_photo(
                        chat_id=message.chat.id,
                        photo=dbtools.get_first_media(util.get_platform_video_id(url))[0],
                        caption="Here's your [media](" + url + ") >w<",
                        parse_mode="Markdown",
                        reply_to_message_id=message.message_id
                    )
                else:
                    bot.send_video(
                        chat_id=message.chat.id,
                        video=dbtools.get_first_media(util.get_platform_video_id(url))[0],
                        supports_streaming=True,
                        caption="Here's your [media](" + url + ") >w<",
                        parse_mode="Markdown",
                        reply_to_message_id=message.message_id
                    )
                return
            elif dbtools.get_number_of_media_by_platform_id(util.get_platform_video_id(url)) > 1:
                i = 0  # Questo loop mi pare abbastanza orrendo
                medias = []

                for row in dbtools.get_all_media(util.get_platform_video_id(url)):
                    if i == 0:
                        if row[3] == "photo":
                            medias.append(
                                InputMediaPhoto(row[0], caption="Here's your [media](" + url + ") >w<",
                                                parse_mode="Markdown"))
                        else:
                            medias.append(
                                InputMediaVideo(row[0], caption="Here's your [media](" + url + ") >w<",
                                                parse_mode="Markdown"))

                    elif i == 10:
                        bot.send_media_group(chat_id=message.chat.id, media=medias,
                                             reply_to_message_id=message.message_id)
                        medias = []

                        if row[3] == "photo":
                            medias.append(
                                InputMediaPhoto(row[0]))
                        else:
                            medias.append(
                                InputMediaVideo(row[0]))

                    else:
                        if row[3] == "photo":
                            medias.append(
                                InputMediaPhoto(row[0]))
                        else:
                            medias.append(
                                InputMediaVideo(row[0]))

                    i = i + 1

                bot.send_media_group(chat_id=message.chat.id, media=medias, reply_to_message_id=message.message_id)
                return

            if "youtube.com" in url or "youtu.be" in url:
                try:
                    url = util.get_yt_video_url(util.get_yt_video_id(url))

                    if util.is_video_longer_than(url, 420):  # 7 minutes
                        return
                except Exception as e:
                    return

            filename = util.get_filename(url, "mp4")

            if filename == "-1":
                return

            sent_msg = bot.reply_to(message, ">.< | Downloading...")

            if "instagram.com" not in url and "tiktok.com" not in url:
                try:
                    if "youtube.com" in url or "youtu.be" in url:
                        if util.is_video_longer_than(url, 120):
                            util.download_video_720(url, filename)
                        else:
                            util.download_video(url, filename)
                    else:
                        util.download_video(url, filename)
                except Exception as e:
                    logger.error(e)
                    if "18 years" in str(e):
                        bot.edit_message_text("*ᇂ_ᇂ | This video is age restricted!*", chat_id=message.chat.id,
                                              message_id=sent_msg.message_id, parse_mode="Markdown")
                    else:
                        bot.edit_message_text("*ᇂ_ᇂ | Error downloading!*", chat_id=message.chat.id,
                                              message_id=sent_msg.message_id, parse_mode="Markdown")
                    time.sleep(3)
                    bot.delete_message(sent_msg.chat.id, sent_msg.message_id)
                    return
            else:
                ig_routine(message, url)
                bot.delete_message(sent_msg.chat.id, sent_msg.message_id)
                return
        else:
            return

        if os.path.exists(filename) and filename:
            if util.is_file_smaller_than_50mb(filename):
                try:
                    bot.edit_message_text("=w= | Uploading...", chat_id=message.chat.id,
                                          message_id=sent_msg.message_id)

                    with open(filename, 'rb') as video_file:
                        response = bot.send_video(
                            chat_id=message.chat.id,
                            video=video_file,
                            supports_streaming=True,
                            caption="Here's your [video](" + url + ") >w<",
                            parse_mode="Markdown",
                            reply_to_message_id=message.message_id
                        )

                    bot.delete_message(sent_msg.chat.id, sent_msg.message_id)

                    dbtools.add_video(response.video.file_id, util.get_platform_video_id(url),
                                      util.get_platform(url))

                    os.remove(filename)
                except Exception as e:
                    bot.edit_message_text("*(⋟﹏⋞) | Error uploading!*", chat_id=message.chat.id,
                                          message_id=sent_msg.message_id, parse_mode="Markdown")
                    time.sleep(3)
                    bot.delete_message(sent_msg.chat.id, sent_msg.message_id)

                    os.remove(filename)

            else:
                bot.edit_message_text("*O.O | Too big!*", chat_id=message.chat.id, message_id=sent_msg.message_id,
                                      parse_mode="Markdown")
                time.sleep(3)
                bot.delete_message(sent_msg.chat.id, sent_msg.message_id)

                os.remove(filename)

        else:
            bot.edit_message_text("*╥﹏╥ | Error downloading!*", chat_id=message.chat.id,
                                  message_id=sent_msg.message_id, parse_mode="Markdown")
            time.sleep(3)
            bot.delete_message(sent_msg.chat.id, sent_msg.message_id)


def download_direct_mp4(url: str, message: telebot.types.Message):
    filename = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    filename += '.mp4'

    if util.check_if_mp4_url_is_larger_than_50mb(url):
        sent_msg = bot.reply_to(message, "O.O | Too big!")
        time.sleep(3)
        bot.delete_message(sent_msg.chat.id, sent_msg.message_id)
        return

    sent_msg = bot.reply_to(message, ">.< | Downloading...")

    try:
        urllib.request.urlretrieve(url, filename)
    except Exception as e:
        logger.error(e)
        bot.edit_message_text("*ᇂ_ᇂ | Error downloading!*", chat_id=message.chat.id,
                              message_id=sent_msg.message_id, parse_mode="Markdown")
        time.sleep(3)
        bot.delete_message(sent_msg.chat.id, sent_msg.message_id)
        return

    try:
        bot.edit_message_text("=w= | Uploading...", chat_id=message.chat.id,
                              message_id=sent_msg.message_id)

        with open(filename, 'rb') as video_file:
            response = bot.send_video(
                chat_id=message.chat.id,
                video=video_file,
                supports_streaming=True,
                caption="Here's your [video](" + url + ") >w<",
                parse_mode="Markdown",
                reply_to_message_id=message.message_id
            )

        bot.delete_message(sent_msg.chat.id, sent_msg.message_id)

        os.remove(filename)
    except Exception as e:
        logger.error(e)
        bot.edit_message_text("*(⋟﹏⋞) | Error uploading!*", chat_id=message.chat.id,
                              message_id=sent_msg.message_id, parse_mode="Markdown")
        time.sleep(3)
        bot.delete_message(sent_msg.chat.id, sent_msg.message_id)

        os.remove(filename)


def ig_routine(message, url):
    util.download_media(url)

    jpgs = [
        f for f in os.listdir("media-downloads/" + util.get_platform(url) + "/" + util.get_platform_video_id(url))
        if f.startswith(util.get_platform_video_id(url)) and (f.endswith(".webp") or f.endswith(".jpg") or f.endswith(".mp4"))
    ]

    # jpgs.sort()
    jpgs = util.naturally_sort_filenames(jpgs)
    file_objects = []
    medias = []

    for i, f in enumerate(jpgs):
        file_path = os.path.join("media-downloads/" + util.get_platform(url) + "/" + util.get_platform_video_id(url), f)
        photo_file = open(file_path, 'rb')
        file_objects.append(photo_file)

        if i == 0:
            if jpgs[i].endswith('.webp') or jpgs[i].endswith('.jpg'):
                file_id = bot.send_photo(PRIVATE_CHANNEL_ID, photo_file).photo[-1].file_id
                dbtools.add_photo(file_id, util.get_platform_video_id(url), util.get_platform(url))

                medias.append(
                    InputMediaPhoto(file_id, caption="Here's your [media](" + url + ") >w<",
                                    parse_mode="Markdown"))
            else:
                file_id = bot.send_video(PRIVATE_CHANNEL_ID, photo_file).video.file_id
                dbtools.add_video(file_id, util.get_platform_video_id(url), util.get_platform(url))

                medias.append(
                    InputMediaVideo(file_id, caption="Here's your [media](" + url + ") >w<",
                                    parse_mode="Markdown"))

        elif i == 10:
            bot.send_media_group(chat_id=message.chat.id, media=medias, reply_to_message_id=message.message_id)
            medias = []
            if jpgs[i].endswith('.webp') or jpgs[i].endswith('.jpg'):
                file_id = bot.send_photo(PRIVATE_CHANNEL_ID, photo_file).photo[-1].file_id
                dbtools.add_photo(file_id, util.get_platform_video_id(url), util.get_platform(url))

                medias.append(InputMediaPhoto(file_id))
            else:
                file_id = bot.send_video(PRIVATE_CHANNEL_ID, photo_file).video.file_id
                dbtools.add_video(file_id, util.get_platform_video_id(url), util.get_platform(url))

                medias.append(InputMediaVideo(file_id))
        else:
            if jpgs[i].endswith('.webp') or jpgs[i].endswith('.jpg'):
                file_id = bot.send_photo(PRIVATE_CHANNEL_ID, photo_file).photo[-1].file_id
                dbtools.add_photo(file_id, util.get_platform_video_id(url), util.get_platform(url))

                medias.append(InputMediaPhoto(file_id))
            else:
                file_id = bot.send_video(PRIVATE_CHANNEL_ID, photo_file).video.file_id
                dbtools.add_video(file_id, util.get_platform_video_id(url), util.get_platform(url))

                medias.append(InputMediaVideo(file_id))

    bot.send_media_group(chat_id=message.chat.id, media=medias, reply_to_message_id=message.message_id)

    for file_obj in file_objects:
        file_obj.close()

    shutil.rmtree("media-downloads/" + util.get_platform(url) + "/" + util.get_platform_video_id(url))


bot.infinity_polling()
