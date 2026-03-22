from flask import Flask, request, jsonify
import hmac, hashlib, time, requests, os

app = Flask(__name__)

# ── AYARLAR ──────────────────────────────────────────────
API_KEY        = os.environ.get("BINANCE_API_KEY", "")
API_SECRET     = os.environ.get("BINANCE_API_SECRET", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "gizlianahtar123")

BASE_URL = "https://api.binance.tr"
# ─────────────────────────────────────────────────────────

def sign(params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()

def place_order(symbol, side, try_amount):
    price_r = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={"symbol": symbol})
    price = float(price_r.json()["price"])
    qty = round(try_amount / price, 6)

    params = {
        "symbol":    symbol,
        "side":      side.upper(),
        "type":      "MARKET",
        "quantity":  qty,
        "timestamp": int(time.time() * 1000),
    }
    params["signature"] = sign(params)

    headers = {"X-MBX-APIKEY": API_KEY}
    r = requests.post(f"{BASE_URL}/api/v3/order", params=params, headers=headers)
    return r.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}

    if data.get("secret") != WEBHOOK_SECRET:
        return {"error": "yetkisiz"}, 403

    symbol     = data.get("symbol", "BTCTRY")
    side       = data.get("side", "BUY")
    try_amount = float(data.get("amount", 100))

    result = place_order(symbol, side, try_amount)
    print(f"[EMIR] {side} {symbol} {try_amount}TRY | {result}")
    return result

@app.route("/")
def home():
    return "Bot calisıyor"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
