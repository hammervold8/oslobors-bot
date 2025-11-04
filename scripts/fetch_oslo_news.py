#!/usr/bin/env python3
import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import urllib.request
import xml.etree.ElementTree as ET
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

DATA_DIR = Path("data")

FEEDS = {
    "e24": "https://e24.no/rss2/?seksjon=boers-og-finans",
    # use the one you saw in the browser 👇
    "dn": "https://services.dn.no/api/feed/rss/?categories=b%C3%B8rs&topics=",
}

OSLO_INDEX_KEYWORDS = [
    "børsen", "oslo børs", "oslobørs", "børsen åpner", "børsen stenger",
    "hovedindeksen", "obx", "omx", "omx oslo 20", "børsfall",
    "børsoppgang", "oljeprisen", "brent", "råolje",
]

def safe_url(url: str) -> str:
    parts = urlsplit(url)
    encoded_path = quote(parts.path)
    encoded_query = quote(parts.query, safe="=&,")
    return urlunsplit((parts.scheme, parts.netloc, encoded_path, encoded_query, parts.fragment))

def fetch(url: str) -> bytes:
    safe = safe_url(url)
    with urllib.request.urlopen(safe, timeout=10) as r:
        return r.read()

def parse_rss(xml_bytes: bytes, source: str):
    root = ET.fromstring(xml_bytes)
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        yield {
            "source": source,
            "title": title,
            "link": link,
            "description": desc,
            "published": pub,
        }

def is_oslo_relevant(item: dict) -> bool:
    text = f"{item['title']} {item['description']}".lower()
    return any(k in text for k in OSLO_INDEX_KEYWORDS)

def save_news_file(data: dict) -> Path:
    """Persist fetched news to timestamped JSON file and return the path."""
    tz = ZoneInfo("Europe/Oslo")
    now = datetime.now(tz)
    timestamp = now.strftime("%H%M-%d-%m-%Y")
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / f"oslo_news_{timestamp}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path

def collect_oslo_news(save: bool = True):
    """
    Fetch Oslo-relevant news from configured feeds.

    Returns a tuple of (data, saved_path). saved_path is None when save=False.
    """
    all_items = []

    for name, url in FEEDS.items():
        try:
            raw = fetch(url)
            for itm in parse_rss(raw, name):
                if is_oslo_relevant(itm):
                    all_items.append(itm)
        except Exception as e:
            # make error printing not crash on ø/å
            sys.stderr.buffer.write(f"ERR {name}: {e}\n".encode("utf-8", "replace"))

    # dedupe
    seen = set()
    filtered = []
    for itm in all_items:
        key = itm["link"] or itm["title"]
        if key in seen:
            continue
        seen.add(key)
        filtered.append(itm)

    output = {
        "fetched_at": int(time.time()),
        "count": len(filtered),
        "items": filtered,
    }

    saved_path = save_news_file(output) if save else None
    return output, saved_path

def main():
    data, _ = collect_oslo_news(save=True)
    print(json.dumps(data, ensure_ascii=False))

if __name__ == "__main__":
    main()
