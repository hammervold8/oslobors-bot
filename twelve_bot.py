import os
from twelvedata import TDClient
from datetime import datetime, timedelta, timezone
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")

td = TDClient(apikey=TWELVE_API_KEY)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, data=data)

def get_spy_change():
    ts = td.time_series(symbol="SPY", interval="1day", outputsize=2).as_pandas()
    if ts is None or len(ts) < 2:
        raise ValueError("Not enough SPY data")
    prev_close = ts["close"].iloc[-2]
    yesterday_close = ts["close"].iloc[-1]
    return (yesterday_close - prev_close) / prev_close * 100

def get_nikkei_intraday_change():
    ts = td.time_series(symbol="EWJ", interval="15min", outputsize=200).as_pandas()
    if ts is None or len(ts) < 10:
        raise ValueError("Not enough EWJ intraday data")

    today = datetime.now(timezone.utc).date()
    yesterday_data = ts[ts.index.date < today]
    if len(yesterday_data) == 0:
        raise ValueError("No yesterday data for EWJ")
    yesterday_close = yesterday_data["close"].iloc[-1]

    latest_price = ts["close"].iloc[-1]

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

    msg = "📊 *Morning Signal (Twelve Data)*\n"
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
