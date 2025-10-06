#!/usr/bin/env python3
"""
API Error Classes
Custom error classes for API error handling
"""

from typing import Optional


class APIError(Exception):
    """Base API error class"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "api_error",
        status_code: int = 500,
        details: Optional[dict] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(APIError):
    """Validation error"""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="validation_error",
            status_code=400,
            details=details
        )


class AuthenticationError(APIError):
    """Authentication error"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="authentication_error",
            status_code=401
        )


class AuthorizationError(APIError):
    """Authorization error"""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code="authorization_error",
            status_code=403
        )


class NotFoundError(APIError):
    """Not found error"""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message=message,
            error_code="not_found",
            status_code=404
        )


class DatabaseError(APIError):
    """Database error"""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="database_error",
            status_code=500,
            details=details
        )


class ExternalServiceError(APIError):
    """External service error"""
    
    def __init__(self, message: str, service_name: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="external_service_error",
            status_code=502,
            details={**details, "service": service_name} if details else {"service": service_name}
        )