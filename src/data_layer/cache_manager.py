#!/usr/bin/env python3
"""
Cache Manager for Redis Operations
Centralized Redis caching logic for dashboard data with sub-100ms response times
"""

import json
import pickle
import hashlib
import logging
from typing import Any, Optional, Dict, List, Union, Callable
from datetime import datetime, timedelta, timezone
from uuid import UUID
import asyncio
from functools import wraps

try:
    import redis
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    aioredis = None

# Configure logging
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'password': None,
    'decode_responses': True,
    'socket_timeout': 5,
    'socket_connect_timeout': 5,
    'retry_on_timeout': True,
    'max_connections': 20,
    'health_check_interval': 30
}

# Default TTL values for different data types (in seconds)
DEFAULT_TTL = {
    'dashboard_overview': 300,      # 5 minutes
    'dashboard_analytics': 600,     # 10 minutes
    'user_preferences': 1800,       # 30 minutes
    'system_status': 60,            # 1 minute
    'performance_metrics': 300,     # 5 minutes
    'recent_analyses': 120,         # 2 minutes
    'notifications': 600,           # 10 minutes
    'widget_data': 300,             # 5 minutes
    'aggregated_analytics': 900,    # 15 minutes
    'cache_metrics': 60,            # 1 minute
    'default': 300                  # 5 minutes
}

# Cache key prefixes for different data types
CACHE_PREFIXES = {
    'dashboard': 'dash',
    'user': 'user',
    'analytics': 'analytics',
    'system': 'system',
    'widget': 'widget',
    'metrics': 'metrics',
    'session': 'session',
    'preferences': 'prefs',
    'notifications': 'notif',
    'performance': 'perf'
}


