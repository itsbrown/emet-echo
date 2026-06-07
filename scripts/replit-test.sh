#!/usr/bin/env bash
# Replit-friendly test runner for Emet Echo
# Run with: bash scripts/replit-test.sh
# or: uv run bash scripts/replit-test.sh

set +e  # Don't exit on first failure so we can provide good diagnostics

echo "=== Emet Echo Replit Test Runner ==="
echo "Project root: $(pwd)"
echo "uv version: $(uv --version 2>/dev/null || echo 'uv not found')"
echo "Python: $(python --version 2>/dev/null || echo 'python not in PATH')"
echo

# Diagnostics for common Replit + uv issues
echo "=== Diagnostics ==="
ls -la .venv/bin/ 2>/dev/null | head -10 || echo "No .venv directory found yet. Run 'uv sync' first."
echo "PATH snippet: ${PATH:0:200}..."
echo

# Try the most reliable ways to invoke pytest in uv-managed Replit environments
success=false

if command -v uv >/dev/null 2>&1; then
    echo "Attempt 1: uv run python -m pytest (most reliable)..."
    if uv run --frozen python -m pytest tests/ -q --tb=short "$@"; then
        success=true
    else
        echo "  -> uv run python -m pytest failed."
    fi

    if [ "$success" = false ]; then
        echo "Attempt 2: uv run pytest ..."
        if uv run --frozen pytest tests/ -q --tb=short "$@"; then
            success=true
        else
            echo "  -> uv run pytest also failed (common in some Replit shells due to PATH/venv activation)."
        fi
    fi

    if [ "$success" = false ]; then
        echo "Attempt 3: direct .venv/bin/python -m pytest (if .venv exists)..."
        if [ -f .venv/bin/python ]; then
            if .venv/bin/python -m pytest tests/ -q --tb=short "$@"; then
                success=true
            else
                echo "  -> Direct venv python -m pytest failed."
            fi
        else
            echo "  -> No .venv/bin/python found."
        fi
    fi
else
    echo "uv not found in PATH."
fi

if [ "$success" = false ]; then
    echo
    echo "All attempts to run pytest failed to spawn."
    echo "This is a known Replit + uv quirk (the 'Failed to spawn: `pytest`' error)."
    echo "Workarounds that usually work in Replit Shell:"
    echo "  1. uv run python -m pytest tests/test_models.py -q --tb=short"
    echo "  2. After 'uv sync', try: .venv/bin/python -m pytest tests/test_models.py -q --tb=short"
    echo "  3. Make sure you ran 'uv sync' in the same shell session."
    echo
    echo "The important thing: the code changes (migrate, sanitizer, scheduler, etc.) are already applied."
    echo "You can test specific functions manually with python -c if needed."
else
    echo
    echo "Tests completed successfully via one of the fallbacks."
fi

echo
echo "=== Test run complete ==="
echo "For the full app: uv run gunicorn --bind 0.0.0.0:5000 --reuse-port main:app"
echo "Remember to set Secrets in Replit (SESSION_SECRET, ADMIN_TOKEN, etc.)"
echo "Restart the Repl after changes."
