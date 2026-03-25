import datetime
from binance.client import Client
from flask import Flask, request

# Binance TR API anahtarlarını buraya koyacaksın
API_KEY = "SENIN_API_KEY"
API_SECRET = "SENIN_API_SECRET"

client = Client(API_KEY, API_SECRET)
app = Flask(__name__)

# Bot kontrol flag'i
bot_active = False

# Log fonksiyonu
def log_trade(action, symbol, qty, response):
    with open("trade_logs.txt", "a") as f:
        f.write(f"{datetime.datetime.now()} - {action} - {symbol} - {qty} - {response}\n")

# Basit emir gönderme fonksiyonları
def buy(symbol, qty):
    order = client.order_market_buy(symbol=symbol, quantity=qty)
    log_trade("BUY", symbol, qty, order)

def sell(symbol, qty):
    order = client.order_market_sell(symbol=symbol, quantity=qty)
    log_trade("SELL", symbol, qty, order)

# Manuel kontrol endpointleri
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

# Strateji sinyali endpointi (senin özel kodun buradan çağrılacak)
@app.route("/signal", methods=["POST"])
def signal():
    global bot_active
    if not bot_active:
        return "Bot durdurulmuş durumda"
    
    data = request.json
    action = data.get("action")   # "BUY" veya "SELL"
    symbol = data.get("symbol")   # örn: "COSUSDT"
    qty = data.get("qty")         # miktar
    
    if action == "BUY":
        buy(symbol, qty)
    elif action == "SELL":
        sell(symbol, qty)
    
    return f"{action} emri gönderildi"

if __name__ == "__main__":
    app.run(port=5000) 
