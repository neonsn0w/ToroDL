import telebot
import os
from dotenv import load_dotenv
import time

import toolbox as util

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['migliorsistemaoperativo'])
def caccaos(message):
    bot.reply_to(message, "Il miglior sistema operativo è CasaOS")


@bot.message_handler(commands=['start'])
def start(message):
    if os.path.exists("huh-toro.jpg"):
        with open("huh-toro.jpg", "rb") as f:
            bot.send_photo(message.chat.id, f, reply_to_message_id=message.message_id)


@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    if "https://" in message.text:
        url = util.extract_https_url(message.text)
        if util.is_supported_website(url):
            if "youtube.com" in url or "youtu.be" in url:
                url = util.get_video_url(util.get_video_id(url))

                if util.is_video_longer_than_5m(url):
                    return

            sent_msg = bot.reply_to(message, ">.< | Downloading...")

            util.download_video(url)

            if "video.mp4" and os.path.exists("video.mp4"):
                if util.is_file_smaller_than_50mb("video.mp4"):
                    try:
                        bot.edit_message_text("=w= Uploading...", chat_id=message.chat.id,
                                              message_id=sent_msg.message_id)

                        with open("video.mp4", 'rb') as video_file:
                            bot.send_video(
                                chat_id=message.chat.id,
                                video=video_file,
                                supports_streaming=True,
                                caption="Here's your video >w<\n" + url,
                                reply_to_message_id=message.message_id
                            )

                        bot.delete_message(sent_msg.chat.id, sent_msg.message_id)
                        os.remove("video.mp4")
                    except Exception as e:
                        bot.edit_message_text("qmq | Error uploading!", chat_id=message.chat.id, message_id=sent_msg.message_id)
                        time.sleep(3)
                        bot.delete_message(sent_msg.chat.id, sent_msg.message_id)

                        os.remove("video.mp4")

                else:
                    bot.edit_message_text("O.O | Too big!", chat_id=message.chat.id, message_id=sent_msg.message_id)
                    time.sleep(3)
                    bot.delete_message(sent_msg.chat.id, sent_msg.message_id)

                    os.remove("video.mp4")

            else:
                bot.edit_message_text("qmq | Error downloading!", chat_id=message.chat.id, message_id=sent_msg.message_id)
                time.sleep(3)
                bot.delete_message(sent_msg.chat.id, sent_msg.message_id)

bot.infinity_polling()
