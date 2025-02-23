import aiohttp
import asyncio
import logging
from bs4 import BeautifulSoup

# Directly set the values for your variables
TELEGRAM_BOT_TOKEN = '7524524705:AAH7aBrV5cAZNRFIx3ZZhO72kbi4tjNd8lI'
TELEGRAM_CHAT_ID = '-1002340139937'
BASE_URL = 'https://skymovieshd.video/movie'
CHECK_INTERVAL = 180  # Check every 3 minutes

# Ensure all required variables are set
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID or not BASE_URL:
    logging.error("Missing required variables: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, BASE_URL.")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Storage for seen links
seen_links = set()

async def fetch_html(session, url):
    async with session.get(url) as response:
        return await response.text()

async def scrape_post_links(session):
    html = await fetch_html(session, BASE_URL)
    soup = BeautifulSoup(html, "html.parser")

    # Find all post links
    post_links = []
    for a_tag in soup.find_all("a", href=True):
        post_url = a_tag['href']
        if 'howblogs.xyz' in post_url:
            post_links.append(post_url)
    return post_links

async def scrape_download_links(session, post_url):
    html = await fetch_html(session, post_url)
    soup = BeautifulSoup(html, "html.parser")

    # Find download links
    download_links = []
    for a_tag in soup.find_all("a", href=True):
        link = a_tag['href']
        if 'gofile.io' in link or 'streamtape.to' in link:
            download_links.append(link)
    return download_links

async def send_telegram_message(message):
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": message}

    async with aiohttp.ClientSession() as session:
        async with session.post(telegram_url, params=params) as response:
            if response.status == 200:
                logging.info("Sent to Telegram.")
            else:
                logging.error(f"Failed to send message: {await response.text()}")

async def main():
    global seen_links

    async with aiohttp.ClientSession() as session:
        logging.info("Bot restarted")
        # Send a bot restart message to Telegram
        await send_telegram_message("Bot restarted")

        while True:
            logging.info("Checking for new posts...")
            post_links = await scrape_post_links(session)

            for post_url in post_links:
                if post_url not in seen_links:
                    logging.info(f"New post found: {post_url}")
                    download_links = await scrape_download_links(session, post_url)

                    for link in download_links:
                        message = f"⚡ {link}\n📺 {post_url}"
                        await send_telegram_message(message)

                    seen_links.add(post_url)

            logging.info(f"Sleeping for {CHECK_INTERVAL} seconds before next check...")
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
