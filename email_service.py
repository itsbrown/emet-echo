import os
import logging
import uuid
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, TemplateId, Personalization
from flask import url_for, render_template
from models import EmailSubscriber, Article, db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SendGrid API Key
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
DEFAULT_FROM_EMAIL = 'news@trustedconservative.news'  # Replace with your sending domain

def send_confirmation_email(subscriber):
    """
    Send confirmation email to new subscribers
    
    Args:
        subscriber: EmailSubscriber model instance
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not SENDGRID_API_KEY:
        logger.error("SendGrid API key not found. Cannot send confirmation email.")
        return False
    
    # Generate confirmation token if needed
    if not subscriber.confirmation_token:
        subscriber.confirmation_token = str(uuid.uuid4())
        db.session.commit()
    
    # TODO: Create a template in SendGrid and use the template ID
    # For now, let's create a simple email
    subject = "Confirm Your Conservative News Digest Subscription"
    
    # Create confirmation URL
    confirmation_url = url_for(
        'confirm_subscription', 
        token=subscriber.confirmation_token, 
        _external=True
    )
    
    # HTML content with confirmation link
    html_content = render_template(
        'emails/confirmation_email.html',
        first_name=subscriber.first_name,
        confirmation_url=confirmation_url
    )
    
    # Plain text content
    text_content = f"""
    Hello {subscriber.first_name or 'there'},
    
    Thank you for subscribing to the Conservative News Digest!
    
    Please confirm your subscription by clicking this link:
    {confirmation_url}
    
    If you did not sign up for this service, please ignore this email.
    """
    
    try:
        message = Mail(
            from_email=Email(DEFAULT_FROM_EMAIL),
            to_emails=To(subscriber.email),
            subject=subject
        )
        
        # Add plain text content
        message.content = Content("text/plain", text_content)
        
        # Add HTML content
        message.add_content(Content("text/html", html_content))
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        # Check status code
        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"Confirmation email sent to {subscriber.email}")
            return True
        else:
            logger.error(f"Failed to send confirmation email. Status code: {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"Error sending confirmation email: {str(e)}")
        return False

def send_daily_digest(subscriber):
    """
    Send daily news digest email to a subscriber
    
    Args:
        subscriber: EmailSubscriber model instance
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not SENDGRID_API_KEY:
        logger.error("SendGrid API key not found. Cannot send daily digest email.")
        return False
    
    # Only send to confirmed subscribers
    if not subscriber.confirmed_at or not subscriber.is_active:
        logger.warning(f"Skipping unconfirmed or inactive subscriber: {subscriber.email}")
        return False
    
    # Get personalized news for this subscriber
    articles = get_personalized_articles(subscriber)
    
    if not articles:
        logger.warning(f"No articles found for subscriber: {subscriber.email}")
        return False
    
    # Send email with articles
    subject = f"Your Conservative News Digest for {datetime.now().strftime('%B %d, %Y')}"
    
    html_content = render_template(
        'emails/daily_digest.html',
        first_name=subscriber.first_name,
        articles=articles,
        date=datetime.now().strftime('%B %d, %Y')
    )
    
    text_content = f"""
    Hello {subscriber.first_name or 'there'},
    
    Here is your Conservative News Digest for {datetime.now().strftime('%B %d, %Y')}:
    
    """
    
    # Add articles to text content
    for idx, article in enumerate(articles[:5], 1):
        text_content += f"\n{idx}. {article.title}\n   {article.url}\n"
    
    text_content += "\n\nTo unsubscribe, click here: {unsubscribe_url}"
    
    try:
        message = Mail(
            from_email=Email(DEFAULT_FROM_EMAIL),
            to_emails=To(subscriber.email),
            subject=subject
        )
        
        # Add plain text content
        message.content = Content("text/plain", text_content)
        
        # Add HTML content
        message.add_content(Content("text/html", html_content))
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        # Check status code
        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"Daily digest email sent to {subscriber.email}")
            
            # Update last_email_sent
            subscriber.last_email_sent = datetime.utcnow()
            db.session.commit()
            
            return True
        else:
            logger.error(f"Failed to send daily digest email. Status code: {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"Error sending daily digest email: {str(e)}")
        return False

def get_personalized_articles(subscriber, limit=10):
    """
    Get personalized articles for a subscriber based on their preferences
    
    Args:
        subscriber: EmailSubscriber model instance
        limit: Maximum number of articles to return
    
    Returns:
        list: List of Article objects
    """
    # Get subscriber preferences
    preferred_categories = subscriber.get_preferred_categories()
    preferred_sources = subscriber.get_preferred_sources()
    excluded_sources = subscriber.get_excluded_sources()
    
    # Base query
    query = Article.query
    
    # Filter by date (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)
    query = query.filter(Article.published_at >= yesterday)
    
    # Apply category preferences if specified
    if preferred_categories:
        query = query.filter(Article.category.in_(preferred_categories))
    
    # Apply source preferences if specified
    if preferred_sources:
        query = query.filter(Article.source_name.in_(preferred_sources))
    
    # Apply source exclusions if specified
    if excluded_sources:
        query = query.filter(~Article.source_name.in_(excluded_sources))
    
    # Order by publish date (newest first)
    query = query.order_by(Article.published_at.desc())
    
    # Limit results
    articles = query.limit(limit).all()
    
    return articles

def send_all_daily_digests():
    """
    Send daily digest emails to all confirmed and active subscribers
    
    Returns:
        tuple: (successful_count, failed_count)
    """
    # Get all confirmed and active subscribers
    subscribers = EmailSubscriber.query.filter(
        EmailSubscriber.confirmed_at.isnot(None),
        EmailSubscriber.is_active == True
    ).all()
    
    successful_count = 0
    failed_count = 0
    
    logger.info(f"Sending daily digests to {len(subscribers)} subscribers")
    
    for subscriber in subscribers:
        # Skip if already sent today
        if (subscriber.last_email_sent and 
            subscriber.last_email_sent.date() == datetime.utcnow().date()):
            logger.info(f"Skipping subscriber {subscriber.email}, already sent today")
            continue
            
        # Send digest
        if send_daily_digest(subscriber):
            successful_count += 1
        else:
            failed_count += 1
    
    logger.info(f"Sent {successful_count} digests successfully, {failed_count} failed")
    
    return successful_count, failed_count