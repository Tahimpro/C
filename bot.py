import requests
import threading
import logging
import re
from bs4 import BeautifulSoup
from flask import Flask
from pymongo import MongoClient
from time import sleep

# 🔹 Configuration
BOT_TOKEN = "7524524705:AAH7aBrV5cAZNRFIx3ZZhO72kbi4tjNd8lI"
CHAT_ID = "-1002340139937"
MONGO_URI = "mongodb+srv://FF:FF@cluster0.xpbvq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "skymovieshd"
COLLECTION_NAME = "seen_links"
BASE_URL = "https://skymovieshd.video"
CATEGORY_URL = f"{BASE_URL}/category/Bengali-Movies.html"
INTERVAL = 180  # Time in seconds

# 🔹 Logger Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 🔹 Flask App (Health Check for Koyeb)
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

# 🔹 MongoDB Connection
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# 🔹 Telegram Message Function
def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        logging.info(f"Sent message: {text}")
    except Exception as e:
        logging.error(f"Failed to send message: {e}")

# 🔹 Scraper Function
def scrape_posts():
    try:
        logging.info("Checking for new posts...")
        response = requests.get(CATEGORY_URL)
        soup = BeautifulSoup(response.text, "html.parser")

        # Find movie post links
        movie_links = [a["href"] for a in soup.find_all("a", href=True) if "/movie/" in a["href"]]

        for link in movie_links:
            if not collection.find_one({"link": link}):
                collection.insert_one({"link": link})
                full_url = f"{BASE_URL}{link}"

                # Extract `howblogs.xyz` links
                howblogs_links = extract_howblogs_links(full_url)

                # Extract Gofile.io & Streamtape.to links
                for howblogs_link in howblogs_links:
                    download_links = extract_download_links(howblogs_link)
                    if download_links:
                        movie_name = extract_movie_name(full_url)
                        for dl_link in download_links:
                            send_message(f"🌟 {movie_name} {dl_link}")

        logging.info("Scraping complete.")
    except Exception as e:
        logging.error(f"Scraping error: {e}")

# 🔹 Extract `howblogs.xyz` Links
def extract_howblogs_links(movie_url):
    try:
        response = requests.get(movie_url)
        soup = BeautifulSoup(response.text, "html.parser")

        howblogs_links = [a["href"] for a in soup.find_all("a", href=True) if "howblogs.xyz" in a["href"]]
        return howblogs_links

    except Exception as e:
        logging.error(f"Error extracting howblogs.xyz links: {e}")
        return []

# 🔹 Extract Gofile.io & Streamtape.to Links
def extract_download_links(howblogs_url):
    try:
        response = requests.get(howblogs_url)
        soup = BeautifulSoup(response.text, "html.parser")

        download_links = [a["href"] for a in soup.find_all("a", href=True) if "gofile.io" in a["href"] or "streamtape.to" in a["href"]]
        return download_links

    except Exception as e:
        logging.error(f"Error extracting download links: {e}")
        return []

# 🔹 Extract Movie Name
def extract_movie_name(movie_url):
    try:
        match = re.search(r"/movie/([^/]+)", movie_url)
        if match:
            movie_name = match.group(1).replace("-", " ")
            return movie_name
        return "Unknown Movie"
    except Exception as e:
        logging.error(f"Error extracting movie name: {e}")
        return "Unknown Movie"

# 🔹 Fetch Old Posts If No New Posts Found
def fetch_old_posts():
    logging.info("Fetching old posts...")
    for page in range(1, 196):
        page_url = f"{BASE_URL}/category/Bengali-Movies/{page}.html"
        try:
            response = requests.get(page_url)
            soup = BeautifulSoup(response.text, "html.parser")
            movie_links = [a["href"] for a in soup.find_all("a", href=True) if "/movie/" in a["href"]]

            for link in movie_links:
                full_url = f"{BASE_URL}{link}"
                movie_name = extract_movie_name(full_url)
                
                # Extract `howblogs.xyz` links
                howblogs_links = extract_howblogs_links(full_url)

                # Extract Gofile & Streamtape links
                for howblogs_link in howblogs_links:
                    download_links = extract_download_links(howblogs_link)
                    for dl_link in download_links:
                        send_message(f"🌟 {movie_name} {dl_link}")

                sleep(2)  # Prevent Telegram spam blocking

            return  # Stop after first batch of old posts

        except Exception as e:
            logging.error(f"Error fetching old posts: {e}")

# 🔹 Main Bot Loop
def start_bot():
    send_message("Bot restarted ✅")  # Notify restart
    while True:
        scrape_posts()
        sleep(INTERVAL)

# 🔹 Start Flask in a Thread
def run_flask():
    app.run(host="0.0.0.0", port=8080)

# 🔹 Start Bot & Flask Server
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    start_bot()
