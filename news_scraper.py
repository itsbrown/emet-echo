import os
import requests
import logging
import trafilatura
from datetime import datetime

logger = logging.getLogger(__name__)

# Default API key (will be overridden by environment variable)
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "YOUR_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2"

# List of approved conservative and independent news sources
APPROVED_SOURCES = [
    # Conservative news sources
    "foxnews.com",
    "nypost.com",
    "washingtontimes.com",
    "theepochtimes.com",
    "breitbart.com",
    "dailywire.com",
    "oann.com",
    "newsmax.com",
    "theblaze.com",
    "westernjournal.com",
    "dailycaller.com",
    "washingtonexaminer.com",
    "spectator.org",
    
    # Independent news sources
    "zerohedge.com",
    "reason.com",
    "thehill.com",
    "realclearpolitics.com",
    "axios.com",
    "theintercept.com",
    "justthenews.com",
    "substack.com",
    "ground.news",
    "breakingpoints.com"
]

def is_approved_source(article):
    """
    Check if an article comes from an approved source
    
    Args:
        article: Article object from NewsAPI
        
    Returns:
        Boolean indicating if the source is approved
    """
    if not article or not article.get('url'):
        return False
        
    article_url = article.get('url', '').lower()
    
    # Check if the article URL contains any of the approved domains
    for source in APPROVED_SOURCES:
        if source.lower() in article_url:
            return True
            
    return False

def fetch_news(country="us", category="general", page_size=100):
    """
    Fetch trending news from NewsAPI
    
    Args:
        country: Country code (default: 'us')
        category: News category (default: 'general')
        page_size: Number of articles to fetch (default: 100)
        
    Returns:
        List of news articles from approved conservative sources
    """
    logger.info(f"Fetching conservative trending news for {country} in {category} category")
    
    try:
        # Use the "everything" endpoint instead of "top-headlines" to have more flexibility
        url = f"{NEWS_API_URL}/everything"
        
        # Create domain queries that NewsAPI can directly use
        domains = ','.join(APPROVED_SOURCES)
        
        # Create a query based on category
        query = category
        if category == "general":
            query = ""  # Empty query for general news to get more results
            
        params = {
            "domains": domains,
            "q": query,
            "language": "en",
            "pageSize": page_size,
            "sortBy": "publishedAt",
            "apiKey": NEWS_API_KEY
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        articles = data.get("articles", [])
        logger.info(f"Found {len(articles)} articles from approved conservative sources")
        
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

def search_news(query, language="en", page_size=100):
    """
    Search for news articles by keyword from approved conservative sources
    
    Args:
        query: Search term
        language: Language code (default: 'en')
        page_size: Number of articles to fetch (default: 100)
        
    Returns:
        List of news articles matching the query from approved sources
    """
    logger.info(f"Searching conservative news for query: {query}")
    
    try:
        # Check if query includes a site: prefix, which means user is searching for a specific site
        is_site_specific = query.startswith("site:")
        
        # Search for articles
        url = f"{NEWS_API_URL}/everything"
        
        # If there's a site: prefix, use that specific domain. Otherwise, use all approved domains.
        if is_site_specific:
            # Handle direct site queries (from the dropdown menu)
            domain = query.split("site:")[1].strip()
            search_query = ""  # Empty query to get all articles from this domain
            params = {
                "domains": domain,
                "language": language,
                "pageSize": page_size,
                "sortBy": "publishedAt",
                "apiKey": NEWS_API_KEY
            }
            logger.info(f"Searching for all articles from {domain}")
        else:
            # Create a domain query string for approved sources
            domains = ','.join([source for source in APPROVED_SOURCES])
            
            params = {
                "q": query,
                "language": language,
                "pageSize": page_size,
                "sortBy": "relevancy",
                "domains": domains,
                "apiKey": NEWS_API_KEY
            }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        articles = data.get("articles", [])
        logger.info(f"Found {len(articles)} articles from approved sources matching query '{query}'")
        
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
