import aiohttp
import asyncio
import logging
import re
from bs4 import BeautifulSoup

# Directly set the values for your variables
TELEGRAM_BOT_TOKEN = '7524524705:AAH7aBrV5cAZNRFIx3ZZhO72kbi4tjNd8lI'
TELEGRAM_CHAT_ID = '-1002340139937'
BASE_URL = 'https://skymovieshd.video/movie'  # Corrected base URL for movie links
CHECK_INTERVAL = 180  # Default to 180 seconds if not set

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

async def find_howblogs_link(session, post_url):
    html = await fetch_html(session, post_url)
    soup = BeautifulSoup(html, "html.parser")

    # Find the howblogs.xyz link
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "howblogs.xyz" in href:
            return href
    return None

async def find_external_links(session, howblogs_url):
    html = await fetch_html(session, howblogs_url)
    soup = BeautifulSoup(html, "html.parser")

    # Look for gofile.io or streamtape.to links
    external_links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "gofile.io" in href or "streamtape.to" in href:
            external_links.append(href)

    return external_links

async def send_telegram_message(link, post_name):
    message = f"⚡ {link}\n📺 {post_name}"
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": message}

    async with aiohttp.ClientSession() as session:
        async with session.post(telegram_url, params=params) as response:
            if response.status == 200:
                logging.info(f"Sent to Telegram: {link}")
            else:
                logging.error(f"Failed to send message: {await response.text()}")

async def scrape_latest_posts(session):
    url = f"{BASE_URL}"  # The page containing all the movie links
    html = await fetch_html(session, url)
    soup = BeautifulSoup(html, "html.parser")

    # Find all the movie post links
    post_links = []
    for div in soup.find_all("div", class_="Fmvideo"):
        a_tag = div.find("a")
        if a_tag:
            post_name = a_tag.text.strip()
            post_link = BASE_URL + a_tag["href"]  # Full post URL
            if post_link not in seen_links:  # Avoid duplicate processing
                post_links.append((post_name, post_link))

    return post_links

async def main():
    global seen_links

    async with aiohttp.ClientSession() as session:
        logging.info("Bot restarted")
        # Send a bot restart message to Telegram
        await send_telegram_message("Bot restarted", "Bot restarted")

        while True:
            logging.info("Checking for new posts...")
            posts = await scrape_latest_posts(session)

            for post_name, post_url in posts:
                # Mark the post as seen
                seen_links.add(post_url)
                
                # Find the howblogs.xyz link in the post
                howblogs_link = await find_howblogs_link(session, post_url)
                if howblogs_link:
                    logging.info(f"Found howblogs.xyz link: {howblogs_link}")
                    
                    # Find external links (gofile.io or streamtape.to) in the howblogs link
                    external_links = await find_external_links(session, howblogs_link)
                    for link in external_links:
                        await send_telegram_message(link, post_name)

            logging.info("Sleeping before next check...")
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
