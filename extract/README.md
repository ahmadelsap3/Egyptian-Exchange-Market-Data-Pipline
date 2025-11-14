Extract directory
===============

This directory contains starter extractor scripts for the project.

Files:
- `kaggle/download_kaggle.py` — downloads the Kaggle dataset (uses the `kaggle` package and your `KAGGLE_USERNAME`/`KAGGLE_KEY` in env)
- `egx/scraper.py` — simple scraper for EGX homepage/ticker pages that saves raw JSON to `extract/egx`
- `massive/api_consumer.py` — simple API consumer example for Massive dashboard, stores JSON responses in `extract/massive`

Run examples (from repo root):

1) Kaggle dataset (requires `kaggle` CLI installed and credentials configured):

```bash
python extract/kaggle/download_kaggle.py --dataset saurabhshahane/egyptian-stock-exchange --outdir extract/kaggle/raw
```

2) EGX scraping (quick test):

```bash
python extract/egx/scraper.py --outdir extract/egx/raw
```

3) Massive API (use provided key in `.env` or pass via env):

```bash
MASSIVE_API_KEY=6xetVzZ1BUNVbeJTeJzuNu44g5EA5SGs python extract/massive/api_consumer.py --outdir extract/massive/raw
```

Notes
- These are starter scripts — treat them as PoCs. Add retries, robust parsing, rate-limit respect, and data validation before using in production.
