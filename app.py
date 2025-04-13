import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from datetime import datetime, timedelta
import json
import requests
import threading
from summarizer import generate_summary
from news_scraper import fetch_news, search_news
from scheduler import start_scheduler

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# In-memory storage for news articles
news_data = {
    "trending": [],
    "last_updated": None,
    "by_keyword": {}
}

def initialize_data():
    """Initialize data with trending news"""
    global news_data
    try:
        articles = fetch_news()
        
        # Generate AI summaries for each article
        for article in articles:
            if 'content' in article and article['content']:
                article['summary'] = generate_summary(article['content'])
            else:
                article['summary'] = "Summary not available."
        
        news_data["trending"] = articles
        news_data["last_updated"] = datetime.now()
        
        logger.info(f"Initialized with {len(articles)} trending articles")
    except Exception as e:
        logger.error(f"Error initializing data: {str(e)}")
        news_data["trending"] = []
        news_data["last_updated"] = datetime.now()

# Background initialization to avoid blocking app startup
threading.Thread(target=initialize_data).start()

# Start the scheduler for periodic updates
start_scheduler(news_data)

@app.route('/')
def index():
    """Display trending news on the homepage"""
    last_updated = news_data["last_updated"]
    formatted_time = last_updated.strftime("%Y-%m-%d %H:%M:%S") if last_updated else "Never"
    
    return render_template('index.html', 
                          articles=news_data["trending"], 
                          last_updated=formatted_time,
                          search_query=None)

@app.route('/search')
def search():
    """Search news by keyword"""
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('index'))
    
    # Check if we already have results for this keyword
    if query in news_data["by_keyword"] and news_data["by_keyword"][query]["timestamp"] > datetime.now() - timedelta(hours=1):
        articles = news_data["by_keyword"][query]["articles"]
        logger.info(f"Using cached results for '{query}' with {len(articles)} articles")
    else:
        try:
            articles = search_news(query)
            
            # Generate AI summaries for each article
            for article in articles:
                if 'content' in article and article['content']:
                    article['summary'] = generate_summary(article['content'])
                else:
                    article['summary'] = "Summary not available."
            
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

@app.route('/refresh')
def refresh_trending():
    """Manually refresh trending news"""
    try:
        initialize_data()
        flash("News refreshed successfully", "success")
    except Exception as e:
        flash(f"Error refreshing news: {str(e)}", "danger")
    
    return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error="Server error occurred"), 500
