import os
import re
import json
import logging

from app import db

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    _openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except Exception:
    _openai_client = None


def generate_article_analysis(article):
    """
    Generate indie vs. mainstream AI analysis for a news article.
    Populates indie_vs_mainstream, bias_score, and omission_callouts fields.
    Stores results in the database (lazy, cached after first run).

    Args:
        article: Article ORM instance
    """
    if not _openai_client:
        logger.warning("OpenAI client not available — skipping article analysis")
        return

    source_text = article.content or article.description or article.summary or article.title or ""
    source_text = source_text[:4000]

    prompt = f"""You are an independent media analyst providing balanced coverage analysis of news articles.

Article Title: {article.title}
Source: {article.source_name or 'Unknown'}
Published: {article.published_at.strftime('%B %d, %Y') if article.published_at else 'Unknown'}

Article excerpt:
{source_text}

Analyze how independent/alternative media vs. mainstream media would cover this story differently.

Provide a JSON response with exactly these four keys:
1. "indie": 2-3 sentences on how independent or libertarian media tends to frame this story — skeptical angles, underreported details, civil liberties concerns, or what the mainstream missed.
2. "mainstream": 2-3 sentences on how mainstream/establishment media tends to frame this story — institutional framing, emphasis on official sources, or conventional narrative.
3. "bias_score": An integer from 0 to 100 representing the estimated coverage gap between indie and mainstream framing. 0 = no gap (both cover it identically), 100 = extreme gap (one side ignores it entirely). Use 40-60 for moderate gaps, 70+ for significant omissions.
4. "omission_callouts": A JSON array of 3-5 short strings (each under 20 words) naming specific angles, facts, or perspectives that mainstream outlets tended to omit or downplay for this story.

Return only valid JSON, no markdown fences."""

    try:
        response = _openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.5
        )
        raw = response.choices[0].message.content.strip()

        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

        data = json.loads(raw)

        ivm = {
            "indie": data.get("indie", ""),
            "mainstream": data.get("mainstream", "")
        }
        bias_score = max(0, min(100, int(data.get("bias_score", 50))))
        omissions = data.get("omission_callouts", [])
        if not isinstance(omissions, list):
            omissions = []

        article.indie_vs_mainstream = json.dumps(ivm)
        article.bias_score = bias_score
        article.omission_callouts = json.dumps(omissions)

        db.session.commit()
        logger.info(f"Article analysis generated and cached for article id={article.id}")

        return {
            "indie": ivm["indie"],
            "mainstream": ivm["mainstream"],
            "bias_score": bias_score,
            "omission_callouts": omissions
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OpenAI JSON response for article id={article.id}: {e}")
    except Exception as e:
        logger.error(f"Error generating article analysis for article id={article.id}: {e}")

    return None
