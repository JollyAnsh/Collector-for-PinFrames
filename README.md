# PinFrames Collector

Standalone Pinterest home-feed collector. It signs in to Pinterest in a local Chromium window, collects the best available image URLs, and uploads them to the PinFrames cloud feed. Pinterest cookies and passwords stay on this computer.

## Setup

Clone the repository. Launch `setup.command` on macOS, `setup.bat` on Windows, or `bash run-linux.sh` on Linux. On first run, the launcher downloads a local copy of `uv` and uses it to provide Python 3.12; no separate Python or `uv` installation is required. The bootstrap then creates the virtual environment and installs dependencies and Chromium. These runtime files and caches are kept in the collector folder. Later runs reuse them and only reinstall dependencies if `requirements.txt` changes. An internet connection is required for initial setup. On Linux, Chromium may also require system libraries provided by your distribution.

To remove the collector's installed runtime, dependencies, caches, and Chromium, run the platform launcher with `-delete` (for example, `./setup.command -delete` on macOS). This preserves the saved feed token and Pinterest login profile.

When `setup.command` is double-clicked in macOS Terminal, it opens an interactive shell after the collector finishes so the Terminal window stays available for more commands.

No manual `.env` setup is needed. Each run privately asks for the Render feed token; press Enter to reuse the saved token. If a token is rejected, the CLI asks again and retries. A verified token is saved in a permission-restricted, git-ignored `.env`. The Render service URL is built in, so it never prompts for it.

## Pinterest account commands

Run the platform launcher with `--login` (for example, `./setup.command --login` on macOS).

This opens the home feed in Chromium and waits until signed-in Pins appear, then waits 15 seconds for the feed to settle. Keep the window open until the command reports success. Signup/login artwork is ignored because only images inside Pin links are collected.

Sign out of the local Pinterest session:

Run the platform launcher with `--logout`.

Replace the saved PinFrames feed token:

Run the platform launcher with `--change-token`.

## Scrape and sync

Run this after login; use `--force` to ignore the shared refresh age:

Run the platform launcher with `--force`.

For normal startup checks, run:

Run the platform launcher with no options.

The collector checks the shared feed's refresh age and skips scraping if it is still fresh. Add `--force` to scrape and upload immediately. Every computer needs its own one-time Pinterest sign-in and private `.env`; only the image links and scrape timestamp sync to PinFrames. The token can be re-entered by deleting `.env` and running the collector again.