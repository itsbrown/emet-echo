from datetime import datetime
import json

# Import db from separate file to avoid circular imports
from app import db

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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