from fastapi import FastAPI, Request
from datetime import datetime
from telegram_utils import send_telegram
from sheets_utils import log_to_sheet
from signal_utils import compute_signal
# from broker_nordnet import place_order, close_position

app = FastAPI()

@app.get("/run")
async def run_job(job: str):
    now = datetime.now().isoformat()

    if job == "morning":
        # Fetch market data (placeholder)
        nikkei_ret, nyse_ret = 0.005, -0.002
        decision, raw = compute_signal(nikkei_ret, nyse_ret)

        # Example trade execution (replace with Nordnet call)
        # place_order(decision)

        msg = f"[{now}] Morning job: Signal={decision} (raw={raw:.4f})"
        log_to_sheet(job, decision, raw)
        send_telegram(msg)
        return {"status": "ok", "message": msg}

    elif job == "afternoon":
        # Example close
        # close_position()

        msg = f"[{now}] Afternoon job: Closing position"
        log_to_sheet(job, "close", None)
        send_telegram(msg)
        return {"status": "ok", "message": msg}

    else:
        return {"status": "error", "message": "Unknown job"}
