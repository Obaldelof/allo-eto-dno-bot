import os
import logging
import feedparser
from random import choice
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv
import asyncio

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
ADD_IRONY = os.getenv("ADD_IRONY", "True") == "True"

bot = Bot(token=BOT_TOKEN)

irony_lines = [
    "Ну, как вам такое?",
    "Алло, это дно?",
    "Где мы и где логика?",
    "Без комментариев...",
    "🤡"
]

feeds = [
    "https://lenta.ru/rss",
    "https://meduza.io/rss/all",
    "https://ria.ru/export/rss2/archive/index.xml",
    "https://tass.ru/rss/v2.xml",
    "https://rssexport.rbc.ru/rbcnews/news/30/full.rss",
    "https://www.kommersant.ru/RSS/news.xml",
    "https://vc.ru/rss/all",
    "https://thebell.io/feed",
    "https://holod.media/feed/"
]

HISTORY_FILE = "last_news.txt"

def get_last_posted_links(limit=5):
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines()][-limit:]

def save_posted_link(link: str):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")

def fetch_news():
    last_links = get_last_posted_links()

    for url in feeds:
        d = feedparser.parse(url)
        if d.entries:
            for entry in d.entries:
                if entry.link not in last_links:
                    irony = choice(irony_lines)
                    message = (
                        f"🗞 <b>{entry.title}</b>\n\n"
                        f"{entry.summary}\n\n"
                        f"🔗 <a href='{entry.link}'>Читать полностью</a>\n\n"
                        f"<i>{irony}</i>\n\n"
                        "—\n"
                        "🤡 🤬 😱 🤔 ❤️\n\n"
                        "<a href='https://t.me/alloetodno'>Подписаться на канал</a>"
                    )
                    save_posted_link(entry.link)
                    return message

    return "Свежих новостей не найдено."

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = fetch_news()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, parse_mode="HTML")

async def scheduled_post():
    message = fetch_news()
    await bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode="HTML")

def start_scheduler(loop):
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: asyncio.run_coroutine_threadsafe(scheduled_post(), loop),
                      trigger=IntervalTrigger(minutes=1))
    scheduler.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("test", test_command))

    # запуск планировщика в контексте event loop
    loop = asyncio.get_event_loop()
    start_scheduler(loop)

    app.run_polling()
