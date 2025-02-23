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
    """Send message to Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        logging.info("Message sent successfully.")
    else:
        logging.error(f"Failed to send message: {response.text}")

def fetch_movie_links():
    """Fetch all movie post links from the category page."""
    try:
        response = requests.get(CATEGORY_URL, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            logging.error(f"Failed to fetch category page: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        links = []

        for post in soup.select("h2.entry-title a"):
            post_link = post["href"]
            if not collection.find_one({"url": post_link}):
                links.append(post_link)

        return links
    except Exception as e:
        logging.error(f"Error fetching movie links: {e}")
        return []

def extract_download_links(post_url):
    """Extract Gofile.io and Streamtape.to links from howblogs.xyz."""
    try:
        response = requests.get(post_url, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            logging.error(f"Failed to fetch post: {response.status_code}")
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

        # Fetch howblogs page
        response = requests.get(howblogs_link, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            logging.error(f"Failed to fetch howblogs.xyz: {response.status_code}")
            return None, None

        soup = BeautifulSoup(response.text, "html.parser")
        gofile_link = None
        streamtape_link = None

        for a in soup.find_all("a", href=True):
            if "gofile.io" in a["href"]:
                gofile_link = a["href"]
            if "streamtape.to" in a["href"]:
                streamtape_link = a["href"]

        return gofile_link, streamtape_link

    except Exception as e:
        logging.error(f"Error extracting links: {e}")
        return None, None

def process_movies():
    """Fetch movie posts, extract links, and send to Telegram."""
    while True:
        logging.info("Fetching movie posts...")
        movie_links = fetch_movie_links()

        for link in movie_links:
            movie_name = link.split("/")[-1].replace("-", " ").replace(".html", "")
            gofile, streamtape = extract_download_links(link)

            if gofile or streamtape:
                message = f"⭐ *{movie_name}*"
                if gofile:
                    message += f"\n🔗 [Gofile]({gofile})"
                if streamtape:
                    message += f"\n🔗 [Streamtape]({streamtape})"

                send_telegram_message(message)
                collection.insert_one({"url": link})

        logging.info("Sleeping for 1 minutes...")
        time.sleep(60)

# Run bot in a separate thread
threading.Thread(target=process_movies, daemon=True).start()

# Run Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
