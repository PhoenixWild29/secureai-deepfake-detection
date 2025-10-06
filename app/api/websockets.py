#!/usr/bin/env python3
"""
WebSocket Real-Time Analysis Updates
FastAPI WebSocket endpoint for real-time analysis progress updates
"""

import os
import logging
import asyncio
import json
import uuid
from typing import Dict, Any, Optional, Set
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Path
from fastapi.websockets import WebSocketState

from app.models.analysis_events import (
    StatusUpdate, ResultUpdate, ErrorEvent, HeartbeatEvent,
    EventType, AnalysisStage, create_heartbeat_event
)
from app.core.redis_manager import redis_manager, subscribe_to_analysis_updates
from app.dependencies.auth import authenticate_websocket_connection, WebSocketAuthError

logger = logging.getLogger(__name__)

# Create router for WebSocket endpoints
router = APIRouter()

# Connection management
class ConnectionManager:
    """
    Manages WebSocket connections and their subscriptions.
    """
    
    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
        self.heartbeat_timeouts: Dict[WebSocket, asyncio.Task] = {}
        
        logger.info("WebSocket connection manager initialized")
    
    async def connect(self, websocket: WebSocket, analysis_id: str, user_id: Optional[str] = None):
        """
        Connect WebSocket to analysis updates.
        
        Args:
            websocket: WebSocket connection
            analysis_id: Analysis ID
            user_id: User ID (optional)
        """
        try:
            # Accept WebSocket connection
            await websocket.accept()
            
            # Store connection info
            connection_info = {
                'analysis_id': analysis_id,
                'user_id': user_id,
                'connected_at': datetime.now(timezone.utc),
                'last_heartbeat': datetime.now(timezone.utc),
                'is_active': True
            }
            self.connection_info[websocket] = connection_info
            
            # Add to active connections
            if analysis_id not in self.active_connections:
                self.active_connections[analysis_id] = set()
            self.active_connections[analysis_id].add(websocket)
            
            # Start heartbeat monitoring
            self.heartbeat_timeouts[websocket] = asyncio.create_task(
                self._monitor_heartbeat(websocket)
            )
            
            # Subscribe to Redis channel
            await self._subscribe_to_analysis_updates(analysis_id)
            
            logger.info(f"WebSocket connected for analysis {analysis_id}, user {user_id}")
            
            # Send welcome message
            await self._send_welcome_message(websocket, analysis_id)
            
        except Exception as e:
            logger.error(f"Error connecting WebSocket: {str(e)}")
            await self.disconnect(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        """
        Disconnect WebSocket and cleanup resources.
        
        Args:
            websocket: WebSocket connection
        """
        try:
            # Get connection info
            connection_info = self.connection_info.get(websocket, {})
            analysis_id = connection_info.get('analysis_id')
            
            # Remove from active connections
            if analysis_id and analysis_id in self.active_connections:
                self.active_connections[analysis_id].discard(websocket)
                
                # Clean up empty analysis groups
                if not self.active_connections[analysis_id]:
                    del self.active_connections[analysis_id]
                    await self._unsubscribe_from_analysis_updates(analysis_id)
            
            # Cancel heartbeat monitoring
            if websocket in self.heartbeat_timeouts:
                self.heartbeat_timeouts[websocket].cancel()
                del self.heartbeat_timeouts[websocket]
            
            # Remove connection info
            if websocket in self.connection_info:
                del self.connection_info[websocket]
            
            # Close WebSocket if still connected
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close()
            
            logger.info(f"WebSocket disconnected for analysis {analysis_id}")
            
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {str(e)}")
    
    async def send_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """
        Send message to WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            message: Message to send
        """
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps(message, default=str))
                logger.debug(f"Message sent to WebSocket: {message.get('event_type', 'unknown')}")
            else:
                logger.warning("Attempted to send message to disconnected WebSocket")
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {str(e)}")
    
    async def broadcast_to_analysis(self, analysis_id: str, message: Dict[str, Any]):
        """
        Broadcast message to all connections for an analysis.
        
        Args:
            analysis_id: Analysis ID
            message: Message to broadcast
        """
        try:
            if analysis_id not in self.active_connections:
                return
            
            connections = self.active_connections[analysis_id].copy()
            for websocket in connections:
                await self.send_message(websocket, message)
            
            logger.debug(f"Broadcasted message to {len(connections)} connections for analysis {analysis_id}")
            
        except Exception as e:
            logger.error(f"Error broadcasting message to analysis {analysis_id}: {str(e)}")
    
    async def _subscribe_to_analysis_updates(self, analysis_id: str):
        """
        Subscribe to Redis updates for analysis.
        
        Args:
            analysis_id: Analysis ID
        """
        try:
            await subscribe_to_analysis_updates(
                analysis_id,
                lambda channel, data: asyncio.create_task(
                    self._handle_redis_message(analysis_id, data)
                )
            )
            logger.debug(f"Subscribed to Redis updates for analysis {analysis_id}")
        except Exception as e:
            logger.error(f"Error subscribing to Redis updates for analysis {analysis_id}: {str(e)}")
    
    async def _unsubscribe_from_analysis_updates(self, analysis_id: str):
        """
        Unsubscribe from Redis updates for analysis.
        
        Args:
            analysis_id: Analysis ID
        """
        try:
            await redis_manager.unsubscribe_from_channel(
                redis_manager.get_analysis_channel(analysis_id)
            )
            logger.debug(f"Unsubscribed from Redis updates for analysis {analysis_id}")
        except Exception as e:
            logger.error(f"Error unsubscribing from Redis updates for analysis {analysis_id}: {str(e)}")
    
    async def _handle_redis_message(self, analysis_id: str, data: Dict[str, Any]):
        """
        Handle incoming Redis message.
        
        Args:
            analysis_id: Analysis ID
            data: Message data
        """
        try:
            await self.broadcast_to_analysis(analysis_id, data)
        except Exception as e:
            logger.error(f"Error handling Redis message for analysis {analysis_id}: {str(e)}")
    
    async def _send_welcome_message(self, websocket: WebSocket, analysis_id: str):
        """
        Send welcome message to new connection.
        
        Args:
            websocket: WebSocket connection
            analysis_id: Analysis ID
        """
        try:
            welcome_message = {
                'event_type': 'connection_established',
                'analysis_id': analysis_id,
                'message': 'Connected to real-time analysis updates',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            await self.send_message(websocket, welcome_message)
        except Exception as e:
            logger.error(f"Error sending welcome message: {str(e)}")
    
    async def _monitor_heartbeat(self, websocket: WebSocket):
        """
        Monitor WebSocket heartbeat and close if timeout.
        
        Args:
            websocket: WebSocket connection
        """
        try:
            while websocket.client_state == WebSocketState.CONNECTED:
                await asyncio.sleep(30)  # 30-second timeout
                
                connection_info = self.connection_info.get(websocket, {})
                last_heartbeat = connection_info.get('last_heartbeat')
                
                if last_heartbeat:
                    time_since_heartbeat = datetime.now(timezone.utc) - last_heartbeat
                    if time_since_heartbeat > timedelta(seconds=30):
                        logger.warning("WebSocket heartbeat timeout, closing connection")
                        await self.disconnect(websocket)
                        break
                        
        except asyncio.CancelledError:
            logger.debug("Heartbeat monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in heartbeat monitoring: {str(e)}")
    
    def update_heartbeat(self, websocket: WebSocket):
        """
        Update heartbeat timestamp for WebSocket.
        
        Args:
            websocket: WebSocket connection
        """
        if websocket in self.connection_info:
            self.connection_info[websocket]['last_heartbeat'] = datetime.now(timezone.utc)


# Global connection manager
connection_manager = ConnectionManager()


@router.websocket("/ws/analysis/{analysis_id}")
async def websocket_analysis_updates(
    websocket: WebSocket,
    analysis_id: str = Path(..., description="Analysis ID for real-time updates")
):
    """
    WebSocket endpoint for real-time analysis updates.
    
    This endpoint:
    - Authenticates WebSocket connections using JWT tokens
    - Subscribes to Redis pub/sub channel for analysis updates
    - Forwards structured status and result updates to clients
    - Handles client heartbeat messages and connection health
    - Properly cleans up Redis subscriptions on disconnect
    
    Args:
        websocket: WebSocket connection
        analysis_id: Analysis ID for updates
        
    Raises:
        WebSocketDisconnect: When client disconnects
        WebSocketAuthError: When authentication fails (closes with code 4001)
    """
    try:
        logger.info(f"WebSocket connection attempt for analysis {analysis_id}")
        
        # Authenticate WebSocket connection
        try:
            auth_result = await authenticate_websocket_connection(websocket)
            user_id = auth_result.get('user_id')
            logger.info(f"WebSocket authenticated for user {user_id}")
        except WebSocketAuthError as e:
            logger.warning(f"WebSocket authentication failed: {str(e)}")
            # Connection already closed with code 4001
            return
        
        # Connect to analysis updates
        await connection_manager.connect(websocket, analysis_id, user_id)
        
        # Handle incoming messages
        try:
            while websocket.client_state == WebSocketState.CONNECTED:
                # Receive message from client
                message_text = await websocket.receive_text()
                
                try:
                    # Parse message
                    message_data = json.loads(message_text)
                    message_type = message_data.get('type', '').lower()
                    
                    if message_type == 'ping':
                        # Handle heartbeat
                        connection_manager.update_heartbeat(websocket)
                        
                        # Send pong response
                        heartbeat_event = create_heartbeat_event("pong")
                        await connection_manager.send_message(websocket, heartbeat_event.dict())
                        
                        logger.debug("Heartbeat received and responded")
                    
                    elif message_type == 'subscribe':
                        # Handle subscription request (if needed)
                        logger.debug("Subscription request received")
                    
                    else:
                        logger.warning(f"Unknown message type received: {message_type}")
                        
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON message received")
                except Exception as e:
                    logger.error(f"Error processing client message: {str(e)}")
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for analysis {analysis_id}")
        except Exception as e:
            logger.error(f"Error in WebSocket message handling: {str(e)}")
        finally:
            # Cleanup on disconnect
            await connection_manager.disconnect(websocket)
            
    except Exception as e:
        logger.error(f"Unexpected error in WebSocket endpoint: {str(e)}")
        try:
            await connection_manager.disconnect(websocket)
        except:
            pass


@router.get("/ws/health")
async def websocket_health_check():
    """
    Health check endpoint for WebSocket service.
    
    Returns:
        Health status information
    """
    try:
        # Check Redis connection
        redis_health = await redis_manager.health_check()
        
        # Get connection statistics
        total_connections = sum(len(connections) for connections in connection_manager.active_connections.values())
        active_analyses = len(connection_manager.active_connections)
        
        return {
            'status': 'healthy' if redis_health['status'] == 'healthy' else 'unhealthy',
            'redis': redis_health,
            'websocket_stats': {
                'total_connections': total_connections,
                'active_analyses': active_analyses,
                'connection_manager_healthy': True
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"WebSocket health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


# Utility functions for external use
async def send_status_update(
    analysis_id: str,
    task_id: str,
    progress: float,
    current_stage: AnalysisStage,
    message: str,
    estimated_completion: Optional[datetime] = None,
    error: Optional[str] = None
):
    """
    Send status update to all connected clients for an analysis.
    
    Args:
        analysis_id: Analysis ID
        task_id: Celery task ID
        progress: Progress percentage (0.0-1.0)
        current_stage: Current processing stage
        message: Status message
        estimated_completion: Estimated completion time
        error: Error message if any
    """
    try:
        status_update = StatusUpdate(
            task_id=task_id,
            analysis_id=analysis_id,
            progress=progress,
            current_stage=current_stage,
            message=message,
            estimated_completion=estimated_completion,
            error=error
        )
        
        await connection_manager.broadcast_to_analysis(analysis_id, status_update.dict())
        
        # Also publish to Redis for persistence
        await redis_manager.publish_message(
            redis_manager.get_analysis_channel(analysis_id),
            status_update.dict()
        )
        
        logger.debug(f"Status update sent for analysis {analysis_id}: {current_stage}")
        
    except Exception as e:
        logger.error(f"Error sending status update: {str(e)}")


async def send_result_update(
    analysis_id: str,
    confidence_score: float,
    frames_processed: int,
    total_frames: int,
    suspicious_regions: list = None,
    blockchain_hash: Optional[str] = None,
    processing_time_ms: int = 0,
    is_fake: bool = False
):
    """
    Send result update to all connected clients for an analysis.
    
    Args:
        analysis_id: Analysis ID
        confidence_score: Overall confidence score
        frames_processed: Number of frames processed
        total_frames: Total frames in video
        suspicious_regions: Detected suspicious regions
        blockchain_hash: Blockchain verification hash
        processing_time_ms: Total processing time in milliseconds
        is_fake: Whether video is detected as fake
    """
    try:
        result_update = ResultUpdate(
            analysis_id=analysis_id,
            confidence_score=confidence_score,
            frames_processed=frames_processed,
            total_frames=total_frames,
            suspicious_regions=suspicious_regions or [],
            blockchain_hash=blockchain_hash,
            processing_time_ms=processing_time_ms,
            is_fake=is_fake
        )
        
        await connection_manager.broadcast_to_analysis(analysis_id, result_update.dict())
        
        # Also publish to Redis for persistence
        await redis_manager.publish_message(
            redis_manager.get_analysis_channel(analysis_id),
            result_update.dict()
        )
        
        logger.info(f"Result update sent for analysis {analysis_id}: confidence={confidence_score}")
        
    except Exception as e:
        logger.error(f"Error sending result update: {str(e)}")


async def send_error_update(
    analysis_id: str,
    error_code: str,
    error_message: str,
    error_details: Optional[Dict[str, Any]] = None
):
    """
    Send error update to all connected clients for an analysis.
    
    Args:
        analysis_id: Analysis ID
        error_code: Error code
        error_message: Error message
        error_details: Additional error details
    """
    try:
        error_event = ErrorEvent(
            analysis_id=analysis_id,
            error_code=error_code,
            error_message=error_message,
            error_details=error_details
        )
        
        await connection_manager.broadcast_to_analysis(analysis_id, error_event.dict())
        
        # Also publish to Redis for persistence
        await redis_manager.publish_message(
            redis_manager.get_analysis_channel(analysis_id),
            error_event.dict()
        )
        
        logger.warning(f"Error update sent for analysis {analysis_id}: {error_code}")
        
    except Exception as e:
        logger.error(f"Error sending error update: {str(e)}")


# Export
__all__ = [
    'router',
    'connection_manager',
    'send_status_update',
    'send_result_update',
    'send_error_update'
]
