import os
import feedparser
import logging
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADD_IRONY = os.getenv("ADD_IRONY", "True") == "True"

bot = Bot(token=BOT_TOKEN)

def post_news():
    feeds = [
        "https://lenta.ru/rss",
        "https://meduza.io/rss/all"
    ]
    irony_lines = [
        "Ну, как вам такое?",
        "Алло, это дно?",
        "Где мы и где логика?",
        "Без комментариев...",
        "🤡"
    ]
    for url in feeds:
        d = feedparser.parse(url)
        if d.entries:
            entry = d.entries[0]
            message = f"<b>{entry.title}</b>\n\n{entry.summary}\n\nСсылка: {entry.link}"
            if ADD_IRONY:
                from random import choice
                message += f"\n\n<i>{choice(irony_lines)}</i>"
            try:
                bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode=ParseMode.HTML)
            except TelegramError as e:
                print(f"Ошибка отправки: {e}")
            break

scheduler = BlockingScheduler()
scheduler.add_job(post_news, 'interval', minutes=30)

logging.basicConfig(level=logging.INFO)
scheduler.start()
