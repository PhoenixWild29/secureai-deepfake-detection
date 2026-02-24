#!/usr/bin/env python3
"""
Dashboard Services Module
Cache-aside pattern implementation for dashboard data retrieval with sub-100ms response times
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Union
from uuid import UUID
from datetime import datetime, timezone, timedelta
from functools import wraps

# Import existing cache manager and dashboard models
from src.data_layer.cache_manager import cache_manager, cached
from src.api.schemas.dashboard_models import (
    DashboardOverviewResponse,
    DashboardAnalyticsResponse,
    UserPreferencesRequest,
    DashboardConfigurationResponse
)
from src.dashboard.cache_keys import (
    DashboardCacheType,
    WidgetType,
    DASHBOARD_CACHE_PREFIXES,
    get_dashboard_overview_cache_key,
    get_dashboard_analytics_cache_key,
    get_user_preferences_cache_key,
    get_widget_data_cache_key,
    get_system_status_cache_key,
    get_performance_metrics_cache_key,
    get_recent_activity_cache_key,
    get_notifications_cache_key,
    get_aggregated_analytics_cache_key,
    get_cache_key_ttl
)

# Configure logging
logger = logging.getLogger(__name__)


class DashboardDataService:
    """
    Dashboard data service with cache-aside pattern implementation.
    Provides sub-100ms response times for dashboard interactions.
    """
    
    def __init__(self):
        self.cache_manager = cache_manager
        self._data_layer = None  # Will be injected or initialized
    
    def set_data_layer(self, data_layer):
        """Set the data layer for database operations"""
        self._data_layer = data_layer
    
    async def get_dashboard_overview(
        self,
        user_id: Union[str, UUID],
        force_refresh: bool = False
    ) -> DashboardOverviewResponse:
        """
        Get dashboard overview data with caching.
        
        Args:
            user_id: User identifier
            force_refresh: Force refresh from database
            
        Returns:
            DashboardOverviewResponse: Dashboard overview data
        """
        cache_key = get_dashboard_overview_cache_key(user_id)
        
        # Try cache first unless force refresh
        if not force_refresh:
            cached_data = await self.cache_manager.get_from_cache_async(
                cache_key, 
                data_type='dashboard_overview'
            )
            if cached_data is not None:
                logger.debug(f"Cache hit for dashboard overview: {user_id}")
                return DashboardOverviewResponse(**cached_data)
        
        # Cache miss or force refresh - get from database
        logger.debug(f"Cache miss for dashboard overview: {user_id}")
        overview_data = await self._fetch_dashboard_overview_from_db(user_id)
        
        # Store in cache
        await self.cache_manager.set_to_cache_async(
            cache_key,
            overview_data.dict(),
            ttl=get_cache_key_ttl(DashboardCacheType.OVERVIEW),
            data_type='dashboard_overview'
        )
        
        return overview_data
    
    async def get_dashboard_analytics(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        period: str = "30d",
        filters: Optional[Dict[str, Any]] = None,
        force_refresh: bool = False
    ) -> DashboardAnalyticsResponse:
        """
        Get dashboard analytics data with caching.
        
        Args:
            user_id: User identifier (optional for global analytics)
            period: Time period for analytics
            filters: Analytics filters
            force_refresh: Force refresh from database
            
        Returns:
            DashboardAnalyticsResponse: Dashboard analytics data
        """
        cache_key = get_dashboard_analytics_cache_key(user_id, period, filters)
        
        # Try cache first unless force refresh
        if not force_refresh:
            cached_data = await self.cache_manager.get_from_cache_async(
                cache_key,
                data_type='dashboard_analytics'
            )
            if cached_data is not None:
                logger.debug(f"Cache hit for dashboard analytics: {user_id}, {period}")
                return DashboardAnalyticsResponse(**cached_data)
        
        # Cache miss or force refresh - get from database
        logger.debug(f"Cache miss for dashboard analytics: {user_id}, {period}")
        analytics_data = await self._fetch_dashboard_analytics_from_db(user_id, period, filters)
        
        # Store in cache
        await self.cache_manager.set_to_cache_async(
            cache_key,
            analytics_data.dict(),
            ttl=get_cache_key_ttl(DashboardCacheType.ANALYTICS),
            data_type='dashboard_analytics'
        )
        
        return analytics_data
    
    async def get_user_preferences(
        self,
        user_id: Union[str, UUID],
        force_refresh: bool = False
    ) -> UserPreferencesRequest:
        """
        Get user dashboard preferences with caching.
        
        Args:
            user_id: User identifier
            force_refresh: Force refresh from database
            
        Returns:
            UserPreferencesRequest: User preferences data
        """
        cache_key = get_user_preferences_cache_key(user_id)
        
        # Try cache first unless force refresh
        if not force_refresh:
            cached_data = await self.cache_manager.get_from_cache_async(
                cache_key,
                data_type='user_preferences'
            )
            if cached_data is not None:
                logger.debug(f"Cache hit for user preferences: {user_id}")
                return UserPreferencesRequest(**cached_data)
        
        # Cache miss or force refresh - get from database
        logger.debug(f"Cache miss for user preferences: {user_id}")
        preferences_data = await self._fetch_user_preferences_from_db(user_id)
        
        # Store in cache
        await self.cache_manager.set_to_cache_async(
            cache_key,
            preferences_data.dict(),
            ttl=get_cache_key_ttl(DashboardCacheType.USER_PREFERENCES),
            data_type='user_preferences'
        )
        
        return preferences_data
    
    async def get_widget_data(
        self,
        user_id: Union[str, UUID],
        widget_type: WidgetType,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get specific widget data with caching.
        
        Args:
            user_id: User identifier
            widget_type: Type of widget
            **kwargs: Additional widget parameters
            
        Returns:
            Dict[str, Any]: Widget data
        """
        cache_key = get_widget_data_cache_key(user_id, widget_type, **kwargs)
        
        # Try cache first
        cached_data = await self.cache_manager.get_from_cache_async(
            cache_key,
            data_type='widget_data'
        )
        if cached_data is not None:
            logger.debug(f"Cache hit for widget data: {user_id}, {widget_type}")
            return cached_data
        
        # Cache miss - get from database
        logger.debug(f"Cache miss for widget data: {user_id}, {widget_type}")
        widget_data = await self._fetch_widget_data_from_db(user_id, widget_type, **kwargs)
        
        # Store in cache
        await self.cache_manager.set_to_cache_async(
            cache_key,
            widget_data,
            ttl=get_cache_key_ttl(DashboardCacheType.WIDGET_DATA),
            data_type='widget_data'
        )
        
        return widget_data
    
    async def get_system_status(self, component: Optional[str] = None) -> Dict[str, Any]:
        """
        Get system status data with caching.
        
        Args:
            component: Specific system component
            
        Returns:
            Dict[str, Any]: System status data
        """
        cache_key = get_system_status_cache_key(component)
        
        # Try cache first
        cached_data = await self.cache_manager.get_from_cache_async(
            cache_key,
            data_type='system_status'
        )
        if cached_data is not None:
            logger.debug(f"Cache hit for system status: {component}")
            return cached_data
        
        # Cache miss - get from database
        logger.debug(f"Cache miss for system status: {component}")
        status_data = await self._fetch_system_status_from_db(component)
        
        # Store in cache
        await self.cache_manager.set_to_cache_async(
            cache_key,
            status_data,
            ttl=get_cache_key_ttl(DashboardCacheType.SYSTEM_STATUS),
            data_type='system_status'
        )
        
        return status_data
    
    async def get_performance_metrics(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        period: str = "1h"
    ) -> Dict[str, Any]:
        """
        Get performance metrics data with caching.
        
        Args:
            user_id: User identifier (optional for global metrics)
            period: Time period for metrics
            
        Returns:
            Dict[str, Any]: Performance metrics data
        """
        cache_key = get_performance_metrics_cache_key(user_id, period)
        
        # Try cache first
        cached_data = await self.cache_manager.get_from_cache_async(
            cache_key,
            data_type='performance_metrics'
        )
        if cached_data is not None:
            logger.debug(f"Cache hit for performance metrics: {user_id}, {period}")
            return cached_data
        
        # Cache miss - get from database
        logger.debug(f"Cache miss for performance metrics: {user_id}, {period}")
        metrics_data = await self._fetch_performance_metrics_from_db(user_id, period)
        
        # Store in cache
        await self.cache_manager.set_to_cache_async(
            cache_key,
            metrics_data,
            ttl=get_cache_key_ttl(DashboardCacheType.PERFORMANCE_METRICS),
            data_type='performance_metrics'
        )
        
        return metrics_data
    
    async def get_recent_activity(
        self,
        user_id: Union[str, UUID],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent activity data with caching.
        
        Args:
            user_id: User identifier
            limit: Number of recent activities
            
        Returns:
            List[Dict[str, Any]]: Recent activity data
        """
        cache_key = get_recent_activity_cache_key(user_id, limit)
        
        # Try cache first
        cached_data = await self.cache_manager.get_from_cache_async(
            cache_key,
            data_type='recent_activity'
        )
        if cached_data is not None:
            logger.debug(f"Cache hit for recent activity: {user_id}")
            return cached_data
        
        # Cache miss - get from database
        logger.debug(f"Cache miss for recent activity: {user_id}")
        activity_data = await self._fetch_recent_activity_from_db(user_id, limit)
        
        # Store in cache
        await self.cache_manager.set_to_cache_async(
            cache_key,
            activity_data,
            ttl=get_cache_key_ttl(DashboardCacheType.RECENT_ACTIVITY),
            data_type='recent_activity'
        )
        
        return activity_data
    
    async def get_notifications(
        self,
        user_id: Union[str, UUID]
    ) -> List[Dict[str, Any]]:
        """
        Get user notifications with caching.
        
        Args:
            user_id: User identifier
            
        Returns:
            List[Dict[str, Any]]: Notifications data
        """
        cache_key = get_notifications_cache_key(user_id)
        
        # Try cache first
        cached_data = await self.cache_manager.get_from_cache_async(
            cache_key,
            data_type='notifications'
        )
        if cached_data is not None:
            logger.debug(f"Cache hit for notifications: {user_id}")
            return cached_data
        
        # Cache miss - get from database
        logger.debug(f"Cache miss for notifications: {user_id}")
        notifications_data = await self._fetch_notifications_from_db(user_id)
        
        # Store in cache
        await self.cache_manager.set_to_cache_async(
            cache_key,
            notifications_data,
            ttl=get_cache_key_ttl(DashboardCacheType.NOTIFICATIONS),
            data_type='notifications'
        )
        
        return notifications_data
    
    async def get_aggregated_analytics(
        self,
        period: str = "30d",
        aggregation_type: str = "daily",
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated analytics data with caching.
        
        Args:
            period: Time period for aggregation
            aggregation_type: Type of aggregation
            filters: Additional filters
            
        Returns:
            Dict[str, Any]: Aggregated analytics data
        """
        cache_key = get_aggregated_analytics_cache_key(period, aggregation_type, filters)
        
        # Try cache first
        cached_data = await self.cache_manager.get_from_cache_async(
            cache_key,
            data_type='aggregated_analytics'
        )
        if cached_data is not None:
            logger.debug(f"Cache hit for aggregated analytics: {period}, {aggregation_type}")
            return cached_data
        
        # Cache miss - get from database
        logger.debug(f"Cache miss for aggregated analytics: {period}, {aggregation_type}")
        analytics_data = await self._fetch_aggregated_analytics_from_db(period, aggregation_type, filters)
        
        # Store in cache
        await self.cache_manager.set_to_cache_async(
            cache_key,
            analytics_data,
            ttl=get_cache_key_ttl(DashboardCacheType.AGGREGATED_ANALYTICS),
            data_type='aggregated_analytics'
        )
        
        return analytics_data
    
    # Database fetch methods (to be implemented with actual data layer)
    async def _fetch_dashboard_overview_from_db(
        self,
        user_id: Union[str, UUID]
    ) -> DashboardOverviewResponse:
        """Fetch dashboard overview data from database"""
        # This would integrate with the actual data layer
        # For now, return mock data structure
        return DashboardOverviewResponse(
            user_summary={
                "total_analyses": 0,
                "success_rate": 100.0,
                "account_type": "free",
                "last_analysis": None
            },
            recent_analyses=[],
            system_status={
                "overall_status": "healthy",
                "services": {
                    "detection_engine": "healthy",
                    "blockchain": "healthy",
                    "storage": "healthy"
                }
            },
            quick_stats={
                "total_detections": 0,
                "processing_time_avg": 0.0,
                "accuracy_rate": 100.0
            },
            notifications=[],
            preferences={}
        )
    
    async def _fetch_dashboard_analytics_from_db(
        self,
        user_id: Optional[Union[str, UUID]],
        period: str,
        filters: Optional[Dict[str, Any]]
    ) -> DashboardAnalyticsResponse:
        """Fetch dashboard analytics data from database"""
        # This would integrate with the actual data layer
        return DashboardAnalyticsResponse(
            performance_trends={
                "processing_time_trend": {
                    "data_points": []
                },
                "accuracy_trend": {
                    "data_points": []
                }
            },
            usage_metrics={
                "total_users": 0,
                "active_users": 0,
                "analyses_count": 0
            },
            confidence_distribution={
                "bins": {},
                "statistics": {
                    "mean": 0.0,
                    "median": 0.0,
                    "std_dev": 0.0
                }
            },
            processing_metrics={
                "average_processing_time": 0.0,
                "throughput": 0.0,
                "success_rate": 100.0
            },
            analytics_period=period
        )
    
    async def _fetch_user_preferences_from_db(
        self,
        user_id: Union[str, UUID]
    ) -> UserPreferencesRequest:
        """Fetch user preferences from database"""
        return UserPreferencesRequest(
            layout_config={},
            notification_settings={},
            theme_preferences={},
            analytics_filters={},
            user_id=UUID(str(user_id)) if isinstance(user_id, str) else user_id
        )
    
    async def _fetch_widget_data_from_db(
        self,
        user_id: Union[str, UUID],
        widget_type: WidgetType,
        **kwargs
    ) -> Dict[str, Any]:
        """Fetch widget data from database"""
        # This would integrate with the actual data layer based on widget type
        return {
            "widget_type": widget_type.value,
            "data": {},
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    async def _fetch_system_status_from_db(
        self,
        component: Optional[str]
    ) -> Dict[str, Any]:
        """Fetch system status from database"""
        return {
            "overall_status": "healthy",
            "components": {
                component or "all": "healthy"
            },
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    async def _fetch_performance_metrics_from_db(
        self,
        user_id: Optional[Union[str, UUID]],
        period: str
    ) -> Dict[str, Any]:
        """Fetch performance metrics from database"""
        return {
            "period": period,
            "metrics": {
                "avg_response_time": 0.0,
                "cache_hit_rate": 0.0,
                "throughput": 0.0
            },
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    async def _fetch_recent_activity_from_db(
        self,
        user_id: Union[str, UUID],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Fetch recent activity from database"""
        return []
    
    async def _fetch_notifications_from_db(
        self,
        user_id: Union[str, UUID]
    ) -> List[Dict[str, Any]]:
        """Fetch notifications from database"""
        return []
    
    async def _fetch_aggregated_analytics_from_db(
        self,
        period: str,
        aggregation_type: str,
        filters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Fetch aggregated analytics from database"""
        return {
            "period": period,
            "aggregation_type": aggregation_type,
            "data": {},
            "last_updated": datetime.now(timezone.utc).isoformat()
        }


# Decorator for cache-aside pattern
def dashboard_cached(
    cache_type: DashboardCacheType,
    ttl: Optional[int] = None,
    key_prefix: str = 'dashboard'
):
    """
    Decorator for implementing cache-aside pattern for dashboard data.
    
    Args:
        cache_type: Type of dashboard cache
        ttl: Time to live in seconds (overrides cache type default)
        key_prefix: Prefix for cache key generation
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = cache_manager._generate_cache_key(*key_parts)
            
            # Try to get from cache
            cached_result = await cache_manager.get_from_cache_async(
                cache_key, 
                data_type=cache_type.value
            )
            if cached_result is not None:
                return cached_result
            
            # Execute function if not in cache
            result = await func(*args, **kwargs)
            
            # Store result in cache
            cache_ttl = ttl or get_cache_key_ttl(cache_type)
            await cache_manager.set_to_cache_async(
                cache_key, 
                result, 
                ttl=cache_ttl, 
                data_type=cache_type.value
            )
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = cache_manager._generate_cache_key(*key_parts)
            
            # Try to get from cache
            cached_result = cache_manager.get_from_cache(
                cache_key, 
                data_type=cache_type.value
            )
            if cached_result is not None:
                return cached_result
            
            # Execute function if not in cache
            result = func(*args, **kwargs)
            
            # Store result in cache
            cache_ttl = ttl or get_cache_key_ttl(cache_type)
            cache_manager.set_to_cache(
                cache_key, 
                result, 
                ttl=cache_ttl, 
                data_type=cache_type.value
            )
            
            return result
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Global dashboard service instance
dashboard_service = DashboardDataService()


# Utility functions for dashboard caching
async def warm_dashboard_cache(
    user_id: Union[str, UUID],
    cache_types: Optional[List[DashboardCacheType]] = None
) -> Dict[str, bool]:
    """
    Warm dashboard cache for a user.
    
    Args:
        user_id: User identifier
        cache_types: Types of cache to warm (None for all types)
        
    Returns:
        Dict[str, bool]: Results of cache warming operations
    """
    if cache_types is None:
        cache_types = [
            DashboardCacheType.OVERVIEW,
            DashboardCacheType.ANALYTICS,
            DashboardCacheType.USER_PREFERENCES,
            DashboardCacheType.RECENT_ACTIVITY,
            DashboardCacheType.NOTIFICATIONS
        ]
    
    results = {}
    
    for cache_type in cache_types:
        try:
            if cache_type == DashboardCacheType.OVERVIEW:
                await dashboard_service.get_dashboard_overview(user_id)
            elif cache_type == DashboardCacheType.ANALYTICS:
                await dashboard_service.get_dashboard_analytics(user_id)
            elif cache_type == DashboardCacheType.USER_PREFERENCES:
                await dashboard_service.get_user_preferences(user_id)
            elif cache_type == DashboardCacheType.RECENT_ACTIVITY:
                await dashboard_service.get_recent_activity(user_id)
            elif cache_type == DashboardCacheType.NOTIFICATIONS:
                await dashboard_service.get_notifications(user_id)
            
            results[cache_type.value] = True
            logger.info(f"Successfully warmed cache for {cache_type.value}: {user_id}")
            
        except Exception as e:
            results[cache_type.value] = False
            logger.error(f"Failed to warm cache for {cache_type.value}: {user_id}, error: {e}")
    
    return results


async def invalidate_user_dashboard_cache(user_id: Union[str, UUID]) -> bool:
    """
    Invalidate all dashboard cache for a user.
    
    Args:
        user_id: User identifier
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get user cache pattern
        from src.dashboard.cache_keys import get_user_cache_pattern
        pattern = get_user_cache_pattern(user_id)
        
        # Invalidate all matching keys
        invalidated_count = await cache_manager.invalidate_pattern_async(pattern)
        
        logger.info(f"Invalidated {invalidated_count} cache keys for user: {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to invalidate user cache: {user_id}, error: {e}")
        return False


async def get_dashboard_cache_stats() -> Dict[str, Any]:
    """
    Get dashboard cache statistics.
    
    Returns:
        Dict[str, Any]: Cache statistics
    """
    try:
        cache_metrics = cache_manager.get_cache_metrics()
        
        return {
            "cache_metrics": cache_metrics,
            "dashboard_specific": {
                "cache_types": len(DashboardCacheType),
                "widget_types": len(WidgetType),
                "supported_periods": ["1h", "1d", "7d", "30d", "90d", "1y"],
                "cache_prefixes": len(DASHBOARD_CACHE_PREFIXES)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboard cache stats: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
