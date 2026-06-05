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
            if usage:
                logger.info(
                    "OpenAI usage: prompt=%s completion=%s total=%s model=%s",
                    getattr(usage, "prompt_tokens", 0),
                    getattr(usage, "completion_tokens", 0),
                    getattr(usage, "total_tokens", 0),
                    model,
                )
            # TODO: add budget check here using env vars + persistent counter (redis/db)
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