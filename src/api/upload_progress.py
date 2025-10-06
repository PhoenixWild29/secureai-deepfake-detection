#!/usr/bin/env python3
"""
Upload Progress API Endpoint
REST API endpoint for retrieving upload progress data with user access validation
"""

import logging
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from src.models.upload_progress import ProgressResponse, ProgressStatus
from src.services.redis_progress_service import get_redis_progress_service
from src.utils.error_handlers import validate_upload_session_redis
from src.auth.upload_auth import get_current_user_jwt

logger = logging.getLogger(__name__)

# Create router for upload progress endpoints
router = APIRouter(
    prefix="/v1/dashboard/upload",
    tags=["dashboard-upload-progress"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)


@router.get(
    "/progress/{session_id}",
    response_model=ProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Upload Progress",
    description="Retrieve current upload progress with percentage, bytes uploaded, total bytes, and upload speed"
)
async def get_upload_progress(
    session_id: UUID,
    current_user: UUID = Depends(get_current_user_jwt)
) -> ProgressResponse:
    """
    Get current upload progress for a session.
    
    This endpoint:
    - Validates user access to session data and returns 403 for unauthorized requests
    - Returns current upload progress with percentage, bytes uploaded, total bytes, and upload speed
    - Includes estimated completion times and upload status
    - Provides video ID, analysis ID, and redirect URL when upload is completed
    - Returns error information when upload has failed
    
    Args:
        session_id: Upload session ID
        current_user: Current authenticated user
        
    Returns:
        ProgressResponse: Current upload progress data
        
    Raises:
        HTTPException: 403 for unauthorized access, 404 for session not found, 500 for server errors
    """
    try:
        logger.info(f"User {current_user} requesting progress for session {session_id}")
        
        # Validate user access to session
        session_validation = await validate_upload_session_redis(session_id, current_user)
        if not session_validation['is_valid']:
            logger.warning(f"Unauthorized access attempt for session {session_id} by user {current_user}: {session_validation.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "UNAUTHORIZED_ACCESS",
                    "error_message": session_validation.get('error', 'Unauthorized access to session data')
                }
            )
        
        # Get Redis progress service
        redis_service = get_redis_progress_service()
        if not redis_service.redis_client:
            await redis_service.initialize()
        
        # Retrieve progress data from Redis
        progress = await redis_service.get_progress(session_id)
        if not progress:
            logger.warning(f"Progress data not found for session {session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "PROGRESS_NOT_FOUND",
                    "error_message": "Upload progress data not found or session has expired"
                }
            )
        
        # Convert to response format
        response = ProgressResponse(
            session_id=progress.session_id,
            percentage=progress.percentage,
            bytes_uploaded=progress.bytes_uploaded,
            total_bytes=progress.total_bytes,
            upload_speed=progress.upload_speed,
            estimated_completion=progress.estimated_completion,
            status=progress.status,
            filename=progress.filename,
            video_id=progress.video_id,
            analysis_id=progress.analysis_id,
            redirect_url=progress.redirect_url,
            error_message=progress.error_message,
            error_code=progress.error_code,
            started_at=progress.started_at,
            last_updated=progress.last_updated,
            completed_at=progress.completed_at
        )
        
        logger.debug(f"Retrieved progress for session {session_id}: {progress.percentage:.1f}%")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to get upload progress for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "error_message": "Failed to retrieve upload progress data"
            }
        )


@router.get(
    "/progress/{session_id}/status",
    status_code=status.HTTP_200_OK,
    summary="Get Upload Status",
    description="Get simplified upload status for a session"
)
async def get_upload_status(
    session_id: UUID,
    current_user: UUID = Depends(get_current_user_jwt)
) -> Dict[str, Any]:
    """
    Get simplified upload status for a session.
    
    Args:
        session_id: Upload session ID
        current_user: Current authenticated user
        
    Returns:
        Dict[str, Any]: Simplified status information
    """
    try:
        # Validate user access to session
        session_validation = await validate_upload_session_redis(session_id, current_user)
        if not session_validation['is_valid']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "UNAUTHORIZED_ACCESS",
                    "error_message": "Unauthorized access to session data"
                }
            )
        
        # Get Redis progress service
        redis_service = get_redis_progress_service()
        if not redis_service.redis_client:
            await redis_service.initialize()
        
        # Retrieve progress data
        progress = await redis_service.get_progress(session_id)
        if not progress:
            return {
                "session_id": str(session_id),
                "status": "not_found",
                "message": "Progress data not found"
            }
        
        return {
            "session_id": str(session_id),
            "status": progress.status.value,
            "percentage": progress.percentage,
            "filename": progress.filename,
            "last_updated": progress.last_updated.isoformat(),
            "is_completed": progress.status == ProgressStatus.COMPLETED,
            "has_error": progress.status == ProgressStatus.ERROR,
            "video_id": str(progress.video_id) if progress.video_id else None,
            "redirect_url": progress.redirect_url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get upload status for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "error_message": "Failed to retrieve upload status"
            }
        )


