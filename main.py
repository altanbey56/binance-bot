from flask import Flask, jsonify
import hmac, hashlib, time, requests, os
import pandas as pd
import numpy as np
from datetime import datetime

app = Flask(__name__)

# ---------------- AYARLAR ----------------
API_KEY    = os.environ.get("BINANCE_API_KEY", "")
API_SECRET = os.environ.get("BINANCE_API_SECRET", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "sinyal2024")
KEY_VALUE  = float(os.environ.get("KEY_VALUE", "1"))
ATR_PERIOD = int(os.environ.get("ATR_PERIOD", "10"))
SYMBOL     = os.environ.get("SYMBOL", "COSTRY")
AMOUNT     = float(os.environ.get("AMOUNT", "59000"))
INTERVAL   = os.environ.get("INTERVAL", "30m")
BASE_URL   = "https://api.binance.me"  # Binance TR API

bot_active = True
trade_log = []
last_signal = {"signal": None, "time": 0}

# ---------------- FONKSİYONLAR ----------------
def sign(params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()

def place_order(symbol, side, try_amount):
    # Anlık fiyat
    price_r = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={"symbol": symbol})
    data = price_r.json()
    if "price" not in data:
        return {"status": "ERROR", "error": data.get("msg", "Fiyat yok")}
    price = float(data["price"])
    qty = round(try_amount / price, 6)

    # Market order parametreleri
    params = {
        "symbol": symbol,
        "side": side.upper(),
        "type": "MARKET",
        "quantity": qty,
        "timestamp": int(time.time() * 1000)
    }
    params["signature"] = sign(params)
    headers = {"X-MBX-APIKEY": API_KEY}
    r = requests.post(f"{BASE_URL}/api/v3/order", params=params, headers=headers)
    result = r.json()

    # Trade log
    trade_log.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "side": side.upper(),
        "symbol": symbol,
        "amount_try": try_amount,
        "price": price,
        "qty": qty,
        "result": result.get("status", str(result))
    })
    if len(trade_log) > 200:
        trade_log.pop(0)
    return result

def get_klines(symbol, interval, limit=100):
    r = requests.get(f"{BASE_URL}/api/v3/klines", params={"symbol": symbol, "interval": interval, "limit": limit})
    df = pd.DataFrame(r.json(), columns=[
        "open_time","open","high","low","close","volume","close_time",
        "qav","trades","tbav","tqav","ignore"
    ])
    df["close"] = df["close"].astype(float)
    df["high"]  = df["high"].astype(float)
    df["low"]   = df["low"].astype(float)
    return df

def calculate_ut_bot(df, key_value=1, atr_period=10):
    if df.empty or len(df) < atr_period: return False, False
    src = df["close"].values
    high, low = df["high"].values, df["low"].values
    if len(src) < 2: return False, False

    tr = np.maximum(high[1:]-low[1:], np.maximum(abs(high[1:]-src[:-1]), abs(low[1:]-src[:-1])))
    tr = np.insert(tr, 0, high[0]-low[0])
    atr = np.zeros(len(tr))
    atr[atr_period-1] = np.mean(tr[:atr_period])
    for i in range(atr_period, len(tr)):
        atr[i] = (atr[i-1]*(atr_period-1)+tr[i])/atr_period
    n_loss = key_value*atr
    xATR_ts = np.zeros(len(src))
    for i in range(1, len(src)):
        prev = xATR_ts[i-1]
        if src[i] > prev and src[i-1] > prev: xATR_ts[i] = max(prev, src[i]-n_loss[i])
        elif src[i] < prev and src[i-1] < prev: xATR_ts[i] = min(prev, src[i]+n_loss[i])
        elif src[i] > prev: xATR_ts[i] = src[i]-n_loss[i]
        else: xATR_ts[i] = src[i]+n_loss[i]
    ema = src.copy()
    buy = sell = False
    if len(src) >= 2:
        above = ema[-1]>xATR_ts[-1] and ema[-2]<=xATR_ts[-2]
        below = xATR_ts[-1]>ema[-1] and xATR_ts[-2]<=ema[-2]
        buy  = src[-1]>xATR_ts[-1] and above
        sell = src[-1]<xATR_ts[-1] and below
    return buy, sell

def check_and_trade():
    global last_signal
    if not bot_active: return "DURDURULDU", {}

    try:
        price_r = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={"symbol": SYMBOL})
        data = price_r.json()
        if "price" not in data:
            return "ERROR", {"error": data.get("msg","Fiyat yok")}
        current_price = float(data["price"])

        df = get_klines(SYMBOL, INTERVAL, limit=max(ATR_PERIOD*3,100))
        if df.empty or len(df)<ATR_PERIOD: return "NO DATA", {"price": current_price}

        buy, sell = calculate_ut_bot(df, KEY_VALUE, ATR_PERIOD)
        now = time.time()

        if buy and last_signal["signal"] != "BUY":
            last_signal = {"signal":"BUY","time":now}
            result = place_order(SYMBOL,"BUY",AMOUNT)
            return "BUY", {"price":current_price,"order":result}

        elif sell and last_signal["signal"] != "SELL":
            last_signal = {"signal":"SELL","time":now}
            result = place_order(SYMBOL,"SELL",AMOUNT)
            return "SELL", {"price":current_price,"order":result}

        else:
            return "HOLD", {"price":current_price}

    except Exception as e:
        return "ERROR", {"error":str(e)}

# ---------------- FLASK ROUTES ----------------
@app.route("/")
def home():
    durum = "AKTIF" if bot_active else "DURDURULDU"
    return jsonify({"status": durum, "trades": trade_log})

@app.route("/start")
def start_bot():
    global bot_active
    bot_active = True
    return jsonify({"status":"Bot başlatıldı"})

@app.route("/stop")
def stop_bot():
    global bot_active
    bot_active = False
    return jsonify({"status":"Bot durduruldu"})

@app.route("/check")
def check():
    durum, data = check_and_trade()
    return jsonify({"status":durum,"data":data})

# ---------------- UYGULAMA BAŞLAT ----------------
if __name__=="__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port)
