from flask import Flask, request, jsonify
import hmac, hashlib, time, requests, os
import pandas as pd
import numpy as np
from datetime import datetime
import threading

app = Flask(__name__)

API_KEY        = os.environ.get("BINANCE_API_KEY", "")
API_SECRET     = os.environ.get("BINANCE_API_SECRET", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "sinyal2024")
KEY_VALUE  = float(os.environ.get("KEY_VALUE", "1"))
ATR_PERIOD = int(os.environ.get("ATR_PERIOD", "10"))
SYMBOL     = os.environ.get("SYMBOL", "COSTRY")
AMOUNT     = float(os.environ.get("AMOUNT", "59000"))
INTERVAL   = os.environ.get("INTERVAL", "30m")
BASE_URL   = "https://api.binance.me"

bot_active = True
trade_log = []
last_signal = {"signal": None, "time": 0}

def sign(params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()

def place_order(symbol, side, try_amount):
    price_r = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={"symbol": symbol})
    price = float(price_r.json()["price"])
    qty = round(try_amount / price, 6)
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
    data = r.json()
    df = pd.DataFrame(data, columns=[
        "open_time","open","high","low","close","volume","close_time",
        "qav","trades","tbav","tqav","ignore"
    ])
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

def check_and_trade():
    global last_signal
    if not bot_active:
        return "DURDURULDU", {}

    try:
        # Anlık fiyatı çek
        price_r = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={"symbol": SYMBOL})
        current_price = float(price_r.json()["price"])
        print(f"[FİYAT] {SYMBOL} anlık fiyat: {current_price}")

        df = get_klines(SYMBOL, INTERVAL, limit=max(ATR_PERIOD * 3, 100))

        if df.empty or len(df) < ATR_PERIOD:
            print(f"[HATA] {SYMBOL} için veri yok veya yetersiz")
            return "NO DATA", {"price": current_price}

        buy, sell = calculate_ut_bot(df, KEY_VALUE, ATR_PERIOD)
        now = time.time()

        if buy and last_signal["signal"] != "BUY":
            last_signal = {"signal": "BUY", "time": now}
            result = place_order(SYMBOL, "BUY", AMOUNT)
            print(f"[BUY] {SYMBOL} {AMOUNT}TRY | fiyat: {current_price} | {result}")
            return "BUY", {"price": current_price, "order": result}

        elif sell and last_signal["signal"] != "SELL":
            last_signal = {"signal": "SELL", "time": now}
            result = place_order(SYMBOL, "SELL", AMOUNT)
            print(f"[SELL] {SYMBOL} {AMOUNT}TRY | fiyat: {current_price} | {result}")
            return "SELL", {"price": current_price, "order": result}

        else:
            print(f"[HOLD] {SYMBOL} fiyat: {current_price}")
            return "HOLD", {"price": current_price}

    except Exception as e:
        print(f"[HATA] {e}")
        return "ERROR", {"error": str(e)}

@app.route("/")
def home():
    durum = "AKTIF" if bot_active else "DURDURULDU"
    rows = ""
    for t in reversed(trade_log):
        renk = "#2ecc71" if t["side"] == "BUY" else "#e74c3c"
        rows += f"<tr><td>{t['time']}</td><td style='color:{renk};font-weight:bold'>{t['side']}</td><td>{t['symbol']}</td><td>{t['amount_try']:,.0f} TRY</td><td>{t['price']}</td><td>{t['qty']}</td><td>{t['result']}</td></tr>"
    return f"""<html><head><meta charset='utf-8'><title>UT Bot</title>
    <style>body{{background:#0d0f14;color:#e8eaf0;font-family:monospace;padding:20px}}
    h2{{color:#4f8eff}}.badge{{padding:6px 16px;border-radius:20px;font-weight:bold}}
    .aktif{{background:#1a3a1a;color:#2ecc71;border:1px solid #2ecc71}}
    .dur{{background:#3a1a1a;color:#e74c3c;border:1px solid #e74c3c}}
    .btn{{padding:10px 24px;border:none;border-radius:8px;cursor:pointer;font-size:14px;margin:8px 4px}}
    .btn-dur{{background:#e74c3c;color:#fff}}.btn-bas{{background:#2ecc71;color:#000}}
    table{{width:100%;border-collapse:collapse;margin-top:20px}}
    th{{background:#1e2230;padding:10px;text-align:left;font-size:12px;color:#7a7f96}}
    td{{padding:8px 10px;border-bottom:1px solid #1e2230;font-size:13px}}</style></head>
    <body><h2>UT Bot — {SYMBOL}</h2>
    <p>Durum: <span class='badge {"
