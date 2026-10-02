# PinFrames Collector

Standalone Pinterest home-feed collector. It signs in to Pinterest in a local Chromium window, collects the best available image URLs, and uploads them to the PinFrames cloud feed. Pinterest cookies and passwords stay on this computer.

## Setup

Clone this repository, then run these commands from the cloned repository folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
```

No manual `.env` setup is needed. Each run privately asks for the Render feed token; press Enter to reuse the saved token. If a token is rejected, the CLI asks again and retries. A verified token is saved in a permission-restricted, git-ignored `.env`. The Render service URL is built in, so it never prompts for it.

## Pinterest account commands

```bash
./.venv/bin/python collector.py --login
```

This opens the home feed in Chromium and waits until signed-in Pins appear, then waits 15 seconds for the feed to settle. Keep the window open until the command reports success. Signup/login artwork is ignored because only images inside Pin links are collected.

Sign out of the local Pinterest session:

```bash
./.venv/bin/python collector.py --logout
```

Replace the saved PinFrames feed token:

```bash
./.venv/bin/python collector.py --change-token
```

## Scrape and sync

Run this after login; use `--force` to ignore the shared refresh age:

```bash
./.venv/bin/python collector.py --force
```

For normal startup checks, run:

```bash
./.venv/bin/python collector.py
```

The collector checks the shared feed's refresh age and skips scraping if it is still fresh. Add `--force` to scrape and upload immediately. Every computer needs its own one-time Pinterest sign-in and private `.env`; only the image links and scrape timestamp sync to PinFrames. The token can be re-entered by deleting `.env` and running the collector again.