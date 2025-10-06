#!/usr/bin/env python3
"""
Notifications Configuration
Configuration settings for dashboard notifications management system
"""

import os
from typing import Dict, Any, Optional, List
from pydantic import BaseSettings, Field
from enum import Enum


class NotificationDeliveryMode(str, Enum):
    """Notification delivery mode options"""
    IMMEDIATE = "immediate"
    BATCHED = "batched"
    SCHEDULED = "scheduled"


class NotificationRetentionPolicy(str, Enum):
    """Notification retention policy options"""
    SHORT = "short"  # 7 days
    MEDIUM = "medium"  # 30 days
    LONG = "long"  # 90 days
    PERMANENT = "permanent"


class NotificationConfig(BaseSettings):
    """
    Notifications configuration settings
    """
    
    # General Settings
    notifications_enabled: bool = Field(default=True, description="Enable notifications functionality")
    notifications_version: str = Field(default="1.0.0", description="Notifications API version")
    notifications_debug: bool = Field(default=False, description="Enable notifications debug mode")
    
    # Delivery Configuration
    delivery_mode: NotificationDeliveryMode = Field(
        default=NotificationDeliveryMode.IMMEDIATE,
        description="Default delivery mode for notifications"
    )
    max_delivery_attempts: int = Field(default=3, description="Maximum delivery attempts per notification")
    delivery_retry_delay_seconds: int = Field(default=60, description="Delay between delivery retries in seconds")
    batch_delivery_interval_seconds: int = Field(default=300, description="Interval for batch delivery processing")
    
    # Queue Configuration
    queue_enabled: bool = Field(default=True, description="Enable notification queue")
    queue_max_size: int = Field(default=10000, description="Maximum queue size")
    queue_processing_workers: int = Field(default=3, description="Number of queue processing workers")
    queue_timeout_seconds: int = Field(default=30, description="Queue operation timeout")
    
    # Real-time Configuration
    websocket_enabled: bool = Field(default=True, description="Enable WebSocket delivery")
    websocket_room_prefix: str = Field(default="notifications", description="WebSocket room prefix")
    websocket_heartbeat_interval: int = Field(default=30, description="WebSocket heartbeat interval in seconds")
    websocket_max_connections: int = Field(default=1000, description="Maximum WebSocket connections")
    
    # Email Configuration
    email_enabled: bool = Field(default=False, description="Enable email delivery")
    email_smtp_host: Optional[str] = Field(default=None, description="SMTP host for email delivery")
    email_smtp_port: int = Field(default=587, description="SMTP port")
    email_smtp_username: Optional[str] = Field(default=None, description="SMTP username")
    email_smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    email_from_address: Optional[str] = Field(default=None, description="Default from email address")
    email_from_name: str = Field(default="SecureAI Notifications", description="Default from name")
    
    # Push Notification Configuration
    push_enabled: bool = Field(default=False, description="Enable push notifications")
    push_firebase_config: Optional[str] = Field(default=None, description="Firebase configuration file path")
    push_apns_config: Optional[str] = Field(default=None, description="APNS configuration file path")
    
    # SMS Configuration
    sms_enabled: bool = Field(default=False, description="Enable SMS delivery")
    sms_provider: str = Field(default="twilio", description="SMS provider (twilio, aws_sns)")
    sms_twilio_account_sid: Optional[str] = Field(default=None, description="Twilio account SID")
    sms_twilio_auth_token: Optional[str] = Field(default=None, description="Twilio auth token")
    sms_twilio_from_number: Optional[str] = Field(default=None, description="Twilio from number")
    
    # Webhook Configuration
    webhook_enabled: bool = Field(default=False, description="Enable webhook delivery")
    webhook_timeout_seconds: int = Field(default=10, description="Webhook timeout in seconds")
    webhook_max_retries: int = Field(default=3, description="Maximum webhook retries")
    webhook_retry_delay_seconds: int = Field(default=30, description="Webhook retry delay")
    
    # Retention and Cleanup
    retention_policy: NotificationRetentionPolicy = Field(
        default=NotificationRetentionPolicy.MEDIUM,
        description="Notification retention policy"
    )
    cleanup_enabled: bool = Field(default=True, description="Enable automatic cleanup")
    cleanup_interval_hours: int = Field(default=24, description="Cleanup interval in hours")
    cleanup_batch_size: int = Field(default=1000, description="Cleanup batch size")
    
    # Performance Configuration
    max_notifications_per_user: int = Field(default=1000, description="Maximum notifications per user")
    max_notifications_per_minute: int = Field(default=100, description="Rate limit per minute")
    max_notifications_per_hour: int = Field(default=1000, description="Rate limit per hour")
    notification_size_limit_kb: int = Field(default=64, description="Maximum notification size in KB")
    
    # Security Configuration
    encryption_enabled: bool = Field(default=True, description="Enable notification encryption")
    encryption_key: Optional[str] = Field(default=None, description="Encryption key for sensitive data")
    audit_logging_enabled: bool = Field(default=True, description="Enable audit logging")
    rate_limiting_enabled: bool = Field(default=True, description="Enable rate limiting")
    
    # Feature Flags
    feature_real_time_delivery: bool = Field(default=True, description="Enable real-time delivery")
    feature_batch_delivery: bool = Field(default=True, description="Enable batch delivery")
    feature_scheduled_delivery: bool = Field(default=True, description="Enable scheduled delivery")
    feature_notification_preferences: bool = Field(default=True, description="Enable user preferences")
    feature_notification_history: bool = Field(default=True, description="Enable notification history")
    feature_notification_templates: bool = Field(default=False, description="Enable notification templates")
    feature_notification_analytics: bool = Field(default=True, description="Enable notification analytics")
    
    # Integration Configuration
    morpheus_integration_enabled: bool = Field(default=True, description="Enable Morpheus security integration")
    real_time_alerting_enabled: bool = Field(default=True, description="Enable real-time alerting integration")
    websocket_integration_enabled: bool = Field(default=True, description="Enable WebSocket integration")
    
    # Monitoring Configuration
    monitoring_enabled: bool = Field(default=True, description="Enable notifications monitoring")
    metrics_collection_enabled: bool = Field(default=True, description="Enable metrics collection")
    alert_on_delivery_failures: bool = Field(default=True, description="Alert on delivery failures")
    alert_on_queue_overload: bool = Field(default=True, description="Alert on queue overload")
    
    # API Configuration
    api_rate_limit_requests_per_minute: int = Field(default=60, description="API rate limit requests per minute")
    api_rate_limit_requests_per_hour: int = Field(default=1000, description="API rate limit requests per hour")
    api_max_page_size: int = Field(default=100, description="Maximum page size for API responses")
    api_default_page_size: int = Field(default=20, description="Default page size for API responses")
    
    class Config:
        env_prefix = "NOTIFICATIONS_"
        case_sensitive = False
        env_file = ".env"


