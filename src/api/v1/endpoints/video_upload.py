#!/usr/bin/env python3
"""
Enhanced Video Upload Endpoint
POST /v1/upload/video endpoint with multipart file uploads, progressive upload support,
and automatic processing integration
"""

import os
import uuid
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse

from ...services.video_upload_service import VideoUploadService
from ...core.celery_tasks import process_video_async
from ...models.video import EnhancedVideoDetectionRequest, VideoUploadResponse
from ...utils.file_validation import validate_video_file_content
from ...utils.hash_generator import generate_content_hash
from ...config.settings import get_upload_settings
from ...schemas.websocket_events import UploadProgressEvent, ProcessingInitiatedEvent
from ...middleware.cognito_auth import get_current_user_optional
from ...errors.api_errors import (
    ValidationError,
    FileValidationError,
    UploadSessionError,
    ProcessingError
)


# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/v1/upload", tags=["video-upload"])

# Global upload service instance
_upload_service: Optional[VideoUploadService] = None


def get_upload_service() -> VideoUploadService:
    """Get or create the global upload service instance."""
    global _upload_service
    if _upload_service is None:
        _upload_service = VideoUploadService()
    return _upload_service


@router.post("/video", response_model=VideoUploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    chunk_index: Optional[int] = Form(None),
    total_chunks: Optional[int] = Form(None),
    file_hash: Optional[str] = Form(None),
    options: Optional[str] = Form(None),
    priority: Optional[int] = Form(None),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> JSONResponse:
    """
    Enhanced video upload endpoint with multipart support and progressive upload.
    
    Supports:
    - Single file uploads (traditional)
    - Multipart chunked uploads
    - Progressive upload resumption
    - Hash-based deduplication
    - Automatic processing initiation
    
    Args:
        file: Video file or chunk
        session_id: Upload session ID for progressive uploads
        chunk_index: Current chunk index (0-based)
        total_chunks: Total number of chunks
        file_hash: Pre-calculated file hash for deduplication
        options: JSON string with upload options
        priority: Processing priority (1-10)
        current_user: Authenticated user (optional)
        
    Returns:
        JSON response with upload details and processing information
    """
    try:
        # Get upload service and settings
        upload_service = get_upload_service()
        settings = get_upload_settings()
        
        # Extract user information
        user_id = current_user.get('user_id') if current_user else None
        username = current_user.get('username', 'anonymous') if current_user else 'anonymous'
        
        logger.info(f"Video upload started by user {username}: {file.filename}")
        
        # Parse options if provided
        upload_options = {}
        if options:
            try:
                import json
                upload_options = json.loads(options)
            except json.JSONDecodeError:
                raise ValidationError("Invalid options JSON format")
        
        # Validate priority if provided
        if priority is not None:
            if not (1 <= priority <= 10):
                raise ValidationError("Priority must be between 1 and 10")
        
        # Handle different upload types
        if chunk_index is not None and total_chunks is not None:
            # Multipart chunked upload
            return await _handle_chunked_upload(
                upload_service=upload_service,
                file=file,
                session_id=session_id,
                chunk_index=chunk_index,
                total_chunks=total_chunks,
                file_hash=file_hash,
                upload_options=upload_options,
                priority=priority,
                user_id=user_id,
                username=username,
                background_tasks=background_tasks
            )
        else:
            # Single file upload
            return await _handle_single_upload(
                upload_service=upload_service,
                file=file,
                file_hash=file_hash,
                upload_options=upload_options,
                priority=priority,
                user_id=user_id,
                username=username,
                background_tasks=background_tasks
            )
            
    except ValidationError as e:
        logger.warning(f"Validation error in upload: {e.message}")
        raise HTTPException(
            status_code=422,
            detail={
                'success': False,
                'error': {
                    'code': e.error_code,
                    'message': e.message,
                    'details': e.details
                }
            }
        )
    except FileValidationError as e:
        logger.warning(f"File validation error: {e.message}")
        raise HTTPException(
            status_code=400,
            detail={
                'success': False,
                'error': {
                    'code': e.error_code,
                    'message': e.message,
                    'details': e.details
                }
            }
        )
    except UploadSessionError as e:
        logger.warning(f"Upload session error: {e.message}")
        raise HTTPException(
            status_code=409,
            detail={
                'success': False,
                'error': {
                    'code': e.error_code,
                    'message': e.message,
                    'details': e.details
                }
            }
        )
    except ProcessingError as e:
        logger.error(f"Processing error: {e.message}")
        raise HTTPException(
            status_code=500,
            detail={
                'success': False,
                'error': {
                    'code': e.error_code,
                    'message': e.message,
                    'details': e.details
                }
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in video upload: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                'success': False,
                'error': {
                    'code': 'INTERNAL_SERVER_ERROR',
                    'message': 'An unexpected error occurred during upload',
                    'details': {'original_error': str(e)}
                }
            }
        )


async def _handle_single_upload(
    upload_service: VideoUploadService,
    file: UploadFile,
    file_hash: Optional[str],
    upload_options: Dict[str, Any],
    priority: Optional[int],
    user_id: Optional[str],
    username: str,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """Handle single file upload."""
    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validate file
        validation_result = await validate_video_file_content(
            filename=file.filename,
            content_type=file.content_type,
            file_size=file_size,
            content=file_content
        )
        
        if not validation_result['is_valid']:
            raise FileValidationError(
                message=f"File validation failed: {'; '.join(validation_result['errors'])}",
                filename=file.filename,
                file_size=file_size,
                content_type=file.content_type,
                details=validation_result
            )
        
        # Generate file hash if not provided
        if not file_hash:
            file_hash = await generate_content_hash(file_content)
        
        # Check for deduplication
        duplicate_result = await upload_service.check_duplicate(file_hash)
        if duplicate_result['is_duplicate']:
            logger.info(f"Duplicate file detected: {file.filename} (hash: {file_hash[:8]}...)")
            
            # Return instant result for duplicate
            return JSONResponse(
                status_code=200,
                content={
                    'success': True,
                    'duplicate': True,
                    'data': {
                        'upload_id': duplicate_result['upload_id'],
                        'file_hash': file_hash,
                        'analysis_id': duplicate_result['analysis_id'],
                        'result': duplicate_result['result'],
                        'processing_time_ms': duplicate_result.get('processing_time_ms', 0),
                        'message': 'File already analyzed - returning cached result'
                    }
                }
            )
        
        # Save file and create upload record
        upload_result = await upload_service.save_uploaded_file(
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type,
            file_hash=file_hash,
            user_id=user_id,
            upload_options=upload_options
        )
        
        # Initiate async processing
        processing_task = background_tasks.add_task(
            process_video_async.delay,
            upload_result['file_path'],
            upload_result['upload_id'],
            upload_options,
            priority or 5,
            user_id
        )
        
        logger.info(f"Upload completed for {file.filename}, processing initiated")
        
        # Prepare response
        response_data = {
            'success': True,
            'duplicate': False,
            'data': {
                'upload_id': upload_result['upload_id'],
                'analysis_id': upload_result['analysis_id'],
                'filename': file.filename,
                'file_size': file_size,
                'file_hash': file_hash,
                'processing_job_id': str(processing_task),
                'estimated_completion_time': _estimate_completion_time(file_size),
                'upload_timestamp': datetime.now(timezone.utc).isoformat(),
                'status': 'processing_initiated'
            }
        }
        
        return JSONResponse(status_code=200, content=response_data)
        
    except Exception as e:
        logger.error(f"Error in single upload: {e}")
        raise


async def _handle_chunked_upload(
    upload_service: VideoUploadService,
    file: UploadFile,
    session_id: Optional[str],
    chunk_index: int,
    total_chunks: int,
    file_hash: Optional[str],
    upload_options: Dict[str, Any],
    priority: Optional[int],
    user_id: Optional[str],
    username: str,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """Handle multipart chunked upload."""
    try:
        # Read chunk content
        chunk_content = await file.read()
        
        # Create or update upload session
        session_result = await upload_service.handle_chunk(
            session_id=session_id,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            chunk_content=chunk_content,
            filename=file.filename,
            file_hash=file_hash,
            user_id=user_id,
            upload_options=upload_options
        )
        
        # Check if upload is complete
        if session_result['upload_complete']:
            # Validate complete file
            complete_file_content = session_result['complete_file_content']
            file_size = len(complete_file_content)
            
            validation_result = await validate_video_file_content(
                filename=file.filename,
                content_type=file.content_type or 'video/mp4',
                file_size=file_size,
                content=complete_file_content
            )
            
            if not validation_result['is_valid']:
                # Clean up session on validation failure
                await upload_service.cleanup_session(session_result['session_id'])
                raise FileValidationError(
                    message=f"File validation failed: {'; '.join(validation_result['errors'])}",
                    filename=file.filename,
                    file_size=file_size,
                    content_type=file.content_type,
                    details=validation_result
                )
            
            # Generate final hash if not provided
            if not file_hash:
                file_hash = await generate_content_hash(complete_file_content)
            
            # Check for deduplication
            duplicate_result = await upload_service.check_duplicate(file_hash)
            if duplicate_result['is_duplicate']:
                logger.info(f"Duplicate file detected in chunked upload: {file.filename}")
                
                # Clean up session
                await upload_service.cleanup_session(session_result['session_id'])
                
                return JSONResponse(
                    status_code=200,
                    content={
                        'success': True,
                        'duplicate': True,
                        'upload_complete': True,
                        'data': {
                            'upload_id': duplicate_result['upload_id'],
                            'file_hash': file_hash,
                            'analysis_id': duplicate_result['analysis_id'],
                            'result': duplicate_result['result'],
                            'processing_time_ms': duplicate_result.get('processing_time_ms', 0),
                            'message': 'File already analyzed - returning cached result'
                        }
                    }
                )
            
            # Save complete file
            upload_result = await upload_service.save_uploaded_file(
                file_content=complete_file_content,
                filename=file.filename,
                content_type=file.content_type or 'video/mp4',
                file_hash=file_hash,
                user_id=user_id,
                upload_options=upload_options
            )
            
            # Initiate async processing
            processing_task = background_tasks.add_task(
                process_video_async.delay,
                upload_result['file_path'],
                upload_result['upload_id'],
                upload_options,
                priority or 5,
                user_id
            )
            
            # Clean up session
            await upload_service.cleanup_session(session_result['session_id'])
            
            logger.info(f"Chunked upload completed for {file.filename}, processing initiated")
            
            return JSONResponse(
                status_code=200,
                content={
                    'success': True,
                    'duplicate': False,
                    'upload_complete': True,
                    'data': {
                        'upload_id': upload_result['upload_id'],
                        'analysis_id': upload_result['analysis_id'],
                        'filename': file.filename,
                        'file_size': file_size,
                        'file_hash': file_hash,
                        'processing_job_id': str(processing_task),
                        'estimated_completion_time': _estimate_completion_time(file_size),
                        'upload_timestamp': datetime.now(timezone.utc).isoformat(),
                        'status': 'processing_initiated'
                    }
                }
            )
        else:
            # Upload not complete, return session info
            return JSONResponse(
                status_code=200,
                content={
                    'success': True,
                    'upload_complete': False,
                    'data': {
                        'session_id': session_result['session_id'],
                        'chunks_received': session_result['chunks_received'],
                        'total_chunks': total_chunks,
                        'progress_percentage': round((session_result['chunks_received'] / total_chunks) * 100, 2),
                        'status': 'upload_in_progress'
                    }
                }
            )
            
    except Exception as e:
        logger.error(f"Error in chunked upload: {e}")
        raise


@router.get("/video/session/{session_id}")
async def get_upload_session_status(
    session_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> JSONResponse:
    """
    Get upload session status for progressive upload resumption.
    
    Args:
        session_id: Upload session ID
        current_user: Authenticated user (optional)
        
    Returns:
        JSON response with session status
    """
    try:
        upload_service = get_upload_service()
        
        session_status = await upload_service.get_session_status(session_id)
        
        if not session_status:
            raise HTTPException(
                status_code=404,
                detail={
                    'success': False,
                    'error': {
                        'code': 'SESSION_NOT_FOUND',
                        'message': 'Upload session not found',
                        'details': {'session_id': session_id}
                    }
                }
            )
        
        return JSONResponse(
            status_code=200,
            content={
                'success': True,
                'data': session_status
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                'success': False,
                'error': {
                    'code': 'INTERNAL_SERVER_ERROR',
                    'message': 'Failed to get session status',
                    'details': {'original_error': str(e)}
                }
            }
        )


@router.delete("/video/session/{session_id}")
async def cancel_upload_session(
    session_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> JSONResponse:
    """
    Cancel and cleanup an upload session.
    
    Args:
        session_id: Upload session ID
        current_user: Authenticated user (optional)
        
    Returns:
        JSON response with cancellation status
    """
    try:
        upload_service = get_upload_service()
        
        await upload_service.cleanup_session(session_id)
        
        return JSONResponse(
            status_code=200,
            content={
                'success': True,
                'message': 'Upload session cancelled and cleaned up'
            }
        )
        
    except Exception as e:
        logger.error(f"Error cancelling session: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                'success': False,
                'error': {
                    'code': 'INTERNAL_SERVER_ERROR',
                    'message': 'Failed to cancel upload session',
                    'details': {'original_error': str(e)}
                }
            }
        )


def _estimate_completion_time(file_size: int) -> str:
    """
    Estimate processing completion time based on file size.
    
    Args:
        file_size: File size in bytes
        
    Returns:
        ISO timestamp string for estimated completion
    """
    # Rough estimate: 1 second per MB of video
    estimated_seconds = max(30, file_size // (1024 * 1024))
    completion_time = datetime.now(timezone.utc).timestamp() + estimated_seconds
    return datetime.fromtimestamp(completion_time, timezone.utc).isoformat()


# Export router
__all__ = ['router']
