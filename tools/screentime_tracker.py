import time
import requests
import pygetwindow as gw
import logging

# Configuration
API_URL = "http://localhost:5001/api/screentime"
JWT_TOKEN = "YOUR_JWT_TOKEN_HERE"  # Get this from local storage in your browser
CHECK_INTERVAL = 60  # seconds

# List of distractive keywords
DISTRACTION_KEYWORDS = ["YouTube", "Netflix", "Facebook", "Instagram", "Reddit", "Game", "Steam"]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def get_active_window():
    try:
        window = gw.getActiveWindow()
        return window.title if window else "Unknown"
    except Exception:
        return "Unknown"

def send_update(seconds, is_screen_time=True):
    headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
    payload = {
        "active_seconds": 0 if is_screen_time else seconds,
        "screen_seconds": seconds if is_screen_time else 0
    }
    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        if response.status_code == 200:
            logging.info(f"Updated: {seconds}s usage synced.")
        else:
            logging.warning(f"Failed to sync: {response.text}")
    except Exception as e:
        logging.error(f"Error syncing: {e}")

def main():
    logging.info("Desktop Screen Time Tracker starting...")
    logging.info(f"Monitoring distractions: {DISTRACTION_KEYWORDS}")
    
    while True:
        time.sleep(CHECK_INTERVAL)
        title = get_active_window()
        is_distraction = any(kw.lower() in title.lower() for kw in DISTRACTION_KEYWORDS)
        
        if is_distraction:
            logging.info(f"Distraction detected: {title}")
            # In a real version, we'd send more data, but for now we sync usage.
            send_update(CHECK_INTERVAL, is_screen_time=True)
        else:
            logging.info(f"Focused on: {title}")

if __name__ == "__main__":
    main()
