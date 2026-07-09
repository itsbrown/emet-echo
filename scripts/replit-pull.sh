#!/usr/bin/env bash
# Replit-friendly script to pull the latest commit from GitHub.
# Run this in the Replit Shell after any git/auth issues:
#
#   bash scripts/replit-pull.sh
#
# It will:
#   - Ensure the correct remote
#   - Fetch and hard-reset to origin/main (brings in all latest review fixes)
#   - Then remind you to run uv sync + migrate + tests

set -e

echo "=== Emet Echo Replit Pull Latest ==="
echo "Current dir: $(pwd)"
echo

# Make sure we are in the project root (Replit shell usually is, but be safe)
if [ ! -f "pyproject.toml" ] || [ ! -d "scripts" ]; then
    echo "ERROR: This does not look like the project root."
    echo "cd into the directory that contains pyproject.toml and scripts/, then re-run."
    exit 1
fi

echo "Fixing git remote..."
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/itsbrown/emet-echo.git

echo "Fetching from GitHub..."
git fetch origin

echo "Resetting workspace to latest main (this updates all files)..."
git reset --hard origin/main

echo
echo "=== Pull complete. Files are now at the latest commit. ==="
echo
echo "Next steps (copy/paste these):"
echo "  uv sync"
echo "  python scripts/migrate.py || echo 'Migration non-fatal'"
echo
echo ">>> IMPORTANT: Replit often serves stale template files until you fully restart."
echo "    1. In the Replit UI, click the STOP button on the running web app."
echo "    2. Wait 5-10 seconds."
echo "    3. Click RUN (or the big green play button)."
echo "    4. Wait for it to fully start (check Logs for 'Running on')."
echo
echo "Then hard-refresh your browser (Cmd+Shift+R or Ctrl+Shift+R)."
echo
echo "Verify the share buttons with:"
echo "  grep -A5 'for card in pattern_cards' templates/index.html | head -20"
echo
echo "Set your Secrets (SESSION_SECRET, ADMIN_TOKEN, etc.) if not already done."