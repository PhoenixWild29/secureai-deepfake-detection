#!/usr/bin/env python3
"""
Authentication Middleware
Simplified authentication for dashboard API endpoints
"""

import logging
from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Get current user from authentication credentials
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User information dictionary
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # In a real implementation, this would validate the JWT token
        # and extract user information from it
        token = credentials.credentials
        
        # Simplified user extraction (in production, validate JWT)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials required"
            )
        
        # Mock user data (replace with actual JWT validation)
        user_data = {
            "user_id": "user_123",
            "email": "user@example.com",
            "role": "user",
            "timezone": "UTC",
            "permissions": ["dashboard:read", "dashboard:write"]
        }
        
        logger.debug(f"Authenticated user: {user_data['user_id']}")
        return user_data
        
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


async def get_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current admin user
    
    Args:
        current_user: Current user from authentication
        
    Returns:
        Admin user information
        
    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user
