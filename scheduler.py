import threading
import logging
import time
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

def start_scheduler(news_data, interval=900):  # Default 15 minutes (900 seconds)
    """
    Start a background scheduler to refresh news data
    
    Args:
        news_data: Reference to the global news data dictionary
        interval: Refresh interval in seconds (default: 900)
    """
    def refresh_task():
        from news_scraper import fetch_news
        from summarizer import generate_summary
        
        while True:
            try:
                logger.info("Scheduled refresh: Fetching new trending articles")
                
                # Fetch new trending articles
                articles = fetch_news()
                
                # Generate AI summaries
                for article in articles:
                    if 'content' in article and article['content']:
                        article['summary'] = generate_summary(article['content'])
                    else:
                        article['summary'] = "Summary not available."
                
                # Update global data
                news_data["trending"] = articles
                news_data["last_updated"] = datetime.now()
                
                logger.info(f"Scheduled refresh complete: {len(articles)} articles")
                
            except Exception as e:
                logger.error(f"Error in scheduled refresh: {str(e)}")
            
            # Sleep for the specified interval
            time.sleep(interval)
    
    # Start the refresh task in a background thread
    refresh_thread = threading.Thread(target=refresh_task, daemon=True)
    refresh_thread.start()
    
    logger.info(f"Scheduler started with {interval} second interval")
    
    return refresh_thread