class NotificationLimits:
    """
    Notifications system limits and constraints
    """
    
    # Notification Limits
    MAX_NOTIFICATION_TITLE_LENGTH = 200
    MAX_NOTIFICATION_MESSAGE_LENGTH = 1000
    MAX_NOTIFICATION_SUMMARY_LENGTH = 500
    MAX_NOTIFICATION_TAGS = 10
    MAX_NOTIFICATION_CONTEXT_SIZE_KB = 32
    
    # Delivery Limits
    MAX_DELIVERY_METHODS = 5
    MAX_SCHEDULED_NOTIFICATIONS = 10000
    MAX_BATCH_SIZE = 100
    
    # User Limits
    MAX_NOTIFICATIONS_PER_USER = 10000
    MAX_USER_PREFERENCES_SIZE_KB = 16
    MAX_QUIET_HOURS_RANGE = 24  # hours
    
    # System Limits
    MAX_QUEUE_SIZE = 50000
    MAX_CONCURRENT_DELIVERIES = 100
    MAX_DELIVERY_TIMEOUT_SECONDS = 30
    
    # Retention Limits
    MAX_RETENTION_DAYS = 365
    MIN_RETENTION_DAYS = 1
    MAX_CLEANUP_BATCH_SIZE = 5000


class NotificationEndpoints:
    """
    Notifications API endpoint configuration
    """
    
    # API Endpoints
    NOTIFICATIONS_BASE_PATH = "/api/v1/dashboard/notifications"
    NOTIFICATIONS_LIST_PATH = ""
    NOTIFICATIONS_CREATE_PATH = ""
    NOTIFICATIONS_UPDATE_PATH = "/{notification_id}"
    NOTIFICATIONS_DELETE_PATH = "/{notification_id}"
    NOTIFICATIONS_STATS_PATH = "/stats"
    NOTIFICATIONS_PREFERENCES_PATH = "/preferences"
    NOTIFICATIONS_HISTORY_PATH = "/history"
    NOTIFICATIONS_BULK_UPDATE_PATH = "/bulk"
    NOTIFICATIONS_CLEANUP_PATH = "/cleanup"
    NOTIFICATIONS_HEALTH_PATH = "/health"
    
    # Response Formats
    SUPPORTED_RESPONSE_FORMATS = ["json"]
    DEFAULT_RESPONSE_FORMAT = "json"
    
    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    MIN_PAGE_SIZE = 1


