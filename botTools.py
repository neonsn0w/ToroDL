import telebot

def get_document_file_id(bot: telebot.TeleBot, file_path: str, private_channel_id: str) -> str:
    """Uploads a photo file to the private channel to get a Telegram File ID."""
    with open(file_path, "rb") as f:
        return bot.send_document(private_channel_id, f).document.file_id

def get_photo_file_id(bot: telebot.TeleBot, file_path: str, private_channel_id: str) -> str:
    """Uploads a photo file to the private channel to get a Telegram File ID."""
    with open(file_path, "rb") as f:
        return bot.send_photo(private_channel_id, f).photo[-1].file_id