
import logging
import os
import feedparser
from telegram import Bot
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
            message = f"📰 <b>{entry.title}</b>"

{entry.summary}

🔗 {entry.link}"
            if ADD_IRONY:
                from random import choice
                message += f"

<i>{choice(irony_lines)}</i>"
            bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode="HTML")
            break

scheduler = BlockingScheduler()
scheduler.add_job(post_news, 'interval', minutes=30)
logging.basicConfig()
scheduler.start()
