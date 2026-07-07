import html
import logging
import os
import re
import time
from datetime import datetime, timezone

import feedparser
import requests

logger = logging.getLogger(__name__)

RSSHUB_BASE_URL = os.environ.get("RSSHUB_BASE_URL", "https://rsshub.app").strip().rstrip("/").rstrip()

# Warn once if the base URL looks invalid (common misconfig causing 404 spam)
if "google.com" in RSSHUB_BASE_URL or not RSSHUB_BASE_URL.startswith(("http://", "https://")):
    logger.error("RSSHUB_BASE_URL appears invalid (%s). Falling back to https://rsshub.app . Fix the secret!", RSSHUB_BASE_URL)
    RSSHUB_BASE_URL = "https://rsshub.app"


def _parse_timestamp(value: str) -> str:
    """Normalise various timestamp formats to ISO-8601 UTC string."""
    if not value:
        return ""
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, TypeError):
            continue
    return value


def _strip_html(text: str) -> str:
    """Remove HTML tags and unescape HTML entities from text."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_handle_posts(handle: str) -> list[dict]:
    """Fetch recent posts for a single X handle via RSSHub.

    Returns a list of post dicts. Returns empty list on any fetch/parse error.
    """
    url = f"{RSSHUB_BASE_URL}/twitter/user/{handle}"
    logger.debug("Fetching RSSHub feed: %s", url)

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("x_scraper: RSSHub request failed for @%s: %s", handle, exc)
        return []

    feed = feedparser.parse(resp.text)

    if feed.bozo and not feed.entries:
        logger.warning("x_scraper: could not parse feed for @%s", handle)
        return []

    posts: list[dict] = []
    for entry in feed.entries:
        try:
            text = _strip_html(entry.get("summary") or entry.get("title") or "")
            link = entry.get("link") or ""
            tweet_id = ""
            if "/status/" in link:
                tweet_id = link.split("/status/")[-1].split("/")[0].split("?")[0]

            published = ""
            if entry.get("published"):
                published = _parse_timestamp(entry["published"])
            elif entry.get("updated"):
                published = _parse_timestamp(entry["updated"])

            if not text and not tweet_id:
                continue

            posts.append(
                {
                    "handle": handle,
                    "text": text,
                    "tweet_id": tweet_id,
                    "created_at": published,
                    "likes": 0,
                    "retweets": 0,
                    "views": 0,
                }
            )
        except Exception as exc:
            logger.debug("x_scraper: error parsing entry for @%s: %s", handle, exc)
            continue

    logger.info("Fetched %d posts for @%s", len(posts), handle)
    return posts


# Simple in-memory cache for X posts to avoid hammering RSSHub (and slowing / on every load)
_x_posts_cache = {"posts": [], "error": None, "ts": 0}
_X_CACHE_TTL = 300  # 5 minutes

def fetch_all_handle_posts() -> tuple[list[dict], str | None]:
    """Load all handles from DB and fetch their posts via RSSHub.

    Returns (posts_list, error_message). Handles that fail are skipped
    gracefully. Posts are sorted newest first.
    Uses short-lived cache to keep homepage responsive.
    """
    now = time.time()
    if now - _x_posts_cache["ts"] < _X_CACHE_TTL:
        return _x_posts_cache["posts"], _x_posts_cache["error"]

    try:
        from models import XHandle
        handles = XHandle.query.order_by(XHandle.handle).all()
    except Exception as exc:
        logger.warning("x_scraper: could not load handles from DB: %s", exc)
        return [], f"Database error loading handles: {exc}"

    if not handles:
        _x_posts_cache.update({"posts": [], "error": None, "ts": now})
        return [], None

    all_posts: list[dict] = []
    for h in handles:
        try:
            posts = fetch_handle_posts(h.handle)
            all_posts.extend(posts)
        except Exception as exc:
            logger.warning("x_scraper: failed to fetch @%s: %s", h.handle, exc)

    def _sort_key(post: dict):
        ts = post.get("created_at", "")
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
            try:
                return datetime.strptime(ts, fmt)
            except Exception:
                continue
        return datetime.min

    all_posts.sort(key=_sort_key, reverse=True)
    _x_posts_cache.update({"posts": all_posts, "error": None, "ts": now})
    return all_posts, None
