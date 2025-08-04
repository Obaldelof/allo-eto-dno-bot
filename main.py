import os
import logging
import feedparser
from random import choice
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
import asyncio
import datetime

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

from datetime import datetime
from email.utils import parsedate_to_datetime

from datetime import datetime
from email.utils import parsedate_to_datetime
import urllib.request
import random

def fetch_news():
    last_links = get_last_posted_links()
    candidates = []

    headers = {'User-Agent': 'Mozilla/5.0'}
    for url in feeds:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                data = response.read()
                d = feedparser.parse(data)

            print(f"🔍 Проверяю ленту: {url}")

            for entry in d.entries:
                link = entry.get("link", "")
                if link in last_links:
                    continue

                try:
                    if "published" in entry:
                        entry_date = parsedate_to_datetime(entry.published)
                    elif "updated" in entry:
                        entry_date = parsedate_to_datetime(entry.updated)
                    else:
                        print(f"⏭ Пропущена без даты: {entry.get('title', 'без названия')}")
                        continue
                except Exception as e:
                    print(f"⛔ Ошибка даты: {e}")
                    continue

                summary = entry.get("summary") or entry.get("description", "")
                if not summary:
                    print(f"⏭ Пропущена без описания: {entry.get('title', 'без названия')}")
                    continue

                candidates.append({
                    "title": entry.get("title", "Без заголовка"),
                    "summary": summary,
                    "link": link,
                    "date": entry_date,
                    "source": url
                })

        except Exception as e:
            print(f"❌ Ошибка в {url}: {e}")
            continue

    if candidates:
        chosen = random.choice(candidates)
        irony = choice(irony_lines)
        message = (
            f" <b>Алло, это дно?</b>\n\n"
            f"☎️ <b>{newest_entry['title']}</b>\n\n"
            f"{newest_entry['summary']}\n\n"
            f"<i>{irony}</i>\n\n"
            "—\n"
            "<a href='https://t.me/alloetodno'>Алло, это дно? Подпишите!</a>"
        )
        save_posted_link(chosen["link"])
        print(f"[{datetime.now()}] 🎲 Случайная новость: {chosen['title']} (из {chosen['source']})")
        return message

    print(f"[{datetime.now()}] ⏭ Новостей не найдено или все уже были.")
    return None


async def scheduled_post():
    print(f"[{datetime.now()}] ⏰ scheduled_post() вызван")
    message = fetch_news()
    if message:
        try:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=message,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            print(f"[{datetime.now()}] 📤 Новость отправлена в канал.")
        except Exception as e:
            print(f"[{datetime.now()}] ❌ Ошибка при отправке: {e}")
    else:
        print(f"[{datetime.now()}] ⏭ Нет новых новостей.")

async def background_news_loop():
    while True:
        await scheduled_post()
        await asyncio.sleep(60)

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = fetch_news()
    if message:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=message, 
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Нет новых новостей."
        )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("test", test_command))

    loop = asyncio.get_event_loop()
    loop.create_task(background_news_loop())

    app.run_polling()
