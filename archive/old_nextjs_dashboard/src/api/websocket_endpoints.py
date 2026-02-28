#!/usr/bin/env python3
"""
WebSocket Endpoints for Real-Time Communication
WebSocket endpoints for upload progress tracking and real-time updates
"""

import json
import logging
import uuid
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.websockets import WebSocketState

from src.services.websocket_service import get_websocket_progress_service
from src.utils.error_handlers import validate_upload_session_redis
from src.auth.upload_auth import get_current_user_jwt

logger = logging.getLogger(__name__)

# Create router for WebSocket endpoints
router = APIRouter(
    prefix="/ws",
    tags=["websocket-upload-progress"],
    responses={
        400: {"description": "Bad request"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"}
    }
)


@router.websocket("/upload-progress")
async def websocket_upload_progress(
    websocket: WebSocket,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for real-time upload progress updates.
    
    This endpoint:
    - Establishes WebSocket connection for real-time communication
    - Validates user authentication via JWT token
    - Handles session subscription and unsubscription
    - Broadcasts upload progress events with session ID, progress percentage, upload speed, and estimated completion
    - Broadcasts upload complete events with video ID, analysis ID, and redirect URL
    - Handles error states and broadcasts error messages through WebSocket events
    
    Args:
        websocket: WebSocket connection
        token: Optional JWT token for authentication
        
    Message Format:
        Client to Server:
        {
            "type": "subscribe_session|unsubscribe_session|ping",
            "session_id": "uuid", // for subscription messages
            "token": "jwt_token" // for authentication
        }
        
        Server to Client:
        {
            "event_type": "upload_progress|upload_complete|upload_error",
            "session_id": "uuid",
            "data": {
                "percentage": 45.5,
                "bytes_uploaded": 1024000,
                "total_bytes": 2250000,
                "upload_speed": 102400,
                "estimated_completion": "2025-01-01T12:05:00Z",
                "video_id": "uuid", // for complete events
                "analysis_id": "uuid", // for complete events
                "redirect_url": "/dashboard/videos/uuid/results", // for complete events
                "error_message": "Upload failed" // for error events
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
            # This would integrate with your existing JWT validation
            # For now, we'll use a placeholder
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
        
        logger.info(f"WebSocket connection {connection_id} established for user {user_id}")
        
        # Handle WebSocket messages
        while True:
            try:
                # Receive message from client
                message = await websocket.receive_text()
                
                # Parse and handle the message
                await _handle_websocket_message(
                    websocket=websocket,
                    connection_id=connection_id,
                    user_id=user_id,
                    message=message,
                    connection_manager=connection_manager
                )
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket connection {connection_id} disconnected")
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message from {connection_id}: {e}")
                break
        
    except Exception as e:
        logger.error(f"Error in WebSocket connection handler for {connection_id}: {e}")
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


async def _handle_websocket_message(
    websocket: WebSocket,
    connection_id: str,
    user_id: UUID,
    message: str,
    connection_manager
):
    """
    Handle incoming WebSocket messages.
    
    Args:
        websocket: WebSocket connection
        connection_id: Connection ID
        user_id: User ID
        message: Client message
        connection_manager: Connection manager instance
    """
    try:
        data = json.loads(message)
        message_type = data.get('type')
        
        if message_type == 'subscribe_session':
            session_id = data.get('session_id')
            if session_id:
                # Validate user access to session
                session_validation = await validate_upload_session_redis(UUID(session_id), user_id)
                if not session_validation['is_valid']:
                    # Send error response
                    error_response = {
                        'type': 'subscription_error',
                        'session_id': session_id,
                        'error': 'Unauthorized access to session',
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    await websocket.send_text(json.dumps(error_response))
                    return
                
                # Subscribe to session updates
                success = connection_manager.subscribe_to_session(connection_id, session_id)
                
                if success:
                    # Send confirmation
                    response = {
                        'type': 'subscription_confirmed',
                        'session_id': session_id,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    await websocket.send_text(json.dumps(response))
                    logger.info(f"Connection {connection_id} subscribed to session {session_id}")
                else:
                    # Send error response
                    error_response = {
                        'type': 'subscription_error',
                        'session_id': session_id,
                        'error': 'Failed to subscribe to session',
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    await websocket.send_text(json.dumps(error_response))
        
        elif message_type == 'unsubscribe_session':
            session_id = data.get('session_id')
            if session_id:
                # Unsubscribe from session updates
                success = connection_manager.unsubscribe_from_session(connection_id, session_id)
                
                if success:
                    # Send confirmation
                    response = {
                        'type': 'unsubscription_confirmed',
                        'session_id': session_id,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    await websocket.send_text(json.dumps(response))
                    logger.info(f"Connection {connection_id} unsubscribed from session {session_id}")
                else:
                    # Send error response
                    error_response = {
                        'type': 'unsubscription_error',
                        'session_id': session_id,
                        'error': 'Failed to unsubscribe from session',
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    await websocket.send_text(json.dumps(error_response))
        
        elif message_type == 'ping':
            # Respond to ping with pong
            response = {
                'type': 'pong',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            await websocket.send_text(json.dumps(response))
        
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
            error_response = {
                'type': 'error',
                'error': f'Unknown message type: {message_type}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            await websocket.send_text(json.dumps(error_response))
            
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON message from connection {connection_id}: {message}")
        error_response = {
            'type': 'error',
            'error': 'Invalid JSON message',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        await websocket.send_text(json.dumps(error_response))
    except Exception as e:
        logger.error(f"Error handling WebSocket message from {connection_id}: {e}")
        error_response = {
            'type': 'error',
            'error': 'Internal server error',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        await websocket.send_text(json.dumps(error_response))


@router.websocket("/upload-progress/{session_id}")
async def websocket_session_progress(
    websocket: WebSocket,
    session_id: UUID,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for specific session progress updates.
    
    This endpoint:
    - Establishes WebSocket connection for a specific upload session
    - Validates user access to the session
    - Automatically subscribes to progress updates for the session
    - Broadcasts real-time progress events
    
    Args:
        websocket: WebSocket connection
        session_id: Upload session ID
        token: Optional JWT token for authentication
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
        
        # Validate user access to session
        session_validation = await validate_upload_session_redis(session_id, user_id)
        if not session_validation['is_valid']:
            await websocket.close(code=1008, reason="Unauthorized access to session")
            return
        
        # Accept the connection
        success = await connection_manager.connect(websocket, connection_id, str(user_id))
        if not success:
            await websocket.close(code=1013, reason="Connection limit exceeded")
            return
        
        # Automatically subscribe to session updates
        connection_manager.subscribe_to_session(connection_id, str(session_id))
        
        logger.info(f"WebSocket connection {connection_id} established for session {session_id}")
        
        # Send initial confirmation
        confirmation = {
            'type': 'connection_established',
            'session_id': str(session_id),
            'auto_subscribed': True,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        await websocket.send_text(json.dumps(confirmation))
        
        # Handle WebSocket messages
        while True:
            try:
                # Receive message from client
                message = await websocket.receive_text()
                
                # Parse and handle the message
                await _handle_websocket_message(
                    websocket=websocket,
                    connection_id=connection_id,
                    user_id=user_id,
                    message=message,
                    connection_manager=connection_manager
                )
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket connection {connection_id} disconnected")
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message from {connection_id}: {e}")
                break
        
    except Exception as e:
        logger.error(f"Error in WebSocket connection handler for {connection_id}: {e}")
    finally:
        # Clean up the connection
        if 'connection_manager' in locals():
            connection_manager.disconnect(connection_id)


# Export router
__all__ = ['router']
