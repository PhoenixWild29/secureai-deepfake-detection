#!/usr/bin/env python3
"""
Global Error Handling Middleware
Centralized error handling for API endpoints with structured error responses
"""

import logging
import traceback
from datetime import datetime, timezone
from typing import Union, Dict, Any, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..errors.api_errors import APIError, InternalServerError


# Configure logging
logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Global error handler for API endpoints.
    Provides structured error responses and logging.
    """
    
    @staticmethod
    def create_error_response(
        error: Exception,
        request: Request,
        include_traceback: bool = False
    ) -> JSONResponse:
        """
        Create a structured error response.
        
        Args:
            error: The exception that occurred
            request: FastAPI request object
            include_traceback: Whether to include traceback in response
            
        Returns:
            JSONResponse with error details
        """
        # Generate error ID for tracking
        error_id = f"err_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{id(error)}"
        
        # Log the error
        ErrorHandler._log_error(error, request, error_id)
        
        # Create error response
        if isinstance(error, APIError):
            return ErrorHandler._create_api_error_response(error, error_id, include_traceback)
        elif isinstance(error, HTTPException):
            return ErrorHandler._create_http_error_response(error, error_id, include_traceback)
        elif isinstance(error, RequestValidationError):
            return ErrorHandler._create_validation_error_response(error, error_id, include_traceback)
        else:
            return ErrorHandler._create_generic_error_response(error, error_id, include_traceback)
    
    @staticmethod
    def _log_error(error: Exception, request: Request, error_id: str) -> None:
        """
        Log error details for debugging and monitoring.
        
        Args:
            error: The exception that occurred
            request: FastAPI request object
            error_id: Unique error identifier
        """
        # Prepare log data
        log_data = {
            'error_id': error_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'request_method': request.method,
            'request_url': str(request.url),
            'request_headers': dict(request.headers),
            'client_ip': request.client.host if request.client else None,
            'user_agent': request.headers.get('user-agent'),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Add additional context for API errors
        if isinstance(error, APIError):
            log_data.update({
                'error_code': error.error_code,
                'status_code': error.status_code,
                'error_details': error.details
            })
        
        # Log based on error severity
        if isinstance(error, APIError) and error.status_code >= 500:
            logger.error(f"Server error {error_id}: {error.message}", extra=log_data)
            logger.error(f"Traceback for {error_id}:\n{traceback.format_exc()}")
        elif isinstance(error, APIError) and error.status_code >= 400:
            logger.warning(f"Client error {error_id}: {str(error)}", extra=log_data)
        else:
            logger.error(f"Unexpected error {error_id}: {str(error)}", extra=log_data)
            logger.error(f"Traceback for {error_id}:\n{traceback.format_exc()}")
    
    @staticmethod
    def _create_api_error_response(
        error: APIError,
        error_id: str,
        include_traceback: bool
    ) -> JSONResponse:
        """
        Create response for APIError instances.
        
        Args:
            error: APIError instance
            error_id: Unique error identifier
            include_traceback: Whether to include traceback
            
        Returns:
            JSONResponse with error details
        """
        response_data = {
            'success': False,
            'error': {
                'code': error.error_code,
                'message': error.message,
                'error_id': error_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'details': error.details
            }
        }
        
        if include_traceback:
            response_data['error']['traceback'] = traceback.format_exc()
        
        return JSONResponse(
            status_code=error.status_code,
            content=response_data,
            headers={
                'X-Error-ID': error_id,
                'X-Error-Code': error.error_code
            }
        )
    
    @staticmethod
    def _create_http_error_response(
        error: HTTPException,
        error_id: str,
        include_traceback: bool
    ) -> JSONResponse:
        """
        Create response for HTTPException instances.
        
        Args:
            error: HTTPException instance
            error_id: Unique error identifier
            include_traceback: Whether to include traceback
            
        Returns:
            JSONResponse with error details
        """
        response_data = {
            'success': False,
            'error': {
                'code': 'HTTP_ERROR',
                'message': error.detail,
                'error_id': error_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status_code': error.status_code
            }
        }
        
        if include_traceback:
            response_data['error']['traceback'] = traceback.format_exc()
        
        return JSONResponse(
            status_code=error.status_code,
            content=response_data,
            headers={
                'X-Error-ID': error_id,
                'X-Error-Code': 'HTTP_ERROR'
            }
        )
    
    @staticmethod
    def _create_validation_error_response(
        error: RequestValidationError,
        error_id: str,
        include_traceback: bool
    ) -> JSONResponse:
        """
        Create response for RequestValidationError instances.
        
        Args:
            error: RequestValidationError instance
            error_id: Unique error identifier
            include_traceback: Whether to include traceback
            
        Returns:
            JSONResponse with error details
        """
        # Format validation errors
        formatted_errors = []
        for validation_error in error.errors():
            formatted_errors.append({
                'field': '.'.join(str(loc) for loc in validation_error['loc']),
                'message': validation_error['msg'],
                'type': validation_error['type'],
                'input': validation_error.get('input')
            })
        
        response_data = {
            'success': False,
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': 'Request validation failed',
                'error_id': error_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'validation_errors': formatted_errors
            }
        }
        
        if include_traceback:
            response_data['error']['traceback'] = traceback.format_exc()
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=response_data,
            headers={
                'X-Error-ID': error_id,
                'X-Error-Code': 'VALIDATION_ERROR'
            }
        )
    
    @staticmethod
    def _create_generic_error_response(
        error: Exception,
        error_id: str,
        include_traceback: bool
    ) -> JSONResponse:
        """
        Create response for generic exception instances.
        
        Args:
            error: Generic Exception instance
            error_id: Unique error identifier
            include_traceback: Whether to include traceback
            
        Returns:
            JSONResponse with error details
        """
        response_data = {
            'success': False,
            'error': {
                'code': 'INTERNAL_SERVER_ERROR',
                'message': 'An unexpected error occurred',
                'error_id': error_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        }
        
        if include_traceback:
            response_data['error']['traceback'] = traceback.format_exc()
            response_data['error']['original_message'] = str(error)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response_data,
            headers={
                'X-Error-ID': error_id,
                'X-Error-Code': 'INTERNAL_SERVER_ERROR'
            }
        )


# FastAPI exception handlers
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """
    Handle APIError exceptions.
    
    Args:
        request: FastAPI request object
        exc: APIError instance
        
    Returns:
        JSONResponse with error details
    """
    return ErrorHandler.create_error_response(exc, request)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle HTTPException instances.
    
    Args:
        request: FastAPI request object
        exc: HTTPException instance
        
    Returns:
        JSONResponse with error details
    """
    return ErrorHandler.create_error_response(exc, request)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle RequestValidationError instances.
    
    Args:
        request: FastAPI request object
        exc: RequestValidationError instance
        
    Returns:
        JSONResponse with error details
    """
    return ErrorHandler.create_error_response(exc, request)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle generic Exception instances.
    
    Args:
        request: FastAPI request object
        exc: Generic Exception instance
        
    Returns:
        JSONResponse with error details
    """
    return ErrorHandler.create_error_response(exc, request)


