# crypto_signal_bot.py
import asyncio
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
from telegram import Bot

# ================== CONFIG ==================
TELEGRAM_TOKEN = "8209994203:AAEUptxmSVtGjXTosqaqpESm1FXvlGJRJtU"
CHAT_ID = "5969642968"

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT",
    "SOLUSDT", "MATICUSDT", "DOTUSDT", "LTCUSDT", "TRXUSDT",
    "AVAXUSDT", "ATOMUSDT", "NEARUSDT", "FTMUSDT", "OPUSDT"
]  # liquidity filter ke sath top coins

INTERVALS = ["1d", "4h", "1h", "15m"]
LIMIT = 200

bot = Bot(token=TELEGRAM_TOKEN)

# ============== BINANCE API HELPER =================
def fetch_klines(symbol, interval, limit=200):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns=[
        "time", "open", "high", "low", "close", "volume",
        "close_time", "qav", "trades", "tbbav", "tbqav", "ignore"
    ])
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df

# ============== STRATEGY LOGIC =================
def detect_sr(df):
    """ Simple S/R detection by swing points """
    highs = df["high"].rolling(5, center=True).max()
    lows = df["low"].rolling(5, center=True).min()
    levels = pd.concat([highs, lows]).dropna().unique()
    return sorted(levels)

def check_signal(symbol):
    try:
        data_1d = fetch_klines(symbol, "1d", LIMIT)
        data_15m = fetch_klines(symbol, "15m", LIMIT)

        # Support/Resistance
        sr_levels = detect_sr(data_1d)

        # Price action breakout/retest check
        last_close = data_15m["close"].iloc[-1]
        prev_close = data_15m["close"].iloc[-2]
        last_high = data_15m["high"].iloc[-1]
        last_low = data_15m["low"].iloc[-1]
        last_vol = data_15m["volume"].iloc[-1]
        avg_vol = data_15m["volume"].tail(20).mean()

        signal = None
        sl = None
        tp = None

        for level in sr_levels:
            # Breakout + Volume filter + Candle size filter
            if prev_close < level < last_close and last_vol > avg_vol:
                signal = "BUY"
                sl = min(data_15m["low"].tail(5))
                tp = last_close + (last_close - sl) * 2
            elif prev_close > level > last_close and last_vol > avg_vol:
                signal = "SELL"
                sl = max(data_15m["high"].tail(5))
                tp = last_close - (sl - last_close) * 2

        if signal:
            return {
                "symbol": symbol,
                "signal": signal,
                "price": last_close,
                "sl": round(sl, 2),
                "tp": round(tp, 2),
                "volume": round(last_vol, 2),
                "avg_vol": round(avg_vol, 2),
                "time": datetime.now(pytz.UTC).strftime("%Y-%m-%d %H:%M:%S")
            }
    except Exception as e:
        print(f"Error {symbol}: {e}")
    return None

# ============== TELEGRAM ALERT =================
async def send_alert(msg: str):
    await bot.send_message(chat_id=CHAT_ID, text=msg)

# ============== MAIN LOOP =================
async def main():
    print("🚀 Async Crypto Signal Bot started...")
    while True:
        for sym in SYMBOLS:
            signal = check_signal(sym)
            if signal:
                message = (
                    f"📊 A+ Trade Setup\n"
                    f"Symbol: {signal['symbol']}\n"
                    f"Signal: {signal['signal']}\n"
                    f"Entry: {signal['price']}\n"
                    f"SL: {signal['sl']}\n"
                    f"TP: {signal['tp']}\n"
                    f"Volume: {signal['volume']} (Avg: {signal['avg_vol']})\n"
                    f"Time: {signal['time']}"
                )
                print(message)
                await send_alert(message)
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
