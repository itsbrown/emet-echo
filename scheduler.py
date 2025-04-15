import threading
import logging
import time
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

# Email digest settings
DIGEST_HOUR = 8  # Send at 8 AM local server time

def start_scheduler(news_data, interval=900):  # Default 15 minutes (900 seconds)
    """
    Start a background scheduler to refresh news data and send daily digests
    
    Args:
        news_data: Reference to the global news data dictionary
        interval: Refresh interval in seconds (default: 900)
    """
    def refresh_task():
        from news_scraper import fetch_news
        from summarizer import generate_summary
        # Get Flask app to use app_context
        from app import app, db
        from models import Article, EmailSubscriber
        # Import email service
        from email_service import send_all_daily_digests
        
        while True:
            try:
                logger.info("Scheduled refresh: Fetching new trending articles")
                
                # Make sure all database operations use an app context
                with app.app_context():
                    # Check if it's time to send daily digest emails (at DIGEST_HOUR o'clock)
                    current_time = datetime.now()
                    if current_time.hour == DIGEST_HOUR and current_time.minute < 15:
                        logger.info("Sending daily digest emails to subscribers")
                        try:
                            successful, failed = send_all_daily_digests()
                            logger.info(f"Daily digest emails sent: {successful} successful, {failed} failed")
                        except Exception as email_err:
                            logger.error(f"Error sending daily digest emails: {str(email_err)}")
                    
                    # Fetch new trending articles
                    articles = fetch_news()
                    stored_articles = []
                    
                    # Process each article and store in database
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
                                    article_data['summary'] = new_article.summary
                                except Exception as sum_err:
                                    logger.error(f"Error generating summary: {str(sum_err)}")
                                    new_article.summary = "Summary not available."
                                    article_data['summary'] = "Summary not available."
                            
                            # Add to database
                            db.session.add(new_article)
                            
                            # Add to cache list
                            stored_articles.append(article_data)
                        else:
                            # Use the existing article from database
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
                                'published_time': existing_article.published_at.strftime("%B %d, %Y") if existing_article.published_at else '',
                                'source_type': existing_article.source_type
                            }
                            stored_articles.append(article_dict)
                    
                    # Commit all database changes
                    db.session.commit()
                    
                    # Update global data
                    news_data["trending"] = stored_articles
                    news_data["last_updated"] = datetime.now()
                    
                    logger.info(f"Scheduled refresh complete: {len(stored_articles)} articles")
                
            except Exception as e:
                logger.error(f"Error in scheduled refresh: {str(e)}")
            
            # Sleep for the specified interval
            time.sleep(interval)
    
    # Start the refresh task in a background thread
    refresh_thread = threading.Thread(target=refresh_task, daemon=True)
    refresh_thread.start()
    
    logger.info(f"Scheduler started with {interval} second interval")
    
    return refresh_thread
