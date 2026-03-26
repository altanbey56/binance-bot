import requests
import pandas as pd
import time
import os

# Railway'den alır
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

symbol = "COSTRYUSDT"
interval = "30m"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message
    }
    requests.post(url, data=data)

def get_data():
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=100"
    data = requests.get(url).json()
    
    df = pd.DataFrame(data)
    df = df.iloc[:, :6]
    df.columns = ["time","open","high","low","close","volume"]

    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)

    return df

def ut_bot(df, a=1, c=10):
    df["ATR"] = df["high"] - df["low"]
    df["nLoss"] = a * df["ATR"]

    trailing_stop = [0]

    for i in range(1, len(df)):
        prev = trailing_stop[i-1]
        price = df["close"][i]

        if price > prev:
            trailing_stop.append(max(prev, price - df["nLoss"][i]))
        else:
            trailing_stop.append(min(prev, price + df["nLoss"][i]))

    df["TS"] = trailing_stop

    df["buy"] = (df["close"] > df["TS"]) & (df["close"].shift(1) <= df["TS"].shift(1))
    df["sell"] = (df["close"] < df["TS"]) & (df["close"].shift(1) >= df["TS"].shift(1))

    return df

last_signal = None

# BOT BAŞLADI MESAJI
send_telegram("🤖 BOT AKTİF 🚀")

while True:
    try:
        df = get_data()
        df = ut_bot(df)

        last = df.iloc[-1]

        if last["buy"] and last_signal != "buy":
            send_telegram(f"🟢 AL Sinyali\nFiyat: {last['close']}")
            last_signal = "buy"

        elif last["sell"] and last_signal != "sell":
            send_telegram(f"🔴 SAT Sinyali\nFiyat: {last['close']}")
            last_signal = "sell"

    except Exception as e:
        send_telegram(f"Hata: {e}")

    time.sleep(60)
