import os
import textwrap
import urllib.error
import urllib.request
from telebot import TeleBot
from telebot.types import Message, ReactionTypeEmoji


def register_commands(bot: TeleBot, cube_toro_file_id: str):
    def start(message: Message):
        start_text: str = textwrap.dedent("""
            Hello!
            Thank you for choosing to use me :3

            Here are the platforms I support:
            - Youtube (up to 10 minutes)
            - Instagram
            - Tiktok
            - Twitter (X)
            - Reddit (supports only videos)
            - Danbooru
            - Safebooru
            - Bigrat.monster

            To download something just send the link to me and I'll take care of it, or just add me to a group and I'll download all of the links sent in the group.

            If you want to take a look at my terrible source code, you can do it here:
            https://github.com/neonsn0w/ToroDL

            <blockquote>ToroDL is maintained and hosted for free by a single person as a side project, expect breakage at all times.</blockquote> 
            """)

        bot.reply_to(message, start_text, parse_mode="HTML")

    def help_command(messsage: Message):
        help_text: str = textwrap.dedent("""
            To download videos, you just need to send a link to the bot or in a group the bot is part of, no need for commands!

            But if you *really* want some commands, here are some not-so-useful ones:
            - /cat - Get a random cat picture
            - /httpcat XXX - Remember the meaning of a specific HTTP code through cat pictures
            - /cube - Take a look at a beautiful fanart
            """)

        bot.reply_to(messsage, help_text, parse_mode="Markdown")

    def send_random_cat_pic(message: Message):
        """Sends a random cat picture using cataas.com"""

        urllib.request.urlretrieve("https://cataas.com/cat", "catpic.cat")
        with open("catpic.cat", "rb") as f:
            bot.send_photo(message.chat.id, f, reply_to_message_id=message.message_id)

        os.remove("catpic.cat")

    def send_cube_pic(message: Message):
        """Send a very cute fanart of Toro inside a Gamecube."""
        # Thank you lucabeagle510

        if cube_toro_file_id:
            bot.send_photo(message.chat.id, cube_toro_file_id,
                           caption="Art by https://www.instagram.com/lucabeagle510/\n\nThank you so much!",
                           reply_to_message_id=message.message_id)

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
                bot.set_message_reaction(message.chat.id, message.id, [ReactionTypeEmoji('👾')])
                bot.send_photo(message.chat.id, f, reply_to_message_id=message.message_id)
        else:
            with open("httpcat.tmp", "rb") as f:
                bot.send_photo(message.chat.id, f, reply_to_message_id=message.message_id,
                               caption="Unknown HTTP error code...")

        os.remove("httpcat.tmp")

    bot.register_message_handler(start, commands=['start'], chat_types=['private'])
    bot.register_message_handler(help_command, commands=['help', 'commands', 'command'], chat_types=['private'])
    bot.register_message_handler(send_random_cat_pic, commands=['cat'])
    bot.register_message_handler(send_cube_pic, commands=['cube'])
    bot.register_message_handler(send_httpcat_pic, commands=['httpcat'])
