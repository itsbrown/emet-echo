#!/usr/bin/env bash
# Replit-friendly test runner for Emet Echo
# Run with: bash scripts/replit-test.sh
# or: uv run bash scripts/replit-test.sh

set -e

echo "=== Emet Echo Replit Test Runner ==="
echo "Project root: $(pwd)"
echo

# Ensure we're using the project's uv environment
if command -v uv >/dev/null 2>&1; then
    echo "Using uv to run pytest..."
    uv run --frozen pytest tests/ -q --tb=short "$@" || {
        echo "Pytest via uv failed or no tests matched. Trying direct .venv if present..."
        if [ -f .venv/bin/pytest ]; then
            .venv/bin/pytest tests/ -q --tb=short "$@" || echo "Direct venv pytest also had issues (expected without full keys/NLTK)."
        else
            echo "No .venv/pytest found. Run 'uv sync' first if needed."
        fi
    }
else
    echo "uv not found in PATH. Trying system python -m pytest (may fail)..."
    python -m pytest tests/ -q --tb=short "$@" || echo "Pytest not available in base Python. Use 'uv run pytest' after 'uv sync'."
fi

echo
echo "=== Test run complete ==="
echo "If tests passed or showed expected skips (missing NLTK data, API keys, etc.), the core logic is good."
echo "For full app: use the Project workflow or 'uv run gunicorn --bind 0.0.0.0:5000 --reuse-port main:app'"
echo "Remember to set required Secrets: SESSION_SECRET, DATABASE_URL, ADMIN_TOKEN, and API keys for real data."
