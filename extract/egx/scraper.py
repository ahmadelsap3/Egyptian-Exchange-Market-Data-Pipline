#!/usr/bin/env python3
"""Simple EGX website scraper (PoC).

This script requests the EGX homepage and extracts available tickers and summary info.
It's a proof-of-concept: add politeness (sleep/backoff), robots.txt checks, and robust selectors
before production use.
"""
import argparse
import json
import os
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup


def scrape_homepage() -> dict:
    url = "https://www.egx.com.eg/en/homepage.aspx"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # PoC: attempt to find ticker table rows; selectors may need to be adapted for the real page
    tickers = []
    # Example: search for links or rows that look like tickers
    for a in soup.select("a"):
        txt = a.get_text(strip=True)
        if txt and len(txt) <= 6 and txt.isupper():
            tickers.append({"symbol": txt, "text": txt})

    return {"scraped_at": datetime.utcnow().isoformat(), "url": url, "tickers_sample": tickers[:50]}


def save_json(data: dict, outdir: str):
    os.makedirs(outdir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(outdir, f"egx_homepage_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", required=True, help="Output directory")
    args = parser.parse_args()

    print("Scraping EGX homepage (PoC). Respect robots.txt and rate limits in production.)")
    data = scrape_homepage()
    save_json(data, args.outdir)


if __name__ == "__main__":
    main()
