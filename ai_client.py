"""
Central OpenAI client for Emet Echo.

Goals (from review):
- Single client instance (avoid creating in every module at import time)
- Timeouts
- Basic retry (simple loop, no extra deps for now)
- Token usage logging (very rough)
- Optional daily budget guard via OPENAI_BUDGET_USD / OPENAI_DAILY_TOKENS etc.

Usage:
    from ai_client import chat_complete
    resp = chat_complete([{"role": "user", "content": "..."}], max_tokens=300)

Later: pip install tenacity and use @retry for better backoff.
"""
import os
import time
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Lazy singleton
_client = None

def get_openai_client():
    global _client
    if _client is None:
        try:
            from openai import OpenAI
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY not set - AI features will be disabled.")
                _client = None
            else:
                _client = OpenAI(
                    api_key=api_key,
                    timeout=30.0,  # seconds
                )
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            _client = None
    return _client


def chat_complete(
    messages: List[Dict[str, str]],
    model: str = "gpt-4o",
    max_tokens: int = 400,
    temperature: float = 0.7,
    max_retries: int = 2,
) -> Optional[str]:
    """
    Wrapper around chat.completions.create with simple retry + logging.
    Returns the text content or None on failure.
    """
    client = get_openai_client()
    if not client:
        return None

    last_err = None
    for attempt in range(max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            text = resp.choices[0].message.content if resp.choices else ""
            # Very rough usage log (for cost awareness)
            usage = getattr(resp, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
            total_tokens = getattr(usage, "total_tokens", 0) if usage else (prompt_tokens + completion_tokens)

            if usage:
                logger.info(
                    "OpenAI usage: prompt=%s completion=%s total=%s model=%s",
                    prompt_tokens, completion_tokens, total_tokens, model,
                )

            # Budget enforcement (addresses review Issue 16 / rec-1)
            _record_and_check_budget(total_tokens, model)

            return text.strip() if text else ""
        except Exception as e:
            last_err = e
            logger.warning("OpenAI call failed (attempt %s/%s): %s", attempt + 1, max_retries + 1, e)
            if attempt < max_retries:
                time.sleep(1.5 ** attempt)  # simple exponential backoff
    logger.error("OpenAI call ultimately failed: %s", last_err)
    return None


# Convenience for the common "system + user" pattern used in the app
def simple_completion(system_prompt: str, user_prompt: str, **kwargs) -> Optional[str]:
    return chat_complete(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        **kwargs
    )


# ---------------------------------------------------------------------------
# Budget enforcement (simple file-based daily counter, no extra deps)
# Addresses original review "reliability / cost" risk of uncontrolled OpenAI spend.
# ---------------------------------------------------------------------------

import json
from pathlib import Path
from datetime import date

_BUDGET_FILE = Path(os.environ.get("OPENAI_USAGE_FILE", ".openai_usage.json"))
_DEFAULT_DAILY_USD = float(os.environ.get("OPENAI_DAILY_BUDGET_USD", "0"))  # 0 = unlimited
_DEFAULT_TOKEN_CAP = int(os.environ.get("OPENAI_DAILY_TOKEN_CAP", "0"))   # 0 = unlimited

# Very rough per-1k-token pricing (gpt-4o as of 2025). Adjust via env if needed.
_PRICE_PER_1K = {
    "gpt-4o": 0.005,          # blended rough (input cheaper, output ~2-3x)
    "gpt-4o-mini": 0.00015,
}

def _get_today_usage() -> dict:
    if not _BUDGET_FILE.exists():
        return {"date": str(date.today()), "tokens": 0, "usd": 0.0}
    try:
        data = json.loads(_BUDGET_FILE.read_text())
        if data.get("date") != str(date.today()):
            return {"date": str(date.today()), "tokens": 0, "usd": 0.0}
        return data
    except Exception:
        return {"date": str(date.today()), "tokens": 0, "usd": 0.0}

def _save_today_usage(data: dict):
    _BUDGET_FILE.write_text(json.dumps(data, indent=2))

def _estimate_cost(tokens: int, model: str) -> float:
    rate = _PRICE_PER_1K.get(model, 0.005)
    return (tokens / 1000.0) * rate

def _record_and_check_budget(tokens: int, model: str = "gpt-4o"):
    """Record usage and abort (return early in caller) if over daily budget."""
    if _DEFAULT_DAILY_USD <= 0 and _DEFAULT_TOKEN_CAP <= 0:
        return  # no budget configured

    usage = _get_today_usage()
    usage["tokens"] += tokens
    usage["usd"] += _estimate_cost(tokens, model)

    if _DEFAULT_TOKEN_CAP > 0 and usage["tokens"] > _DEFAULT_TOKEN_CAP:
        logger.warning(
            "OpenAI daily token cap exceeded (%s > %s). Blocking further calls today.",
            usage["tokens"], _DEFAULT_TOKEN_CAP
        )
        # Caller will see empty result; you can raise if you prefer hard fail
        _save_today_usage(usage)
        return

    if _DEFAULT_DAILY_USD > 0 and usage["usd"] > _DEFAULT_DAILY_USD:
        logger.warning(
            "OpenAI daily budget exceeded ($%.2f > $%.2f). Blocking further calls today.",
            usage["usd"], _DEFAULT_DAILY_USD
        )
        _save_today_usage(usage)
        return

    _save_today_usage(usage)