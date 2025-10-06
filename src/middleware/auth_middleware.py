#!/usr/bin/env python3
"""
Analytics Authentication Middleware
Role-based access control for analytics data with AWS Cognito integration
"""

import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

from src.dependencies.auth import get_current_user_optional, UserClaims
from src.models.analytics_data import (
    AnalyticsRequest,
    DataClassification,
    AnalyticsPermission
)
from src.config.dashboard_config import get_aws_config

logger = structlog.get_logger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


class AnalyticsPermissionManager:
    """
    Manages analytics permissions and role-based access control
    Integrates with AWS Cognito for user authentication and authorization
    """
    
    def __init__(self):
        """Initialize analytics permission manager"""
        self.aws_config = get_aws_config()
        
        # Define role-based permissions matrix
        self.role_permissions = {
            "admin": {
                "read": [DataClassification.PUBLIC, DataClassification.INTERNAL, DataClassification.CONFIDENTIAL],
                "write": [DataClassification.PUBLIC, DataClassification.INTERNAL, DataClassification.CONFIDENTIAL],
                "export": [DataClassification.PUBLIC, DataClassification.INTERNAL, DataClassification.CONFIDENTIAL],
                "admin": [DataClassification.PUBLIC, DataClassification.INTERNAL, DataClassification.CONFIDENTIAL]
            },
            "analyst": {
                "read": [DataClassification.PUBLIC, DataClassification.INTERNAL],
                "write": [DataClassification.PUBLIC],
                "export": [DataClassification.PUBLIC, DataClassification.INTERNAL],
                "admin": []
            },
            "viewer": {
                "read": [DataClassification.PUBLIC],
                "write": [],
                "export": [DataClassification.PUBLIC],
                "admin": []
            },
            "system_admin": {
                "read": [DataClassification.PUBLIC, DataClassification.INTERNAL, DataClassification.CONFIDENTIAL],
                "write": [DataClassification.PUBLIC, DataClassification.INTERNAL],
                "export": [DataClassification.PUBLIC, DataClassification.INTERNAL, DataClassification.CONFIDENTIAL],
                "admin": [DataClassification.PUBLIC, DataClassification.INTERNAL]
            }
        }
        
        # Define resource-based permissions
        self.resource_permissions = {
            "detection_performance": {
                "admin": ["read", "write", "export", "admin"],
                "analyst": ["read", "export"],
                "viewer": ["read"],
                "system_admin": ["read", "write", "export", "admin"]
            },
            "user_engagement": {
                "admin": ["read", "write", "export", "admin"],
                "analyst": ["read", "export"],
                "viewer": [],  # No access to user engagement data for viewers
                "system_admin": ["read", "export", "admin"]
            },
            "system_utilization": {
                "admin": ["read", "write", "export", "admin"],
                "analyst": ["read", "export"],
                "viewer": ["read"],
                "system_admin": ["read", "write", "export", "admin"]
            },
            "blockchain_metrics": {
                "admin": ["read", "write", "export", "admin"],
                "analyst": ["read", "export"],
                "viewer": ["read"],
                "system_admin": ["read", "write", "export", "admin"]
            }
        }
        
        logger.info("AnalyticsPermissionManager initialized")
    
    def check_permission(
        self,
        user_claims: Optional[UserClaims],
        permission_type: str,
        resource: str,
        classification_level: DataClassification
    ) -> bool:
        """
        Check if user has permission to access resource
        
        Args:
            user_claims: User claims from JWT token
            permission_type: Type of permission (read, write, export, admin)
            resource: Resource being accessed
            classification_level: Data classification level
            
        Returns:
            True if permission is granted, False otherwise
        """
        try:
            # If no user claims, only allow public data read access
            if not user_claims:
                return (
                    permission_type == "read" and 
                    classification_level == DataClassification.PUBLIC
                )
            
            # Get user roles
            user_roles = user_claims.roles + user_claims.groups
            
            # Check if user has any role that grants permission
            for role in user_roles:
                if self._has_role_permission(role, permission_type, classification_level):
                    if self._has_resource_permission(role, resource, permission_type):
                        logger.debug(
                            "Permission granted",
                            user_id=user_claims.user_id,
                            role=role,
                            permission_type=permission_type,
                            resource=resource,
                            classification_level=classification_level.value
                        )
                        return True
            
            logger.warning(
                "Permission denied",
                user_id=user_claims.user_id,
                user_roles=user_roles,
                permission_type=permission_type,
                resource=resource,
                classification_level=classification_level.value
            )
            return False
            
        except Exception as e:
            logger.error(
                "Permission check failed",
                user_id=user_claims.user_id if user_claims else None,
                error=str(e)
            )
            return False
    
    def _has_role_permission(
        self,
        role: str,
        permission_type: str,
        classification_level: DataClassification
    ) -> bool:
        """Check if role has permission for classification level"""
        if role not in self.role_permissions:
            return False
        
        role_perm = self.role_permissions[role]
        if permission_type not in role_perm:
            return False
        
        return classification_level in role_perm[permission_type]
    
    def _has_resource_permission(
        self,
        role: str,
        resource: str,
        permission_type: str
    ) -> bool:
        """Check if role has permission for specific resource"""
        if resource not in self.resource_permissions:
            return True  # Default allow for unknown resources
        
        resource_perm = self.resource_permissions[resource]
        if role not in resource_perm:
            return False
        
        return permission_type in resource_perm[role]
    
    def get_user_data_access_level(
        self,
        user_claims: Optional[UserClaims]
    ) -> DataClassification:
        """
        Determine the highest data classification level user can access
        
        Args:
            user_claims: User claims from JWT token
            
        Returns:
            Highest data classification level user can access
        """
        if not user_claims:
            return DataClassification.PUBLIC
        
        user_roles = user_claims.roles + user_claims.groups
        
        # Find highest classification level across all roles
        highest_level = DataClassification.PUBLIC
        
        for role in user_roles:
            if role in self.role_permissions:
                role_perm = self.role_permissions[role]
                if "read" in role_perm:
                    for classification in role_perm["read"]:
                        if classification.value == "confidential" and highest_level != DataClassification.CONFIDENTIAL:
                            highest_level = DataClassification.CONFIDENTIAL
                        elif classification.value == "internal" and highest_level == DataClassification.PUBLIC:
                            highest_level = DataClassification.INTERNAL
        
        return highest_level
    
    def validate_analytics_request(
        self,
        user_claims: Optional[UserClaims],
        request: AnalyticsRequest
    ) -> AnalyticsRequest:
        """
        Validate and filter analytics request based on user permissions
        
        Args:
            user_claims: User claims from JWT token
            request: Analytics request to validate
            
        Returns:
            Validated and filtered request
            
        Raises:
            HTTPException: If request is not authorized
        """
        try:
            # Determine user's data access level
            user_access_level = self.get_user_data_access_level(user_claims)
            
            # Filter out requests for data user cannot access
            # This would be implemented based on specific business rules
            
            # Check export permissions if export is requested
            if request.export_format:
                has_export_permission = False
                for resource in ["detection_performance", "user_engagement", "system_utilization"]:
                    if self.check_permission(
                        user_claims, "export", resource, user_access_level
                    ):
                        has_export_permission = True
                        break
                
                if not has_export_permission:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions for data export"
                    )
            
            logger.debug(
                "Analytics request validated",
                user_id=user_claims.user_id if user_claims else None,
                access_level=user_access_level.value,
                export_format=request.export_format
            )
            
            return request
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Analytics request validation failed",
                user_id=user_claims.user_id if user_claims else None,
                error=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Request validation failed"
            )
    
    def create_permission_record(
        self,
        user_claims: UserClaims,
        permission_type: str,
        resource: str,
        classification_level: DataClassification,
        granted: bool
    ) -> AnalyticsPermission:
        """
        Create a permission record for audit purposes
        
        Args:
            user_claims: User claims from JWT token
            permission_type: Type of permission requested
            resource: Resource being accessed
            classification_level: Data classification level
            granted: Whether permission was granted
            
        Returns:
            Permission record for audit
        """
        return AnalyticsPermission(
            user_id=user_claims.user_id,
            permission_type=permission_type,
            resource=resource,
            classification_level=classification_level,
            granted=granted,
            granted_by="system",
            granted_at=datetime.now(timezone.utc)
        )


