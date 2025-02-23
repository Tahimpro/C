import aiohttp
import asyncio
import logging
import re
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup

# Directly set the values for your variables
TELEGRAM_BOT_TOKEN = '7524524705:AAH7aBrV5cAZNRFIx3ZZhO72kbi4tjNd8lI'
TELEGRAM_CHAT_ID = '-1002340139937'
BASE_URL = 'https://skymovieshd.video'  # Corrected to lowercase
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
    try:
        timeout = ClientTimeout(total=30)  # Set timeout to 30 seconds
        async with session.get(url, timeout=timeout) as response:
            return await response.text()
    except aiohttp.client_exceptions.ClientConnectorError as e:
        logging.error(f"Connection error while fetching {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred while fetching {url}: {e}")
        return None

async def scrape_latest_movies(session):
    url = f"{BASE_URL}"
    html = await fetch_html(session, url)
    if html:
        logging.info(f"Fetched HTML: {html[:500]}")  # Log first 500 characters to check structure
    else:
        logging.warning(f"Failed to fetch HTML from {BASE_URL}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    
    # Find "Latest Updated Movies" section
    latest_section = soup.find("div", class_="Robiul", text=re.compile("Latest Updated Movies"))
    if not latest_section:
        logging.warning("Couldn't find 'Latest Updated Movies' section.")
        return []

    movies = []
    for div in latest_section.find_all_next("div", class_="Fmvideo"):
        a_tag = div.find("a")
        if a_tag:
            movie_name = a_tag.text.strip()
            movie_link = BASE_URL + a_tag["href"]
            movies.append((movie_name, movie_link))

    return movies

async def extract_final_links(session, movie_name, movie_url):
    html = await fetch_html(session, movie_url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Find howblogs.xyz link
    external_link = None
    for a_tag in soup.find_all("a", href=True):
        if "howblogs.xyz" in a_tag["href"]:
            external_link = a_tag["href"]
            break

    if not external_link:
        logging.info(f"No howblogs.xyz link found for {movie_name}")
        return None

    # Visit howblogs.xyz and extract gofile.io or streamtape.to links
    html = await fetch_html(session, external_link)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    for a_tag in soup.find_all("a", href=True):
        if "gofile.io" in a_tag["href"] or "streamtape.to" in a_tag["href"]:
            return a_tag["href"]

    return None

async def send_telegram_message(movie_name, final_link):
    message = f"🌟 {movie_name} {final_link}"
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": message}

    async with aiohttp.ClientSession() as session:
        async with session.post(telegram_url, params=params) as response:
            if response.status == 200:
                logging.info(f"Sent to Telegram: {movie_name}")
            else:
                logging.error(f"Failed to send message: {await response.text()}")

async def main():
    global seen_links

    async with aiohttp.ClientSession() as session:
        logging.info("Bot restarted")
        # Send a bot restart message to Telegram
        await send_telegram_message("Bot", "Bot restarted")

        while True:
            logging.info("Checking for new movies...")
            movies = await scrape_latest_movies(session)

            for movie_name, movie_url in movies:
                if movie_url in seen_links:
                    continue

                final_link = await extract_final_links(session, movie_name, movie_url)
                if final_link:
                    await send_telegram_message(movie_name, final_link)
                    seen_links.add(movie_url)

            logging.info("Sleeping before next check...")
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
