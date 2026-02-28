#!/usr/bin/env python3
"""
Dashboard Upload Session API Endpoints
FastAPI endpoints for upload session management
"""

import logging
from typing import Dict, Any, List
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from src.api.v1.dashboard.schemas import (
    UploadSessionInitiateRequest,
    UploadSessionResponse,
    UploadSessionValidationRequest,
    UploadSessionValidationResponse,
    UploadSessionStatus,
    UploadSessionError,
    UploadSessionErrorCodes
)
from src.services.upload_session_service import upload_session_service
from src.services.quota_management import QuotaExceededError

logger = logging.getLogger(__name__)

# Create router for dashboard upload endpoints
router = APIRouter(
    prefix="/v1/dashboard/upload",
    tags=["dashboard-upload"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)


# Authentication dependency (placeholder - would integrate with actual auth)
async def get_current_user() -> UUID:
    """
    Get current authenticated user.
    This is a placeholder implementation - would integrate with actual authentication.
    """
    # In a real implementation, this would extract user from JWT token or session
    # For now, return a test user ID
    return UUID("12345678-1234-5678-9012-123456789012")


# Dependency to ensure upload session service is initialized
async def get_upload_service():
    """Get initialized upload session service"""
    if not upload_session_service.redis:
        initialized = await upload_session_service.initialize()
        if not initialized:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Upload session service unavailable"
            )
    return upload_session_service


@router.post(
    "/initiate",
    response_model=UploadSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate Upload Session",
    description="Create a new upload session with quota validation and Redis storage"
)
async def initiate_upload_session(
    request: UploadSessionInitiateRequest,
    current_user: UUID = Depends(get_current_user),
    service = Depends(get_upload_service)
) -> UploadSessionResponse:
    """
    Initiate a new upload session for dashboard file uploads.
    
    This endpoint:
    - Validates user upload quotas
    - Returns 429 status with descriptive error when quota is exceeded
    - Generates unique session IDs and stores session data in Redis with 1-hour expiry
    - Includes upload URL, max file size (500MB), allowed formats, and remaining quota count
    - Stores dashboard context with source section, workflow type, and user preferences
    - Integrates with existing Web Dashboard Interface authentication patterns
    
    Args:
        request: Upload session initiation request
        current_user: Current authenticated user
        service: Upload session service
        
    Returns:
        UploadSessionResponse: Session details and upload information
        
    Raises:
        HTTPException: 429 if quota exceeded, 400 for validation errors, 500 for server errors
    """
    try:
        logger.info(f"User {current_user} requesting upload session for {request.dashboard_context.source_section}")
        
        # Create upload session
        response = await service.create_upload_session(current_user, request)
        
        logger.info(f"Created upload session {response.session_id} for user {current_user}")
        return response
        
    except QuotaExceededError as e:
        logger.warning(f"Quota exceeded for user {current_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error_code": UploadSessionErrorCodes.QUOTA_EXCEEDED,
                "error_message": str(e),
                "quota_info": {
                    "max_file_size_mb": service.config.upload_session.max_file_size_mb,
                    "quota_reset_days": service.config.upload_session.quota_reset_period_days
                }
            }
        )
        
    except ValueError as e:
        logger.warning(f"Validation error for user {current_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": UploadSessionErrorCodes.INVALID_REQUEST,
                "error_message": str(e)
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to create upload session for user {current_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": UploadSessionErrorCodes.SESSION_CREATION_FAILED,
                "error_message": "Failed to create upload session"
            }
        )


@router.post(
    "/validate",
    response_model=UploadSessionValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate Upload Session",
    description="Validate an upload session and check user ownership"
)
async def validate_upload_session(
    request: UploadSessionValidationRequest,
    current_user: UUID = Depends(get_current_user),
    service = Depends(get_upload_service)
) -> UploadSessionValidationResponse:
    """
    Validate an upload session and verify user ownership.
    
    This endpoint:
    - Verifies session exists and is not expired
    - Checks user ownership and returns 403 for unauthorized access attempts
    - Returns session status and validity information
    - Integrates with existing authentication patterns
    
    Args:
        request: Session validation request
        current_user: Current authenticated user
        service: Upload session service
        
    Returns:
        UploadSessionValidationResponse: Validation results
        
    Raises:
        HTTPException: 403 for unauthorized access, 500 for server errors
    """
    try:
        logger.info(f"User {current_user} validating session {request.session_id}")
        
        # Validate session
        response = await service.validate_upload_session(request)
        
        if not response.is_owner:
            logger.warning(f"Unauthorized access attempt to session {request.session_id} by user {current_user}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": UploadSessionErrorCodes.UNAUTHORIZED_ACCESS,
                    "error_message": "Unauthorized access to session"
                }
            )
        
        logger.info(f"Session {request.session_id} validated for user {current_user}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate session {request.session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": UploadSessionErrorCodes.SESSION_NOT_FOUND,
                "error_message": "Failed to validate session"
            }
        )


