#!/usr/bin/env python3
"""
Video Upload API Endpoint
Main API endpoint for video file uploads with complete workflow integration
"""

import logging
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from src.api.v1.dashboard.schemas import UploadSessionValidationRequest
from src.schemas.video_upload_schema import (
    VideoUploadRequest,
    VideoUploadResponse,
    VideoUploadError,
    VideoUploadErrorCodes,
    VideoUploadConfig,
    VideoFormat
)
from src.models.video import Video, VideoStatusEnum, VideoFormatEnum, create_video_record
from src.services.s3_service import get_dashboard_s3_service
from src.services.video_processing_service import get_video_processing_service
from src.services.detection_engine_service import get_detection_engine_service
from src.services.quota_management import QuotaService, QuotaExceededError
from src.utils.error_handlers import handle_video_upload_error, validate_upload_session_redis
from src.auth.upload_auth import get_current_user_jwt

logger = logging.getLogger(__name__)

# Create router for video upload endpoints
router = APIRouter(
    prefix="/v1/dashboard/upload",
    tags=["dashboard-video-upload"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)


# Dependency to ensure services are initialized
async def get_services():
    """Get initialized service instances"""
    services = {
        's3_service': get_dashboard_s3_service(),
        'video_service': get_video_processing_service(),
        'detection_service': get_detection_engine_service(),
        'quota_service': QuotaService()
    }
    return services


@router.post(
    "/{session_id}",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Video File",
    description="Upload video file with session validation, S3 storage, and automatic analysis initiation"
)
async def upload_video_file(
    session_id: UUID,
    file: UploadFile = File(...),
    filename: Optional[str] = Form(None),
    content_type: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    current_user: UUID = Depends(get_current_user_jwt),
    services = Depends(get_services)
) -> VideoUploadResponse:
    """
    Upload video file with complete workflow integration.
    
    This endpoint:
    - Validates upload sessions and returns 404 for expired/invalid sessions
    - Performs file validation (format, size, content validity)
    - Uploads to S3 with dashboard-uploads/{user_id} key prefix
    - Creates video database record with all required fields
    - Initiates automatic analysis using Core Detection Engine
    - Decrements user upload quota after successful upload
    - Returns comprehensive response with video ID, analysis ID, status, redirect URL
    - Handles failures with S3 and Redis cleanup
    
    Args:
        session_id: Upload session ID for validation
        file: Video file to upload
        filename: Optional filename override
        content_type: Optional content type override
        metadata: Optional metadata as JSON string
        current_user: Current authenticated user
        services: Initialized service instances
        
    Returns:
        VideoUploadResponse: Complete upload response with analysis details
        
    Raises:
        HTTPException: 404 for invalid sessions, 400 for validation errors, 500 for server errors
    """
    video_id = None
    s3_key = None
    
    try:
        logger.info(f"User {current_user} uploading video with session {session_id}")
        
        # 1. Validate upload session
        session_validation = await validate_upload_session_redis(session_id, current_user)
        if not session_validation['is_valid']:
            logger.warning(f"Invalid session {session_id} for user {current_user}: {session_validation.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": VideoUploadErrorCodes.SESSION_NOT_FOUND,
                    "error_message": session_validation.get('error', 'Session not found or expired')
                }
            )
        
        session_data = session_validation['session_data']
        
        # 2. Prepare file data
        file_content = await file.read()
        actual_filename = filename or file.filename or "unknown.mp4"
        actual_content_type = content_type or file.content_type or "video/mp4"
        
        # Parse metadata if provided
        parsed_metadata = None
        if metadata:
            try:
                import json
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                logger.warning(f"Invalid metadata JSON for session {session_id}")
        
        # 3. Validate video file
        logger.info(f"Validating video file: {actual_filename}")
        validation_result = services['video_service'].validate_video_file(
            file_content=file_content,
            filename=actual_filename,
            content_type=actual_content_type
        )
        
        if not validation_result.is_valid:
            logger.warning(f"Video validation failed for {actual_filename}: {validation_result.validation_errors}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": VideoUploadErrorCodes.VALIDATION_FAILED,
                    "error_message": "Video file validation failed",
                    "validation_errors": validation_result.validation_errors
                }
            )
        
        # 4. Calculate file hash
        file_hash = services['video_service'].calculate_file_hash(file_content)
        
        # 5. Check for duplicate files
        # This would typically query the database for existing files with the same hash
        # For now, we'll proceed with the upload
        
        # 6. Upload to S3
        logger.info(f"Uploading to S3: {actual_filename}")
        s3_upload_result = services['s3_service'].upload_video_file(
            file_content=file_content,
            filename=actual_filename,
            user_id=current_user,
            content_type=actual_content_type,
            session_id=session_id,
            metadata=parsed_metadata
        )
        
        if not s3_upload_result['success']:
            logger.error(f"S3 upload failed for {actual_filename}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": VideoUploadErrorCodes.S3_UPLOAD_FAILED,
                    "error_message": "Failed to upload file to S3"
                }
            )
        
        s3_key = s3_upload_result['s3_key']
        
        # 7. Create video database record
        logger.info(f"Creating video record for {actual_filename}")
        video_record = create_video_record(
            filename=actual_filename,
            file_hash=file_hash,
            file_size=len(file_content),
            format=VideoFormatEnum(validation_result.format.value),
            s3_key=s3_key,
            s3_bucket=services['s3_service'].bucket_name,
            user_id=current_user,
            upload_session_id=session_id,
            dashboard_context=session_data.get('dashboard_context'),
            metadata={
                **(parsed_metadata or {}),
                'validation_result': validation_result.dict(),
                's3_upload_result': s3_upload_result
            }
        )
        
        # In a real implementation, this would save to database
        video_id = video_record.id
        
        # 8. Initiate video analysis
        logger.info(f"Initiating analysis for video {video_id}")
        analysis_response = services['detection_service'].initiate_video_analysis(
            video_id=video_id,
            s3_key=s3_key,
            s3_bucket=services['s3_service'].bucket_name,
            model_type="resnet",  # Default model
            analysis_config={
                'session_id': str(session_id),
                'user_id': str(current_user),
                'dashboard_context': session_data.get('dashboard_context')
            }
        )
        
        # 9. Update video record with analysis results
        video_record.analysis_id = analysis_response.analysis_id
        video_record.status = VideoStatusEnum.ANALYZED if analysis_response.status == "completed" else VideoStatusEnum.PROCESSING
        video_record.detection_result = analysis_response.detection_result
        video_record.confidence_score = analysis_response.confidence_score
        video_record.is_fake = analysis_response.is_fake
        video_record.processing_time = analysis_response.processing_time
        video_record.analyzed_at = analysis_response.completed_at
        
        # 10. Decrement user quota
        try:
            services['quota_service'].update_user_quota(
                str(current_user),
                len(file_content)
            )
            logger.info(f"Updated quota for user {current_user}")
        except QuotaExceededError as e:
            logger.warning(f"Quota exceeded for user {current_user}: {e}")
            # Note: We don't fail the upload here since it's already completed
        
        # 11. Generate redirect URL
        redirect_url = f"/dashboard/videos/{video_id}/results"
        
        # 12. Estimate processing time
        estimated_processing_time = services['detection_service'].estimate_processing_time(
            len(file_content),
            "resnet"
        )
        
        # 13. Create response
        response = VideoUploadResponse(
            video_id=video_id,
            analysis_id=analysis_response.analysis_id,
            upload_status="analyzed" if analysis_response.status == "completed" else "processing",
            redirect_url=redirect_url,
            estimated_processing_time=estimated_processing_time,
            filename=actual_filename,
            file_size=len(file_content),
            file_hash=file_hash,
            format=VideoFormat(validation_result.format.value),
            s3_key=s3_key,
            s3_url=s3_upload_result['s3_url'],
            created_at=video_record.created_at,
            uploaded_at=datetime.now(timezone.utc),
            detection_result=analysis_response.detection_result,
            confidence_score=analysis_response.confidence_score,
            is_fake=analysis_response.is_fake,
            processing_time=analysis_response.processing_time,
            metadata={
                **(parsed_metadata or {}),
                'validation_warnings': validation_result.warnings,
                'dashboard_context': session_data.get('dashboard_context')
            }
        )
        
        logger.info(f"Successfully uploaded video {video_id} for user {current_user}")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except QuotaExceededError as e:
        logger.warning(f"Quota exceeded for user {current_user}: {e}")
        error_response = await handle_video_upload_error(
            error=e,
            error_code=VideoUploadErrorCodes.QUOTA_EXCEEDED,
            video_id=video_id,
            session_id=session_id,
            s3_key=s3_key,
            user_id=current_user
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error_response.dict()
        )
    except Exception as e:
        logger.error(f"Upload failed for user {current_user}: {str(e)}")
        error_response = await handle_video_upload_error(
            error=e,
            error_code=VideoUploadErrorCodes.DATABASE_ERROR,
            video_id=video_id,
            session_id=session_id,
            s3_key=s3_key,
            user_id=current_user
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.dict()
        )


