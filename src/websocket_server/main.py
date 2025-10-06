#!/usr/bin/env python3
"""
WebSocket Server Integration for Real-Time Notifications
Main WebSocket server component that integrates notification manager, Redis pub/sub,
and real-time broadcasting for comprehensive status tracking notifications.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.websockets import WebSocketState

from src.notifications.websocket_manager import get_notification_websocket_manager, NotificationWebSocketManager
from src.notifications.redis_publisher import get_notification_publisher, NotificationRedisPublisher
from src.notifications.event_processor import get_status_event_processor, StatusEventProcessor
from src.notifications.schemas import (
    NotificationEvent,
    NotificationEventType,
    StatusUpdateNotification,
    ResultUpdateNotification,
    StageTransitionNotification,
    ErrorNotification,
    CompletionNotification,
    HeartbeatNotification
)
from src.services.redis_pubsub_service import get_redis_pubsub_service, RedisPubSubService

logger = logging.getLogger(__name__)


class NotificationWebSocketServer:
    """
    Main WebSocket server for real-time notification delivery.
    Integrates WebSocket connection management, Redis pub/sub, and event processing
    to provide comprehensive status tracking notifications.
    """
    
    def __init__(self):
        """Initialize the notification WebSocket server."""
        self.websocket_manager = get_notification_websocket_manager()
        self.notification_publisher = get_notification_publisher()
        self.event_processor = get_status_event_processor(self.notification_publisher)
        self.redis_pubsub = get_redis_pubsub_service()
        
        # Server state
        self.running = False
        self.redis_subscription_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.heartbeat_interval = 30  # seconds
        self.cleanup_interval = 60  # seconds
        self.connection_timeout = 300  # seconds
        
        # Statistics
        self.server_stats = {
            "started_at": None,
            "total_connections": 0,
            "active_connections": 0,
            "total_notifications_sent": 0,
            "total_errors": 0,
            "redis_subscriptions_active": 0
        }
    
    async def start_server(self):
        """Start the notification WebSocket server."""
        if self.running:
            logger.warning("Notification WebSocket server is already running")
            return
        
        try:
            self.running = True
            self.server_stats["started_at"] = datetime.now(timezone.utc)
            
            # Start Redis subscription task
            self.redis_subscription_task = asyncio.create_task(self._redis_subscription_loop())
            
            # Start heartbeat task
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # Start cleanup task
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            logger.info("Notification WebSocket server started successfully")
            
        except Exception as e:
            logger.error(f"Error starting notification WebSocket server: {e}")
            await self.stop_server()
            raise
    
    async def stop_server(self):
        """Stop the notification WebSocket server."""
        if not self.running:
            return
        
        try:
            self.running = False
            
            # Cancel all tasks
            tasks = [self.redis_subscription_task, self.heartbeat_task, self.cleanup_task]
            for task in tasks:
                if task and not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # Disconnect all clients
            await self._disconnect_all_clients()
            
            logger.info("Notification WebSocket server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping notification WebSocket server: {e}")
    
    async def handle_websocket_connection(
        self,
        websocket: WebSocket,
        client_id: str,
        user_id: Optional[str] = None,
        permissions: Optional[Dict[str, Any]] = None
    ):
        """
        Handle a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier
            user_id: Optional user identifier
            permissions: Optional client permissions
        """
        try:
            # Accept WebSocket connection
            await websocket.accept()
            
            # Authenticate client first
            auth_context = await self._authenticate_client(client_id, user_id, permissions)
            if not auth_context:
                await websocket.close(code=1008, reason="Authentication failed")
                return
            
            # Connect client with notification capabilities
            success = await self.websocket_manager.connect_client(
                websocket, client_id, user_id, permissions
            )
            
            if not success:
                await websocket.close(code=1008, reason="Connection failed")
                return
            
            # Update server stats
            self.server_stats["total_connections"] += 1
            self.server_stats["active_connections"] = len(self.websocket_manager.authorized_clients)
            
            logger.info(f"WebSocket connection established for client {client_id}")
            
            # Handle client messages
            await self._handle_client_messages(websocket, client_id)
            
        except WebSocketDisconnect:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error handling WebSocket connection for client {client_id}: {e}")
        finally:
            # Clean up client connection
            await self.websocket_manager.disconnect_client(client_id)
            self.server_stats["active_connections"] = len(self.websocket_manager.authorized_clients)
    
    async def _handle_client_messages(self, websocket: WebSocket, client_id: str):
        """Handle incoming messages from a client."""
        try:
            while websocket.client_state == WebSocketState.CONNECTED:
                # Receive message
                message = await websocket.receive_text()
                
                # Handle message
                await self.websocket_manager.handle_client_message(client_id, message)
                
        except WebSocketDisconnect:
            logger.debug(f"Client {client_id} disconnected during message handling")
        except Exception as e:
            logger.error(f"Error handling messages for client {client_id}: {e}")
    
    async def _redis_subscription_loop(self):
        """Main Redis subscription loop for receiving notification events."""
        try:
            logger.info("Starting Redis subscription loop")
            
            # Subscribe to all notification channels
            channels = [
                "notifications:status_updates",
                "notifications:result_updates",
                "notifications:stage_transitions",
                "notifications:errors",
                "notifications:completions",
                "notifications:heartbeats"
            ]
            
            for channel in channels:
                await self.redis_pubsub.subscribe_to_analysis(channel, self._handle_redis_notification)
            
            self.server_stats["redis_subscriptions_active"] = len(channels)
            
            # Keep the subscription active
            while self.running:
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info("Redis subscription loop cancelled")
        except Exception as e:
            logger.error(f"Error in Redis subscription loop: {e}")
            self.server_stats["total_errors"] += 1
    
    async def _handle_redis_notification(self, channel: str, data: str):
        """
        Handle incoming Redis notification events.
        
        Args:
            channel: Redis channel name
            data: Serialized notification data
        """
        try:
            # Parse notification data
            notification_data = json.loads(data)
            event_type = notification_data.get("event_type")
            
            if not event_type:
                logger.warning(f"Received notification without event_type from channel {channel}")
                return
            
            # Create notification object based on event type
            notification = self._create_notification_from_data(notification_data, event_type)
            
            if not notification:
                logger.warning(f"Failed to create notification for event_type {event_type}")
                return
            
            # Broadcast notification to relevant clients
            await self._broadcast_notification(notification, channel)
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in Redis notification from channel {channel}: {e}")
            self.server_stats["total_errors"] += 1
        except Exception as e:
            logger.error(f"Error handling Redis notification from channel {channel}: {e}")
            self.server_stats["total_errors"] += 1
    
    def _create_notification_from_data(
        self,
        notification_data: Dict[str, Any],
        event_type: str
    ) -> Optional[NotificationEvent]:
        """Create a notification object from parsed data."""
        try:
            if event_type == NotificationEventType.STATUS_UPDATE.value:
                return StatusUpdateNotification(**notification_data)
            elif event_type == NotificationEventType.RESULT_UPDATE.value:
                return ResultUpdateNotification(**notification_data)
            elif event_type == NotificationEventType.STAGE_TRANSITION.value:
                return StageTransitionNotification(**notification_data)
            elif event_type == NotificationEventType.ERROR_NOTIFICATION.value:
                return ErrorNotification(**notification_data)
            elif event_type == NotificationEventType.COMPLETION_NOTIFICATION.value:
                return CompletionNotification(**notification_data)
            elif event_type == NotificationEventType.HEARTBEAT.value:
                return HeartbeatNotification(**notification_data)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating notification for event_type {event_type}: {e}")
            return None
    
    async def _broadcast_notification(
        self,
        notification: NotificationEvent,
        channel: str
    ):
        """Broadcast notification to relevant clients."""
        try:
            # Determine target clients based on channel and notification
            target_clients = None
            
            # Check if this is a targeted notification
            if hasattr(notification, 'metadata') and notification.metadata.target_clients:
                target_clients = notification.metadata.target_clients
            
            # Check if this is an analysis-specific notification
            elif hasattr(notification, 'analysis_id'):
                # Get clients subscribed to this analysis
                analysis_subscribers = await self.notification_publisher.get_analysis_subscribers(
                    notification.analysis_id
                )
                target_clients = analysis_subscribers
            
            # Broadcast to clients
            results = await self.websocket_manager.broadcast_notification(
                notification, target_clients
            )
            
            # Update stats
            successful_sends = sum(1 for success in results.values() if success)
            self.server_stats["total_notifications_sent"] += successful_sends
            
            logger.debug(f"Broadcasted {notification.event_type} to {successful_sends}/{len(results)} clients")
            
        except Exception as e:
            logger.error(f"Error broadcasting notification: {e}")
            self.server_stats["total_errors"] += 1
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat notifications to all connected clients."""
        try:
            while self.running:
                await asyncio.sleep(self.heartbeat_interval)
                
                if not self.running:
                    break
                
                # Send heartbeat to all connected clients
                active_clients = list(self.websocket_manager.authorized_clients)
                
                for client_id in active_clients:
                    try:
                        await self.websocket_manager.send_heartbeat(client_id)
                    except Exception as e:
                        logger.error(f"Error sending heartbeat to client {client_id}: {e}")
                
                logger.debug(f"Sent heartbeat to {len(active_clients)} clients")
                
        except asyncio.CancelledError:
            logger.info("Heartbeat loop cancelled")
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}")
            self.server_stats["total_errors"] += 1
    
    async def _cleanup_loop(self):
        """Periodic cleanup of disconnected clients and expired data."""
        try:
            while self.running:
                await asyncio.sleep(self.cleanup_interval)
                
                if not self.running:
                    break
                
                # Clean up disconnected clients
                await self._cleanup_disconnected_clients()
                
                logger.debug("Completed periodic cleanup")
                
        except asyncio.CancelledError:
            logger.info("Cleanup loop cancelled")
        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}")
            self.server_stats["total_errors"] += 1
    
    async def _cleanup_disconnected_clients(self):
        """Clean up clients that have disconnected."""
        try:
            active_clients = list(self.websocket_manager.authorized_clients)
            disconnected_clients = []
            
            for client_id in active_clients:
                if not self.websocket_manager._is_client_connected(client_id):
                    disconnected_clients.append(client_id)
            
            # Clean up disconnected clients
            for client_id in disconnected_clients:
                await self.websocket_manager.disconnect_client(client_id)
                logger.info(f"Cleaned up disconnected client {client_id}")
            
            if disconnected_clients:
                logger.info(f"Cleaned up {len(disconnected_clients)} disconnected clients")
                
        except Exception as e:
            logger.error(f"Error cleaning up disconnected clients: {e}")
    
    async def _disconnect_all_clients(self):
        """Disconnect all connected clients."""
        try:
            active_clients = list(self.websocket_manager.authorized_clients)
            
            for client_id in active_clients:
                await self.websocket_manager.disconnect_client(client_id)
            
            logger.info(f"Disconnected {len(active_clients)} clients")
            
        except Exception as e:
            logger.error(f"Error disconnecting all clients: {e}")
    
    async def _authenticate_client(
        self,
        client_id: str,
        user_id: Optional[str],
        permissions: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Authenticate a WebSocket client.
        
        Args:
            client_id: Client identifier
            user_id: User identifier
            permissions: Client permissions
            
        Returns:
            bool: True if authenticated
        """
        try:
            # In a real implementation, this would integrate with the authentication system
            # For now, we'll simulate authentication
            if user_id:
                logger.info(f"Client {client_id} authenticated as user {user_id}")
                return True
            else:
                logger.warning(f"Client {client_id} authentication failed - no user ID")
                return False
                
        except Exception as e:
            logger.error(f"Error authenticating client {client_id}: {e}")
            return False
    
    async def get_server_stats(self) -> Dict[str, Any]:
        """Get comprehensive server statistics."""
        try:
            websocket_stats = self.websocket_manager.get_manager_stats()
            notification_stats = await self.notification_publisher.get_notification_stats()
            processor_stats = await self.event_processor.get_processor_stats()
            
            combined_stats = {
                "server": self.server_stats,
                "websocket_manager": websocket_stats,
                "notification_publisher": notification_stats,
                "event_processor": processor_stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return combined_stats
            
        except Exception as e:
            logger.error(f"Error getting server stats: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the notification server."""
        try:
            health_status = {
                "status": "healthy",
                "running": self.running,
                "active_connections": len(self.websocket_manager.authorized_clients),
                "redis_subscriptions_active": self.server_stats["redis_subscriptions_active"],
                "total_errors": self.server_stats["total_errors"],
                "uptime_seconds": None,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Calculate uptime
            if self.server_stats["started_at"]:
                uptime = (datetime.now(timezone.utc) - self.server_stats["started_at"]).total_seconds()
                health_status["uptime_seconds"] = uptime
            
            # Check for issues
            if self.server_stats["total_errors"] > 100:
                health_status["status"] = "warning"
                health_status["warning"] = "High error count detected"
            
            if not self.running:
                health_status["status"] = "unhealthy"
                health_status["error"] = "Server is not running"
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


# Global server instance
_notification_server: Optional[NotificationWebSocketServer] = None


def get_notification_server() -> NotificationWebSocketServer:
    """Get the global notification server instance."""
    global _notification_server
    if _notification_server is None:
        _notification_server = NotificationWebSocketServer()
    return _notification_server


async def start_notification_server():
    """Start the global notification server."""
    server = get_notification_server()
    await server.start_server()


async def stop_notification_server():
    """Stop the global notification server."""
    server = get_notification_server()
    await server.stop_server()


# Export all classes and functions
__all__ = [
    'NotificationWebSocketServer',
    'get_notification_server',
    'start_notification_server',
    'stop_notification_server'
]