import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    _openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except Exception:
    _openai_client = None

_cache = {}

_PLACEHOLDER_WEEKLY_DIGEST = (
    "This week's AI digest is currently unavailable. "
    "Please check back shortly as our editorial engine refreshes its analysis."
)

_PLACEHOLDER_MISSED_ANGLES = [
    "Underreported story analysis is temporarily unavailable.",
    "Our AI editorial team is refreshing its missed-angles report.",
    "Check back soon for overlooked perspectives from this week's news.",
    "Analysis of underreported stories will return shortly.",
]

_PLACEHOLDER_EO_PATTERNS = (
    "Our AI analysis of executive order issuance patterns is temporarily unavailable. "
    "Visit the EO Tracker for the latest data on executive orders issued by the current administration."
)


def _cache_key(label):
    now = datetime.now()
    return f"{label}_{now.strftime('%Y%m%d_%H')}"


def _is_fresh(label):
    stored_key = _cache.get(f"_key_{label}")
    return stored_key == _cache_key(label)


def _set_cached(label, value):
    _cache[label] = value
    _cache[f"_key_{label}"] = _cache_key(label)


def generate_weekly_digest(articles):
    label = "weekly_digest"
    if _is_fresh(label):
        return _cache.get(label, _PLACEHOLDER_WEEKLY_DIGEST)

    if not _openai_client:
        _set_cached(label, _PLACEHOLDER_WEEKLY_DIGEST)
        return _PLACEHOLDER_WEEKLY_DIGEST

    try:
        titles_and_descs = []
        for a in articles[:20]:
            title = a.get("title", "")
            desc = a.get("description") or a.get("summary") or ""
            if title:
                titles_and_descs.append(f"- {title}: {desc[:120]}")

        article_context = "\n".join(titles_and_descs) if titles_and_descs else "No articles available."

        prompt = (
            "You are a sharp, independent-minded editorial writer for Emet Echo, a conservative and independent "
            "news aggregator. Based on the following headlines and descriptions from this week's top articles, "
            "write a 2-3 paragraph AI Weekly Digest summarizing the major themes, key developments, and "
            "overarching narratives that emerged this week. Write in a clear, authoritative editorial voice. "
            "Do not use bullet points. Write in flowing prose.\n\n"
            f"Articles:\n{article_context}"
        )

        response = _openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.6
        )
        result = response.choices[0].message.content.strip()
        _set_cached(label, result)
        return result
    except Exception as e:
        logger.error(f"Error generating weekly digest: {e}")
        _set_cached(label, _PLACEHOLDER_WEEKLY_DIGEST)
        return _PLACEHOLDER_WEEKLY_DIGEST


def generate_missed_angles(articles):
    label = "missed_angles"
    if _is_fresh(label):
        return _cache.get(label, _PLACEHOLDER_MISSED_ANGLES)

    if not _openai_client:
        _set_cached(label, _PLACEHOLDER_MISSED_ANGLES)
        return _PLACEHOLDER_MISSED_ANGLES

    try:
        titles_and_descs = []
        for a in articles[:30]:
            title = a.get("title", "")
            desc = a.get("description") or a.get("summary") or ""
            if title:
                titles_and_descs.append(f"- {title}: {desc[:100]}")

        article_context = "\n".join(titles_and_descs) if titles_and_descs else "No articles available."

        prompt = (
            "You are an investigative editor at Emet Echo. Based on the following articles from this week, "
            "identify 4-6 underreported stories or overlooked angles that mainstream coverage missed or downplayed. "
            "Frame each as a short, punchy headline-style bullet (1-2 sentences max). "
            "Focus on stories that deserve more scrutiny from a conservative or independent perspective. "
            "You must return exactly 4 to 6 bullets. "
            "Return only the bullets as a numbered list, one per line, no preamble.\n\n"
            f"Articles:\n{article_context}"
        )

        response = _openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.7
        )
        raw = response.choices[0].message.content.strip()
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        bullets = []
        for line in lines:
            cleaned = line.lstrip("0123456789.-) ").strip()
            if cleaned:
                bullets.append(cleaned)

        if len(bullets) < 4:
            bullets = bullets + _PLACEHOLDER_MISSED_ANGLES[len(bullets):4]
        result = bullets[:6]
        _set_cached(label, result)
        return result
    except Exception as e:
        logger.error(f"Error generating missed angles: {e}")
        _set_cached(label, _PLACEHOLDER_MISSED_ANGLES)
        return _PLACEHOLDER_MISSED_ANGLES


def generate_eo_patterns_summary(eo_stats):
    """
    eo_stats: dict with keys:
      - total_count: int total EOs in DB
      - recent_eos: list of {title, date_issued, category} for most recent EOs
      - issuance_rate_per_day: float average EOs per day based on date range
      - admin_historical: dict of {administration_name: known_total_eos} for context
    """
    label = "eo_patterns"
    if _is_fresh(label):
        return _cache.get(label, _PLACEHOLDER_EO_PATTERNS)

    if not _openai_client:
        _set_cached(label, _PLACEHOLDER_EO_PATTERNS)
        return _PLACEHOLDER_EO_PATTERNS

    try:
        total_count = eo_stats.get("total_count", 0)
        recent_eos = eo_stats.get("recent_eos", [])
        rate = eo_stats.get("issuance_rate_per_day", 0)
        admin_historical = eo_stats.get("admin_historical", {})

        recent_lines = []
        for eo in recent_eos[:10]:
            title = eo.get("title", "")
            date = eo.get("date_issued", "")
            category = eo.get("category", "")
            if title:
                recent_lines.append(f"- {title} ({date}) [{category}]")
        recent_context = "\n".join(recent_lines) if recent_lines else "None available."

        hist_lines = []
        for admin, count in admin_historical.items():
            hist_lines.append(f"  {admin}: ~{count} total EOs over their full term")
        hist_context = "\n".join(hist_lines) if hist_lines else "  Historical data not available."

        prompt = (
            "You are a political historian and analyst writing for Emet Echo. "
            "Write a 3-5 sentence prose summary contextualizing executive order issuance rates. "
            "Use the statistics below — including recent EO count, issuance rate, and historical comparisons — "
            "to provide concrete, data-grounded analysis. "
            "Compare the current rate and themes to historical norms across recent administrations. "
            "Be concise, analytical, and balanced. Write in plain prose, no bullet points.\n\n"
            f"Current administration stats:\n"
            f"  Total EOs tracked in database: {total_count}\n"
            f"  Average issuance rate: {rate:.2f} EOs/day\n\n"
            f"Historical reference (approximate full-term totals):\n{hist_context}\n\n"
            f"Recent executive orders issued:\n{recent_context}"
        )

        response = _openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.5
        )
        result = response.choices[0].message.content.strip()
        _set_cached(label, result)
        return result
    except Exception as e:
        logger.error(f"Error generating EO patterns summary: {e}")
        _set_cached(label, _PLACEHOLDER_EO_PATTERNS)
        return _PLACEHOLDER_EO_PATTERNS