@router.get(
    "/{session_id}/status",
    status_code=status.HTTP_200_OK,
    summary="Get Upload Status",
    description="Get status of video upload by session ID"
)
async def get_upload_status(
    session_id: UUID,
    current_user: UUID = Depends(get_current_user_jwt)
) -> Dict[str, Any]:
    """
    Get upload status for a session.
    
    Args:
        session_id: Upload session ID
        current_user: Current authenticated user
        
    Returns:
        Dictionary with upload status information
    """
    try:
        # Validate session
        session_validation = await validate_upload_session_redis(session_id, current_user)
        if not session_validation['is_valid']:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": VideoUploadErrorCodes.SESSION_NOT_FOUND,
                    "error_message": session_validation.get('error', 'Session not found')
                }
            )
        
        # In a real implementation, this would query the database for upload status
        return {
            "session_id": str(session_id),
            "status": "active",
            "message": "Session is valid and active"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get upload status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": VideoUploadErrorCodes.DATABASE_ERROR,
                "error_message": "Failed to get upload status"
            }
        )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel Upload Session",
    description="Cancel upload session and cleanup resources"
)
async def cancel_upload_session(
    session_id: UUID,
    current_user: UUID = Depends(get_current_user_jwt)
):
    """
    Cancel upload session and cleanup resources.
    
    Args:
        session_id: Upload session ID to cancel
        current_user: Current authenticated user
    """
    try:
        # Validate session ownership
        session_validation = await validate_upload_session_redis(session_id, current_user)
        if not session_validation['is_valid']:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": VideoUploadErrorCodes.SESSION_NOT_FOUND,
                    "error_message": "Session not found or expired"
                }
            )
        
        # Cleanup session
        from src.utils.error_handlers import get_video_upload_redis_utils
        redis_utils = get_video_upload_redis_utils()
        await redis_utils.cleanup_upload_session(session_id, current_user)
        
        logger.info(f"Cancelled upload session {session_id} for user {current_user}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel upload session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": VideoUploadErrorCodes.DATABASE_ERROR,
                "error_message": "Failed to cancel upload session"
            }
        )
