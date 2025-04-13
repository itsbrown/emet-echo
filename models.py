from datetime import datetime

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