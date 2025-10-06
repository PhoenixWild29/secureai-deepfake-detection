#!/usr/bin/env python3
"""
User Preferences Configuration
Configuration settings for user preferences management system
"""

import os
from typing import Dict, Any, Optional, List
from pydantic import BaseSettings, Field
from enum import Enum


class PreferencesStorageType(str, Enum):
    """Preferences storage type options"""
    DATABASE = "database"
    CACHE = "cache"
    HYBRID = "hybrid"


class PreferencesValidationLevel(str, Enum):
    """Preferences validation level options"""
    BASIC = "basic"
    STRICT = "strict"
    CUSTOM = "custom"


class PreferencesConfig(BaseSettings):
    """
    User preferences configuration settings
    """
    
    # General Settings
    preferences_enabled: bool = Field(default=True, description="Enable user preferences functionality")
    preferences_version: str = Field(default="1.0.0", description="User preferences API version")
    preferences_debug: bool = Field(default=False, description="Enable preferences debug mode")
    
    # Storage Configuration
    storage_type: PreferencesStorageType = Field(
        default=PreferencesStorageType.DATABASE,
        description="Preferences storage type"
    )
    cache_enabled: bool = Field(default=True, description="Enable preferences caching")
    cache_ttl_seconds: int = Field(default=300, description="Cache TTL in seconds")
    cache_max_size_mb: int = Field(default=50, description="Maximum cache size in MB")
    
    # Validation Configuration
    validation_enabled: bool = Field(default=True, description="Enable preferences validation")
    validation_level: PreferencesValidationLevel = Field(
        default=PreferencesValidationLevel.STRICT,
        description="Validation level for preferences"
    )
    auto_fix_validation_errors: bool = Field(default=False, description="Automatically fix validation errors")
    
    # Security Configuration
    role_based_customization: bool = Field(default=True, description="Enable role-based customization")
    audit_logging_enabled: bool = Field(default=True, description="Enable audit logging")
    history_retention_days: int = Field(default=365, description="History retention period in days")
    max_preferences_size_kb: int = Field(default=1024, description="Maximum preferences size in KB")
    
    # Performance Configuration
    max_widgets_per_user: int = Field(default=20, description="Maximum widgets per user")
    max_custom_settings: int = Field(default=50, description="Maximum custom settings per user")
    batch_operations_enabled: bool = Field(default=True, description="Enable batch operations")
    async_validation: bool = Field(default=True, description="Enable asynchronous validation")
    
    # Default Settings
    default_theme: str = Field(default="light", description="Default theme type")
    default_layout: str = Field(default="grid", description="Default layout type")
    default_notifications: bool = Field(default=True, description="Default notification setting")
    auto_create_defaults: bool = Field(default=True, description="Auto-create default preferences for new users")
    
    # Role-based Defaults
    admin_default_widgets: int = Field(default=8, description="Default widget count for admin users")
    analyst_default_widgets: int = Field(default=6, description="Default widget count for analyst users")
    viewer_default_widgets: int = Field(default=4, description="Default widget count for viewer users")
    security_officer_default_widgets: int = Field(default=7, description="Default widget count for security officers")
    compliance_manager_default_widgets: int = Field(default=5, description="Default widget count for compliance managers")
    
    # Feature Flags
    feature_widget_customization: bool = Field(default=True, description="Enable widget customization")
    feature_theme_selection: bool = Field(default=True, description="Enable theme selection")
    feature_layout_customization: bool = Field(default=True, description="Enable layout customization")
    feature_notification_settings: bool = Field(default=True, description="Enable notification settings")
    feature_accessibility_options: bool = Field(default=True, description="Enable accessibility options")
    feature_custom_settings: bool = Field(default=True, description="Enable custom settings")
    feature_preferences_history: bool = Field(default=True, description="Enable preferences history")
    feature_preferences_export: bool = Field(default=True, description="Enable preferences export")
    feature_preferences_import: bool = Field(default=True, description="Enable preferences import")
    
    # API Configuration
    max_request_size_kb: int = Field(default=512, description="Maximum request size in KB")
    request_timeout_seconds: int = Field(default=30, description="Request timeout in seconds")
    rate_limit_requests_per_minute: int = Field(default=60, description="Rate limit requests per minute")
    rate_limit_requests_per_hour: int = Field(default=1000, description="Rate limit requests per hour")
    
    # Database Configuration
    database_connection_pool_size: int = Field(default=10, description="Database connection pool size")
    database_query_timeout_seconds: int = Field(default=10, description="Database query timeout")
    database_retry_attempts: int = Field(default=3, description="Database retry attempts")
    
    # Monitoring Configuration
    monitoring_enabled: bool = Field(default=True, description="Enable preferences monitoring")
    metrics_collection_enabled: bool = Field(default=True, description="Enable metrics collection")
    alert_on_validation_failures: bool = Field(default=True, description="Alert on validation failures")
    alert_on_storage_errors: bool = Field(default=True, description="Alert on storage errors")
    
    class Config:
        env_prefix = "PREFERENCES_"
        case_sensitive = False
        env_file = ".env"


