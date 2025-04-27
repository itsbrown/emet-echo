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

# Register blueprints
from blueprints.email import email_bp, init_app as init_email_blueprint

# Register the email blueprint
app.register_blueprint(email_bp)

# Initialize the email blueprint with app context
with app.app_context():
    init_email_blueprint(app, db)

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
                    'source_type': article.source_type
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
    
    return render_template('index.html', 
                          articles=articles, 
                          last_updated=formatted_time,
                          search_query=None)

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
    
    return render_template('index.html', 
                          articles=articles, 
                          last_updated=last_updated,
                          search_query=query)

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
                'published_time': db_article.published_at.strftime("%B %d, %Y") if db_article.published_at else ''
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
    
    return render_template('article.html', article=article)

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
        
        # Get filter parameters
        category = request.args.get('category', '')
        status = request.args.get('status', '')
        search = request.args.get('search', '')
        order_number = request.args.get('order', '')
        
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
            
        if order_number:
            query = query.filter(ExecutiveOrder.order_number == order_number)
        
        # Get orders sorted by date (newest first)
        orders = query.order_by(ExecutiveOrder.date_issued.desc()).all()
        
        # Get unique categories and statuses for filters
        categories = db.session.query(ExecutiveOrder.category).distinct().all()
        categories = sorted([cat[0] for cat in categories if cat[0]])
        
        statuses = db.session.query(ExecutiveOrder.status).distinct().all()
        statuses = sorted([stat[0] for stat in statuses if stat[0]])
        
        # If a specific order is requested but multiple filters were applied,
        # redirect to just show that specific order
        if order_number and len(orders) > 1:
            return redirect(url_for('executive_orders', order=order_number))
        
        # If only one order is found and it's a specific request, show the detailed view
        if len(orders) == 1 and order_number:
            return render_template('executive_order_detail.html',
                                order=orders[0])
        
        return render_template('executive_orders.html',
                             orders=orders,
                             categories=categories,
                             statuses=statuses,
                             category=category,
                             status=status,
                             search=search,
                             last_updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    except Exception as e:
        logger.error(f"Error displaying executive orders: {str(e)}")
        flash(f"Error loading executive orders: {str(e)}", "danger")
        return redirect(url_for('index'))

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


