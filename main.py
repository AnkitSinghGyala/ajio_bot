import requests
from bs4 import BeautifulSoup
import time
import telebot
import os

# === CONFIG ===
PRODUCT_1_URL = 'https://www.ajio.com/nike-initiator-lace-up-running-shoes/p/469647549_blackgrey'
PRODUCT_1_NAME = 'Initiator 1'
PRODUCT_2_URL = 'https://www.ajio.com/nike-men-initiator-running-shoes/p/469691390_white?'
PRODUCT_2_NAME = 'Initiator 2'
TARGET_SIZE = 'UK 9'
CHECK_INTERVAL = 60 * 30  # every 30 minutes

# Load environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def check_stock(product_url, product_name):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(product_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    buttons = soup.find_all('button')
    for btn in buttons:
        text = btn.get_text(strip=True)
        if TARGET_SIZE in text and 'Out of Stock' not in text:
            return True
    return False

def send_telegram_alert(message):
    bot.send_message(TELEGRAM_CHAT_ID, message)
    print(f'✅ Telegram alert sent: {message}')

if __name__ == '__main__':
    while True:
        print('🔍 Checking stock...')
        try:
            status_messages = []

            for url, name in [(PRODUCT_1_URL, PRODUCT_1_NAME), (PRODUCT_2_URL, PRODUCT_2_NAME)]:
                if check_stock(url, name):
                    print(f'🎯 In stock: {name}')
                    status_messages.append(f'✅ {name} ({TARGET_SIZE}) is in stock!\n{url}')
                else:
                    print(f'❌ Not available: {name}')
                    status_messages.append(f'❌ {name} ({TARGET_SIZE}) is still out of stock.')

            # Send full status update
            status_messages.append('🤖 Stock check complete. Bot is running.')
            send_telegram_alert('\n'.join(status_messages))
        except Exception as e:
            print(f'⚠️ Error: {e}')
            send_telegram_alert(f'⚠️ Bot encountered an error: {e}')

        print(f'⏳ Waiting {CHECK_INTERVAL // 60} minutes...')
        time.sleep(CHECK_INTERVAL)