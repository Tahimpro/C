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

async def scrape_latest_movies(session):
    url = f"{BASE_URL}"
    html = await fetch_html(session, url)
    soup = BeautifulSoup(html, "html.parser")

    # Find all movie links in the page using the structure provided
    movie_links = []
    for div in soup.find_all("div", class_="Fmvideo"):
        a_tag = div.find("a")
        if a_tag:
            movie_name = a_tag.text.strip()
            movie_link = BASE_URL + a_tag["href"]  # Full movie link
            if movie_link not in seen_links:  # Avoid sending duplicates
                movie_links.append((movie_name, movie_link))

    return movie_links

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
                # Avoid sending duplicates
                seen_links.add(movie_url)
                await send_telegram_message(movie_name, movie_url)

            logging.info("Sleeping before next check...")
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
