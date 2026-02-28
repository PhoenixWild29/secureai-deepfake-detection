#!/usr/bin/env python3
"""
Dashboard Models with Caching Integration
Extended dashboard models with Redis caching methods for sub-100ms response times
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Union
from uuid import UUID
from datetime import datetime, timezone

# Import existing dashboard models
from src.api.schemas.dashboard_models import (
    DashboardOverviewResponse,
    DashboardAnalyticsResponse,
    UserPreferencesRequest,
    DashboardConfigurationResponse
)

# Import cache manager and cache keys
from src.data_layer.cache_manager import cache_manager
from src.dashboard.cache_keys import (
    DashboardCacheType,
    get_dashboard_overview_cache_key,
    get_dashboard_analytics_cache_key,
    get_user_preferences_cache_key,
    get_cache_key_ttl
)

# Configure logging
logger = logging.getLogger(__name__)


class CachedDashboardOverviewResponse(DashboardOverviewResponse):
    """
    Extended DashboardOverviewResponse with caching methods.
    Integrates seamlessly with existing Redis infrastructure.
    """
    
    async def cache_data(self, user_id: Union[str, UUID]) -> bool:
        """
        Cache the dashboard overview data.
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if cached successfully, False otherwise
        """
        try:
            cache_key = get_dashboard_overview_cache_key(user_id)
            
            success = await cache_manager.set_to_cache_async(
                cache_key,
                self.dict(),
                ttl=get_cache_key_ttl(DashboardCacheType.OVERVIEW),
                data_type='dashboard_overview'
            )
            
            if success:
                logger.debug(f"Cached dashboard overview for user: {user_id}")
            else:
                logger.warning(f"Failed to cache dashboard overview for user: {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching dashboard overview for user {user_id}: {e}")
            return False
    
    @classmethod
    async def from_cache(
        cls,
        user_id: Union[str, UUID],
        force_refresh: bool = False
    ) -> Optional['CachedDashboardOverviewResponse']:
        """
        Load dashboard overview data from cache.
        
        Args:
            user_id: User identifier
            force_refresh: Force refresh from database
            
        Returns:
            CachedDashboardOverviewResponse or None if not in cache
        """
        if force_refresh:
            return None
        
        try:
            cache_key = get_dashboard_overview_cache_key(user_id)
            
            cached_data = await cache_manager.get_from_cache_async(
                cache_key,
                data_type='dashboard_overview'
            )
            
            if cached_data is not None:
                logger.debug(f"Loaded dashboard overview from cache for user: {user_id}")
                return cls(**cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading dashboard overview from cache for user {user_id}: {e}")
            return None
    
    async def invalidate_cache(self, user_id: Union[str, UUID]) -> bool:
        """
        Invalidate cached dashboard overview data.
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if invalidated successfully, False otherwise
        """
        try:
            cache_key = get_dashboard_overview_cache_key(user_id)
            
            success = await cache_manager.invalidate_cache_async(cache_key)
            
            if success:
                logger.debug(f"Invalidated dashboard overview cache for user: {user_id}")
            else:
                logger.warning(f"Failed to invalidate dashboard overview cache for user: {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error invalidating dashboard overview cache for user {user_id}: {e}")
            return False
    
    def get_cache_metadata(self, user_id: Union[str, UUID]) -> Dict[str, Any]:
        """
        Get cache metadata for this dashboard overview.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict[str, Any]: Cache metadata
        """
        cache_key = get_dashboard_overview_cache_key(user_id)
        
        return {
            "cache_key": cache_key,
            "cache_type": DashboardCacheType.OVERVIEW.value,
            "ttl_seconds": get_cache_key_ttl(DashboardCacheType.OVERVIEW),
            "data_size_bytes": len(str(self.dict())),
            "last_updated": self.last_updated.isoformat(),
            "user_id": str(user_id)
        }


class CachedDashboardAnalyticsResponse(DashboardAnalyticsResponse):
    """
    Extended DashboardAnalyticsResponse with caching methods.
    Integrates seamlessly with existing Redis infrastructure.
    """
    
    async def cache_data(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        period: str = "30d",
        filters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Cache the dashboard analytics data.
        
        Args:
            user_id: User identifier (optional for global analytics)
            period: Time period for analytics
            filters: Analytics filters
            
        Returns:
            bool: True if cached successfully, False otherwise
        """
        try:
            cache_key = get_dashboard_analytics_cache_key(user_id, period, filters)
            
            success = await cache_manager.set_to_cache_async(
                cache_key,
                self.dict(),
                ttl=get_cache_key_ttl(DashboardCacheType.ANALYTICS),
                data_type='dashboard_analytics'
            )
            
            if success:
                logger.debug(f"Cached dashboard analytics for user: {user_id}, period: {period}")
            else:
                logger.warning(f"Failed to cache dashboard analytics for user: {user_id}, period: {period}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching dashboard analytics for user {user_id}, period {period}: {e}")
            return False
    
    @classmethod
    async def from_cache(
        cls,
        user_id: Optional[Union[str, UUID]] = None,
        period: str = "30d",
        filters: Optional[Dict[str, Any]] = None,
        force_refresh: bool = False
    ) -> Optional['CachedDashboardAnalyticsResponse']:
        """
        Load dashboard analytics data from cache.
        
        Args:
            user_id: User identifier (optional for global analytics)
            period: Time period for analytics
            filters: Analytics filters
            force_refresh: Force refresh from database
            
        Returns:
            CachedDashboardAnalyticsResponse or None if not in cache
        """
        if force_refresh:
            return None
        
        try:
            cache_key = get_dashboard_analytics_cache_key(user_id, period, filters)
            
            cached_data = await cache_manager.get_from_cache_async(
                cache_key,
                data_type='dashboard_analytics'
            )
            
            if cached_data is not None:
                logger.debug(f"Loaded dashboard analytics from cache for user: {user_id}, period: {period}")
                return cls(**cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading dashboard analytics from cache for user {user_id}, period {period}: {e}")
            return None
    
    async def invalidate_cache(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        period: str = "30d",
        filters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Invalidate cached dashboard analytics data.
        
        Args:
            user_id: User identifier (optional for global analytics)
            period: Time period for analytics
            filters: Analytics filters
            
        Returns:
            bool: True if invalidated successfully, False otherwise
        """
        try:
            cache_key = get_dashboard_analytics_cache_key(user_id, period, filters)
            
            success = await cache_manager.invalidate_cache_async(cache_key)
            
            if success:
                logger.debug(f"Invalidated dashboard analytics cache for user: {user_id}, period: {period}")
            else:
                logger.warning(f"Failed to invalidate dashboard analytics cache for user: {user_id}, period: {period}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error invalidating dashboard analytics cache for user {user_id}, period {period}: {e}")
            return False
    
    def get_cache_metadata(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        period: str = "30d",
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get cache metadata for this dashboard analytics.
        
        Args:
            user_id: User identifier (optional for global analytics)
            period: Time period for analytics
            filters: Analytics filters
            
        Returns:
            Dict[str, Any]: Cache metadata
        """
        cache_key = get_dashboard_analytics_cache_key(user_id, period, filters)
        
        return {
            "cache_key": cache_key,
            "cache_type": DashboardCacheType.ANALYTICS.value,
            "ttl_seconds": get_cache_key_ttl(DashboardCacheType.ANALYTICS),
            "data_size_bytes": len(str(self.dict())),
            "generated_at": self.generated_at.isoformat(),
            "analytics_period": self.analytics_period,
            "user_id": str(user_id) if user_id else None,
            "period": period,
            "filters": filters
        }


class CachedUserPreferencesRequest(UserPreferencesRequest):
    """
    Extended UserPreferencesRequest with caching methods.
    Integrates seamlessly with existing Redis infrastructure.
    """
    
    async def cache_data(self, user_id: Union[str, UUID]) -> bool:
        """
        Cache the user preferences data.
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if cached successfully, False otherwise
        """
        try:
            cache_key = get_user_preferences_cache_key(user_id)
            
            success = await cache_manager.set_to_cache_async(
                cache_key,
                self.dict(),
                ttl=get_cache_key_ttl(DashboardCacheType.USER_PREFERENCES),
                data_type='user_preferences'
            )
            
            if success:
                logger.debug(f"Cached user preferences for user: {user_id}")
            else:
                logger.warning(f"Failed to cache user preferences for user: {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching user preferences for user {user_id}: {e}")
            return False
    
    @classmethod
    async def from_cache(
        cls,
        user_id: Union[str, UUID],
        force_refresh: bool = False
    ) -> Optional['CachedUserPreferencesRequest']:
        """
        Load user preferences data from cache.
        
        Args:
            user_id: User identifier
            force_refresh: Force refresh from database
            
        Returns:
            CachedUserPreferencesRequest or None if not in cache
        """
        if force_refresh:
            return None
        
        try:
            cache_key = get_user_preferences_cache_key(user_id)
            
            cached_data = await cache_manager.get_from_cache_async(
                cache_key,
                data_type='user_preferences'
            )
            
            if cached_data is not None:
                logger.debug(f"Loaded user preferences from cache for user: {user_id}")
                return cls(**cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading user preferences from cache for user {user_id}: {e}")
            return None
    
    async def invalidate_cache(self, user_id: Union[str, UUID]) -> bool:
        """
        Invalidate cached user preferences data.
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if invalidated successfully, False otherwise
        """
        try:
            cache_key = get_user_preferences_cache_key(user_id)
            
            success = await cache_manager.invalidate_cache_async(cache_key)
            
            if success:
                logger.debug(f"Invalidated user preferences cache for user: {user_id}")
            else:
                logger.warning(f"Failed to invalidate user preferences cache for user: {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error invalidating user preferences cache for user {user_id}: {e}")
            return False
    
    def get_cache_metadata(self, user_id: Union[str, UUID]) -> Dict[str, Any]:
        """
        Get cache metadata for this user preferences.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict[str, Any]: Cache metadata
        """
        cache_key = get_user_preferences_cache_key(user_id)
        
        return {
            "cache_key": cache_key,
            "cache_type": DashboardCacheType.USER_PREFERENCES.value,
            "ttl_seconds": get_cache_key_ttl(DashboardCacheType.USER_PREFERENCES),
            "data_size_bytes": len(str(self.dict())),
            "updated_at": self.updated_at.isoformat(),
            "user_id": str(user_id)
        }


class CachedDashboardConfigurationResponse(DashboardConfigurationResponse):
    """
    Extended DashboardConfigurationResponse with caching methods.
    Integrates seamlessly with existing Redis infrastructure.
    """
    
    async def cache_data(self) -> bool:
        """
        Cache the dashboard configuration data.
        
        Returns:
            bool: True if cached successfully, False otherwise
        """
        try:
            cache_key = "dash:config:global"
            
            success = await cache_manager.set_to_cache_async(
                cache_key,
                self.dict(),
                ttl=3600,  # 1 hour for configuration data
                data_type='dashboard_config'
            )
            
            if success:
                logger.debug("Cached dashboard configuration")
            else:
                logger.warning("Failed to cache dashboard configuration")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching dashboard configuration: {e}")
            return False
    
    @classmethod
    async def from_cache(cls, force_refresh: bool = False) -> Optional['CachedDashboardConfigurationResponse']:
        """
        Load dashboard configuration data from cache.
        
        Args:
            force_refresh: Force refresh from database
            
        Returns:
            CachedDashboardConfigurationResponse or None if not in cache
        """
        if force_refresh:
            return None
        
        try:
            cache_key = "dash:config:global"
            
            cached_data = await cache_manager.get_from_cache_async(
                cache_key,
                data_type='dashboard_config'
            )
            
            if cached_data is not None:
                logger.debug("Loaded dashboard configuration from cache")
                return cls(**cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading dashboard configuration from cache: {e}")
            return None
    
    async def invalidate_cache(self) -> bool:
        """
        Invalidate cached dashboard configuration data.
        
        Returns:
            bool: True if invalidated successfully, False otherwise
        """
        try:
            cache_key = "dash:config:global"
            
            success = await cache_manager.invalidate_cache_async(cache_key)
            
            if success:
                logger.debug("Invalidated dashboard configuration cache")
            else:
                logger.warning("Failed to invalidate dashboard configuration cache")
            
            return success
            
        except Exception as e:
            logger.error(f"Error invalidating dashboard configuration cache: {e}")
            return False
    
    def get_cache_metadata(self) -> Dict[str, Any]:
        """
        Get cache metadata for this dashboard configuration.
        
        Returns:
            Dict[str, Any]: Cache metadata
        """
        cache_key = "dash:config:global"
        
        return {
            "cache_key": cache_key,
            "cache_type": "dashboard_config",
            "ttl_seconds": 3600,
            "data_size_bytes": len(str(self.dict())),
            "last_updated": self.last_updated.isoformat(),
            "configuration_version": self.configuration_version
        }


# Utility functions for dashboard model caching
async def cache_dashboard_models_batch(
    overview_data: Optional[CachedDashboardOverviewResponse] = None,
    analytics_data: Optional[CachedDashboardAnalyticsResponse] = None,
    preferences_data: Optional[CachedUserPreferencesRequest] = None,
    config_data: Optional[CachedDashboardConfigurationResponse] = None,
    user_id: Optional[Union[str, UUID]] = None,
    analytics_period: str = "30d",
    analytics_filters: Optional[Dict[str, Any]] = None
) -> Dict[str, bool]:
    """
    Cache multiple dashboard models in batch.
    
    Args:
        overview_data: Dashboard overview data to cache
        analytics_data: Dashboard analytics data to cache
        preferences_data: User preferences data to cache
        config_data: Dashboard configuration data to cache
        user_id: User identifier (required for user-specific data)
        analytics_period: Period for analytics data
        analytics_filters: Filters for analytics data
        
    Returns:
        Dict[str, bool]: Results of cache operations
    """
    results = {}
    
    # Cache overview data
    if overview_data and user_id:
        results['overview'] = await overview_data.cache_data(user_id)
    
    # Cache analytics data
    if analytics_data:
        results['analytics'] = await analytics_data.cache_data(
            user_id, analytics_period, analytics_filters
        )
    
    # Cache preferences data
    if preferences_data and user_id:
        results['preferences'] = await preferences_data.cache_data(user_id)
    
    # Cache configuration data
    if config_data:
        results['configuration'] = await config_data.cache_data()
    
    return results


async def invalidate_dashboard_models_batch(
    user_id: Optional[Union[str, UUID]] = None,
    analytics_period: str = "30d",
    analytics_filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Invalidate multiple dashboard model caches in batch.
    
    Args:
        user_id: User identifier (required for user-specific data)
        analytics_period: Period for analytics data
        analytics_filters: Filters for analytics data
        
    Returns:
        Dict[str, bool]: Results of invalidation operations
    """
    results = {}
    
    try:
        # Invalidate user-specific caches
        if user_id:
            from src.dashboard.cache_keys import get_user_cache_pattern
            pattern = get_user_cache_pattern(user_id)
            invalidated_count = await cache_manager.invalidate_pattern_async(pattern)
            results['user_specific'] = invalidated_count > 0
            logger.info(f"Invalidated {invalidated_count} user-specific cache keys for user: {user_id}")
        
        # Invalidate global configuration cache
        config_cache_key = "dash:config:global"
        config_invalidated = await cache_manager.invalidate_cache_async(config_cache_key)
        results['configuration'] = config_invalidated
        
        # Invalidate analytics cache
        if analytics_period:
            from src.dashboard.cache_keys import get_analytics_cache_pattern
            analytics_pattern = get_analytics_cache_pattern(analytics_period)
            analytics_invalidated_count = await cache_manager.invalidate_pattern_async(analytics_pattern)
            results['analytics'] = analytics_invalidated_count > 0
        
        return results
        
    except Exception as e:
        logger.error(f"Error invalidating dashboard models batch: {e}")
        return {"error": str(e), "success": False}


def get_dashboard_model_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics for dashboard models.
    
    Returns:
        Dict[str, Any]: Cache statistics
    """
    try:
        cache_metrics = cache_manager.get_cache_metrics()
        
        return {
            "cache_metrics": cache_metrics,
            "dashboard_models": {
                "overview_response": {
                    "cache_type": DashboardCacheType.OVERVIEW.value,
                    "ttl_seconds": get_cache_key_ttl(DashboardCacheType.OVERVIEW),
                    "supports_user_specific": True
                },
                "analytics_response": {
                    "cache_type": DashboardCacheType.ANALYTICS.value,
                    "ttl_seconds": get_cache_key_ttl(DashboardCacheType.ANALYTICS),
                    "supports_user_specific": True,
                    "supports_period_filtering": True
                },
                "user_preferences": {
                    "cache_type": DashboardCacheType.USER_PREFERENCES.value,
                    "ttl_seconds": get_cache_key_ttl(DashboardCacheType.USER_PREFERENCES),
                    "supports_user_specific": True
                },
                "configuration_response": {
                    "cache_type": "dashboard_config",
                    "ttl_seconds": 3600,
                    "supports_user_specific": False
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard model cache stats: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
