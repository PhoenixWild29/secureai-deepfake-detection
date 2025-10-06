#!/usr/bin/env python3
"""
WebSocket Status API Endpoint Implementation
Work Order #31 - WebSocket Status API Integration

This module provides WebSocket endpoints for real-time status streaming
and integrates with the status tracking models from Work Order #34.
"""

import json
import logging
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from fastapi.routing import APIRouter

# Import status tracking models from status_integration
from src.api.status_integration import (
    StatusTrackingResponse,
    StatusHistoryResponse,
    ProcessingStageEnum,
    StatusTransitionValidator
)
from src.services.websocket_service import get_websocket_service
from src.services.websocket_message_handler import WebSocketMessageHandler, WebSocketMessageType
from src.services.status_broadcast_service import StatusBroadcastService
from src.utils.auth import validate_jwt_token

# Configure logging
logger = logging.getLogger(__name__)

# Create router for WebSocket endpoints
router = APIRouter(prefix="/ws", tags=["websocket"])

class WebSocketStatusAPI:
    """WebSocket Status API implementation"""
    
    def __init__(self):
        self.websocket_service = get_websocket_service()
        self.message_handler = WebSocketMessageHandler()
        self.broadcast_service = StatusBroadcastService()
        self.active_connections: Dict[str, Dict[str, Any]] = {}
    
    async def websocket_status_endpoint(self, websocket: WebSocket, analysis_id: str = None):
        """
        WebSocket endpoint for real-time status streaming
        
        Args:
            websocket: WebSocket connection
            analysis_id: Optional analysis ID to subscribe to
        """
        connection_id = str(uuid4())
        
        try:
            # Accept the WebSocket connection
            await websocket.accept()
            logger.info(f"WebSocket connection established: {connection_id}")
            
            # Add connection to active connections
            self.active_connections[connection_id] = {
                'websocket': websocket,
                'analysis_id': analysis_id,
                'user_id': None,
                'jwt_token': None,
                'connected_at': datetime.now(timezone.utc),
                'last_ping': datetime.now(timezone.utc)
            }
            
            # Send welcome message
            welcome_message = {
                'type': 'connection_established',
                'connection_id': connection_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'analysis_id': analysis_id
            }
            await websocket.send_text(json.dumps(welcome_message))
            
            # Handle WebSocket messages
            await self.handle_websocket_connection(connection_id, websocket)
            
        except WebSocketDisconnect:
            logger.info(f"WebSocket connection disconnected: {connection_id}")
            await self.handle_disconnection(connection_id)
        except Exception as e:
            logger.error(f"WebSocket error for connection {connection_id}: {e}")
            await self.handle_disconnection(connection_id)
    
    async def handle_websocket_connection(self, connection_id: str, websocket: WebSocket):
        """Handle incoming WebSocket messages"""
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    error_response = {
                        'type': 'error',
                        'message': 'Invalid JSON format',
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    await websocket.send_text(json.dumps(error_response))
                    continue
                
                # Handle the message
                response = await self.message_handler.handle_message(
                    connection_id, 
                    message, 
                    self.active_connections.get(connection_id)
                )
                
                # Send response if available
                if response:
                    await websocket.send_text(json.dumps(response))
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected during message handling: {connection_id}")
            raise
        except Exception as e:
            logger.error(f"Error handling WebSocket messages for {connection_id}: {e}")
            error_response = {
                'type': 'error',
                'message': 'Internal server error',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            try:
                await websocket.send_text(json.dumps(error_response))
            except:
                pass  # Connection might be closed
    
    async def handle_status_request(self, connection_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status request message"""
        try:
            analysis_id = message.get('analysis_id')
            if not analysis_id:
                return {
                    'type': 'error',
                    'message': 'analysis_id is required',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Validate analysis ID format
            try:
                UUID(analysis_id)
            except ValueError:
                return {
                    'type': 'error',
                    'message': 'Invalid analysis_id format',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Get status from database or cache
            status_response = await self.get_analysis_status(analysis_id)
            
            return {
                'type': 'status_response',
                'analysis_id': analysis_id,
                'status': status_response.dict() if status_response else None,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error handling status request: {e}")
            return {
                'type': 'error',
                'message': 'Failed to retrieve status',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def handle_subscribe_request(self, connection_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscribe request message"""
        try:
            analysis_id = message.get('analysis_id')
            jwt_token = message.get('jwt_token')
            
            if not analysis_id:
                return {
                    'type': 'error',
                    'message': 'analysis_id is required for subscription',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Validate JWT token if provided
            if jwt_token:
                user_id = await validate_jwt_token(jwt_token)
                if not user_id:
                    return {
                        'type': 'error',
                        'message': 'Invalid JWT token',
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
            else:
                user_id = None
            
            # Update connection with analysis subscription
            if connection_id in self.active_connections:
                self.active_connections[connection_id]['analysis_id'] = analysis_id
                self.active_connections[connection_id]['user_id'] = user_id
                self.active_connections[connection_id]['jwt_token'] = jwt_token
            
            # Subscribe to analysis updates
            await self.broadcast_service.subscribe_to_analysis(connection_id, analysis_id)
            
            return {
                'type': 'subscribe_success',
                'analysis_id': analysis_id,
                'message': 'Successfully subscribed to analysis updates',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error handling subscribe request: {e}")
            return {
                'type': 'error',
                'message': 'Failed to subscribe to analysis',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def handle_unsubscribe_request(self, connection_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unsubscribe request message"""
        try:
            analysis_id = message.get('analysis_id')
            
            if connection_id in self.active_connections:
                current_analysis_id = self.active_connections[connection_id].get('analysis_id')
                
                # Unsubscribe from analysis updates
                if analysis_id or current_analysis_id:
                    target_analysis_id = analysis_id or current_analysis_id
                    await self.broadcast_service.unsubscribe_from_analysis(connection_id, target_analysis_id)
                
                # Clear subscription from connection
                self.active_connections[connection_id]['analysis_id'] = None
            
            return {
                'type': 'unsubscribe_success',
                'analysis_id': analysis_id,
                'message': 'Successfully unsubscribed from analysis updates',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error handling unsubscribe request: {e}")
            return {
                'type': 'error',
                'message': 'Failed to unsubscribe from analysis',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def handle_ping_request(self, connection_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping request message"""
        try:
            # Update last ping time
            if connection_id in self.active_connections:
                self.active_connections[connection_id]['last_ping'] = datetime.now(timezone.utc)
            
            return {
                'type': 'pong',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error handling ping request: {e}")
            return {
                'type': 'error',
                'message': 'Failed to process ping',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def get_analysis_status(self, analysis_id: str) -> Optional[StatusTrackingResponse]:
        """Get current status for an analysis"""
        try:
            # This would typically query the database
            # For now, return a mock response
            return StatusTrackingResponse(
                analysis_id=UUID(analysis_id),
                status="processing",
                progress_percentage=45.5,
                current_stage="feature_analysis",
                processing_time_elapsed=120000,
                retry_count=0,
                stage_history=[
                    {
                        "stage": "upload",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "status": "completed"
                    },
                    {
                        "stage": "preprocessing",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "status": "completed"
                    }
                ],
                last_updated=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Error getting analysis status for {analysis_id}: {e}")
            return None
    
    async def broadcast_status_update(self, analysis_id: str, status_update: StatusTrackingResponse):
        """Broadcast status update to subscribed connections"""
        try:
            await self.broadcast_service.broadcast_analysis_status(analysis_id, status_update)
        except Exception as e:
            logger.error(f"Error broadcasting status update for {analysis_id}: {e}")
    
    async def handle_disconnection(self, connection_id: str):
        """Handle WebSocket disconnection"""
        try:
            if connection_id in self.active_connections:
                connection_info = self.active_connections[connection_id]
                analysis_id = connection_info.get('analysis_id')
                
                # Unsubscribe from analysis updates
                if analysis_id:
                    await self.broadcast_service.unsubscribe_from_analysis(connection_id, analysis_id)
                
                # Remove connection
                del self.active_connections[connection_id]
                
                logger.info(f"Connection {connection_id} cleaned up successfully")
                
        except Exception as e:
            logger.error(f"Error handling disconnection for {connection_id}: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        try:
            total_connections = len(self.active_connections)
            active_analyses = set()
            
            for conn_info in self.active_connections.values():
                analysis_id = conn_info.get('analysis_id')
                if analysis_id:
                    active_analyses.add(analysis_id)
            
            return {
                'total_connections': total_connections,
                'active_analyses_tracked': len(active_analyses),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting connection stats: {e}")
            return {
                'total_connections': 0,
                'active_analyses_tracked': 0,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

# Global instance
websocket_status_api = WebSocketStatusAPI()

# WebSocket endpoint
@router.websocket("/status/{analysis_id}")
async def websocket_status_endpoint(websocket: WebSocket, analysis_id: str):
    """WebSocket endpoint for status streaming"""
    await websocket_status_api.websocket_status_endpoint(websocket, analysis_id)

@router.websocket("/status")
async def websocket_status_endpoint_general(websocket: WebSocket):
    """WebSocket endpoint for general status streaming"""
    await websocket_status_api.websocket_status_endpoint(websocket)

# HTTP endpoints for connection management
@router.get("/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    return websocket_status_api.get_connection_stats()

@router.post("/broadcast/{analysis_id}")
async def trigger_status_broadcast(analysis_id: str, status_update: StatusTrackingResponse):
    """Trigger status broadcast for an analysis"""
    await websocket_status_api.broadcast_status_update(analysis_id, status_update)
    return {"message": "Status broadcast triggered", "analysis_id": analysis_id}
