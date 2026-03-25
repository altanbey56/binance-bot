import datetime
from flask import Flask, request
from okx import Trade, Account

API_KEY = "SENIN_OKX_API_KEY"
API_SECRET = "SENIN_OKX_API_SECRET"
API_PASSPHRASE = "SENIN_OKX_API_PASSPHRASE"

tradeAPI = Trade.TradeAPI(API_KEY, API_SECRET, API_PASSPHRASE, False, "0")
accountAPI = Account.AccountAPI(API_KEY, API_SECRET, API_PASSPHRASE, False, "0")

app = Flask(__name__)
bot_active = False

def log_trade(action, symbol, qty, response):
    with open("trade_logs.txt", "a") as f:
        f.write(f"{datetime.datetime.now()} - {action} - {symbol} - {qty} - {response}\n")

def buy(symbol, qty):
    order = tradeAPI.place_order(instId=symbol, tdMode="cash", side="buy", ordType="market", sz=str(qty))
    log_trade("BUY", symbol, qty, order)
    return order

def sell(symbol, qty):
    order = tradeAPI.place_order(instId=symbol, tdMode="cash", side="sell", ordType="market", sz=str(qty))
    log_trade("SELL", symbol, qty, order)
    return order

@app.route("/start", methods=["POST"])
def start_bot():
    global bot_active
    bot_active = True
    return "Bot başlatıldı"

@app.route("/stop", methods=["POST"])
def stop_bot():
    global bot_active
    bot_active = False
    return "Bot durduruldu"

@app.route("/signal", methods=["POST"])
def signal():
    global bot_active
    if not bot_active:
        return "Bot durdurulmuş durumda"
    
    data = request.json
    action = data.get("action")
    symbol = data.get("symbol")   # Örn: "BTC-TRY", "ETH-TRY", "USDT-TRY"
    qty = data.get("qty")
    
    if action == "BUY":
        response = buy(symbol, qty)
    elif action == "SELL":
        response = sell(symbol, qty)
    else:
        return "Geçersiz sinyal"
    
    return f"{action} emri gönderildi: {response}"

if __name__ == "__main__":
    app.run(port=5000)
