import time
import random

# ----------------------------
# BOT AYARLARI
# ----------------------------

SYMBOL = "BTC/USDT"       # Örnek coin
INTERVAL = 60             # 60 saniyede bir veri çek
LOG_FILE = "bot_log.txt"  # Log kaydı

# ----------------------------
# SAHTE VERİ / TEST
# ----------------------------

def get_fake_price():
    """Fake fiyat verisi üretir"""
    return round(random.uniform(65000, 66000), 2)

# ----------------------------
# ALIŞ / SATIŞ SİNYALİ
# ----------------------------

def check_signal(price, last_signal):
    """
    Basit örnek: fiyat rastgele değişince alış/satış sinyali üret
    """
    if last_signal is None:
        return "HİÇBİRİ"
    if price > last_signal:
        return "ALIŞ"
    else:
        return "SATIŞ"

# ----------------------------
# LOG YAZMA
# ----------------------------

def log_signal(signal, price):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} | Fiyat: {price} | Sinyal: {signal}"
    print(log_line)
    with open(LOG_FILE, "a") as f:
        f.write(log_line + "\n")

# ----------------------------
# ANA DÖNGÜ
# ----------------------------

def main():
    print("BOT BASLADI...")
    last_price = get_fake_price()
    last_signal = None

    while True:
        price = get_fake_price()
        signal = check_signal(price, last_price)
        log_signal(signal, price)
        last_price = price
        last_signal = signal
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
