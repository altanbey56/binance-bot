import os
from telegram import Bot

# Railway'den alınacak değişkenler
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Kontrol
if not TOKEN or not CHAT_ID:
    print("HATA: TOKEN veya CHAT_ID eksik!")
    exit()

bot = Bot(token=TOKEN)

print("Bot çalıştı...")

# Mesaj gönder
bot.send_message(chat_id=CHAT_ID, text="Bot aktif 🚀")
