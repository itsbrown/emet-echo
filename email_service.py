import os
import logging
import uuid
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, TemplateId, Personalization
from flask import url_for, render_template, current_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SendGrid API Key
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
DEFAULT_FROM_EMAIL = 'news@trustedconservative.news'  # Replace with your sending domain

def init_app(app, db):
    """Initialize email service with app context"""
    
    # Register routes for subscription management
    @app.route('/subscribe', methods=['GET', 'POST'])
    def subscribe():
        """Subscription form and processing"""
        from flask import request, redirect, flash, session
        from models import EmailSubscriber
        
        if request.method == 'POST':
            email = request.form.get('email')
            first_name = request.form.get('first_name', '')
            last_name = request.form.get('last_name', '')
            
            if not email:
                flash('Email is required', 'danger')
                return redirect(url_for('subscribe'))
                
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
            
            # Create new subscriber
            new_subscriber = EmailSubscriber(
                email=email,
                first_name=first_name,
                last_name=last_name,
                confirmation_token=str(uuid.uuid4())
            )
            
            # Save to database
            db.session.add(new_subscriber)
            db.session.commit()
            
            # Send confirmation email
            if send_confirmation_email(new_subscriber, db):
                flash('Please check your email to confirm your subscription', 'success')
            else:
                flash('There was an error sending the confirmation email. Please try again later.', 'danger')
                
            return redirect(url_for('index'))
            
        # GET request - show form
        return render_template('subscribe.html')
    
    @app.route('/confirm/<token>')
    def confirm_subscription(token):
        """Confirm email subscription with token"""
        from flask import flash, redirect
        from models import EmailSubscriber
        
        subscriber = EmailSubscriber.query.filter_by(confirmation_token=token).first()
        
        if not subscriber:
            flash('Invalid confirmation link', 'danger')
            return redirect(url_for('index'))
            
        subscriber.confirmed_at = datetime.utcnow()
        db.session.commit()
        
        flash('Your subscription has been confirmed. Thank you!', 'success')
        return redirect(url_for('index'))
    
    @app.route('/unsubscribe/<token>')
    def unsubscribe(token):
        """Unsubscribe from newsletter"""
        from flask import flash, redirect
        from models import EmailSubscriber
        
        subscriber = EmailSubscriber.query.filter_by(confirmation_token=token).first()
        
        if not subscriber:
            flash('Invalid unsubscribe link', 'danger')
            return redirect(url_for('index'))
            
        subscriber.is_active = False
        db.session.commit()
        
        flash('You have been unsubscribed from our newsletter', 'success')
        return redirect(url_for('index'))
    
    @app.route('/manage-preferences/<token>')
    def manage_preferences(token):
        """Manage email preferences"""
        from flask import request, flash, redirect
        from models import EmailSubscriber
        
        subscriber = EmailSubscriber.query.filter_by(confirmation_token=token).first()
        
        if not subscriber:
            flash('Invalid link', 'danger')
            return redirect(url_for('index'))
            
        if request.method == 'POST':
            # Update preferences
            categories = request.form.getlist('categories')
            sources = request.form.getlist('sources')
            excluded = request.form.getlist('excluded_sources')
            
            subscriber.set_preferred_categories(categories)
            subscriber.set_preferred_sources(sources)
            subscriber.set_excluded_sources(excluded)
            
            db.session.commit()
            
            flash('Your preferences have been updated', 'success')
            return redirect(url_for('index'))
            
        # GET request - show form
        return render_template('preferences.html', subscriber=subscriber)

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
    from models import Article
    
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