class NotificationValidation:
    """
    Notifications validation rules and constraints
    """
    
    # Notification Type Validation
    VALID_NOTIFICATION_TYPES = [
        "analysis_completion", "system_status", "compliance_alert", "security_alert",
        "user_activity", "maintenance", "performance_alert", "blockchain_update",
        "export_completion", "training_completion"
    ]
    
    # Notification Category Validation
    VALID_NOTIFICATION_CATEGORIES = [
        "detection", "security", "system", "compliance", "user",
        "maintenance", "performance", "blockchain", "export", "training"
    ]
    
    # Priority Validation
    VALID_NOTIFICATION_PRIORITIES = ["critical", "high", "medium", "low"]
    PRIORITY_LEVELS = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    
    # Status Validation
    VALID_NOTIFICATION_STATUSES = [
        "pending", "delivered", "read", "acknowledged", "dismissed", "failed"
    ]
    
    # Delivery Method Validation
    VALID_DELIVERY_METHODS = ["in_app", "email", "push", "sms", "webhook"]
    
    # Action Validation
    VALID_NOTIFICATION_ACTIONS = [
        "acknowledge", "dismiss", "mark_read", "mark_unread", "archive", "restore"
    ]
    
    # Timing Validation
    VALID_DIGEST_FREQUENCIES = ["immediate", "hourly", "daily"]
    VALID_TIMEZONES = ["UTC", "America/New_York", "America/Los_Angeles", "Europe/London", "Asia/Tokyo"]
    
    # Email Validation
    EMAIL_PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    
    # Phone Validation
    PHONE_PATTERN = r"^\+?[1-9]\d{1,14}$"
    
    # Time Validation
    TIME_PATTERN = r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"


