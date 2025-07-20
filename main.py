# ==============================================================================
# AJIO STOCK CHECKER TELEGRAM BOT (v8 - Final)
# ==============================================================================
#
# DESCRIPTION:
# This bot monitors specified Ajio product pages for a target shoe size.
# It uses ScraperAPI to render the JavaScript-heavy page, then intelligently
# finds and parses the product data embedded within the page's HTML.
#
# WHAT'S NEW (v8):
# - SIMPLIFIED STRATEGY: The script no longer searches for the product by its
#   code. Instead, it performs a single, direct search across the entire
#   page's data for a list that looks like size options. This is the most
#   resilient method yet against website changes.
# - Removed unnecessary functions for a cleaner codebase.
# - Corrected stock check logic to match Ajio's data structure.
#
# SETUP INSTRUCTIONS:
#
# 1. Install Required Libraries:
#    pip install pytelegrambotapi python-dotenv requests beautifulsoup4
#
# 2. Create a '.env' file in the same directory with your keys:
#    TELEGRAM_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
#    TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"
#    SCRAPERAPI_KEY="YOUR_SCRAPERAPI_KEY"
#
# 3. Configure the Bot below and run: python your_script_name.py
#
# ==============================================================================

import time
import telebot
import os
import requests
import json
import re
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# --- Load Environment Variables ---
load_dotenv()

# === CONFIG ===
PRODUCTS = [
    {
        "name": "Nike Initiator Black/Grey",
        "url": "https://www.ajio.com/nike-initiator-lace-up-running-shoes/p/469647549_blackgrey"
    },
    {
        "name": "Nike Initiator White",
        "url": "https://www.ajio.com/nike-men-initiator-running-shoes/p/469691390_white"
    }
]
TARGET_SIZE = '9'
CHECK_INTERVAL = 60 * 30  # 30 minutes

# --- Load Credentials ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
SCRAPERAPI_KEY = os.getenv('SCRAPERAPI_KEY')

# --- Basic Validation ---
if not all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, SCRAPERAPI_KEY]):
    print("FATAL ERROR: One or more environment variables are missing.")
    exit()

bot = telebot.TeleBot(TELEGRAM_TOKEN)


def sanitize_filename(name):
    """Removes invalid characters from a string to make it a valid filename."""
    return re.sub(r'[\\/*?:"<>|]', "_", name)


def find_size_options_list(data_blob):
    """
    Recursively finds the first list that looks like a size options list.
    We identify it as a list of dicts where the first dict has 'scDisplaySize'.
    """
    if isinstance(data_blob, list):
        if data_blob and isinstance(data_blob[0], dict) and 'scDisplaySize' in data_blob[0]:
            return data_blob
        for item in data_blob:
            found = find_size_options_list(item)
            if found is not None:
                return found
    elif isinstance(data_blob, dict):
        for value in data_blob.values():
            found = find_size_options_list(value)
            if found is not None:
                return found
    return None


