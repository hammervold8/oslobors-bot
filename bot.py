import os
from dotenv import load_dotenv
import yfinance as yf
import requests

# ==============================
# Load environment variables
# ==============================
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise ValueError("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID in environment")

# ==============================
# Configuration
# ==============================
NIKKEI_TICKERS = ["EWJ"]  # Japan ETF proxy
NYSE_TICKER = "SPY"        # S&P 500 ETF as US market proxy

# ==============================
# Functions
# ==============================
def get_index_change(tickers):
    """
    Tries each ticker in the list until it gets valid data.
    Returns percent change between yesterday and today.
    """
    for ticker in tickers:
        try:
            data = yf.download(ticker, period="2d", interval="1d", progress=False)
            if data.empty or "Close" not in data or len(data["Close"]) < 2:
                continue
            yesterday, today = data["Close"].iloc[-2:]
            return (today - yesterday) / yesterday * 100
        except Exception:
            continue
    return 0.0

def compute_signal(nikkei, nyse):
    if nikkei > 0 and nyse > 0:
        return "LONG"
    elif nikkei < 0 and nyse < 0:
        return "SHORT"
    else:
        return "NEUTRAL"

def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

# ==============================
# Main
# ==============================
def main():
    nikkei = get_index_change(NIKKEI_TICKERS)
    nyse = get_index_change([NYSE_TICKER])

    signal = compute_signal(nikkei, nyse)
    msg = (
        f"📊 Morning Signal\n"
        f"Nikkei: {nikkei:.2f}%\n"
        f"NYSE: {nyse:.2f}%\n"
        f"➡️ Signal: {signal}"
    )
    print(msg)
    send_telegram(msg)

if __name__ == "__main__":
    main()
