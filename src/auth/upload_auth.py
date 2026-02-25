#!/usr/bin/env python3
"""
Authentication Integration for Upload Sessions
Integration with existing authentication patterns for upload session management
"""

import logging
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import json

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer()


class AuthenticationError(Exception):
    """Custom exception for authentication errors"""
    pass


class UserAuthentication:
    """
    User authentication service for upload sessions.
    Integrates with existing authentication patterns.
    """
    
    def __init__(self):
        self.secret_key = self._get_secret_key()
        self.algorithm = "HS256"
        self.token_expiry_hours = 24
    
    def _get_secret_key(self) -> str:
        """Get JWT secret key from environment or use default"""
        import os
        return os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    
    async def get_current_user_from_token(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> UUID:
        """
        Extract and validate user from JWT token.
        
        Args:
            credentials: HTTP Bearer token credentials
            
        Returns:
            UUID: User ID from token
            
        Raises:
            HTTPException: 401 if token is invalid or expired
        """
        try:
            token = credentials.credentials
            
            # Decode JWT token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Extract user ID
            user_id_str = payload.get('user_id')
            if not user_id_str:
                raise AuthenticationError("User ID not found in token")
            
            user_id = UUID(user_id_str)
            
            # Validate token expiry
            exp = payload.get('exp')
            if exp and exp < self._get_current_timestamp():
                raise AuthenticationError("Token has expired")
            
            logger.info(f"Authenticated user {user_id} from JWT token")
            return user_id
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except AuthenticationError as e:
            logger.warning(f"Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
    
    async def get_current_user_from_session(
        self,
        session_data: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """
        Extract user from session data (for Flask-style sessions).
        
        Args:
            session_data: Session data dictionary
            
        Returns:
            UUID: User ID from session
            
        Raises:
            HTTPException: 401 if session is invalid
        """
        try:
            if not session_data:
                raise AuthenticationError("No session data provided")
            
            user_id_str = session_data.get('user_id')
            if not user_id_str:
                raise AuthenticationError("User ID not found in session")
            
            user_id = UUID(user_id_str)
            
            # Validate session is active
            if not session_data.get('authenticated', False):
                raise AuthenticationError("Session not authenticated")
            
            logger.info(f"Authenticated user {user_id} from session")
            return user_id
            
        except AuthenticationError as e:
            logger.warning(f"Session authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected session authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session authentication failed"
            )
    
    async def validate_user_permissions(
        self,
        user_id: UUID,
        required_permissions: Optional[list] = None
    ) -> bool:
        """
        Validate user permissions for upload operations.
        
        Args:
            user_id: User ID to validate
            required_permissions: List of required permissions
            
        Returns:
            bool: True if user has required permissions
            
        Raises:
            HTTPException: 403 if user lacks required permissions
        """
        try:
            # In a real implementation, this would check user roles/permissions
            # For now, we'll assume all authenticated users can upload
            
            if required_permissions:
                # Placeholder permission check
                user_permissions = await self._get_user_permissions(user_id)
                
                for permission in required_permissions:
                    if permission not in user_permissions:
                        logger.warning(f"User {user_id} lacks permission: {permission}")
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Insufficient permissions: {permission} required"
                        )
            
            logger.info(f"User {user_id} has required permissions")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Permission validation error for user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission validation failed"
            )
    
    async def _get_user_permissions(self, user_id: UUID) -> list:
        """
        Get user permissions from database or cache.
        This is a placeholder implementation.
        
        Args:
            user_id: User ID
            
        Returns:
            list: List of user permissions
        """
        # Placeholder - in real implementation, this would query user roles/permissions
        return ['upload_files', 'create_sessions', 'manage_quota']
    
    def _get_current_timestamp(self) -> int:
        """Get current timestamp for JWT validation"""
        import time
        return int(time.time())
    
    def create_user_token(self, user_id: UUID, additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """
        Create JWT token for user (for testing purposes).
        
        Args:
            user_id: User ID
            additional_claims: Additional claims to include in token
            
        Returns:
            str: JWT token
        """
        try:
            import time
            
            payload = {
                'user_id': str(user_id),
                'iat': self._get_current_timestamp(),
                'exp': self._get_current_timestamp() + (self.token_expiry_hours * 3600),
                'type': 'upload_session'
            }
            
            if additional_claims:
                payload.update(additional_claims)
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Created JWT token for user {user_id}")
            return token
            
        except Exception as e:
            logger.error(f"Failed to create token for user {user_id}: {e}")
            raise AuthenticationError(f"Token creation failed: {str(e)}")


# Global authentication service instance
auth_service = UserAuthentication()


# FastAPI dependency functions for authentication
async def get_current_user_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UUID:
    """
    FastAPI dependency to get current user from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        UUID: Current user ID
        
    Raises:
        HTTPException: 401 if authentication fails
    """
    return await auth_service.get_current_user_from_token(credentials)


async def get_current_user_session(
    session_data: Optional[Dict[str, Any]] = None
) -> UUID:
    """
    FastAPI dependency to get current user from session data.
    
    Args:
        session_data: Session data dictionary
        
    Returns:
        UUID: Current user ID
        
    Raises:
        HTTPException: 401 if authentication fails
    """
    return await auth_service.get_current_user_from_session(session_data)


async def require_upload_permissions(
    user_id: UUID = Depends(get_current_user_jwt),
    permissions: Optional[list] = None
) -> UUID:
    """
    FastAPI dependency to require upload permissions.
    
    Args:
        user_id: Current user ID
        permissions: Required permissions
        
    Returns:
        UUID: Current user ID
        
    Raises:
        HTTPException: 403 if user lacks required permissions
    """
    await auth_service.validate_user_permissions(user_id, permissions)
    return user_id


# Integration with existing Flask-style authentication
class FlaskAuthIntegration:
    """
    Integration layer for Flask-style authentication patterns.
    Provides compatibility with existing authentication mechanisms.
    """
    
    @staticmethod
    def extract_user_from_flask_session(session_data: Dict[str, Any]) -> Optional[UUID]:
        """
        Extract user ID from Flask session data.
        
        Args:
            session_data: Flask session data
            
        Returns:
            Optional[UUID]: User ID if found, None otherwise
        """
        try:
            user_id_str = session_data.get('user_id')
            if user_id_str:
                return UUID(user_id_str)
            return None
        except Exception as e:
            logger.error(f"Failed to extract user from Flask session: {e}")
            return None
    
    @staticmethod
    def is_flask_session_authenticated(session_data: Dict[str, Any]) -> bool:
        """
        Check if Flask session is authenticated.
        
        Args:
            session_data: Flask session data
            
        Returns:
            bool: True if session is authenticated
        """
        return session_data.get('authenticated', False) and session_data.get('user_id') is not None
    
    @staticmethod
    def create_fastapi_auth_from_flask(session_data: Dict[str, Any]) -> UUID:
        """
        Create FastAPI authentication from Flask session data.
        
        Args:
            session_data: Flask session data
            
        Returns:
            UUID: User ID
            
        Raises:
            HTTPException: 401 if session is not authenticated
        """
        if not FlaskAuthIntegration.is_flask_session_authenticated(session_data):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session not authenticated"
            )
        
        user_id = FlaskAuthIntegration.extract_user_from_flask_session(session_data)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session data"
            )
        
        return user_id


# Utility functions for authentication
def create_test_user_token(user_id: str = "12345678-1234-5678-9012-123456789012") -> str:
    """
    Create a test JWT token for development/testing purposes.
    
    Args:
        user_id: User ID string
        
    Returns:
        str: JWT token
    """
    return auth_service.create_user_token(UUID(user_id))


def validate_upload_session_ownership(session_user_id: UUID, requesting_user_id: UUID) -> bool:
    """
    Validate that a user owns an upload session.
    
    Args:
        session_user_id: User ID who owns the session
        requesting_user_id: User ID requesting access
        
    Returns:
        bool: True if user owns the session
    """
    return session_user_id == requesting_user_id


# Authentication middleware for request logging
class AuthenticationMiddleware:
    """Middleware for logging authentication events"""
    
    @staticmethod
    def log_authentication_event(
        user_id: UUID,
        event_type: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log authentication events for monitoring.
        
        Args:
            user_id: User ID
            event_type: Type of authentication event
            details: Additional event details
        """
        log_data = {
            'user_id': str(user_id),
            'event_type': event_type,
            'timestamp': auth_service._get_current_timestamp()
        }
        
        if details:
            log_data.update(details)
        
        logger.info(f"Authentication event: {json.dumps(log_data)}")
