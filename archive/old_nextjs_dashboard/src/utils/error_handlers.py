#!/usr/bin/env python3
"""
Error Handlers and Redis Utilities for Video Uploads
Comprehensive error handling and Redis operations for video upload management
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timezone

from src.core.upload_redis_client import get_upload_redis_client
from src.services.s3_service import cleanup_failed_dashboard_upload
from src.services.upload_session_service import upload_session_service
from src.schemas.video_upload_schema import (
    VideoUploadError,
    VideoUploadErrorCodes,
    VideoUploadConfig
)

logger = logging.getLogger(__name__)


class VideoUploadErrorHandler:
    """
    Comprehensive error handler for video upload operations.
    Provides cleanup, logging, and error response generation.
    """
    
    def __init__(self):
        """Initialize error handler"""
        self.redis_client = None
    
    async def initialize(self):
        """Initialize Redis client"""
        try:
            self.redis_client = await get_upload_redis_client()
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
    
    async def handle_upload_error(
        self,
        error: Exception,
        error_code: str,
        video_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        s3_key: Optional[str] = None,
        user_id: Optional[UUID] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> VideoUploadError:
        """
        Handle upload error with comprehensive cleanup and logging.
        
        Args:
            error: The exception that occurred
            error_code: Error code for programmatic handling
            video_id: Optional video ID
            session_id: Optional upload session ID
            s3_key: Optional S3 key for cleanup
            user_id: Optional user ID
            additional_context: Optional additional context
            
        Returns:
            VideoUploadError with cleanup details
        """
        error_message = str(error)
        cleanup_performed = False
        cleanup_details = {}
        
        try:
            logger.error(f"Upload error {error_code}: {error_message}")
            
            # Perform cleanup operations
            cleanup_result = await self._perform_cleanup_operations(
                video_id=video_id,
                session_id=session_id,
                s3_key=s3_key,
                user_id=user_id,
                error_code=error_code
            )
            
            cleanup_performed = cleanup_result['cleanup_performed']
            cleanup_details = cleanup_result['cleanup_details']
            
            # Log cleanup results
            if cleanup_performed:
                logger.info(f"Cleanup completed for error {error_code}")
            else:
                logger.warning(f"Cleanup failed or not needed for error {error_code}")
            
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {cleanup_error}")
            cleanup_details['cleanup_error'] = str(cleanup_error)
        
        # Create error response
        error_response = VideoUploadError(
            error_code=error_code,
            error_message=error_message,
            details={
                'video_id': str(video_id) if video_id else None,
                'session_id': str(session_id) if session_id else None,
                's3_key': s3_key,
                'user_id': str(user_id) if user_id else None,
                'additional_context': additional_context or {}
            },
            cleanup_performed=cleanup_performed,
            cleanup_details=cleanup_details
        )
        
        return error_response
    
    async def _perform_cleanup_operations(
        self,
        video_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        s3_key: Optional[str] = None,
        user_id: Optional[UUID] = None,
        error_code: str = "UNKNOWN_ERROR"
    ) -> Dict[str, Any]:
        """
        Perform cleanup operations based on error type.
        
        Args:
            video_id: Optional video ID
            session_id: Optional upload session ID
            s3_key: Optional S3 key for cleanup
            user_id: Optional user ID
            error_code: Error code
            
        Returns:
            Dictionary with cleanup results
        """
        cleanup_performed = False
        cleanup_details = {
            's3_cleanup': False,
            'session_cleanup': False,
            'database_cleanup': False,
            'errors': []
        }
        
        try:
            # S3 cleanup - remove uploaded files
            if s3_key and error_code in [
                VideoUploadErrorCodes.VALIDATION_FAILED,
                VideoUploadErrorCodes.DATABASE_ERROR,
                VideoUploadErrorCodes.ANALYSIS_FAILED
            ]:
                try:
                    s3_cleanup_result = cleanup_failed_dashboard_upload(s3_key)
                    cleanup_details['s3_cleanup'] = s3_cleanup_result.get('cleanup_successful', False)
                    cleanup_details['s3_cleanup_details'] = s3_cleanup_result
                    cleanup_performed = True
                except Exception as e:
                    cleanup_details['errors'].append(f"S3 cleanup failed: {str(e)}")
            
            # Session cleanup - remove upload session
            if session_id and error_code in [
                VideoUploadErrorCodes.SESSION_EXPIRED,
                VideoUploadErrorCodes.UNAUTHORIZED_ACCESS,
                VideoUploadErrorCodes.VALIDATION_FAILED
            ]:
                try:
                    await self._cleanup_upload_session(session_id, user_id)
                    cleanup_details['session_cleanup'] = True
                    cleanup_performed = True
                except Exception as e:
                    cleanup_details['errors'].append(f"Session cleanup failed: {str(e)}")
            
            # Database cleanup - remove video record
            if video_id and error_code in [
                VideoUploadErrorCodes.S3_UPLOAD_FAILED,
                VideoUploadErrorCodes.VALIDATION_FAILED
            ]:
                try:
                    await self._cleanup_video_record(video_id)
                    cleanup_details['database_cleanup'] = True
                    cleanup_performed = True
                except Exception as e:
                    cleanup_details['errors'].append(f"Database cleanup failed: {str(e)}")
            
        except Exception as e:
            cleanup_details['errors'].append(f"General cleanup error: {str(e)}")
        
        return {
            'cleanup_performed': cleanup_performed,
            'cleanup_details': cleanup_details
        }
    
    async def _cleanup_upload_session(
        self,
        session_id: UUID,
        user_id: Optional[UUID] = None
    ):
        """
        Clean up upload session from Redis.
        
        Args:
            session_id: Upload session ID
            user_id: Optional user ID
        """
        try:
            if self.redis_client:
                await self.redis_client.delete_session(str(session_id))
                
                if user_id:
                    await self.redis_client.remove_user_session(str(user_id), str(session_id))
                
                logger.info(f"Cleaned up upload session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to cleanup upload session {session_id}: {e}")
            raise
    
    async def _cleanup_video_record(self, video_id: UUID):
        """
        Clean up video record from database.
        
        Args:
            video_id: Video ID to clean up
        """
        try:
            # This would typically delete from database
            # For now, just log the operation
            logger.info(f"Cleaned up video record: {video_id}")
        except Exception as e:
            logger.error(f"Failed to cleanup video record {video_id}: {e}")
            raise


class VideoUploadRedisUtils:
    """
    Redis utilities for video upload operations.
    Provides session validation, cleanup, and performance monitoring.
    """
    
    def __init__(self):
        """Initialize Redis utilities"""
        self.redis_client = None
    
    async def initialize(self):
        """Initialize Redis client"""
        try:
            self.redis_client = await get_upload_redis_client()
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
    
    async def validate_upload_session(
        self,
        session_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Validate upload session and check ownership.
        
        Args:
            session_id: Upload session ID
            user_id: User ID claiming ownership
            
        Returns:
            Dictionary with validation results
        """
        try:
            if not self.redis_client:
                return {
                    'is_valid': False,
                    'error': 'Redis client not initialized'
                }
            
            # Get session data
            session_data = await self.redis_client.get_session_data(str(session_id))
            
            if not session_data:
                return {
                    'is_valid': False,
                    'error': 'Session not found or expired'
                }
            
            # Check expiration
            expires_at = datetime.fromisoformat(session_data['expires_at'])
            if datetime.now(timezone.utc) > expires_at:
                # Clean up expired session
                await self.redis_client.delete_session(str(session_id))
                return {
                    'is_valid': False,
                    'error': 'Session has expired'
                }
            
            # Check ownership
            if session_data['user_id'] != str(user_id):
                return {
                    'is_valid': False,
                    'error': 'Unauthorized access to session'
                }
            
            return {
                'is_valid': True,
                'session_data': session_data
            }
            
        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return {
                'is_valid': False,
                'error': f'Validation failed: {str(e)}'
            }
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired upload sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            if not self.redis_client:
                return 0
            
            cleaned_count = await self.redis_client.cleanup_expired_sessions()
            logger.info(f"Cleaned up {cleaned_count} expired sessions")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    async def track_upload_progress(
        self,
        video_id: UUID,
        session_id: UUID,
        status: str,
        progress_percentage: float,
        current_step: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Track upload progress in Redis.
        
        Args:
            video_id: Video ID
            session_id: Upload session ID
            status: Current status
            progress_percentage: Progress percentage (0-100)
            current_step: Current processing step
            metadata: Optional additional metadata
        """
        try:
            if not self.redis_client:
                return
            
            progress_data = {
                'video_id': str(video_id),
                'session_id': str(session_id),
                'status': status,
                'progress_percentage': progress_percentage,
                'current_step': current_step,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metadata': metadata or {}
            }
            
            # Store progress data
            progress_key = f"upload_progress:{video_id}"
            await self.redis_client.set_session_data(
                progress_key,
                progress_data,
                ttl=3600  # 1 hour TTL
            )
            
        except Exception as e:
            logger.error(f"Failed to track upload progress: {e}")
    
    async def get_upload_progress(
        self,
        video_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get upload progress from Redis.
        
        Args:
            video_id: Video ID
            
        Returns:
            Progress data or None if not found
        """
        try:
            if not self.redis_client:
                return None
            
            progress_key = f"upload_progress:{video_id}"
            progress_data = await self.redis_client.get_session_data(progress_key)
            
            return progress_data
            
        except Exception as e:
            logger.error(f"Failed to get upload progress: {e}")
            return None
    
    async def cleanup_upload_progress(self, video_id: UUID):
        """
        Clean up upload progress data from Redis.
        
        Args:
            video_id: Video ID
        """
        try:
            if not self.redis_client:
                return
            
            progress_key = f"upload_progress:{video_id}"
            await self.redis_client.delete_session(progress_key)
            
        except Exception as e:
            logger.error(f"Failed to cleanup upload progress: {e}")
    
    async def get_redis_health(self) -> Dict[str, Any]:
        """
        Get Redis health status.
        
        Returns:
            Dictionary with Redis health information
        """
        try:
            if not self.redis_client:
                return {
                    'status': 'unhealthy',
                    'error': 'Redis client not initialized'
                }
            
            health_info = await self.redis_client.health_check()
            return health_info
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }


