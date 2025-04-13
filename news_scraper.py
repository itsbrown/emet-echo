import os
import requests
import logging
import trafilatura
from datetime import datetime

logger = logging.getLogger(__name__)

# Default API key (will be overridden by environment variable)
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "YOUR_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2"

def fetch_news(country="us", category="technology", page_size=24):
    """
    Fetch trending news from NewsAPI
    
    Args:
        country: Country code (default: 'us')
        category: News category (default: 'technology')
        page_size: Number of articles to fetch (default: 24)
        
    Returns:
        List of news articles
    """
    logger.info(f"Fetching trending news for {country} in {category} category")
    
    try:
        # Fetch trending headlines
        url = f"{NEWS_API_URL}/top-headlines"
        params = {
            "country": country,
            "category": category,
            "pageSize": page_size,
            "apiKey": NEWS_API_KEY
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        articles = data.get("articles", [])
        
        # Enhance articles with additional content from original source
        enhanced_articles = []
        for article in articles:
            try:
                # Add article source URL for scraping
                if article.get('url'):
                    article['content'] = fetch_article_content(article['url'])
                
                # Add timestamp for display
                if article.get('publishedAt'):
                    article['published_time'] = format_timestamp(article['publishedAt'])
                
                enhanced_articles.append(article)
            except Exception as e:
                logger.error(f"Error enhancing article {article.get('title')}: {str(e)}")
                # Still keep the article even if enhancement fails
                enhanced_articles.append(article)
        
        return enhanced_articles
    
    except requests.RequestException as e:
        logger.error(f"Error fetching news: {str(e)}")
        raise Exception(f"Error fetching news: {str(e)}")

def search_news(query, language="en", page_size=24):
    """
    Search for news articles by keyword
    
    Args:
        query: Search term
        language: Language code (default: 'en')
        page_size: Number of articles to fetch (default: 24)
        
    Returns:
        List of news articles matching the query
    """
    logger.info(f"Searching news for query: {query}")
    
    try:
        # Search for articles
        url = f"{NEWS_API_URL}/everything"
        params = {
            "q": query,
            "language": language,
            "pageSize": page_size,
            "sortBy": "relevancy",
            "apiKey": NEWS_API_KEY
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        articles = data.get("articles", [])
        
        # Enhance articles with additional content
        enhanced_articles = []
        for article in articles:
            try:
                # Add article source URL for scraping
                if article.get('url'):
                    article['content'] = fetch_article_content(article['url'])
                
                # Add timestamp for display
                if article.get('publishedAt'):
                    article['published_time'] = format_timestamp(article['publishedAt'])
                
                enhanced_articles.append(article)
            except Exception as e:
                logger.error(f"Error enhancing article {article.get('title')}: {str(e)}")
                # Still keep the article even if enhancement fails
                enhanced_articles.append(article)
        
        return enhanced_articles
    
    except requests.RequestException as e:
        logger.error(f"Error searching news: {str(e)}")
        raise Exception(f"Error searching news: {str(e)}")

def fetch_article_content(url):
    """
    Fetch full content of an article using trafilatura
    
    Args:
        url: Article URL
        
    Returns:
        Article content as plain text
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        text = trafilatura.extract(downloaded)
        return text if text else "Content not available"
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {str(e)}")
        return "Content not available"

def format_timestamp(timestamp_str):
    """
    Format timestamp for display
    
    Args:
        timestamp_str: ISO format timestamp string
        
    Returns:
        Formatted timestamp string
    """
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%B %d, %Y")
    except:
        return timestamp_str
