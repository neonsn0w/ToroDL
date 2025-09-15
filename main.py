import os
import platform
import time

import telebot
from dotenv import load_dotenv

import toolbox as util

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

print("Bot running on " + platform.platform())

if platform.system() == "Linux":
    os.system("rm *.mp4")


@bot.message_handler(commands=['start'])
def start(message):
    if os.path.exists("huh-toro.jpg"):
        with open("huh-toro.jpg", "rb") as f:
            bot.send_photo(message.chat.id, f, reply_to_message_id=message.message_id)


@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    if "bigrat.monster" in message.text:
        if os.path.exists("bigrat.jpg"):
            with open("bigrat.jpg", "rb") as f:
                bot.send_photo(message.chat.id, f, reply_to_message_id=message.message_id)

        return

    if "https://" in message.text:
        url = util.extract_https_url(message.text)
        if util.is_supported_website(url):
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
                bot.edit_message_text("*ᇂ_ᇂ | Error downloading!*", chat_id=message.chat.id,
                                      message_id=sent_msg.message_id, parse_mode="Markdown")
                time.sleep(3)
                bot.delete_message(sent_msg.chat.id, sent_msg.message_id)
                return

            if filename and os.path.exists(filename):
                if util.is_file_smaller_than_50mb(filename):
                    try:
                        bot.edit_message_text("=w= Uploading...", chat_id=message.chat.id,
                                              message_id=sent_msg.message_id)

                        with open(filename, 'rb') as video_file:
                            bot.send_video(
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


bot.infinity_polling()
