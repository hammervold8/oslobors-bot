import os
import requests
from dotenv import load_dotenv
from twelvedata import TDClient
from datetime import datetime
import time

# ==============================
# Load environment variables
# ==============================
load_dotenv()  # optional for local testing
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
T12_API_KEY = os.getenv("TWELVE_API_KEY")

if not TOKEN or not CHAT_ID or not T12_API_KEY:
    raise ValueError("Missing TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, or TWELVE_API_KEY")

# ==============================
# Initialize Twelve Data Client
# ==============================
td = TDClient(apikey=T12_API_KEY)

# ==============================
# Configuration
# ==============================
NIKKEI_SYMBOL = "EWJ"  # Japan ETF proxy
US_SYMBOL = "SPY"      # S&P 500 ETF

# ==============================
# Functions
# ==============================
def get_percent_change(symbol, retries=3, delay=5):
    """
    Fetch percent change between the previous two full trading days.
    Retries up to `retries` times on failure.
    """
    for attempt in range(retries):
        try:
            ts = td.time_series(symbol=symbol, interval="1day", outputsize=3)
            data = ts.as_pandas()
            
            # Debug: log available dates and raw data
            print(f"Fetched data for {symbol}:\n{data}")

            if data.empty or len(data) < 3:
                raise ValueError(f"Not enough data for {symbol}")

            # Take previous two full trading days
            close_today = data.iloc[1]["close"]
            close_yesterday = data.iloc[2]["close"]
            pct_change = ((close_today - close_yesterday) / close_yesterday) * 100
            return pct_change

        except Exception as e:
            print(f"Attempt {attempt+1} failed for {symbol}: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                print(f"Failed to get {symbol} after {retries} attempts.")
                return None

def compute_signal(nikkei, us):
    if nikkei is None or us is None:
        return "DATA UNAVAILABLE"
    if nikkei > 0 and us > 0:
        return "LONG"
    elif nikkei < 0 and us < 0:
        return "SHORT"
    else:
        return "NEUTRAL"

def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=payload, timeout=10)
        if not response.ok:
            print(f"Telegram send failed: {response.text}")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

# ==============================
# Main
# ==============================
def main():
    nikkei = get_percent_change(NIKKEI_SYMBOL)
    # Wait to avoid hitting rate limits
    time.sleep(12)
    us = get_percent_change(US_SYMBOL)

    signal = compute_signal(nikkei, us)

    if nikkei is None or us is None:
        warning = "⚠️ Warning: Could not fetch market data. Signal may be invalid."
        print(warning)
        send_telegram(warning)

    msg = f"📊 Morning Signal ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n"
    msg += f"Nikkei (EWJ): {nikkei:.2f}%\n" if nikkei is not None else "Nikkei (EWJ): N/A\n"
    msg += f"US Market (SPY): {us:.2f}%\n" if us is not None else "US Market (SPY): N/A\n"
    msg += f"➡️ Signal: {signal}"

    print(msg)
    send_telegram(msg)

if __name__ == "__main__":
    main()
