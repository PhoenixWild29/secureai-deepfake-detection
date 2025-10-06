#!/usr/bin/env python3
"""
WebSocket Authentication for Notification Channels
Extended WebSocket authentication logic to include authorization checks for specific
notification channels or types, ensuring clients only receive notifications they are permitted to see.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Set
from uuid import UUID
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass

from src.notifications.schemas import NotificationEventType, NotificationPriority

logger = logging.getLogger(__name__)


class PermissionLevel(str, Enum):
    """Enumeration of permission levels for notification access."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class NotificationScope(str, Enum):
    """Enumeration of notification scopes."""
    OWN_ANALYSES = "own_analyses"
    TEAM_ANALYSES = "team_analyses"
    ALL_ANALYSES = "all_analyses"
    SYSTEM_NOTIFICATIONS = "system_notifications"
    ADMIN_NOTIFICATIONS = "admin_notifications"


@dataclass
class NotificationPermission:
    """Represents a notification permission for a user."""
    user_id: str
    permission_level: PermissionLevel
    allowed_event_types: Set[NotificationEventType]
    allowed_scopes: Set[NotificationScope]
    allowed_analyses: Set[str]  # Analysis IDs user can access
    max_concurrent_subscriptions: int = 10
    rate_limit_per_minute: int = 100
    expires_at: Optional[datetime] = None
    
    def is_valid(self) -> bool:
        """Check if permission is still valid."""
        if self.expires_at is None:
            return True
        return datetime.now(timezone.utc) < self.expires_at
    
    def can_access_event_type(self, event_type: NotificationEventType) -> bool:
        """Check if user can access a specific event type."""
        return event_type in self.allowed_event_types
    
    def can_access_analysis(self, analysis_id: str) -> bool:
        """Check if user can access a specific analysis."""
        if NotificationScope.ALL_ANALYSES in self.allowed_scopes:
            return True
        return analysis_id in self.allowed_analyses
    
    def can_access_scope(self, scope: NotificationScope) -> bool:
        """Check if user can access a specific scope."""
        return scope in self.allowed_scopes


@dataclass
class ClientAuthContext:
    """Authentication context for a WebSocket client."""
    client_id: str
    user_id: str
    session_token: str
    permissions: NotificationPermission
    connected_at: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)
    
    def is_session_valid(self, max_inactivity_minutes: int = 60) -> bool:
        """Check if session is still valid."""
        if not self.permissions.is_valid():
            return False
        
        inactivity_threshold = datetime.now(timezone.utc) - timedelta(minutes=max_inactivity_minutes)
        return self.last_activity > inactivity_threshold


