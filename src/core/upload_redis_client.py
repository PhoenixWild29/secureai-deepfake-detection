#!/usr/bin/env python3
"""
Redis Client Configuration for Upload Sessions
Enhanced Redis client with upload session management capabilities
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
import aioredis
from aioredis import Redis, ConnectionPool

from src.core.config import upload_settings

logger = logging.getLogger(__name__)


class UploadSessionRedisClient:
    """
    Enhanced Redis client specifically for upload session management.
    Provides connection pooling, health monitoring, and session-specific operations.
    """
    
    def __init__(self):
        self.pool: Optional[ConnectionPool] = None
        self.redis: Optional[Redis] = None
        self.config = upload_settings
        self._connection_retries = 3
        self._retry_delay = 1
    
    async def initialize(self) -> bool:
        """
        Initialize Redis connection pool and test connection.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Get Redis configuration
            redis_config = self.config.get_redis_config_dict()
            
            # Create connection pool
            self.pool = aioredis.ConnectionPool.from_url(
                f"redis://{redis_config['host']}:{redis_config['port']}/{redis_config['db']}",
                password=redis_config.get('password'),
                decode_responses=redis_config['decode_responses'],
                socket_timeout=redis_config['socket_timeout'],
                socket_connect_timeout=redis_config['socket_connect_timeout'],
                retry_on_timeout=redis_config['retry_on_timeout'],
                max_connections=redis_config['max_connections'],
                health_check_interval=redis_config['health_check_interval']
            )
            
            # Create Redis client
            self.redis = aioredis.Redis(connection_pool=self.pool)
            
            # Test connection
            await self._test_connection()
            
            logger.info("Upload session Redis client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            return False
    
    async def close(self):
        """Close Redis connections and cleanup resources"""
        try:
            if self.redis:
                await self.redis.close()
            if self.pool:
                await self.pool.disconnect()
            logger.info("Redis client closed successfully")
        except Exception as e:
            logger.error(f"Error closing Redis client: {e}")
    
    async def _test_connection(self) -> bool:
        """
        Test Redis connection with retries.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        for attempt in range(self._connection_retries):
            try:
                await self.redis.ping()
                logger.info("Redis connection test successful")
                return True
            except Exception as e:
                logger.warning(f"Redis connection test attempt {attempt + 1} failed: {e}")
                if attempt < self._connection_retries - 1:
                    await asyncio.sleep(self._retry_delay)
        
        raise Exception("Redis connection test failed after all retries")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of Redis connection.
        
        Returns:
            Dict[str, Any]: Health check results
        """
        try:
            # Test basic connectivity
            await self.redis.ping()
            
            # Test basic operations
            test_key = f"{self.config.upload_session.redis_session_prefix}:health_check"
            test_value = "test_value"
            
            # Set and get test
            await self.redis.set(test_key, test_value, ex=10)
            retrieved_value = await self.redis.get(test_key)
            await self.redis.delete(test_key)
            
            # Test hash operations
            hash_key = f"{self.config.upload_session.redis_session_prefix}:health_hash"
            await self.redis.hset(hash_key, "test_field", "test_value")
            await self.redis.hget(hash_key, "test_field")
            await self.redis.delete(hash_key)
            
            # Test set operations
            set_key = f"{self.config.upload_session.redis_session_prefix}:health_set"
            await self.redis.sadd(set_key, "test_member")
            await self.redis.smembers(set_key)
            await self.redis.delete(set_key)
            
            # Get Redis info
            info = await self.redis.info()
            
            return {
                "status": "healthy",
                "connected": True,
                "operations_tested": True,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "uptime": info.get("uptime_in_seconds")
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "connected": False,
                "operations_tested": False,
                "error": str(e)
            }
    
    async def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data from Redis.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Optional[Dict[str, Any]]: Session data or None if not found
        """
        try:
            session_key = f"{self.config.upload_session.redis_session_prefix}:{session_id}"
            data = await self.redis.hgetall(session_key)
            return data if data else None
        except Exception as e:
            logger.error(f"Failed to get session data for {session_id}: {e}")
            return None
    
    async def set_session_data(self, session_id: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Set session data in Redis.
        
        Args:
            session_id: Session identifier
            data: Session data to store
            ttl: Time to live in seconds (uses default if None)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            session_key = f"{self.config.upload_session.redis_session_prefix}:{session_id}"
            ttl = ttl or self.config.upload_session.session_ttl_seconds
            
            await self.redis.hset(session_key, mapping=data)
            await self.redis.expire(session_key, ttl)
            return True
        except Exception as e:
            logger.error(f"Failed to set session data for {session_id}: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session from Redis.
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            session_key = f"{self.config.upload_session.redis_session_prefix}:{session_id}"
            result = await self.redis.delete(session_key)
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def add_user_session(self, user_id: str, session_id: str) -> bool:
        """
        Add session to user's active sessions set.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            user_sessions_key = f"{self.config.upload_session.redis_session_prefix}:user:{user_id}"
            await self.redis.sadd(user_sessions_key, session_id)
            await self.redis.expire(user_sessions_key, self.config.upload_session.session_ttl_seconds)
            return True
        except Exception as e:
            logger.error(f"Failed to add session {session_id} to user {user_id}: {e}")
            return False
    
    async def remove_user_session(self, user_id: str, session_id: str) -> bool:
        """
        Remove session from user's active sessions set.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            user_sessions_key = f"{self.config.upload_session.redis_session_prefix}:user:{user_id}"
            result = await self.redis.srem(user_sessions_key, session_id)
            return result > 0
        except Exception as e:
            logger.error(f"Failed to remove session {session_id} from user {user_id}: {e}")
            return False
    
    async def get_user_sessions(self, user_id: str) -> List[str]:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List[str]: List of session IDs
        """
        try:
            user_sessions_key = f"{self.config.upload_session.redis_session_prefix}:user:{user_id}"
            sessions = await self.redis.smembers(user_sessions_key)
            return list(sessions) if sessions else []
        except Exception as e:
            logger.error(f"Failed to get sessions for user {user_id}: {e}")
            return []
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions by scanning Redis keys.
        
        Returns:
            int: Number of sessions cleaned up
        """
        try:
            pattern = f"{self.config.upload_session.redis_session_prefix}:*"
            keys = await self.redis.keys(pattern)
            
            cleaned_count = 0
            for key in keys:
                if ":user:" in key:
                    continue  # Skip user session sets
                
                # Check if session has expired by checking TTL
                ttl = await self.redis.ttl(key)
                if ttl == -1:  # No expiry set
                    await self.redis.delete(key)
                    cleaned_count += 1
                elif ttl == -2:  # Key doesn't exist
                    cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} expired sessions")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    async def get_redis_stats(self) -> Dict[str, Any]:
        """
        Get Redis statistics and performance metrics.
        
        Returns:
            Dict[str, Any]: Redis statistics
        """
        try:
            info = await self.redis.info()
            
            # Get session-related statistics
            session_pattern = f"{self.config.upload_session.redis_session_prefix}:*"
            session_keys = await self.redis.keys(session_pattern)
            
            user_sessions = 0
            active_sessions = 0
            
            for key in session_keys:
                if ":user:" in key:
                    user_sessions += 1
                else:
                    active_sessions += 1
            
            return {
                "redis_info": {
                    "version": info.get("redis_version"),
                    "uptime_seconds": info.get("uptime_in_seconds"),
                    "used_memory": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "total_commands_processed": info.get("total_commands_processed"),
                    "keyspace_hits": info.get("keyspace_hits"),
                    "keyspace_misses": info.get("keyspace_misses")
                },
                "session_stats": {
                    "total_session_keys": len(session_keys),
                    "user_session_sets": user_sessions,
                    "active_sessions": active_sessions,
                    "session_prefix": self.config.upload_session.redis_session_prefix
                },
                "performance": {
                    "hit_rate": self._calculate_hit_rate(info),
                    "memory_efficiency": self._calculate_memory_efficiency(info)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get Redis stats: {e}")
            return {"error": str(e)}
    
    def _calculate_hit_rate(self, info: Dict[str, Any]) -> float:
        """Calculate Redis hit rate percentage"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0
    
    def _calculate_memory_efficiency(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate memory efficiency metrics"""
        used_memory = info.get("used_memory", 0)
        max_memory = info.get("maxmemory", 0)
        
        efficiency = {
            "used_memory_bytes": used_memory,
            "max_memory_bytes": max_memory,
            "memory_usage_percentage": (used_memory / max_memory * 100) if max_memory > 0 else 0,
            "memory_fragmentation_ratio": info.get("mem_fragmentation_ratio", 0)
        }
        
        return efficiency


# Global Redis client instance
upload_redis_client = UploadSessionRedisClient()


# Utility functions for Redis operations
async def initialize_upload_redis() -> bool:
    """Initialize the upload session Redis client"""
    return await upload_redis_client.initialize()


async def close_upload_redis():
    """Close the upload session Redis client"""
    await upload_redis_client.close()


async def get_upload_redis_client() -> UploadSessionRedisClient:
    """Get the upload session Redis client instance"""
    if not upload_redis_client.redis:
        await upload_redis_client.initialize()
    return upload_redis_client
