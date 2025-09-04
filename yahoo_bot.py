import os
import yfinance as yf
from datetime import datetime, timedelta, timezone
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, data=data)

def get_spy_change():
    spy = yf.Ticker("SPY")
    hist = spy.history(period="5d", interval="1d")
    if len(hist) < 2:
        raise ValueError("Not enough SPY data")
    prev_close = hist["Close"].iloc[-2]
    yesterday_close = hist["Close"].iloc[-1]
    return (yesterday_close - prev_close) / prev_close * 100

def get_nikkei_intraday_change():
    nikkei = yf.Ticker("^N225")
    hist = nikkei.history(period="2d", interval="15m")
    if len(hist) < 10:
        raise ValueError("Not enough Nikkei intraday data")

    # Yesterday’s close
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    yesterday_data = hist[hist.index.date == yesterday]
    if len(yesterday_data) == 0:
        raise ValueError("No yesterday data for Nikkei")
    yesterday_close = yesterday_data["Close"].iloc[-1]

    # Latest price
    latest_price = hist["Close"].iloc[-1]

    return (latest_price - yesterday_close) / yesterday_close * 100

def main():
    try:
        spy_change = get_spy_change()
    except Exception as e:
        spy_change = None
        print(f"SPY error: {e}")

    try:
        nikkei_change = get_nikkei_intraday_change()
    except Exception as e:
        nikkei_change = None
        print(f"Nikkei error: {e}")

    msg = "📊 *Morning Signal (Yahoo)*\n"
    msg += f"Nikkei intraday: {nikkei_change:.2f}%\n" if nikkei_change else "Nikkei: N/A\n"
    msg += f"S&P 500 (yesterday): {spy_change:.2f}%\n" if spy_change else "S&P 500: N/A\n"

    if nikkei_change is None or spy_change is None:
        signal = "DATA UNAVAILABLE"
    elif nikkei_change > 0 and spy_change > 0:
        signal = "LONG"
    elif nikkei_change < 0 and spy_change < 0:
        signal = "SHORT"
    else:
        signal = "NEUTRAL"

    msg += f"➡️ Signal: *{signal}*"
    print(msg)
    send_telegram(msg)

if __name__ == "__main__":
    main()
