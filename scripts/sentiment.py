#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from typing import List, Dict

import requests
from transformers import pipeline

from dotenv import load_dotenv
load_dotenv()

# -------- CONFIG -------- #

MODEL_NAME = "Kushtrim/norbert3-large-norsk-sentiment-sst2"

# Weight title more than description
TITLE_WEIGHT = 2.0
DESC_WEIGHT = 1.0

# Thresholds for aggregate sentiment -> trade signal
POS_THRESHOLD = 0.2   # above this -> BULL
NEG_THRESHOLD = -0.2  # below this -> BEAR

DATA_DIR = Path("data")  # where fetch_oslo_news.py saves json files


# -------- TELEGRAM -------- #

def send_telegram(message: str) -> None:
    """
    Send a message to Telegram using env vars:
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
    """
    
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("WARN: Telegram env vars missing, skipping send.", file=sys.stderr)
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if not r.ok:
            print(f"WARN: Telegram send failed: {r.status_code} {r.text}", file=sys.stderr)
    except Exception as e:
        print(f"WARN: Telegram send exception: {e}", file=sys.stderr)


# -------- DATA LOADING -------- #

def load_latest_news() -> Dict:
    """
    Load the latest oslo_news_*.json file from DATA_DIR.
    """
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Data directory {DATA_DIR} does not exist.")

    files = sorted(DATA_DIR.glob("oslo_news_*.json"))
    if not files:
        raise FileNotFoundError(f"No oslo_news_*.json files found in {DATA_DIR}")

    latest = files[-1]
    with latest.open(encoding="utf-8") as f:
        data = json.load(f)

    print(f"Using news file: {latest}", file=sys.stderr)
    return data


# -------- SENTIMENT MODEL -------- #

def build_pipeline():
    """
    Build a Hugging Face transformers sentiment pipeline.
    """
    clf = pipeline(
        "text-classification",
        model=MODEL_NAME,
        truncation=True,
        trust_remote_code=True
    )
    return clf


def score_text(clf, text: str) -> float:
    """
    Run sentiment on a single text and return a numeric score in [-1, 1]:
    positive -> +score, negative -> -score, neutral/other -> 0
    """
    text = (text or "").strip()
    if not text:
        return 0.0

    out = clf(text)[0]   # {'label': 'POSITIVE', 'score': 0.9} or LABEL_1 etc.
    label = str(out["label"]).upper()
    score = float(out["score"])

    # Handle both POSITIVE/NEGATIVE and LABEL_0/LABEL_1 styles
    if "NEG" in label or label.endswith("0"):
        return -score
    if "POS" in label or label.endswith("1"):
        return score
    return 0.0


def score_article(clf, item: Dict) -> float:
    """
    Compute a weighted sentiment score for one news item
    using title (heavier) and description.
    """
    title = item.get("title", "")
    desc = item.get("description", "")

    s_title = score_text(clf, title)
    s_desc = score_text(clf, desc)

    w_title = TITLE_WEIGHT if title.strip() else 0.0
    w_desc = DESC_WEIGHT if desc.strip() else 0.0
    total_w = w_title + w_desc

    if total_w == 0:
        return 0.0

    return (s_title * w_title + s_desc * w_desc) / total_w


def aggregate_scores(scores: List[float]) -> float:
    """
    Aggregate list of article scores to one overall score.
    Simple mean for now.
    """
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def score_to_signal(score: float) -> str:
    """
    Map aggregated score to a trade signal.
    """
    if score >= POS_THRESHOLD:
        return "BULL"
    if score <= NEG_THRESHOLD:
        return "BEAR"
    return "FLAT"


# -------- MAIN -------- #

def main():
    try:
        data = load_latest_news()
    except Exception as e:
        print(f"ERROR: could not load news: {e}", file=sys.stderr)
        return

    items = data.get("items", [])
    if not items:
        print("No news items found. Sending FLAT signal.", file=sys.stderr)
        send_telegram("📉 *OsloBot*: No relevant news items found. Signal: `FLAT` (no trade).")
        return

    clf = build_pipeline()

    article_scores = []
    for item in items:
        s = score_article(clf, item)
        article_scores.append((item, s))

    # overall score
    overall = aggregate_scores([s for _, s in article_scores])
    signal = score_to_signal(overall)

    # Build a readable message for Telegram
    lines = []
    lines.append(f"📰 *OsloBot sentiment*")
    lines.append(f"• Overall sentiment score: `{overall:.3f}`")
    lines.append(f"• Trade signal: *`{signal}`*")
    lines.append("")
    lines.append("_Top headlines:_")

    # Show top 3 by absolute sentiment
    top_articles = sorted(article_scores, key=lambda x: abs(x[1]), reverse=True)[:3]
    for item, s in top_articles:
        title = item.get("title", "").strip()
        src = item.get("source", "")
        lines.append(f"- ({src}) `{s:+.3f}` – {title}")

    message = "\n".join(lines)

    print(message)         # for logs
    send_telegram(message) # send to your phone

    # Optionally: also print raw JSON-like output if you want
    debug = {
        "overall_score": overall,
        "signal": signal,
        "article_scores": [
            {
                "title": i.get("title", ""),
                "source": i.get("source", ""),
                "score": s,
                "link": i.get("link", ""),
            }
            for i, s in article_scores
        ],
    }
    print(json.dumps(debug, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()