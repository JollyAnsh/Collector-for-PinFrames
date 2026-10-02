import argparse
import getpass
import json
import os
import re
from pathlib import Path
import sys
import time
from datetime import datetime
from urllib.parse import urlsplit
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from dotenv import load_dotenv, set_key

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


HOMEFEED_URL = "https://in.pinterest.com/homefeed/"
ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / ".frame-state.json"
PROFILE_DIR = ROOT / ".pinterest-browser-profile"
ENV_FILE = ROOT / ".env"
DEFAULT_API_URL = "https://pinframes.onrender.com"
FEED_READY_SCRIPT = """() => {
    const path = location.pathname.toLowerCase();
    const isPinterestHomeFeed = location.hostname.endsWith('pinterest.com') && path.includes('homefeed');
    const isAuthRoute = /\/(login|signup|register)(\/|$)/i.test(path);
    const isPasswordForm = Array.from(document.querySelectorAll('input[type="password"]')).some(input => input.getClientRects().length);
    const pinImages = Array.from(document.querySelectorAll("a[href*='/pin/'] img"));
    const hasPinImage = pinImages.some(image => (image.currentSrc || image.src || '').includes('i.pinimg.com/'));
    return isPinterestHomeFeed && !isAuthRoute && !isPasswordForm && hasPinImage;
}"""


def prompt_for_feed_token():
    for attempt in range(3):
        token = getpass.getpass("PinFrames private feed token: ").strip()
        if not token:
            print("A private feed token is required.", file=sys.stderr)
            continue
        try:
            cloud_api_request("/api/auth", token, DEFAULT_API_URL)
        except RuntimeError as error:
            print(f"Feed token rejected: {error}", file=sys.stderr)
            continue
        save_feed_token(token)
        print("Verified and saved the private feed token in this folder's .env.")
        return token
    raise ValueError("Could not verify the feed token after three attempts.")


def configure_cloud(force_prompt=False):
    load_dotenv(ENV_FILE, override=True)
    saved_token = os.getenv("PINFRAMES_FEED_TOKEN", "").strip()
    if force_prompt or not saved_token:
        return DEFAULT_API_URL, prompt_for_feed_token()
    try:
        cloud_api_request("/api/auth", saved_token, DEFAULT_API_URL)
    except RuntimeError as error:
        print(f"Saved feed token rejected: {error}", file=sys.stderr)
        return DEFAULT_API_URL, prompt_for_feed_token()
    print("Saved feed token verified.")
    return DEFAULT_API_URL, saved_token


def save_feed_token(token):
    set_key(str(ENV_FILE), "PINFRAMES_FEED_TOKEN", token, quote_mode="always")
    try:
        ENV_FILE.chmod(0o600)
    except OSError:
        pass
    os.environ["PINFRAMES_FEED_TOKEN"] = token


def cloud_api_request(path, token, api_url, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        api_url.rstrip("/") + path,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="GET" if body is None else "POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"PinFrames API returned HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach the PinFrames API: {error.reason}") from error


def cloud_scrape_is_due(settings, force=False):
    if force:
        return True
    last_scraped_at = settings.get("last_scraped_at")
    if not isinstance(last_scraped_at, str) or not last_scraped_at:
        return True
    try:
        timestamp = datetime.fromisoformat(last_scraped_at.replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError, OverflowError):
        return True
    interval = settings.get("refresh_after_seconds", 86400)
    if isinstance(interval, bool) or not isinstance(interval, (int, float)) or interval < 60:
        interval = 86400
    return time.time() - timestamp >= interval


def record_successful_scrape():
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            state = {}
    except (OSError, ValueError):
        state = {}
    state["last_scrape_at"] = time.time()
    state["pinterest_signed_in"] = True
    temporary_file = STATE_FILE.with_name(STATE_FILE.name + ".tmp")
    temporary_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temporary_file.replace(STATE_FILE)


def sign_out_pinterest():
    user_data_dir = PROFILE_DIR
    if not user_data_dir.is_dir():
        return

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=True,
            viewport={"width": 1280, "height": 900},
        )
        context.clear_cookies()
        page = context.pages[0] if context.pages else context.new_page()
        for url in ("https://in.pinterest.com/", "https://www.pinterest.com/"):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.evaluate("localStorage.clear(); sessionStorage.clear();")
            except PlaywrightTimeoutError:
                continue
        context.close()


def wait_for_pinterest_feed(page, settle_delay_ms=0):
    try:
        page.wait_for_function(FEED_READY_SCRIPT, timeout=180000)
        if settle_delay_ms:
            page.wait_for_timeout(settle_delay_ms)
        if not page.evaluate(FEED_READY_SCRIPT):
            raise RuntimeError("Pinterest left the home feed during the delay.")
    except PlaywrightTimeoutError as error:
        raise RuntimeError(
            "Pinterest is still showing login/signup or the home feed did not load. "
            "Sign in and wait for the home-feed pins to appear."
        ) from error


def login_pinterest():
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1440, "height": 1000},
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(HOMEFEED_URL, wait_until="domcontentloaded", timeout=60000)
            wait_for_pinterest_feed(page, settle_delay_ms=15000)
        except (PlaywrightError, RuntimeError) as error:
            try:
                context.close()
            except PlaywrightError:
                pass
            raise RuntimeError(f"Pinterest sign-in was not completed: {error}") from error
        context.close()
    print("Pinterest sign-in saved on this computer.")


