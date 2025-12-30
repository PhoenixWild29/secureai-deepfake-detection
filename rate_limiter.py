# Rate Limiting for Flask API
# Install: pip install Flask-Limiter

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, request

def setup_rate_limiter(app: Flask):
    """Setup rate limiting for Flask app"""
    
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per hour", "50 per minute"],
        storage_uri="memory://",  # Use Redis in production: "redis://localhost:6379"
        strategy="fixed-window"
    )
    
    # Custom limits for specific endpoints
    @limiter.limit("10 per minute")
    def video_upload_limit():
        """Limit video uploads to 10 per minute"""
        pass
    
    @limiter.limit("30 per minute")
    def api_limit():
        """Limit general API calls to 30 per minute"""
        pass
    
    @limiter.limit("5 per hour")
    def blockchain_submit_limit():
        """Limit blockchain submissions to 5 per hour"""
        pass
    
    return limiter

# Usage in api.py:
# from rate_limiter import setup_rate_limiter
# limiter = setup_rate_limiter(app)
#
# @app.route('/api/analyze', methods=['POST'])
# @limiter.limit("10 per minute")
# def analyze_video():
#     ...

