# Emet Echo - Conservative News Aggregator

## Overview

Emet Echo is a Flask-based news aggregation platform focused on conservative and independent news sources. The application scrapes and aggregates news from approved sources, generates AI-powered summaries using NLTK, and provides features like Trump executive order tracking, email newsletter subscriptions, and merchandise integration via Printify.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
- **Flask** with SQLAlchemy ORM for database operations
- Gunicorn as the production WSGI server (entry point: `main.py`)
- Blueprint pattern for modular route organization (e.g., `blueprints/email.py`)

### Database
- **PostgreSQL** via SQLAlchemy with connection pooling (`pool_recycle=300`, `pool_pre_ping=True`)
- Models defined in `models.py`: Article, UserPreference, SearchHistory, ExecutiveOrder, EmailSubscriber, XHandle
- Database URL configured via `DATABASE_URL` environment variable

### News Aggregation
- Custom scraper in `news_scraper.py` with curated list of approved conservative/independent sources
- NewsAPI integration for fetching trending articles
- Trafilatura for content extraction
- Background scheduler (`scheduler.py`) refreshes news every 15 minutes

### AI Summarization
- **NLTK** for text processing and extractive summarization
- Sentence tokenization and frequency-based sentence ranking
- Located in `summarizer.py`

### Email System
- **SendGrid** for transactional emails (confirmations, daily digests)
- Subscription management with confirmation tokens
- Daily digest emails sent at 8 AM via scheduler
- Email templates in `templates/emails/`

### Frontend
- Server-side rendering with Jinja2 templates
- Bootstrap 5 with dark theme
- Custom CSS in `static/css/styles.css`
- Client-side JavaScript for share functionality, lazy loading

### Printify Shop Integration
- **Service Module** (`printify.py`) - API client with rate limiting, caching, and error handling
- **Database Model** (`PrintifyProduct`) - Local caching of product data for performance
- **Shop URL** - `shop.emetecho.com` (Printify subdomain)
- **API Features**:
  - Bearer token authentication with proper User-Agent headers
  - 30-minute product caching to minimize API calls
  - Rate limit handling with exponential backoff (600 req/min global limit)
  - Graceful fallback when API is unavailable
- **Display Locations**:
  - Navigation bar "Shop" link
  - Homepage featured products grid (6 products)
  - Trump News page promotional banner
  - RFK Jr. Health page sidebar banner
  - Footer shop promotion on all pages

### Key Features
1. **News Feed** - Aggregated articles with AI summaries
2. **Executive Order Tracker** - Fetches from Federal Register API with AI summaries
3. **Email Newsletter** - Daily/weekly digests with preference management
4. **Search** - Keyword-based article search
5. **RFK Jr. Health News** - Dedicated section for health-related content
6. **Source Suggestions** - User submission for new sources
7. **Merchandise Shop** - Printify integration with featured products display
8. **X Posts Monitor** - Admin-curated list of X (Twitter) handles. Note: public RSSHub /twitter/ feeds are currently non-functional due to platform restrictions (see x_scraper.py and troubleshooting section).

### Authentication
- Session-based user identification using Flask sessions (SESSION_SECRET now strictly required)
- Email confirmation tokens for newsletter subscriptions
- No user login system - relies on session IDs for preferences
- Admin endpoints (e.g. /admin/x-handles) protected by ADMIN_TOKEN (see .env.example)

## External Dependencies

### APIs & Services
- **NewsAPI** (`NEWS_API_KEY`) - News article fetching
- **SendGrid** (`SENDGRID_API_KEY`) - Email delivery from `info@emetecho.com`
- **Printify** (`PRINTIFY_API_TOKEN`) - Merchandise integration at `shop.emetecho.com`
- **Federal Register API** - Executive order data

### Analytics & Advertising
- **Google Analytics** (G-3RSW54KBPR)
- **Google AdSense** (ca-pub-3252817577059646)

### Python Packages
- Flask, Flask-SQLAlchemy
- SendGrid Python SDK
- NLTK with punkt, stopwords
- Trafilatura for web scraping
- Requests for HTTP calls

### Database
- PostgreSQL (configured via `DATABASE_URL` environment variable)

