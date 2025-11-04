#!/usr/bin/env python3
import json
import time
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import urllib.request
import xml.etree.ElementTree as ET
import sys
from urllib.parse import quote, urlsplit, urlunsplit

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

def main():
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

    # 1) print (so GitHub Actions etc can read it)
    print(json.dumps(output, ensure_ascii=False))

    # 2) save to file (so your sentiment step can load it)
    # use Norway local time (Europe/Oslo) and include timezone abbreviation (CET/CEST)
    tz = ZoneInfo("Europe/Oslo")
    now = datetime.now(tz)
    # filename format requested: 24HR (HHMM)-DD-MM-YYYY plus TZ abbr (e.g. 0930-03-11-2025_CET)
    timestamp = now.strftime("%H%M-%d-%m-%Y")
    os.makedirs("data", exist_ok=True)
    filename = f"data/oslo_news_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()