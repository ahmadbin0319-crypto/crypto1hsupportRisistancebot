"""
pro_crypto_bot_render.py
Render friendly Telegram bot – scans every 15 minutes
Sends only ONE strong pro setup alert (no spam)
"""

import os
import time
import ccxt
import pandas as pd
from datetime import datetime, timezone
from telegram import Bot
from telegram.constants import ParseMode

# ------------------ CONFIG ------------------
TELEGRAM_TOKEN = "8209994203:AAEUptxmSVtGjXTosqaqpESm1FXvlGJRJtU"   # <-- apna token
CHAT_ID = "5969642968"  # <-- apna chat id

EXCHANGE = ccxt.binance({'enableRateLimit': True})
SYMBOLS = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT"]

bot = Bot(token=TELEGRAM_TOKEN)

# ------------------ HELPERS ------------------
def fetch_ohlcv(symbol, timeframe, limit=200):
    data = EXCHANGE.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(data, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    return df

def get_swings(df, days=3):
    recent = df.tail(days)
    return recent['high'].max(), recent['low'].min()

def detect_sr(df):
    levels = []
    for i in range(2, len(df) - 2):
        if df['high'][i] == max(df['high'][i-2:i+3]):
            levels.append({'price': df['high'][i], 'type': 'res'})
        if df['low'][i] == min(df['low'][i-2:i+3]):
            levels.append({'price': df['low'][i], 'type': 'sup'})
    uniq = {}
    for l in levels:
        uniq[round(l['price'], 2)] = l
    return list(uniq.values())

def price_action_signal(df15):
    if len(df15) < 3:
        return None
    last, prev = df15.iloc[-1], df15.iloc[-2]

    # bullish engulfing
    if (
        last['close'] > last['open']
        and prev['close'] < prev['open']
        and last['close'] > prev['open']
        and last['open'] < prev['close']
    ):
        return "LONG"

    # bearish engulfing
    if (
        last['close'] < last['open']
        and prev['close'] > prev['open']
        and last['close'] < prev['open']
        and last['open'] > prev['close']
    ):
        return "SHORT"

    # breakout
    if last['close'] > prev['high']:
        return "LONG"
    if last['close'] < prev['low']:
        return "SHORT"

    return None

def nearest_sr(levels, price):
    if not levels:
        return None
    return min(levels, key=lambda l: abs(price - l['price']))

def analyze(symbol):
    try:
        df1d = fetch_ohlcv(symbol, "1d", 50)
        df4h = fetch_ohlcv(symbol, "4h", 100)
        df1h = fetch_ohlcv(symbol, "1h", 200)
        df15 = fetch_ohlcv(symbol, "15m", 100)

        swing_high, swing_low = get_swings(df1d, 3)
        sr_levels = detect_sr(df1d) + detect_sr(df4h) + detect_sr(df1h)

        last_price = df15['close'].iloc[-1]
        pa = price_action_signal(df15)
        nearest = nearest_sr(sr_levels, last_price)

        if not pa or not nearest:
            return None

        signal, sl, tp = None, None, None

        if pa == "LONG" and nearest['type'] == "sup" and last_price > nearest['price']:
            sl = nearest['price']
            rr = last_price - sl
            tp = last_price + rr * 3
            signal = "LONG"
        elif pa == "SHORT" and nearest['type'] == "res" and last_price < nearest['price']:
            sl = nearest['price']
            rr = sl - last_price
            tp = last_price - rr * 3
            signal = "SHORT"

        if signal:
            return {
                "symbol": symbol,
                "price": last_price,
                "signal": signal,
                "swing_high": swing_high,
                "swing_low": swing_low,
                "nearest": nearest,
                "sl": sl,
                "tp": tp,
            }
        return None

    except Exception as e:
        # Error alert bhi Telegram pe bhej do
        try:
            bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Error in {symbol}: {e}")
        except:
            pass
        return None

def format_msg(r):
    return (
        f"📊 <b>{r['symbol']}</b> | Price: <b>{r['price']}</b>\n"
        f"Swing High(3d): {r['swing_high']} | Swing Low: {r['swing_low']}\n"
        f"✅ Signal: <b>{r['signal']}</b>\n"
        f"Nearest {r['nearest']['type'].upper()}: {r['nearest']['price']}\n"
        f"SL: {r['sl']} | TP: {r['tp']} (1:3 RR)"
    )

# ------------------ LOOP ------------------
if __name__ == "__main__":
    while True:
        print(f"\n⏳ Scanning {datetime.now(timezone.utc)} ...")
        for sym in SYMBOLS:
            r = analyze(sym)
            if r:  # send only ONE pro setup
                msg = format_msg(r)
                print(msg)
                bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode=ParseMode.HTML)
                break
        time.sleep(900)  # wait 15 min before next scan


