import os
import logging
import feedparser
from random import choice
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADD_IRONY = os.getenv("ADD_IRONY", "True") == "True"

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

# Универсальный метод генерации сообщения
def get_news_message():
    for url in feeds:
        d = feedparser.parse(url)
        if d.entries:
            entry = d.entries[0]
            message = f"<b>{entry.title}</b>\n\n{entry.summary}\n\n🔗 {entry.link}"
            if ADD_IRONY:
                message += f"\n\n<i>{choice(irony_lines)}</i>"
            return message
    return "🤷‍♂️ Не удалось получить новости."

# Отправка в канал
async def post_news_to_channel():
    message = get_news_message()
    await app.bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode="HTML")

# Обработчик команды /test
async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = get_news_message()
    await update.message.reply_text(message, parse_mode="HTML")

# Инициализация
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Планировщик для авто-публикации
scheduler = BackgroundScheduler()
scheduler.add_job(lambda: app.create_task(post_news_to_channel()), 'interval', minutes=30)
scheduler.start()

# Команды
app.add_handler(CommandHandler("test", test_command))

# Старт
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run_polling()