class PreferencesLimits:
    """
    Preferences system limits and constraints
    """
    
    # Widget Limits
    MAX_WIDGETS_PER_USER = 25
    MAX_WIDGET_WIDTH = 12
    MAX_WIDGET_HEIGHT = 8
    MIN_WIDGET_WIDTH = 1
    MIN_WIDGET_HEIGHT = 1
    
    # Layout Limits
    MAX_GRID_COLUMNS = 24
    MIN_GRID_COLUMNS = 6
    MAX_GRID_GAP = 32
    MIN_GRID_GAP = 4
    
    # Theme Limits
    MAX_CUSTOM_COLORS = 10
    MIN_FONT_SIZE = 0.5
    MAX_FONT_SIZE = 2.0
    
    # Notification Limits
    MAX_EMAIL_ADDRESSES = 3
    MAX_PHONE_NUMBERS = 2
    MAX_ALERT_TYPES = 20
    
    # Storage Limits
    MAX_PREFERENCES_SIZE_KB = 2048
    MAX_CUSTOM_SETTINGS = 100
    MAX_HISTORY_RECORDS = 1000
    
    # Performance Limits
    MAX_VALIDATION_TIME_MS = 5000
    MAX_STORAGE_TIME_MS = 10000
    MAX_CACHE_ENTRIES = 10000


class PreferencesEndpoints:
    """
    Preferences API endpoint configuration
    """
    
    # API Endpoints
    PREFERENCES_BASE_PATH = "/api/v1/dashboard/preferences"
    PREFERENCES_CREATE_PATH = ""
    PREFERENCES_GET_PATH = ""
    PREFERENCES_UPDATE_PATH = ""
    PREFERENCES_DELETE_PATH = "/delete"
    PREFERENCES_DEFAULTS_PATH = "/defaults"
    PREFERENCES_VALIDATE_PATH = "/validate"
    PREFERENCES_SUMMARY_PATH = "/summary"
    PREFERENCES_HISTORY_PATH = "/history"
    PREFERENCES_RESTORE_PATH = "/restore"
    PREFERENCES_EXPORT_PATH = "/export"
    PREFERENCES_IMPORT_PATH = "/import"
    
    # Response Formats
    SUPPORTED_RESPONSE_FORMATS = ["json", "yaml"]
    DEFAULT_RESPONSE_FORMAT = "json"
    
    # Pagination
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 200
    MIN_PAGE_SIZE = 10


class PreferencesValidation:
    """
    Preferences validation rules and constraints
    """
    
    # Widget Validation Rules
    WIDGET_ID_PATTERN = r"^[a-zA-Z0-9_-]+$"
    WIDGET_ID_MIN_LENGTH = 3
    WIDGET_ID_MAX_LENGTH = 50
    
    # Color Validation Rules
    HEX_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"
    
    # Email Validation Rules
    EMAIL_PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    
    # Phone Validation Rules
    PHONE_PATTERN = r"^\+?[1-9]\d{1,14}$"
    
    # Theme Validation Rules
    VALID_THEME_TYPES = ["light", "dark", "high_contrast", "auto"]
    VALID_FONT_SIZES = ["small", "medium", "large", "xlarge"]
    VALID_FONT_FAMILIES = ["system", "serif", "sans-serif", "monospace"]
    
    # Layout Validation Rules
    VALID_LAYOUT_TYPES = ["grid", "list", "compact", "expanded", "custom"]
    
    # Notification Validation Rules
    VALID_NOTIFICATION_TYPES = ["email", "in_app", "push", "sms"]
    VALID_NOTIFICATION_FREQUENCIES = ["immediate", "daily", "weekly", "monthly", "never"]


