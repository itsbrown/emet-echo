import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from datetime import datetime, timedelta
import json
import requests
import threading
import uuid
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from summarizer import generate_summary
from news_scraper import fetch_news, search_news
from scheduler import start_scheduler
import printify

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy with Flask
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
# Initialize the app with the extension
db.init_app(app)

# Custom Jinja2 filter: convert raw HTML to human-readable plain text,
# preserving paragraph/line structure for legacy DB records that may
# contain raw HTML from before the ingest-time extraction was added.
from html_utils import extract_plain_text as _html_to_text

@app.template_filter('html_to_text')
def html_to_text_filter(value):
    if not value:
        return value
    if '<' in value and '>' in value:
        return _html_to_text(value)
    return value

# Register blueprints
from blueprints.email import email_bp, init_app as init_email_blueprint

# Register the email blueprint
app.register_blueprint(email_bp)

# Initialize the email blueprint with app context
with app.app_context():
    init_email_blueprint(app, db)

# Auto-migrate: ensure new ExecutiveOrder columns exist on every startup
with app.app_context():
    try:
        with db.engine.connect() as conn:
            from sqlalchemy import text
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
        logger.info("ExecutiveOrder schema migration applied (IF NOT EXISTS).")
    except Exception as _mig_err:
        logger.warning(f"Schema migration skipped or failed (may be normal): {_mig_err}")

# Auto-migrate: ensure new Article columns exist on every startup
with app.app_context():
    try:
        with db.engine.connect() as conn:
            from sqlalchemy import text as _text
            conn.execute(_text("""
                ALTER TABLE article
                    ADD COLUMN IF NOT EXISTS indie_vs_mainstream TEXT,
                    ADD COLUMN IF NOT EXISTS bias_score INTEGER,
                    ADD COLUMN IF NOT EXISTS omission_callouts TEXT
            """))
            conn.commit()
        logger.info("Article schema migration applied (IF NOT EXISTS).")
    except Exception as _mig_err2:
        logger.warning(f"Article schema migration skipped or failed (may be normal): {_mig_err2}")

def _safe_json_loads(value, default=None):
    """Parse JSON string safely, returning default on failure or when value is falsy."""
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default

# Startup backfill: generate ai_quip for orders that have ai_summary but no ai_quip (max 20)
with app.app_context():
    try:
        from models import ExecutiveOrder as _EO
        from executive_orders import generate_ai_quip as _gen_quip
        _backfill_orders = _EO.query.filter(
            _EO.ai_summary.isnot(None),
            _EO.ai_quip.is_(None)
        ).limit(20).all()
        for _o in _backfill_orders:
            try:
                _gen_quip(_o)
            except Exception as _qe:
                logger.warning(f"Quip backfill skipped for {_o.order_number}: {_qe}")
        if _backfill_orders:
            logger.info(f"ai_quip backfill completed for {len(_backfill_orders)} orders.")
    except Exception as _bf_err:
        logger.warning(f"ai_quip backfill skipped: {_bf_err}")

# Clear cached AI summaries so all EOs get re-analyzed with the America First perspective
with app.app_context():
    try:
        from sqlalchemy import text as _text
        with db.engine.connect() as _conn:
            _conn.execute(_text("""
                UPDATE executive_order
                SET ai_summary = NULL,
                    indie_vs_mainstream = NULL,
                    historical_context = NULL,
                    data_ties = NULL
                WHERE ai_summary IS NOT NULL
                   OR indie_vs_mainstream IS NOT NULL
                   OR historical_context IS NOT NULL
                   OR data_ties IS NOT NULL
            """))
            _conn.commit()
        logger.info("Cleared cached AI summaries for America First re-analysis.")
    except Exception as _clear_err:
        logger.warning(f"AI cache clear skipped or failed: {_clear_err}")

# Ensure user has a session ID
def get_or_create_user_id():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return session['user_id']

# In-memory cache for news articles
news_data = {
    "trending": [],
    "last_updated": None,
    "by_keyword": {}
}

def initialize_data():
    """Initialize data with trending news and store in database"""
    global news_data
    try:
        from models import Article
        
        # Fetch new articles from the API
        articles = fetch_news()
        stored_articles = []
        
        # Process each article
        for article_data in articles:
            # Check if article with same URL already exists in database
            existing_article = Article.query.filter_by(url=article_data.get('url', '')).first()
            
            if not existing_article:
                # Create new article in database
                new_article = Article(
                    title=article_data.get('title', 'No Title'),
                    url=article_data.get('url', ''),
                    source_name=article_data.get('source', {}).get('name', '') if article_data.get('source') else '',
                    source_url=article_data.get('source', {}).get('url', '') if article_data.get('source') else '',
                    published_at=datetime.fromisoformat(article_data.get('publishedAt', '').replace('Z', '+00:00')) if article_data.get('publishedAt') else None,
                    author=article_data.get('author', ''),
                    description=article_data.get('description', ''),
                    content=article_data.get('content', ''),
                    url_to_image=article_data.get('urlToImage', ''),
                    category=article_data.get('category', 'general'),
                    source_type='conservative' if any(source in article_data.get('url', '') for source in ['foxnews', 'breitbart', 'dailywire', 'nypost', 'washingtontimes', 'theepochtimes']) else 'independent'
                )
                
                # Generate summary if content is available
                if article_data.get('content'):
                    try:
                        new_article.summary = generate_summary(article_data.get('content'))
                    except Exception as sum_err:
                        logger.error(f"Error generating summary: {str(sum_err)}")
                        new_article.summary = "Summary not available."
                
                # Add to database
                db.session.add(new_article)
                
                # Add to list for in-memory cache
                stored_articles.append(article_data)
            else:
                # Use the existing article (could update here if needed)
                article_dict = {
                    'title': existing_article.title,
                    'url': existing_article.url,
                    'source': {'name': existing_article.source_name},
                    'publishedAt': existing_article.published_at.isoformat() if existing_article.published_at else '',
                    'author': existing_article.author,
                    'description': existing_article.description,
                    'content': existing_article.content,
                    'summary': existing_article.summary,
                    'urlToImage': existing_article.url_to_image,
                    'published_time': existing_article.published_at.strftime("%B %d, %Y") if existing_article.published_at else ''
                }
                stored_articles.append(article_dict)
        
        # Commit all database changes
        db.session.commit()
        
        # Update in-memory cache
        news_data["trending"] = stored_articles
        news_data["last_updated"] = datetime.now()
        
        # Initialize executive orders database with fresh data from Federal Register API
        from executive_orders import initialize_executive_orders
        # Force refresh to ensure we have the latest data from Federal Register API
        initialize_executive_orders(force_refresh=True)
        
        logger.info(f"Initialized with {len(stored_articles)} trending articles")
    except Exception as e:
        logger.error(f"Error initializing data: {str(e)}")
        news_data["trending"] = []
        news_data["last_updated"] = datetime.now()

