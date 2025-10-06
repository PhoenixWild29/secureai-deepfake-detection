#!/usr/bin/env python3
"""
Redis Client for Caching and Pub/Sub
Utility module for Redis operations including caching embeddings and real-time progress updates
"""

import json
import hashlib
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
import redis
import redis.asyncio as aioredis
from redis.exceptions import RedisError, ConnectionError, TimeoutError

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis client for caching and pub/sub operations.
    Handles embedding cache, progress updates, and real-time notifications.
    """
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        retry_on_timeout: bool = True,
        health_check_interval: int = 30
    ):
        """
        Initialize Redis client.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            decode_responses: Whether to decode responses
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connect timeout in seconds
            retry_on_timeout: Whether to retry on timeout
            health_check_interval: Health check interval in seconds
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        
        # Connection pool configuration
        self.pool_config = {
            'host': host,
            'port': port,
            'db': db,
            'password': password,
            'decode_responses': decode_responses,
            'socket_timeout': socket_timeout,
            'socket_connect_timeout': socket_connect_timeout,
            'retry_on_timeout': retry_on_timeout,
            'health_check_interval': health_check_interval,
            'max_connections': 20
        }
        
        # Initialize connection pools
        self._sync_pool = None
        self._async_pool = None
        
        # Cache key prefixes
        self.EMBEDDING_PREFIX = 'embed'
        self.ANALYSIS_PREFIX = 'analysis'
        self.PROGRESS_PREFIX = 'progress'
        self.RESULT_PREFIX = 'result'
        self.METRICS_PREFIX = 'metrics'
        
    def _get_sync_client(self) -> redis.Redis:
        """Get synchronous Redis client."""
        if self._sync_pool is None:
            self._sync_pool = redis.ConnectionPool(**self.pool_config)
        return redis.Redis(connection_pool=self._sync_pool)
    
    def _get_async_client(self) -> aioredis.Redis:
        """Get asynchronous Redis client."""
        if self._async_pool is None:
            self._async_pool = aioredis.ConnectionPool(**self.pool_config)
        return aioredis.Redis(connection_pool=self._async_pool)
    
    def _generate_cache_key(self, prefix: str, identifier: str) -> str:
        """
        Generate cache key with prefix and identifier.
        
        Args:
            prefix: Key prefix
            identifier: Unique identifier
            
        Returns:
            Generated cache key
        """
        return f"{prefix}:{identifier}"
    
    def _generate_video_hash(self, video_path: str) -> str:
        """
        Generate hash for video path.
        
        Args:
            video_path: Path to video file
            
        Returns:
            SHA256 hash of video path
        """
        return hashlib.sha256(video_path.encode('utf-8')).hexdigest()
    
    # Embedding Cache Operations
    
    def get_embedding_cache_key(self, video_path: str) -> str:
        """
        Get embedding cache key for video.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Cache key for embeddings
        """
        video_hash = self._generate_video_hash(video_path)
        return self._generate_cache_key(self.EMBEDDING_PREFIX, video_hash)
    
    def get_cached_embeddings(self, video_path: str) -> Optional[Dict[str, Any]]:
        """
        Get cached embeddings for video.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Cached embeddings or None if not found
        """
        try:
            client = self._get_sync_client()
            cache_key = self.get_embedding_cache_key(video_path)
            
            cached_data = client.get(cache_key)
            if cached_data:
                embeddings = json.loads(cached_data)
                logger.info(f"Cache hit for embeddings: {video_path}")
                return embeddings
            else:
                logger.info(f"Cache miss for embeddings: {video_path}")
                return None
                
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error retrieving cached embeddings: {str(e)}")
            return None
    
    async def get_cached_embeddings_async(self, video_path: str) -> Optional[Dict[str, Any]]:
        """
        Get cached embeddings for video (async).
        
        Args:
            video_path: Path to video file
            
        Returns:
            Cached embeddings or None if not found
        """
        try:
            client = self._get_async_client()
            cache_key = self.get_embedding_cache_key(video_path)
            
            cached_data = await client.get(cache_key)
            if cached_data:
                embeddings = json.loads(cached_data)
                logger.info(f"Cache hit for embeddings: {video_path}")
                return embeddings
            else:
                logger.info(f"Cache miss for embeddings: {video_path}")
                return None
                
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error retrieving cached embeddings: {str(e)}")
            return None
    
    def cache_embeddings(
        self,
        video_path: str,
        embeddings: Dict[str, Any],
        ttl: int = 86400  # 24 hours
    ) -> bool:
        """
        Cache embeddings for video.
        
        Args:
            video_path: Path to video file
            embeddings: Embeddings data to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_sync_client()
            cache_key = self.get_embedding_cache_key(video_path)
            
            # Add metadata to embeddings
            embeddings_with_metadata = {
                'embeddings': embeddings,
                'cached_at': datetime.now(timezone.utc).isoformat(),
                'video_path': video_path,
                'ttl': ttl
            }
            
            client.setex(cache_key, ttl, json.dumps(embeddings_with_metadata))
            logger.info(f"Cached embeddings for: {video_path}")
            return True
            
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Error caching embeddings: {str(e)}")
            return False
    
    async def cache_embeddings_async(
        self,
        video_path: str,
        embeddings: Dict[str, Any],
        ttl: int = 86400  # 24 hours
    ) -> bool:
        """
        Cache embeddings for video (async).
        
        Args:
            video_path: Path to video file
            embeddings: Embeddings data to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_async_client()
            cache_key = self.get_embedding_cache_key(video_path)
            
            # Add metadata to embeddings
            embeddings_with_metadata = {
                'embeddings': embeddings,
                'cached_at': datetime.now(timezone.utc).isoformat(),
                'video_path': video_path,
                'ttl': ttl
            }
            
            await client.setex(cache_key, ttl, json.dumps(embeddings_with_metadata))
            logger.info(f"Cached embeddings for: {video_path}")
            return True
            
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Error caching embeddings: {str(e)}")
            return False
    
    # Progress Updates and Pub/Sub
    
    def publish_progress_update(
        self,
        analysis_id: str,
        progress_data: Dict[str, Any]
    ) -> bool:
        """
        Publish progress update to Redis pub/sub.
        
        Args:
            analysis_id: Analysis ID
            progress_data: Progress data to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_sync_client()
            channel = self._generate_cache_key(self.ANALYSIS_PREFIX, analysis_id)
            
            # Add timestamp to progress data
            progress_data['timestamp'] = datetime.now(timezone.utc).isoformat()
            progress_data['analysis_id'] = analysis_id
            
            client.publish(channel, json.dumps(progress_data))
            logger.debug(f"Published progress update for analysis: {analysis_id}")
            return True
            
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Error publishing progress update: {str(e)}")
            return False
    
    async def publish_progress_update_async(
        self,
        analysis_id: str,
        progress_data: Dict[str, Any]
    ) -> bool:
        """
        Publish progress update to Redis pub/sub (async).
        
        Args:
            analysis_id: Analysis ID
            progress_data: Progress data to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_async_client()
            channel = self._generate_cache_key(self.ANALYSIS_PREFIX, analysis_id)
            
            # Add timestamp to progress data
            progress_data['timestamp'] = datetime.now(timezone.utc).isoformat()
            progress_data['analysis_id'] = analysis_id
            
            await client.publish(channel, json.dumps(progress_data))
            logger.debug(f"Published progress update for analysis: {analysis_id}")
            return True
            
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Error publishing progress update: {str(e)}")
            return False
    
    def publish_completion_update(
        self,
        analysis_id: str,
        result_data: Dict[str, Any]
    ) -> bool:
        """
        Publish completion update to Redis pub/sub.
        
        Args:
            analysis_id: Analysis ID
            result_data: Result data to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_sync_client()
            channel = self._generate_cache_key(self.ANALYSIS_PREFIX, analysis_id)
            
            # Add completion metadata
            completion_data = {
                'type': 'completion',
                'analysis_id': analysis_id,
                'result': result_data,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': 'completed'
            }
            
            client.publish(channel, json.dumps(completion_data))
            logger.info(f"Published completion update for analysis: {analysis_id}")
            return True
            
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Error publishing completion update: {str(e)}")
            return False
    
    def publish_error_update(
        self,
        analysis_id: str,
        error_data: Dict[str, Any]
    ) -> bool:
        """
        Publish error update to Redis pub/sub.
        
        Args:
            analysis_id: Analysis ID
            error_data: Error data to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_sync_client()
            channel = self._generate_cache_key(self.ANALYSIS_PREFIX, analysis_id)
            
            # Add error metadata
            error_update = {
                'type': 'error',
                'analysis_id': analysis_id,
                'error': error_data,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': 'failed'
            }
            
            client.publish(channel, json.dumps(error_update))
            logger.error(f"Published error update for analysis: {analysis_id}")
            return True
            
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Error publishing error update: {str(e)}")
            return False
    
    # Result Caching
    
    def cache_result(
        self,
        analysis_id: str,
        result_data: Dict[str, Any],
        ttl: int = 3600  # 1 hour
    ) -> bool:
        """
        Cache analysis result.
        
        Args:
            analysis_id: Analysis ID
            result_data: Result data to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_sync_client()
            cache_key = self._generate_cache_key(self.RESULT_PREFIX, analysis_id)
            
            # Add metadata to result
            result_with_metadata = {
                'result': result_data,
                'cached_at': datetime.now(timezone.utc).isoformat(),
                'analysis_id': analysis_id,
                'ttl': ttl
            }
            
            client.setex(cache_key, ttl, json.dumps(result_with_metadata))
            logger.info(f"Cached result for analysis: {analysis_id}")
            return True
            
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Error caching result: {str(e)}")
            return False
    
    def get_cached_result(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached analysis result.
        
        Args:
            analysis_id: Analysis ID
            
        Returns:
            Cached result or None if not found
        """
        try:
            client = self._get_sync_client()
            cache_key = self._generate_cache_key(self.RESULT_PREFIX, analysis_id)
            
            cached_data = client.get(cache_key)
            if cached_data:
                result_data = json.loads(cached_data)
                logger.info(f"Cache hit for result: {analysis_id}")
                return result_data
            else:
                logger.info(f"Cache miss for result: {analysis_id}")
                return None
                
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error retrieving cached result: {str(e)}")
            return None
    
    # Metrics and Monitoring
    
    def store_metrics(
        self,
        analysis_id: str,
        metrics: Dict[str, Any],
        ttl: int = 86400  # 24 hours
    ) -> bool:
        """
        Store processing metrics.
        
        Args:
            analysis_id: Analysis ID
            metrics: Metrics data to store
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_sync_client()
            cache_key = self._generate_cache_key(self.METRICS_PREFIX, analysis_id)
            
            # Add timestamp to metrics
            metrics_with_timestamp = {
                'metrics': metrics,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'analysis_id': analysis_id
            }
            
            client.setex(cache_key, ttl, json.dumps(metrics_with_timestamp))
            logger.debug(f"Stored metrics for analysis: {analysis_id}")
            return True
            
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Error storing metrics: {str(e)}")
            return False
    
    # Health Check
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Redis connection health.
        
        Returns:
            Health status information
        """
        try:
            client = self._get_sync_client()
            
            # Test basic operations
            test_key = 'health_check_test'
            test_value = 'ok'
            
            client.set(test_key, test_value, ex=10)
            retrieved_value = client.get(test_key)
            client.delete(test_key)
            
            if retrieved_value == test_value:
                return {
                    'status': 'healthy',
                    'host': self.host,
                    'port': self.port,
                    'db': self.db,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            else:
                return {
                    'status': 'unhealthy',
                    'error': 'Data integrity check failed',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    # Cleanup Operations
    
    def cleanup_expired_keys(self, pattern: str = '*') -> int:
        """
        Clean up expired keys matching pattern.
        
        Args:
            pattern: Key pattern to match
            
        Returns:
            Number of keys cleaned up
        """
        try:
            client = self._get_sync_client()
            
            # Get all keys matching pattern
            keys = client.keys(pattern)
            cleaned_count = 0
            
            for key in keys:
                if client.ttl(key) == -1:  # Key exists but has no expiration
                    continue
                elif client.ttl(key) == -2:  # Key has expired
                    client.delete(key)
                    cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} expired keys")
            return cleaned_count
            
        except RedisError as e:
            logger.error(f"Error cleaning up expired keys: {str(e)}")
            return 0


# Global Redis client instance
redis_client = RedisClient()


# Utility functions for easy access
def get_embedding_cache_key(video_path: str) -> str:
    """Get embedding cache key for video."""
    return redis_client.get_embedding_cache_key(video_path)


def get_cached_embeddings(video_path: str) -> Optional[Dict[str, Any]]:
    """Get cached embeddings for video."""
    return redis_client.get_cached_embeddings(video_path)


def cache_embeddings(video_path: str, embeddings: Dict[str, Any], ttl: int = 86400) -> bool:
    """Cache embeddings for video."""
    return redis_client.cache_embeddings(video_path, embeddings, ttl)


def publish_progress_update(analysis_id: str, progress_data: Dict[str, Any]) -> bool:
    """Publish progress update to Redis pub/sub."""
    return redis_client.publish_progress_update(analysis_id, progress_data)


def publish_completion_update(analysis_id: str, result_data: Dict[str, Any]) -> bool:
    """Publish completion update to Redis pub/sub."""
    return redis_client.publish_completion_update(analysis_id, result_data)


def publish_error_update(analysis_id: str, error_data: Dict[str, Any]) -> bool:
    """Publish error update to Redis pub/sub."""
    return redis_client.publish_error_update(analysis_id, error_data)


# Export
__all__ = [
    'RedisClient',
    'redis_client',
    'get_embedding_cache_key',
    'get_cached_embeddings',
    'cache_embeddings',
    'publish_progress_update',
    'publish_completion_update',
    'publish_error_update'
]
