#!/usr/bin/env python3
"""
JWT Authentication Dependency for WebSocket Connections
Authentication dependency for securing WebSocket endpoints with JWT tokens
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import jwt
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class WebSocketAuthError(Exception):
    """Custom exception for WebSocket authentication errors."""
    pass


class JWTWebSocketAuth:
    """
    JWT authentication for WebSocket connections.
    Handles token extraction, validation, and user identification.
    """
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        token_prefix: str = "Bearer",
        token_param: str = "token",
        cookie_name: str = "access_token"
    ):
        """
        Initialize JWT WebSocket authentication.
        
        Args:
            secret_key: JWT secret key
            algorithm: JWT algorithm
            token_prefix: Token prefix for Authorization header
            token_param: Query parameter name for token
            cookie_name: Cookie name for token
        """
        self.secret_key = secret_key or os.getenv('JWT_SECRET_KEY', 'your-secret-key')
        self.algorithm = algorithm
        self.token_prefix = token_prefix
        self.token_param = token_param
        self.cookie_name = cookie_name
        
        logger.info("JWT WebSocket authentication initialized")
    
    def extract_token_from_websocket(self, websocket: WebSocket) -> Optional[str]:
        """
        Extract JWT token from WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            
        Returns:
            JWT token string or None if not found
        """
        try:
            # Method 1: Query parameters
            token = websocket.query_params.get(self.token_param)
            if token:
                logger.debug("Token extracted from query parameters")
                return token
            
            # Method 2: Authorization header (if available in headers)
            headers = websocket.headers
            auth_header = headers.get("authorization") or headers.get("Authorization")
            if auth_header and auth_header.startswith(f"{self.token_prefix} "):
                token = auth_header[len(f"{self.token_prefix} "):]
                logger.debug("Token extracted from Authorization header")
                return token
            
            # Method 3: Cookies
            cookies = websocket.cookies
            token = cookies.get(self.cookie_name)
            if token:
                logger.debug("Token extracted from cookies")
                return token
            
            logger.warning("No JWT token found in WebSocket connection")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting token from WebSocket: {str(e)}")
            return None
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token and extract payload.
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload dictionary
            
        Raises:
            WebSocketAuthError: If token is invalid
        """
        try:
            # Decode and validate token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": True}
            )
            
            # Check required fields
            if 'user_id' not in payload and 'sub' not in payload:
                raise WebSocketAuthError("Token missing user identification")
            
            # Extract user ID
            user_id = payload.get('user_id') or payload.get('sub')
            if not user_id:
                raise WebSocketAuthError("Invalid user ID in token")
            
            # Add validation timestamp
            payload['validated_at'] = datetime.now(timezone.utc).isoformat()
            
            logger.debug(f"Token validated for user: {user_id}")
            return payload
            
        except jwt.ExpiredSignatureError:
            raise WebSocketAuthError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise WebSocketAuthError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Error validating token: {str(e)}")
            raise WebSocketAuthError(f"Token validation failed: {str(e)}")
    
    async def authenticate_websocket(self, websocket: WebSocket) -> Dict[str, Any]:
        """
        Authenticate WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            
        Returns:
            Authentication result with user information
            
        Raises:
            WebSocketAuthError: If authentication fails
        """
        try:
            # Extract token
            token = self.extract_token_from_websocket(websocket)
            if not token:
                raise WebSocketAuthError("No authentication token provided")
            
            # Validate token
            payload = self.validate_token(token)
            
            # Return authentication result
            auth_result = {
                'authenticated': True,
                'user_id': payload.get('user_id') or payload.get('sub'),
                'token_payload': payload,
                'authenticated_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"WebSocket authenticated for user: {auth_result['user_id']}")
            return auth_result
            
        except WebSocketAuthError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during WebSocket authentication: {str(e)}")
            raise WebSocketAuthError(f"Authentication failed: {str(e)}")
    
    async def close_websocket_with_auth_error(
        self,
        websocket: WebSocket,
        error_message: str = "Authentication failed"
    ):
        """
        Close WebSocket connection with authentication error.
        
        Args:
            websocket: WebSocket connection
            error_message: Error message to send
        """
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(code=4001, reason=error_message)
                logger.warning(f"WebSocket closed with auth error: {error_message}")
        except Exception as e:
            logger.error(f"Error closing WebSocket with auth error: {str(e)}")


# Global JWT WebSocket auth instance
jwt_websocket_auth = JWTWebSocketAuth()


async def authenticate_websocket_connection(websocket: WebSocket) -> Dict[str, Any]:
    """
    Authenticate WebSocket connection using JWT token.
    
    Args:
        websocket: WebSocket connection
        
    Returns:
        Authentication result with user information
        
    Raises:
        WebSocketAuthError: If authentication fails
    """
    try:
        return await jwt_websocket_auth.authenticate_websocket(websocket)
    except WebSocketAuthError as e:
        # Close WebSocket with authentication error
        await jwt_websocket_auth.close_websocket_with_auth_error(websocket, str(e))
        raise


async def require_websocket_auth(websocket: WebSocket) -> Dict[str, Any]:
    """
    Dependency function for WebSocket authentication.
    
    Args:
        websocket: WebSocket connection
        
    Returns:
        Authentication result
        
    Raises:
        WebSocketAuthError: If authentication fails
    """
    return await authenticate_websocket_connection(websocket)


class WebSocketAuthDependency:
    """
    FastAPI dependency class for WebSocket authentication.
    """
    
    def __init__(self, auth_instance: Optional[JWTWebSocketAuth] = None):
        """
        Initialize WebSocket auth dependency.
        
        Args:
            auth_instance: JWT WebSocket auth instance
        """
        self.auth = auth_instance or jwt_websocket_auth
    
    async def __call__(self, websocket: WebSocket) -> Dict[str, Any]:
        """
        Call dependency for WebSocket authentication.
        
        Args:
            websocket: WebSocket connection
            
        Returns:
            Authentication result
        """
        return await self.auth.authenticate_websocket(websocket)


# Utility functions for token management
def create_mock_token(
    user_id: str,
    expires_in_hours: int = 24,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a mock JWT token for testing purposes.
    
    Args:
        user_id: User ID
        expires_in_hours: Token expiration in hours
        additional_claims: Additional claims to include
        
    Returns:
        JWT token string
    """
    try:
        from datetime import timedelta
        
        # Create payload
        payload = {
            'user_id': user_id,
            'sub': user_id,
            'iat': datetime.now(timezone.utc),
            'exp': datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
            'type': 'access'
        }
        
        # Add additional claims
        if additional_claims:
            payload.update(additional_claims)
        
        # Generate token
        token = jwt.encode(
            payload,
            jwt_websocket_auth.secret_key,
            algorithm=jwt_websocket_auth.algorithm
        )
        
        logger.debug(f"Mock token created for user: {user_id}")
        return token
        
    except Exception as e:
        logger.error(f"Error creating mock token: {str(e)}")
        raise


def validate_token_structure(token: str) -> bool:
    """
    Validate JWT token structure without verifying signature.
    
    Args:
        token: JWT token string
        
    Returns:
        True if token structure is valid, False otherwise
    """
    try:
        # Decode without verification to check structure
        jwt.decode(
            token,
            options={"verify_signature": False, "verify_exp": False}
        )
        return True
    except Exception:
        return False


# Export
__all__ = [
    'WebSocketAuthError',
    'JWTWebSocketAuth',
    'jwt_websocket_auth',
    'authenticate_websocket_connection',
    'require_websocket_auth',
    'WebSocketAuthDependency',
    'create_mock_token',
    'validate_token_structure'
]
