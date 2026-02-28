#!/usr/bin/env python3
"""
Upload API Endpoints
API endpoints for generating S3 presigned URLs for secure file uploads
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from ...services.s3_presigned_service import get_s3_presigned_service
from ...middleware.cognito_auth import get_current_user
from ...utils.file_validation import validate_video_file
from ...config.aws_config import get_s3_config
from ...errors.api_errors import (
    ValidationError,
    FileValidationError,
    InvalidFileTypeError,
    FileSizeExceededError
)


# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/v1/upload", tags=["upload"])


@router.get("/presigned-url")
async def generate_presigned_upload_url(
    filename: str = Query(..., description="Original filename"),
    content_type: str = Query(..., description="File MIME type"),
    file_size: int = Query(..., description="File size in bytes", gt=0),
    expires_in: int = Query(3600, description="URL expiration time in seconds", ge=300, le=86400),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> JSONResponse:
    """
    Generate a presigned URL for secure file upload to S3.
    
    This endpoint creates a secure, time-limited URL that allows direct upload
    to S3 without exposing AWS credentials to the client.
    
    Args:
        filename: Original filename of the file to upload
        content_type: MIME type of the file (e.g., video/mp4)
        file_size: Size of the file in bytes
        expires_in: URL expiration time in seconds (300-86400, default: 3600)
        current_user: Authenticated user information
        
    Returns:
        JSON response with presigned URL and upload details
        
    Raises:
        HTTPException: If validation fails or S3 service error occurs
    """
    try:
        # Get configuration
        s3_config = get_s3_config()
        
        # Validate file
        logger.info(f"Validating file upload: {filename} ({file_size} bytes, {content_type})")
        validation_result = validate_video_file(
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            max_size=s3_config.max_file_size
        )
        
        if not validation_result['is_valid']:
            errors = validation_result.get('errors', [])
            if any('Invalid content type' in error for error in errors):
                raise InvalidFileTypeError(
                    content_type=content_type,
                    allowed_types=['video/mp4', 'video/avi', 'video/mov', 'video/mkv', 'video/webm', 'video/ogg'],
                    filename=filename
                )
            elif any('File too large' in error for error in errors):
                raise FileSizeExceededError(
                    file_size=file_size,
                    max_size=s3_config.max_file_size,
                    filename=filename
                )
            else:
                raise FileValidationError(
                    message=f"File validation failed: {'; '.join(errors)}",
                    filename=filename,
                    file_size=file_size,
                    content_type=content_type
                )
        
        # Log warnings if any
        warnings = validation_result.get('warnings', [])
        if warnings:
            logger.warning(f"File validation warnings for {filename}: {warnings}")
        
        # Get S3 service
        s3_service = get_s3_presigned_service()
        
        # Extract user ID for organization
        user_id = current_user.get('user_id')
        username = current_user.get('username', 'unknown')
        
        # Prepare metadata
        metadata = {
            'uploaded-by': username,
            'upload-source': 'api',
            'original-filename': filename
        }
        
        # Generate presigned URL
        logger.info(f"Generating presigned URL for user {user_id}: {filename}")
        upload_data = s3_service.generate_presigned_url(
            s3_key=s3_service.generate_s3_key(filename, user_id, s3_config.upload_prefix),
            content_type=content_type,
            file_size=file_size,
            expires_in=expires_in,
            user_id=user_id,
            metadata=metadata
        )
        
        # Prepare response
        response_data = {
            'success': True,
            'data': {
                'presigned_url': upload_data['presigned_url'],
                'upload_url': upload_data['upload_url'],
                's3_key': upload_data['s3_key'],
                'bucket': upload_data['bucket'],
                'region': upload_data['region'],
                'expires_at': upload_data['expires_at'],
                'expires_in': upload_data['expires_in'],
                'required_headers': upload_data['required_headers'],
                'metadata': upload_data['metadata']
            }
        }
        
        # Add warnings to response if any
        if warnings:
            response_data['warnings'] = warnings
        
        logger.info(f"Successfully generated presigned URL for {filename} (user: {user_id})")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_data,
            headers={
                'X-Upload-Expires-At': upload_data['expires_at'],
                'X-Upload-Expires-In': str(upload_data['expires_in']),
                'X-S3-Key': upload_data['s3_key']
            }
        )
        
    except (InvalidFileTypeError, FileSizeExceededError, FileValidationError) as e:
        logger.warning(f"File validation failed for {filename}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                'success': False,
                'error': {
                    'code': e.error_code,
                    'message': e.message,
                    'details': e.details
                }
            }
        )
    except ValidationError as e:
        logger.warning(f"Validation error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
        logger.error(f"Unexpected error generating presigned URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                'success': False,
                'error': {
                    'code': 'INTERNAL_SERVER_ERROR',
                    'message': 'Failed to generate presigned URL',
                    'details': {'original_error': str(e)}
                }
            }
        )


@router.get("/presigned-post")
async def generate_presigned_post_url(
    filename: str = Query(..., description="Original filename"),
    content_type: str = Query(..., description="File MIME type"),
    file_size: int = Query(..., description="File size in bytes", gt=0),
    expires_in: int = Query(3600, description="URL expiration time in seconds", ge=300, le=86400),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> JSONResponse:
    """
    Generate a presigned POST URL for multipart file upload to S3.
    
    This endpoint creates a presigned POST form that allows multipart uploads
    directly to S3, useful for large files or when you need more control over
    the upload process.
    
    Args:
        filename: Original filename of the file to upload
        content_type: MIME type of the file (e.g., video/mp4)
        file_size: Size of the file in bytes
        expires_in: URL expiration time in seconds (300-86400, default: 3600)
        current_user: Authenticated user information
        
    Returns:
        JSON response with presigned POST data
        
    Raises:
        HTTPException: If validation fails or S3 service error occurs
    """
    try:
        # Get configuration
        s3_config = get_s3_config()
        
        # Validate file
        logger.info(f"Validating file upload (POST): {filename} ({file_size} bytes, {content_type})")
        validation_result = validate_video_file(
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            max_size=s3_config.max_file_size
        )
        
        if not validation_result['is_valid']:
            errors = validation_result.get('errors', [])
            if any('Invalid content type' in error for error in errors):
                raise InvalidFileTypeError(
                    content_type=content_type,
                    allowed_types=['video/mp4', 'video/avi', 'video/mov', 'video/mkv', 'video/webm', 'video/ogg'],
                    filename=filename
                )
            elif any('File too large' in error for error in errors):
                raise FileSizeExceededError(
                    file_size=file_size,
                    max_size=s3_config.max_file_size,
                    filename=filename
                )
            else:
                raise FileValidationError(
                    message=f"File validation failed: {'; '.join(errors)}",
                    filename=filename,
                    file_size=file_size,
                    content_type=content_type
                )
        
        # Log warnings if any
        warnings = validation_result.get('warnings', [])
        if warnings:
            logger.warning(f"File validation warnings for {filename}: {warnings}")
        
        # Get S3 service
        s3_service = get_s3_presigned_service()
        
        # Extract user ID for organization
        user_id = current_user.get('user_id')
        username = current_user.get('username', 'unknown')
        
        # Prepare metadata
        metadata = {
            'uploaded-by': username,
            'upload-source': 'api-post',
            'original-filename': filename
        }
        
        # Generate presigned POST
        logger.info(f"Generating presigned POST for user {user_id}: {filename}")
        upload_data = s3_service.generate_presigned_post(
            s3_key=s3_service.generate_s3_key(filename, user_id, s3_config.upload_prefix),
            content_type=content_type,
            file_size=file_size,
            expires_in=expires_in,
            user_id=user_id,
            metadata=metadata
        )
        
        # Prepare response
        response_data = {
            'success': True,
            'data': {
                'presigned_post': upload_data['presigned_post'],
                'upload_url': upload_data['upload_url'],
                's3_key': upload_data['s3_key'],
                'bucket': upload_data['bucket'],
                'region': upload_data['region'],
                'expires_at': upload_data['expires_at'],
                'expires_in': upload_data['expires_in'],
                'metadata': upload_data['metadata']
            }
        }
        
        # Add warnings to response if any
        if warnings:
            response_data['warnings'] = warnings
        
        logger.info(f"Successfully generated presigned POST for {filename} (user: {user_id})")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_data,
            headers={
                'X-Upload-Expires-At': upload_data['expires_at'],
                'X-Upload-Expires-In': str(upload_data['expires_in']),
                'X-S3-Key': upload_data['s3_key']
            }
        )
        
    except (InvalidFileTypeError, FileSizeExceededError, FileValidationError) as e:
        logger.warning(f"File validation failed for {filename}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                'success': False,
                'error': {
                    'code': e.error_code,
                    'message': e.message,
                    'details': e.details
                }
            }
        )
    except ValidationError as e:
        logger.warning(f"Validation error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
        logger.error(f"Unexpected error generating presigned POST: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                'success': False,
                'error': {
                    'code': 'INTERNAL_SERVER_ERROR',
                    'message': 'Failed to generate presigned POST',
                    'details': {'original_error': str(e)}
                }
            }
        )


@router.get("/verify/{s3_key:path}")
async def verify_upload(
    s3_key: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> JSONResponse:
    """
    Verify that a file was successfully uploaded to S3.
    
    This endpoint checks if a file exists in S3 and returns its metadata.
    
    Args:
        s3_key: S3 object key to verify
        current_user: Authenticated user information
        
    Returns:
        JSON response with verification results
        
    Raises:
        HTTPException: If verification fails
    """
    try:
        # Get S3 service
        s3_service = get_s3_presigned_service()
        
        # Verify upload
        logger.info(f"Verifying upload for user {current_user.get('user_id')}: {s3_key}")
        verification_result = s3_service.verify_upload(s3_key)
        
        if verification_result['exists']:
            response_data = {
                'success': True,
                'data': {
                    'exists': True,
                    'size': verification_result['size'],
                    'last_modified': verification_result['last_modified'].isoformat() if verification_result['last_modified'] else None,
                    'etag': verification_result['etag'],
                    'content_type': verification_result['content_type'],
                    'metadata': verification_result['metadata'],
                    's3_url': verification_result['s3_url']
                }
            }
        else:
            response_data = {
                'success': True,
                'data': {
                    'exists': False,
                    'error': verification_result.get('error', 'Object not found')
                }
            }
        
        logger.info(f"Upload verification completed for {s3_key}: {verification_result['exists']}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_data
        )
        
    except Exception as e:
        logger.error(f"Error verifying upload {s3_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                'success': False,
                'error': {
                    'code': 'VERIFICATION_ERROR',
                    'message': 'Failed to verify upload',
                    'details': {'original_error': str(e)}
                }
            }
        )


@router.get("/config")
async def get_upload_config(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> JSONResponse:
    """
    Get upload configuration information.
    
    Returns configuration details that clients need for file uploads,
    including allowed file types, size limits, and other constraints.
    
    Args:
        current_user: Authenticated user information
        
    Returns:
        JSON response with upload configuration
    """
    try:
        # Get configuration
        s3_config = get_s3_config()
        
        response_data = {
            'success': True,
            'data': {
                'max_file_size': s3_config.max_file_size,
                'max_file_size_formatted': _format_file_size(s3_config.max_file_size),
                'allowed_content_types': [
                    'video/mp4',
                    'video/avi',
                    'video/mov',
                    'video/quicktime',
                    'video/x-msvideo',
                    'video/mkv',
                    'video/x-matroska',
                    'video/webm',
                    'video/ogg'
                ],
                'allowed_extensions': [
                    '.mp4',
                    '.avi',
                    '.mov',
                    '.mkv',
                    '.webm',
                    '.ogg'
                ],
                'default_url_expiration': 3600,
                'min_url_expiration': 300,
                'max_url_expiration': 86400,
                'bucket_region': s3_config.region,
                'supports_presigned_urls': True,
                'supports_presigned_posts': True
            }
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_data
        )
        
    except Exception as e:
        logger.error(f"Error getting upload config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                'success': False,
                'error': {
                    'code': 'CONFIG_ERROR',
                    'message': 'Failed to get upload configuration',
                    'details': {'original_error': str(e)}
                }
            }
        )


def _format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 Bytes"
    
    size_names = ["Bytes", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


# Export router
__all__ = ['router']
