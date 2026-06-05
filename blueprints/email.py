import os
import logging
import uuid
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, TemplateId, Personalization
from flask import Blueprint, request, redirect, url_for, flash, render_template, current_app, session
# We'll get db in the routes to avoid circular imports

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint
email_bp = Blueprint('email', __name__, url_prefix='/email')

def init_app(app, db):
    """Initialize email blueprint with app and database"""
    # Add link to subscription page in navbar
    @app.context_processor
    def inject_email_routes():
        return {
            'email_routes': {
                'subscribe': url_for('email.subscribe')
            }
        }

# SendGrid API Key
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
DEFAULT_FROM_EMAIL = 'info@emetecho.com'  # Updated sender email

@email_bp.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    """Subscription form and processing"""
    from models import EmailSubscriber
    from app import db
    
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        
        if not email:
            flash('Email is required', 'danger')
            return redirect(url_for('email.subscribe'))
            
        # Check if already subscribed
        existing = EmailSubscriber.query.filter_by(email=email).first()
        if existing:
            if existing.confirmed_at:
                flash('You are already subscribed to our newsletter', 'info')
            else:
                # Resend confirmation email
                send_confirmation_email(existing, db)
                flash('Confirmation email resent. Please check your inbox', 'info')
            return redirect(url_for('index'))
        
        # Get content types
        content_types = request.form.getlist('content_types')
        if not content_types:
            content_types = ['general']  # Default to general news if nothing selected
        
        # Create new subscriber
        new_subscriber = EmailSubscriber(
            email=email,
            first_name=first_name,
            last_name=last_name,
            confirmation_token=str(uuid.uuid4())
        )
        
        # Set content types
        new_subscriber.set_content_types(content_types)
        
        # Save to database
        db.session.add(new_subscriber)
        db.session.commit()
        
        # Send confirmation email
        if send_confirmation_email(new_subscriber, db):
            flash('Please check your email to confirm your subscription', 'success')
            return redirect(url_for('index'))
        else:
            flash('There was an error sending the confirmation email. Please try again later.', 'danger')
            return redirect(url_for('index'))
        
    # GET request - show form
    return render_template('subscribe.html')

@email_bp.route('/confirm/<token>')
def confirm_subscription(token):
    """Confirm email subscription with token"""
    from models import EmailSubscriber
    from app import db
    
    subscriber = EmailSubscriber.query.filter_by(confirmation_token=token).first()
    
    if not subscriber:
        flash('Invalid confirmation link', 'danger')
        return redirect(url_for('index'))
        
    subscriber.confirmed_at = datetime.utcnow()
    db.session.commit()
    
    flash('Your subscription has been confirmed. Thank you!', 'success')
    return redirect(url_for('index'))

@email_bp.route('/unsubscribe/<token>')
def unsubscribe(token):
    """Unsubscribe from newsletter"""
    from models import EmailSubscriber
    from app import db
    
    subscriber = EmailSubscriber.query.filter_by(confirmation_token=token).first()
    
    if not subscriber:
        flash('Invalid unsubscribe link', 'danger')
        return redirect(url_for('index'))
        
    subscriber.is_active = False
    db.session.commit()
    
    flash('You have been unsubscribed from our newsletter', 'success')
    return redirect(url_for('index'))