class PreferencesFeatures:
    """
    Feature flags and capabilities
    """
    
    # Core Features
    WIDGET_CUSTOMIZATION = "widget_customization"
    THEME_SELECTION = "theme_selection"
    LAYOUT_CUSTOMIZATION = "layout_customization"
    NOTIFICATION_SETTINGS = "notification_settings"
    ACCESSIBILITY_OPTIONS = "accessibility_options"
    CUSTOM_SETTINGS = "custom_settings"
    
    # Advanced Features
    PREFERENCES_HISTORY = "preferences_history"
    PREFERENCES_EXPORT = "preferences_export"
    PREFERENCES_IMPORT = "preferences_import"
    PREFERENCES_SHARING = "preferences_sharing"
    PREFERENCES_TEMPLATES = "preferences_templates"
    PREFERENCES_BACKUP = "preferences_backup"
    
    # Role-based Features
    ROLE_BASED_CUSTOMIZATION = "role_based_customization"
    ADMIN_OVERRIDE = "admin_override"
    USER_MANAGEMENT = "user_management"
    SYSTEM_DEFAULTS = "system_defaults"
    
    # Performance Features
    CACHING = "caching"
    ASYNC_VALIDATION = "async_validation"
    BATCH_OPERATIONS = "batch_operations"
    OPTIMISTIC_UPDATES = "optimistic_updates"


