# Sentry Configuration for Error Tracking
# Install: pip install sentry-sdk[flask]

import os
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from flask import Flask

def init_sentry(app: Flask):
    """Initialize Sentry for error tracking"""
    sentry_dsn = os.getenv('SENTRY_DSN')
    
    if not sentry_dsn:
        print("WARNING: Sentry DSN not configured. Error tracking disabled.")
        return
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            FlaskIntegration(),
            SqlalchemyIntegration(),
        ],
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        profiles_sample_rate=float(os.getenv('SENTRY_PROFILES_SAMPLE_RATE', '0.1')),
        # Environment
        environment=os.getenv('ENVIRONMENT', 'production'),
        # Release version
        release=os.getenv('APP_VERSION', '1.0.0'),
        # Filter sensitive data
        before_send=lambda event, hint: filter_sensitive_data(event),
    )
    
    print("OK: Sentry error tracking initialized")


def filter_sensitive_data(event):
    """Filter sensitive data from Sentry events"""
    # Remove sensitive headers
    if 'request' in event and 'headers' in event['request']:
        sensitive_headers = ['authorization', 'cookie', 'x-api-key']
        for header in sensitive_headers:
            event['request']['headers'].pop(header, None)
    
    # Remove sensitive user data
    if 'user' in event:
        event['user'].pop('email', None)
        event['user'].pop('ip_address', None)
    
    return event

# Usage in api.py:
# from monitoring.sentry_config import init_sentry
# init_sentry(app)