def collect_image_urls(page):
    urls = page.evaluate(
        """() => {
          const values = [];
                    for (const image of document.querySelectorAll("a[href*='/pin/'] img")) {
            values.push(image.currentSrc, image.src, image.getAttribute('data-src'));
            const srcset = image.getAttribute('srcset');
            if (srcset) {
              values.push(...srcset.split(',').map(candidate => candidate.trim().split(/\\s+/)[0]));
            }
          }
          return values.filter(Boolean);
        }"""
    )
    return {
        url.split("?")[0]
        for url in urls
        if urlsplit(url).hostname == "i.pinimg.com"
    }


def select_best_image_urls(urls):
    best_by_image = {}
    for url in urls:
        parts = urlsplit(url)
        path_parts = parts.path.strip("/").split("/")
        if len(path_parts) < 2:
            continue

        size = path_parts[0]
        if size == "originals":
            rank = float("inf")
        else:
            match = re.fullmatch(r"(\d+)x(?:\d+)?(?:_RS)?", size)
            if not match:
                continue
            rank = int(match.group(1))

        image_path = "/".join(path_parts[1:])
        candidate = parts._replace(query="", fragment="").geturl()
        previous = best_by_image.get(image_path)
        if previous is None or rank > previous[0]:
            best_by_image[image_path] = (rank, candidate)

    return {candidate for _, candidate in best_by_image.values()}


def main():
    parser = argparse.ArgumentParser(
        description="Collect image URLs visible in your Pinterest home feed."
    )
    parser.add_argument("--url", default=HOMEFEED_URL, help="Pinterest feed URL")
    parser.add_argument("--scrolls", type=int, default=10, help="Feed scrolls to load")
    parser.add_argument("--output", default="image-links.txt", help="Output text file")
    parser.add_argument("--headed", action="store_true", help="Show the browser while scraping")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--login", action="store_true", help="Sign in to Pinterest and verify the home feed")
    actions.add_argument("--logout", "--signout", dest="logout", action="store_true", help="Clear the saved Pinterest session")
    actions.add_argument("--change-token", "--set-token", dest="change_token", action="store_true", help="Replace the saved PinFrames feed token")
    parser.add_argument(
        "--pause", type=float, default=1.5, help="Seconds to wait after each scroll"
    )
    parser.add_argument("--force", action="store_true", help="Ignore the cloud refresh age and scrape now")
    args = parser.parse_args()

    if args.scrolls < 0 or args.pause < 0:
        parser.error("--scrolls and --pause must be non-negative")

    if args.logout:
        sign_out_pinterest()
        print("Pinterest session cleared on this computer.")
        return 0

    if args.login:
        try:
            login_pinterest()
        except (PlaywrightError, RuntimeError) as error:
            print(error, file=sys.stderr)
            return 1
        return 0

    try:
        api_url, api_token = configure_cloud(force_prompt=args.change_token)
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 2

    if args.change_token:
        return 0

    first_run = not PROFILE_DIR.is_dir()
    if first_run:
        args.headed = True
        print("First run on this computer: sign in to Pinterest in the browser window and leave it open until scraping finishes.")

    try:
        settings = cloud_api_request("/api/settings", api_token, api_url)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1

    if not args.headed and not cloud_scrape_is_due(settings, args.force):
        print("The saved PinFrames feed is still fresh; no scrape was started.")
        return 0

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image_urls = set()

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=not args.headed,
            viewport={"width": 1440, "height": 1000},
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
            wait_for_pinterest_feed(page, settle_delay_ms=15000 if args.headed else 0)

            image_urls.update(collect_image_urls(page))
            for _ in range(args.scrolls):
                page.evaluate("window.scrollBy(0, Math.max(window.innerHeight * 0.85, 600))")
                page.wait_for_timeout(int(args.pause * 1000))
                image_urls.update(collect_image_urls(page))

            page_url = page.url
            page_title = page.title()
        except PlaywrightError as error:
            try:
                context.close()
            except PlaywrightError:
                pass
            if "closed" in str(error).lower():
                print(
                    "Pinterest window closed before the scrape finished. "
                    "Click Log in again and keep the window open until completion.",
                    file=sys.stderr,
                )
            else:
                print(f"Pinterest scrape failed: {error}", file=sys.stderr)
            return 1
        context.close()

    best_image_urls = select_best_image_urls(image_urls)
    if not best_image_urls:
        print("No supported Pinterest image URLs found; output file was not changed.")
        print(f"Current page: {page_title} ({page_url})")
        if image_urls:
            print("Pinterest images were detected, but their URL sizes were not recognized.")
        else:
            print("Make sure you are signed in and the home feed finished loading before continuing.")
        return 1

    ordered_images = sorted(best_image_urls)
    try:
        cloud_api_request("/api/collect", api_token, api_url, {"images": ordered_images})
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1

    output_path.write_text("\n".join(ordered_images) + "\n", encoding="utf-8")
    record_successful_scrape()
    print(f"Saved {len(best_image_urls)} highest-resolution image links to {output_path}")
    print("Synced image links to the PinFrames cloud feed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())