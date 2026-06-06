#!/bin/bash
set -e

# Emet Echo post-merge / deploy hook (updated after runtime DDL removal)
# - Use `uv` (preferred) or pip with pyproject.toml + uv.lock
# - Schema: no more auto ALTER/CREATE on every start. Use Alembic in future
#   or run explicit migrations. For fresh dev DB you can do:
#     python -c '
#     import os
#     os.environ.setdefault("DATABASE_URL", "sqlite:///dev.db")
#     os.environ.setdefault("SESSION_SECRET", "dev-only-secret")
#     from app import app, db
#     with app.app_context():
#         db.create_all()
#     '
#   (Note: some features assume Postgres; sqlite is for quick smoke tests only.)

echo "Post-merge: install deps with 'uv sync' or 'pip install -e .'"
# uv sync --frozen || pip install -e .[dev] || true

echo "Post-merge: running explicit schema migrations (safe to re-run)..."
python scripts/migrate.py || echo "Migrate script non-fatal (check logs if DB not ready yet)"

echo "Post-merge hook complete. For ongoing schema changes consider Alembic (see scripts/migrate.py header)."
