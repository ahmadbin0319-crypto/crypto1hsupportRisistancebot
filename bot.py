# crypto_signal_bot_advanced.py
import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime
import pytz
import telegram

# ================== CONFIG ==================
TELEGRAM_TOKEN = "8209994203:AAEUptxmSVtGjXTosqaqpESm1FXvlGJRJtU"
CHAT_ID = "5969642968"

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT",
    "SOLUSDT", "MATICUSDT", "DOTUSDT", "LTCUSDT", "TRXUSDT",
    "AVAXUSDT", "ATOMUSDT", "NEARUSDT", "FTMUSDT", "OPUSDT"
]

LIMIT = 200
bot = telegram.Bot(token=TELEGRAM_TOKEN)

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

# ============== SWING HIGH/LOW (KEY ZONES) =================
def detect_swings(df, lookback=3):
    recent = df.tail(lookback)
    swing_high = recent["high"].max()
    swing_low = recent["low"].min()
    return swing_high, swing_low

# ============== STRATEGY LOGIC =================
def check_signal(symbol):
    try:
        data_1d = fetch_klines(symbol, "1d", LIMIT)
        data_15m = fetch_klines(symbol, "15m", LIMIT)

        # Key zones (last 2-3 day swing high/low)
        swing_high, swing_low = detect_swings(data_1d, lookback=3)

        last_close = data_15m["close"].iloc[-1]
        prev_close = data_15m["close"].iloc[-2]
        last_high = data_15m["high"].iloc[-1]
        last_low = data_15m["low"].iloc[-1]
        last_vol = data_15m["volume"].iloc[-1]
        avg_vol = data_15m["volume"].tail(20).mean()

        signal = None
        sl = None
        tp = None
        setup_type = None

        # ========== ChartPrime Breakout + LuxAlgo Retest Logic ==========
        # Breakout UP
        if prev_close < swing_high < last_close and last_vol > avg_vol:
            # Retest check → price recently tested breakout zone
            if abs(last_low - swing_high) / swing_high < 0.002:  # ~0.2% retest margin
                signal = "BUY"
                setup_type = "ChartPrime Breakout + LuxAlgo Retest"
                sl = swing_low  # LuxAlgo next support
                tp = last_close + (last_close - sl) * 2

        # Breakout DOWN
        elif prev_close > swing_low > last_close and last_vol > avg_vol:
            if abs(last_high - swing_low) / swing_low < 0.002:
                signal = "SELL"
                setup_type = "ChartPrime Breakout + LuxAlgo Retest"
                sl = swing_high  # LuxAlgo next resistance
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
                "setup": setup_type,
                "time": datetime.now(pytz.UTC).strftime("%Y-%m-%d %H:%M:%S")
            }

    except Exception as e:
        print(f"Error {symbol}: {e}")
    return None

# ============== TELEGRAM ALERT =================
def send_alert(msg):
    bot.send_message(chat_id=CHAT_ID, text=msg)

# ============== MAIN LOOP =================
def main():
    print("🚀 Advanced Crypto Bot (ChartPrime + LuxAlgo logic) started...")
    while True:
        for sym in SYMBOLS:
            signal = check_signal(sym)
            if signal:
                message = (
                    f"📊 A+ Trade Setup\n"
                    f"Symbol: {signal['symbol']}\n"
                    f"Signal: {signal['signal']}\n"
                    f"Setup: {signal['setup']}\n"
                    f"Entry: {signal['price']}\n"
                    f"SL: {signal['sl']}\n"
                    f"TP: {signal['tp']}\n"
                    f"Volume: {signal['volume']} (Avg: {signal['avg_vol']})\n"
                    f"Time: {signal['time']}"
                )
                print(message)
                send_alert(message)
        time.sleep(60)

if __name__ == "__main__":
    main()
