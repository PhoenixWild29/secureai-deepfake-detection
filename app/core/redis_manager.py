#!/usr/bin/env python3
"""
Redis Manager for WebSocket Pub/Sub Operations
Centralized Redis connection management and pub/sub operations for real-time updates
"""

import os
import logging
import asyncio
import json
from typing import Dict, Any, Optional, Callable, Set
from datetime import datetime, timezone
import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError, ConnectionError, TimeoutError

logger = logging.getLogger(__name__)


class RedisManager:
    """
    Redis manager for WebSocket pub/sub operations.
    Handles connection management, channel subscriptions, and message publishing.
    """
    
    def __init__(
        self,
        host: str = "localhost",
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
        Initialize Redis manager.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            decode_responses: Whether to decode responses
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connection timeout in seconds
            retry_on_timeout: Whether to retry on timeout
            health_check_interval: Health check interval in seconds
        """
        self.host = host or os.getenv('REDIS_HOST', 'localhost')
        self.port = port or int(os.getenv('REDIS_PORT', 6379))
        self.db = db or int(os.getenv('REDIS_DB', 0))
        self.password = password or os.getenv('REDIS_PASSWORD')
        self.decode_responses = decode_responses
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        self.health_check_interval = health_check_interval
        
        # Connection pools
        self._pub_pool: Optional[redis.ConnectionPool] = None
        self._sub_pool: Optional[redis.ConnectionPool] = None
        
        # Active connections
        self._pub_client: Optional[Redis] = None
        self._sub_client: Optional[Redis] = None
        
        # Subscription management
        self._active_subscriptions: Set[str] = set()
        self._subscription_callbacks: Dict[str, Callable] = {}
        
        # Health monitoring
        self._is_healthy = False
        self._last_health_check = None
        
        logger.info(f"Redis manager initialized: {self.host}:{self.port}/{self.db}")
    
    async def connect(self) -> bool:
        """
        Establish Redis connections.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Create connection pools
            self._pub_pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=self.decode_responses,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                retry_on_timeout=self.retry_on_timeout,
                max_connections=10
            )
            
            self._sub_pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=self.decode_responses,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                retry_on_timeout=self.retry_on_timeout,
                max_connections=5
            )
            
            # Create clients
            self._pub_client = Redis(connection_pool=self._pub_pool)
            self._sub_client = Redis(connection_pool=self._sub_pool)
            
            # Test connections
            await self._pub_client.ping()
            await self._sub_client.ping()
            
            self._is_healthy = True
            self._last_health_check = datetime.now(timezone.utc)
            
            logger.info("Redis connections established successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self._is_healthy = False
            await self.disconnect()
            return False
    
    async def disconnect(self):
        """Disconnect from Redis."""
        try:
            # Close all subscriptions
            await self.unsubscribe_all()
            
            # Close clients
            if self._pub_client:
                await self._pub_client.close()
                self._pub_client = None
            
            if self._sub_client:
                await self._sub_client.close()
                self._sub_client = None
            
            # Close pools
            if self._pub_pool:
                await self._pub_pool.disconnect()
                self._pub_pool = None
            
            if self._sub_pool:
                await self._sub_pool.disconnect()
                self._sub_pool = None
            
            self._is_healthy = False
            logger.info("Redis connections closed")
            
        except Exception as e:
            logger.error(f"Error disconnecting from Redis: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Redis connections.
        
        Returns:
            Health status information
        """
        try:
            if not self._pub_client or not self._sub_client:
                return {
                    'status': 'unhealthy',
                    'reason': 'No active connections',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Test publisher connection
            await self._pub_client.ping()
            
            # Test subscriber connection
            await self._sub_client.ping()
            
            # Get Redis info
            info = await self._pub_client.info()
            
            self._is_healthy = True
            self._last_health_check = datetime.now(timezone.utc)
            
            return {
                'status': 'healthy',
                'redis_version': info.get('redis_version', 'unknown'),
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory_human', 'unknown'),
                'active_subscriptions': len(self._active_subscriptions),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self._is_healthy = False
            logger.error(f"Redis health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def publish_message(
        self,
        channel: str,
        message: Dict[str, Any],
        expire_seconds: Optional[int] = None
    ) -> bool:
        """
        Publish message to Redis channel.
        
        Args:
            channel: Redis channel name
            message: Message data to publish
            expire_seconds: Optional message expiration
            
        Returns:
            True if published successfully, False otherwise
        """
        try:
            if not self._pub_client:
                logger.error("No publisher client available")
                return False
            
            # Serialize message
            message_json = json.dumps(message, default=str)
            
            # Publish message
            subscribers = await self._pub_client.publish(channel, message_json)
            
            # Set expiration if specified
            if expire_seconds:
                await self._pub_client.expire(f"message:{channel}:{datetime.now().timestamp()}", expire_seconds)
            
            logger.debug(f"Published message to channel '{channel}' to {subscribers} subscribers")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message to channel '{channel}': {str(e)}")
            return False
    
    async def subscribe_to_channel(
        self,
        channel: str,
        callback: Callable[[str, Dict[str, Any]], None]
    ) -> bool:
        """
        Subscribe to Redis channel with callback.
        
        Args:
            channel: Redis channel name
            callback: Callback function for received messages
            
        Returns:
            True if subscribed successfully, False otherwise
        """
        try:
            if not self._sub_client:
                logger.error("No subscriber client available")
                return False
            
            # Add to active subscriptions
            self._active_subscriptions.add(channel)
            self._subscription_callbacks[channel] = callback
            
            # Subscribe to channel
            pubsub = self._sub_client.pubsub()
            await pubsub.subscribe(channel)
            
            # Start message processing task
            asyncio.create_task(self._process_messages(pubsub, channel))
            
            logger.info(f"Subscribed to channel '{channel}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to channel '{channel}': {str(e)}")
            return False
    
    async def unsubscribe_from_channel(self, channel: str) -> bool:
        """
        Unsubscribe from Redis channel.
        
        Args:
            channel: Redis channel name
            
        Returns:
            True if unsubscribed successfully, False otherwise
        """
        try:
            if channel not in self._active_subscriptions:
                logger.warning(f"Not subscribed to channel '{channel}'")
                return True
            
            # Remove from active subscriptions
            self._active_subscriptions.discard(channel)
            self._subscription_callbacks.pop(channel, None)
            
            logger.info(f"Unsubscribed from channel '{channel}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from channel '{channel}': {str(e)}")
            return False
    
    async def unsubscribe_all(self) -> bool:
        """
        Unsubscribe from all channels.
        
        Returns:
            True if unsubscribed successfully, False otherwise
        """
        try:
            channels_to_unsubscribe = list(self._active_subscriptions)
            
            for channel in channels_to_unsubscribe:
                await self.unsubscribe_from_channel(channel)
            
            logger.info(f"Unsubscribed from {len(channels_to_unsubscribe)} channels")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from all channels: {str(e)}")
            return False
    
    async def _process_messages(self, pubsub, channel: str):
        """
        Process messages from Redis pub/sub.
        
        Args:
            pubsub: Redis pub/sub object
            channel: Channel name
        """
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        # Parse message data
                        message_data = json.loads(message['data'])
                        
                        # Call registered callback
                        if channel in self._subscription_callbacks:
                            callback = self._subscription_callbacks[channel]
                            callback(channel, message_data)
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse message from channel '{channel}': {str(e)}")
                    except Exception as e:
                        logger.error(f"Error processing message from channel '{channel}': {str(e)}")
                        
        except Exception as e:
            logger.error(f"Error in message processing for channel '{channel}': {str(e)}")
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception as e:
                logger.error(f"Error closing pubsub for channel '{channel}': {str(e)}")
    
    def get_analysis_channel(self, analysis_id: str) -> str:
        """
        Get Redis channel name for analysis updates.
        
        Args:
            analysis_id: Analysis ID
            
        Returns:
            Channel name
        """
        return f"analysis:{analysis_id}"
    
    def get_system_channel(self) -> str:
        """
        Get Redis channel name for system-wide updates.
        
        Returns:
            Channel name
        """
        return "system:updates"
    
    def get_user_channel(self, user_id: str) -> str:
        """
        Get Redis channel name for user-specific updates.
        
        Args:
            user_id: User ID
            
        Returns:
            Channel name
        """
        return f"user:{user_id}"
    
    @property
    def is_healthy(self) -> bool:
        """Check if Redis connections are healthy."""
        return self._is_healthy
    
    @property
    def active_subscriptions(self) -> Set[str]:
        """Get set of active subscription channels."""
        return self._active_subscriptions.copy()


# Global Redis manager instance
redis_manager = RedisManager()


# Utility functions for easy access
async def publish_analysis_update(
    analysis_id: str,
    event_data: Dict[str, Any]
) -> bool:
    """Publish analysis update to Redis channel."""
    channel = redis_manager.get_analysis_channel(analysis_id)
    return await redis_manager.publish_message(channel, event_data)


async def subscribe_to_analysis_updates(
    analysis_id: str,
    callback: Callable[[str, Dict[str, Any]], None]
) -> bool:
    """Subscribe to analysis updates from Redis channel."""
    channel = redis_manager.get_analysis_channel(analysis_id)
    return await redis_manager.subscribe_to_channel(channel, callback)


async def publish_system_update(event_data: Dict[str, Any]) -> bool:
    """Publish system-wide update to Redis channel."""
    channel = redis_manager.get_system_channel()
    return await redis_manager.publish_message(channel, event_data)


async def publish_user_update(
    user_id: str,
    event_data: Dict[str, Any]
) -> bool:
    """Publish user-specific update to Redis channel."""
    channel = redis_manager.get_user_channel(user_id)
    return await redis_manager.publish_message(channel, event_data)


# Export
__all__ = [
    'RedisManager',
    'redis_manager',
    'publish_analysis_update',
    'subscribe_to_analysis_updates',
    'publish_system_update',
    'publish_user_update'
]
