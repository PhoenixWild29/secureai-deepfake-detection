#!/usr/bin/env python3
"""
Analytics Configuration
Configuration settings for analytics endpoint and data processing
"""

import os
from typing import Dict, Any, Optional
from pydantic import BaseSettings, Field
from enum import Enum


class AnalyticsCacheStrategy(str, Enum):
    """Analytics cache strategy options"""
    REDIS = "redis"
    MEMORY = "memory"
    NONE = "none"


class AnalyticsExportStrategy(str, Enum):
    """Analytics export strategy options"""
    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"
    BACKGROUND = "background"


class AnalyticsConfig(BaseSettings):
    """
    Analytics configuration settings
    """
    
    # General Analytics Settings
    analytics_enabled: bool = Field(default=True, description="Enable analytics functionality")
    analytics_version: str = Field(default="1.0.0", description="Analytics API version")
    analytics_debug: bool = Field(default=False, description="Enable analytics debug mode")
    
    # Data Processing Settings
    max_analytics_records: int = Field(default=10000, description="Maximum records per analytics query")
    default_date_range_days: int = Field(default=30, description="Default date range in days")
    analytics_timeout_seconds: int = Field(default=300, description="Analytics query timeout")
    
    # Caching Configuration
    cache_enabled: bool = Field(default=True, description="Enable analytics caching")
    cache_strategy: AnalyticsCacheStrategy = Field(
        default=AnalyticsCacheStrategy.REDIS, 
        description="Analytics cache strategy"
    )
    cache_ttl_seconds: int = Field(default=300, description="Cache TTL in seconds")
    cache_max_size_mb: int = Field(default=100, description="Maximum cache size in MB")
    
    # Export Configuration
    export_enabled: bool = Field(default=True, description="Enable analytics export")
    export_strategy: AnalyticsExportStrategy = Field(
        default=AnalyticsExportStrategy.ASYNCHRONOUS,
        description="Analytics export strategy"
    )
    export_directory: str = Field(default="exports", description="Export directory path")
    export_max_file_size_mb: int = Field(default=500, description="Maximum export file size in MB")
    export_compression_enabled: bool = Field(default=True, description="Enable export compression")
    export_retention_hours: int = Field(default=24, description="Export file retention in hours")
    
    # Security Configuration
    data_classification_enabled: bool = Field(default=True, description="Enable data classification")
    privacy_compliance_enabled: bool = Field(default=True, description="Enable privacy compliance checks")
    audit_logging_enabled: bool = Field(default=True, description="Enable audit logging")
    permission_cache_ttl_seconds: int = Field(default=60, description="Permission cache TTL")
    
    # Performance Configuration
    max_concurrent_queries: int = Field(default=10, description="Maximum concurrent analytics queries")
    query_batch_size: int = Field(default=1000, description="Query batch size for large datasets")
    trend_analysis_enabled: bool = Field(default=True, description="Enable trend analysis")
    predictive_analytics_enabled: bool = Field(default=True, description="Enable predictive analytics")
    insights_generation_enabled: bool = Field(default=True, description="Enable insights generation")
    
    # Data Layer Integration
    data_layer_timeout_seconds: int = Field(default=30, description="Data layer timeout")
    data_layer_retry_attempts: int = Field(default=3, description="Data layer retry attempts")
    data_layer_batch_size: int = Field(default=500, description="Data layer batch size")
    
    # External Services
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    
    # AWS Configuration (inherited from dashboard config)
    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_cognito_user_pool_id: Optional[str] = Field(default=None, description="AWS Cognito user pool ID")
    aws_cognito_client_id: Optional[str] = Field(default=None, description="AWS Cognito client ID")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests_per_minute: int = Field(default=100, description="Rate limit requests per minute")
    rate_limit_requests_per_hour: int = Field(default=1000, description="Rate limit requests per hour")
    
    # Monitoring and Alerting
    monitoring_enabled: bool = Field(default=True, description="Enable monitoring")
    alert_on_high_cpu_usage: bool = Field(default=True, description="Alert on high CPU usage")
    alert_on_high_memory_usage: bool = Field(default=True, description="Alert on high memory usage")
    alert_on_slow_queries: bool = Field(default=True, description="Alert on slow queries")
    slow_query_threshold_seconds: float = Field(default=5.0, description="Slow query threshold")
    
    # Data Quality
    data_validation_enabled: bool = Field(default=True, description="Enable data validation")
    data_sampling_enabled: bool = Field(default=False, description="Enable data sampling for large datasets")
    data_sampling_rate: float = Field(default=0.1, description="Data sampling rate (0.0 to 1.0)")
    
    # Feature Flags
    feature_trend_analysis: bool = Field(default=True, description="Enable trend analysis feature")
    feature_predictive_analytics: bool = Field(default=True, description="Enable predictive analytics feature")
    feature_custom_insights: bool = Field(default=True, description="Enable custom insights feature")
    feature_real_time_analytics: bool = Field(default=False, description="Enable real-time analytics feature")
    feature_advanced_filtering: bool = Field(default=True, description="Enable advanced filtering feature")
    feature_data_export: bool = Field(default=True, description="Enable data export feature")
    
    class Config:
        env_prefix = "ANALYTICS_"
        case_sensitive = False
        env_file = ".env"