class AnalyticsAuthMiddleware:
    """
    Middleware for analytics authentication and authorization
    Provides dependency injection for role-based access control
    """
    
    def __init__(self):
        """Initialize analytics auth middleware"""
        self.permission_manager = AnalyticsPermissionManager()
        
        logger.info("AnalyticsAuthMiddleware initialized")
    
    async def require_analytics_access(
        self,
        permission_type: str,
        resource: str,
        classification_level: DataClassification,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> UserClaims:
        """
        Dependency for requiring specific analytics access
        
        Args:
            permission_type: Type of permission required
            resource: Resource being accessed
            classification_level: Required data classification level
            credentials: HTTP authorization credentials
            
        Returns:
            User claims if access is granted
            
        Raises:
            HTTPException: If access is denied
        """
        try:
            # Get user claims (this will handle authentication)
            from src.dependencies.auth import get_current_user
            user_claims = await get_current_user(credentials)
            
            # Check permission
            has_permission = self.permission_manager.check_permission(
                user_claims, permission_type, resource, classification_level
            )
            
            if not has_permission:
                # Create audit record
                permission_record = self.permission_manager.create_permission_record(
                    user_claims, permission_type, resource, classification_level, False
                )
                
                logger.warning(
                    "Analytics access denied",
                    user_id=user_claims.user_id,
                    permission_type=permission_type,
                    resource=resource,
                    classification_level=classification_level.value
                )
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied for {resource} at {classification_level.value} level"
                )
            
            # Create audit record for granted access
            permission_record = self.permission_manager.create_permission_record(
                user_claims, permission_type, resource, classification_level, True
            )
            
            logger.info(
                "Analytics access granted",
                user_id=user_claims.user_id,
                permission_type=permission_type,
                resource=resource,
                classification_level=classification_level.value
            )
            
            return user_claims
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Analytics access check failed",
                error=str(e)
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Access check failed"
            )
    
    async def get_user_analytics_context(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Dict[str, Any]:
        """
        Get user analytics context including permissions and access levels
        
        Args:
            credentials: HTTP authorization credentials
            
        Returns:
            User analytics context
        """
        try:
            from src.dependencies.auth import get_current_user_optional
            user_claims = await get_current_user_optional(credentials)
            
            if not user_claims:
                return {
                    "authenticated": False,
                    "data_access_level": DataClassification.PUBLIC.value,
                    "permissions": {
                        "read": [DataClassification.PUBLIC.value],
                        "write": [],
                        "export": [DataClassification.PUBLIC.value],
                        "admin": []
                    },
                    "available_resources": ["detection_performance", "system_utilization"]
                }
            
            # Get user's data access level
            access_level = self.permission_manager.get_user_data_access_level(user_claims)
            
            # Build permissions summary
            permissions = {
                "read": [],
                "write": [],
                "export": [],
                "admin": []
            }
            
            available_resources = []
            
            for role in user_claims.roles + user_claims.groups:
                if role in self.permission_manager.role_permissions:
                    role_perm = self.permission_manager.role_permissions[role]
                    
                    for perm_type, classifications in role_perm.items():
                        for classification in classifications:
                            if classification.value not in permissions[perm_type]:
                                permissions[perm_type].append(classification.value)
                
                # Check resource access
                for resource, resource_perm in self.permission_manager.resource_permissions.items():
                    if role in resource_perm and "read" in resource_perm[role]:
                        if resource not in available_resources:
                            available_resources.append(resource)
            
            return {
                "authenticated": True,
                "user_id": user_claims.user_id,
                "user_roles": user_claims.roles + user_claims.groups,
                "data_access_level": access_level.value,
                "permissions": permissions,
                "available_resources": available_resources
            }
            
        except Exception as e:
            logger.error("Failed to get user analytics context", error=str(e))
            return {
                "authenticated": False,
                "error": "Failed to determine user context"
            }


# Global middleware instance
_analytics_auth_middleware: Optional[AnalyticsAuthMiddleware] = None


def get_analytics_auth_middleware() -> AnalyticsAuthMiddleware:
    """Get global analytics auth middleware instance"""
    global _analytics_auth_middleware
    
    if _analytics_auth_middleware is None:
        _analytics_auth_middleware = AnalyticsAuthMiddleware()
    
    return _analytics_auth_middleware


# Convenience dependency functions
async def require_analytics_read(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserClaims:
    """Require analytics read access"""
    middleware = get_analytics_auth_middleware()
    return await middleware.require_analytics_access(
        "read", "analytics", DataClassification.INTERNAL, credentials
    )


async def require_analytics_export(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserClaims:
    """Require analytics export access"""
    middleware = get_analytics_auth_middleware()
    return await middleware.require_analytics_access(
        "export", "analytics", DataClassification.INTERNAL, credentials
    )


async def require_analytics_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserClaims:
    """Require analytics admin access"""
    middleware = get_analytics_auth_middleware()
    return await middleware.require_analytics_access(
        "admin", "analytics", DataClassification.CONFIDENTIAL, credentials
    )


async def get_analytics_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """Get user analytics context"""
    middleware = get_analytics_auth_middleware()
    return await middleware.get_user_analytics_context(credentials)
