import requests
from bs4 import BeautifulSoup
import time
import telebot

# === CONFIG ===
PRODUCT_URL = 'https://www.ajio.com/nike-initiator-lace-up-running-shoes/p/469647549_blackgrey'
TARGET_SIZE = 'UK 9'
CHECK_INTERVAL = 60 * 30  # every 30 minutes


# Telegram config
TELEGRAM_TOKEN = '7830827607:AAFCckivUw-iGOuAF0ZvWpmVGYsWD-B-suY'
TELEGRAM_CHAT_ID = '1116571699'

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



def send_telegram_alert():
    message = f'🎉 Your size ({TARGET_SIZE}) is in stock!\n{PRODUCT_URL}'
    bot.send_message(TELEGRAM_CHAT_ID, message)
    print('✅ Telegram alert sent!')


if __name__ == '__main__':
    while True:
        print('🔍 Checking stock...')
        try:
            if check_stock():
                print('🎯 In stock! Sending Telegram alert...')
                send_telegram_alert()
            else:
                print(f'❌ Not available: {TARGET_SIZE}')
        except Exception as e:
            print(f'⚠️ Error: {e}')

        print(f'⏳ Waiting {CHECK_INTERVAL // 60} minutes...')
        time.sleep(CHECK_INTERVAL)