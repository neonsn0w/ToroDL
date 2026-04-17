import telebot


def get_document_file_id(bot: telebot.TeleBot, file_path: str, private_channel_id: str) -> str:
    """Uploads a photo file to the private channel to get a Telegram File ID."""
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
