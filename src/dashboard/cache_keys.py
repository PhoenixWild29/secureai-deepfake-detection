#!/usr/bin/env python3
"""
Dashboard Cache Key Generation Module
Standardized Redis cache key generation for dashboard widgets, user preferences, and aggregated analytics data
"""

import hashlib
from typing import Optional, Dict, Any, Union, List
from uuid import UUID
from datetime import datetime, timezone
from enum import Enum


class DashboardCacheType(str, Enum):
    """Enumeration of dashboard cache types"""
    OVERVIEW = "overview"
    ANALYTICS = "analytics"
    USER_PREFERENCES = "user_preferences"
    WIDGET_DATA = "widget_data"
    SYSTEM_STATUS = "system_status"
    PERFORMANCE_METRICS = "performance_metrics"
    RECENT_ACTIVITY = "recent_activity"
    NOTIFICATIONS = "notifications"
    AGGREGATED_ANALYTICS = "aggregated_analytics"


class WidgetType(str, Enum):
    """Enumeration of dashboard widget types"""
    OVERVIEW_STATS = "overview_stats"
    ANALYTICS_CHART = "analytics_chart"
    RECENT_ACTIVITY_FEED = "recent_activity_feed"
    SYSTEM_STATUS_PANEL = "system_status_panel"
    PERFORMANCE_METRICS = "performance_metrics"
    CONFIDENCE_DISTRIBUTION = "confidence_distribution"
    PROCESSING_TRENDS = "processing_trends"
    USER_STATISTICS = "user_statistics"


# Cache key prefixes for different dashboard data types
DASHBOARD_CACHE_PREFIXES = {
    'dashboard': 'dash',
    'user': 'user',
    'analytics': 'analytics',
    'system': 'system',
    'widget': 'widget',
    'metrics': 'metrics',
    'preferences': 'prefs',
    'notifications': 'notif',
    'performance': 'perf',
    'activity': 'activity'
}


def generate_dashboard_cache_key(
    cache_type: DashboardCacheType,
    user_id: Optional[Union[str, UUID]] = None,
    widget_type: Optional[WidgetType] = None,
    period: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    **kwargs
) -> str:
    """
    Generate standardized Redis cache key for dashboard data.
    
    Args:
        cache_type: Type of dashboard cache
        user_id: User identifier (required for user-specific data)
        widget_type: Widget type (for widget-specific caching)
        period: Time period for analytics data (e.g., '30d', '7d', '1h')
        filters: Additional filters for cache key differentiation
        **kwargs: Additional parameters for cache key generation
        
    Returns:
        str: Formatted Redis cache key
        
    Examples:
        >>> generate_dashboard_cache_key(DashboardCacheType.OVERVIEW, user_id="123")
        "dash:overview:user:123"
        
        >>> generate_dashboard_cache_key(DashboardCacheType.ANALYTICS, period="30d", filters={"type": "confidence"})
        "dash:analytics:30d:hash:a1b2c3d4"
    """
    prefix = DASHBOARD_CACHE_PREFIXES['dashboard']
    key_parts = [prefix, cache_type.value]
    
    # Add user-specific identifier if provided
    if user_id is not None:
        key_parts.extend(['user', str(user_id)])
    
    # Add widget type if provided
    if widget_type is not None:
        key_parts.append(widget_type.value)
    
    # Add time period if provided
    if period is not None:
        key_parts.append(period)
    
    # Add filters hash if provided
    if filters:
        # Create deterministic hash from sorted filters
        filters_str = str(sorted(filters.items()))
        filters_hash = hashlib.md5(filters_str.encode()).hexdigest()[:8]
        key_parts.append(f"filters:{filters_hash}")
    
    # Add additional parameters
    if kwargs:
        # Sort kwargs for deterministic key generation
        sorted_kwargs = sorted(kwargs.items())
        kwargs_str = str(sorted_kwargs)
        kwargs_hash = hashlib.md5(kwargs_str.encode()).hexdigest()[:8]
        key_parts.append(f"params:{kwargs_hash}")
    
    # Join parts with colons
    cache_key = ':'.join(key_parts)
    
    # Ensure key length is within Redis limits (512MB, but we'll limit to 250 chars for performance)
    if len(cache_key) > 250:
        # Create hash of long keys
        key_hash = hashlib.md5(cache_key.encode()).hexdigest()[:16]
        cache_key = f"{prefix}:hash:{key_hash}"
    
    return cache_key


