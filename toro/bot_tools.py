import time

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_document_file_id(bot: telebot.TeleBot, file_path: str, private_channel_id: str) -> str:
    """Uploads a document file to the private channel to get a Telegram File ID."""
    with open(file_path, "rb") as f:
        return bot.send_document(private_channel_id, f).document.file_id


def get_photo_file_id(bot: telebot.TeleBot, file_path: str, private_channel_id: str) -> str:
    """Uploads a photo file to the private channel to get a Telegram File ID."""
    with open(file_path, "rb") as f:
        return bot.send_photo(private_channel_id, f).photo[-1].file_id


def send_status_msg(bot: telebot.TeleBot, message: telebot.types.Message,
                    downloading_gif_file_id: str) -> telebot.types.Message:
    return bot.send_document(chat_id=message.chat.id,
                             caption=">.< | Downloading...",
                             reply_to_message_id=message.message_id,
                             document=downloading_gif_file_id)


def send_too_big_msg(bot: telebot.TeleBot, message: telebot.types.Message,
                     sad_toro_file_id: str) -> telebot.types.Message:
    return bot.send_photo(chat_id=message.chat.id,
                          caption="*O.O | Too big!*",
                          reply_to_message_id=message.message_id,
                          parse_mode="Markdown",
                          photo=sad_toro_file_id)


def send_error_msg(bot: telebot.TeleBot, message: telebot.types.Message,
                   sad_toro_file_id: str) -> telebot.types.Message:
    return bot.send_photo(chat_id=message.chat.id,
                          caption="*(⋟﹏⋞) | Error downloading!*",
                          reply_to_message_id=message.message_id,
                          parse_mode="Markdown",
                          photo=sad_toro_file_id)


def safe_delete(bot: telebot.TeleBot, message: telebot.types.Message, delay: int = 0):
    if delay:
        time.sleep(delay)
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception as e:
        pass  # I'll take the gamble


def gen_spoiler_markup(enable_spoiler: bool = True):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    if enable_spoiler:
        markup.add(InlineKeyboardButton("Toggle Spoiler", callback_data="spoiler_1"))
    else:
        markup.add(InlineKeyboardButton("Toggle Spoiler", callback_data="spoiler_0"))

    return markup


def gen_spoiler_markup_with_audio(shortcode: str, enable_spoiler: bool = True):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    if enable_spoiler:
        markup.add(InlineKeyboardButton("Toggle Spoiler", callback_data="spoiler_1"),
                   InlineKeyboardButton("Download Audio", callback_data="a$" + shortcode))
    else:
        markup.add(InlineKeyboardButton("Toggle Spoiler", callback_data="spoiler_0"),
                   InlineKeyboardButton("Download Audio", callback_data="a$" + shortcode))

    return markup


def send_message_to_admin(bot: telebot.TeleBot, admin_user_id: str, message_contents: str):
    bot.send_message(admin_user_id, message_contents)