class AnalyticsThresholds:
    """
    Analytics performance and quality thresholds
    """
    
    # Performance Thresholds
    MAX_QUERY_EXECUTION_TIME_MS = 5000  # 5 seconds
    MAX_EXPORT_GENERATION_TIME_MS = 30000  # 30 seconds
    MAX_CACHE_HIT_RATIO = 0.8  # 80%
    MIN_DATA_FRESHNESS_MINUTES = 5
    
    # Quality Thresholds
    MIN_CONFIDENCE_SCORE = 0.7  # 70%
    MAX_DATA_LOSS_PERCENTAGE = 0.05  # 5%
    MIN_TREND_SIGNIFICANCE_LEVEL = 0.95  # 95%
    
    # System Thresholds
    MAX_CPU_USAGE_PERCENTAGE = 80.0
    MAX_MEMORY_USAGE_PERCENTAGE = 85.0
    MAX_DISK_USAGE_PERCENTAGE = 90.0
    
    # Security Thresholds
    MAX_FAILED_AUTH_ATTEMPTS = 5
    MAX_EXPORT_REQUESTS_PER_HOUR = 10
    MAX_DATA_ACCESS_ATTEMPTS_PER_MINUTE = 100


class AnalyticsEndpoints:
    """
    Analytics endpoint configuration
    """
    
    # API Endpoints
    ANALYTICS_BASE_PATH = "/api/v1/dashboard/analytics"
    ANALYTICS_HEALTH_PATH = "/health"
    ANALYTICS_EXPORT_PATH = "/export"
    ANALYTICS_CONTEXT_PATH = "/context"
    ANALYTICS_PERMISSIONS_PATH = "/permissions"
    
    # Response Formats
    SUPPORTED_RESPONSE_FORMATS = ["json", "csv", "pdf", "excel"]
    DEFAULT_RESPONSE_FORMAT = "json"
    
    # Pagination
    DEFAULT_PAGE_SIZE = 100
    MAX_PAGE_SIZE = 1000
    MIN_PAGE_SIZE = 1


class AnalyticsDataSources:
    """
    Analytics data source configuration
    """
    
    # Data Sources
    DETECTION_PERFORMANCE_SOURCE = "detection_performance"
    USER_ENGAGEMENT_SOURCE = "user_engagement"
    SYSTEM_UTILIZATION_SOURCE = "system_utilization"
    BLOCKCHAIN_METRICS_SOURCE = "blockchain_metrics"
    
    # Data Refresh Intervals (seconds)
    DETECTION_PERFORMANCE_REFRESH = 300  # 5 minutes
    USER_ENGAGEMENT_REFRESH = 600  # 10 minutes
    SYSTEM_UTILIZATION_REFRESH = 60  # 1 minute
    BLOCKCHAIN_METRICS_REFRESH = 900  # 15 minutes
    
    # Data Retention Periods (days)
    DETECTION_PERFORMANCE_RETENTION = 90
    USER_ENGAGEMENT_RETENTION = 30
    SYSTEM_UTILIZATION_RETENTION = 7
    BLOCKCHAIN_METRICS_RETENTION = 365


class AnalyticsPermissions:
    """
    Analytics permissions configuration
    """
    
    # Permission Types
    READ_PERMISSION = "read"
    WRITE_PERMISSION = "write"
    EXPORT_PERMISSION = "export"
    ADMIN_PERMISSION = "admin"
    
    # Resource Types
    ANALYTICS_RESOURCE = "analytics"
    DETECTION_PERFORMANCE_RESOURCE = "detection_performance"
    USER_ENGAGEMENT_RESOURCE = "user_engagement"
    SYSTEM_UTILIZATION_RESOURCE = "system_utilization"
    BLOCKCHAIN_METRICS_RESOURCE = "blockchain_metrics"
    
    # Role Hierarchy (from highest to lowest privilege)
    ROLE_HIERARCHY = [
        "admin",
        "system_admin", 
        "analyst",
        "viewer"
    ]
    
    # Default Permissions for Unauthenticated Users
    UNAUTHENTICATED_PERMISSIONS = {
        "read": ["public"],
        "write": [],
        "export": ["public"],
        "admin": []
    }


