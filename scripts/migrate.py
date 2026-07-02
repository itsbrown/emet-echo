#!/usr/bin/env python
"""
Explicit schema migration / bootstrap script for Emet Echo.

Run this during deploy or for fresh DBs instead of the old runtime DDL that
used to execute on every app import.

Usage:
    python scripts/migrate.py

It is safe to run multiple times (uses IF NOT EXISTS / create_all).

For production evolution, prefer Alembic + Flask-Migrate:
    pip install alembic flask-migrate
    # then flask db init, migrate, upgrade etc.

This script keeps the previous "ensure columns/tables" logic that was
scattered in app.py (removed from runtime to improve reliability).
"""
import os
import sys

# Ensure we can import the app even if run from scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, logger
from sqlalchemy import text


def ensure_schema():
    with app.app_context():
        # 1. Create any tables defined in models that don't exist yet.
        #    (This is the equivalent of the old db.create_all() calls.)
        db.create_all()
        logger.info("Base tables ensured via create_all().")

        # 2. ExecutiveOrder columns (historical additions)
        try:
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE executive_order
                        ADD COLUMN IF NOT EXISTS ai_summary TEXT,
                        ADD COLUMN IF NOT EXISTS indie_vs_mainstream TEXT,
                        ADD COLUMN IF NOT EXISTS historical_context TEXT,
                        ADD COLUMN IF NOT EXISTS data_ties TEXT,
                        ADD COLUMN IF NOT EXISTS poll_yes INTEGER DEFAULT 0,
                        ADD COLUMN IF NOT EXISTS poll_no INTEGER DEFAULT 0,
                        ADD COLUMN IF NOT EXISTS ai_quip TEXT
                """))
                conn.commit()
            logger.info("ExecutiveOrder columns ensured.")
        except Exception as err:
            logger.warning("ExecutiveOrder column ensure skipped or failed (may be normal on SQLite or if columns exist): %s", err)

        # 3. Article columns (historical additions)
        try:
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE article
                        ADD COLUMN IF NOT EXISTS indie_vs_mainstream TEXT,
                        ADD COLUMN IF NOT EXISTS bias_score INTEGER,
                        ADD COLUMN IF NOT EXISTS omission_callouts TEXT
                """))
                conn.commit()
            logger.info("Article columns ensured.")
        except Exception as err:
            logger.warning("Article column ensure skipped or failed (may be normal): %s", err)

        # 4. x_handle table (used by admin X monitor)
        try:
            with db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS x_handle (
                        id SERIAL PRIMARY KEY,
                        handle VARCHAR(100) UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                conn.commit()
            logger.info("x_handle table ensured.")
        except Exception as err:
            logger.warning("x_handle table ensure skipped or failed (may be normal on non-Postgres): %s", err)

        logger.info("Schema migration / bootstrap complete.")


def ensure_nltk_data():
    """Ensure NLTK resources are downloaded (for summarizer).
    Downloads to default location (in Replit this is typically /home/runner/nltk_data).
    Safe to run multiple times; only downloads if missing.
    """
    try:
        import nltk
        resources = [
            ('punkt', 'tokenizers/punkt'),
            ('punkt_tab', 'tokenizers/punkt_tab'),
            ('stopwords', 'corpora/stopwords'),
        ]
        for name, path in resources:
            try:
                nltk.data.find(path)
                logger.info(f"NLTK resource {name} already available.")
            except LookupError:
                logger.info(f"Downloading NLTK {name} (this may take a moment on first run)...")
                nltk.download(name)
                logger.info(f"NLTK {name} downloaded.")
    except Exception as e:
        logger.warning(f"NLTK data ensure failed or skipped (may affect summarization): {e}")


if __name__ == "__main__":
    # Allow overriding DATABASE_URL etc from env for the script
    if not os.environ.get("DATABASE_URL"):
        print("Warning: DATABASE_URL not set. Using whatever is in the environment / .env")
    ensure_schema()
    ensure_nltk_data()
    print("Done. You can now start the app.")