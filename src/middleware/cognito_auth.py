#!/usr/bin/env python3
"""
AWS Cognito Authentication Middleware
Middleware for JWT token validation and user authentication with AWS Cognito
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from functools import wraps

import jwt
import requests
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..errors.api_errors import AuthenticationError, CognitoError, ConfigurationError


# Configure logging
logger = logging.getLogger(__name__)


class CognitoAuth:
    """
    AWS Cognito authentication handler with JWT token validation.
    """
    
    def __init__(
        self,
        user_pool_id: Optional[str] = None,
        client_id: Optional[str] = None,
        region: Optional[str] = None,
        enable_cache: bool = True,
        cache_ttl: int = 3600
    ):
        """
        Initialize Cognito authentication handler.
        
        Args:
            user_pool_id: AWS Cognito User Pool ID
            client_id: AWS Cognito App Client ID
            region: AWS region
            enable_cache: Whether to enable token validation cache
            cache_ttl: Cache time-to-live in seconds
        """
        self.user_pool_id = user_pool_id or os.getenv('COGNITO_USER_POOL_ID')
        self.client_id = client_id or os.getenv('COGNITO_CLIENT_ID')
        self.region = region or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        
        # Validate configuration
        if not self.user_pool_id:
            raise ConfigurationError("COGNITO_USER_POOL_ID not configured")
        if not self.client_id:
            raise ConfigurationError("COGNITO_CLIENT_ID not configured")
        
        # Construct JWKS URL
        self.jwks_url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
        
        # Token validation cache
        self.token_cache: Dict[str, Dict[str, Any]] = {}
        
        # Load JWKS keys
        self.jwks_keys = self._load_jwks_keys()
    
    def _load_jwks_keys(self) -> Dict[str, Any]:
        """
        Load JSON Web Key Set (JWKS) from Cognito.
        
        Returns:
            Dictionary of JWKS keys
        """
        try:
            response = requests.get(self.jwks_url, timeout=10)
            response.raise_for_status()
            jwks_data = response.json()
            
            # Convert JWKS to a more usable format
            keys = {}
            for key in jwks_data.get('keys', []):
                key_id = key.get('kid')
                if key_id:
                    keys[key_id] = key
            
            logger.info(f"Loaded {len(keys)} JWKS keys from Cognito")
            return keys
            
        except requests.RequestException as e:
            logger.error(f"Failed to load JWKS keys: {e}")
            raise ConfigurationError(f"Failed to load JWKS keys from Cognito: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing JWKS keys: {e}")
            raise ConfigurationError(f"Error processing JWKS keys: {str(e)}")
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token and extract user information.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Dictionary with user information and token claims
            
        Raises:
            AuthenticationError: If token validation fails
            CognitoError: If Cognito-specific errors occur
        """
        try:
            # Check cache first
            if self.enable_cache and token in self.token_cache:
                cached_data = self.token_cache[token]
                if datetime.now(timezone.utc).timestamp() < cached_data['expires_at']:
                    return cached_data['user_info']
                else:
                    # Remove expired token from cache
                    del self.token_cache[token]
            
            # Decode token header to get key ID
            header = jwt.get_unverified_header(token)
            key_id = header.get('kid')
            
            if not key_id:
                raise AuthenticationError("Token missing key ID")
            
            # Get the appropriate key
            if key_id not in self.jwks_keys:
                raise AuthenticationError(f"Unknown key ID: {key_id}")
            
            jwk = self.jwks_keys[key_id]
            
            # Convert JWK to PEM format for PyJWT
            public_key = self._jwk_to_pem(jwk)
            
            # Decode and validate token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                audience=self.client_id,
                issuer=f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
            )
            
            # Extract user information
            user_info = self._extract_user_info(payload)
            
            # Cache the result
            if self.enable_cache:
                self.token_cache[token] = {
                    'user_info': user_info,
                    'expires_at': payload.get('exp', 0)
                }
            
            return user_info
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise AuthenticationError(f"Token validation failed: {str(e)}")
    
    def _jwk_to_pem(self, jwk: Dict[str, Any]) -> str:
        """
        Convert JWK to PEM format for PyJWT.
        
        Args:
            jwk: JSON Web Key
            
        Returns:
            PEM-formatted public key
        """
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            import base64
            
            # Extract RSA components
            n = base64.urlsafe_b64decode(jwk['n'] + '==')
            e = base64.urlsafe_b64decode(jwk['e'] + '==')
            
            # Convert to integers
            n_int = int.from_bytes(n, 'big')
            e_int = int.from_bytes(e, 'big')
            
            # Create RSA public key
            public_key = rsa.RSAPublicNumbers(e_int, n_int).public_key()
            
            # Serialize to PEM
            pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return pem.decode('utf-8')
            
        except ImportError:
            # Fallback to simple validation if cryptography is not available
            logger.warning("cryptography library not available, using basic token validation")
            return ""
        except Exception as e:
            logger.error(f"Error converting JWK to PEM: {e}")
            raise CognitoError(f"Error processing JWK: {str(e)}")
    
    def _extract_user_info(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract user information from JWT payload.
        
        Args:
            payload: JWT payload
            
        Returns:
            Dictionary with user information
        """
        user_info = {
            'user_id': payload.get('sub'),
            'username': payload.get('cognito:username'),
            'email': payload.get('email'),
            'email_verified': payload.get('email_verified', False),
            'phone_number': payload.get('phone_number'),
            'phone_number_verified': payload.get('phone_number_verified', False),
            'groups': payload.get('cognito:groups', []),
            'custom_attributes': {},
            'token_use': payload.get('token_use'),
            'issued_at': payload.get('iat'),
            'expires_at': payload.get('exp'),
            'client_id': payload.get('aud'),
            'issuer': payload.get('iss')
        }
        
        # Extract custom attributes
        for key, value in payload.items():
            if key.startswith('custom:'):
                user_info['custom_attributes'][key[7:]] = value
        
        return user_info
    
    def get_user_from_token(self, token: str) -> Dict[str, Any]:
        """
        Get user information from token (convenience method).
        
        Args:
            token: JWT token
            
        Returns:
            User information dictionary
        """
        return self.validate_token(token)
    
    def is_user_in_group(self, token: str, group_name: str) -> bool:
        """
        Check if user belongs to a specific group.
        
        Args:
            token: JWT token
            group_name: Group name to check
            
        Returns:
            True if user is in group, False otherwise
        """
        try:
            user_info = self.validate_token(token)
            return group_name in user_info.get('groups', [])
        except Exception:
            return False
    
    def has_custom_attribute(self, token: str, attribute_name: str, expected_value: Optional[str] = None) -> bool:
        """
        Check if user has a custom attribute with optional value validation.
        
        Args:
            token: JWT token
            attribute_name: Custom attribute name
            expected_value: Optional expected value
            
        Returns:
            True if attribute exists and matches expected value
        """
        try:
            user_info = self.validate_token(token)
            custom_attrs = user_info.get('custom_attributes', {})
            
            if attribute_name not in custom_attrs:
                return False
            
            if expected_value is not None:
                return custom_attrs[attribute_name] == expected_value
            
            return True
        except Exception:
            return False
    
    def clear_cache(self) -> None:
        """Clear the token validation cache."""
        self.token_cache.clear()
        logger.info("Token validation cache cleared")


# Global Cognito auth instance
_cognito_auth: Optional[CognitoAuth] = None


def get_cognito_auth() -> CognitoAuth:
    """
    Get or create the global Cognito auth instance.
    
    Returns:
        CognitoAuth instance
    """
    global _cognito_auth
    
    if _cognito_auth is None:
        _cognito_auth = CognitoAuth()
    
    return _cognito_auth


# FastAPI dependency for authentication
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    FastAPI dependency to get current authenticated user.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        User information dictionary
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        cognito_auth = get_cognito_auth()
        user_info = cognito_auth.validate_token(credentials.credentials)
        return user_info
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user_optional(
    request: Request
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency to get current user (optional).
    Returns None if no authentication is provided.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User information dictionary or None
    """
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        cognito_auth = get_cognito_auth()
        return cognito_auth.validate_token(token)
    except Exception:
        return None


def require_group(group_name: str):
    """
    Decorator to require user to be in a specific group.
    
    Args:
        group_name: Required group name
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user from kwargs or request
            user = kwargs.get('current_user')
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if group_name not in user.get('groups', []):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required group: {group_name}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_custom_attribute(attribute_name: str, expected_value: Optional[str] = None):
    """
    Decorator to require user to have a specific custom attribute.
    
    Args:
        attribute_name: Required custom attribute name
        expected_value: Optional expected value
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user from kwargs or request
            user = kwargs.get('current_user')
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            custom_attrs = user.get('custom_attributes', {})
            if attribute_name not in custom_attrs:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required attribute: {attribute_name}"
                )
            
            if expected_value is not None and custom_attrs[attribute_name] != expected_value:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Invalid attribute value for: {attribute_name}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Export main components
__all__ = [
    'CognitoAuth',
    'get_cognito_auth',
    'get_current_user',
    'get_current_user_optional',
    'require_group',
    'require_custom_attribute',
    'security'
]