@router.get(
    "/progress/user/{user_id}/sessions",
    status_code=status.HTTP_200_OK,
    summary="Get User Progress Sessions",
    description="Get all active progress sessions for a user"
)
async def get_user_progress_sessions(
    user_id: UUID,
    current_user: UUID = Depends(get_current_user_jwt)
) -> Dict[str, Any]:
    """
    Get all active progress sessions for a user.
    
    Args:
        user_id: User ID to get sessions for
        current_user: Current authenticated user
        
    Returns:
        Dict[str, Any]: List of active progress sessions
    """
    try:
        # Validate user access (users can only access their own sessions)
        if current_user != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "UNAUTHORIZED_ACCESS",
                    "error_message": "Users can only access their own progress sessions"
                }
            )
        
        # Get Redis progress service
        redis_service = get_redis_progress_service()
        if not redis_service.redis_client:
            await redis_service.initialize()
        
        # Get user's progress sessions
        session_ids = await redis_service.get_user_progress_sessions(user_id)
        
        # Get progress data for each session
        sessions = []
        for session_id in session_ids:
            progress = await redis_service.get_progress(session_id)
            if progress:
                sessions.append({
                    "session_id": str(session_id),
                    "status": progress.status.value,
                    "percentage": progress.percentage,
                    "filename": progress.filename,
                    "started_at": progress.started_at.isoformat(),
                    "last_updated": progress.last_updated.isoformat(),
                    "is_completed": progress.status == ProgressStatus.COMPLETED,
                    "has_error": progress.status == ProgressStatus.ERROR
                })
        
        return {
            "user_id": str(user_id),
            "total_sessions": len(sessions),
            "active_sessions": len([s for s in sessions if s["status"] == "uploading"]),
            "completed_sessions": len([s for s in sessions if s["is_completed"]]),
            "error_sessions": len([s for s in sessions if s["has_error"]]),
            "sessions": sessions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get progress sessions for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "error_message": "Failed to retrieve user progress sessions"
            }
        )


@router.delete(
    "/progress/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Upload Progress",
    description="Delete progress data for a completed or failed upload"
)
async def delete_upload_progress(
    session_id: UUID,
    current_user: UUID = Depends(get_current_user_jwt)
):
    """
    Delete progress data for a session.
    
    Args:
        session_id: Upload session ID
        current_user: Current authenticated user
    """
    try:
        # Validate user access to session
        session_validation = await validate_upload_session_redis(session_id, current_user)
        if not session_validation['is_valid']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "UNAUTHORIZED_ACCESS",
                    "error_message": "Unauthorized access to session data"
                }
            )
        
        # Get Redis progress service
        redis_service = get_redis_progress_service()
        if not redis_service.redis_client:
            await redis_service.initialize()
        
        # Check if progress exists
        progress = await redis_service.get_progress(session_id)
        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "PROGRESS_NOT_FOUND",
                    "error_message": "Progress data not found"
                }
            )
        
        # Only allow deletion of completed or failed uploads
        if progress.status not in [ProgressStatus.COMPLETED, ProgressStatus.ERROR, ProgressStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_STATUS",
                    "error_message": "Can only delete progress for completed, failed, or cancelled uploads"
                }
            )
        
        # Delete progress data
        success = await redis_service.delete_progress(session_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "DELETE_FAILED",
                    "error_message": "Failed to delete progress data"
                }
            )
        
        logger.info(f"Deleted progress data for session {session_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete progress for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "error_message": "Failed to delete progress data"
            }
        )


@router.get(
    "/progress/stats",
    status_code=status.HTTP_200_OK,
    summary="Get Progress Statistics",
    description="Get upload progress tracking statistics"
)
async def get_progress_stats(
    current_user: UUID = Depends(get_current_user_jwt)
) -> Dict[str, Any]:
    """
    Get upload progress tracking statistics.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Dict[str, Any]: Progress tracking statistics
    """
    try:
        # Get Redis progress service
        redis_service = get_redis_progress_service()
        if not redis_service.redis_client:
            await redis_service.initialize()
        
        # Get progress statistics
        stats = await redis_service.get_progress_stats()
        
        # Get user's specific stats
        user_sessions = await redis_service.get_user_progress_sessions(current_user)
        user_stats = {
            "user_id": str(current_user),
            "total_sessions": len(user_sessions),
            "active_sessions": 0,
            "completed_sessions": 0,
            "error_sessions": 0
        }
        
        for session_id in user_sessions:
            progress = await redis_service.get_progress(session_id)
            if progress:
                if progress.status == ProgressStatus.UPLOADING:
                    user_stats["active_sessions"] += 1
                elif progress.status == ProgressStatus.COMPLETED:
                    user_stats["completed_sessions"] += 1
                elif progress.status == ProgressStatus.ERROR:
                    user_stats["error_sessions"] += 1
        
        return {
            "global_stats": stats,
            "user_stats": user_stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get progress stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "error_message": "Failed to retrieve progress statistics"
            }
        )
