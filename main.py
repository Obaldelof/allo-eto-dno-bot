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
import traceback

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
USE_IMAGES = os.getenv("USE_IMAGES", "True") == "True"

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
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
    draw.text((40, 180), title[:80] + ("..." if len(title) > 80 else ""), font=font, fill=(255, 255, 255))
    img.save("generated.jpg")

def extract_image(entry_soup):
    # 1. media:content
    media = entry_soup.find("media:content")
    if media and media.get("url"):
        return media["url"]

    # 2. enclosure
    enclosure = entry_soup.find("enclosure")
    if enclosure and enclosure.get("url"):
        return enclosure["url"]

    # 3. img inside description
    description = entry_soup.find("description")
    if description:
        soup = BeautifulSoup(description.text, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]

    # 4. img inside content:encoded
    content = entry_soup.find("content:encoded")
    if content:
        soup = BeautifulSoup(content.text, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]

    return None

def extract_og_image(link):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(link, headers=headers, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Иногда og:image может быть записан через name вместо property
        og_img = soup.find('meta', attrs={"property": "og:image"}) or soup.find('meta', attrs={"name": "og:image"})

        if og_img and og_img.get("content"):
            return og_img["content"]

        # Альтернатива: взять первый img, если og:image нет
        img_tag = soup.find("img")
        if img_tag and img_tag.get("src"):
            return img_tag["src"]

    except Exception as e:
        print(f"[og:image error] {link}: {e}")

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
                soup = BeautifulSoup(data, "lxml-xml")

            items = soup.find_all("item")

            for item in items:
                title = item.title.text if item.title else "Без заголовка"
                link = item.link.text if item.link else ""
                description = item.description.text if item.description else ""
                pub_date_raw = item.pubDate.text if item.pubDate else None

                if link in last_links or not pub_date_raw or not description:
                    continue

                try:
                    entry_date = parsedate_to_datetime(pub_date_raw)
                    if (datetime.now(entry_date.tzinfo) - entry_date).total_seconds() > 1800:
                        continue  # Пропустить старые новости (старше 30 минут)
                except:
                    continue

                image_url = extract_image(item)
                if not image_url:
                    image_url = extract_og_image(link)

                candidates.append({
                    "title": title,
                    "summary": description,
                    "link": link,
                    "date": entry_date,
                    "image": image_url
                })

        except Exception as e:
            print(f"[feed error] {url}: {e}")
            traceback.print_exc()
            continue

    if candidates:
        chosen = choice(candidates)
        irony = choice(irony_lines)
        message = (
            f"☎️ <b>{chosen['title']}</b>\n\n
            
            "
            f"{chosen['summary']}\n\n
            
            "
            f"<i>{irony}</i>\n\n
            "            
            f"<a href='https://t.me/alloetodno'>Алло, это дно? Подпишите!</a>"
        )
        save_posted_link(chosen["link"])

        image_path = "generated.jpg"
        if USE_IMAGES:
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

        return message, image_path if USE_IMAGES else None

    return None, None


async def scheduled_post():
    message, image_path = fetch_news()
    if message:
        try:
            if USE_IMAGES and image_path:
                await bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=open(image_path, "rb"),
                    caption=message,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=message,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
        except Exception as e:
            print(f"[ERROR] {e}")
            traceback.print_exc()


async def background_news_loop():
    while True:
        await scheduled_post()
        await asyncio.sleep(60)

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message, image_path = fetch_news()
    if message:
        if USE_IMAGES and image_path:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=open(image_path, "rb"),
                caption=message,
                parse_mode="HTML"
            )
        else:
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
