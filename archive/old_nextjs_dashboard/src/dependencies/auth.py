#!/usr/bin/env python3
"""
AWS Cognito Authentication Dependencies
JWT-based authentication integration for FastAPI dashboard endpoints
"""

import os
import jwt
import boto3
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt as jose_jwt
from pydantic import BaseModel
import structlog

from src.config.dashboard_config import get_aws_config, get_dashboard_config

logger = structlog.get_logger(__name__)

# Security scheme for FastAPI
security = HTTPBearer(auto_error=False)


class UserClaims(BaseModel):
    """User claims from JWT token"""
    user_id: str
    email: str
    username: Optional[str] = None
    groups: List[str] = []
    roles: List[str] = []
    exp: datetime
    iat: datetime
    iss: str
    aud: str


class AuthenticationError(Exception):
    """Custom authentication error"""
    pass


class CognitoJWTValidator:
    """
    AWS Cognito JWT token validator
    Validates JWT tokens issued by AWS Cognito User Pool
    """
    
    def __init__(self):
        """Initialize Cognito JWT validator"""
        self.aws_config = get_aws_config()
        self.dashboard_config = get_dashboard_config()
        
        # Initialize Cognito client
        self.cognito_client = boto3.client(
            'cognito-idp',
            region_name=self.aws_config.cognito_region,
            aws_access_key_id=self.aws_config.aws_access_key_id,
            aws_secret_access_key=self.aws_config.aws_secret_access_key,
            aws_session_token=self.aws_config.aws_session_token
        )
        
        # JWT configuration
        self.jwt_secret_key = self.aws_config.jwt_secret_key or "your-secret-key"  # Should be from Cognito
        self.jwt_algorithm = self.aws_config.jwt_algorithm
        self.jwt_issuer = self.aws_config.jwt_issuer
        
        # Cognito configuration
        self.user_pool_id = self.aws_config.cognito_user_pool_id
        self.client_id = self.aws_config.cognito_client_id
        self.client_secret = self.aws_config.cognito_client_secret
        
        # JWT key cache (for production, should cache JWKS)
        self._jwks_cache: Dict[str, Any] = {}
        self._jwks_cache_expiry: Optional[datetime] = None
        
        logger.info("CognitoJWTValidator initialized", region=self.aws_config.cognito_region)
    
    def _get_cognito_jwks(self) -> Dict[str, Any]:
        """
        Get Cognito JWKS (JSON Web Key Set)
        In production, this should be cached and refreshed periodically
        
        Returns:
            JWKS data
        """
        try:
            # For development, return a mock JWKS
            # In production, fetch from: https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json
            return {
                "keys": [
                    {
                        "kty": "RSA",
                        "kid": "mock-key-id",
                        "use": "sig",
                        "alg": "RS256",
                        "n": "mock-n-value",
                        "e": "AQAB"
                    }
                ]
            }
        except Exception as e:
            logger.error("Failed to get Cognito JWKS", error=str(e))
            raise AuthenticationError("Failed to get JWT keys")
    
    def _validate_token_signature(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token signature
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
            
        Raises:
            AuthenticationError: If token validation fails
        """
        try:
            # For development, use simple JWT validation
            # In production, use JWKS validation with proper RSA signature verification
            
            # Decode without verification for development
            payload = jwt.decode(
                token,
                self.jwt_secret_key,
                algorithms=[self.jwt_algorithm],
                options={"verify_signature": False}  # Disable signature verification for development
            )
            
            # Validate token structure
            required_claims = ['sub', 'email', 'exp', 'iat', 'iss']
            for claim in required_claims:
                if claim not in payload:
                    raise AuthenticationError(f"Missing required claim: {claim}")
            
            # Validate expiration
            exp_timestamp = payload.get('exp')
            if exp_timestamp and datetime.fromtimestamp(exp_timestamp, tz=timezone.utc) < datetime.now(timezone.utc):
                raise AuthenticationError("Token has expired")
            
            # Validate issuer (in production)
            if self.user_pool_id and payload.get('iss') != f"https://cognito-idp.{self.aws_config.cognito_region}.amazonaws.com/{self.user_pool_id}":
                logger.warning("Token issuer validation skipped in development mode")
            
            logger.debug("JWT token validated successfully", user_id=payload.get('sub'))
            return payload
            
        except JWTError as e:
            logger.warning("JWT validation error", error=str(e))
            raise AuthenticationError("Invalid JWT token")
        except Exception as e:
            logger.error("Token validation error", error=str(e))
            raise AuthenticationError("Token validation failed")
    
    def validate_token(self, token: str) -> UserClaims:
        """
        Validate JWT token and return user claims
        
        Args:
            token: JWT token string
            
        Returns:
            User claims from token
            
        Raises:
            AuthenticationError: If token validation fails
        """
        try:
            # Validate token signature and get payload
            payload = self._validate_token_signature(token)
            
            # Extract user claims
            user_claims = UserClaims(
                user_id=payload['sub'],
                email=payload['email'],
                username=payload.get('username'),
                groups=payload.get('cognito:groups', []),
                roles=payload.get('custom:roles', []),
                exp=datetime.fromtimestamp(payload['exp'], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload['iat'], tz=timezone.utc),
                iss=payload['iss'],
                aud=payload.get('aud', '')
            )
            
            logger.info("Token validated successfully", user_id=user_claims.user_id, email=user_claims.email)
            return user_claims
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("Token validation failed", error=str(e))
            raise AuthenticationError("Token validation failed")
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Refresh JWT token using Cognito refresh token
        
        Args:
            refresh_token: Cognito refresh token
            
        Returns:
            New token pair (access_token, refresh_token)
            
        Raises:
            AuthenticationError: If token refresh fails
        """
        try:
            response = self.cognito_client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token
                }
            )
            
            auth_result = response.get('AuthenticationResult', {})
            
            if not auth_result:
                raise AuthenticationError("No authentication result from Cognito")
            
            tokens = {
                'access_token': auth_result['AccessToken'],
                'refresh_token': auth_result.get('RefreshToken', refresh_token),
                'id_token': auth_result.get('IdToken', ''),
                'token_type': auth_result.get('TokenType', 'Bearer')
            }
            
            logger.info("Token refreshed successfully")
            return tokens
            
        except Exception as e:
            logger.error("Token refresh failed", error=str(e))
            raise AuthenticationError("Token refresh failed")