# Function to ensure initialization happens in an app context
def initialize_with_app_context():
    with app.app_context():
        initialize_data()

# Background initialization to avoid blocking app startup
threading.Thread(target=initialize_with_app_context).start()

# Start the scheduler for periodic updates (wrapped in app context)
def start_scheduler_with_context():
    with app.app_context():
        start_scheduler(news_data)
        
threading.Thread(target=start_scheduler_with_context).start()

@app.route('/')
def index():
    """Display trending news on the homepage"""
    last_updated = news_data["last_updated"]
    formatted_time = last_updated.strftime("%Y-%m-%d %H:%M:%S") if last_updated else "Never"
    
    try:
        # Get articles from database (most recent first)
        from models import Article
        db_articles = Article.query.order_by(Article.published_at.desc()).limit(50).all()
        
        # If we have articles in the database, convert them to the expected format
        if db_articles:
            articles = []
            for article in db_articles:
                article_dict = {
                    'title': article.title,
                    'url': article.url,
                    'source': {'name': article.source_name},
                    'publishedAt': article.published_at.isoformat() if article.published_at else '',
                    'author': article.author,
                    'description': article.description,
                    'content': article.content,
                    'summary': article.summary,
                    'urlToImage': article.url_to_image,
                    'published_time': article.published_at.strftime("%B %d, %Y") if article.published_at else '',
                    'source_type': article.source_type,
                    'bias_score': article.bias_score,
                    'ivm': _safe_json_loads(article.indie_vs_mainstream),
                    'omission_callouts': _safe_json_loads(article.omission_callouts, default=[])
                }
                articles.append(article_dict)
            
            # Update the in-memory cache with the database results
            news_data["trending"] = articles
            
            # Log the success
            logger.info(f"Loaded {len(articles)} articles from database")
        else:
            # If no articles in database yet, use the in-memory cache
            articles = news_data["trending"]
            logger.info(f"Using {len(articles)} articles from in-memory cache")
    except Exception as e:
        # If there's an error, fall back to in-memory cache
        logger.error(f"Error loading articles from database: {str(e)}")
        articles = news_data["trending"]
    
    # Generate AI content using full article pool (pre-cap)
    from home_ai import generate_weekly_digest, generate_missed_angles, generate_eo_patterns_summary
    
    weekly_digest = generate_weekly_digest(articles)
    missed_angles = generate_missed_angles(articles)
    
    # Fetch EO issuance stats for patterns summary
    try:
        from models import ExecutiveOrder
        eo_records = ExecutiveOrder.query.order_by(ExecutiveOrder.date_issued.desc()).limit(15).all()
        total_eo_count = ExecutiveOrder.query.count()
        
        recent_eos = [
            {
                'title': eo.title,
                'date_issued': eo.date_issued.strftime('%Y-%m-%d') if eo.date_issued else '',
                'category': eo.category or ''
            }
            for eo in eo_records
        ]
        
        issuance_rate = 0.0
        if eo_records and len(eo_records) >= 2:
            dates = [eo.date_issued for eo in eo_records if eo.date_issued]
            if len(dates) >= 2:
                oldest = min(dates)
                newest = max(dates)
                days_span = max((newest - oldest).days, 1)
                issuance_rate = total_eo_count / days_span
        
        eo_stats = {
            'total_count': total_eo_count,
            'recent_eos': recent_eos,
            'issuance_rate_per_day': issuance_rate,
            'admin_historical': {
                'Reagan (2 terms)': 381,
                'Clinton (2 terms)': 364,
                'Bush 43 (2 terms)': 291,
                'Obama (2 terms)': 276,
                'Trump 1st term (1 term)': 220,
                'Biden (1 term)': 162,
            }
        }
    except Exception as eo_err:
        logger.error(f"Error fetching EO data for home AI: {eo_err}")
        eo_stats = {'total_count': 0, 'recent_eos': [], 'issuance_rate_per_day': 0.0, 'admin_historical': {}}
    
    eo_patterns_summary = generate_eo_patterns_summary(eo_stats)
    
    # Cap articles to ~8 for the home page grid (~40% of content)
    display_articles = articles[:8]
    
    featured_products = printify.get_featured_products(6)

    # EO Watch: 3 most recent EOs with an ai_quip
    latest_eos = []
    try:
        from models import ExecutiveOrder as _EO_home
        latest_eos = _EO_home.query.filter(
            _EO_home.ai_quip.isnot(None),
            _EO_home.ai_quip != ''
        ).order_by(_EO_home.date_issued.desc()).limit(3).all()
    except Exception as _eo_home_err:
        logger.error(f"Error fetching latest EOs for homepage: {_eo_home_err}")
        latest_eos = []
    
    return render_template('index.html', 
                          articles=display_articles, 
                          last_updated=formatted_time,
                          search_query=None,
                          featured_products=featured_products,
                          weekly_digest=weekly_digest,
                          missed_angles=missed_angles,
                          eo_patterns_summary=eo_patterns_summary,
                          latest_eos=latest_eos)