class CacheManager:
    """
    Centralized cache manager for Redis operations
    Provides high-performance caching with sub-100ms response times
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize cache manager with Redis configuration
        
        Args:
            config: Redis configuration dictionary
        """
        self.config = {**CACHE_CONFIG, **(config or {})}
        self._redis_client: Optional[redis.Redis] = None
        self._async_redis_client: Optional[aioredis.Redis] = None
        self._is_connected = False
        self._connection_lock = asyncio.Lock()
        
        # Performance metrics
        self._metrics = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0,
            'avg_response_time': 0.0
        }
        
        # Initialize connection
        self._initialize_connection()
    
    def _initialize_connection(self) -> None:
        """Initialize Redis connection"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available - running in no-cache mode")
            return
        
        try:
            # Synchronous client for sync operations
            self._redis_client = redis.Redis(
                host=self.config['host'],
                port=self.config['port'],
                db=self.config['db'],
                password=self.config['password'],
                decode_responses=self.config['decode_responses'],
                socket_timeout=self.config['socket_timeout'],
                socket_connect_timeout=self.config['socket_connect_timeout'],
                retry_on_timeout=self.config['retry_on_timeout'],
                max_connections=self.config['max_connections'],
                health_check_interval=self.config['health_check_interval']
            )
            
            # Test connection
            self._redis_client.ping()
            self._is_connected = True
            logger.info("Redis cache manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            self._is_connected = False
    
    async def _get_async_client(self) -> Optional[aioredis.Redis]:
        """Get async Redis client with connection pooling"""
        if not REDIS_AVAILABLE or not self._is_connected:
            return None
        
        async with self._connection_lock:
            if self._async_redis_client is None:
                try:
                    self._async_redis_client = aioredis.Redis(
                        host=self.config['host'],
                        port=self.config['port'],
                        db=self.config['db'],
                        password=self.config['password'],
                        decode_responses=self.config['decode_responses'],
                        socket_timeout=self.config['socket_timeout'],
                        socket_connect_timeout=self.config['socket_connect_timeout'],
                        retry_on_timeout=self.config['retry_on_timeout'],
                        max_connections=self.config['max_connections'],
                        health_check_interval=self.config['health_check_interval']
                    )
                    await self._async_redis_client.ping()
                except Exception as e:
                    logger.error(f"Failed to initialize async Redis connection: {e}")
                    return None
            
            return self._async_redis_client
    
    def _update_metrics(self, operation: str, response_time: float, success: bool = True) -> None:
        """Update cache performance metrics"""
        if operation == 'hit':
            self._metrics['hits'] += 1
        elif operation == 'miss':
            self._metrics['misses'] += 1
        elif operation == 'set':
            self._metrics['sets'] += 1
        elif operation == 'delete':
            self._metrics['deletes'] += 1
        elif operation == 'error':
            self._metrics['errors'] += 1
        
        # Update average response time
        total_operations = self._metrics['hits'] + self._metrics['misses'] + self._metrics['sets'] + self._metrics['deletes']
        if total_operations > 0:
            current_avg = self._metrics['avg_response_time']
            self._metrics['avg_response_time'] = (current_avg * (total_operations - 1) + response_time) / total_operations
    
    def _serialize_data(self, data: Any) -> str:
        """Serialize data for Redis storage"""
        try:
            # Try JSON first for simple data types
            if isinstance(data, (dict, list, str, int, float, bool, type(None))):
                return json.dumps(data, default=str)
            else:
                # Use pickle for complex objects
                return pickle.dumps(data).hex()
        except (TypeError, ValueError):
            # Fallback to pickle
            return pickle.dumps(data).hex()
    
    def _deserialize_data(self, data: str) -> Any:
        """Deserialize data from Redis storage"""
        try:
            # Try JSON first
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            try:
                # Try pickle
                return pickle.loads(bytes.fromhex(data))
            except (pickle.PickleError, ValueError):
                # Return as string if all else fails
                return data
    
    def _generate_cache_key(self, prefix: str, *parts: Union[str, UUID, int]) -> str:
        """Generate standardized cache key"""
        # Convert all parts to strings and create hash for long keys
        key_parts = [str(part) for part in parts]
        full_key = f"{prefix}:{':'.join(key_parts)}"
        
        # Redis key length limit is 512MB, but we'll limit to 250 chars for performance
        if len(full_key) > 250:
            # Create hash of long keys
            key_hash = hashlib.md5(full_key.encode()).hexdigest()[:16]
            full_key = f"{prefix}:hash:{key_hash}"
        
        return full_key
    
    def get_from_cache(self, key: str, data_type: str = 'default') -> Optional[Any]:
        """
        Get data from cache
        
        Args:
            key: Cache key
            data_type: Type of data for TTL lookup
            
        Returns:
            Cached data or None if not found
        """
        if not self._is_connected or not self._redis_client:
            return None
        
        start_time = datetime.now()
        try:
            cached_data = self._redis_client.get(key)
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if cached_data is not None:
                self._update_metrics('hit', response_time)
                logger.debug(f"Cache hit for key: {key}")
                return self._deserialize_data(cached_data)
            else:
                self._update_metrics('miss', response_time)
                logger.debug(f"Cache miss for key: {key}")
                return None
                
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_metrics('error', response_time, success=False)
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def get_from_cache_async(self, key: str, data_type: str = 'default') -> Optional[Any]:
        """
        Get data from cache asynchronously
        
        Args:
            key: Cache key
            data_type: Type of data for TTL lookup
            
        Returns:
            Cached data or None if not found
        """
        client = await self._get_async_client()
        if not client:
            return None
        
        start_time = datetime.now()
        try:
            cached_data = await client.get(key)
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if cached_data is not None:
                self._update_metrics('hit', response_time)
                logger.debug(f"Async cache hit for key: {key}")
                return self._deserialize_data(cached_data)
            else:
                self._update_metrics('miss', response_time)
                logger.debug(f"Async cache miss for key: {key}")
                return None
                
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_metrics('error', response_time, success=False)
            logger.error(f"Async cache get error for key {key}: {e}")
            return None
    
    def set_to_cache(self, key: str, data: Any, ttl: Optional[int] = None, data_type: str = 'default') -> bool:
        """
        Set data in cache
        
        Args:
            key: Cache key
            data: Data to cache
            ttl: Time to live in seconds (overrides data_type default)
            data_type: Type of data for default TTL lookup
            
        Returns:
            True if successful, False otherwise
        """
        if not self._is_connected or not self._redis_client:
            return False
        
        # Determine TTL
        if ttl is None:
            ttl = DEFAULT_TTL.get(data_type, DEFAULT_TTL['default'])
        
        start_time = datetime.now()
        try:
            serialized_data = self._serialize_data(data)
            result = self._redis_client.setex(key, ttl, serialized_data)
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if result:
                self._update_metrics('set', response_time)
                logger.debug(f"Cache set for key: {key} (TTL: {ttl}s)")
                return True
            else:
                self._update_metrics('error', response_time, success=False)
                logger.error(f"Failed to set cache for key: {key}")
                return False
                
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_metrics('error', response_time, success=False)
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def set_to_cache_async(self, key: str, data: Any, ttl: Optional[int] = None, data_type: str = 'default') -> bool:
        """
        Set data in cache asynchronously
        
        Args:
            key: Cache key
            data: Data to cache
            ttl: Time to live in seconds (overrides data_type default)
            data_type: Type of data for default TTL lookup
            
        Returns:
            True if successful, False otherwise
        """
        client = await self._get_async_client()
        if not client:
            return False
        
        # Determine TTL
        if ttl is None:
            ttl = DEFAULT_TTL.get(data_type, DEFAULT_TTL['default'])
        
        start_time = datetime.now()
        try:
            serialized_data = self._serialize_data(data)
            result = await client.setex(key, ttl, serialized_data)
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if result:
                self._update_metrics('set', response_time)
                logger.debug(f"Async cache set for key: {key} (TTL: {ttl}s)")
                return True
            else:
                self._update_metrics('error', response_time, success=False)
                logger.error(f"Failed to set async cache for key: {key}")
                return False
                
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_metrics('error', response_time, success=False)
            logger.error(f"Async cache set error for key {key}: {e}")
            return False
    
    def invalidate_cache(self, key: str) -> bool:
        """
        Invalidate cache entry
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            True if successful, False otherwise
        """
        if not self._is_connected or not self._redis_client:
            return False
        
        start_time = datetime.now()
        try:
            result = self._redis_client.delete(key)
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if result:
                self._update_metrics('delete', response_time)
                logger.debug(f"Cache invalidated for key: {key}")
                return True
            else:
                self._update_metrics('delete', response_time)  # Still count as delete operation
                logger.debug(f"Cache key not found for invalidation: {key}")
                return True  # Consider not found as successful
                
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_metrics('error', response_time, success=False)
            logger.error(f"Cache invalidation error for key {key}: {e}")
            return False
    
    async def invalidate_cache_async(self, key: str) -> bool:
        """
        Invalidate cache entry asynchronously
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            True if successful, False otherwise
        """
        client = await self._get_async_client()
        if not client:
            return False
        
        start_time = datetime.now()
        try:
            result = await client.delete(key)
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if result:
                self._update_metrics('delete', response_time)
                logger.debug(f"Async cache invalidated for key: {key}")
                return True
            else:
                self._update_metrics('delete', response_time)
                logger.debug(f"Async cache key not found for invalidation: {key}")
                return True
                
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_metrics('error', response_time, success=False)
            logger.error(f"Async cache invalidation error for key {key}: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching pattern
        
        Args:
            pattern: Redis key pattern (e.g., 'dash:*', 'user:123:*')
            
        Returns:
            Number of keys invalidated
        """
        if not self._is_connected or not self._redis_client:
            return 0
        
        start_time = datetime.now()
        try:
            # Find all keys matching pattern
            keys = self._redis_client.keys(pattern)
            if not keys:
                logger.debug(f"No cache keys found matching pattern: {pattern}")
                return 0
            
            # Delete all matching keys
            result = self._redis_client.delete(*keys)
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            self._update_metrics('delete', response_time)
            logger.debug(f"Cache invalidated {result} keys matching pattern: {pattern}")
            return result
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_metrics('error', response_time, success=False)
            logger.error(f"Cache pattern invalidation error for pattern {pattern}: {e}")
            return 0
    
    async def invalidate_pattern_async(self, pattern: str) -> int:
        """
        Invalidate cache entries matching pattern asynchronously
        
        Args:
            pattern: Redis key pattern (e.g., 'dash:*', 'user:123:*')
            
        Returns:
            Number of keys invalidated
        """
        client = await self._get_async_client()
        if not client:
            return 0
        
        start_time = datetime.now()
        try:
            # Find all keys matching pattern
            keys = await client.keys(pattern)
            if not keys:
                logger.debug(f"No async cache keys found matching pattern: {pattern}")
                return 0
            
            # Delete all matching keys
            result = await client.delete(*keys)
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            self._update_metrics('delete', response_time)
            logger.debug(f"Async cache invalidated {result} keys matching pattern: {pattern}")
            return result
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_metrics('error', response_time, success=False)
            logger.error(f"Async cache pattern invalidation error for pattern {pattern}: {e}")
            return 0
    
    def get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics"""
        total_requests = self._metrics['hits'] + self._metrics['misses']
        hit_rate = (self._metrics['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hits': self._metrics['hits'],
            'misses': self._metrics['misses'],
            'sets': self._metrics['sets'],
            'deletes': self._metrics['deletes'],
            'errors': self._metrics['errors'],
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2),
            'avg_response_time_ms': round(self._metrics['avg_response_time'], 2),
            'is_connected': self._is_connected,
            'redis_available': REDIS_AVAILABLE
        }
    
    def clear_all_cache(self) -> bool:
        """Clear all cache entries (use with caution)"""
        if not self._is_connected or not self._redis_client:
            return False
        
        try:
            self._redis_client.flushdb()
            logger.warning("All cache entries cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing all cache: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Perform cache health check"""
        if not REDIS_AVAILABLE:
            return {
                'status': 'unavailable',
                'message': 'Redis not available',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        if not self._is_connected:
            return {
                'status': 'disconnected',
                'message': 'Redis not connected',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        try:
            start_time = datetime.now()
            self._redis_client.ping()
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                'status': 'healthy',
                'message': 'Cache is operational',
                'response_time_ms': round(response_time, 2),
                'metrics': self.get_cache_metrics(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Cache health check failed: {e}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }


# Global cache manager instance
cache_manager = CacheManager()


# Decorator for cache-aside pattern
def cached(ttl: Optional[int] = None, data_type: str = 'default', key_prefix: str = 'cache'):
    """
    Decorator for implementing cache-aside pattern
    
    Args:
        ttl: Time to live in seconds
        data_type: Type of data for default TTL
        key_prefix: Prefix for cache key generation
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = cache_manager._generate_cache_key(*key_parts)
            
            # Try to get from cache
            cached_result = await cache_manager.get_from_cache_async(cache_key, data_type)
            if cached_result is not None:
                return cached_result
            
            # Execute function if not in cache
            result = await func(*args, **kwargs)
            
            # Store result in cache
            await cache_manager.set_to_cache_async(cache_key, result, ttl, data_type)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = cache_manager._generate_cache_key(*key_parts)
            
            # Try to get from cache
            cached_result = cache_manager.get_from_cache(cache_key, data_type)
            if cached_result is not None:
                return cached_result
            
            # Execute function if not in cache
            result = func(*args, **kwargs)
            
            # Store result in cache
            cache_manager.set_to_cache(cache_key, result, ttl, data_type)
            
            return result
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Utility functions for common cache operations
def get_dashboard_cache_key(user_id: Union[str, UUID], widget_type: str, **kwargs) -> str:
    """Generate cache key for dashboard data"""
    key_parts = [CACHE_PREFIXES['dashboard'], str(user_id), widget_type]
    if kwargs:
        key_parts.append(hashlib.md5(str(sorted(kwargs.items())).encode()).hexdigest()[:8])
    return cache_manager._generate_cache_key(*key_parts)


def get_user_preferences_cache_key(user_id: Union[str, UUID]) -> str:
    """Generate cache key for user preferences"""
    return cache_manager._generate_cache_key(CACHE_PREFIXES['user'], str(user_id), 'preferences')


def get_analytics_cache_key(period: str, filters: Optional[Dict] = None) -> str:
    """Generate cache key for analytics data"""
    key_parts = [CACHE_PREFIXES['analytics'], period]
    if filters:
        key_parts.append(hashlib.md5(str(sorted(filters.items())).encode()).hexdigest()[:8])
    return cache_manager._generate_cache_key(*key_parts)


def get_system_status_cache_key(component: Optional[str] = None) -> str:
    """Generate cache key for system status"""
    key_parts = [CACHE_PREFIXES['system'], 'status']
    if component:
        key_parts.append(component)
    return cache_manager._generate_cache_key(*key_parts)


def get_detection_results_cache_key(analysis_id: Union[str, UUID]) -> str:
    """Generate cache key for detection results (added for Work Order #20)"""
    return cache_manager._generate_cache_key('detection', str(analysis_id), 'results')


# Extended CacheManager class methods for detection results export (Work Order #20)
class DetectionResultsCacheManager:
    """Extended cache functionality for detection results export"""
    
    @staticmethod
    async def get_cached_detection_result(analysis_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached detection results for export.
        
        Args:
            analysis_id: Analysis identifier
            
        Returns:
            Dict containing detection results or None if not found
        """
        try:
            cache_key = get_detection_results_cache_key(analysis_id)
            
            # Attempt to retrieve from cache
            cached_data = await cache_manager.get_from_cache_async(cache_key, 'pickle')
            
            if cached_data is not None:
                logger.info(f"Retrieved cached detection results for analysis {analysis_id}")
                return cached_data
            
            # If not in cache, try alternative key formats
            alternative_keys = [
                f"detection_result:{analysis_id}",
                f"analysis:{analysis_id}:results",
                f"detection_analysis:{analysis_id}"
            ]
            
            for alt_key in alternative_keys:
                cached_data = await cache_manager.get_from_cache_async(alt_key, 'json')
                if cached_data is not None:
                    logger.info(f"Retrieved detection results from alternative cache {alt_key} for analysis {analysis_id}")
                    return cached_data
                    
            logger.warning(f"No cached detection results found for analysis {analysis_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached detection results for analysis {analysis_id}: {str(e)}")
            return None
    
    @staticmethod
    async def cache_detection_result(analysis_id: Union[str, UUID], detection_data: Dict[str, Any], ttl: int = 3600) -> bool:
        """
        Cache detection results for future export retrieval.
        
        Args:
            analysis_id: Analysis identifier
            detection_data: Detection results to cache
            ttl: Time to live in seconds
            
        Returns:
            bool: Success status
        """
        try:
            cache_key = get_detection_results_cache_key(analysis_id)
            
            # Store as pickle for complex objects
            success = await cache_manager.set_to_cache_async(cache_key, detection_data, ttl, 'pickle')
            
            # Also store as JSON for fallback
            await cache_manager.set_to_cache_async(f"detection_result:{analysis_id}", detection_data, ttl, 'json')
            
            if success:
                logger.info(f"Cached detection results for analysis {analysis_id} with TTL {ttl}s")
                
            return success
            
        except Exception as e:
            logger.error(f"Error caching detection results for analysis {analysis_id}: {str(e)}")
            return False


# Monkey patch the original CacheManager to include detection results methods
async def get_cached_detection_result(self, analysis_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
    """Monkey patch method for cache manager"""
    return await DetectionResultsCacheManager.get_cached_detection_result(analysis_id)


async def cache_detection_result(self, analysis_id: Union[str, UUID], detection_data: Dict[str, Any], ttl: int = 3600) -> bool:
    """Monkey patch method for cache manager"""
    return await DetectionResultsCacheManager.cache_detection_result(analysis_id, detection_data, ttl)


# Add methods to CacheManager instance
cache_manager.get_cached_detection_result = get_cached_detection_result.__get__(cache_manager, CacheManager)
cache_manager.cache_detection_result = cache_detection_result.__get__(cache_manager, CacheManager)


# ============================================================================
# Heatmap-specific cache functions (Work Order #29)
# ============================================================================

def get_cache_manager_heatmap_key(analysis_id: Union[str, UUID], frame_number: int, grid_size: str, color_scheme: str) -> str:
    """Generate cache key for heatmap data (Work Order #29)"""
    return cache_manager._generate_cache_key('heatmap', str(analysis_id), f'frame_{frame_number}', grid_size, color_scheme)


class HeatmapCacheManager(CacheManager):
    """Extended cache manager functionality for heatmap data (Work Order #29)"""
    
    @staticmethod
    async def get_cached_heatmap_data(analysis_id: Union[str, UUID], frame_number: int, grid_size: str, color_scheme: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached heatmap data for specific analysis and frame.
        
        Args:
            analysis_id: Analysis identifier
            frame_number: Frame number
            grid_size: Grid granularity (low, medium, high, ultra)
            color_scheme: Color mapping scheme
            
        Returns:
            Cached heatmap data or None if not found
        """
        try:
            cache_key = get_cache_manager_heatmap_key(analysis_id, frame_number, grid_size, color_scheme)
            
            # Attempt to retrieve from cache
            cached_data = await cache_manager.get_from_cache_async(cache_key, 'json')
            
            if cached_data is not None:
                logger.info(f"Retrieved cached heatmap data for analysis {analysis_id}, frame {frame_number}")
                return cached_data
            
            logger.info(f"No cached heatmap data found for analysis {analysis_id}, frame {frame_number}")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached heatmap data for analysis {analysis_id}, frame {frame_number}: {str(e)}")
            return None
    
    @staticmethod
    async def cache_heatmap_data(analysis_id: Union[str, UUID], frame_number: int, grid_size: str, color_scheme: str, heatmap_data: Dict[str, Any], ttl: int = 3600) -> bool:
        """
        Cache heatmap data for specific analysis and frame.
        
        Args:
            analysis_id: Analysis identifier
            frame_number: Frame number
            grid_size: Grid granularity
            color_scheme: Color mapping scheme
            heatmap_data: Heatmap data to cache
            ttl: Time to live in seconds
            
        Returns:
            bool: Success status
        """
        try:
            cache_key = get_cache_manager_heatmap_key(analysis_id, frame_number, grid_size, color_scheme)
            
            # Store as JSON
            success = await cache_manager.set_to_cache_async(cache_key, heatmap_data, ttl, 'json')
            
            if success:
                logger.info(f"Cached heatmap data for analysis {analysis_id}, frame {frame_number} with TTL {ttl}s")
                
            return success
            
        except Exception as e:
            logger.error(f"Error caching heatmap data for analysis {analysis_id}, frame {frame_number}: {str(e)}")
            return False
    
    @staticmethod
    async def invalidate_heatmap_cache_for_analysis(analysis_id: Union[str, UUID]) -> bool:
        """
        Invalidate all heatmap cache entries for a specific analysis.
        
        Args:
            analysis_id: Analysis identifier
            
        Returns:
            bool: Success status
        """
        try:
            # Generate pattern for all heatmap cache keys for this analysis
            pattern = f"{cache_manager._generate_cache_key('heatmap', str(analysis_id), '*')}"
            
            # Get all matching keys
            matching_keys = await cache_manager.get_keys_by_pattern(pattern)
            
            if matching_keys:
                # Delete all matching cache entries
                deleted_count = await cache_manager.delete_multiple_keys(matching_keys)
                logger.info(f"Invalidated {deleted_count} heatmap cache entries for analysis {analysis_id}")
                return True
            else:
                logger.info(f"No heatmap cache entries found to invalidate for analysis {analysis_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error invalidating heatmap cache for analysis {analysis_id}: {str(e)}")
            return False
    
    @staticmethod
    async def invalidate_heatmap_cache_for_frame(analysis_id: Union[str, UUID], frame_number: int) -> bool:
        """
        Invalidate all heatmap cache entries for a specific analysis frame across all grid sizes and color schemes.
        
        Args:
            analysis_id: Analysis identifier
            frame_number: Frame number
            
        Returns:
            bool: Success status
        """
        try:
            # Generate pattern for heatmap cache keys for this analysis and frame
            pattern = f"{cache_manager._generate_cache_key('heatmap', str(analysis_id), f'frame_{frame_number}', '*')}"
            
            # Get all matching keys
            matching_keys = await cache_manager.get_keys_by_pattern(pattern)
            
            if matching_keys:
                # Delete all matching cache entries
                deleted_count = await cache_manager.delete_multiple_keys(matching_keys)
                logger.info(f"Invalidated {deleted_count} heatmap cache entries for analysis {analysis_id}, frame {frame_number}")
                return True
            else:
                logger.info(f"No heatmap cache entries found to invalidate for analysis {analysis_id}, frame {frame_number}")
                return True
                
        except Exception as e:
            logger.error(f"Error invalidating heatmap cache for analysis {analysis_id}, frame {frame_number}: {str(e)}")
            return False


# Monkey patch methods for heatmap functionality (Work Order #29)
async def get_cached_heatmap_data_monkey_patch(self, analysis_id: Union[str, UUID], frame_number: int, grid_size: str, color_scheme: str) -> Optional[Dict[str, Any]]:
    """Monkey patch method for heatmap cache manager"""
    return await HeatmapCacheManager.get_cached_heatmap_data(analysis_id, frame_number, grid_size, color_scheme)


async def cache_heatmap_data_monkey_patch(self, analysis_id: Union[str, UUID], frame_number: int, grid_size: str, color_scheme: str, heatmap_data: Dict[str, Any], ttl: int = 3600) -> bool:
    """Monkey patch method for heatmap cache manager"""
    return await HeatmapCacheManager.cache_heatmap_data(analysis_id, frame_number, grid_size, color_scheme, heatmap_data, ttl)


async def invalidate_heatmap_cache_monkey_patch(self, analysis_id: Union[str, UUID]) -> bool:
    """Monkey patch method for heatmap cache manager"""
    return await HeatmapCacheManager.invalidate_heatmap_cache_for_analysis(analysis_id)


# Add heatmap methods to CacheManager instance
cache_manager.get_cached_heatmap_data = get_cached_heatmap_data_monkey_patch.__get__(cache_manager, CacheManager)
cache_manager.cache_heatmap_data = cache_heatmap_data_monkey_patch.__get__(cache_manager, CacheManager)
cache_manager.invalidate_heatmap_cache = invalidate_heatmap_cache_monkey_patch.__get__(cache_manager, CacheManager)