class NotificationFeatures:
    """
    Feature flags and capabilities
    """
    
    # Core Features
    NOTIFICATION_CREATION = "notification_creation"
    NOTIFICATION_DELIVERY = "notification_delivery"
    NOTIFICATION_FILTERING = "notification_filtering"
    NOTIFICATION_PREFERENCES = "notification_preferences"
    NOTIFICATION_HISTORY = "notification_history"
    
    # Advanced Features
    REAL_TIME_DELIVERY = "real_time_delivery"
    BATCH_DELIVERY = "batch_delivery"
    SCHEDULED_DELIVERY = "scheduled_delivery"
    NOTIFICATION_TEMPLATES = "notification_templates"
    NOTIFICATION_ANALYTICS = "notification_analytics"
    NOTIFICATION_ENCRYPTION = "notification_encryption"
    
    # Integration Features
    MORPHEUS_INTEGRATION = "morpheus_integration"
    REAL_TIME_ALERTING = "real_time_alerting"
    WEBSOCKET_INTEGRATION = "websocket_integration"
    EMAIL_INTEGRATION = "email_integration"
    PUSH_INTEGRATION = "push_integration"
    SMS_INTEGRATION = "sms_integration"
    WEBHOOK_INTEGRATION = "webhook_integration"
    
    # Management Features
    NOTIFICATION_CLEANUP = "notification_cleanup"
    NOTIFICATION_MONITORING = "notification_monitoring"
    NOTIFICATION_METRICS = "notification_metrics"
    NOTIFICATION_AUDIT = "notification_audit"


class NotificationRoles:
    """
    Role-based permissions for notifications
    """
    
    # Role Hierarchy (from highest to lowest privilege)
    ROLE_HIERARCHY = [
        "admin",
        "system_admin",
        "security_officer",
        "compliance_manager",
        "analyst",
        "viewer"
    ]
    
    # Role Capabilities
    ROLE_CAPABILITIES = {
        "admin": [
            NotificationFeatures.NOTIFICATION_CREATION,
            NotificationFeatures.NOTIFICATION_DELIVERY,
            NotificationFeatures.NOTIFICATION_FILTERING,
            NotificationFeatures.NOTIFICATION_PREFERENCES,
            NotificationFeatures.NOTIFICATION_HISTORY,
            NotificationFeatures.REAL_TIME_DELIVERY,
            NotificationFeatures.BATCH_DELIVERY,
            NotificationFeatures.SCHEDULED_DELIVERY,
            NotificationFeatures.NOTIFICATION_ANALYTICS,
            NotificationFeatures.NOTIFICATION_CLEANUP,
            NotificationFeatures.NOTIFICATION_MONITORING,
            NotificationFeatures.NOTIFICATION_METRICS,
            NotificationFeatures.NOTIFICATION_AUDIT
        ],
        "system_admin": [
            NotificationFeatures.NOTIFICATION_CREATION,
            NotificationFeatures.NOTIFICATION_DELIVERY,
            NotificationFeatures.NOTIFICATION_FILTERING,
            NotificationFeatures.NOTIFICATION_PREFERENCES,
            NotificationFeatures.NOTIFICATION_HISTORY,
            NotificationFeatures.REAL_TIME_DELIVERY,
            NotificationFeatures.BATCH_DELIVERY,
            NotificationFeatures.NOTIFICATION_ANALYTICS,
            NotificationFeatures.NOTIFICATION_CLEANUP,
            NotificationFeatures.NOTIFICATION_MONITORING
        ],
        "security_officer": [
            NotificationFeatures.NOTIFICATION_CREATION,
            NotificationFeatures.NOTIFICATION_DELIVERY,
            NotificationFeatures.NOTIFICATION_FILTERING,
            NotificationFeatures.NOTIFICATION_PREFERENCES,
            NotificationFeatures.NOTIFICATION_HISTORY,
            NotificationFeatures.REAL_TIME_DELIVERY,
            NotificationFeatures.NOTIFICATION_ANALYTICS,
            NotificationFeatures.MORPHEUS_INTEGRATION,
            NotificationFeatures.REAL_TIME_ALERTING
        ],
        "compliance_manager": [
            NotificationFeatures.NOTIFICATION_CREATION,
            NotificationFeatures.NOTIFICATION_DELIVERY,
            NotificationFeatures.NOTIFICATION_FILTERING,
            NotificationFeatures.NOTIFICATION_PREFERENCES,
            NotificationFeatures.NOTIFICATION_HISTORY,
            NotificationFeatures.NOTIFICATION_ANALYTICS,
            NotificationFeatures.NOTIFICATION_AUDIT
        ],
        "analyst": [
            NotificationFeatures.NOTIFICATION_DELIVERY,
            NotificationFeatures.NOTIFICATION_FILTERING,
            NotificationFeatures.NOTIFICATION_PREFERENCES,
            NotificationFeatures.NOTIFICATION_HISTORY
        ],
        "viewer": [
            NotificationFeatures.NOTIFICATION_DELIVERY,
            NotificationFeatures.NOTIFICATION_FILTERING,
            NotificationFeatures.NOTIFICATION_PREFERENCES
        ]
    }


