#!/usr/bin/env python3
"""
Redis Publisher for Real-Time Notifications
Enhanced Redis client and utility functions for publishing notification events with client targeting.
Extends existing Redis pub/sub patterns for efficient multi-client distribution.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from uuid import UUID
from datetime import datetime, timezone

from src.notifications.schemas import (
    NotificationEvent,
    NotificationEventType,
    NotificationPriority,
    StatusUpdateNotification,
    ResultUpdateNotification,
    StageTransitionNotification,
    ErrorNotification,
    CompletionNotification,
    HeartbeatNotification
)
from src.services.redis_pubsub_service import RedisPubSubService, get_redis_pubsub_service

logger = logging.getLogger(__name__)


class NotificationRedisPublisher:
    """
    Enhanced Redis publisher for notification events with client targeting and authorization.
    Extends existing Redis pub/sub service for comprehensive notification distribution.
    """
    
    def __init__(self, redis_pubsub_service: Optional[RedisPubSubService] = None):
        """
        Initialize notification Redis publisher.
        
        Args:
            redis_pubsub_service: Optional Redis pub/sub service instance
        """
        self.redis_pubsub = redis_pubsub_service or get_redis_pubsub_service()
        self.notification_channels = {
            NotificationEventType.STATUS_UPDATE: "notifications:status_updates",
            NotificationEventType.RESULT_UPDATE: "notifications:result_updates",
            NotificationEventType.STAGE_TRANSITION: "notifications:stage_transitions",
            NotificationEventType.ERROR_NOTIFICATION: "notifications:errors",
            NotificationEventType.COMPLETION_NOTIFICATION: "notifications:completions",
            NotificationEventType.HEARTBEAT: "notifications:heartbeats"
        }
        self.client_channels = {}  # client_id -> set of subscribed channels
        self.analysis_channels = {}  # analysis_id -> set of subscribed clients
        
    async def publish_notification(
        self,
        notification: NotificationEvent,
        target_clients: Optional[List[str]] = None,
        target_analysis: Optional[UUID] = None
    ) -> bool:
        """
        Publish a notification event to Redis channels.
        
        Args:
            notification: Notification event to publish
            target_clients: Specific client IDs to target (None for broadcast)
            target_analysis: Specific analysis ID to target
            
        Returns:
            bool: True if successful
        """
        try:
            # Get the appropriate channel for the notification type
            channel = self.notification_channels.get(notification.event_type)
            if not channel:
                logger.error(f"No channel configured for event type: {notification.event_type}")
                return False
            
            # Serialize notification data
            notification_data = notification.dict()
            notification_json = json.dumps(notification_data, default=str)
            
            # Determine target channels
            target_channels = []
            
            if target_clients:
                # Target specific clients
                for client_id in target_clients:
                    client_channel = f"{channel}:client:{client_id}"
                    target_channels.append(client_channel)
            elif target_analysis:
                # Target clients subscribed to specific analysis
                analysis_channel = f"{channel}:analysis:{target_analysis}"
                target_channels.append(analysis_channel)
            else:
                # Broadcast to all clients
                target_channels.append(channel)
            
            # Publish to all target channels
            publish_tasks = []
            for target_channel in target_channels:
                task = self._publish_to_channel(target_channel, notification_json, notification)
                publish_tasks.append(task)
            
            # Also broadcast to clients if needed
            if notification.metadata.broadcast_to_all:
                await self._broadcast_to_clients(notification, target_clients)
            
            # Wait for all publications to complete
            results = await asyncio.gather(*publish_tasks, return_exceptions=True)
            
            # Check for any failures
            failed_channels = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_channels.append(target_channels[i])
                    logger.error(f"Failed to publish to channel {target_channels[i]}: {result}")
                elif not result:
                    failed_channels.append(target_channels[i])
            
            if failed_channels:
                logger.warning(f"Failed to publish to {len(failed_channels)} channels: {failed_channels}")
                return len(failed_channels) < len(target_channels)  # Success if at least one succeeded
            
            logger.debug(f"Successfully published {notification.event_type} notification to {len(target_channels)} channels")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing notification: {e}")
            return False
    
    async def _publish_to_channel(
        self,
        channel: str,
        data: str,
        notification: NotificationEvent
    ) -> bool:
        """
        Publish data to a specific Redis channel.
        
        Args:
            channel: Redis channel name
            data: Serialized notification data
            notification: Notification event object
            
        Returns:
            bool: True if successful
        """
        try:
            # Use the existing Redis pub/sub service
            await self.redis_pubsub.publish_analysis_event(
                channel=channel,
                event_type=notification.event_type.value,
                data=data,
                analysis_id=getattr(notification, 'analysis_id', None)
            )
            
            # Update metadata with delivery information
            if hasattr(notification, 'metadata'):
                notification.metadata.delivery_status = "delivered"
                notification.metadata.retry_count = 0
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish to channel {channel}: {e}")
            return False
    
    async def _broadcast_to_clients(
        self,
        notification: NotificationEvent,
        target_clients: Optional[List[str]] = None
    ) -> bool:
        """
        Broadcast notification directly to clients.
        
        Args:
            notification: Notification event to broadcast
            target_clients: Specific client IDs to target
            
        Returns:
            bool: True if successful
        """
        try:
            # This would integrate with the WebSocket manager for direct client broadcasting
            # For now, we'll just log the broadcast attempt
            logger.debug(f"Broadcasting {notification.event_type} to clients: {target_clients or 'all'}")
            return True
            
        except Exception as e:
            logger.error(f"Error broadcasting to clients: {e}")
            return False
    
    async def publish_status_update(
        self,
        notification: StatusUpdateNotification,
        target_clients: Optional[List[str]] = None
    ) -> bool:
        """
        Publish a status update notification.
        
        Args:
            notification: Status update notification
            target_clients: Specific client IDs to target
            
        Returns:
            bool: True if successful
        """
        return await self.publish_notification(notification, target_clients)
    
    async def publish_result_update(
        self,
        notification: ResultUpdateNotification,
        target_clients: Optional[List[str]] = None
    ) -> bool:
        """
        Publish a result update notification.
        
        Args:
            notification: Result update notification
            target_clients: Specific client IDs to target
            
        Returns:
            bool: True if successful
        """
        return await self.publish_notification(notification, target_clients)
    
    async def publish_stage_transition(
        self,
        notification: StageTransitionNotification,
        target_clients: Optional[List[str]] = None
    ) -> bool:
        """
        Publish a stage transition notification.
        
        Args:
            notification: Stage transition notification
            target_clients: Specific client IDs to target
            
        Returns:
            bool: True if successful
        """
        return await self.publish_notification(notification, target_clients)
    
    async def publish_error_notification(
        self,
        notification: ErrorNotification,
        target_clients: Optional[List[str]] = None
    ) -> bool:
        """
        Publish an error notification.
        
        Args:
            notification: Error notification
            target_clients: Specific client IDs to target
            
        Returns:
            bool: True if successful
        """
        # Error notifications should be high priority and broadcast to all
        notification.metadata.priority = NotificationPriority.HIGH
        notification.metadata.broadcast_to_all = True
        return await self.publish_notification(notification, target_clients)
    
    async def publish_completion_notification(
        self,
        notification: CompletionNotification,
        target_clients: Optional[List[str]] = None
    ) -> bool:
        """
        Publish a completion notification.
        
        Args:
            notification: Completion notification
            target_clients: Specific client IDs to target
            
        Returns:
            bool: True if successful
        """
        return await self.publish_notification(notification, target_clients)
    
    async def publish_heartbeat(
        self,
        notification: HeartbeatNotification,
        target_clients: Optional[List[str]] = None
    ) -> bool:
        """
        Publish a heartbeat notification.
        
        Args:
            notification: Heartbeat notification
            target_clients: Specific client IDs to target
            
        Returns:
            bool: True if successful
        """
        return await self.publish_notification(notification, target_clients)
    
    async def subscribe_client_to_analysis(
        self,
        client_id: str,
        analysis_id: UUID,
        event_types: Optional[List[NotificationEventType]] = None
    ) -> bool:
        """
        Subscribe a client to notifications for a specific analysis.
        
        Args:
            client_id: Client identifier
            analysis_id: Analysis identifier
            event_types: Specific event types to subscribe to (None for all)
            
        Returns:
            bool: True if successful
        """
        try:
            if event_types is None:
                event_types = list(NotificationEventType)
            
            subscribed_channels = []
            for event_type in event_types:
                base_channel = self.notification_channels.get(event_type)
                if base_channel:
                    analysis_channel = f"{base_channel}:analysis:{analysis_id}"
                    subscribed_channels.append(analysis_channel)
            
            # Update client subscription tracking
            if client_id not in self.client_channels:
                self.client_channels[client_id] = set()
            
            for channel in subscribed_channels:
                self.client_channels[client_id].add(channel)
            
            # Update analysis subscription tracking
            analysis_key = str(analysis_id)
            if analysis_key not in self.analysis_channels:
                self.analysis_channels[analysis_key] = set()
            self.analysis_channels[analysis_key].add(client_id)
            
            logger.info(f"Client {client_id} subscribed to analysis {analysis_id} for {len(event_types)} event types")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing client {client_id} to analysis {analysis_id}: {e}")
            return False
    
    async def unsubscribe_client_from_analysis(
        self,
        client_id: str,
        analysis_id: UUID
    ) -> bool:
        """
        Unsubscribe a client from notifications for a specific analysis.
        
        Args:
            client_id: Client identifier
            analysis_id: Analysis identifier
            
        Returns:
            bool: True if successful
        """
        try:
            # Remove from client subscription tracking
            if client_id in self.client_channels:
                analysis_key = str(analysis_id)
                channels_to_remove = []
                for channel in self.client_channels[client_id]:
                    if f":analysis:{analysis_key}" in channel:
                        channels_to_remove.append(channel)
                
                for channel in channels_to_remove:
                    self.client_channels[client_id].remove(channel)
            
            # Remove from analysis subscription tracking
            analysis_key = str(analysis_id)
            if analysis_key in self.analysis_channels:
                self.analysis_channels[analysis_key].discard(client_id)
                if not self.analysis_channels[analysis_key]:
                    del self.analysis_channels[analysis_key]
            
            logger.info(f"Client {client_id} unsubscribed from analysis {analysis_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error unsubscribing client {client_id} from analysis {analysis_id}: {e}")
            return False
    
    async def get_client_subscriptions(self, client_id: str) -> List[str]:
        """
        Get all channels a client is subscribed to.
        
        Args:
            client_id: Client identifier
            
        Returns:
            List[str]: List of subscribed channels
        """
        return list(self.client_channels.get(client_id, set()))
    
    async def get_analysis_subscribers(self, analysis_id: UUID) -> List[str]:
        """
        Get all clients subscribed to a specific analysis.
        
        Args:
            analysis_id: Analysis identifier
            
        Returns:
            List[str]: List of subscribed client IDs
        """
        analysis_key = str(analysis_id)
        return list(self.analysis_channels.get(analysis_key, set()))
    
    async def cleanup_client_subscriptions(self, client_id: str) -> bool:
        """
        Clean up all subscriptions for a disconnected client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            bool: True if successful
        """
        try:
            # Remove from all analysis subscriptions
            if client_id in self.client_channels:
                subscribed_channels = list(self.client_channels[client_id])
                
                # Extract analysis IDs from channels
                analysis_ids = set()
                for channel in subscribed_channels:
                    if ":analysis:" in channel:
                        parts = channel.split(":analysis:")
                        if len(parts) > 1:
                            analysis_ids.add(parts[1])
                
                # Remove from analysis tracking
                for analysis_id in analysis_ids:
                    if analysis_id in self.analysis_channels:
                        self.analysis_channels[analysis_id].discard(client_id)
                        if not self.analysis_channels[analysis_id]:
                            del self.analysis_channels[analysis_id]
                
                # Remove from client tracking
                del self.client_channels[client_id]
            
            logger.info(f"Cleaned up subscriptions for client {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up subscriptions for client {client_id}: {e}")
            return False
    
    async def get_notification_stats(self) -> Dict[str, Any]:
        """
        Get statistics about notification distribution.
        
        Returns:
            Dict[str, Any]: Notification statistics
        """
        try:
            stats = {
                "total_clients": len(self.client_channels),
                "total_analyses": len(self.analysis_channels),
                "channels_configured": len(self.notification_channels),
                "client_subscriptions": {
                    client_id: len(channels) 
                    for client_id, channels in self.client_channels.items()
                },
                "analysis_subscribers": {
                    analysis_id: len(clients) 
                    for analysis_id, clients in self.analysis_channels.items()
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting notification stats: {e}")
            return {"error": str(e)}


# Factory function
def get_notification_publisher(redis_pubsub_service: Optional[RedisPubSubService] = None) -> NotificationRedisPublisher:
    """
    Factory function to create NotificationRedisPublisher instance.
    
    Args:
        redis_pubsub_service: Optional Redis pub/sub service instance
        
    Returns:
        NotificationRedisPublisher instance
    """
    return NotificationRedisPublisher(redis_pubsub_service)


# Convenience functions for common operations
async def publish_status_update_notification(
    analysis_id: UUID,
    status: str,
    progress: float,
    message: str,
    target_clients: Optional[List[str]] = None
) -> bool:
    """
    Convenience function to publish a status update notification.
    
    Args:
        analysis_id: Analysis identifier
        status: Current status
        progress: Progress percentage
        message: Status message
        target_clients: Specific client IDs to target
        
    Returns:
        bool: True if successful
    """
    try:
        from src.notifications.schemas import (
            create_status_update_notification,
            DetectionStatus,
            ProcessingStage,
            StageProgressInfo
        )
        
        # Create a basic status update notification
        notification = create_status_update_notification(
            analysis_id=analysis_id,
            status=DetectionStatus(status),
            overall_progress=progress,
            current_stage=ProcessingStage.PROCESSING,
            stage_progress=StageProgressInfo(
                stage_name="processing",
                stage_status="active",
                stage_progress_percentage=progress
            ),
            message=message
        )
        
        # Publish the notification
        publisher = get_notification_publisher()
        return await publisher.publish_status_update(notification, target_clients)
        
    except Exception as e:
        logger.error(f"Error publishing status update notification: {e}")
        return False


async def publish_error_notification_simple(
    analysis_id: UUID,
    error_message: str,
    error_type: str = "processing",
    target_clients: Optional[List[str]] = None
) -> bool:
    """
    Convenience function to publish an error notification.
    
    Args:
        analysis_id: Analysis identifier
        error_message: Error message
        error_type: Error type
        target_clients: Specific client IDs to target
        
    Returns:
        bool: True if successful
    """
    try:
        from src.notifications.schemas import (
            create_error_notification,
            ErrorContext
        )
        
        # Create error context
        error_context = ErrorContext(
            error_type=error_type,
            error_code="UNKNOWN_ERROR",
            error_severity="error",
            context_data={"message": error_message}
        )
        
        # Create error notification
        notification = create_error_notification(
            analysis_id=analysis_id,
            error_context=error_context,
            impact_level="moderate"
        )
        
        # Publish the notification
        publisher = get_notification_publisher()
        return await publisher.publish_error_notification(notification, target_clients)
        
    except Exception as e:
        logger.error(f"Error publishing error notification: {e}")
        return False


# Export all classes and functions
__all__ = [
    'NotificationRedisPublisher',
    'get_notification_publisher',
    'publish_status_update_notification',
    'publish_error_notification_simple'
]