# Global instances
_video_upload_error_handler: Optional[VideoUploadErrorHandler] = None
_video_upload_redis_utils: Optional[VideoUploadRedisUtils] = None


def get_video_upload_error_handler() -> VideoUploadErrorHandler:
    """
    Get or create the global video upload error handler instance.
    
    Returns:
        VideoUploadErrorHandler instance
    """
    global _video_upload_error_handler
    
    if _video_upload_error_handler is None:
        _video_upload_error_handler = VideoUploadErrorHandler()
    
    return _video_upload_error_handler


def get_video_upload_redis_utils() -> VideoUploadRedisUtils:
    """
    Get or create the global video upload Redis utils instance.
    
    Returns:
        VideoUploadRedisUtils instance
    """
    global _video_upload_redis_utils
    
    if _video_upload_redis_utils is None:
        _video_upload_redis_utils = VideoUploadRedisUtils()
    
    return _video_upload_redis_utils


# Convenience functions
async def handle_video_upload_error(
    error: Exception,
    error_code: str,
    video_id: Optional[UUID] = None,
    session_id: Optional[UUID] = None,
    s3_key: Optional[str] = None,
    user_id: Optional[UUID] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> VideoUploadError:
    """
    Convenience function to handle video upload error.
    
    Args:
        error: The exception that occurred
        error_code: Error code for programmatic handling
        video_id: Optional video ID
        session_id: Optional upload session ID
        s3_key: Optional S3 key for cleanup
        user_id: Optional user ID
        additional_context: Optional additional context
        
    Returns:
        VideoUploadError with cleanup details
    """
    handler = get_video_upload_error_handler()
    if not handler.redis_client:
        await handler.initialize()
    
    return await handler.handle_upload_error(
        error=error,
        error_code=error_code,
        video_id=video_id,
        session_id=session_id,
        s3_key=s3_key,
        user_id=user_id,
        additional_context=additional_context
    )


async def validate_upload_session_redis(
    session_id: UUID,
    user_id: UUID
) -> Dict[str, Any]:
    """
    Convenience function to validate upload session.
    
    Args:
        session_id: Upload session ID
        user_id: User ID claiming ownership
        
    Returns:
        Dictionary with validation results
    """
    utils = get_video_upload_redis_utils()
    if not utils.redis_client:
        await utils.initialize()
    
    return await utils.validate_upload_session(session_id, user_id)


# Export main classes and convenience functions
__all__ = [
    'VideoUploadErrorHandler',
    'VideoUploadRedisUtils',
    'get_video_upload_error_handler',
    'get_video_upload_redis_utils',
    'handle_video_upload_error',
    'validate_upload_session_redis'
]
