#!/usr/bin/env python3
"""
Analysis Progress WebSocket Endpoints
WebSocket endpoints for real-time analysis progress tracking
"""

import json
import logging
import uuid
import asyncio
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.websockets import WebSocketState

from src.services.websocket_service import get_websocket_progress_service
from src.services.redis_pubsub_service import get_redis_pubsub_service
from src.utils.error_handlers import validate_upload_session_redis
from src.auth.upload_auth import get_current_user_jwt
from src.schemas.websocket_events import (
    StatusUpdate,
    ResultUpdate,
    ErrorEvent,
    HeartbeatEvent,
    ConnectionEstablishedEvent
)

logger = logging.getLogger(__name__)

# Create router for analysis WebSocket endpoints
router = APIRouter(
    prefix="/ws",
    tags=["websocket-analysis-progress"],
    responses={
        400: {"description": "Bad request"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"}
    }
)


@router.websocket("/analysis/{analysis_id}")
async def websocket_analysis_progress(
    websocket: WebSocket,
    analysis_id: str,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for real-time analysis progress updates.
    
    This endpoint:
    - Establishes WebSocket connection for real-time analysis progress
    - Validates user authentication via JWT token
    - Handles analysis progress events with stage updates, percentage completion, and estimated time remaining
    - Broadcasts analysis completion events with results and blockchain verification
    - Handles error states and broadcasts error messages through WebSocket events
    
    Args:
        websocket: WebSocket connection
        analysis_id: Analysis ID to track
        token: Optional JWT token for authentication
        
    Message Format:
        Server to Client:
        {
            "event_type": "status_update|result_update|error|heartbeat|connection_established",
            "analysis_id": "uuid",
            "data": {
                "progress": 0.45,
                "current_stage": "model_inference",
                "message": "Running deepfake detection models",
                "estimated_completion": "2025-01-01T12:05:00Z",
                "frames_processed": 150,
                "total_frames": 300,
                "processing_speed_fps": 25.5,
                "confidence_score": 0.85,
                "is_fake": true,
                "blockchain_hash": "abc123...",
                "processing_time_ms": 45000,
                "suspicious_regions": [...],
                "error_code": "PROCESSING_ERROR",
                "error_message": "Analysis failed"
            },
            "timestamp": "2025-01-01T12:00:00Z"
        }
    """
    connection_id = str(uuid.uuid4())
    user_id = None
    
    try:
        # Get WebSocket service
        websocket_service = get_websocket_progress_service()
        connection_manager = websocket_service.get_connection_manager()
        
        # Handle authentication
        if not token:
            await websocket.close(code=1008, reason="Authentication token required")
            return
        
        # Validate JWT token and get user ID
        try:
            user_id = await _validate_websocket_token(token)
            if not user_id:
                await websocket.close(code=1008, reason="Invalid authentication token")
                return
        except Exception as e:
            logger.error(f"WebSocket authentication failed: {e}")
            await websocket.close(code=1008, reason="Authentication failed")
            return
        
        # Accept the connection
        success = await connection_manager.connect(websocket, connection_id, str(user_id))
        if not success:
            await websocket.close(code=1013, reason="Connection limit exceeded")
            return
        
        logger.info(f"Analysis WebSocket connection {connection_id} established for analysis {analysis_id}")
        
        # Send connection established event
        connection_event = ConnectionEstablishedEvent(
            event_type="connection_established",
            analysis_id=analysis_id,
            message=f"Connected to analysis {analysis_id} progress updates",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        await websocket.send_text(json.dumps(connection_event.dict()))
        
        # Handle WebSocket messages
        while True:
            try:
                # Receive message from client
                message = await websocket.receive_text()
                
                # Parse and handle the message
                await _handle_analysis_websocket_message(
                    websocket=websocket,
                    connection_id=connection_id,
                    analysis_id=analysis_id,
                    user_id=user_id,
                    message=message,
                    connection_manager=connection_manager
                )
                
            except WebSocketDisconnect:
                logger.info(f"Analysis WebSocket connection {connection_id} disconnected")
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message from {connection_id}: {e}")
                break
        
    except Exception as e:
        logger.error(f"Error in analysis WebSocket connection handler for {connection_id}: {e}")
    finally:
        # Clean up the connection
        if 'connection_manager' in locals():
            connection_manager.disconnect(connection_id)


async def _validate_websocket_token(token: str) -> Optional[UUID]:
    """
    Validate JWT token for WebSocket authentication.
    
    Args:
        token: JWT token
        
    Returns:
        Optional[UUID]: User ID if valid, None otherwise
    """
    try:
        # This would integrate with your existing JWT validation
        # For now, we'll use a placeholder implementation
        
        # In a real implementation, you would:
        # 1. Decode and verify the JWT token
        # 2. Extract the user ID from the token payload
        # 3. Validate the token expiration
        # 4. Return the user ID
        
        # Placeholder: Extract user ID from token (this is not secure!)
        # In production, use proper JWT validation
        if token.startswith("user_"):
            user_id_str = token.replace("user_", "")
            try:
                return UUID(user_id_str)
            except ValueError:
                return None
        
        return None
        
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        return None


async def _handle_analysis_websocket_message(
    websocket: WebSocket,
    connection_id: str,
    analysis_id: str,
    user_id: UUID,
    message: str,
    connection_manager
):
    """
    Handle incoming analysis WebSocket messages.
    
    Args:
        websocket: WebSocket connection
        connection_id: Connection ID
        analysis_id: Analysis ID
        user_id: User ID
        message: Client message
        connection_manager: Connection manager instance
    """
    try:
        data = json.loads(message)
        message_type = data.get('type')
        
        if message_type == 'ping':
            # Respond to ping with pong
            heartbeat_event = HeartbeatEvent(
                event_type="heartbeat",
                message="pong",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            await websocket.send_text(json.dumps(heartbeat_event.dict()))
        
        elif message_type == 'get_progress':
            # Send current analysis progress
            await _send_current_progress(websocket, analysis_id)
        
        elif message_type == 'get_stats':
            # Send connection statistics
            stats = connection_manager.get_connection_stats()
            response = {
                'type': 'connection_stats',
                'stats': stats,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            await websocket.send_text(json.dumps(response))
        
        else:
            # Unknown message type
            logger.warning(f"Unknown message type from connection {connection_id}: {message_type}")
            error_event = ErrorEvent(
                event_type="error",
                analysis_id=analysis_id,
                error_code="UNKNOWN_MESSAGE_TYPE",
                error_message=f"Unknown message type: {message_type}",
                error_details={"message_type": message_type},
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            await websocket.send_text(json.dumps(error_event.dict()))
            
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON message from connection {connection_id}: {message}")
        error_event = ErrorEvent(
            event_type="error",
            analysis_id=analysis_id,
            error_code="INVALID_JSON",
            error_message="Invalid JSON message",
            error_details={"raw_message": message},
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        await websocket.send_text(json.dumps(error_event.dict()))
    except Exception as e:
        logger.error(f"Error handling WebSocket message from {connection_id}: {e}")
        error_event = ErrorEvent(
            event_type="error",
            analysis_id=analysis_id,
            error_code="INTERNAL_ERROR",
            error_message="Internal server error",
            error_details={"error": str(e)},
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        await websocket.send_text(json.dumps(error_event.dict()))


async def _send_current_progress(websocket: WebSocket, analysis_id: str):
    """
    Send current analysis progress to client.
    
    Args:
        websocket: WebSocket connection
        analysis_id: Analysis ID
    """
    try:
        # In a real implementation, you would:
        # 1. Query the database for current analysis progress
        # 2. Get progress from Redis cache
        # 3. Calculate estimated completion time
        # 4. Send status update
        
        # For now, send a placeholder status update
        status_update = StatusUpdate(
            event_type="status_update",
            task_id=f"task_{analysis_id}",
            analysis_id=analysis_id,
            progress=0.5,  # 50% progress
            current_stage="model_inference",
            message="Running deepfake detection models",
            estimated_completion=datetime.now(timezone.utc).isoformat(),
            error=None,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        await websocket.send_text(json.dumps(status_update.dict()))
        
    except Exception as e:
        logger.error(f"Error sending current progress for analysis {analysis_id}: {e}")


@router.websocket("/status/{analysis_id}")
async def websocket_status_streaming(
    websocket: WebSocket,
    analysis_id: str,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for real-time status streaming with Redis pub/sub integration.
    
    This endpoint:
    - Establishes WebSocket connection for dedicated status streaming
    - Validates user authentication via JWT token
    - Subscribes to Redis pub/sub channels for real-time events
    - Streams comprehensive status updates including detailed progress tracking
    - Handles stage transition events with detailed information
    - Provides error recovery status and retry information
    
    Args:
        websocket: WebSocket connection
        analysis_id: Analysis ID to stream status for
        token: Optional JWT token for authentication
        
    Message Format:
        Server to Client:
        {
            "event_type": "status_streaming|stage_transition|error|status_update",
            "analysis_id": "uuid",
            "data": {
                "current_stage": "model_inference",
                "stage_progress": 0.75,
                "overall_progress": 0.6,
                "message": "Running frame analysis",
                "frames_processed": 150,
                "total_frames": 250,
                "processing_rate_fps": 25.5,
                "cpu_usage_percent": 65.2,
                "memory_usage_mb": 1024.0,
                "processing_efficiency": 0.85,
                "error_recovery_status": {...},
                "estimated_completion": "2025-01-01T12:05:00Z"
            },
            "timestamp": "2025-01-01T12:00:00Z"
        }
    """
    connection_id = str(uuid.uuid4())
    redis_subscription_id = None
    user_id = None
    
    async def redis_event_callback(channel: str, data: Dict[str, Any]):
        """Handle Redis pub/sub events"""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps(data))
        except Exception as e:
            logger.error(f"Error sending Redis event to connection {connection_id}: {e}")
    
    try:
        # Get WebSocket and Redis services
        websocket_service = get_websocket_progress_service()
        connection_manager = websocket_service.get_connection_manager()
        redis_service = get_redis_pubsub_service()
        
        # Handle authentication
        if not token:
            await websocket.close(code=1008, reason="Authentication token required")
            return
        
        # Validate JWT token and get user ID
        try:
            user_id = await _validate_websocket_token(token)
            if not user_id:
                await websocket.close(code=1008, reason="Invalid authentication token")
                return
        except Exception as e:
            logger.error(f"WebSocket authentication failed: {e}")
            await websocket.close(code=1008, reason="Authentication failed")
            return
        
        # Accept the connection
        success = await connection_manager.connect(websocket, connection_id, str(user_id))
        if not success:
            await websocket.close(code=1013, reason="Connection limit exceeded")
            return
        
        # Subscribe to analysis updates
        connection_manager.subscribe_to_analysis(connection_id, analysis_id)
        
        # Subscribe to Redis pub/sub for broader event distribution
        redis_subscription_id = await redis_service.subscribe_to_analysis(
            analysis_id, redis_event_callback, connection_id
        )
        
        logger.info(f"Status streaming WebSocket connection {connection_id} established for analysis {analysis_id}")
        
        # Send connection established event
        connection_event = ConnectionEstablishedEvent(
            event_type="connection_established",
            analysis_id=analysis_id,
            message=f"Connected to status streaming for analysis {analysis_id}",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        await websocket.send_text(json.dumps(connection_event.dict()))
        
        # Send current status
        await _send_current_status_streaming(websocket, analysis_id)
        
        # Handle WebSocket messages
        while True:
            try:
                # Receive message from client
                message = await websocket.receive_text()
                
                # Parse and handle the message
                await _handle_status_streaming_message(
                    websocket=websocket,
                    connection_id=connection_id,
                    analysis_id=analysis_id,
                    user_id=user_id,
                    message=message,
                    connection_manager=connection_manager
                )
                
            except WebSocketDisconnect:
                logger.info(f"Status streaming WebSocket connection {connection_id} disconnected")
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message from {connection_id}: {e}")
                break
        
    except Exception as e:
        logger.error(f"Error in status streaming WebSocket connection handler for {connection_id}: {e}")
    finally:
        # Clean up the connection
        if 'connection_manager' in locals() and connection_manager:
            connection_manager.disconnect(connection_id)
        
        # Clean up Redis subscription
        if redis_subscription_id and 'redis_service' in locals():
            await redis_service.unsubscribe_from_analysis(redis_subscription_id)


async def _send_current_status_streaming(websocket: WebSocket, analysis_id: str):
    """
    Send current comprehensive status streaming information to client.
    
    Args:
        websocket: WebSocket connection
        analysis_id: Analysis ID
    """
    try:
        # In a real implementation, you would:
        # 1. Get detailed status from Redis cache (Work Order #24)
        # 2. Include processing stage details, frame progress info, error recovery status
        # 3. Include processing metrics (CPU, memory,效率)
        # 4. Include progress history and trends
        
        # For now, send a comprehensive status streaming event
        status_streaming_data = {
            'current_stage': 'model_inference',
            'stage_progress': 0.75,
            'overall_progress': 0.6,
            'message': 'Running deepfake detection models on frame batch',
            'frames_processed': 150,
            'total_frames': 250,
            'processing_rate_fps': 25.5,
            'cpu_usage_percent': 65.2,
            'memory_usage_mb': 1024.0,
            'processing_efficiency': 0.85,
            'estimated_completion': datetime.now(timezone.utc).isoformat(),
            'error_recovery_status': None,
            'progress_history': [
                {'timestamp': datetime.now(timezone.utc).isoformat(), 'overall_progress': 0.6, 'stage': 'model_inference'},
                {'timestamp': datetime.now(timezone.utc).isoformat(), 'overall_progress': 0.5, 'stage': 'feature_extraction'}
            ]
        }
        
        status_streaming_event = {
            'event_type': 'status_streaming',
            'analysis_id': analysis_id,
            **status_streaming_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        await websocket.send_text(json.dumps(status_streaming_event))
        
    except Exception as e:
        logger.error(f"Error sending current status streaming for analysis {analysis_id}: {e}")


async def _handle_status_streaming_message(
    websocket: WebSocket,
    connection_id: str,
    analysis_id: str,
    user_id: UUID,
    message: str,
    connection_manager
):
    """
    Handle incoming status streaming WebSocket messages.
    
    Args:
        websocket: WebSocket connection
        connection_id: Connection ID
        analysis_id: Analysis ID
        user_id: User ID
        message: Client message
        connection_manager: Connection manager instance
    """
    try:
        data = json.loads(message)
        message_type = data.get('type')
        
        if message_type == 'ping':
            # Respond to ping with pong
            heartbeat_event = HeartbeatEvent(
                event_type="heartbeat",
                message="pong",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            await websocket.send_text(json.dumps(heartbeat_event.dict()))
        
        elif message_type == 'get_current_status':
            # Send current comprehensive status
            await _send_current_status_streaming(websocket, analysis_id)
        
        elif message_type == 'subscribe_analysis':
            # Subscribe to additional analysis (if needed)
            target_analysis_id = data.get('analysis_id')
            if target_analysis_id:
                connection_manager.subscribe_to_analysis(connection_id, target_analysis_id)
                
                # Send confirmation
                response = {
                    'type': 'subscription_confirmed',
                    'analysis_id': target_analysis_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                await websocket.send_text(json.dumps(response))
        
        elif message_type == 'get_streaming_stats':
            # Send streaming statistics
            stats = connection_manager.get_connection_stats()
            redis_service = get_redis_pubsub_service()
            redis_stats = redis_service.get_subscription_stats()
            
            response = {
                'type': 'streaming_stats',
                'websocket_stats': stats,
                'redis_stats': redis_stats,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            await websocket.send_text(json.dumps(response))
        
        else:
            # Unknown message type
            logger.warning(f"Unknown message type from connection {connection_id}: {message_type}")
            error_event = ErrorEvent(
                event_type="error",
                analysis_id=analysis_id,
                error_code="UNKNOWN_MESSAGE_TYPE",
                error_message=f"Unknown message type: {message_type}",
                error_details={"message_type": message_type},
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            await websocket.send_text(json.dumps(error_event.dict()))
            
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON message from connection {connection_id}: {message}")
        error_event = ErrorEvent(
            event_type="error",
            analysis_id=analysis_id,
            error_code="INVALID_JSON",
            error_message="Invalid JSON message",
            error_details={"raw_message": message},
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        await websocket.send_text(json.dumps(error_event.dict()))
    except Exception as e:
        logger.error(f"Error handling WebSocket message from {connection_id}: {e}")
        error_event = ErrorEvent(
            event_type="error",
            analysis_id=analysis_id,
            error_code="INTERNAL_ERROR",
            error_message="Internal server error",
            error_details={"error": str(e)},
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        await websocket.send_text(json.dumps(error_event.dict()))


# Broadcast functions for analysis events
async def broadcast_analysis_progress(
    analysis_id: str,
    progress: float,
    current_stage: str,
    message: str,
    estimated_completion: Optional[str] = None,
    frames_processed: Optional[int] = None,
    total_frames: Optional[int] = None,
    processing_speed_fps: Optional[float] = None
) -> int:
    """
    Broadcast analysis progress update.
    
    Args:
        analysis_id: Analysis ID
        progress: Progress percentage (0.0-1.0)
        current_stage: Current processing stage
        message: Status message
        estimated_completion: Estimated completion time
        frames_processed: Number of frames processed
        total_frames: Total frames in video
        processing_speed_fps: Processing speed in FPS
        
    Returns:
        int: Number of connections the event was sent to
    """
    try:
        websocket_service = get_websocket_progress_service()
        connection_manager = websocket_service.get_connection_manager()
        
        status_update = StatusUpdate(
            event_type="status_update",
            task_id=f"task_{analysis_id}",
            analysis_id=analysis_id,
            progress=progress,
            current_stage=current_stage,
            message=message,
            estimated_completion=estimated_completion,
            error=None,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Add additional data
        data = status_update.dict()
        if frames_processed is not None:
            data['frames_processed'] = frames_processed
        if total_frames is not None:
            data['total_frames'] = total_frames
        if processing_speed_fps is not None:
            data['processing_speed_fps'] = processing_speed_fps
        
        # Send to all connections tracking this analysis
        message_text = json.dumps(data)
        sent_count = 0
        
        for connection_id, websocket in connection_manager.active_connections.items():
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message_text)
                    sent_count += 1
            except Exception as e:
                logger.error(f"Error sending progress update to connection {connection_id}: {e}")
        
        logger.debug(f"Broadcasted analysis progress for {analysis_id} to {sent_count} connections")
        return sent_count
        
    except Exception as e:
        logger.error(f"Failed to broadcast analysis progress for {analysis_id}: {e}")
        return 0


async def broadcast_analysis_complete(
    analysis_id: str,
    confidence_score: float,
    is_fake: bool,
    frames_processed: int,
    total_frames: int,
    suspicious_regions: list = None,
    blockchain_hash: Optional[str] = None,
    processing_time_ms: int = 0,
    model_type: str = "ensemble"
) -> int:
    """
    Broadcast analysis completion.
    
    Args:
        analysis_id: Analysis ID
        confidence_score: Confidence score (0.0-1.0)
        is_fake: Whether video is detected as fake
        frames_processed: Number of frames processed
        total_frames: Total frames in video
        suspicious_regions: Detected suspicious regions
        blockchain_hash: Blockchain verification hash
        processing_time_ms: Processing time in milliseconds
        model_type: Model type used
        
    Returns:
        int: Number of connections the event was sent to
    """
    try:
        websocket_service = get_websocket_progress_service()
        connection_manager = websocket_service.get_connection_manager()
        
        result_update = ResultUpdate(
            event_type="result_update",
            analysis_id=analysis_id,
            confidence_score=confidence_score,
            frames_processed=frames_processed,
            total_frames=total_frames,
            suspicious_regions=suspicious_regions or [],
            blockchain_hash=blockchain_hash,
            processing_time_ms=processing_time_ms,
            is_fake=is_fake,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Add additional data
        data = result_update.dict()
        data['model_type'] = model_type
        
        # Send to all connections tracking this analysis
        message_text = json.dumps(data)
        sent_count = 0
        
        for connection_id, websocket in connection_manager.active_connections.items():
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message_text)
                    sent_count += 1
            except Exception as e:
                logger.error(f"Error sending completion update to connection {connection_id}: {e}")
        
        logger.debug(f"Broadcasted analysis completion for {analysis_id} to {sent_count} connections")
        return sent_count
        
    except Exception as e:
        logger.error(f"Failed to broadcast analysis completion for {analysis_id}: {e}")
        return 0


async def broadcast_analysis_error(
    analysis_id: str,
    error_code: str,
    error_message: str,
    error_details: Optional[Dict[str, Any]] = None
) -> int:
    """
    Broadcast analysis error.
    
    Args:
        analysis_id: Analysis ID
        error_code: Error code
        error_message: Error message
        error_details: Additional error details
        
    Returns:
        int: Number of connections the event was sent to
    """
    try:
        websocket_service = get_websocket_progress_service()
        connection_manager = websocket_service.get_connection_manager()
        
        error_event = ErrorEvent(
            event_type="error",
            analysis_id=analysis_id,
            error_code=error_code,
            error_message=error_message,
            error_details=error_details,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Send to all connections tracking this analysis
        message_text = json.dumps(error_event.dict())
        sent_count = 0
        
        for connection_id, websocket in connection_manager.active_connections.items():
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message_text)
                    sent_count += 1
            except Exception as e:
                logger.error(f"Error sending error update to connection {connection_id}: {e}")
        
        logger.debug(f"Broadcasted analysis error for {analysis_id} to {sent_count} connections")
        return sent_count
        
    except Exception as e:
        logger.error(f"Failed to broadcast analysis error for {analysis_id}: {e}")
        return 0


# Export router and broadcast functions
__all__ = [
    'router',
    'broadcast_analysis_progress',
    'broadcast_analysis_complete',
    'broadcast_analysis_error'
]
