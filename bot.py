import aiohttp
import asyncio
import logging
from bs4 import BeautifulSoup
import pymongo
from pymongo import MongoClient
from urllib.parse import urljoin

# Direct configuration values
TELEGRAM_BOT_TOKEN = '7524524705:AAH7aBrV5cAZNRFIx3ZZhO72kbi4tjNd8lI'
TELEGRAM_CHAT_ID = '-1002340139937'
BASE_URL = 'https://skymovieshd.video'
CHECK_INTERVAL = 180  # Check every 3 minutes

# MongoDB Configuration
MONGODB_URI = "mongodb+srv://FF:FF@cluster0.xpbvq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "skymovieshd"
COLLECTION_NAME = "seen_links"

# Ensure all required values are set
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID or not BASE_URL:
    logging.error("Missing required environment variables.")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Connect to MongoDB
client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Load seen links from MongoDB
seen_links = {entry['url'] for entry in collection.find({}, {"_id": 0, "url": 1})}

async def fetch_html(session, url):
    """Fetches HTML content of a URL."""
    try:
        async with session.get(url) as response:
            return await response.text()
    except Exception as e:
        logging.error(f"Failed to fetch {url}: {e}")
        return None

async def scrape_post_links(session):
    """Scrapes movie post links from the homepage."""
    html = await fetch_html(session, BASE_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    post_links = set()

    for a_tag in soup.find_all("a", href=True):
        post_url = a_tag['href']
        if '/movie/' in post_url:
            full_post_url = urljoin(BASE_URL, post_url)  # Ensures correct URL
            post_links.add(full_post_url)

    return list(post_links)

async def extract_howblogs_link(session, post_url):
    """Extracts howblogs.xyz link from the movie post page."""
    html = await fetch_html(session, post_url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    for a_tag in soup.find_all("a", href=True):
        if "howblogs.xyz" in a_tag['href']:
            return a_tag['href']
    return None

async def scrape_download_links(session, howblogs_url):
    """Scrapes Gofile and Streamtape links from howblogs.xyz."""
    html = await fetch_html(session, howblogs_url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    download_links = []

    for a_tag in soup.find_all("a", href=True):
        link = a_tag['href']
        if 'gofile.io' in link or 'streamtape.to' in link:
            download_links.append(link)

    return download_links

async def send_telegram_message(message):
    """Sends a message to the Telegram channel."""
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": message}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(telegram_url, params=params) as response:
                if response.status == 200:
                    logging.info("Message sent to Telegram.")
                else:
                    logging.error(f"Failed to send message: {await response.text()}")
        except Exception as e:
            logging.error(f"Error sending message: {e}")

async def save_seen_links():
    """Saves new seen links to MongoDB."""
    new_links = [{"url": link} for link in seen_links if not collection.find_one({"url": link})]
    if new_links:
        collection.insert_many(new_links)
        logging.info("Seen links saved to MongoDB.")

async def main():
    """Main scraping loop."""
    global seen_links

    async with aiohttp.ClientSession() as session:
        logging.info("Bot restarted")
        await send_telegram_message("Bot restarted")

        while True:
            logging.info("Checking for new posts...")
            post_links = await scrape_post_links(session)

            for post_url in post_links:
                if post_url not in seen_links:
                    logging.info(f"New post found: {post_url}")

                    # Extract howblogs.xyz link
                    howblogs_url = await extract_howblogs_link(session, post_url)
                    if howblogs_url:
                        logging.info(f"Found howblogs link: {howblogs_url}")

                        # Extract Gofile/Streamtape links
                        download_links = await scrape_download_links(session, howblogs_url)

                        for link in download_links:
                            message = f"🌟 {post_url}\n🔗 {link}"

                            logging.info(f"Sending: {message}")
                            await send_telegram_message(message)

                    seen_links.add(post_url)

            # Save seen links periodically
            await save_seen_links()

            logging.info(f"Sleeping for {CHECK_INTERVAL} seconds before next check...")
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
