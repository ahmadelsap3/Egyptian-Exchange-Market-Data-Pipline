#!/usr/bin/env python3
"""Simple Massive.com API consumer (PoC).

This script calls a hypothetical Massive dashboard API endpoint using an API key and
saves the JSON response locally. Replace the endpoint and parsing logic with the
real API details when available.
"""
import argparse
import json
import os
from datetime import datetime

import requests


DEFAULT_ENDPOINT = "https://massive.com/dashboard/api/data"  # placeholder — change when precise endpoint known


def fetch_massive(endpoint: str, api_key: str) -> dict:
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    resp = requests.get(endpoint, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def save_json(data: dict, outdir: str, name_prefix: str = "massive"):
    os.makedirs(outdir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(outdir, f"{name_prefix}_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--api-key", default=None)
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("MASSIVE_API_KEY")
    if not api_key:
        raise SystemExit("MASSIVE_API_KEY must be provided as env var or --api-key")

    print(f"Fetching {args.endpoint} ...")
    data = fetch_massive(args.endpoint, api_key)
    save_json(data, args.outdir)


if __name__ == "__main__":
    main()