# Global configuration instance
_analytics_config: Optional[AnalyticsConfig] = None


def get_analytics_config() -> AnalyticsConfig:
    """Get global analytics configuration instance"""
    global _analytics_config
    
    if _analytics_config is None:
        _analytics_config = AnalyticsConfig()
    
    return _analytics_config


def get_analytics_thresholds() -> AnalyticsThresholds:
    """Get analytics thresholds"""
    return AnalyticsThresholds()


def get_analytics_endpoints() -> AnalyticsEndpoints:
    """Get analytics endpoints configuration"""
    return AnalyticsEndpoints()


def get_analytics_data_sources() -> AnalyticsDataSources:
    """Get analytics data sources configuration"""
    return AnalyticsDataSources()


def get_analytics_permissions() -> AnalyticsPermissions:
    """Get analytics permissions configuration"""
    return AnalyticsPermissions()


# Environment-specific configurations
def get_development_config() -> Dict[str, Any]:
    """Get development-specific configuration"""
    return {
        "analytics_debug": True,
        "cache_enabled": False,
        "rate_limit_enabled": False,
        "monitoring_enabled": False,
        "data_validation_enabled": True,
        "feature_real_time_analytics": True
    }


def get_production_config() -> Dict[str, Any]:
    """Get production-specific configuration"""
    return {
        "analytics_debug": False,
        "cache_enabled": True,
        "rate_limit_enabled": True,
        "monitoring_enabled": True,
        "data_validation_enabled": True,
        "audit_logging_enabled": True,
        "privacy_compliance_enabled": True
    }


def get_testing_config() -> Dict[str, Any]:
    """Get testing-specific configuration"""
    return {
        "analytics_debug": True,
        "cache_enabled": False,
        "rate_limit_enabled": False,
        "monitoring_enabled": False,
        "data_validation_enabled": False,
        "feature_real_time_analytics": False,
        "max_analytics_records": 100
    }


def apply_environment_config(environment: str = "development") -> None:
    """
    Apply environment-specific configuration
    
    Args:
        environment: Environment name (development, production, testing)
    """
    global _analytics_config
    
    if environment == "production":
        config_overrides = get_production_config()
    elif environment == "testing":
        config_overrides = get_testing_config()
    else:  # development
        config_overrides = get_development_config()
    
    # Apply overrides
    if _analytics_config:
        for key, value in config_overrides.items():
            if hasattr(_analytics_config, key):
                setattr(_analytics_config, key, value)


# Configuration validation
def validate_analytics_config(config: AnalyticsConfig) -> bool:
    """
    Validate analytics configuration
    
    Args:
        config: Analytics configuration to validate
        
    Returns:
        True if configuration is valid, False otherwise
    """
    try:
        # Validate numeric ranges
        if config.max_analytics_records <= 0:
            return False
        
        if config.cache_ttl_seconds <= 0:
            return False
        
        if config.export_max_file_size_mb <= 0:
            return False
        
        if config.rate_limit_requests_per_minute <= 0:
            return False
        
        # Validate feature flags consistency
        if config.feature_predictive_analytics and not config.predictive_analytics_enabled:
            return False
        
        if config.feature_trend_analysis and not config.trend_analysis_enabled:
            return False
        
        # Validate export settings
        if config.export_enabled and not config.feature_data_export:
            return False
        
        return True
        
    except Exception:
        return False


# Configuration utilities
def get_config_summary() -> Dict[str, Any]:
    """Get configuration summary for monitoring"""
    config = get_analytics_config()
    
    return {
        "version": config.analytics_version,
        "enabled": config.analytics_enabled,
        "debug": config.analytics_debug,
        "cache_enabled": config.cache_enabled,
        "cache_strategy": config.cache_strategy.value,
        "export_enabled": config.export_enabled,
        "export_strategy": config.export_strategy.value,
        "rate_limit_enabled": config.rate_limit_enabled,
        "monitoring_enabled": config.monitoring_enabled,
        "features": {
            "trend_analysis": config.feature_trend_analysis,
            "predictive_analytics": config.feature_predictive_analytics,
            "custom_insights": config.feature_custom_insights,
            "real_time_analytics": config.feature_real_time_analytics,
            "advanced_filtering": config.feature_advanced_filtering,
            "data_export": config.feature_data_export
        }
    }