class PreferencesRoles:
    """
    Role-based permissions and capabilities
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
            PreferencesFeatures.WIDGET_CUSTOMIZATION,
            PreferencesFeatures.THEME_SELECTION,
            PreferencesFeatures.LAYOUT_CUSTOMIZATION,
            PreferencesFeatures.NOTIFICATION_SETTINGS,
            PreferencesFeatures.ACCESSIBILITY_OPTIONS,
            PreferencesFeatures.CUSTOM_SETTINGS,
            PreferencesFeatures.PREFERENCES_HISTORY,
            PreferencesFeatures.PREFERENCES_EXPORT,
            PreferencesFeatures.PREFERENCES_IMPORT,
            PreferencesFeatures.ADMIN_OVERRIDE,
            PreferencesFeatures.USER_MANAGEMENT,
            PreferencesFeatures.SYSTEM_DEFAULTS
        ],
        "system_admin": [
            PreferencesFeatures.WIDGET_CUSTOMIZATION,
            PreferencesFeatures.THEME_SELECTION,
            PreferencesFeatures.LAYOUT_CUSTOMIZATION,
            PreferencesFeatures.NOTIFICATION_SETTINGS,
            PreferencesFeatures.ACCESSIBILITY_OPTIONS,
            PreferencesFeatures.CUSTOM_SETTINGS,
            PreferencesFeatures.PREFERENCES_HISTORY,
            PreferencesFeatures.PREFERENCES_EXPORT,
            PreferencesFeatures.SYSTEM_DEFAULTS
        ],
        "security_officer": [
            PreferencesFeatures.WIDGET_CUSTOMIZATION,
            PreferencesFeatures.THEME_SELECTION,
            PreferencesFeatures.LAYOUT_CUSTOMIZATION,
            PreferencesFeatures.NOTIFICATION_SETTINGS,
            PreferencesFeatures.ACCESSIBILITY_OPTIONS,
            PreferencesFeatures.CUSTOM_SETTINGS,
            PreferencesFeatures.PREFERENCES_HISTORY,
            PreferencesFeatures.PREFERENCES_EXPORT
        ],
        "compliance_manager": [
            PreferencesFeatures.WIDGET_CUSTOMIZATION,
            PreferencesFeatures.THEME_SELECTION,
            PreferencesFeatures.LAYOUT_CUSTOMIZATION,
            PreferencesFeatures.NOTIFICATION_SETTINGS,
            PreferencesFeatures.ACCESSIBILITY_OPTIONS,
            PreferencesFeatures.CUSTOM_SETTINGS,
            PreferencesFeatures.PREFERENCES_HISTORY,
            PreferencesFeatures.PREFERENCES_EXPORT
        ],
        "analyst": [
            PreferencesFeatures.WIDGET_CUSTOMIZATION,
            PreferencesFeatures.THEME_SELECTION,
            PreferencesFeatures.LAYOUT_CUSTOMIZATION,
            PreferencesFeatures.NOTIFICATION_SETTINGS,
            PreferencesFeatures.ACCESSIBILITY_OPTIONS,
            PreferencesFeatures.CUSTOM_SETTINGS
        ],
        "viewer": [
            PreferencesFeatures.THEME_SELECTION,
            PreferencesFeatures.LAYOUT_CUSTOMIZATION,
            PreferencesFeatures.NOTIFICATION_SETTINGS,
            PreferencesFeatures.ACCESSIBILITY_OPTIONS
        ]
    }


# Global configuration instance
_preferences_config: Optional[PreferencesConfig] = None


def get_preferences_config() -> PreferencesConfig:
    """Get global preferences configuration instance"""
    global _preferences_config
    
    if _preferences_config is None:
        _preferences_config = PreferencesConfig()
    
    return _preferences_config


def get_preferences_limits() -> PreferencesLimits:
    """Get preferences limits"""
    return PreferencesLimits()


def get_preferences_endpoints() -> PreferencesEndpoints:
    """Get preferences endpoints configuration"""
    return PreferencesEndpoints()


def get_preferences_validation() -> PreferencesValidation:
    """Get preferences validation configuration"""
    return PreferencesValidation()


def get_preferences_features() -> PreferencesFeatures:
    """Get preferences features configuration"""
    return PreferencesFeatures()


def get_preferences_roles() -> PreferencesRoles:
    """Get preferences roles configuration"""
    return PreferencesRoles()


# Environment-specific configurations
def get_development_config() -> Dict[str, Any]:
    """Get development-specific configuration"""
    return {
        "preferences_debug": True,
        "cache_enabled": False,
        "validation_level": "basic",
        "rate_limit_requests_per_minute": 1000,
        "monitoring_enabled": False,
        "auto_fix_validation_errors": True
    }


def get_production_config() -> Dict[str, Any]:
    """Get production-specific configuration"""
    return {
        "preferences_debug": False,
        "cache_enabled": True,
        "validation_level": "strict",
        "audit_logging_enabled": True,
        "monitoring_enabled": True,
        "metrics_collection_enabled": True,
        "auto_fix_validation_errors": False
    }


def get_testing_config() -> Dict[str, Any]:
    """Get testing-specific configuration"""
    return {
        "preferences_debug": True,
        "cache_enabled": False,
        "validation_level": "basic",
        "rate_limit_requests_per_minute": 10000,
        "monitoring_enabled": False,
        "auto_fix_validation_errors": True,
        "max_preferences_size_kb": 100,
        "max_widgets_per_user": 5
    }


def apply_environment_config(environment: str = "development") -> None:
    """
    Apply environment-specific configuration
    
    Args:
        environment: Environment name (development, production, testing)
    """
    global _preferences_config
    
    if environment == "production":
        config_overrides = get_production_config()
    elif environment == "testing":
        config_overrides = get_testing_config()
    else:  # development
        config_overrides = get_development_config()
    
    # Apply overrides
    if _preferences_config:
        for key, value in config_overrides.items():
            if hasattr(_preferences_config, key):
                setattr(_preferences_config, key, value)


# Configuration validation
def validate_preferences_config(config: PreferencesConfig) -> bool:
    """
    Validate preferences configuration
    
    Args:
        config: Preferences configuration to validate
        
    Returns:
        True if configuration is valid, False otherwise
    """
    try:
        # Validate numeric ranges
        if config.max_widgets_per_user <= 0:
            return False
        
        if config.cache_ttl_seconds <= 0:
            return False
        
        if config.history_retention_days <= 0:
            return False
        
        if config.max_preferences_size_kb <= 0:
            return False
        
        # Validate feature flags consistency
        if not config.feature_widget_customization and config.max_widgets_per_user > 0:
            return False
        
        # Validate role-based settings
        if config.role_based_customization and not config.auto_create_defaults:
            return False
        
        return True
        
    except Exception:
        return False


# Configuration utilities
def get_config_summary() -> Dict[str, Any]:
    """Get configuration summary for monitoring"""
    config = get_preferences_config()
    
    return {
        "version": config.preferences_version,
        "enabled": config.preferences_enabled,
        "debug": config.preferences_debug,
        "storage_type": config.storage_type.value,
        "cache_enabled": config.cache_enabled,
        "validation_enabled": config.validation_enabled,
        "validation_level": config.validation_level.value,
        "role_based_customization": config.role_based_customization,
        "audit_logging_enabled": config.audit_logging_enabled,
        "monitoring_enabled": config.monitoring_enabled,
        "features": {
            "widget_customization": config.feature_widget_customization,
            "theme_selection": config.feature_theme_selection,
            "layout_customization": config.feature_layout_customization,
            "notification_settings": config.feature_notification_settings,
            "accessibility_options": config.feature_accessibility_options,
            "custom_settings": config.feature_custom_settings,
            "preferences_history": config.feature_preferences_history,
            "preferences_export": config.feature_preferences_export,
            "preferences_import": config.feature_preferences_import
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
    roles_config = get_preferences_roles()
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
