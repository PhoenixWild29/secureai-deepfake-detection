#!/usr/bin/env python3
"""
WebSocket Manager for Real-Time Notifications
Enhanced WebSocket connection manager that handles client connections, disconnections, 
authorization, and real-time notification delivery for status tracking.
Extends existing WebSocket infrastructure for comprehensive notification management.
"""

import json
import logging
import asyncio
from typing import Dict, Set, Optional, List, Any
from uuid import UUID
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from src.services.websocket_service import WebSocketConnectionManager
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
from src.notifications.redis_publisher import get_notification_publisher, NotificationRedisPublisher

logger = logging.getLogger(__name__)


class NotificationWebSocketManager:
    """
    Enhanced WebSocket manager for real-time notification delivery.
    Extends existing WebSocketConnectionManager with notification-specific functionality
    including client authorization, subscription management, and error handling.
    """
    
    def __init__(self, base_manager: Optional[WebSocketConnectionManager] = None):
        """
        Initialize the notification WebSocket manager.
        
        Args:
            base_manager: Optional base WebSocket connection manager
        """
        self.base_manager = base_manager or WebSocketConnectionManager()
        self.notification_publisher = get_notification_publisher()
        
        # Notification-specific tracking
        self.client_notifications: Dict[str, Set[str]] = {}  # client_id -> set of analysis_ids
        self.notification_subscriptions: Dict[str, Set[NotificationEventType]] = {}  # client_id -> set of event_types
        self.authorized_clients: Set[str] = set()  # Set of authorized client IDs
        self.client_permissions: Dict[str, Dict[str, Any]] = {}  # client_id -> permissions
        
        # Performance tracking
        self.notification_stats: Dict[str, Dict[str, Any]] = {}  # client_id -> stats
        self.max_notifications_per_client = 1000  # Rate limiting
        self.notification_rate_limit_window = 60  # seconds
        self.max_connections_per_user = 5
        self.max_connections_total = 1000
        
        # Health monitoring
        self.last_heartbeat: Dict[str, datetime] = {}  # client_id -> last_heartbeat_time
        self.heartbeat_interval = 30  # seconds
        self.connection_timeout = 300  # seconds
    
    async def connect_client(
        self,
        websocket: WebSocket,
        client_id: str,
        user_id: Optional[str] = None,
        permissions: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Connect a client with notification capabilities.
        
        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier
            user_id: Optional user identifier
            permissions: Optional client permissions
            
        Returns:
            bool: True if successful
        """
        try:
            # Connect using base manager
            success = await self.base_manager.connect(websocket, client_id, user_id)
            
            if success:
                # Initialize notification-specific tracking
                self.client_notifications[client_id] = set()
                self.notification_subscriptions[client_id] = set()
                self.notification_stats[client_id] = {
                    "connected_at": datetime.now(timezone.utc),
                    "notifications_sent": 0,
                    "notifications_failed": 0,
                    "last_notification": None,
                    "subscription_count": 0
                }
                
                # Set permissions
                if permissions:
                    self.client_permissions[client_id] = permissions
                else:
                    self.client_permissions[client_id] = {
                        "can_receive_notifications": True,
                        "can_subscribe_to_analyses": True,
                        "max_concurrent_analyses": 10
                    }
                
                # Authorize client
                self.authorized_clients.add(client_id)
                
                # Update heartbeat
                self.last_heartbeat[client_id] = datetime.now(timezone.utc)
                
                logger.info(f"Client {client_id} connected with notification capabilities")
                
                # Send connection established notification
                await self._send_connection_established(client_id)
                
                return True
            else:
                logger.warning(f"Failed to connect client {client_id} via base manager")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting client {client_id}: {e}")
            return False
    
    async def disconnect_client(self, client_id: str) -> bool:
        """
        Disconnect a client and clean up notification subscriptions.
        
        Args:
            client_id: Client identifier
            
        Returns:
            bool: True if successful
        """
        try:
            # Clean up notification subscriptions
            if client_id in self.client_notifications:
                # Unsubscribe from all analyses
                analysis_ids = list(self.client_notifications[client_id])
                for analysis_id in analysis_ids:
                    await self.notification_publisher.unsubscribe_client_from_analysis(
                        client_id, UUID(analysis_id)
                    )
                
                del self.client_notifications[client_id]
            
            # Clean up other tracking
            self.notification_subscriptions.pop(client_id, None)
            self.authorized_clients.discard(client_id)
            self.client_permissions.pop(client_id, None)
            self.notification_stats.pop(client_id, None)
            self.last_heartbeat.pop(client_id, None)
            
            # Disconnect using base manager
            success = await self.base_manager.disconnect(client_id)
            
            if success:
                logger.info(f"Client {client_id} disconnected and cleaned up")
            else:
                logger.warning(f"Failed to disconnect client {client_id} via base manager")
            
            return success
            
        except Exception as e:
            logger.error(f"Error disconnecting client {client_id}: {e}")
            return False
    
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
            event_types: Specific event types to subscribe to
            
        Returns:
            bool: True if successful
        """
        try:
            # Check authorization
            if not self._is_client_authorized(client_id):
                logger.warning(f"Unauthorized client {client_id} attempted to subscribe to analysis {analysis_id}")
                return False
            
            # Check subscription limits
            if not self._check_subscription_limits(client_id):
                logger.warning(f"Client {client_id} exceeded subscription limits")
                return False
            
            # Subscribe via notification publisher
            success = await self.notification_publisher.subscribe_client_to_analysis(
                client_id, analysis_id, event_types
            )
            
            if success:
                # Update local tracking
                self.client_notifications[client_id].add(str(analysis_id))
                if event_types:
                    self.notification_subscriptions[client_id].update(event_types)
                else:
                    # Subscribe to all event types
                    self.notification_subscriptions[client_id].update(NotificationEventType)
                
                # Update stats
                self.notification_stats[client_id]["subscription_count"] = len(self.client_notifications[client_id])
                
                logger.info(f"Client {client_id} subscribed to analysis {analysis_id}")
                return True
            else:
                logger.warning(f"Failed to subscribe client {client_id} to analysis {analysis_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error subscribing client {client_id} to analysis {analysis_id}: {e}")
            return False
    
    async def unsubscribe_client_from_analysis(self, client_id: str, analysis_id: UUID) -> bool:
        """
        Unsubscribe a client from notifications for a specific analysis.
        
        Args:
            client_id: Client identifier
            analysis_id: Analysis identifier
            
        Returns:
            bool: True if successful
        """
        try:
            # Unsubscribe via notification publisher
            success = await self.notification_publisher.unsubscribe_client_from_analysis(
                client_id, analysis_id
            )
            
            if success:
                # Update local tracking
                self.client_notifications[client_id].discard(str(analysis_id))
                self.notification_stats[client_id]["subscription_count"] = len(self.client_notifications[client_id])
                
                logger.info(f"Client {client_id} unsubscribed from analysis {analysis_id}")
                return True
            else:
                logger.warning(f"Failed to unsubscribe client {client_id} from analysis {analysis_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error unsubscribing client {client_id} from analysis {analysis_id}: {e}")
            return False
    
    async def send_notification_to_client(
        self,
        client_id: str,
        notification: NotificationEvent
    ) -> bool:
        """
        Send a notification to a specific client.
        
        Args:
            client_id: Client identifier
            notification: Notification event to send
            
        Returns:
            bool: True if successful
        """
        try:
            # Check if client is authorized and connected
            if not self._is_client_authorized(client_id):
                logger.warning(f"Attempted to send notification to unauthorized client {client_id}")
                return False
            
            if not self._is_client_connected(client_id):
                logger.warning(f"Attempted to send notification to disconnected client {client_id}")
                return False
            
            # Check rate limiting
            if not self._check_rate_limits(client_id):
                logger.warning(f"Client {client_id} exceeded rate limits")
                return False
            
            # Check if client is subscribed to this event type
            if not self._is_client_subscribed_to_event(client_id, notification.event_type):
                logger.debug(f"Client {client_id} not subscribed to event type {notification.event_type}")
                return False
            
            # Serialize notification
            notification_data = notification.dict()
            message = json.dumps(notification_data, default=str)
            
            # Send via base manager
            success = await self.base_manager.send_personal_message(message, client_id)
            
            if success:
                # Update stats
                self.notification_stats[client_id]["notifications_sent"] += 1
                self.notification_stats[client_id]["last_notification"] = datetime.now(timezone.utc)
                
                logger.debug(f"Sent {notification.event_type} notification to client {client_id}")
                return True
            else:
                # Update failure stats
                self.notification_stats[client_id]["notifications_failed"] += 1
                logger.warning(f"Failed to send notification to client {client_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending notification to client {client_id}: {e}")
            return False
    
    async def broadcast_notification(
        self,
        notification: NotificationEvent,
        target_clients: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Broadcast a notification to multiple clients.
        
        Args:
            notification: Notification event to broadcast
            target_clients: Specific client IDs to target (None for all authorized clients)
            
        Returns:
            Dict[str, bool]: Results for each client
        """
        try:
            if target_clients is None:
                target_clients = list(self.authorized_clients)
            
            # Send to each client
            results = {}
            tasks = []
            
            for client_id in target_clients:
                task = self.send_notification_to_client(client_id, notification)
                tasks.append((client_id, task))
            
            # Wait for all sends to complete
            for client_id, task in tasks:
                try:
                    results[client_id] = await task
                except Exception as e:
                    logger.error(f"Error broadcasting to client {client_id}: {e}")
                    results[client_id] = False
            
            successful_sends = sum(1 for success in results.values() if success)
            logger.info(f"Broadcast {notification.event_type} notification to {successful_sends}/{len(target_clients)} clients")
            
            return results
            
        except Exception as e:
            logger.error(f"Error broadcasting notification: {e}")
            return {}
    
    async def send_heartbeat(self, client_id: str) -> bool:
        """
        Send a heartbeat notification to a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            bool: True if successful
        """
        try:
            heartbeat = HeartbeatNotification(
                timestamp=datetime.now(timezone.utc),
                server_id="notification_server",
                active_connections=len(self.authorized_clients),
                system_status="healthy"
            )
            
            return await self.send_notification_to_client(client_id, heartbeat)
            
        except Exception as e:
            logger.error(f"Error sending heartbeat to client {client_id}: {e}")
            return False
    
    async def handle_client_message(
        self,
        client_id: str,
        message: str
    ) -> bool:
        """
        Handle incoming messages from clients.
        
        Args:
            client_id: Client identifier
            message: Message content
            
        Returns:
            bool: True if handled successfully
        """
        try:
            message_data = json.loads(message)
            message_type = message_data.get("type")
            
            if message_type == "ping":
                # Respond with pong
                response = {"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}
                await self.base_manager.send_personal_message(json.dumps(response), client_id)
                return True
                
            elif message_type == "subscribe":
                # Handle subscription request
                analysis_id = message_data.get("analysis_id")
                event_types = message_data.get("event_types")
                
                if analysis_id:
                    event_type_objects = None
                    if event_types:
                        event_type_objects = [NotificationEventType(et) for et in event_types]
                    
                    success = await self.subscribe_client_to_analysis(
                        client_id, UUID(analysis_id), event_type_objects
                    )
                    
                    # Send response
                    response = {
                        "type": "subscription_response",
                        "success": success,
                        "analysis_id": analysis_id
                    }
                    await self.base_manager.send_personal_message(json.dumps(response), client_id)
                    return success
                
            elif message_type == "unsubscribe":
                # Handle unsubscription request
                analysis_id = message_data.get("analysis_id")
                
                if analysis_id:
                    success = await self.unsubscribe_client_from_analysis(client_id, UUID(analysis_id))
                    
                    # Send response
                    response = {
                        "type": "unsubscription_response",
                        "success": success,
                        "analysis_id": analysis_id
                    }
                    await self.base_manager.send_personal_message(json.dumps(response), client_id)
                    return success
            
            elif message_type == "get_stats":
                # Send client statistics
                stats = self.get_client_stats(client_id)
                response = {"type": "stats_response", "stats": stats}
                await self.base_manager.send_personal_message(json.dumps(response), client_id)
                return True
            
            else:
                logger.warning(f"Unknown message type from client {client_id}: {message_type}")
                return False
                
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON message from client {client_id}")
            return False
        except Exception as e:
            logger.error(f"Error handling message from client {client_id}: {e}")
            return False
    
    def _is_client_authorized(self, client_id: str) -> bool:
        """Check if client is authorized to receive notifications."""
        return client_id in self.authorized_clients
    
    def _is_client_connected(self, client_id: str) -> bool:
        """Check if client is still connected."""
        return client_id in self.base_manager.active_connections
    
    def _check_subscription_limits(self, client_id: str) -> bool:
        """Check if client has reached subscription limits."""
        permissions = self.client_permissions.get(client_id, {})
        max_analyses = permissions.get("max_concurrent_analyses", 10)
        current_subscriptions = len(self.client_notifications.get(client_id, set()))
        return current_subscriptions < max_analyses
    
    def _check_rate_limits(self, client_id: str) -> bool:
        """Check if client has exceeded rate limits."""
        stats = self.notification_stats.get(client_id, {})
        notifications_sent = stats.get("notifications_sent", 0)
        return notifications_sent < self.max_notifications_per_client
    
    def _is_client_subscribed_to_event(self, client_id: str, event_type: NotificationEventType) -> bool:
        """Check if client is subscribed to a specific event type."""
        subscribed_types = self.notification_subscriptions.get(client_id, set())
        return event_type in subscribed_types or NotificationEventType.STATUS_UPDATE in subscribed_types
    
    async def _send_connection_established(self, client_id: str):
        """Send connection established notification to client."""
        try:
            from src.notifications.schemas import NotificationMetadata
            
            connection_event = {
                "type": "connection_established",
                "client_id": client_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_capabilities": {
                    "notifications": True,
                    "subscriptions": True,
                    "heartbeat": True
                }
            }
            
            await self.base_manager.send_personal_message(json.dumps(connection_event), client_id)
            
        except Exception as e:
            logger.error(f"Error sending connection established to client {client_id}: {e}")
    
    def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """Get statistics for a specific client."""
        stats = self.notification_stats.get(client_id, {})
        return {
            "client_id": client_id,
            "connected": client_id in self.authorized_clients,
            "subscriptions": len(self.client_notifications.get(client_id, set())),
            "notifications_sent": stats.get("notifications_sent", 0),
            "notifications_failed": stats.get("notifications_failed", 0),
            "connected_at": stats.get("connected_at"),
            "last_notification": stats.get("last_notification"),
            "last_heartbeat": self.last_heartbeat.get(client_id)
        }
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get overall manager statistics."""
        return {
            "total_clients": len(self.authorized_clients),
            "total_subscriptions": sum(len(subs) for subs in self.client_notifications.values()),
            "total_notifications_sent": sum(stats.get("notifications_sent", 0) for stats in self.notification_stats.values()),
            "total_notifications_failed": sum(stats.get("notifications_failed", 0) for stats in self.notification_stats.values()),
            "active_connections": len(self.base_manager.active_connections),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Factory function
def get_notification_websocket_manager(
    base_manager: Optional[WebSocketConnectionManager] = None
) -> NotificationWebSocketManager:
    """
    Factory function to create NotificationWebSocketManager instance.
    
    Args:
        base_manager: Optional base WebSocket connection manager
        
    Returns:
        NotificationWebSocketManager instance
    """
    return NotificationWebSocketManager(base_manager)


# Export all classes and functions
__all__ = [
    'NotificationWebSocketManager',
    'get_notification_websocket_manager'
]