@app.route('/search')
def search():
    """Search news by keyword"""
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('index'))
    
    # Save search to history
    try:
        from models import SearchHistory
        user_id = get_or_create_user_id()
        search_history = SearchHistory(user_id=user_id, query=query)
        db.session.add(search_history)
        db.session.commit()
    except Exception as e:
        logger.error(f"Error saving search history: {str(e)}")
    
    # Check if we already have results for this keyword
    if query in news_data["by_keyword"] and news_data["by_keyword"][query]["timestamp"] > datetime.now() - timedelta(hours=1):
        articles = news_data["by_keyword"][query]["articles"]
        logger.info(f"Using cached results for '{query}' with {len(articles)} articles")
    else:
        try:
            from models import Article
            
            # Check if query is a site-specific search
            if query.startswith("site:"):
                domain = query.split("site:")[1].strip()
                articles_from_api = search_news(query)
                
                # Also search database for existing articles from this domain
                db_articles = Article.query.filter(Article.url.like(f"%{domain}%")).all()
                
                # Convert DB articles to dictionary format
                db_articles_dict = []
                for article in db_articles:
                    article_dict = {
                        'title': article.title,
                        'url': article.url,
                        'source': {'name': article.source_name},
                        'publishedAt': article.published_at.isoformat() if article.published_at else '',
                        'author': article.author,
                        'description': article.description,
                        'content': article.content,
                        'summary': article.summary,
                        'urlToImage': article.url_to_image,
                        'published_time': article.published_at.strftime("%B %d, %Y") if article.published_at else ''
                    }
                    db_articles_dict.append(article_dict)
                
                # Combine results from API and database, avoiding duplicates
                existing_urls = set(a.get('url', '') for a in articles_from_api)
                for db_article in db_articles_dict:
                    if db_article['url'] not in existing_urls:
                        articles_from_api.append(db_article)
                        
                articles = articles_from_api
            else:
                # Regular keyword search
                articles_from_api = search_news(query)
                
                # Also search database for articles matching the keyword
                db_articles = Article.query.filter(
                    db.or_(
                        Article.title.ilike(f"%{query}%"),
                        Article.description.ilike(f"%{query}%"),
                        Article.content.ilike(f"%{query}%")
                    )
                ).all()
                
                # Convert DB articles to dictionary format
                db_articles_dict = []
                for article in db_articles:
                    article_dict = {
                        'title': article.title,
                        'url': article.url,
                        'source': {'name': article.source_name},
                        'publishedAt': article.published_at.isoformat() if article.published_at else '',
                        'author': article.author,
                        'description': article.description,
                        'content': article.content,
                        'summary': article.summary,
                        'urlToImage': article.url_to_image,
                        'published_time': article.published_at.strftime("%B %d, %Y") if article.published_at else ''
                    }
                    db_articles_dict.append(article_dict)
                
                # Combine results from API and database, avoiding duplicates
                existing_urls = set(a.get('url', '') for a in articles_from_api)
                for db_article in db_articles_dict:
                    if db_article['url'] not in existing_urls:
                        articles_from_api.append(db_article)
                        
                articles = articles_from_api
            
            # Process and store new articles in database
            for article_data in articles:
                # Skip if no URL
                if not article_data.get('url'):
                    continue
                    
                # Check if article with same URL already exists in database
                existing_article = Article.query.filter_by(url=article_data.get('url', '')).first()
                
                if not existing_article:
                    # Create new article in database
                    new_article = Article(
                        title=article_data.get('title', 'No Title'),
                        url=article_data.get('url', ''),
                        source_name=article_data.get('source', {}).get('name', '') if article_data.get('source') else '',
                        source_url=article_data.get('source', {}).get('url', '') if article_data.get('source') else '',
                        published_at=datetime.fromisoformat(article_data.get('publishedAt', '').replace('Z', '+00:00')) if article_data.get('publishedAt') else None,
                        author=article_data.get('author', ''),
                        description=article_data.get('description', ''),
                        content=article_data.get('content', ''),
                        url_to_image=article_data.get('urlToImage', ''),
                        category=article_data.get('category', 'general'),
                        source_type='conservative' if any(source in article_data.get('url', '') for source in ['foxnews', 'breitbart', 'dailywire', 'nypost', 'washingtontimes', 'theepochtimes']) else 'independent'
                    )
                    
                    # Generate summary if content is available
                    if article_data.get('content') and not article_data.get('summary'):
                        try:
                            new_article.summary = generate_summary(article_data.get('content'))
                            article_data['summary'] = new_article.summary
                        except Exception as sum_err:
                            logger.error(f"Error generating summary: {str(sum_err)}")
                            new_article.summary = "Summary not available."
                            article_data['summary'] = "Summary not available."
                    
                    # Add to database
                    db.session.add(new_article)
            
            # Commit all database changes
            db.session.commit()
            
            # Cache the results
            news_data["by_keyword"][query] = {
                "articles": articles,
                "timestamp": datetime.now()
            }
            
            logger.info(f"Fetched {len(articles)} articles for '{query}'")
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            flash(f"Error searching for '{query}': {str(e)}", "danger")
            articles = []
    
    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # EO Watch: pass empty list for search results page
    latest_eos = []
    try:
        from models import ExecutiveOrder as _EO_search
        latest_eos = _EO_search.query.filter(
            _EO_search.ai_quip.isnot(None),
            _EO_search.ai_quip != ''
        ).order_by(_EO_search.date_issued.desc()).limit(3).all()
    except Exception as _eo_s_err:
        logger.error(f"Error fetching latest EOs for search page: {_eo_s_err}")
        latest_eos = []
    
    return render_template('index.html', 
                          articles=articles, 
                          last_updated=last_updated,
                          search_query=query,
                          latest_eos=latest_eos)

