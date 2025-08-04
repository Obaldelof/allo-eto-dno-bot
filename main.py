import os
import logging
import feedparser
from random import choice
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
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
    "https://meduza.io/rss/all"
]

def fetch_news():
    for url in feeds:
        d = feedparser.parse(url)
        if d.entries:
            entry = d.entries[0]
            message = f"<b>{entry.title}</b>\n\n{entry.summary}\n\nСсылка: {entry.link}"
            if ADD_IRONY:
                message += f"\n\n<i>{choice(irony_lines)}</i>"
            return message
    return "Новостей не найдено."

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = fetch_news()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, parse_mode="HTML")

async def scheduled_post():
    message = fetch_news()
    await bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode="HTML")

def run_async_job():
    asyncio.run(scheduled_post())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Планировщик
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_async_job, 'interval', minutes=1)
    scheduler.start()

    # Telegram App
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("test", test_command))
    app.run_polling()
