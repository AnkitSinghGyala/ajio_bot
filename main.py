import requests
from bs4 import BeautifulSoup
import time
import telebot
import os

# === CONFIG ===
PRODUCT_URL = 'https://www.ajio.com/nike-initiator-lace-up-running-shoes/p/469647549_blackgrey'
TARGET_SIZE = 'UK 9'
CHECK_INTERVAL = 60 * 30  # every 30 minutes

# Load environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def check_stock():
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(PRODUCT_URL, headers=headers)
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
            if check_stock():
                print('🎯 In stock! Sending Telegram alert...')
                send_telegram_alert(f'🎉 Your size ({TARGET_SIZE}) is in stock!\n{PRODUCT_URL}')
            else:
                print(f'❌ Not available: {TARGET_SIZE}')
                send_telegram_alert(f'❌ Still out of stock for size {TARGET_SIZE}. Bot is running fine.')
        except Exception as e:
            print(f'⚠️ Error: {e}')
            send_telegram_alert(f'⚠️ Bot encountered an error: {e}')

        print(f'⏳ Waiting {CHECK_INTERVAL // 60} minutes...')
        time.sleep(CHECK_INTERVAL)