@app.route('/article/<path:article_url>')
def article_detail(article_url):
    """Display detailed view of an article"""
    # Find the article in our data
    article = None
    
    try:
        # First try to find the article in the database
        from models import Article
        db_article = Article.query.filter_by(url=article_url).first()
        
        if db_article:
            # Lazy-generate indie vs mainstream analysis if not yet cached
            if db_article.indie_vs_mainstream is None:
                try:
                    from article_analysis import generate_article_analysis
                    generate_article_analysis(db_article)
                except Exception as _aa_err:
                    logger.error(f"Article analysis generation failed: {_aa_err}")

            # Parse indie_vs_mainstream JSON for template
            ivm = None
            if db_article.indie_vs_mainstream:
                try:
                    ivm = json.loads(db_article.indie_vs_mainstream)
                except Exception:
                    ivm = None

            omission_callouts = []
            if db_article.omission_callouts:
                try:
                    omission_callouts = json.loads(db_article.omission_callouts)
                except Exception:
                    omission_callouts = []

            # Convert DB article to dictionary format for template
            article = {
                'title': db_article.title,
                'url': db_article.url,
                'source': {'name': db_article.source_name},
                'publishedAt': db_article.published_at.isoformat() if db_article.published_at else '',
                'author': db_article.author,
                'description': db_article.description,
                'content': db_article.content,
                'summary': db_article.summary,
                'urlToImage': db_article.url_to_image,
                'published_time': db_article.published_at.strftime("%B %d, %Y") if db_article.published_at else '',
                'ivm': ivm,
                'bias_score': db_article.bias_score,
                'omission_callouts': omission_callouts
            }
        else:
            # If not found in DB, check in-memory cache
            # Check trending articles
            for a in news_data["trending"]:
                if a.get('url') == article_url:
                    article = a
                    break
            
            # Check keyword search results if not found
            if article is None:
                for keyword, data in news_data["by_keyword"].items():
                    for a in data["articles"]:
                        if a.get('url') == article_url:
                            article = a
                            break
                    if article:
                        break
            
            # If found in cache but not DB, store in DB for future
            if article:
                new_article = Article(
                    title=article.get('title', 'No Title'),
                    url=article.get('url', ''),
                    source_name=article.get('source', {}).get('name', '') if article.get('source') else '',
                    source_url=article.get('source', {}).get('url', '') if article.get('source') else '',
                    published_at=datetime.fromisoformat(article.get('publishedAt', '').replace('Z', '+00:00')) if article.get('publishedAt') else None,
                    author=article.get('author', ''),
                    description=article.get('description', ''),
                    content=article.get('content', ''),
                    summary=article.get('summary', ''),
                    url_to_image=article.get('urlToImage', ''),
                    category=article.get('category', 'general'),
                    source_type='conservative' if any(source in article.get('url', '') for source in ['foxnews', 'breitbart', 'dailywire', 'nypost', 'washingtontimes', 'theepochtimes']) else 'independent'
                )
                db.session.add(new_article)
                db.session.commit()
    except Exception as e:
        logger.error(f"Error retrieving article from database: {str(e)}")
        # Continue with in-memory search on error
        # Check trending articles
        for a in news_data["trending"]:
            if a.get('url') == article_url:
                article = a
                break
        
        # Check keyword search results if not found
        if article is None:
            for keyword, data in news_data["by_keyword"].items():
                for a in data["articles"]:
                    if a.get('url') == article_url:
                        article = a
                        break
                if article:
                    break
    
    if not article:
        flash("Article not found", "danger")
        return redirect(url_for('index'))
    
    ivm = article.get('ivm') if isinstance(article, dict) else None
    bias_score = article.get('bias_score') if isinstance(article, dict) else None
    omission_callouts = article.get('omission_callouts', []) if isinstance(article, dict) else []

    return render_template('article.html', article=article, ivm=ivm, bias_score=bias_score, omission_callouts=omission_callouts)