@router.get(
    "/sessions",
    response_model=List[UploadSessionStatus],
    status_code=status.HTTP_200_OK,
    summary="Get User Active Sessions",
    description="Get all active upload sessions for the current user"
)
async def get_user_active_sessions(
    current_user: UUID = Depends(get_current_user),
    service = Depends(get_upload_service)
) -> List[UploadSessionStatus]:
    """
    Get all active upload sessions for the current user.
    
    This endpoint:
    - Returns list of active sessions for the authenticated user
    - Includes session status, expiry, and dashboard context
    - Automatically cleans up expired sessions
    
    Args:
        current_user: Current authenticated user
        service: Upload session service
        
    Returns:
        List[UploadSessionStatus]: List of active sessions
        
    Raises:
        HTTPException: 500 for server errors
    """
    try:
        logger.info(f"Getting active sessions for user {current_user}")
        
        # Get active sessions
        sessions = await service.get_user_active_sessions(current_user)
        
        logger.info(f"Found {len(sessions)} active sessions for user {current_user}")
        return sessions
        
    except Exception as e:
        logger.error(f"Failed to get active sessions for user {current_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": UploadSessionErrorCodes.SESSION_NOT_FOUND,
                "error_message": "Failed to retrieve active sessions"
            }
        )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Upload Session",
    description="Delete a specific upload session"
)
async def delete_upload_session(
    session_id: UUID,
    current_user: UUID = Depends(get_current_user),
    service = Depends(get_upload_service)
):
    """
    Delete a specific upload session.
    
    This endpoint:
    - Validates user ownership of the session
    - Removes session from Redis storage
    - Returns 403 for unauthorized access attempts
    
    Args:
        session_id: Session ID to delete
        current_user: Current authenticated user
        service: Upload session service
        
    Raises:
        HTTPException: 403 for unauthorized access, 404 if not found, 500 for server errors
    """
    try:
        logger.info(f"User {current_user} deleting session {session_id}")
        
        # Validate session ownership
        validation_request = UploadSessionValidationRequest(
            session_id=session_id,
            user_id=current_user
        )
        
        validation_response = await service.validate_upload_session(validation_request)
        
        if not validation_response.is_owner:
            logger.warning(f"Unauthorized delete attempt for session {session_id} by user {current_user}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": UploadSessionErrorCodes.UNAUTHORIZED_ACCESS,
                    "error_message": "Unauthorized access to session"
                }
            )
        
        if not validation_response.is_valid:
            logger.warning(f"Attempting to delete invalid session {session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": UploadSessionErrorCodes.SESSION_NOT_FOUND,
                    "error_message": "Session not found or expired"
                }
            )
        
        # Delete session
        await service._cleanup_session(session_id, current_user)
        
        logger.info(f"Session {session_id} deleted by user {current_user}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": UploadSessionErrorCodes.SESSION_NOT_FOUND,
                "error_message": "Failed to delete session"
            }
        )


@router.get(
    "/quota",
    status_code=status.HTTP_200_OK,
    summary="Get User Quota Information",
    description="Get current user's upload quota information"
)
async def get_user_quota_info(
    current_user: UUID = Depends(get_current_user),
    service = Depends(get_upload_service)
) -> Dict[str, Any]:
    """
    Get current user's upload quota information.
    
    This endpoint:
    - Returns quota limit, used, and remaining amounts
    - Includes quota in both bytes and GB
    - Shows usage percentage and reset date
    
    Args:
        current_user: Current authenticated user
        service: Upload session service
        
    Returns:
        Dict[str, Any]: Quota information
        
    Raises:
        HTTPException: 500 for server errors
    """
    try:
        logger.info(f"Getting quota info for user {current_user}")
        
        # Get quota information
        quota_info = await service._get_user_quota_info(current_user)
        
        logger.info(f"Retrieved quota info for user {current_user}")
        return quota_info.dict()
        
    except Exception as e:
        logger.error(f"Failed to get quota info for user {current_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": UploadSessionErrorCodes.QUOTA_VALIDATION_FAILED,
                "error_message": "Failed to retrieve quota information"
            }
        )


@router.post(
    "/cleanup",
    status_code=status.HTTP_200_OK,
    summary="Cleanup Expired Sessions",
    description="Clean up expired upload sessions (admin endpoint)"
)
async def cleanup_expired_sessions(
    current_user: UUID = Depends(get_current_user),
    service = Depends(get_upload_service)
) -> Dict[str, Any]:
    """
    Clean up expired upload sessions.
    
    This is an admin endpoint that:
    - Removes all expired sessions from Redis
    - Returns count of cleaned up sessions
    - Should be called periodically or on-demand
    
    Args:
        current_user: Current authenticated user
        service: Upload session service
        
    Returns:
        Dict[str, Any]: Cleanup results
        
    Raises:
        HTTPException: 500 for server errors
    """
    try:
        logger.info(f"User {current_user} requesting session cleanup")
        
        # Clean up expired sessions
        cleaned_count = await service.cleanup_expired_sessions()
        
        logger.info(f"Cleaned up {cleaned_count} expired sessions")
        return {
            "cleaned_sessions": cleaned_count,
            "timestamp": service.config.upload_session.session_ttl_seconds,
            "message": f"Successfully cleaned up {cleaned_count} expired sessions"
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": UploadSessionErrorCodes.SESSION_CREATION_FAILED,
                "error_message": "Failed to cleanup expired sessions"
            }
        )


# Health check endpoint
@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Upload Service Health Check",
    description="Check upload session service health"
)
async def health_check(
    service = Depends(get_upload_service)
) -> Dict[str, Any]:
    """
    Check upload session service health.
    
    Returns:
        Dict[str, Any]: Health status information
    """
    try:
        # Test Redis connection
        await service.redis.ping()
        
        return {
            "status": "healthy",
            "redis_connected": True,
            "service_initialized": service.redis is not None,
            "configuration_valid": service.config.validate_configuration()['overall_valid']
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "redis_connected": False,
            "service_initialized": False,
            "error": str(e)
        }