# Utility functions for creating structured errors
def create_error_response(
    error_code: str,
    message: str,
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None,
    error_id: Optional[str] = None
) -> JSONResponse:
    """
    Create a structured error response.
    
    Args:
        error_code: Error code
        message: Error message
        status_code: HTTP status code
        details: Additional error details
        error_id: Optional error ID
        
    Returns:
        JSONResponse with error details
    """
    if error_id is None:
        error_id = f"err_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{id(message)}"
    
    response_data = {
        'success': False,
        'error': {
            'code': error_code,
            'message': message,
            'error_id': error_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'details': details or {}
        }
    }
    
    return JSONResponse(
        status_code=status_code,
        content=response_data,
        headers={
            'X-Error-ID': error_id,
            'X-Error-Code': error_code
        }
    )


def create_validation_error_response(
    message: str,
    validation_errors: list,
    error_id: Optional[str] = None
) -> JSONResponse:
    """
    Create a validation error response.
    
    Args:
        message: Error message
        validation_errors: List of validation errors
        error_id: Optional error ID
        
    Returns:
        JSONResponse with validation error details
    """
    if error_id is None:
        error_id = f"err_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{id(message)}"
    
    response_data = {
        'success': False,
        'error': {
            'code': 'VALIDATION_ERROR',
            'message': message,
            'error_id': error_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'validation_errors': validation_errors
        }
    }
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response_data,
        headers={
            'X-Error-ID': error_id,
            'X-Error-Code': 'VALIDATION_ERROR'
        }
    )


# Export main components
__all__ = [
    'ErrorHandler',
    'api_error_handler',
    'http_exception_handler',
    'validation_exception_handler',
    'generic_exception_handler',
    'create_error_response',
    'create_validation_error_response'
]