def check_stock_html(session, product_url, product_name):
    """
    Checks stock by scraping the HTML and searching for the product data blob
    within a list of possible script tags (__NEXT_DATA__, __PRELOADED_STATE__, etc.).
    """
    print(f"  -> Trying Direct Search HTML method for {product_name}...")

    scraperapi_params = {'api_key': SCRAPERAPI_KEY, 'url': product_url, 'render': 'true'}
    try:
        response = session.get('https://api.scraperapi.com', params=scraperapi_params, timeout=120)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        data = None

        # --- NEW LOGIC: Try finding different script tags ---
        # 1. Try finding '__NEXT_DATA__'
        script_tag_next = soup.find('script', id='__NEXT_DATA__')
        if script_tag_next:
            print("  ℹ️  Found __NEXT_DATA__ script tag.")
            data = json.loads(script_tag_next.string)

        # 2. If that fails, try finding '__PRELOADED_STATE__'
        else:
            script_tag_preloaded = soup.find('script', string=lambda t: t and 'window.__PRELOADED_STATE__' in t)
            if script_tag_preloaded:
                print("  ℹ️  Found __PRELOADED_STATE__ script tag.")
                json_str = script_tag_preloaded.string.split('window.__PRELOADED_STATE__ = ')[1].strip().rstrip(';')
                data = json.loads(json_str)

        if not data:
            print(f"  ❌ HTML PARSE ERROR: Could not find a valid data script tag for {product_name}.")
            return None

        size_options = find_size_options_list(data)

        if not size_options:
            print(f"  ❌ HTML PARSE ERROR: Deep search failed to find a size options list for {product_name}.")
            sanitized_name = sanitize_filename(product_name)
            debug_filename = f'debug_data_blob_{sanitized_name}.json'
            with open(debug_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"  ℹ️  Saved full data blob to {debug_filename} for analysis.")
            return None

        available_sizes = {
            option['scDisplaySize']
            for option in size_options
            if option.get('stock', {}).get('stockLevelStatus') == 'inStock'
        }

        print(f"  📦 Sizes from HTML for {product_name}: {sorted(list(available_sizes))}")
        return TARGET_SIZE in available_sizes

    except requests.RequestException as e:
        print(f"  ❌ HTML FETCH ERROR for {product_name}: {e}")
        return None
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"  ❌ HTML PARSE ERROR for {product_name}: {e}")
        sanitized_name = sanitize_filename(product_name)
        debug_filename = f'debug_html_error_{sanitized_name}.html'
        with open(debug_filename, 'w', encoding='utf-8') as f:
            f.write(response.text if 'response' in locals() else 'No response object available.')
        print(f"  ℹ️  Saved error HTML to {debug_filename} for analysis. Error was: {e}")
        return None


def check_product(session, product):
    """Checks a single product for stock availability."""
    name = product["name"]
    url = product["url"]
    print(f"Checking '{name}' (Size: {TARGET_SIZE})...")

    is_in_stock = check_stock_html(session, url, name)

    if is_in_stock is True:
        print(f"  ✅ IN STOCK: '{name}' size {TARGET_SIZE} is available!")
        return f"✅ IN STOCK: {name} (Size {TARGET_SIZE})\n{url}"
    elif is_in_stock is False:
        print(f"  ❌ OUT OF STOCK: '{name}' size {TARGET_SIZE} is not available.")
        return f"❌ Out of Stock: {name} (Size {TARGET_SIZE})"
    else:
        print(f"  ⚠️ CHECK FAILED for '{name}'. Could not determine stock status.")
        return f"⚠️ Check Failed: Could not determine stock status for {name}."


def send_telegram_alert(message):
    """Sends a message to the configured Telegram chat."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message, disable_web_page_preview=True)
        print(f"✔️ Telegram alert sent successfully.")
    except Exception as e:
        print(f"❌ TELEGRAM ERROR: Failed to send message. Error: {e}")


if __name__ == '__main__':
    print("🤖 Bot started (v8 - Final). Initial check will run shortly.")
    send_telegram_alert("🤖 Bot is online and starting its first check cycle.")
    print("---")
    session = requests.Session()

    while True:
        print(f"--- Running stock check cycle at {time.ctime()} ---")
        try:
            in_stock_alerts = []

            for product in PRODUCTS:
                result_message = check_product(session, product)

                # Only send an alert if the product is IN STOCK
                if "IN STOCK" in result_message:
                    in_stock_alerts.append(result_message)

                # Optional: To get a status update even for OOS items, uncomment the next 2 lines
                # else:
                #     send_telegram_alert(result_message)

            if in_stock_alerts:
                alert_title = "🚨 STOCK ALERT! 🚨"
                full_alert = f"{alert_title}\n\n" + "\n\n".join(in_stock_alerts)
                send_telegram_alert(full_alert)

        except Exception as e:
            print(f"An unexpected error occurred in the main loop: {e}")
            send_telegram_alert(f"⚠️ BOT ERROR: The bot encountered an unexpected error: {e}")

        print(f"--- Check cycle complete. Waiting {CHECK_INTERVAL // 60} minutes for the next run. ---")
        time.sleep(CHECK_INTERVAL)