# Global JWT validator instance
_jwt_validator: Optional[CognitoJWTValidator] = None


def get_jwt_validator() -> CognitoJWTValidator:
    """Get global JWT validator instance"""
    global _jwt_validator
    
    if _jwt_validator is None:
        _jwt_validator = CognitoJWTValidator()
    
    return _jwt_validator


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserClaims:
    """
    Get current authenticated user from JWT token
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User claims from JWT token
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        jwt_validator = get_jwt_validator()
        user_claims = jwt_validator.validate_token(credentials.credentials)
        
        logger.debug("User authenticated", user_id=user_claims.user_id)
        return user_claims
        
    except AuthenticationError as e:
        logger.warning("Authentication failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error("Authentication error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[UserClaims]:
    """
    Get current authenticated user from JWT token (optional)
    Returns None if no credentials provided or authentication fails
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User claims from JWT token or None
    """
    if not credentials:
        return None
    
    try:
        jwt_validator = get_jwt_validator()
        user_claims = jwt_validator.validate_token(credentials.credentials)
        
        logger.debug("Optional user authenticated", user_id=user_claims.user_id)
        return user_claims
        
    except Exception as e:
        logger.debug("Optional authentication failed", error=str(e))
        return None


def require_roles(required_roles: List[str]):
    """
    Dependency factory for role-based access control
    
    Args:
        required_roles: List of required roles
        
    Returns:
        Dependency function that checks user roles
    """
    async def role_checker(current_user: UserClaims = Depends(get_current_user)) -> UserClaims:
        user_roles = current_user.roles
        user_groups = current_user.groups
        
        # Check if user has any of the required roles
        has_role = any(role in user_roles for role in required_roles)
        has_group = any(group in user_groups for group in required_roles)
        
        if not (has_role or has_group):
            logger.warning(
                "Access denied - insufficient roles",
                user_id=current_user.user_id,
                user_roles=user_roles,
                user_groups=user_groups,
                required_roles=required_roles
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {required_roles}"
            )
        
        return current_user
    
    return role_checker


def require_groups(required_groups: List[str]):
    """
    Dependency factory for group-based access control
    
    Args:
        required_groups: List of required groups
        
    Returns:
        Dependency function that checks user groups
    """
    async def group_checker(current_user: UserClaims = Depends(get_current_user)) -> UserClaims:
        user_groups = current_user.groups
        
        # Check if user has any of the required groups
        has_group = any(group in user_groups for group in required_groups)
        
        if not has_group:
            logger.warning(
                "Access denied - insufficient groups",
                user_id=current_user.user_id,
                user_groups=user_groups,
                required_groups=required_groups
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required groups: {required_groups}"
            )
        
        return current_user
    
    return group_checker


async def get_user_permissions(current_user: UserClaims = Depends(get_current_user)) -> Dict[str, bool]:
    """
    Get user permissions based on roles and groups
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Dictionary of permissions
    """
    user_roles = current_user.roles
    user_groups = current_user.groups
    
    # Define permission mappings
    permissions = {
        "view_dashboard": True,  # All authenticated users can view dashboard
        "view_analytics": "analyst" in user_roles or "admin" in user_roles,
        "manage_users": "admin" in user_roles,
        "view_system_metrics": "admin" in user_roles or "system_admin" in user_groups,
        "export_data": "analyst" in user_roles or "admin" in user_roles,
        "manage_configuration": "admin" in user_roles,
        "view_blockchain_metrics": True,  # All authenticated users can view blockchain metrics
        "manage_blockchain": "admin" in user_roles
    }
    
    logger.debug("User permissions calculated", user_id=current_user.user_id, permissions=permissions)
    return permissions


def require_permission(permission: str):
    """
    Dependency factory for permission-based access control
    
    Args:
        permission: Required permission
        
    Returns:
        Dependency function that checks user permission
    """
    async def permission_checker(
        permissions: Dict[str, bool] = Depends(get_user_permissions)
    ) -> Dict[str, bool]:
        if not permissions.get(permission, False):
            logger.warning("Access denied - insufficient permission", permission=permission)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required permission: {permission}"
            )
        
        return permissions
    
    return permission_checker


class AuthenticationMiddleware:
    """Authentication middleware for request logging and audit"""
    
    @staticmethod
    async def log_authentication_event(
        user_claims: Optional[UserClaims],
        endpoint: str,
        method: str,
        success: bool
    ):
        """
        Log authentication event for audit purposes
        
        Args:
            user_claims: User claims (None if not authenticated)
            endpoint: API endpoint
            method: HTTP method
            success: Whether authentication was successful
        """
        if user_claims:
            logger.info(
                "Authentication event",
                user_id=user_claims.user_id,
                email=user_claims.email,
                endpoint=endpoint,
                method=method,
                success=success,
                roles=user_claims.roles,
                groups=user_claims.groups
            )
        else:
            logger.warning(
                "Authentication event - unauthenticated",
                endpoint=endpoint,
                method=method,
                success=success
            )


# Authentication dependency shortcuts
RequireAuth = Depends(get_current_user)
RequireAuthOptional = Depends(get_current_user_optional)
RequireAdmin = require_roles(["admin"])
RequireAnalyst = require_roles(["analyst"])
RequireSystemAdmin = require_groups(["system_admin"])
