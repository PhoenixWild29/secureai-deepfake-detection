# Caching Configuration for Performance Optimization
# Redis-based caching for API responses and computed data

import os
import json
import hashlib
from functools import wraps
from typing import Optional, Callable, Any
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0)),
        decode_responses=True
    )
    # Test connection
    redis_client.ping()
    logger.info("✅ Redis cache connected")
except (ImportError, redis.ConnectionError, Exception) as e:
    REDIS_AVAILABLE = False
    redis_client = None
    logger.warning(f"Redis not available, caching disabled: {e}")


def cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate cache key from arguments"""
    key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
    key_hash = hashlib.md5(key_data.encode()).hexdigest()
    return f"cache:{prefix}:{key_hash}"


def cached(ttl: int = 300, key_prefix: str = None):
    """
    Decorator to cache function results
    
    Args:
        ttl: Time to live in seconds (default: 5 minutes)
        key_prefix: Prefix for cache key (default: function name)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not REDIS_AVAILABLE:
                return func(*args, **kwargs)
            
            # Generate cache key
            prefix = key_prefix or func.__name__
            cache_key_str = cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            try:
                cached_value = redis_client.get(cache_key_str)
                if cached_value:
                    logger.debug(f"Cache hit: {cache_key_str}")
                    return json.loads(cached_value)
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
            
            # Cache miss - execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            try:
                redis_client.setex(
                    cache_key_str,
                    ttl,
                    json.dumps(result, default=str)
                )
                logger.debug(f"Cache set: {cache_key_str} (TTL: {ttl}s)")
            except Exception as e:
                logger.warning(f"Cache write error: {e}")
            
            return result
        return wrapper
    return decorator


def invalidate_cache(pattern: str):
    """Invalidate cache entries matching pattern"""
    if not REDIS_AVAILABLE:
        return
    
    try:
        keys = redis_client.keys(f"cache:{pattern}*")
        if keys:
            redis_client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache entries matching {pattern}")
    except Exception as e:
        logger.warning(f"Cache invalidation error: {e}")


def get_cache_stats() -> dict:
    """Get cache statistics"""
    if not REDIS_AVAILABLE:
        return {'available': False}
    
    try:
        info = redis_client.info('stats')
        return {
            'available': True,
            'keys': redis_client.dbsize(),
            'hits': info.get('keyspace_hits', 0),
            'misses': info.get('keyspace_misses', 0),
        }
    except Exception as e:
        logger.warning(f"Cache stats error: {e}")
        return {'available': False, 'error': str(e)}

