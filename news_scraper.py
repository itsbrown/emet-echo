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
    "breakingpoints.com",
    
    # Additional Independent Sources
    "rumble.com",                 # Rumble platform
    "rumble.com/JovanHPulitzer",  # Jovan Hutton Pulitzer Rumble channel
    "rumble.com/c/DonaldJTrumpJr", # Don Jr.'s "Triggered" show
    "rumble.com/c/AndWeKnow",     # And We Know channel
    "tuckercarlson.com",          # Tucker Carlson Network
    "dailywire.com",              # Daily Wire
    "x.com/TuckerCarlson",        # Tucker Carlson X account
    "x.com/JovanHPulitzer",       # Jovan Hutton Pulitzer X account
    "x.com/laralogan",            # Lara Logan X account
    "laralogan.substack.com",     # Lara Logan's Substack
    "rwmalonemd.substack.com",    # Dr. Robert Malone Substack
    "x.com/RWMaloneMD",           # Dr. Robert Malone X account
    "x.com/ScottWAtlas",          # Dr. Scott Atlas X account
    "scottwalteratlas.substack.com", # Dr. Scott Atlas Substack
    "twc.health",                 # The Wellness Company
    "x.com/RobertKennedyJr",      # RFK Jr. X account
    "childrenshealthdefense.org", # Children's Health Defense (RFK Jr.'s organization)
    "bitchute.com",               # BitChute platform
    "gab.com",                    # Gab platform
    "banned.video",               # Banned.video platform
    "frankspeech.com",            # FrankSpeech platform
    "redvoicemedia.com",          # Red Voice Media
    "thegatewaypundit.com",       # The Gateway Pundit
    "redstate.com",               # Red State
    "citizenfreepress.com",       # Citizen Free Press
    "100percentfedup.com",        # 100% Fed Up
    "emeralddb3.substack.com",    # Emerald Robinson's Substack
    "warroom.org",                # War Room
    "1a3t.short.gy"               # 107 Daily
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

def is_sports_content(article):
    """
    Check if an article is sports-related content
    
    Args:
        article: Article object from NewsAPI
        
    Returns:
        Boolean indicating if the article is about sports
    """
    if not article:
        return False
        
    # Get title and description (lowercase for case-insensitive matching)
    title = article.get('title', '').lower()
    description = article.get('description', '').lower()
    
    # List of sports-related keywords to filter out
    sports_keywords = [
        'sports', 'sport', 'nfl', 'mlb', 'nba', 'nhl', 'football', 'baseball', 
        'basketball', 'hockey', 'soccer', 'tennis', 'golf', 'racing', 'olympic',
        'olympics', 'athlete', 'tournament', 'championship', 'playoffs', 'game',
        'match', 'stadium', 'coach', 'player', 'team', 'boxing', 'ufc', 'nascar',
        'wrestl', 'scoring', 'score', 'scored', 'draft', 'league', 'fantasy',
        'scores', 'betting', 'bet', 'odds', 'sports betting'
    ]
    
    # Check if any sports keyword is in the title or description
    for keyword in sports_keywords:
        if keyword in title or keyword in description:
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
            # Skip sports-related content
            if is_sports_content(article):
                logger.debug(f"Skipping sports content: {article.get('title')}")
                continue
                
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
        
        logger.info(f"Returning {len(enhanced_articles)} articles after filtering out sports content")
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
        articles_count = len(articles)
        filtered_count = 0
        
        for article in articles:
            # Skip sports-related content
            if is_sports_content(article):
                logger.debug(f"Skipping sports content from search: {article.get('title')}")
                filtered_count += 1
                continue
                
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
        
        logger.info(f"Returning {len(enhanced_articles)} search results after filtering out {filtered_count} sports articles")
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

def fetch_rfk_jr_news(page_size=30):
    """
    Fetch news about RFK Jr. from approved sources
    
    Args:
        page_size: Number of articles to fetch (default: 30)
        
    Returns:
        List of news articles about RFK Jr.
    """
    logger.info("Fetching RFK Jr. news")
    
    try:
        # Use the "everything" endpoint with RFK Jr. specific query
        url = f"{NEWS_API_URL}/everything"
        
        # Build query for RFK Jr. - include common ways his name appears in articles
        query = "\"Robert Kennedy Jr\" OR \"RFK Jr\" OR \"Robert F. Kennedy Jr\""
        
        # Create a list of health-focused domains for better relevance
        health_domains = [
            "childrenshealthdefense.org",
            "rwmalonemd.substack.com",
            "twc.health",
            "x.com/RobertKennedyJr"
        ]
        
        # Join domains for API query
        domains = ','.join(health_domains)
        
        params = {
            "q": query,
            "domains": domains,
            "language": "en",
            "pageSize": page_size,
            "sortBy": "publishedAt",
            "apiKey": NEWS_API_KEY
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        articles = data.get("articles", [])
        logger.info(f"Found {len(articles)} RFK Jr. articles")
        
        # Enhance articles with additional content
        enhanced_articles = []
        filtered_count = 0
        
        for article in articles:
            # Skip sports-related content
            if is_sports_content(article):
                logger.debug(f"Skipping sports content from RFK Jr. news: {article.get('title')}")
                filtered_count += 1
                continue
                
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
                
        logger.info(f"Returning {len(enhanced_articles)} RFK Jr. articles after filtering out {filtered_count} sports articles")
        
        return enhanced_articles
    
    except requests.RequestException as e:
        logger.error(f"Error fetching RFK Jr. news: {str(e)}")
        raise Exception(f"Error fetching RFK Jr. news: {str(e)}")

def fetch_trump_positive_news(page_size=50):
    """
    Fetch positive news about Trump from around the world
    
    Args:
        page_size: Number of articles to fetch (default: 50)
        
    Returns:
        List of positive Trump news articles
    """
    logger.info("Fetching positive Trump news from around the world")
    
    try:
        # Use the "everything" endpoint with carefully crafted query
        url = f"{NEWS_API_URL}/everything"
        
        # Positive sentiment keywords combined with Trump
        positive_keywords = ["success", "victory", "winning", "achievement", "praised", 
                            "support", "approval", "popular", "gain", "rise", "momentum",
                            "leadership", "breakthrough", "accomplishment", "strength", 
                            "resilience", "comeback", "triumph", "champion", "excellence"]
        
        # Combine positive keywords with Trump in the query
        query_parts = [f"Trump AND {keyword}" for keyword in positive_keywords]
        query = " OR ".join(query_parts)
        
        # We want worldwide news, so we don't restrict by domains
        params = {
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
        logger.info(f"Found {len(articles)} positive Trump articles from around the world")
        
        # Enhance articles with additional content
        enhanced_articles = []
        filtered_count = 0
        
        for article in articles:
            # Skip sports-related content
            if is_sports_content(article):
                logger.debug(f"Skipping sports content from Trump news: {article.get('title')}")
                filtered_count += 1
                continue
                
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
                
        logger.info(f"Returning {len(enhanced_articles)} Trump articles after filtering out {filtered_count} sports articles")
        
        return enhanced_articles
    
    except requests.RequestException as e:
        logger.error(f"Error fetching Trump positive news: {str(e)}")
        raise Exception(f"Error fetching Trump positive news: {str(e)}")
