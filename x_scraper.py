import logging
import random
import time
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

_PROFILE_URL = "https://x.com/{handle}"


def _parse_count(text: str) -> int:
    """Convert abbreviated count strings like '1.2K', '3M' to int."""
    if not text:
        return 0
    text = text.strip().replace(",", "")
    try:
        if text.endswith("K") or text.endswith("k"):
            return int(float(text[:-1]) * 1_000)
        if text.endswith("M") or text.endswith("m"):
            return int(float(text[:-1]) * 1_000_000)
        if text.endswith("B") or text.endswith("b"):
            return int(float(text[:-1]) * 1_000_000_000)
        return int(float(text))
    except (ValueError, TypeError):
        return 0


def _parse_timestamp(aria_label: str | None, datetime_attr: str | None) -> str:
    """Return an ISO-8601 UTC timestamp string from tweet time element attrs."""
    if datetime_attr:
        return datetime_attr
    return ""


def fetch_handle_posts(page, handle: str) -> list[dict]:
    """Scrape recent posts from a single public X profile page.

    Returns a list of post dicts. Raises on navigation/parse failure.
    """
    url = _PROFILE_URL.format(handle=handle)
    logger.debug("Scraping X profile: %s", url)

    page.goto(url, wait_until="domcontentloaded", timeout=30_000)

    try:
        page.wait_for_selector("article[data-testid='tweet']", timeout=15_000)
    except PlaywrightTimeoutError:
        logger.warning("Timeout waiting for tweet articles for @%s", handle)
        return []

    articles = page.query_selector_all("article[data-testid='tweet']")
    posts: list[dict] = []

    for article in articles:
        try:
            text_el = article.query_selector("div[data-testid='tweetText']")
            text = text_el.inner_text() if text_el else ""

            time_el = article.query_selector("time")
            datetime_attr = time_el.get_attribute("datetime") if time_el else None
            created_at = _parse_timestamp(None, datetime_attr) or ""

            tweet_id = ""
            link_el = article.query_selector("a[href*='/status/']")
            if link_el:
                href = link_el.get_attribute("href") or ""
                parts = href.split("/status/")
                if len(parts) > 1:
                    tweet_id = parts[1].split("/")[0].split("?")[0]

            def _stat(testid: str) -> int:
                el = article.query_selector(f"button[data-testid='{testid}'] span[data-testid='app-text-transition-container']")
                if el:
                    return _parse_count(el.inner_text())
                el = article.query_selector(f"div[data-testid='{testid}'] span")
                if el:
                    return _parse_count(el.inner_text())
                return 0

            likes = _stat("like")
            retweets = _stat("retweet")
            views = 0
            views_el = article.query_selector("a[href*='/analytics'] span[data-testid='app-text-transition-container']")
            if views_el:
                views = _parse_count(views_el.inner_text())

            if not text and not tweet_id:
                continue

            posts.append(
                {
                    "handle": handle,
                    "text": text,
                    "tweet_id": tweet_id,
                    "created_at": created_at,
                    "likes": likes,
                    "retweets": retweets,
                    "views": views,
                }
            )
        except Exception as exc:
            logger.debug("Error parsing tweet article for @%s: %s", handle, exc)
            continue

    logger.info("Scraped %d posts for @%s", len(posts), handle)
    return posts


def fetch_all_handle_posts() -> tuple[list[dict], str | None]:
    """Load all handles from DB and scrape their public X profile pages.

    Returns (posts_list, error_message). Handles that fail are skipped with a
    warning log. Posts are sorted newest first.
    """
    try:
        from models import XHandle
        handles = XHandle.query.order_by(XHandle.handle).all()
    except Exception as exc:
        logger.warning("x_scraper: could not load handles from DB: %s", exc)
        return [], f"Database error loading handles: {exc}"

    if not handles:
        return [], None

    all_posts: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = context.new_page()

        for idx, h in enumerate(handles):
            if idx > 0:
                delay = random.uniform(0.5, 2.0)
                logger.debug("Sleeping %.2fs before next handle", delay)
                time.sleep(delay)
            try:
                posts = fetch_handle_posts(page, h.handle)
                all_posts.extend(posts)
            except Exception as exc:
                logger.warning("x_scraper: failed to scrape @%s: %s", h.handle, exc)

        context.close()
        browser.close()

    def _sort_key(post: dict):
        ts = post.get("created_at", "")
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                return datetime.strptime(ts, fmt)
            except Exception:
                continue
        return datetime.min

    all_posts.sort(key=_sort_key, reverse=True)
    return all_posts, None