# Global configuration instance
_notifications_config: Optional[NotificationConfig] = None


def get_notifications_config() -> NotificationConfig:
    """Get global notifications configuration instance"""
    global _notifications_config
    
    if _notifications_config is None:
        _notifications_config = NotificationConfig()
    
    return _notifications_config


def get_notifications_limits() -> NotificationLimits:
    """Get notifications limits"""
    return NotificationLimits()


def get_notifications_endpoints() -> NotificationEndpoints:
    """Get notifications endpoints configuration"""
    return NotificationEndpoints()


def get_notifications_validation() -> NotificationValidation:
    """Get notifications validation configuration"""
    return NotificationValidation()


def get_notifications_features() -> NotificationFeatures:
    """Get notifications features configuration"""
    return NotificationFeatures()


def get_notifications_roles() -> NotificationRoles:
    """Get notifications roles configuration"""
    return NotificationRoles()


# Environment-specific configurations
def get_development_config() -> Dict[str, Any]:
    """Get development-specific configuration"""
    return {
        "notifications_debug": True,
        "queue_enabled": False,
        "email_enabled": False,
        "push_enabled": False,
        "sms_enabled": False,
        "webhook_enabled": False,
        "monitoring_enabled": False,
        "rate_limiting_enabled": False,
        "cleanup_enabled": False,
        "max_notifications_per_minute": 1000,
        "max_notifications_per_hour": 10000
    }


def get_production_config() -> Dict[str, Any]:
    """Get production-specific configuration"""
    return {
        "notifications_debug": False,
        "queue_enabled": True,
        "email_enabled": True,
        "push_enabled": True,
        "sms_enabled": True,
        "webhook_enabled": True,
        "monitoring_enabled": True,
        "rate_limiting_enabled": True,
        "cleanup_enabled": True,
        "encryption_enabled": True,
        "audit_logging_enabled": True,
        "metrics_collection_enabled": True
    }


def get_testing_config() -> Dict[str, Any]:
    """Get testing-specific configuration"""
    return {
        "notifications_debug": True,
        "queue_enabled": False,
        "email_enabled": False,
        "push_enabled": False,
        "sms_enabled": False,
        "webhook_enabled": False,
        "monitoring_enabled": False,
        "rate_limiting_enabled": False,
        "cleanup_enabled": False,
        "max_notifications_per_minute": 10000,
        "max_notifications_per_hour": 100000,
        "max_notifications_per_user": 100
    }


def apply_environment_config(environment: str = "development") -> None:
    """
    Apply environment-specific configuration
    
    Args:
        environment: Environment name (development, production, testing)
    """
    global _notifications_config
    
    if environment == "production":
        config_overrides = get_production_config()
    elif environment == "testing":
        config_overrides = get_testing_config()
    else:  # development
        config_overrides = get_development_config()
    
    # Apply overrides
    if _notifications_config:
        for key, value in config_overrides.items():
            if hasattr(_notifications_config, key):
                setattr(_notifications_config, key, value)


