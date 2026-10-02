# PinFrames Collector

Standalone Pinterest home-feed collector. It signs in to Pinterest in a local Chromium window, collects the best available image URLs, and uploads them to the PinFrames cloud feed. Pinterest cookies and passwords stay on this computer.

## Setup

Clone this repository, then run these commands from the `Collector` folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
```

Edit `.env` and set `PINFRAMES_FEED_TOKEN` to the current token from the Render service. Keep `.env` private; it is ignored by Git. The service URL is already filled in unless Render shows a different URL.

## First run on each computer

```bash
./.venv/bin/python collector.py --headed
```

Sign in to Pinterest in Chromium and keep the window open until the scrape completes. The local login is saved in `.pinterest-browser-profile/` for future runs on this computer.

## Later runs

```bash
./.venv/bin/python collector.py
```

The collector checks the shared feed's refresh age and skips scraping if it is still fresh. Add `--force` to scrape and upload immediately. Every computer needs its own one-time Pinterest sign-in and private `.env`; only the image links and scrape timestamp sync to PinFrames.