import glob
import os
import platform
import time

import telebot
import yt_dlp
from dotenv import load_dotenv
from telebot.types import InputMediaPhoto, InlineQueryResultPhoto, InlineQueryResultVideo

import dbtools
import toolbox as util

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PRIVATE_CHANNEL_ID = os.getenv("PRIVATE_CHANNEL_ID")

bot = telebot.TeleBot(BOT_TOKEN)

dbtools.prepare_db()  # Creates the DB if not present

print("Bot running on " + platform.platform())
print("Using yt-dlp: " + yt_dlp.version.__version__)

if platform.system() == "Linux":
    os.system("rm *.mp4")


@bot.inline_handler(lambda query: True)
def inline_handler(query):
    results = []
    if "bigrat.monster" in query.query:
        if os.path.exists("img/bigrat.jpg"):
            with open("img/bigrat.jpg", "rb") as f:
                photoinfo = bot.send_photo(PRIVATE_CHANNEL_ID, f)

            results.append(InlineQueryResultPhoto(
                id=query.from_user.id,
                title="big rat",
                photo_url=photoinfo.photo[-1].file_id,
                thumbnail_url=photoinfo.photo[0].file_id
            ))

    if query.query.lower() == "huh":
        if os.path.exists("img/huh-toro.jpg"):
            with open("img/huh-toro.jpg", "rb") as f:
                photoinfo = bot.send_photo(PRIVATE_CHANNEL_ID, f)

            results.append(InlineQueryResultPhoto(
                id=query.from_user.id,
                title="huh",
                photo_url=photoinfo.photo[-1].file_id,
                thumbnail_url=photoinfo.photo[0].file_id
            ))

    if "https://" in query.query:
        url = util.extract_https_url(query.query)
        if util.is_supported_website(url):
            if dbtools.check_if_video_is_present(util.get_platform_video_id(url)):
                results.append(InlineQueryResultVideo(
                    id=query.from_user.id,
                    video_url=dbtools.get_video(util.get_platform_video_id(url)),
                    title="video",
                    mime_type="video/mp4",
                    caption="Here's your [video](" + url + ") >w<",
                    thumbnail_url="AgACAgQAAxkDAAIFpGjJ1FpfMEjVL5lLpI4wUPGmYMnfAAIQxjEbl_5RUvHasvEQXWLnAQADAgADeAADNgQ",
                    parse_mode="Markdown"
                ))

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

            try:
                if "youtube.com" in url or "youtu.be" in url:
                    if util.is_video_longer_than(url, 120):
                        util.download_video_720(url, filename)
                    else:
                        util.download_video(url, filename)
                else:
                    util.download_video(url, filename)
            except Exception as e:
                print(e)
                return

            if filename and os.path.exists(filename):
                if util.is_file_smaller_than_50mb(filename):
                    try:
                        with open(filename, 'rb') as video_file:
                            response = bot.send_video(
                                chat_id=PRIVATE_CHANNEL_ID,
                                video=video_file,
                                supports_streaming=True
                            )

                        results.append(InlineQueryResultVideo(
                            id=query.from_user.id,
                            video_url=response.video.file_id,
                            title="video",
                            mime_type="video/mp4",
                            caption="Here's your [video](" + url + ") >w<",
                            thumbnail_url="",
                            parse_mode="Markdown"
                        ))

                        dbtools.add_video(response.video.file_id, util.get_platform_video_id(url))

                        os.remove(filename)
                    except Exception as e:
                        print(e)
                        return

    if len(results) > 0:
        bot.answer_inline_query(query.id, results)


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
        if util.is_supported_website(url):
            if dbtools.check_if_video_is_present(util.get_platform_video_id(url)):
                bot.send_video(
                    chat_id=message.chat.id,
                    video=dbtools.get_video(util.get_platform_video_id(url)),
                    supports_streaming=True,
                    caption="Here's your [video](" + url + ") >w<",
                    parse_mode="Markdown",
                    reply_to_message_id=message.message_id
                )

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

            try:
                if "youtube.com" in url or "youtu.be" in url:
                    if util.is_video_longer_than(url, 120):
                        util.download_video_720(url, filename)
                    else:
                        util.download_video(url, filename)
                else:
                    util.download_video(url, filename)
            except Exception as e:
                print(e)
                if "No video formats found" in str(e) and "instagram.com" in url:
                    bot.edit_message_text("*⇀‸↼ | Let's try with images...*", chat_id=message.chat.id,
                                          message_id=sent_msg.message_id, parse_mode="Markdown")
                    try:
                        ig_img_routine(message, url)
                        bot.delete_message(sent_msg.chat.id, sent_msg.message_id)
                        return

                    except Exception as e:
                        print(e)
                        bot.edit_message_text("*ᇂ_ᇂ | Error downloading!*", chat_id=message.chat.id,
                                              message_id=sent_msg.message_id, parse_mode="Markdown")
                        time.sleep(3)
                        bot.delete_message(sent_msg.chat.id, sent_msg.message_id)
                        return
                else:
                    if "18 years" in str(e):
                        bot.edit_message_text("*ᇂ_ᇂ | This video is age restricted!*", chat_id=message.chat.id,
                                              message_id=sent_msg.message_id, parse_mode="Markdown")
                    else:
                        bot.edit_message_text("*ᇂ_ᇂ | Error downloading!*", chat_id=message.chat.id,
                                              message_id=sent_msg.message_id, parse_mode="Markdown")
                    time.sleep(3)
                    bot.delete_message(sent_msg.chat.id, sent_msg.message_id)
                    return

            if filename and os.path.exists(filename):
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

                        dbtools.add_video(response.video.file_id, util.get_platform_video_id(url))

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
                if "instagram.com" in url:
                    bot.edit_message_text("*⇀‸↼ | Let's try with images...*", chat_id=message.chat.id,
                                          message_id=sent_msg.message_id, parse_mode="Markdown")
                    try:
                        ig_img_routine(message, url)
                        bot.delete_message(sent_msg.chat.id, sent_msg.message_id)
                        return

                    except Exception as e:
                        print(e)
                        bot.edit_message_text("*ᇂ_ᇂ | Error downloading!*", chat_id=message.chat.id,
                                              message_id=sent_msg.message_id, parse_mode="Markdown")
                        time.sleep(3)
                        bot.delete_message(sent_msg.chat.id, sent_msg.message_id)
                        return
                else:
                    bot.edit_message_text("*╥﹏╥ | Error downloading!*", chat_id=message.chat.id,
                                          message_id=sent_msg.message_id, parse_mode="Markdown")
                    time.sleep(3)
                    bot.delete_message(sent_msg.chat.id, sent_msg.message_id)


def ig_img_routine(message, url):
    util.download_ig_pics(url, "ig_img_dl")

    jpgs = [
        f for f in os.listdir("ig_img_dl")
        if f.startswith(util.get_ig_video_id(url)) and f.lower().endswith('.jpg')
    ]

    jpgs.sort()
    file_objects = []
    medias = []

    for i, f in enumerate(jpgs):
        file_path = os.path.join("ig_img_dl", f)
        photo_file = open(file_path, 'rb')
        file_objects.append(photo_file)
        if i == 0:
            medias.append(
                InputMediaPhoto(photo_file, caption="Here's your [photo(s)](" + url + ") >w<", parse_mode="Markdown"))
        elif i == 10:
            bot.send_media_group(chat_id=message.chat.id, media=medias, reply_to_message_id=message.message_id)
            medias = []
            medias.append(InputMediaPhoto(photo_file))
        else:
            medias.append(InputMediaPhoto(photo_file))

    bot.send_media_group(chat_id=message.chat.id, media=medias, reply_to_message_id=message.message_id)

    for file_obj in file_objects:
        file_obj.close()

    for filename in glob.glob("ig_img_dl/" + util.get_ig_video_id(url) + "*"):
        os.remove(filename)
    return


bot.infinity_polling()