# Configuration validation
def validate_notifications_config(config: NotificationConfig) -> bool:
    """
    Validate notifications configuration
    
    Args:
        config: Notifications configuration to validate
        
    Returns:
        True if configuration is valid, False otherwise
    """
    try:
        # Validate numeric ranges
        if config.max_delivery_attempts <= 0 or config.max_delivery_attempts > 10:
            return False
        
        if config.queue_max_size <= 0:
            return False
        
        if config.max_notifications_per_user <= 0:
            return False
        
        if config.cleanup_interval_hours <= 0:
            return False
        
        # Validate feature flags consistency
        if config.feature_real_time_delivery and not config.websocket_enabled:
            return False
        
        if config.feature_batch_delivery and not config.queue_enabled:
            return False
        
        # Validate integration settings
        if config.email_enabled and not config.email_smtp_host:
            return False
        
        if config.sms_enabled and not config.sms_twilio_account_sid:
            return False
        
        return True
        
    except Exception:
        return False


# Configuration utilities
def get_config_summary() -> Dict[str, Any]:
    """Get configuration summary for monitoring"""
    config = get_notifications_config()
    
    return {
        "version": config.notifications_version,
        "enabled": config.notifications_enabled,
        "debug": config.notifications_debug,
        "delivery_mode": config.delivery_mode.value,
        "queue_enabled": config.queue_enabled,
        "websocket_enabled": config.websocket_enabled,
        "email_enabled": config.email_enabled,
        "push_enabled": config.push_enabled,
        "sms_enabled": config.sms_enabled,
        "webhook_enabled": config.webhook_enabled,
        "monitoring_enabled": config.monitoring_enabled,
        "audit_logging_enabled": config.audit_logging_enabled,
        "features": {
            "real_time_delivery": config.feature_real_time_delivery,
            "batch_delivery": config.feature_batch_delivery,
            "scheduled_delivery": config.feature_scheduled_delivery,
            "notification_preferences": config.feature_notification_preferences,
            "notification_history": config.feature_notification_history,
            "notification_templates": config.feature_notification_templates,
            "notification_analytics": config.feature_notification_analytics
        },
        "integrations": {
            "morpheus_integration": config.morpheus_integration_enabled,
            "real_time_alerting": config.real_time_alerting_enabled,
            "websocket_integration": config.websocket_integration_enabled
        }
    }


def get_role_capabilities(role: str) -> List[str]:
    """
    Get capabilities for a specific role
    
    Args:
        role: User role
        
    Returns:
        List of capabilities for the role
    """
    roles_config = get_notifications_roles()
    return roles_config.ROLE_CAPABILITIES.get(role, [])


def is_capability_allowed(role: str, capability: str) -> bool:
    """
    Check if a role has a specific capability
    
    Args:
        role: User role
        capability: Capability to check
        
    Returns:
        True if capability is allowed, False otherwise
    """
    capabilities = get_role_capabilities(role)
    return capability in capabilities


def get_delivery_method_config(method: str) -> Dict[str, Any]:
    """
    Get configuration for a specific delivery method
    
    Args:
        method: Delivery method name
        
    Returns:
        Configuration for the delivery method
    """
    config = get_notifications_config()
    
    if method == "email":
        return {
            "enabled": config.email_enabled,
            "smtp_host": config.email_smtp_host,
            "smtp_port": config.email_smtp_port,
            "from_address": config.email_from_address,
            "from_name": config.email_from_name
        }
    
    elif method == "push":
        return {
            "enabled": config.push_enabled,
            "firebase_config": config.push_firebase_config,
            "apns_config": config.push_apns_config
        }
    
    elif method == "sms":
        return {
            "enabled": config.sms_enabled,
            "provider": config.sms_provider,
            "twilio_account_sid": config.sms_twilio_account_sid,
            "twilio_from_number": config.sms_twilio_from_number
        }
    
    elif method == "webhook":
        return {
            "enabled": config.webhook_enabled,
            "timeout_seconds": config.webhook_timeout_seconds,
            "max_retries": config.webhook_max_retries,
            "retry_delay_seconds": config.webhook_retry_delay_seconds
        }
    
    elif method == "in_app":
        return {
            "enabled": config.websocket_enabled,
            "room_prefix": config.websocket_room_prefix,
            "heartbeat_interval": config.websocket_heartbeat_interval,
            "max_connections": config.websocket_max_connections
        }
    
    return {"enabled": False}
