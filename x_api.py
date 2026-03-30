import os
import logging
from datetime import datetime, timedelta, timezone

import requests

logger = logging.getLogger(__name__)

_BASE = "https://api.twitter.com/2"


def _bearer_token() -> str | None:
    """Read X_BEARER_TOKEN dynamically so runtime changes are picked up."""
    return os.environ.get("X_BEARER_TOKEN")


def _headers():
    return {"Authorization": f"Bearer {_bearer_token()}"}


def get_user_id(username: str) -> tuple[str | None, str | None]:
    """Look up a Twitter user ID by username.

    Returns (user_id, error_message). On success error_message is None.
    On failure user_id is None and error_message contains a human-readable description.
    """
    if not _bearer_token():
        return None, "X_BEARER_TOKEN is not configured."
    try:
        resp = requests.get(
            f"{_BASE}/users/by/username/{username}",
            headers=_headers(),
            timeout=10,
        )
        if resp.status_code == 401:
            return None, "X API authentication failed (401). Check your Bearer Token."
        if resp.status_code == 403:
            return None, "X API access denied (403). Your token may lack required permissions."
        if resp.status_code == 429:
            return None, "X API rate limit reached (429). Please try again later."
        if resp.status_code == 404:
            return None, f"X user @{username} not found."
        resp.raise_for_status()
        data = resp.json()
        uid = data.get("data", {}).get("id")
        if not uid:
            return None, f"X API returned no user ID for @{username}."
        return uid, None
    except requests.exceptions.ConnectionError:
        return None, "Could not reach the X API. Check your network connection."
    except requests.exceptions.Timeout:
        return None, "X API request timed out."
    except Exception as e:
        logger.warning(f"X API: could not get user ID for @{username}: {e}")
        return None, f"X API error for @{username}: {e}"


def fetch_recent_posts(username: str) -> tuple[list[dict], str | None]:
    """Fetch last 24h of tweets for the given username.

    Returns (posts_list, error_message). On success error_message is None.
    On failure posts_list is [] and error_message contains a human-readable description.
    """
    if not _bearer_token():
        return [], "X_BEARER_TOKEN is not configured."

    user_id, err = get_user_id(username)
    if err:
        return [], err

    start_time = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    try:
        resp = requests.get(
            f"{_BASE}/users/{user_id}/tweets",
            headers=_headers(),
            params={
                "start_time": start_time,
                "max_results": 100,
                "tweet.fields": "created_at,public_metrics",
                "exclude": "retweets,replies",
            },
            timeout=15,
        )
        if resp.status_code == 401:
            return [], "X API authentication failed (401). Check your Bearer Token."
        if resp.status_code == 403:
            return [], "X API access denied (403). Your token may lack required permissions."
        if resp.status_code == 429:
            return [], "X API rate limit reached (429). Please try again later."
        resp.raise_for_status()
        payload = resp.json()
        tweets = payload.get("data") or []
        result = []
        for t in tweets:
            metrics = t.get("public_metrics") or {}
            result.append(
                {
                    "handle": username,
                    "text": t.get("text", ""),
                    "tweet_id": t.get("id", ""),
                    "created_at": t.get("created_at", ""),
                    "likes": metrics.get("like_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                }
            )
        return result, None
    except requests.exceptions.ConnectionError:
        return [], "Could not reach the X API. Check your network connection."
    except requests.exceptions.Timeout:
        return [], "X API request timed out."
    except Exception as e:
        logger.warning(f"X API: error fetching tweets for @{username}: {e}")
        return [], f"X API error fetching tweets for @{username}: {e}"


def fetch_all_handle_posts() -> tuple[list[dict], str | None]:
    """Load all handles from DB and fetch their last-24h posts.

    Returns (posts_list, error_message). On success error_message is None.
    The list is sorted newest first. If any handle produces an API error the
    first error encountered is surfaced; posts that succeeded are still returned.
    """
    if not _bearer_token():
        return [], "X_BEARER_TOKEN is not configured."

    try:
        from models import XHandle
        handles = XHandle.query.order_by(XHandle.handle).all()
    except Exception as e:
        logger.warning(f"X API: could not load handles from DB: {e}")
        return [], f"Database error loading handles: {e}"

    all_posts: list[dict] = []
    first_error: str | None = None

    for h in handles:
        posts, err = fetch_recent_posts(h.handle)
        if err and first_error is None:
            first_error = err
        all_posts.extend(posts)

    def _sort_key(post):
        ts = post.get("created_at", "")
        try:
            return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ")
        except Exception:
            try:
                return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                return datetime.min

    all_posts.sort(key=_sort_key, reverse=True)

    if first_error and not all_posts:
        return [], first_error

    return all_posts, None