### Configuration
- See .env.example (committed) for all variables. Copy to .env (git-ignored) and populate.
- Dev backdoors (e.g. /email/dev-confirm) and unauthenticated admin routes were removed/hardened post-review.
- Background scheduler: set RUN_SCHEDULER=1 in exactly one dedicated process/worker (gunicorn multi-worker deploys will otherwise run duplicate refresh loops). See .env.example and code comments in app.py.
- Schema migrations: run `python scripts/migrate.py` explicitly on deploy/fresh DB (no more auto DDL on import). Script lives in scripts/ and is called from post-merge.sh.

### Updating to the latest code from GitHub (in Replit)
The project is linked to https://github.com/itsbrown/emet-echo.git .

**Preferred method (Replit UI):**
1. In your Replit project, open the **Git** tab (left sidebar) or **Tools > Git**.
2. If not connected, click **Connect to GitHub** / "Link repository" and select `itsbrown/emet-echo`.
3. Once linked, click the **Pull** / "Pull changes" button to fetch the latest from `main`.
4. Replit will automatically run the `[postMerge]` hook (`scripts/post-merge.sh`), which does `uv sync` and `python scripts/migrate.py`.

**Fallback: Replit Shell commands (copy-paste this block):**
```bash
# Make sure you're in the project root (usually starts here)
pwd
ls -la | head -5

# Fix/set the Git remote (Replit sometimes uses internal remotes)
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/itsbrown/emet-echo.git

# Fetch and hard-reset to the latest pushed commit (this brings in all review fixes)
git fetch origin
git reset --hard origin/main

# Reinstall Python deps (uv is used by the project)
uv sync

# Run schema migration + NLTK data download (safe to re-run; this will fetch punkt/stopwords etc. if missing)
python scripts/migrate.py || echo "Migration non-fatal - check if DB is ready"

# Verify / run tests (use the improved Replit helper - it has extra fallbacks for the common "Failed to spawn: `pytest`" error)
bash scripts/replit-test.sh

# Direct reliable command if the helper still complains:
# uv run python -m pytest tests/test_models.py -q --tb=short

# Note: bare `pytest` or even plain `uv run pytest` often fails to spawn in Replit shells.
# Always prefer `uv run python -m pytest ...` after `uv sync`.

echo "Update complete. Restart the Repl / workflow for changes to take effect."
```

**Notes for the shell method:**
- If you get "access rights" or "repository exists" errors: Connect your GitHub account in Replit (click your avatar > Connections > GitHub) or generate a GitHub Personal Access Token (repo scope) and temporarily use:
  `git remote set-url origin https://YOUR_TOKEN@github.com/itsbrown/emet-echo.git`
- After `reset --hard`, all files (including the new `scripts/migrate.py`, tests, etc.) will be present.
- `uv run pytest` (not bare `pytest`) because pytest is managed by uv.
- The path error for `migrate.py` happens when the git reset didn't complete. Run the full block above.
- After update, restart the "Project" workflow or the whole Repl.
- New/optional env vars (see .env.example): `OPENAI_DAILY_BUDGET_USD`, `OPENAI_DAILY_TOKEN_CAP`, `RUN_SCHEDULER=1` for the background worker.

**Troubleshooting "healthcheck failed" + "Error when trying to publish" (common with autoscale deployment):**
- X/Twitter feed (x_scraper) is currently non-functional. Public RSSHub instances have largely stopped working for `/twitter/` endpoints due to Twitter/X's restrictions on scraping (often return 404 or empty feeds even with correct RSSHUB_BASE_URL=https://rsshub.app). This is not a config issue in the app. See x_scraper.py for improved warnings. Options to restore: self-host RSSHub with proper Twitter credentials/cookies, or remove/disable the X feed feature.
- / route is heavy on cold start (DB loads, x_scraper fetches for many handles, AI calls, printify). Healthchecks (on mapped port) timeout or 500.
  - Added lightweight `/health` endpoint (returns 200 fast, no work).
  - In Replit deployment advanced settings, set health check path to `/health` if available.
  - Set required Secrets before publish: SESSION_SECRET, DATABASE_URL, ADMIN_TOKEN (silences warning), RSSHUB_BASE_URL, and at least one API key (NEWS_API_KEY etc.). Missing keys cause graceful degradation but can contribute to slow/erring responses.
- Use `bash scripts/replit-test.sh` (or `uv run python -m pytest ...`) to validate locally in shell.
- The app may take time to become responsive; autoscale is strict on initial healthchecks.

If the UI Git integration is not working, the shell reset method above is the most reliable way to get the latest code (including all review fixes for security, reliability, tests, etc.).