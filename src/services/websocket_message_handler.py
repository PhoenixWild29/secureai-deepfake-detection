#!/usr/bin/env python3
"""
WebSocket Message Handler Implementation
Work Order #31 - WebSocket Status API Integration

This module handles incoming WebSocket messages and routes them to appropriate
handlers for status requests, subscriptions, and other operations.
"""

import json
import logging
from enum import Enum
from typing import Dict, Any, Optional, Union
from uuid import UUID
from datetime import datetime, timezone

from src.utils.auth import validate_jwt_token

# Configure logging
logger = logging.getLogger(__name__)

class WebSocketMessageType(Enum):
    """WebSocket message types"""
    STATUS_REQUEST = "status_request"
    SUBSCRIBE_REQUEST = "subscribe_request"
    UNSUBSCRIBE_REQUEST = "unsubscribe_request"
    PING_REQUEST = "ping_request"
    HISTORY_REQUEST = "history_request"
    ERROR = "error"

class WebSocketMessageHandler:
    """WebSocket message handler service"""
    
    def __init__(self):
        self.handlers = {
            WebSocketMessageType.STATUS_REQUEST: self._handle_status_request,
            WebSocketMessageType.SUBSCRIBE_REQUEST: self._handle_subscribe_request,
            WebSocketMessageType.UNSUBSCRIBE_REQUEST: self._handle_unsubscribe_request,
            WebSocketMessageType.PING_REQUEST: self._handle_ping_request,
            WebSocketMessageType.HISTORY_REQUEST: self._handle_history_request,
        }
    
    async def handle_message(
        self, 
        connection_id: str, 
        message: Dict[str, Any], 
        connection_info: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Handle incoming WebSocket message
        
        Args:
            connection_id: ID of the WebSocket connection
            message: Parsed JSON message
            connection_info: Connection information
            
        Returns:
            Response message or None
        """
        try:
            # Validate message format
            if not self.validate_message_format(message):
                return self.create_response_message(
                    WebSocketMessageType.ERROR,
                    "Invalid message format",
                    {"required_fields": ["type", "timestamp"]}
                )
            
            # Get message type
            message_type_str = message.get('type')
            try:
                message_type = WebSocketMessageType(message_type_str)
            except ValueError:
                return self.create_response_message(
                    WebSocketMessageType.ERROR,
                    f"Unknown message type: {message_type_str}",
                    {"valid_types": [mt.value for mt in WebSocketMessageType]}
                )
            
            # Route to appropriate handler
            handler = self.handlers.get(message_type)
            if not handler:
                return self.create_response_message(
                    WebSocketMessageType.ERROR,
                    f"No handler for message type: {message_type.value}"
                )
            
            # Execute handler
            response = await handler(connection_id, message, connection_info)
            return response
            
        except Exception as e:
            logger.error(f"Error handling message for connection {connection_id}: {e}")
            return self.create_response_message(
                WebSocketMessageType.ERROR,
                "Internal server error",
                {"error": str(e)}
            )
    
    def validate_message_format(self, message: Dict[str, Any]) -> bool:
        """Validate WebSocket message format"""
        if not isinstance(message, dict):
            return False
        
        required_fields = ["type"]
        for field in required_fields:
            if field not in message:
                return False
        
        # Validate message type
        message_type = message.get('type')
        if not isinstance(message_type, str):
            return False
        
        try:
            WebSocketMessageType(message_type)
        except ValueError:
            return False
        
        return True
    
    def validate_analysis_id(self, analysis_id: Any) -> bool:
        """Validate analysis ID format"""
        if not analysis_id:
            return False
        
        try:
            UUID(str(analysis_id))
            return True
        except ValueError:
            return False
    
    async def validate_jwt_token(self, jwt_token: str) -> Optional[str]:
        """Validate JWT token and return user ID"""
        if not jwt_token:
            return None
        
        try:
            user_id = await validate_jwt_token(jwt_token)
            return user_id
        except Exception as e:
            logger.error(f"JWT token validation error: {e}")
            return None
    
    def is_valid_json(self, data: str) -> bool:
        """Check if string is valid JSON"""
        try:
            json.loads(data)
            return True
        except json.JSONDecodeError:
            return False
    
    async def _handle_status_request(
        self, 
        connection_id: str, 
        message: Dict[str, Any], 
        connection_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle status request message"""
        try:
            analysis_id = message.get('analysis_id')
            
            # Validate analysis ID
            if not self.validate_analysis_id(analysis_id):
                return self.create_response_message(
                    WebSocketMessageType.ERROR,
                    "Invalid or missing analysis_id",
                    {"required": True, "format": "UUID"}
                )
            
            # Import here to avoid circular imports
            from src.api.status_integration import status_api_integration
            
            # Get status from database
            status_response = await status_api_integration.get_analysis_status(UUID(analysis_id))
            
            if status_response:
                return {
                    'type': 'status_response',
                    'analysis_id': analysis_id,
                    'status': status_response.dict(),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            else:
                return self.create_response_message(
                    WebSocketMessageType.ERROR,
                    "Analysis not found",
                    {"analysis_id": analysis_id}
                )
            
        except Exception as e:
            logger.error(f"Error handling status request: {e}")
            return self.create_response_message(
                WebSocketMessageType.ERROR,
                "Failed to retrieve status",
                {"error": str(e)}
            )
    
    async def _handle_subscribe_request(
        self, 
        connection_id: str, 
        message: Dict[str, Any], 
        connection_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle subscribe request message"""
        try:
            analysis_id = message.get('analysis_id')
            jwt_token = message.get('jwt_token')
            
            # Validate analysis ID
            if not self.validate_analysis_id(analysis_id):
                return self.create_response_message(
                    WebSocketMessageType.ERROR,
                    "Invalid or missing analysis_id",
                    {"required": True, "format": "UUID"}
                )
            
            # Validate JWT token if provided
            user_id = None
            if jwt_token:
                user_id = await self.validate_jwt_token(jwt_token)
                if not user_id:
                    return self.create_response_message(
                        WebSocketMessageType.ERROR,
                        "Invalid JWT token"
                    )
            
            # Import here to avoid circular imports
            from src.api.websocket_status_api import websocket_status_api
            
            # Subscribe to analysis updates
            response = await websocket_status_api.handle_subscribe_request(connection_id, message)
            return response
            
        except Exception as e:
            logger.error(f"Error handling subscribe request: {e}")
            return self.create_response_message(
                WebSocketMessageType.ERROR,
                "Failed to subscribe to analysis",
                {"error": str(e)}
            )
    
    async def _handle_unsubscribe_request(
        self, 
        connection_id: str, 
        message: Dict[str, Any], 
        connection_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle unsubscribe request message"""
        try:
            analysis_id = message.get('analysis_id')
            
            # Import here to avoid circular imports
            from src.api.websocket_status_api import websocket_status_api
            
            # Unsubscribe from analysis updates
            response = await websocket_status_api.handle_unsubscribe_request(connection_id, message)
            return response
            
        except Exception as e:
            logger.error(f"Error handling unsubscribe request: {e}")
            return self.create_response_message(
                WebSocketMessageType.ERROR,
                "Failed to unsubscribe from analysis",
                {"error": str(e)}
            )
    
    async def _handle_ping_request(
        self, 
        connection_id: str, 
        message: Dict[str, Any], 
        connection_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle ping request message"""
        try:
            # Import here to avoid circular imports
            from src.api.websocket_status_api import websocket_status_api
            
            # Handle ping
            response = await websocket_status_api.handle_ping_request(connection_id, message)
            return response
            
        except Exception as e:
            logger.error(f"Error handling ping request: {e}")
            return self.create_response_message(
                WebSocketMessageType.ERROR,
                "Failed to process ping",
                {"error": str(e)}
            )
    
    async def _handle_history_request(
        self, 
        connection_id: str, 
        message: Dict[str, Any], 
        connection_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle history request message"""
        try:
            analysis_id = message.get('analysis_id')
            
            # Validate analysis ID
            if not self.validate_analysis_id(analysis_id):
                return self.create_response_message(
                    WebSocketMessageType.ERROR,
                    "Invalid or missing analysis_id",
                    {"required": True, "format": "UUID"}
                )
            
            # Import here to avoid circular imports
            from src.api.status_integration import status_api_integration
            
            # Get status history
            history_response = await status_api_integration.get_status_history(UUID(analysis_id))
            
            if history_response:
                return {
                    'type': 'history_response',
                    'analysis_id': analysis_id,
                    'history': history_response.dict(),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            else:
                return self.create_response_message(
                    WebSocketMessageType.ERROR,
                    "Analysis not found or no history available",
                    {"analysis_id": analysis_id}
                )
            
        except Exception as e:
            logger.error(f"Error handling history request: {e}")
            return self.create_response_message(
                WebSocketMessageType.ERROR,
                "Failed to retrieve history",
                {"error": str(e)}
            )
    
    def create_response_message(
        self, 
        message_type: WebSocketMessageType, 
        message: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create standardized response message"""
        response = {
            'type': message_type.value,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        if data:
            response['data'] = data
        
        return response
    
    def get_required_fields(self, message_type: WebSocketMessageType) -> List[str]:
        """Get required fields for a message type"""
        field_requirements = {
            WebSocketMessageType.STATUS_REQUEST: ["analysis_id"],
            WebSocketMessageType.SUBSCRIBE_REQUEST: ["analysis_id"],
            WebSocketMessageType.UNSUBSCRIBE_REQUEST: [],
            WebSocketMessageType.PING_REQUEST: [],
            WebSocketMessageType.HISTORY_REQUEST: ["analysis_id"],
        }
        
        return field_requirements.get(message_type, [])
    
    def validate_required_fields(self, message: Dict[str, Any], message_type: WebSocketMessageType) -> List[str]:
        """Validate required fields for a message type"""
        required_fields = self.get_required_fields(message_type)
        missing_fields = []
        
        for field in required_fields:
            if field not in message or message[field] is None:
                missing_fields.append(field)
        
        return missing_fields
