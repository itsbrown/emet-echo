from datetime import datetime
import json
import logging

# Import db from separate file to avoid circular imports
from app import db

from constants import CONSERVATIVE_SOURCE_FRAGMENTS

class Article(db.Model):
    """Model for storing articles"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    url = db.Column(db.String(500), nullable=False, unique=True)
    source_name = db.Column(db.String(300))
    source_url = db.Column(db.String(500))
    published_at = db.Column(db.DateTime)
    author = db.Column(db.Text)
    description = db.Column(db.Text)
    content = db.Column(db.Text)
    summary = db.Column(db.Text)
    url_to_image = db.Column(db.String(500))
    category = db.Column(db.String(100))
    source_type = db.Column(db.String(50))  # 'conservative' or 'independent'
    indie_vs_mainstream = db.Column(db.Text)  # AI-generated indie vs. mainstream comparison (JSON)
    bias_score = db.Column(db.Integer)  # 0-100 bias score
    omission_callouts = db.Column(db.Text)  # JSON list of omission callout strings
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_public_dict(self):
        """Central serializer for Article -> template-friendly dict.
        Replaces many near-identical dict constructions across app.py and scheduler.
        Callers can still override/add 'ivm' / 'omission_callouts' after loading JSON if needed.
        """
        import json as _json  # local to avoid top-level issues
        def _safe_load(val, default=None):
            if not val:
                return default
            try:
                return _json.loads(val)
            except Exception:
                return default

        return {
            'title': self.title,
            'url': self.url,
            'source': {'name': self.source_name},
            'publishedAt': self.published_at.isoformat() if self.published_at else '',
            'author': self.author,
            'description': self.description,
            'content': self.content,
            'summary': self.summary,
            'urlToImage': self.url_to_image,
            'published_time': self.published_at.strftime("%B %d, %Y") if self.published_at else '',
            'source_type': self.source_type,
            'bias_score': self.bias_score,
            'ivm': _safe_load(self.indie_vs_mainstream),
            'omission_callouts': _safe_load(self.omission_callouts, default=[]),
        }

    @classmethod
    def from_news_dict(cls, data: dict):
        """Helper to create an Article from raw NewsAPI / scraper dict (from fetch_news, search_news etc).
        Also tolerates the 'public dict' shape from to_public_dict (for cache fallbacks).
        Centralizes the tedious .get() and date parsing and source_type logic.
        """
        published_at = None
        pub = data.get('publishedAt')
        if pub:
            try:
                published_at = datetime.fromisoformat(pub.replace('Z', '+00:00'))
            except Exception:
                pass

        # Support both raw {'source': {'name': ...}} and public {'source_name': ..., 'source': {'name':...}}
        source = data.get('source') or {}
        if not isinstance(source, dict):
            source = {}
        source_name = data.get('source_name') or source.get('name', '')
        source_url = data.get('source_url') or source.get('url', '')

        return cls(
            title=data.get('title', 'No Title'),
            url=data.get('url', ''),
            source_name=source_name,
            source_url=source_url,
            published_at=published_at,
            author=data.get('author', ''),
            description=data.get('description', ''),
            content=data.get('content', ''),
            url_to_image=data.get('urlToImage', ''),
            category=data.get('category', 'general'),
            source_type='conservative' if any(
                frag in (data.get('url') or '').lower() for frag in CONSERVATIVE_SOURCE_FRAGMENTS
            ) else 'independent'
        )

class UserPreference(db.Model):
    """Model for storing user preferences"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), unique=True)  # Session ID or user ID
    preferred_sources = db.Column(db.Text)  # JSON string of preferred sources
    preferred_categories = db.Column(db.Text)  # JSON string of preferred categories
    excluded_sources = db.Column(db.Text)  # JSON string of excluded sources
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SearchHistory(db.Model):
    """Model for storing search history"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100))  # Session ID or user ID
    query = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ExecutiveOrder(db.Model):
    """Model for storing Trump Executive Orders"""
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True)
    title = db.Column(db.String(500))
    date_issued = db.Column(db.DateTime)
    full_text = db.Column(db.Text)
    summary = db.Column(db.Text)
    status = db.Column(db.String(100))  # e.g., Active, Revoked, Amended
    category = db.Column(db.String(200))  # Policy area e.g., Immigration, Energy
    url = db.Column(db.String(500))  # Link to official document
    source = db.Column(db.String(300))  # Source of the executive order data
    ai_summary = db.Column(db.Text)  # AI-generated neutral summary (150-250 words)
    indie_vs_mainstream = db.Column(db.Text)  # AI-generated indie vs. mainstream comparison (JSON or text)
    historical_context = db.Column(db.Text)  # AI-generated historical cycle connection
    data_ties = db.Column(db.Text)  # AI-generated data/economic context note
    poll_yes = db.Column(db.Integer, default=0)  # Poll: helps independents
    poll_no = db.Column(db.Integer, default=0)   # Poll: hurts independents
    ai_quip = db.Column(db.Text)  # AI-generated punchy one-liner (≤20 words)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def from_federal_register_dict(cls, data: dict):
        """Create ExecutiveOrder from the raw dicts produced by fetch_executive_orders in executive_orders.py.
        Centralizes date parsing and defaults.
        """
        date_issued = None
        date_str = data.get('date_issued') or data.get('signing_date')
        if date_str:
            for fmt in ('%Y-%m-%d', '%m/%d/%Y'):
                try:
                    date_issued = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            if date_issued is None:
                logging.getLogger(__name__).warning(f"Could not parse date '{date_str}', using current date")
                date_issued = datetime.now()
        else:
            date_issued = datetime.now()

        summary = data.get('summary', '')
        if not summary and data.get('full_text'):
            # Note: caller may still want to call summarize_order separately if needed
            summary = data.get('summary', '')

        return cls(
            order_number=data.get('order_number') or data.get('document_number', 'UNKNOWN'),
            title=data.get('title', 'Untitled EO'),
            date_issued=date_issued,
            full_text=data.get('full_text', ''),
            summary=summary,
            status=data.get('status', 'Active'),
            category=data.get('category', 'Federal Regulation'),
            url=data.get('url') or data.get('html_url', ''),
            source=data.get('source', 'Federal Register')
        )

    def to_display_dict(self):
        """Compact dict for home page recent_eos lists etc."""
        return {
            'title': self.title,
            'date_issued': self.date_issued.strftime('%Y-%m-%d') if self.date_issued else '',
            'category': self.category or '',
            'order_number': self.order_number,
        }

    def to_missed_angle_dict(self, blurb: str, is_fallback: bool = False):
        return {
            'title': self.title,
            'order_number': self.order_number,
            'blurb': blurb,
            'is_fallback': is_fallback,
        }

class EmailSubscriber(db.Model):
    """Model for storing email newsletter subscribers"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    
    # Preferences (stored as JSON strings)
    preferred_categories = db.Column(db.Text, default='[]')  # JSON string of categories 
    preferred_sources = db.Column(db.Text, default='[]')     # JSON string of sources
    excluded_sources = db.Column(db.Text, default='[]')      # JSON string of excluded sources
    
    # Content type preferences
    content_types = db.Column(db.Text, default='["general"]')  # JSON string of content types: "general", "trump_news", "executive_orders"
    
    # Email frequency
    frequency = db.Column(db.String(20), default='daily')    # 'daily', 'weekly', etc.
    
    # Tracking fields
    is_active = db.Column(db.Boolean, default=True)          # For opt-out/unsubscribe
    confirmation_token = db.Column(db.String(100))           # For double opt-in confirmation
    confirmed_at = db.Column(db.DateTime)                    # When user confirmed subscription
    last_email_sent = db.Column(db.DateTime)                 # When the last email was sent
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_preferred_categories(self):
        """Get preferred categories as a list"""
        if not self.preferred_categories:
            return []
        return json.loads(self.preferred_categories)
    
    def get_preferred_sources(self):
        """Get preferred sources as a list"""
        if not self.preferred_sources:
            return []
        return json.loads(self.preferred_sources)
    
    def get_excluded_sources(self):
        """Get excluded sources as a list"""
        if not self.excluded_sources:
            return []
        return json.loads(self.excluded_sources)
    
    def set_preferred_categories(self, categories):
        """Set preferred categories from a list"""
        self.preferred_categories = json.dumps(categories)
    
    def set_preferred_sources(self, sources):
        """Set preferred sources from a list"""
        self.preferred_sources = json.dumps(sources)
    
    def set_excluded_sources(self, sources):
        """Set excluded sources from a list"""
        self.excluded_sources = json.dumps(sources)
        
    def get_content_types(self):
        """Get content types preferences as a list"""
        if not self.content_types:
            return ["general"]
        return json.loads(self.content_types)
        
    def set_content_types(self, types):
        """Set content types preferences from a list"""
        self.content_types = json.dumps(types)
        
class SuggestedNewsSource(db.Model):
    """Model for user-suggested news sources"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    source_type = db.Column(db.String(50))  # 'conservative' or 'independent'
    submitter_name = db.Column(db.String(100))
    submitter_email = db.Column(db.String(255))
    reason = db.Column(db.Text)  # Why this source should be included
    status = db.Column(db.String(50), default='pending')  # 'pending', 'approved', 'rejected'
    admin_notes = db.Column(db.Text)  # Admin notes on this suggestion
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class XHandle(db.Model):
    """Model for storing monitored X (Twitter) handles"""
    id = db.Column(db.Integer, primary_key=True)
    handle = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PrintifyProduct(db.Model):
    """Model for caching Printify products locally"""
    id = db.Column(db.Integer, primary_key=True)
    printify_id = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(1000))
    min_price = db.Column(db.Float, default=0)
    max_price = db.Column(db.Float, default=0)
    tags = db.Column(db.Text)  # JSON string of tags
    is_visible = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)