@email_bp.route('/manage-preferences/<token>', methods=['GET', 'POST'])
def manage_preferences(token):
    """Manage email preferences"""
    from models import EmailSubscriber, Article
    from app import db
    
    subscriber = EmailSubscriber.query.filter_by(confirmation_token=token).first()
    
    if not subscriber:
        flash('Invalid link', 'danger')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        # Update preferences
        categories = request.form.getlist('categories')
        sources = request.form.getlist('sources')
        excluded = request.form.getlist('excluded_sources')
        frequency = request.form.get('frequency', 'daily')
        content_types = request.form.getlist('content_types')
        
        # Ensure at least one content type is selected
        if not content_types:
            content_types = ['general']
            
        subscriber.set_preferred_categories(categories)
        subscriber.set_preferred_sources(sources)
        subscriber.set_excluded_sources(excluded)
        subscriber.set_content_types(content_types)
        subscriber.frequency = frequency
        
        db.session.commit()
        
        flash('Your preferences have been updated', 'success')
        return redirect(url_for('email.manage_preferences', token=token))
    
    # For GET request - gather data for the form
    # Get all available categories
    categories = db.session.query(Article.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    
    # Get all available sources
    sources = db.session.query(Article.source_name).distinct().all()
    sources = [s[0] for s in sources if s[0]]
    
    return render_template('preferences.html', 
                          subscriber=subscriber,
                          available_categories=categories,
                          available_sources=sources)

def send_confirmation_email(subscriber, db):
    """
    Send confirmation email to new subscribers
    
    Args:
        subscriber: EmailSubscriber model instance
        db: SQLAlchemy database instance
    
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
    
    # Create confirmation URL
    confirmation_url = url_for(
        'email.confirm_subscription', 
        token=subscriber.confirmation_token, 
        _external=True
    )
    
    # Create unsubscribe URL
    unsubscribe_url = url_for(
        'email.unsubscribe', 
        token=subscriber.confirmation_token, 
        _external=True
    )
    
    # Create preferences URL
    preferences_url = url_for(
        'email.manage_preferences', 
        token=subscriber.confirmation_token, 
        _external=True
    )
    
    # HTML content with confirmation link
    html_content = render_template(
        'emails/confirmation_email.html',
        first_name=subscriber.first_name,
        confirmation_url=confirmation_url,
        unsubscribe_url=unsubscribe_url,
        preferences_url=preferences_url
    )
    
    # Plain text content
    text_content = f"""
    Hello {subscriber.first_name or 'there'},
    
    Thank you for subscribing to the Conservative News Digest!
    
    Please confirm your subscription by clicking this link:
    {confirmation_url}
    
    If you did not sign up for this service, please ignore this email or unsubscribe:
    {unsubscribe_url}
    """
    
    # Email subject
    subject = "Confirm Your Conservative News Digest Subscription"
    
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

def send_daily_digest(subscriber, db):
    """
    Send daily news digest email to a subscriber
    
    Args:
        subscriber: EmailSubscriber model instance
        db: SQLAlchemy database instance
    
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
    
    # Create unsubscribe URL
    unsubscribe_url = url_for(
        'email.unsubscribe', 
        token=subscriber.confirmation_token, 
        _external=True
    )
    
    # Create preferences URL
    preferences_url = url_for(
        'email.manage_preferences', 
        token=subscriber.confirmation_token, 
        _external=True
    )
    
    # Get content types
    content_types = subscriber.get_content_types()
    
    # Create content type descriptions for email
    content_descriptions = []
    if "general" in content_types:
        content_descriptions.append("conservative news")
    if "trump_news" in content_types:
        content_descriptions.append("positive Trump news")
    if "executive_orders" in content_types:
        content_descriptions.append("executive order updates")
        
    content_type_text = " and ".join(content_descriptions)
    
    # Send email with articles
    subject = f"Your Personalized Emet Echo Digest for {datetime.now().strftime('%B %d, %Y')}"
    
    html_content = render_template(
        'emails/daily_digest.html',
        first_name=subscriber.first_name,
        articles=articles,
        date=datetime.now().strftime('%B %d, %Y'),
        unsubscribe_url=unsubscribe_url,
        preferences_url=preferences_url,
        content_type_text=content_type_text
    )
    
    text_content = f"""
    Hello {subscriber.first_name or 'there'},
    
    Here is your personalized Emet Echo digest with {content_type_text} for {datetime.now().strftime('%B %d, %Y')}:
    
    """
    
    # Add articles to text content
    for idx, article in enumerate(articles[:5], 1):
        # Handle both Article objects and dictionary items (executive orders)
        title = article['title'] if isinstance(article, dict) else article.title
        url = article['url'] if isinstance(article, dict) else article.url
        
        # Add indicator for executive orders
        prefix = "[EXECUTIVE ORDER] " if isinstance(article, dict) and article.get('is_executive_order') else ""
        
        text_content += f"\n{idx}. {prefix}{title}\n   {url}\n"
    
    text_content += f"\n\nTo unsubscribe, visit: {unsubscribe_url}"
    text_content += f"\nTo manage your preferences, visit: {preferences_url}"
    
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
    from models import Article, ExecutiveOrder
    from app import db
    
    # Get subscriber preferences
    preferred_categories = subscriber.get_preferred_categories()
    preferred_sources = subscriber.get_preferred_sources()
    excluded_sources = subscriber.get_excluded_sources()
    content_types = subscriber.get_content_types()
    
    # Initialize empty list for all content
    all_content = []
    
    # Get articles based on content type preferences
    if "general" in content_types:
        # Base query for general news
        query = Article.query
        
        # Filter by date (last 24 hours) for general news
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
        
        # Get general news articles
        general_articles = query.limit(limit//2 if len(content_types) > 1 else limit).all()
        all_content.extend(general_articles)
    
    # Get Trump news if selected
    if "trump_news" in content_types:
        # Query specific to Trump-related positive news
        trump_query = Article.query.filter(
            Article.title.ilike('%trump%'),
            Article.published_at >= (datetime.utcnow() - timedelta(days=2))  # Wider time range for Trump news
        )
        
        # Order by publish date (newest first)
        trump_query = trump_query.order_by(Article.published_at.desc())
        
        # Apply source exclusions if specified
        if excluded_sources:
            trump_query = trump_query.filter(~Article.source_name.in_(excluded_sources))
            
        # Get Trump news articles
        trump_articles = trump_query.limit(limit//2 if len(content_types) > 1 else limit).all()
        all_content.extend(trump_articles)
    
    # Get executive orders if selected
    if "executive_orders" in content_types:
        # Query for executive orders, sorted by date issued (newest first)
        eo_query = ExecutiveOrder.query.order_by(ExecutiveOrder.date_issued.desc())
        
        # Get latest executive orders
        exec_orders = eo_query.limit(3).all()  # Limit to 3 executive orders
        
        # Convert executive orders to article-like format for the template
        for order in exec_orders:
            # Create a dictionary with the same keys as an Article would have
            order_dict = {
                'title': f"Executive Order: {order.title}",
                'url': url_for('executive_order_detail', order_id=order.id, _external=True),
                'source_name': 'White House',
                'published_at': order.date_issued,
                'summary': order.summary,
                'is_executive_order': True,
                'order_number': order.order_number
            }
            all_content.append(order_dict)
    
    # Sort combined content by date (newest first)
    # For exec orders which are dictionaries, we need to sort by the published_at key
    # For regular articles, we sort by the published_at attribute
    all_content.sort(key=lambda x: x['published_at'] if isinstance(x, dict) else x.published_at, reverse=True)
    
    # Limit final results
    return all_content[:limit]

def send_all_daily_digests():
    """
    Send daily digest emails to all confirmed and active subscribers
    
    Returns:
        tuple: (successful_count, failed_count)
    """
    from models import EmailSubscriber
    from app import db
    
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
        if send_daily_digest(subscriber, db):
            successful_count += 1
        else:
            failed_count += 1
    
    logger.info(f"Sent {successful_count} digests successfully, {failed_count} failed")
    
    return successful_count, failed_count