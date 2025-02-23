import requests
import time
import random
import logging
import asyncio
from bs4 import BeautifulSoup
from pymongo import MongoClient
from telegram import Bot
from flask import Flask

# Logger setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Telegram Bot Config
TELEGRAM_BOT_TOKEN = "7524524705:AAH7aBrV5cAZNRFIx3ZZhO72kbi4tjNd8lI"
TELEGRAM_CHAT_ID = "-1002340139937"
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# MongoDB Config
MONGO_URI = "mongodb+srv://FF:FF@cluster0.xpbvq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "skymovieshd"
COLLECTION_NAME = "seen_links"
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Website URLs
BASE_URL = "https://skymovieshd.video"
BENGALI_CATEGORY_URL = "https://skymovieshd.video/category/Bengali-Movies.html"
BENGALI_PAGES = [f"https://skymovieshd.video/category/Bengali-Movies/{i}.html" for i in range(1, 196)]

# Flask app for Koyeb health check
app = Flask(__name__)

@app.route("/")
def health_check():
    return "Bot is running!", 200

def get_soup(url):
    """Fetches and parses HTML content."""
    try:
        response = requests.get(url, allow_redirects=False)
        return BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        logging.error(f"Failed to fetch {url}: {e}")
        return None

def extract_movie_links(soup):
    """Extracts movie post links from a page."""
    movie_links = []
    for link in soup.select('a[href*="/movie/"]'):
        post_url = link["href"]
        if not post_url.startswith("http"):
            post_url = BASE_URL + post_url
        movie_links.append(post_url)
    return movie_links

def extract_download_links(movie_url):
    """Extracts howblogs.xyz and direct download links from a movie post."""
    soup = get_soup(movie_url)
    if not soup:
        return None

    # Extract movie title
    title_section = soup.select('div[class^="Robiul"]')
    movie_title = title_section[-1].text.replace("Download ", "") if title_section else "Unknown Movie"

    message = f"<i>{movie_title}</i>"

    _cache = []
    for link in soup.select('a[href*="howblogs.xyz"]'):
        if link["href"] in _cache:
            continue
        _cache.append(link["href"])
        message += f"\n\n<b>{link.text} :</b> \n"

        nsoup = get_soup(link["href"])
        if not nsoup:
            continue

        atag = nsoup.select('div[class="cotent-box"] > a[href]')
        for no, link in enumerate(atag, start=1):
            message += f"{no}. {link['href']}\n"

    return message

def get_new_posts():
    """Finds new movie posts."""
    soup = get_soup(BENGALI_CATEGORY_URL)
    if not soup:
        return []

    new_posts = extract_movie_links(soup)
    return [post for post in new_posts if not collection.find_one({"link": post})]

def get_old_posts():
    """Fetches old posts from Bengali category pages."""
    random.shuffle(BENGALI_PAGES)  # Shuffle pages to avoid repetition
    for page_url in BENGALI_PAGES:
        soup = get_soup(page_url)
        if not soup:
            continue

        old_posts = extract_movie_links(soup)
        unseen_posts = [post for post in old_posts if not collection.find_one({"link": post})]

        if unseen_posts:
            return unseen_posts

    return []

def send_to_telegram(message):
    """Sends a formatted message to Telegram (proper async handling)."""
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="HTML"))
        logging.info("Message sent to Telegram")
        time.sleep(180)  # **Wait 3 minutes after each post**
    except Exception as e:
        logging.error(f"Failed to send message: {e}")

def bot_loop():
    """Main loop to fetch and send movie posts."""
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="🤖 Bot restarted!"))  # Notify bot restart
    except Exception as e:
        logging.error(f"Failed to send bot restart message: {e}")

    logging.info("Bot started!")

    while True:
        new_posts = get_new_posts()

        if new_posts:
            logging.info(f"Found {len(new_posts)} new posts!")
            for post_url in new_posts:
                message = extract_download_links(post_url)
                if message:
                    send_to_telegram(message)
                    collection.insert_one({"link": post_url})  # Mark as seen
        else:
            logging.info("No new posts found, fetching old posts...")
            old_posts = get_old_posts()

            if old_posts:
                for post_url in old_posts:
                    message = extract_download_links(post_url)
                    if message:
                        send_to_telegram(message)
                        collection.insert_one({"link": post_url})  # Mark as seen
            else:
                logging.warning("No old posts available!")

        time.sleep(180)  # Wait 3 minutes before the next cycle

if __name__ == "__main__":
    from threading import Thread
    # Start bot loop in a separate thread
    Thread(target=bot_loop, daemon=True).start()
    
    # Start Flask app for Koyeb health check
    app.run(host="0.0.0.0", port=8080)
