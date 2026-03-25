import ccxt
import pandas as pd
import numpy as np
import time

# API YOK (test mod)
exchange = ccxt.okx()

symbol = 'BTC/USDT'   # BTC/TRY dene, olmazsa bunu kullan
timeframe = '1m'

# ATR
def ATR(df, period=10):
    df['H-L'] = df['high'] - df['low']
    df['H-PC'] = abs(df['high'] - df['close'].shift(1))
    df['L-PC'] = abs(df['low'] - df['close'].shift(1))
    df['TR'] = df[['H-L','H-PC','L-PC']].max(axis=1)
    return df['TR'].rolling(period).mean()

# UT BOT
def UTBot(df, a=1, c=10):
    df['ATR'] = ATR(df, c)
    df['nLoss'] = a * df['ATR']

    trailing = [0]

    for i in range(1, len(df)):
        prev = trailing[i-1]
        price = df['close'][i]

        if price > prev:
            trailing.append(max(prev, price - df['nLoss'][i]))
        else:
            trailing.append(min(prev, price + df['nLoss'][i]))

    df['ts'] = trailing

    df['buy'] = (df['close'] > df['ts']) & (df['close'].shift(1) <= df['ts'].shift(1))
    df['sell'] = (df['close'] < df['ts']) & (df['close'].shift(1) >= df['ts'].shift(1))

    return df

# LOG
def log(text):
    with open("log.txt", "a") as f:
        f.write(f"{time.ctime()} - {text}\n")

print("BOT BASLADI...")

while True:
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=100)
        df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])

        df = UTBot(df)
        last = df.iloc[-1]

        if last['buy']:
            print(f"BUY SIGNAL → Price: {last['close']}")
            log(f"BUY SIGNAL | Price: {last['close']}")

        elif last['sell']:
            print(f"SELL SIGNAL → Price: {last['close']}")
            log(f"SELL SIGNAL | Price: {last['close']}")

        time.sleep(10)

    except Exception as e:
        print("HATA:", e)
        time.sleep(5)
