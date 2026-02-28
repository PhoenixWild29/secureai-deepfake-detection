#!/usr/bin/env python3
"""
Redis Cache Utility
High-performance Redis caching for dashboard API with sub-100ms response times
"""

import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic
from contextlib import asynccontextmanager
import aioredis
from aioredis import Redis
from pydantic import BaseModel
import structlog

from src.models.dashboard import DashboardOverviewResponse, DashboardCacheKey
from src.models.navigation import NavigationState, NavigationCacheKey, NavigationPreferences

# Configure structured logging
logger = structlog.get_logger(__name__)

T = TypeVar('T', bound=BaseModel)


class RedisCacheManager:
    """
    High-performance Redis cache manager for dashboard data
    Optimized for sub-100ms response times
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_connections: int = 20,
        socket_keepalive: bool = True,
        socket_keepalive_options: Dict[int, int] = None,
        health_check_interval: int = 30
    ):
        """
        Initialize Redis cache manager
        
        Args:
            redis_url: Redis connection URL
            max_connections: Maximum number of connections in pool
            socket_keepalive: Enable socket keepalive
            socket_keepalive_options: Socket keepalive options
            health_check_interval: Health check interval in seconds
        """
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.socket_keepalive = socket_keepalive
        self.socket_keepalive_options = socket_keepalive_options or {
            1: 1,  # TCP_KEEPIDLE
            2: 3,  # TCP_KEEPINTVL
            3: 5   # TCP_KEEPCNT
        }
        self.health_check_interval = health_check_interval
        
        self._redis_pool: Optional[Redis] = None
        self._connection_lock = asyncio.Lock()
        self._last_health_check = datetime.now(timezone.utc)
        self._is_healthy = False
        
        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0,
            'total_requests': 0
        }
        
        logger.info(
            "RedisCacheManager initialized",
            redis_url=redis_url,
            max_connections=max_connections,
            socket_keepalive=socket_keepalive
        )
    
    async def _get_redis_pool(self) -> Redis:
        """Get or create Redis connection pool"""
        if self._redis_pool is None or not self._is_healthy:
            async with self._connection_lock:
                if self._redis_pool is None or not self._is_healthy:
                    try:
                        self._redis_pool = aioredis.from_url(
                            self.redis_url,
                            max_connections=self.max_connections,
                            socket_keepalive=self.socket_keepalive,
                            socket_keepalive_options=self.socket_keepalive_options,
                            health_check_interval=self.health_check_interval,
                            retry_on_timeout=True,
                            socket_connect_timeout=5,
                            socket_timeout=5
                        )
                        
                        # Test connection
                        await self._redis_pool.ping()
                        self._is_healthy = True
                        self._last_health_check = datetime.now(timezone.utc)
                        
                        logger.info("Redis connection pool created successfully")
                        
                    except Exception as e:
                        logger.error("Failed to create Redis connection pool", error=str(e))
                        self._is_healthy = False
                        raise
        
        return self._redis_pool
    
    async def health_check(self) -> bool:
        """Perform health check on Redis connection"""
        try:
            redis = await self._get_redis_pool()
            await redis.ping()
            self._is_healthy = True
            self._last_health_check = datetime.now(timezone.utc)
            return True
        except Exception as e:
            logger.warning("Redis health check failed", error=str(e))
            self._is_healthy = False
            return False
    
    async def get(
        self,
        key: Union[str, DashboardCacheKey],
        model_class: Optional[type] = None
    ) -> Optional[Any]:
        """
        Get value from Redis cache with high performance
        
        Args:
            key: Cache key (string or DashboardCacheKey)
            model_class: Pydantic model class for deserialization
            
        Returns:
            Cached value or None if not found
        """
        self.stats['total_requests'] += 1
        start_time = datetime.now(timezone.utc)
        
        try:
            redis = await self._get_redis_pool()
            
            # Convert key to string if needed
            cache_key = key.to_string() if isinstance(key, DashboardCacheKey) else str(key)
            
            # Get value from Redis
            value = await redis.get(cache_key)
            
            if value is None:
                self.stats['misses'] += 1
                logger.debug("Cache miss", key=cache_key)
                return None
            
            # Deserialize JSON
            data = json.loads(value)
            
            # Deserialize to Pydantic model if specified
            if model_class and issubclass(model_class, BaseModel):
                result = model_class(**data)
            else:
                result = data
            
            self.stats['hits'] += 1
            
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            logger.debug(
                "Cache hit",
                key=cache_key,
                response_time_ms=response_time,
                hit_rate=self.get_hit_rate()
            )
            
            return result
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error("Cache get error", key=str(key), error=str(e))
            return None
    
    async def set(
        self,
        key: Union[str, DashboardCacheKey],
        value: Any,
        ttl_seconds: int = 300,
        serialize_model: bool = True
    ) -> bool:
        """
        Set value in Redis cache with TTL
        
        Args:
            key: Cache key (string or DashboardCacheKey)
            value: Value to cache
            ttl_seconds: Time-to-live in seconds
            serialize_model: Whether to serialize Pydantic models
            
        Returns:
            True if successful, False otherwise
        """
        try:
            redis = await self._get_redis_pool()
            
            # Convert key to string if needed
            cache_key = key.to_string() if isinstance(key, DashboardCacheKey) else str(key)
            
            # Serialize value
            if serialize_model and isinstance(value, BaseModel):
                serialized_value = value.model_dump_json()
            elif isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, default=str)
            else:
                serialized_value = str(value)
            
            # Set with TTL
            await redis.setex(cache_key, ttl_seconds, serialized_value)
            
            self.stats['sets'] += 1
            
            logger.debug(
                "Cache set",
                key=cache_key,
                ttl_seconds=ttl_seconds,
                value_size_bytes=len(serialized_value)
            )
            
            return True
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error("Cache set error", key=str(key), error=str(e))
            return False
    
    async def delete(self, key: Union[str, DashboardCacheKey]) -> bool:
        """
        Delete value from Redis cache
        
        Args:
            key: Cache key (string or DashboardCacheKey)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            redis = await self._get_redis_pool()
            
            # Convert key to string if needed
            cache_key = key.to_string() if isinstance(key, DashboardCacheKey) else str(key)
            
            # Delete key
            deleted_count = await redis.delete(cache_key)
            
            if deleted_count > 0:
                self.stats['deletes'] += 1
                logger.debug("Cache delete", key=cache_key)
                return True
            else:
                logger.debug("Cache delete - key not found", key=cache_key)
                return False
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error("Cache delete error", key=str(key), error=str(e))
            return False
    
    async def exists(self, key: Union[str, DashboardCacheKey]) -> bool:
        """
        Check if key exists in Redis cache
        
        Args:
            key: Cache key (string or DashboardCacheKey)
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            redis = await self._get_redis_pool()
            
            # Convert key to string if needed
            cache_key = key.to_string() if isinstance(key, DashboardCacheKey) else str(key)
            
            exists = await redis.exists(cache_key)
            return bool(exists)
            
        except Exception as e:
            logger.error("Cache exists error", key=str(key), error=str(e))
            return False
    
    async def get_ttl(self, key: Union[str, DashboardCacheKey]) -> int:
        """
        Get TTL for key in Redis cache
        
        Args:
            key: Cache key (string or DashboardCacheKey)
            
        Returns:
            TTL in seconds, -1 if no TTL, -2 if key doesn't exist
        """
        try:
            redis = await self._get_redis_pool()
            
            # Convert key to string if needed
            cache_key = key.to_string() if isinstance(key, DashboardCacheKey) else str(key)
            
            ttl = await redis.ttl(cache_key)
            return ttl
            
        except Exception as e:
            logger.error("Cache TTL error", key=str(key), error=str(e))
            return -2
    
    async def increment(self, key: Union[str, DashboardCacheKey], amount: int = 1) -> Optional[int]:
        """
        Increment counter in Redis cache
        
        Args:
            key: Cache key (string or DashboardCacheKey)
            amount: Amount to increment by
            
        Returns:
            New value or None if error
        """
        try:
            redis = await self._get_redis_pool()
            
            # Convert key to string if needed
            cache_key = key.to_string() if isinstance(key, DashboardCacheKey) else str(key)
            
            new_value = await redis.incrby(cache_key, amount)
            return new_value
            
        except Exception as e:
            logger.error("Cache increment error", key=str(key), error=str(e))
            return None
    
    async def set_multiple(
        self,
        key_value_pairs: Dict[Union[str, DashboardCacheKey], Any],
        ttl_seconds: int = 300
    ) -> Dict[str, bool]:
        """
        Set multiple key-value pairs in Redis cache
        
        Args:
            key_value_pairs: Dictionary of key-value pairs
            ttl_seconds: Time-to-live in seconds
            
        Returns:
            Dictionary mapping keys to success status
        """
        results = {}
        
        for key, value in key_value_pairs.items():
            success = await self.set(key, value, ttl_seconds)
            cache_key = key.to_string() if isinstance(key, DashboardCacheKey) else str(key)
            results[cache_key] = success
        
        return results
    
    async def get_multiple(
        self,
        keys: List[Union[str, DashboardCacheKey]],
        model_class: Optional[type] = None
    ) -> Dict[str, Any]:
        """
        Get multiple values from Redis cache
        
        Args:
            keys: List of cache keys
            model_class: Pydantic model class for deserialization
            
        Returns:
            Dictionary mapping keys to values
        """
        try:
            redis = await self._get_redis_pool()
            
            # Convert keys to strings
            cache_keys = [
                key.to_string() if isinstance(key, DashboardCacheKey) else str(key)
                for key in keys
            ]
            
            # Get values from Redis
            values = await redis.mget(cache_keys)
            
            # Process results
            results = {}
            for i, (cache_key, value) in enumerate(zip(cache_keys, values)):
                if value is not None:
                    try:
                        data = json.loads(value)
                        
                        # Deserialize to Pydantic model if specified
                        if model_class and issubclass(model_class, BaseModel):
                            results[cache_key] = model_class(**data)
                        else:
                            results[cache_key] = data
                            
                    except Exception as e:
                        logger.warning("Failed to deserialize cached value", key=cache_key, error=str(e))
                        results[cache_key] = None
                else:
                    results[cache_key] = None
            
            return results
            
        except Exception as e:
            logger.error("Cache get multiple error", keys=[str(k) for k in keys], error=str(e))
            return {}
    
    def get_hit_rate(self) -> float:
        """Get cache hit rate"""
        total_requests = self.stats['total_requests']
        if total_requests == 0:
            return 0.0
        return self.stats['hits'] / total_requests
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            **self.stats,
            'hit_rate': self.get_hit_rate(),
            'is_healthy': self._is_healthy,
            'last_health_check': self._last_health_check.isoformat(),
            'redis_url': self.redis_url,
            'max_connections': self.max_connections
        }
    
    async def clear_stats(self):
        """Clear cache statistics"""
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0,
            'total_requests': 0
        }
        logger.info("Cache statistics cleared")
    
    async def close(self):
        """Close Redis connection pool"""
        if self._redis_pool:
            await self._redis_pool.close()
            self._redis_pool = None
            self._is_healthy = False
            logger.info("Redis connection pool closed")


class DashboardCacheManager:
    """
    Specialized cache manager for dashboard data
    Optimized for dashboard-specific caching patterns
    """
    
    def __init__(self, redis_manager: RedisCacheManager):
        """
        Initialize dashboard cache manager
        
        Args:
            redis_manager: Redis cache manager instance
        """
        self.redis = redis_manager
        
        # Dashboard-specific cache keys
        self.DASHBOARD_OVERVIEW_KEY = DashboardCacheKey(key_type="dashboard_overview", user_id=None, version="v1")
        self.USER_ACTIVITY_KEY = DashboardCacheKey(key_type="user_activity", user_id=None, version="v1")
        self.SYSTEM_METRICS_KEY = DashboardCacheKey(key_type="system_metrics", user_id=None, version="v1")
        self.BLOCKCHAIN_METRICS_KEY = DashboardCacheKey(key_type="blockchain_metrics", user_id=None, version="v1")
        self.PROCESSING_QUEUE_KEY = DashboardCacheKey(key_type="processing_queue", user_id=None, version="v1")
        
        # Cache TTL settings (in seconds)
        self.TTL_DASHBOARD_OVERVIEW = 60  # 1 minute
        self.TTL_USER_ACTIVITY = 120      # 2 minutes
        self.TTL_SYSTEM_METRICS = 30      # 30 seconds
        self.TTL_BLOCKCHAIN_METRICS = 180 # 3 minutes
        self.TTL_PROCESSING_QUEUE = 15    # 15 seconds
        self.TTL_NAVIGATION_CONTEXT = 300  # 5 minutes (NEW)
        self.TTL_USER_PREFERENCES = 3600  # 1 hour (NEW)
        self.TTL_PREFETCH_DATA = 300  # 5 minutes (NEW)
    
    async def get_dashboard_overview(
        self,
        user_id: Optional[str] = None,
        force_refresh: bool = False
    ) -> Optional[DashboardOverviewResponse]:
        """
        Get dashboard overview from cache
        
        Args:
            user_id: User ID for personalized data
            force_refresh: Force refresh from cache
            
        Returns:
            Dashboard overview data or None if not cached
        """
        cache_key = DashboardCacheKey(
            key_type="dashboard_overview",
            user_id=user_id,
            version="v1"
        )
        
        if not force_refresh:
            return await self.redis.get(cache_key, DashboardOverviewResponse)
        
        return None
    
    async def set_dashboard_overview(
        self,
        data: DashboardOverviewResponse,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Cache dashboard overview data
        
        Args:
            data: Dashboard overview data
            user_id: User ID for personalized data
            
        Returns:
            True if successful, False otherwise
        """
        cache_key = DashboardCacheKey(
            key_type="dashboard_overview",
            user_id=user_id,
            version="v1"
        )
        
        return await self.redis.set(
            cache_key,
            data,
            ttl_seconds=self.TTL_DASHBOARD_OVERVIEW
        )
    
    async def invalidate_dashboard_cache(self, user_id: Optional[str] = None):
        """
        Invalidate dashboard cache entries
        
        Args:
            user_id: User ID for personalized cache invalidation
        """
        cache_keys = [
            DashboardCacheKey(key_type="dashboard_overview", user_id=user_id, version="v1"),
            DashboardCacheKey(key_type="user_activity", user_id=user_id, version="v1"),
            DashboardCacheKey(key_type="system_metrics", user_id=None, version="v1"),
            DashboardCacheKey(key_type="blockchain_metrics", user_id=None, version="v1"),
            DashboardCacheKey(key_type="processing_queue", user_id=None, version="v1")
        ]
        
        for cache_key in cache_keys:
            await self.redis.delete(cache_key)
        
        logger.info("Dashboard cache invalidated", user_id=user_id)
    
    # Navigation-specific caching methods (NEW)
    async def get_navigation_context(
        self,
        cache_key: NavigationCacheKey,
        force_refresh: bool = False
    ) -> Optional[NavigationState]:
        """
        Get cached navigation context
        
        Args:
            cache_key: Navigation cache key
            force_refresh: Force refresh from cache
            
        Returns:
            Cached navigation state or None
        """
        if not force_refresh:
            return await self.redis.get(cache_key.to_key(), NavigationState)
        
        return None
    
    async def set_navigation_context(
        self,
        cache_key: NavigationCacheKey,
        navigation_state: NavigationState
    ) -> bool:
        """
        Cache navigation context
        
        Args:
            cache_key: Navigation cache key
            navigation_state: Navigation state to cache
            
        Returns:
            True if successful, False otherwise
        """
        return await self.redis.set(
            cache_key.to_key(),
            navigation_state,
            ttl_seconds=self.TTL_NAVIGATION_CONTEXT
        )
    
    async def get_user_preferences(
        self,
        user_id: str,
        force_refresh: bool = False
    ) -> Optional[NavigationPreferences]:
        """
        Get cached user navigation preferences
        
        Args:
            user_id: User identifier
            force_refresh: Force refresh from cache
            
        Returns:
            Cached user preferences or None
        """
        cache_key = f"nav_prefs:{user_id}"
        
        if not force_refresh:
            return await self.redis.get(cache_key, NavigationPreferences)
        
        return None
    
    async def set_user_preferences(
        self,
        user_id: str,
        preferences: NavigationPreferences
    ) -> bool:
        """
        Cache user navigation preferences
        
        Args:
            user_id: User identifier
            preferences: User preferences to cache
            
        Returns:
            True if successful, False otherwise
        """
        cache_key = f"nav_prefs:{user_id}"
        
        return await self.redis.set(
            cache_key,
            preferences,
            ttl_seconds=self.TTL_USER_PREFERENCES
        )
    
    async def get_prefetch_data(
        self,
        data_source: str,
        route_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached prefetch data
        
        Args:
            data_source: Data source identifier
            route_path: Route path
            
        Returns:
            Cached prefetch data or None
        """
        cache_key = f"prefetch:{data_source}:{route_path}"
        
        return await self.redis.get(cache_key)
    
    async def set_prefetch_data(
        self,
        data_source: str,
        route_path: str,
        data: Dict[str, Any],
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Cache prefetch data
        
        Args:
            data_source: Data source identifier
            route_path: Route path
            data: Data to cache
            ttl_seconds: Cache TTL (uses default if None)
            
        Returns:
            True if successful, False otherwise
        """
        cache_key = f"prefetch:{data_source}:{route_path}"
        ttl = ttl_seconds or self.TTL_PREFETCH_DATA
        
        return await self.redis.set(cache_key, data, ttl_seconds=ttl)
    
    async def invalidate_navigation_cache(self, user_id: str):
        """
        Invalidate navigation cache for user
        
        Args:
            user_id: User identifier
        """
        patterns = [
            f"nav:{user_id}:*",
            f"nav_prefs:{user_id}",
            f"prefetch:*:{user_id}"
        ]
        
        for pattern in patterns:
            # Use Redis SCAN to find keys matching pattern and delete them
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        
        logger.info("Navigation cache invalidated", user_id=user_id, patterns=patterns)


# Global cache manager instance
_cache_manager: Optional[RedisCacheManager] = None
_dashboard_cache_manager: Optional[DashboardCacheManager] = None


async def get_cache_manager() -> RedisCacheManager:
    """Get global Redis cache manager instance"""
    global _cache_manager
    
    if _cache_manager is None:
        redis_url = "redis://localhost:6379"  # Default, should be from config
        _cache_manager = RedisCacheManager(redis_url)
        await _cache_manager.health_check()
    
    return _cache_manager


async def get_dashboard_cache_manager() -> DashboardCacheManager:
    """Get global dashboard cache manager instance"""
    global _dashboard_cache_manager
    
    if _dashboard_cache_manager is None:
        redis_manager = await get_cache_manager()
        _dashboard_cache_manager = DashboardCacheManager(redis_manager)
    
    return _dashboard_cache_manager


@asynccontextmanager
async def cache_context():
    """Context manager for cache operations"""
    cache_manager = await get_cache_manager()
    try:
        yield cache_manager
    finally:
        # Cleanup if needed
        pass