@app.route('/trump')
def trump_news():
    """Display positive Trump news from around the world"""
    try:
        # Get existing articles that mention Trump
        from models import Article
        
        articles = []
        trump_articles = Article.query.filter(
            Article.title.ilike('%trump%')
        ).order_by(Article.published_at.desc()).limit(20).all()
        
        # Format articles for the template
        for article in trump_articles:
            article_dict = {
                'title': article.title,
                'url': article.url,
                'source': {'name': article.source_name},
                'publishedAt': article.published_at.isoformat() if article.published_at else '',
                'author': article.author,
                'description': article.description,
                'content': article.content,
                'summary': article.summary,
                'urlToImage': article.url_to_image,
                'published_time': article.published_at.strftime('%B %d, %Y') if article.published_at else '',
                'source_type': article.source_type
            }
            articles.append(article_dict)
        
        # Return the template with the articles
        return render_template('trump.html', 
                              articles=articles, 
                              last_updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                              
    except Exception as e:
        logger.error(f"Error displaying Trump news: {str(e)}")
        flash(f"Error loading Trump news: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/refresh')
def refresh_trending():
    """Manually refresh trending news"""
    try:
        initialize_data()
        flash("News refreshed successfully", "success")
    except Exception as e:
        flash(f"Error refreshing news: {str(e)}", "danger")
    
    return redirect(url_for('index'))

@app.route('/refresh-executive-orders')
def refresh_executive_orders():
    """Manually refresh executive orders from Federal Register API"""
    try:
        # Import here to avoid circular imports
        from executive_orders import initialize_executive_orders
        
        # Force refresh of executive orders
        initialize_executive_orders(force_refresh=True)
        
        # Get the count of orders after refresh
        from models import ExecutiveOrder
        new_count = ExecutiveOrder.query.count()
        
        flash(f"Executive orders refreshed successfully! Retrieved {new_count} orders from Federal Register API.", "success")
    except Exception as e:
        logger.error(f"Error refreshing executive orders: {str(e)}")
        db.session.rollback()
        flash(f"Error refreshing executive orders: {str(e)}", "danger")
    
    return redirect(url_for('executive_orders'))

@app.route('/executive-orders')
def executive_orders():
    """Display Trump executive orders with AI summaries"""
    try:
        from models import ExecutiveOrder

        # Backwards-compat: ?order=<order_number> redirects to clean URL
        order_number_qs = request.args.get('order', '')
        if order_number_qs:
            return redirect(url_for('executive_order_detail', order_number=order_number_qs), 301)

        # Get filter parameters
        category = request.args.get('category', '')
        status = request.args.get('status', '')
        search = request.args.get('search', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')

        # Build base query
        query = ExecutiveOrder.query

        # Apply filters
        if category:
            query = query.filter(ExecutiveOrder.category.ilike(f'%{category}%'))

        if status:
            query = query.filter(ExecutiveOrder.status == status)

        if search:
            query = query.filter(
                db.or_(
                    ExecutiveOrder.title.ilike(f'%{search}%'),
                    ExecutiveOrder.full_text.ilike(f'%{search}%'),
                    ExecutiveOrder.summary.ilike(f'%{search}%')
                )
            )

        if date_from:
            try:
                dt_from = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(ExecutiveOrder.date_issued >= dt_from)
            except ValueError:
                pass

        if date_to:
            try:
                dt_to = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1) - timedelta(microseconds=1)
                query = query.filter(ExecutiveOrder.date_issued <= dt_to)
            except ValueError:
                pass

        # Get orders sorted by date (newest first)
        orders = query.order_by(ExecutiveOrder.date_issued.desc()).all()

        # Get unique categories and statuses for filters
        categories = db.session.query(ExecutiveOrder.category).distinct().all()
        categories = sorted([cat[0] for cat in categories if cat[0]])

        statuses = db.session.query(ExecutiveOrder.status).distinct().all()
        statuses = sorted([stat[0] for stat in statuses if stat[0]])

        # Quick stats
        from sqlalchemy import func
        total_orders = ExecutiveOrder.query.count()
        this_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        active_this_month = ExecutiveOrder.query.filter(
            ExecutiveOrder.date_issued >= this_month_start,
            ExecutiveOrder.status == 'Active'
        ).count()

        most_common_category_row = db.session.query(
            ExecutiveOrder.category, func.count(ExecutiveOrder.id).label('cnt')
        ).group_by(ExecutiveOrder.category).order_by(func.count(ExecutiveOrder.id).desc()).first()
        most_common_category = most_common_category_row[0] if most_common_category_row else 'N/A'

        # Compute poll sentiment: % "Helps" across all orders
        poll_totals = db.session.query(
            func.coalesce(func.sum(ExecutiveOrder.poll_yes), 0),
            func.coalesce(func.sum(ExecutiveOrder.poll_no), 0)
        ).first()
        total_yes = poll_totals[0] if poll_totals else 0
        total_no = poll_totals[1] if poll_totals else 0
        grand_total_votes = total_yes + total_no
        poll_sentiment_pct = int(round(total_yes / grand_total_votes * 100)) if grand_total_votes > 0 else 0

        # Missed angles blurbs: try to show indie_vs_mainstream from recent AI-analysed orders.
        # If fewer than 2 have AI analysis, trigger generation for the newest without it,
        # then fall back to the regular summary if AI generation fails or quota is exceeded.
        recent_with_ai = ExecutiveOrder.query.filter(
            ExecutiveOrder.indie_vs_mainstream.isnot(None)
        ).order_by(ExecutiveOrder.date_issued.desc()).limit(3).all()

        missed_angles = []
        for eo in recent_with_ai:
            try:
                data = json.loads(eo.indie_vs_mainstream)
                biz_text = data.get('wins', data.get('indie', ''))
                if biz_text:
                    missed_angles.append({'title': eo.title, 'order_number': eo.order_number, 'blurb': biz_text})
            except Exception:
                pass

        # Fallback: use regular summary for any remaining slots (up to 3 total)
        if len(missed_angles) < 3:
            recent_any = ExecutiveOrder.query.filter(
                ExecutiveOrder.summary.isnot(None)
            ).order_by(ExecutiveOrder.date_issued.desc()).limit(5).all()
            seen_ids = {a['order_number'] for a in missed_angles}
            for eo in recent_any:
                if len(missed_angles) >= 3:
                    break
                if eo.order_number not in seen_ids and eo.summary:
                    blurb = eo.summary[:250].rsplit(' ', 1)[0] + '…' if len(eo.summary) > 250 else eo.summary
                    missed_angles.append({'title': eo.title, 'order_number': eo.order_number, 'blurb': blurb, 'is_fallback': True})
                    seen_ids.add(eo.order_number)

        return render_template('executive_orders.html',
                               orders=orders,
                               categories=categories,
                               statuses=statuses,
                               category=category,
                               status=status,
                               search=search,
                               date_from=date_from,
                               date_to=date_to,
                               last_updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                               total_orders=total_orders,
                               active_this_month=active_this_month,
                               most_common_category=most_common_category,
                               poll_sentiment_pct=poll_sentiment_pct,
                               missed_angles=missed_angles)

    except Exception as e:
        logger.error(f"Error displaying executive orders: {str(e)}")
        flash(f"Error loading executive orders: {str(e)}", "danger")
        return redirect(url_for('index'))


@app.route('/executive-orders/<path:order_number>')
def executive_order_detail(order_number):
    """Display detailed view of a single executive order with AI analysis"""
    try:
        from models import ExecutiveOrder
        from executive_orders import generate_ai_analysis

        order = ExecutiveOrder.query.filter_by(order_number=order_number).first()
        if not order:
            flash(f"Executive Order '{order_number}' not found.", "danger")
            return redirect(url_for('executive_orders'))

        # Generate AI analysis lazily (only if not already cached)
        if not order.ai_summary:
            try:
                generate_ai_analysis(order)
            except Exception as e:
                logger.error(f"AI analysis failed for {order_number}: {e}")

        # Parse indie_vs_mainstream JSON (stores small_business_impact: wins + risks)
        indie_text = ''
        mainstream_text = ''
        if order.indie_vs_mainstream:
            try:
                ivm = json.loads(order.indie_vs_mainstream)
                indie_text = ivm.get('wins', ivm.get('indie', ''))
                mainstream_text = ivm.get('risks', ivm.get('mainstream', ''))
            except Exception:
                indie_text = order.indie_vs_mainstream

        # Parse historical context bullets
        historical_bullets = []
        if order.historical_context:
            for line in order.historical_context.split('\n'):
                line = line.strip().lstrip('•').strip()
                if line:
                    historical_bullets.append(line)

        # Poll tally
        poll_total = (order.poll_yes or 0) + (order.poll_no or 0)
        poll_yes_pct = round(((order.poll_yes or 0) / poll_total * 100)) if poll_total > 0 else 0
        poll_no_pct = 100 - poll_yes_pct if poll_total > 0 else 0
        voted = session.get(f'voted_eo_{order.order_number}', False)

        return render_template('executive_order_detail.html',
                               order=order,
                               indie_text=indie_text,
                               mainstream_text=mainstream_text,
                               historical_bullets=historical_bullets,
                               poll_yes_pct=poll_yes_pct,
                               poll_no_pct=poll_no_pct,
                               poll_total=poll_total,
                               voted=voted)

    except Exception as e:
        logger.error(f"Error displaying executive order detail: {str(e)}")
        flash(f"Error loading executive order: {str(e)}", "danger")
        return redirect(url_for('executive_orders'))


@app.route('/executive-orders/<path:order_number>/vote', methods=['POST'])
def executive_order_vote(order_number):
    """Handle Yes/No poll vote for an executive order"""
    try:
        from models import ExecutiveOrder

        session_key = f'voted_eo_{order_number}'
        if session.get(session_key):
            flash("You have already voted on this executive order.", "info")
            return redirect(url_for('executive_order_detail', order_number=order_number))

        order = ExecutiveOrder.query.filter_by(order_number=order_number).first()
        if not order:
            flash("Executive order not found.", "danger")
            return redirect(url_for('executive_orders'))

        vote = request.form.get('vote', '')
        if vote == 'yes':
            order.poll_yes = (order.poll_yes or 0) + 1
        elif vote == 'no':
            order.poll_no = (order.poll_no or 0) + 1
        else:
            flash("Invalid vote.", "danger")
            return redirect(url_for('executive_order_detail', order_number=order_number))

        db.session.commit()
        session[session_key] = True
        flash("Your vote has been recorded. Thank you!", "success")

    except Exception as e:
        logger.error(f"Error recording vote for {order_number}: {e}")
        db.session.rollback()
        flash("Error recording vote. Please try again.", "danger")

    return redirect(url_for('executive_order_detail', order_number=order_number))

@app.route('/api/generate-twitter-summary', methods=['POST'])
def generate_twitter_summary():
    """
    API endpoint to generate Twitter-friendly summaries for executive orders
    
    Accepts JSON object with 'text' parameter containing the full text
    Returns JSON object with 'summary' parameter containing the Twitter-friendly summary
    """
    try:
        # Get the text from the request
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Missing text parameter'}), 400
        
        # Generate a Twitter-friendly summary
        from executive_orders import generate_twitter_summary_for_order
        import html
        
        # Get the text from the request
        text = data['text']
        
        # Generate the Twitter summary
        twitter_summary = generate_twitter_summary_for_order(text)
        
        # Additional cleanup for JSON response
        # Double-check that HTML entities are decoded
        twitter_summary = html.unescape(twitter_summary)
        
        # Return the summary as JSON
        return jsonify({'summary': twitter_summary})
    
    except Exception as e:
        logger.error(f"Error generating Twitter summary: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/eo-evolution')
def eo_evolution():
    """EO Evolution: Policy Patterns Over Time"""
    try:
        from models import ExecutiveOrder
        from sqlalchemy import func
        from eo_history import HISTORICAL_EO_DATA, ANNOTATION_MILESTONES, TRUMP_II_INAUGURATION
        from home_ai import generate_eo_pattern_analysis

        inauguration_date = datetime.strptime(TRUMP_II_INAUGURATION, '%Y-%m-%d')

        trump2_orders = (
            ExecutiveOrder.query
            .filter(ExecutiveOrder.date_issued >= inauguration_date)
            .order_by(ExecutiveOrder.date_issued.asc())
            .all()
        )

        trump2_cumulative = {}
        running_count = 0
        for order in trump2_orders:
            if order.date_issued:
                day_n = (order.date_issued - inauguration_date).days + 1
                if day_n > 0:
                    running_count += 1
                    trump2_cumulative[day_n] = running_count

        max_day = max(trump2_cumulative.keys()) if trump2_cumulative else 365
        max_day = max(max_day, 90)

        chart_labels = list(range(1, max_day + 1))

        def build_cumulative_series(monthly_counts, max_day):
            daily = []
            for count in monthly_counts:
                per_day = count / 30.0
                daily.extend([per_day] * 30)
            running = 0.0
            series = []
            for day in range(1, max_day + 1):
                idx = day - 1
                if idx < len(daily):
                    running += daily[idx]
                series.append(round(running, 1))
            return series

        chart_datasets = []
        for admin_name, admin_data in HISTORICAL_EO_DATA.items():
            series = build_cumulative_series(admin_data['monthly_counts'], max_day)
            chart_datasets.append({
                "label": admin_name,
                "data": series,
                "borderColor": admin_data['border_color'],
                "backgroundColor": admin_data['color'],
                "tension": 0.3,
                "pointRadius": 0,
                "borderWidth": 2,
            })

        prev = None
        trump2_filled = []
        for d in range(1, max_day + 1):
            val = trump2_cumulative.get(d)
            if val is not None:
                prev = val
            trump2_filled.append(prev)

        chart_datasets.append({
            "label": "Trump II (2025)",
            "data": trump2_filled,
            "borderColor": "rgba(255, 193, 7, 1)",
            "backgroundColor": "rgba(255, 193, 7, 0.15)",
            "tension": 0.3,
            "pointRadius": 0,
            "borderWidth": 3,
        })

        monthly_rows = (
            db.session.query(
                func.to_char(ExecutiveOrder.date_issued, 'YYYY-MM').label('month'),
                func.count(ExecutiveOrder.id).label('cnt')
            )
            .filter(
                ExecutiveOrder.date_issued.isnot(None),
                ExecutiveOrder.date_issued >= inauguration_date
            )
            .group_by(func.to_char(ExecutiveOrder.date_issued, 'YYYY-MM'))
            .order_by(func.to_char(ExecutiveOrder.date_issued, 'YYYY-MM'))
            .all()
        )
        trump2_monthly = [{"month": row.month, "count": row.cnt} for row in monthly_rows]

        category_rows = (
            db.session.query(
                ExecutiveOrder.category,
                func.count(ExecutiveOrder.id).label('cnt')
            )
            .filter(
                ExecutiveOrder.category.isnot(None),
                ExecutiveOrder.date_issued >= inauguration_date
            )
            .group_by(ExecutiveOrder.category)
            .order_by(func.count(ExecutiveOrder.id).desc())
            .all()
        )

        def split_categories(cat_str):
            if not cat_str:
                return []
            return [c.strip() for c in cat_str.replace(';', ',').split(',') if c.strip()]

        category_breakdown = {}
        for row in category_rows:
            for cat in split_categories(row.category):
                category_breakdown[cat] = category_breakdown.get(cat, 0) + row.cnt

        stacked_months = [item['month'] for item in trump2_monthly]
        top_categories = sorted(category_breakdown.items(), key=lambda x: -x[1])[:6]
        top_cat_names = [c[0] for c in top_categories]

        cat_colors = [
            "rgba(255, 193, 7, 0.8)",
            "rgba(54, 162, 235, 0.8)",
            "rgba(255, 99, 132, 0.8)",
            "rgba(75, 192, 192, 0.8)",
            "rgba(153, 102, 255, 0.8)",
            "rgba(255, 159, 64, 0.8)",
        ]

        stacked_datasets = []
        for i, cat_name in enumerate(top_cat_names):
            monthly_cat_rows = (
                db.session.query(
                    func.to_char(ExecutiveOrder.date_issued, 'YYYY-MM').label('month'),
                    func.count(ExecutiveOrder.id).label('cnt')
                )
                .filter(
                    ExecutiveOrder.date_issued.isnot(None),
                    ExecutiveOrder.date_issued >= inauguration_date,
                    ExecutiveOrder.category.ilike(f'%{cat_name}%')
                )
                .group_by(func.to_char(ExecutiveOrder.date_issued, 'YYYY-MM'))
                .order_by(func.to_char(ExecutiveOrder.date_issued, 'YYYY-MM'))
                .all()
            )
            month_map = {row.month: row.cnt for row in monthly_cat_rows}
            data = [month_map.get(m, 0) for m in stacked_months]
            stacked_datasets.append({
                "label": cat_name,
                "data": data,
                "backgroundColor": cat_colors[i % len(cat_colors)],
                "borderColor": cat_colors[i % len(cat_colors)].replace('0.8', '1'),
                "borderWidth": 1,
            })

        pattern_cards = generate_eo_pattern_analysis(
            trump2_monthly,
            HISTORICAL_EO_DATA,
            category_breakdown
        )

        context = {
            "chart_labels": chart_labels,
            "chart_datasets": chart_datasets,
            "stacked_months": stacked_months,
            "stacked_datasets": stacked_datasets,
            "pattern_cards": pattern_cards,
            "annotation_milestones": ANNOTATION_MILESTONES,
            "total_orders": len(trump2_orders),
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        return render_template('eo_evolution.html', **context)

    except Exception as e:
        logger.error(f"Error loading EO Evolution page: {e}")
        flash(f"Error loading EO Evolution page: {str(e)}", "danger")
        return redirect(url_for('executive_orders'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error="Server error occurred"), 500

@app.route('/rfk-jr')
def rfk_jr_news():
    """Display news about RFK Jr. and health topics from trusted sources"""
    try:
        # Get existing articles related to RFK Jr.
        from models import Article
        
        # Query for RFK Jr. related articles
        rfk_articles = Article.query.filter(
            (Article.content.ilike('%RFK%')) | 
            (Article.content.ilike('%Robert Kennedy%')) |
            (Article.content.ilike('%Kennedy Jr%')) |
            (Article.source_name.ilike('%children%health%'))
        ).order_by(Article.published_at.desc()).limit(20).all()
        
        # If we don't have enough RFK Jr. articles in the database, fetch new ones
        if len(rfk_articles) < 5:
            # Import here to avoid circular import
            from news_scraper import fetch_rfk_jr_news
            
            # Fetch RFK Jr. news
            articles = fetch_rfk_jr_news()
            
            # Store in database for persistence
            for article_data in articles:
                # Check if article already exists
                existing = Article.query.filter_by(url=article_data.get('url', '')).first()
                if not existing:
                    # Create new article
                    new_article = Article(
                        title=article_data.get('title', 'No Title'),
                        url=article_data.get('url', ''),
                        source_name=article_data.get('source', {}).get('name', '') if article_data.get('source') else '',
                        source_url=article_data.get('source', {}).get('url', '') if article_data.get('source') else '',
                        published_at=datetime.fromisoformat(article_data.get('publishedAt', '').replace('Z', '+00:00')) if article_data.get('publishedAt') else None,
                        author=article_data.get('author', ''),
                        description=article_data.get('description', ''),
                        content=article_data.get('content', ''),
                        summary=generate_summary(article_data.get('content', '')),
                        url_to_image=article_data.get('urlToImage', ''),
                        category='health',
                        source_type='independent'
                    )
                    db.session.add(new_article)
            
            db.session.commit()
            
            # Get the articles we just added
            rfk_articles = Article.query.filter(
                (Article.content.ilike('%RFK%')) | 
                (Article.content.ilike('%Robert Kennedy%')) |
                (Article.content.ilike('%Kennedy Jr%')) |
                (Article.source_name.ilike('%children%health%'))
            ).order_by(Article.published_at.desc()).limit(20).all()
        
        # Render template with articles
        return render_template('rfk_jr.html', articles=rfk_articles)
    
    except Exception as e:
        logger.error(f"Error displaying RFK Jr. news: {str(e)}")
        flash("Error fetching RFK Jr. news. Please try again later.", "danger")
        return redirect(url_for('index'))

@app.route('/suggest-source', methods=['GET', 'POST'])
def suggest_source():
    """
    Allow users to suggest new independent news sources
    """
    from models import SuggestedNewsSource
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            url = request.form.get('url')
            description = request.form.get('description')
            source_type = request.form.get('source_type')
            submitter_name = request.form.get('submitter_name')
            submitter_email = request.form.get('submitter_email')
            reason = request.form.get('reason')
            
            # Validate required fields
            if not all([name, url, source_type, reason, submitter_email]):
                flash("Please fill in all required fields", "danger")
                return render_template('suggest_source.html', 
                                    form_data=request.form)
            
            # Create new suggestion
            suggestion = SuggestedNewsSource(
                name=name,
                url=url,
                description=description,
                source_type=source_type,
                submitter_name=submitter_name,
                submitter_email=submitter_email,
                reason=reason,
                status='pending'
            )
            
            # Save to database
            db.session.add(suggestion)
            db.session.commit()
            
            flash("Thank you! Your news source suggestion has been submitted for review.", "success")
            return redirect(url_for('index'))
            
        except Exception as e:
            logger.error(f"Error processing source suggestion: {str(e)}")
            db.session.rollback()
            flash("An error occurred. Please try again later.", "danger")
            return render_template('suggest_source.html', 
                                form_data=request.form)
    
    # GET request - show form
    return render_template('suggest_source.html')


