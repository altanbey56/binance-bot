import time
import random

# ----------------------------
# AYARLAR
# ----------------------------
SYMBOL = "BTC/USDT"        # Örnek coin
INTERVAL = 60              # Saniye cinsinden veri çekme aralığı
LOG_FILE = "bot_log.txt"   # Log kaydı

# ----------------------------
# SAHTE API / FİYAT VERİSİ
# ----------------------------
def get_fake_price():
    """
    Fake fiyat verisi üretir.
    Test amaçlı: 65000-66000 arasında rastgele değer
    """
    return round(random.uniform(65000, 66000), 2)

# ----------------------------
# SİNYAL HESAPLAMA
# ----------------------------
def check_signal(price, last_price):
    if last_price is None:
        return "HİÇBİRİ"
    if price > last_price:
        return "ALIŞ"
    elif price < last_price:
        return "SATIŞ"
    else:
        return "HİÇBİRİ"

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
    print("BOT BASLADI... (Fake API Testi, Web Service ortamında)")
    last_price = None

    while True:
        price = get_fake_price()
        signal = check_signal(price, last_price)
        log_signal(signal, price)
        last_price = price
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
