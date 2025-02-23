import requests
import threading
import logging
from bs4 import BeautifulSoup
from flask import Flask
from pymongo import MongoClient
from time import sleep

# 🔹 User Credentials & Configurations
BOT_TOKEN = "7524524705:AAH7aBrV5cAZNRFIx3ZZhO72kbi4tjNd8lI"
CHAT_ID = "-1002340139937"
MONGO_URI = "mongodb+srv://FF:FF@cluster0.xpbvq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "skymovieshd"
COLLECTION_NAME = "seen_links"
BASE_URL = "https://skymovieshd.video"
CATEGORY_URL = "https://skymovieshd.video/category/Bengali-Movies.html"
INTERVAL = 180  # Time in seconds

# 🔹 Setup Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 🔹 Flask App for Koyeb Health Check
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

# 🔹 MongoDB Connection
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# 🔹 Function to Send Telegram Message
def send_message_sync(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        logging.info(f"Sent message: {text}")
    except Exception as e:
        logging.error(f"Failed to send message: {e}")

def send_telegram_message(text):
    threading.Thread(target=send_message_sync, args=(text,)).start()

# 🔹 Extract Download Links from HowBlogs.xyz
def extract_download_links(howblogs_url):
    try:
        response = requests.get(howblogs_url)
        soup = BeautifulSoup(response.text, "html.parser")
        
        gofile_link = None
        streamtape_link = None

        # Find all links
        for a in soup.find_all("a", href=True):
            if "gofile.io" in a["href"]:
                gofile_link = a["href"]
            elif "streamtape.to" in a["href"]:
                streamtape_link = a["href"]

        return gofile_link, streamtape_link

    except Exception as e:
        logging.error(f"Failed to extract links from {howblogs_url}: {e}")
        return None, None

# 🔹 Scrape Latest Posts
def scrape_posts():
    try:
        logging.info("Checking for new posts...")
        response = requests.get(CATEGORY_URL)
        soup = BeautifulSoup(response.text, "html.parser")

        # Find movie post links
        movie_links = [a["href"] for a in soup.find_all("a", href=True) if "/movie/" in a["href"]]

        new_posts = []
        for link in movie_links:
            full_link = BASE_URL + link

            if not collection.find_one({"link": full_link}):
                # Mark as seen in MongoDB
                collection.insert_one({"link": full_link})
                
                # Extract howblogs.xyz link
                post_response = requests.get(full_link)
                post_soup = BeautifulSoup(post_response.text, "html.parser")
                
                howblogs_link = None
                for a in post_soup.find_all("a", href=True):
                    if "howblogs.xyz" in a["href"]:
                        howblogs_link = a["href"]
                        break  # Take the first found link

                if howblogs_link:
                    gofile, streamtape = extract_download_links(howblogs_link)
                    if gofile or streamtape:
                        message = f"🌟 {link}\n"
                        if gofile:
                            message += f"📥 Gofile: {gofile}\n"
                        if streamtape:
                            message += f"📥 Streamtape: {streamtape}\n"
                        send_telegram_message(message)
                        new_posts.append(message)
                else:
                    logging.warning(f"No howblogs.xyz link found for {full_link}")

        if not new_posts:
            logging.info("No new posts found, fetching old posts...")
            fetch_old_posts()

    except Exception as e:
        logging.error(f"Scraping error: {e}")

# 🔹 Fetch Old Posts If No New Posts Found
def fetch_old_posts():
    for page in range(1, 196):
        page_url = f"{BASE_URL}/category/Bengali-Movies/{page}.html"
        try:
            response = requests.get(page_url)
            soup = BeautifulSoup(response.text, "html.parser")
            movie_links = [a["href"] for a in soup.find_all("a", href=True) if "/movie/" in a["href"]]

            for link in movie_links:
                send_telegram_message(f"🌟 {link}")
                sleep(2)  # Prevent Telegram spam blocking

            return  # Exit after sending first batch

        except Exception as e:
            logging.error(f"Error fetching old posts: {e}")

# 🔹 Main Loop
def start_bot():
    send_telegram_message("Bot restarted ✅")  # Notify restart
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
