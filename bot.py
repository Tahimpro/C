import requests
import logging
import time
import threading
from bs4 import BeautifulSoup
from flask import Flask
from pymongo import MongoClient

# Configuration
BOT_TOKEN = "7524524705:AAH7aBrV5cAZNRFIx3ZZhO72kbi4tjNd8lI"
CHAT_ID = "-1002340139937"
MONGO_URI = "mongodb+srv://FF:FF@cluster0.xpbvq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "skymovieshd"
COLLECTION_NAME = "seen_links"
BASE_URL = "https://skymovieshd.video"
CATEGORY_URL = "https://skymovieshd.video/category/Bengali-Movies.html"

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# MongoDB setup
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Flask app for uptime monitoring
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running."

def send_telegram_message(message):
    """Send message to Telegram with logging."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}

    try:
        response = requests.post(url, data=payload)
        logging.info(f"Telegram Response: {response.text}")
        return response.text
    except Exception as e:
        logging.error(f"Error sending message to Telegram: {e}")
        return None

def fetch_movie_links():
    """Fetch all movie post links from the category page."""
    try:
        logging.info(f"Fetching category page: {CATEGORY_URL}")
        response = requests.get(CATEGORY_URL, headers={"User-Agent": "Mozilla/5.0"})

        if response.status_code != 200:
            logging.error(f"Failed to fetch category page. Status Code: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        links = []

        for post in soup.select("h2.entry-title a"):
            post_link = post["href"]
            if not collection.find_one({"url": post_link}):
                links.append(post_link)

        logging.info(f"Found {len(links)} new posts.")
        return links

    except Exception as e:
        logging.error(f"Error fetching movie links: {e}")
        return []

def extract_download_links(post_url):
    """Extract Gofile.io and Streamtape.to links from howblogs.xyz."""
    try:
        logging.info(f"Fetching post page: {post_url}")
        response = requests.get(post_url, headers={"User-Agent": "Mozilla/5.0"})

        if response.status_code != 200:
            logging.error(f"Failed to fetch post page. Status Code: {response.status_code}")
            return None, None

        soup = BeautifulSoup(response.text, "html.parser")
        howblogs_link = None

        for a in soup.find_all("a", href=True):
            if "howblogs.xyz" in a["href"]:
                howblogs_link = a["href"]
                break

        if not howblogs_link:
            logging.info("No howblogs.xyz link found.")
            return None, None

        logging.info(f"Found howblogs.xyz link: {howblogs_link}")

        # Fetch howblogs page
        response = requests.get(howblogs_link, headers={"User-Agent": "Mozilla/5.0"})

        if response.status_code != 200:
            logging.error(f"Failed to fetch howblogs.xyz page. Status Code: {response.status_code}")
            return None, None

        soup = BeautifulSoup(response.text, "html.parser")
        gofile_link = None
        streamtape_link = None

        for a in soup.find_all("a", href=True):
            if "gofile.io" in a["href"]:
                gofile_link = a["href"]
            if "streamtape.to" in a["href"]:
                streamtape_link = a["href"]

        logging.info(f"Extracted links - Gofile: {gofile_link}, Streamtape: {streamtape_link}")
        return gofile_link, streamtape_link

    except Exception as e:
        logging.error(f"Error extracting links: {e}")
        return None, None

def process_movies():
    """Fetch movie posts, extract links, and send to Telegram."""
    while True:
        logging.info("Fetching movie posts...")
        movie_links = fetch_movie_links()

        if not movie_links:
            logging.info("No new movie posts found.")
        else:
            logging.info(f"Processing {len(movie_links)} new posts...")

        for link in movie_links:
            movie_name = link.split("/")[-1].replace("-", " ").replace(".html", "")
            logging.info(f"Processing: {movie_name} ({link})")

            gofile, streamtape = extract_download_links(link)
            logging.info(f"Extracted Links - Gofile: {gofile}, Streamtape: {streamtape}")

            if gofile or streamtape:
                message = f"⭐ *{movie_name}*"
                if gofile:
                    message += f"\n🔗 [Gofile]({gofile})"
                if streamtape:
                    message += f"\n🔗 [Streamtape]({streamtape})"

                response = send_telegram_message(message)
                logging.info(f"Telegram Message Sent: {response}")

                collection.insert_one({"url": link})
                logging.info(f"Inserted {link} into MongoDB.")

            else:
                logging.info(f"No valid download links found for {movie_name}.")

        logging.info("Sleeping for 10 minutes...")
        time.sleep(600)

# Run bot in a separate thread
threading.Thread(target=process_movies, daemon=True).start()

# Run Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
