from flask import Flask, request, jsonify
import hmac, hashlib, time, requests, os
import pandas as pd
import numpy as np

app = Flask(__name__)

API_KEY        = os.environ.get("BINANCE_API_KEY", "")
API_SECRET     = os.environ.get("BINANCE_API_SECRET", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "sinyal2024")
KEY_VALUE  = float(os.environ.get("KEY_VALUE", "1"))
ATR_PERIOD = int(os.environ.get("ATR_PERIOD", "10"))
SYMBOL     = os.environ.get("SYMBOL", "BTCTRY")
AMOUNT     = float(os.environ.get("AMOUNT", "100"))
INTERVAL   = os.environ.get("INTERVAL", "1m")
BASE_URL = "https://api.binance.tr"

def sign(params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()

def place_order(symbol, side, try_amount):
    price_r = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={"symbol": symbol})
    price = float(price_r.json()["price"])
    qty = round(try_amount / price, 6)
    params = {"symbol": symbol, "side": side.upper(), "type": "MARKET", "quantity": qty, "timestamp": int(time.time() * 1000)}
    params["signature"] = sign(params)
    headers = {"X-MBX-APIKEY": API_KEY}
    r = requests.post(f"{BASE_URL}/api/v3/order", params=params, headers=headers)
    return r.json()

def get_klines(symbol, interval, limit=100):
    r = requests.get(f"{BASE_URL}/api/v3/klines", params={"symbol": symbol, "interval": interval, "limit": limit})
    data = r.json()
    df = pd.DataFrame(data, columns=["open_time","open","high","low","close","volume","close_time","qav","trades","tbav","tqav","ignore"])
    df["close"] = df["close"].astype(float)
    df["high"]  = df["high"].astype(float)
    df["low"]   = df["low"].astype(float)
    return df

def calculate_ut_bot(df, key_value=1, atr_period=10):
    src = df["close"].values
    high = df["high"].values
    low  = df["low"].values
    tr = np.maximum(high[1:] - low[1:], np.maximum(abs(high[1:] - src[:-1]), abs(low[1:] - src[:-1])))
    tr = np.insert(tr, 0, high[0] - low[0])
    atr = np.zeros(len(tr))
    atr[atr_period-1] = np.mean(tr[:atr_period])
    for i in range(atr_period, len(tr)):
        atr[i] = (atr[i-1] * (atr_period - 1) + tr[i]) / atr_period
    n_loss = key_value * atr
    xATR_ts = np.zeros(len(src))
    for i in range(1, len(src)):
        prev = xATR_ts[i-1]
        if src[i] > prev and src[i-1] > prev:
            xATR_ts[i] = max(prev, src[i] - n_loss[i])
        elif src[i] < prev and src[i-1] < prev:
            xATR_ts[i] = min(prev, src[i] + n_loss[i])
        elif src[i] > prev:
            xATR_ts[i] = src[i] - n_loss[i]
        else:
            xATR_ts[i] = src[i] + n_loss[i]
    ema = src.copy()
    buy = sell = False
    if len(src) >= 2:
        above = ema[-1] > xATR_ts[-1] and ema[-2] <= xATR_ts[-2]
        below = xATR_ts[-1] > ema[-1] and xATR_ts[-2] <= ema[-2]
        buy  = src[-1] > xATR_ts[-1] and above
        sell = src[-1] < xATR_ts[-1] and below
    return buy, sell

last_signal = {"signal": None, "time": 0}

def check_and_trade():
    global last_signal
    try:
        df = get_klines(SYMBOL, INTERVAL, limit=max(ATR_PERIOD * 3, 100))
        buy, sell = calculate_ut_bot(df, KEY_VALUE, ATR_PERIOD)
        now = time.time()
        if buy and last_signal["signal"] != "BUY":
            last_signal = {"signal": "BUY", "time": now}
            result = place_order(SYMBOL, "BUY", AMOUNT)
            print(f"[BUY] {SYMBOL} {AMOUNT}TRY | {result}")
            return "BUY", result
        elif sell and last_signal["signal"] != "SELL":
            last_signal = {"signal": "SELL", "time": now}
            result = place_order(SYMBOL, "SELL", AMOUNT)
            print(f"[SELL] {SYMBOL} {AMOUNT}TRY | {result}")
            return "SELL", result
        else:
            return "HOLD", {}
    except Exception as e:
        print(f"[HATA] {e}")
        return "ERROR", {"error": str(e)}

@app.route("/check", methods=["GET"])
def check():
    signal, result = check_and_trade()
    return jsonify({"signal": signal, "result": result})

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    if data.get("secret") != WEBHOOK_SECRET:
        return {"error": "yetkisiz"}, 403
    signal, result = check_and_trade()
    return jsonify({"signal": signal, "result": result})

@app.route("/")
def home():
    return "UT Bot calisiyor"

import threading
def auto_loop():
    while True:
        check_and_trade()
        time.sleep(60)
t = threading.Thread(target=auto_loop, daemon=True)
t.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