class NotificationAuthManager:
    """
    Authentication manager for WebSocket notification channels.
    Handles client authentication, authorization, and permission management
    for real-time notification delivery.
    """
    
    def __init__(self):
        """Initialize the notification authentication manager."""
        self.authenticated_clients: Dict[str, ClientAuthContext] = {}
        self.user_permissions: Dict[str, NotificationPermission] = {}
        self.session_tokens: Dict[str, str] = {}  # token -> user_id
        
        # Configuration
        self.session_timeout_minutes = 60
        self.max_concurrent_sessions_per_user = 5
        self.default_permission_level = PermissionLevel.READ
        
        # Rate limiting
        self.client_rate_limits: Dict[str, Dict[str, Any]] = {}  # client_id -> rate_limit_data
        self.rate_limit_window_minutes = 1
        self.default_rate_limit = 100  # notifications per minute
        
        # Statistics
        self.auth_stats = {
            "total_authentications": 0,
            "failed_authentications": 0,
            "active_sessions": 0,
            "permission_denials": 0,
            "rate_limit_hits": 0
        }
    
    async def authenticate_client(
        self,
        client_id: str,
        session_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[ClientAuthContext]:
        """
        Authenticate a WebSocket client.
        
        Args:
            client_id: Client identifier
            session_token: Session authentication token
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            ClientAuthContext if authentication successful, None otherwise
        """
        try:
            # Validate session token
            user_id = await self._validate_session_token(session_token)
            if not user_id:
                logger.warning(f"Invalid session token for client {client_id}")
                self.auth_stats["failed_authentications"] += 1
                return None
            
            # Check concurrent session limit
            if not await self._check_session_limit(user_id):
                logger.warning(f"User {user_id} exceeded concurrent session limit")
                self.auth_stats["failed_authentications"] += 1
                return None
            
            # Get user permissions
            permissions = await self._get_user_permissions(user_id)
            if not permissions:
                logger.warning(f"No permissions found for user {user_id}")
                self.auth_stats["failed_authentications"] += 1
                return None
            
            # Create authentication context
            auth_context = ClientAuthContext(
                client_id=client_id,
                user_id=user_id,
                session_token=session_token,
                permissions=permissions,
                connected_at=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc),
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Register authenticated client
            self.authenticated_clients[client_id] = auth_context
            self.session_tokens[session_token] = user_id
            
            # Initialize rate limiting for client
            self._initialize_rate_limiting(client_id, permissions.rate_limit_per_minute)
            
            # Update statistics
            self.auth_stats["total_authentications"] += 1
            self.auth_stats["active_sessions"] = len(self.authenticated_clients)
            
            logger.info(f"Client {client_id} authenticated as user {user_id}")
            return auth_context
            
        except Exception as e:
            logger.error(f"Error authenticating client {client_id}: {e}")
            self.auth_stats["failed_authentications"] += 1
            return None
    
    async def deauthenticate_client(self, client_id: str) -> bool:
        """
        Deauthenticate a WebSocket client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            bool: True if successful
        """
        try:
            if client_id in self.authenticated_clients:
                auth_context = self.authenticated_clients[client_id]
                
                # Clean up session token
                self.session_tokens.pop(auth_context.session_token, None)
                
                # Remove client
                del self.authenticated_clients[client_id]
                
                # Clean up rate limiting
                self.client_rate_limits.pop(client_id, None)
                
                # Update statistics
                self.auth_stats["active_sessions"] = len(self.authenticated_clients)
                
                logger.info(f"Client {client_id} deauthenticated")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deauthenticating client {client_id}: {e}")
            return False
    
    async def authorize_notification_access(
        self,
        client_id: str,
        event_type: NotificationEventType,
        analysis_id: Optional[str] = None,
        scope: Optional[NotificationScope] = None
    ) -> bool:
        """
        Authorize a client's access to a specific notification.
        
        Args:
            client_id: Client identifier
            event_type: Type of notification event
            analysis_id: Analysis identifier (if applicable)
            scope: Notification scope
            
        Returns:
            bool: True if authorized
        """
        try:
            # Get client authentication context
            auth_context = self.authenticated_clients.get(client_id)
            if not auth_context:
                logger.warning(f"Unauthenticated client {client_id} attempted notification access")
                self.auth_stats["permission_denials"] += 1
                return False
            
            # Check session validity
            if not auth_context.is_session_valid(self.session_timeout_minutes):
                logger.warning(f"Expired session for client {client_id}")
                await self.deauthenticate_client(client_id)
                self.auth_stats["permission_denials"] += 1
                return False
            
            # Update activity
            auth_context.update_activity()
            
            # Check event type permission
            if not auth_context.permissions.can_access_event_type(event_type):
                logger.warning(f"Client {client_id} not authorized for event type {event_type}")
                self.auth_stats["permission_denials"] += 1
                return False
            
            # Check analysis access if applicable
            if analysis_id and not auth_context.permissions.can_access_analysis(analysis_id):
                logger.warning(f"Client {client_id} not authorized for analysis {analysis_id}")
                self.auth_stats["permission_denials"] += 1
                return False
            
            # Check scope access if applicable
            if scope and not auth_context.permissions.can_access_scope(scope):
                logger.warning(f"Client {client_id} not authorized for scope {scope}")
                self.auth_stats["permission_denials"] += 1
                return False
            
            # Check rate limiting
            if not self._check_rate_limit(client_id):
                logger.warning(f"Client {client_id} exceeded rate limit")
                self.auth_stats["rate_limit_hits"] += 1
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error authorizing notification access for client {client_id}: {e}")
            self.auth_stats["permission_denials"] += 1
            return False
    
    async def authorize_subscription(
        self,
        client_id: str,
        analysis_id: str,
        event_types: List[NotificationEventType]
    ) -> bool:
        """
        Authorize a client's subscription to analysis notifications.
        
        Args:
            client_id: Client identifier
            analysis_id: Analysis identifier
            event_types: Event types to subscribe to
            
        Returns:
            bool: True if authorized
        """
        try:
            auth_context = self.authenticated_clients.get(client_id)
            if not auth_context:
                return False
            
            # Check analysis access
            if not auth_context.permissions.can_access_analysis(analysis_id):
                return False
            
            # Check event type permissions
            for event_type in event_types:
                if not auth_context.permissions.can_access_event_type(event_type):
                    return False
            
            # Check subscription limits
            current_subscriptions = await self._get_client_subscription_count(client_id)
            if current_subscriptions >= auth_context.permissions.max_concurrent_subscriptions:
                logger.warning(f"Client {client_id} exceeded subscription limit")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error authorizing subscription for client {client_id}: {e}")
            return False
    
    async def _validate_session_token(self, session_token: str) -> Optional[str]:
        """
        Validate a session token and return user ID.
        
        Args:
            session_token: Session token to validate
            
        Returns:
            User ID if valid, None otherwise
        """
        try:
            # In a real implementation, this would validate against your authentication system
            # For now, we'll simulate token validation
            
            if session_token in self.session_tokens:
                return self.session_tokens[session_token]
            
            # Simulate token validation
            if session_token.startswith("valid_"):
                user_id = session_token.replace("valid_", "")
                self.session_tokens[session_token] = user_id
                return user_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error validating session token: {e}")
            return None
    
    async def _check_session_limit(self, user_id: str) -> bool:
        """
        Check if user has reached concurrent session limit.
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if within limit
        """
        try:
            current_sessions = sum(
                1 for auth_context in self.authenticated_clients.values()
                if auth_context.user_id == user_id
            )
            
            return current_sessions < self.max_concurrent_sessions_per_user
            
        except Exception as e:
            logger.error(f"Error checking session limit for user {user_id}: {e}")
            return False
    
    async def _get_user_permissions(self, user_id: str) -> Optional[NotificationPermission]:
        """
        Get notification permissions for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            NotificationPermission if found, None otherwise
        """
        try:
            # Check cache first
            if user_id in self.user_permissions:
                permissions = self.user_permissions[user_id]
                if permissions.is_valid():
                    return permissions
            
            # In a real implementation, this would fetch from database
            # For now, we'll create default permissions
            permissions = self._create_default_permissions(user_id)
            
            # Cache permissions
            self.user_permissions[user_id] = permissions
            
            return permissions
            
        except Exception as e:
            logger.error(f"Error getting permissions for user {user_id}: {e}")
            return None
    
    def _create_default_permissions(self, user_id: str) -> NotificationPermission:
        """Create default permissions for a user."""
        return NotificationPermission(
            user_id=user_id,
            permission_level=self.default_permission_level,
            allowed_event_types={
                NotificationEventType.STATUS_UPDATE,
                NotificationEventType.RESULT_UPDATE,
                NotificationEventType.STAGE_TRANSITION,
                NotificationEventType.ERROR_NOTIFICATION,
                NotificationEventType.COMPLETION_NOTIFICATION
            },
            allowed_scopes={
                NotificationScope.OWN_ANALYSES,
                NotificationScope.SYSTEM_NOTIFICATIONS
            },
            allowed_analyses=set(),  # Will be populated dynamically
            max_concurrent_subscriptions=10,
            rate_limit_per_minute=self.default_rate_limit
        )
    
    def _initialize_rate_limiting(self, client_id: str, rate_limit: int):
        """Initialize rate limiting for a client."""
        self.client_rate_limits[client_id] = {
            "rate_limit": rate_limit,
            "requests": [],
            "window_start": datetime.now(timezone.utc)
        }
    
    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit."""
        try:
            if client_id not in self.client_rate_limits:
                return True
            
            rate_data = self.client_rate_limits[client_id]
            current_time = datetime.now(timezone.utc)
            
            # Clean old requests
            window_start = current_time - timedelta(minutes=self.rate_limit_window_minutes)
            rate_data["requests"] = [
                req_time for req_time in rate_data["requests"]
                if req_time > window_start
            ]
            
            # Check limit
            if len(rate_data["requests"]) >= rate_data["rate_limit"]:
                return False
            
            # Add current request
            rate_data["requests"].append(current_time)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit for client {client_id}: {e}")
            return True  # Allow on error
    
    async def _get_client_subscription_count(self, client_id: str) -> int:
        """Get current subscription count for a client."""
        try:
            # In a real implementation, this would query the subscription manager
            # For now, return 0
            return 0
            
        except Exception as e:
            logger.error(f"Error getting subscription count for client {client_id}: {e}")
            return 0
    
    async def update_user_permissions(
        self,
        user_id: str,
        permissions: NotificationPermission
    ) -> bool:
        """
        Update permissions for a user.
        
        Args:
            user_id: User identifier
            permissions: New permissions
            
        Returns:
            bool: True if successful
        """
        try:
            self.user_permissions[user_id] = permissions
            
            # Update existing authenticated clients
            for auth_context in self.authenticated_clients.values():
                if auth_context.user_id == user_id:
                    auth_context.permissions = permissions
            
            logger.info(f"Updated permissions for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating permissions for user {user_id}: {e}")
            return False
    
    async def add_analysis_access(self, user_id: str, analysis_id: str) -> bool:
        """
        Add analysis access for a user.
        
        Args:
            user_id: User identifier
            analysis_id: Analysis identifier
            
        Returns:
            bool: True if successful
        """
        try:
            if user_id in self.user_permissions:
                self.user_permissions[user_id].allowed_analyses.add(analysis_id)
                
                # Update existing authenticated clients
                for auth_context in self.authenticated_clients.values():
                    if auth_context.user_id == user_id:
                        auth_context.permissions.allowed_analyses.add(analysis_id)
                
                logger.info(f"Added analysis {analysis_id} access for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error adding analysis access for user {user_id}: {e}")
            return False
    
    def get_auth_context(self, client_id: str) -> Optional[ClientAuthContext]:
        """Get authentication context for a client."""
        return self.authenticated_clients.get(client_id)
    
    def get_auth_stats(self) -> Dict[str, Any]:
        """Get authentication statistics."""
        return {
            "auth_stats": self.auth_stats,
            "authenticated_clients": len(self.authenticated_clients),
            "cached_permissions": len(self.user_permissions),
            "active_sessions": len(self.session_tokens),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Global authentication manager instance
_auth_manager: Optional[NotificationAuthManager] = None


def get_notification_auth_manager() -> NotificationAuthManager:
    """Get the global notification authentication manager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = NotificationAuthManager()
    return _auth_manager


# Convenience functions
async def authenticate_websocket_client(
    client_id: str,
    session_token: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Optional[ClientAuthContext]:
    """
    Convenience function to authenticate a WebSocket client.
    
    Args:
        client_id: Client identifier
        session_token: Session token
        ip_address: Client IP address
        user_agent: Client user agent
        
    Returns:
        ClientAuthContext if successful, None otherwise
    """
    auth_manager = get_notification_auth_manager()
    return await auth_manager.authenticate_client(client_id, session_token, ip_address, user_agent)


async def authorize_notification(
    client_id: str,
    event_type: NotificationEventType,
    analysis_id: Optional[str] = None
) -> bool:
    """
    Convenience function to authorize notification access.
    
    Args:
        client_id: Client identifier
        event_type: Event type
        analysis_id: Analysis identifier
        
    Returns:
        bool: True if authorized
    """
    auth_manager = get_notification_auth_manager()
    return await auth_manager.authorize_notification_access(client_id, event_type, analysis_id)


# Export all classes and functions
__all__ = [
    'PermissionLevel',
    'NotificationScope',
    'NotificationPermission',
    'ClientAuthContext',
    'NotificationAuthManager',
    'get_notification_auth_manager',
    'authenticate_websocket_client',
    'authorize_notification'
]