import json
import os
import pytest
from datetime import datetime

# Set minimal env before importing models (which pulls in app.py with validation)
os.environ.setdefault("SESSION_SECRET", "test-secret-123456789012345678901234567890")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# Minimal test that doesn't require full app/DB setup for the serializer.
# For full tests with Flask test client, use pytest-flask fixtures.

from models import Article  # This will trigger app import (needs env)

def test_article_to_public_dict_basic(monkeypatch):
    # Patch the db import side effects if needed, but since we have dummy in other tests...
    # Here we just instantiate a plain object (the method doesn't use db)
    art = Article(
        title="Test Article",
        url="https://example.com/test",
        source_name="Example Source",
        published_at=datetime(2025, 1, 20, 12, 0),
        author="Test Author",
        description="A short desc",
        content="Full content here for summary.",
        summary="A generated summary.",
        url_to_image="https://example.com/img.jpg",
        category="general",
        source_type="independent",
        indie_vs_mainstream=json.dumps({"indie": "good", "mainstream": "bad"}),
        bias_score=42,
        omission_callouts=json.dumps(["missed fact 1", "missed angle 2"]),
    )

    d = art.to_public_dict()

    assert d["title"] == "Test Article"
    assert d["url"] == "https://example.com/test"
    assert d["source"]["name"] == "Example Source"
    assert "2025-01-20" in d["publishedAt"]
    assert d["summary"] == "A generated summary."
    assert d["source_type"] == "independent"
    assert d["bias_score"] == 42
    assert d["ivm"] == {"indie": "good", "mainstream": "bad"}
    assert d["omission_callouts"] == ["missed fact 1", "missed angle 2"]


def test_article_to_public_dict_missing_fields():
    art = Article(
        title="Minimal",
        url="https://ex.com/min",
    )
    d = art.to_public_dict()
    assert d["title"] == "Minimal"
    assert d["ivm"] is None
    assert d["omission_callouts"] == []
    assert d["bias_score"] is None