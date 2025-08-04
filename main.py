import os
import logging
import urllib.request
import requests
from bs4 import BeautifulSoup
from random import choice
from PIL import Image, ImageDraw, ImageFont
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update
from dotenv import load_dotenv
import asyncio
from datetime import datetime
from email.utils import parsedate_to_datetime

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

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

def generate_image(title):
    img = Image.new("RGB", (800, 400), color=(23, 29, 40))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    draw.text((40, 180), title[:80] + ("..." if len(title) > 80 else ""), font=font, fill=(255, 255, 255))
    img.save("generated.jpg")

def extract_image(entry):
    if "media_content" in entry:
        return entry.media_content[0].get("url")
    elif "enclosures" in entry and entry.enclosures:
        return entry.enclosures[0].get("href")
    elif "summary" in entry and "<img" in entry.summary:
        soup = BeautifulSoup(entry.summary, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]
    return None

def fetch_news():
    last_links = get_last_posted_links()
    candidates = []
    headers = {'User-Agent': 'Mozilla/5.0'}

    for url in feeds:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                data = response.read()
                import feedparser
                d = feedparser.parse(data)

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
                        continue
                except:
                    continue

                summary = entry.get("summary") or entry.get("description", "")
                if not summary:
                    continue

                candidates.append({
                    "title": entry.get("title", "Без заголовка"),
                    "summary": summary,
                    "link": link,
                    "date": entry_date,
                    "image": extract_image(entry)
                })
        except:
            continue

    if candidates:
        chosen = choice(candidates)
        irony = choice(irony_lines)
        message = (
            f" <b>Алло, это дно?</b>\n\n"
            f"☎️ <b>{chosen['title']}</b>\n\n"
            f"{chosen['summary']}\n\n"
            f"<i>{irony}</i>\n\n"
            "\u2014\n"
            "<a href='https://t.me/alloetodno'>Алло, это дно? Подпишите!</a>"
        )
        save_posted_link(chosen["link"])

        image_path = "generated.jpg"
        if chosen["image"]:
            try:
                img_data = requests.get(chosen["image"], timeout=5).content
                with open("temp.jpg", "wb") as handler:
                    handler.write(img_data)
                image_path = "temp.jpg"
            except:
                generate_image(chosen["title"])
        else:
            generate_image(chosen["title"])

        return message, image_path

    return None, None

async def scheduled_post():
    message, image_path = fetch_news()
    if message:
        try:
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=open(image_path, "rb"),
                caption=message,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"[ERROR] {e}")

async def background_news_loop():
    while True:
        await scheduled_post()
        await asyncio.sleep(60)

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message, image_path = fetch_news()
    if message:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=open(image_path, "rb"),
            caption=message,
            parse_mode="HTML"
        )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("test", test_command))

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(background_news_loop())

    app.run_polling()