def get_dashboard_overview_cache_key(user_id: Union[str, UUID]) -> str:
    """
    Generate cache key for dashboard overview data.
    
    Args:
        user_id: User identifier
        
    Returns:
        str: Cache key for dashboard overview
    """
    return generate_dashboard_cache_key(
        cache_type=DashboardCacheType.OVERVIEW,
        user_id=user_id
    )


def get_dashboard_analytics_cache_key(
    user_id: Optional[Union[str, UUID]] = None,
    period: str = "30d",
    filters: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate cache key for dashboard analytics data.
    
    Args:
        user_id: User identifier (optional for global analytics)
        period: Time period for analytics
        filters: Analytics filters
        
    Returns:
        str: Cache key for dashboard analytics
    """
    return generate_dashboard_cache_key(
        cache_type=DashboardCacheType.ANALYTICS,
        user_id=user_id,
        period=period,
        filters=filters
    )


def get_user_preferences_cache_key(user_id: Union[str, UUID]) -> str:
    """
    Generate cache key for user dashboard preferences.
    
    Args:
        user_id: User identifier
        
    Returns:
        str: Cache key for user preferences
    """
    return generate_dashboard_cache_key(
        cache_type=DashboardCacheType.USER_PREFERENCES,
        user_id=user_id
    )


def get_widget_data_cache_key(
    user_id: Union[str, UUID],
    widget_type: WidgetType,
    **kwargs
) -> str:
    """
    Generate cache key for specific dashboard widget data.
    
    Args:
        user_id: User identifier
        widget_type: Type of widget
        **kwargs: Additional widget parameters
        
    Returns:
        str: Cache key for widget data
    """
    return generate_dashboard_cache_key(
        cache_type=DashboardCacheType.WIDGET_DATA,
        user_id=user_id,
        widget_type=widget_type,
        **kwargs
    )


def get_system_status_cache_key(component: Optional[str] = None) -> str:
    """
    Generate cache key for system status data.
    
    Args:
        component: Specific system component (optional)
        
    Returns:
        str: Cache key for system status
    """
    return generate_dashboard_cache_key(
        cache_type=DashboardCacheType.SYSTEM_STATUS,
        component=component
    )


def get_performance_metrics_cache_key(
    user_id: Optional[Union[str, UUID]] = None,
    period: str = "1h"
) -> str:
    """
    Generate cache key for performance metrics data.
    
    Args:
        user_id: User identifier (optional for global metrics)
        period: Time period for metrics
        
    Returns:
        str: Cache key for performance metrics
    """
    return generate_dashboard_cache_key(
        cache_type=DashboardCacheType.PERFORMANCE_METRICS,
        user_id=user_id,
        period=period
    )


def get_recent_activity_cache_key(user_id: Union[str, UUID], limit: int = 10) -> str:
    """
    Generate cache key for recent activity data.
    
    Args:
        user_id: User identifier
        limit: Number of recent activities
        
    Returns:
        str: Cache key for recent activity
    """
    return generate_dashboard_cache_key(
        cache_type=DashboardCacheType.RECENT_ACTIVITY,
        user_id=user_id,
        limit=limit
    )


def get_notifications_cache_key(user_id: Union[str, UUID]) -> str:
    """
    Generate cache key for user notifications.
    
    Args:
        user_id: User identifier
        
    Returns:
        str: Cache key for notifications
    """
    return generate_dashboard_cache_key(
        cache_type=DashboardCacheType.NOTIFICATIONS,
        user_id=user_id
    )


def get_aggregated_analytics_cache_key(
    period: str = "30d",
    aggregation_type: str = "daily",
    filters: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate cache key for aggregated analytics data.
    
    Args:
        period: Time period for aggregation
        aggregation_type: Type of aggregation (daily, hourly, weekly)
        filters: Additional filters
        
    Returns:
        str: Cache key for aggregated analytics
    """
    return generate_dashboard_cache_key(
        cache_type=DashboardCacheType.AGGREGATED_ANALYTICS,
        period=period,
        aggregation_type=aggregation_type,
        filters=filters
    )


def parse_dashboard_cache_key(cache_key: str) -> Dict[str, Any]:
    """
    Parse dashboard cache key to extract components.
    
    Args:
        cache_key: Redis cache key
        
    Returns:
        Dict[str, Any]: Parsed components of the cache key
        
    Raises:
        ValueError: If cache key format is invalid
    """
    if not cache_key or not isinstance(cache_key, str):
        raise ValueError("cache_key must be a non-empty string")
    
    parts = cache_key.split(":")
    
    if len(parts) < 2:
        raise ValueError("Invalid cache key format")
    
    prefix = parts[0]
    if prefix != DASHBOARD_CACHE_PREFIXES['dashboard']:
        raise ValueError(f"Invalid dashboard cache key prefix: {prefix}")
    
    result = {
        "prefix": prefix,
        "cache_type": parts[1] if len(parts) > 1 else None,
        "user_id": None,
        "widget_type": None,
        "period": None,
        "filters": None,
        "additional_params": {}
    }
    
    # Parse remaining parts
    i = 2
    while i < len(parts):
        part = parts[i]
        
        if part == "user" and i + 1 < len(parts):
            result["user_id"] = parts[i + 1]
            i += 2
        elif part == "filters" and i + 1 < len(parts):
            result["filters"] = parts[i + 1]
            i += 2
        elif part == "params" and i + 1 < len(parts):
            result["additional_params"]["params_hash"] = parts[i + 1]
            i += 2
        elif part in [wt.value for wt in WidgetType]:
            result["widget_type"] = part
            i += 1
        elif part in ["30d", "7d", "1d", "1h", "1w", "1y"]:
            result["period"] = part
            i += 1
        else:
            # Additional parameter
            result["additional_params"][f"param_{i}"] = part
            i += 1
    
    return result


def get_cache_key_pattern(
    cache_type: Optional[DashboardCacheType] = None,
    user_id: Optional[Union[str, UUID]] = None,
    widget_type: Optional[WidgetType] = None
) -> str:
    """
    Generate Redis pattern for cache key matching (for invalidation).
    
    Args:
        cache_type: Cache type to match (None for all types)
        user_id: User ID to match (None for all users)
        widget_type: Widget type to match (None for all widgets)
        
    Returns:
        str: Redis pattern for key matching
    """
    prefix = DASHBOARD_CACHE_PREFIXES['dashboard']
    pattern_parts = [prefix]
    
    if cache_type:
        pattern_parts.append(cache_type.value)
    else:
        pattern_parts.append("*")
    
    if user_id:
        pattern_parts.extend(["user", str(user_id)])
    else:
        pattern_parts.extend(["user", "*"])
    
    if widget_type:
        pattern_parts.append(widget_type.value)
    else:
        pattern_parts.append("*")
    
    return ":".join(pattern_parts)


def get_user_cache_pattern(user_id: Union[str, UUID]) -> str:
    """
    Generate Redis pattern for all user-specific dashboard cache keys.
    
    Args:
        user_id: User identifier
        
    Returns:
        str: Redis pattern for user cache keys
    """
    return f"{DASHBOARD_CACHE_PREFIXES['dashboard']}:*:user:{user_id}:*"


def get_analytics_cache_pattern(period: Optional[str] = None) -> str:
    """
    Generate Redis pattern for analytics cache keys.
    
    Args:
        period: Time period to match (None for all periods)
        
    Returns:
        str: Redis pattern for analytics cache keys
    """
    if period:
        return f"{DASHBOARD_CACHE_PREFIXES['dashboard']}:analytics:*:{period}:*"
    else:
        return f"{DASHBOARD_CACHE_PREFIXES['dashboard']}:analytics:*"


def get_widget_cache_pattern(widget_type: Optional[WidgetType] = None) -> str:
    """
    Generate Redis pattern for widget cache keys.
    
    Args:
        widget_type: Widget type to match (None for all widgets)
        
    Returns:
        str: Redis pattern for widget cache keys
    """
    if widget_type:
        return f"{DASHBOARD_CACHE_PREFIXES['dashboard']}:widget_data:*:{widget_type.value}:*"
    else:
        return f"{DASHBOARD_CACHE_PREFIXES['dashboard']}:widget_data:*"


def validate_cache_key_format(cache_key: str) -> bool:
    """
    Validate dashboard cache key format.
    
    Args:
        cache_key: Cache key to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        parse_dashboard_cache_key(cache_key)
        return True
    except ValueError:
        return False


def get_cache_key_metadata(cache_key: str) -> Dict[str, Any]:
    """
    Get metadata about a dashboard cache key.
    
    Args:
        cache_key: Cache key to analyze
        
    Returns:
        Dict[str, Any]: Metadata about the cache key
    """
    try:
        parsed = parse_dashboard_cache_key(cache_key)
        
        return {
            "is_valid": True,
            "key_length": len(cache_key),
            "parts_count": len(cache_key.split(":")),
            "cache_type": parsed["cache_type"],
            "is_user_specific": parsed["user_id"] is not None,
            "has_filters": parsed["filters"] is not None,
            "has_widget_type": parsed["widget_type"] is not None,
            "has_period": parsed["period"] is not None,
            "parsed_components": parsed
        }
    except ValueError:
        return {
            "is_valid": False,
            "key_length": len(cache_key),
            "error": "Invalid cache key format"
        }


# Utility functions for common cache operations
def create_cache_key_batch(
    cache_type: DashboardCacheType,
    user_ids: List[Union[str, UUID]],
    **kwargs
) -> List[str]:
    """
    Create batch of cache keys for multiple users.
    
    Args:
        cache_type: Type of cache
        user_ids: List of user identifiers
        **kwargs: Additional parameters
        
    Returns:
        List[str]: List of cache keys
    """
    return [
        generate_dashboard_cache_key(cache_type, user_id=user_id, **kwargs)
        for user_id in user_ids
    ]


def get_cache_key_ttl(cache_type: DashboardCacheType) -> int:
    """
    Get recommended TTL for dashboard cache type.
    
    Args:
        cache_type: Type of dashboard cache
        
    Returns:
        int: TTL in seconds
    """
    ttl_map = {
        DashboardCacheType.OVERVIEW: 300,           # 5 minutes
        DashboardCacheType.ANALYTICS: 600,           # 10 minutes
        DashboardCacheType.USER_PREFERENCES: 1800,   # 30 minutes
        DashboardCacheType.WIDGET_DATA: 300,         # 5 minutes
        DashboardCacheType.SYSTEM_STATUS: 60,       # 1 minute
        DashboardCacheType.PERFORMANCE_METRICS: 300, # 5 minutes
        DashboardCacheType.RECENT_ACTIVITY: 120,    # 2 minutes
        DashboardCacheType.NOTIFICATIONS: 600,      # 10 minutes
        DashboardCacheType.AGGREGATED_ANALYTICS: 900 # 15 minutes
    }
    
    return ttl_map.get(cache_type, 300)  # Default 5 minutes
