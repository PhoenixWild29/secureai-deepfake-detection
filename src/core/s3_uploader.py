#!/usr/bin/env python3
"""
Enhanced S3 Uploader with Progress Callbacks
S3 upload service with real-time progress tracking and WebSocket broadcasting
"""

import os
import uuid
import hashlib
import logging
import asyncio
from typing import Optional, Dict, Any, Callable, Union
from uuid import UUID
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config

from src.services.s3_service import DashboardS3Service
from src.services.redis_progress_service import get_redis_progress_service
from src.services.websocket_service import get_websocket_progress_service
from src.models.upload_progress import (
    UploadProgress,
    ProgressStatus,
    create_upload_progress
)

logger = logging.getLogger(__name__)


class ProgressCallback:
    """
    Progress callback handler for S3 uploads.
    Provides real-time progress tracking and WebSocket broadcasting.
    """
    
    def __init__(
        self,
        session_id: UUID,
        user_id: UUID,
        total_bytes: int,
        filename: Optional[str] = None,
        content_type: Optional[str] = None
    ):
        """
        Initialize progress callback.
        
        Args:
            session_id: Upload session ID
            user_id: User ID
            total_bytes: Total file size in bytes
            filename: Optional filename
            content_type: Optional content type
        """
        self.session_id = session_id
        self.user_id = user_id
        self.total_bytes = total_bytes
        self.filename = filename
        self.content_type = content_type
        
        # Progress tracking
        self.bytes_uploaded = 0
        self.start_time = datetime.now(timezone.utc)
        self.last_update_time = self.start_time
        self.update_interval = 0.5  # Update every 500ms
        
        # Services
        self.redis_service = None
        self.websocket_service = None
        
        # Upload state
        self.is_completed = False
        self.error_occurred = False
        self.error_message = None
    
    async def initialize_services(self):
        """Initialize Redis and WebSocket services"""
        try:
            self.redis_service = get_redis_progress_service()
            if not self.redis_service.redis_client:
                await self.redis_service.initialize()
            
            self.websocket_service = get_websocket_progress_service()
            
            # Create initial progress record
            progress = create_upload_progress(
                session_id=self.session_id,
                user_id=self.user_id,
                total_bytes=self.total_bytes,
                filename=self.filename,
                content_type=self.content_type
            )
            
            await self.redis_service.store_progress(progress)
            await self.websocket_service.broadcast_progress_update(progress)
            
        except Exception as e:
            logger.error(f"Failed to initialize progress callback services: {e}")
            raise
    
    async def __call__(self, bytes_transferred: int):
        """
        Progress callback function called by boto3 during upload.
        
        Args:
            bytes_transferred: Number of bytes transferred so far
        """
        try:
            if self.error_occurred or self.is_completed:
                return
            
            self.bytes_uploaded = bytes_transferred
            
            # Check if we should update (throttle updates)
            current_time = datetime.now(timezone.utc)
            time_since_last_update = (current_time - self.last_update_time).total_seconds()
            
            if time_since_last_update < self.update_interval and bytes_transferred < self.total_bytes:
                return
            
            # Calculate progress metrics
            percentage = (bytes_transferred / self.total_bytes) * 100 if self.total_bytes > 0 else 0
            elapsed_time = (current_time - self.start_time).total_seconds()
            upload_speed = bytes_transferred / elapsed_time if elapsed_time > 0 else 0
            
            # Update progress in Redis
            if self.redis_service:
                progress = await self.redis_service.update_progress(
                    session_id=self.session_id,
                    bytes_uploaded=bytes_transferred,
                    upload_speed=upload_speed
                )
                
                if progress:
                    # Broadcast progress update via WebSocket
                    if self.websocket_service:
                        await self.websocket_service.broadcast_progress_update(progress)
            
            self.last_update_time = current_time
            
            # Log progress for debugging
            if percentage % 10 == 0:  # Log every 10%
                logger.debug(f"Upload progress for session {self.session_id}: {percentage:.1f}%")
            
        except Exception as e:
            logger.error(f"Error in progress callback for session {self.session_id}: {e}")
            await self.handle_error(f"Progress callback error: {str(e)}")
    
    async def handle_completion(
        self,
        video_id: UUID,
        analysis_id: Optional[UUID] = None,
        redirect_url: str = "/dashboard/videos"
    ):
        """
        Handle upload completion.
        
        Args:
            video_id: Video ID after successful upload
            analysis_id: Optional analysis ID
            redirect_url: Redirect URL
        """
        try:
            if self.is_completed or self.error_occurred:
                return
            
            self.is_completed = True
            
            # Update progress as completed
            if self.redis_service:
                progress = await self.redis_service.complete_progress(
                    session_id=self.session_id,
                    video_id=video_id,
                    analysis_id=analysis_id,
                    redirect_url=redirect_url
                )
                
                if progress:
                    # Broadcast completion event via WebSocket
                    if self.websocket_service:
                        await self.websocket_service.broadcast_upload_complete(
                            progress=progress,
                            video_id=video_id,
                            analysis_id=analysis_id,
                            redirect_url=redirect_url
                        )
            
            logger.info(f"Upload completed for session {self.session_id}")
            
        except Exception as e:
            logger.error(f"Error handling completion for session {self.session_id}: {e}")
            await self.handle_error(f"Completion handling error: {str(e)}")
    
    async def handle_error(self, error_message: str, error_code: str = "UPLOAD_ERROR"):
        """
        Handle upload error.
        
        Args:
            error_message: Error message
            error_code: Error code
        """
        try:
            if self.error_occurred or self.is_completed:
                return
            
            self.error_occurred = True
            self.error_message = error_message
            
            # Update progress as failed
            if self.redis_service:
                progress = await self.redis_service.error_progress(
                    session_id=self.session_id,
                    error_code=error_code,
                    error_message=error_message
                )
                
                if progress:
                    # Broadcast error event via WebSocket
                    if self.websocket_service:
                        await self.websocket_service.broadcast_upload_error(
                            progress=progress,
                            error_code=error_code,
                            error_message=error_message
                        )
            
            logger.error(f"Upload error for session {self.session_id}: {error_message}")
            
        except Exception as e:
            logger.error(f"Error handling error for session {self.session_id}: {e}")


class ProgressS3Uploader:
    """
    Enhanced S3 uploader with progress tracking capabilities.
    Extends DashboardS3Service with real-time progress callbacks.
    """
    
    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initialize progress S3 uploader.
        
        Args:
            bucket_name: S3 bucket name (defaults to environment variable)
        """
        self.s3_service = DashboardS3Service(bucket_name)
        self.redis_service = None
        self.websocket_service = None
    
    async def initialize_services(self):
        """Initialize Redis and WebSocket services"""
        try:
            self.redis_service = get_redis_progress_service()
            if not self.redis_service.redis_client:
                await self.redis_service.initialize()
            
            self.websocket_service = get_websocket_progress_service()
            
        except Exception as e:
            logger.error(f"Failed to initialize S3 uploader services: {e}")
            raise
    
    async def upload_video_with_progress(
        self,
        file_content: bytes,
        filename: str,
        user_id: UUID,
        session_id: UUID,
        content_type: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload video file to S3 with real-time progress tracking.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            user_id: User ID
            session_id: Upload session ID
            content_type: File content type
            metadata: Optional additional metadata
            
        Returns:
            Dictionary with upload results
            
        Raises:
            Exception: If upload fails
        """
        try:
            # Initialize services if not already done
            if not self.redis_service or not self.websocket_service:
                await self.initialize_services()
            
            # Create progress callback
            progress_callback = ProgressCallback(
                session_id=session_id,
                user_id=user_id,
                total_bytes=len(file_content),
                filename=filename,
                content_type=content_type
            )
            
            # Initialize progress tracking
            await progress_callback.initialize_services()
            
            # Generate S3 key
            s3_key = self.s3_service.generate_dashboard_s3_key(filename, user_id, session_id)
            
            # Prepare metadata
            upload_metadata = {
                'upload-date': datetime.now(timezone.utc).isoformat(),
                'file-size': str(len(file_content)),
                'content-type': content_type,
                'user-id': str(user_id),
                'filename': filename,
                'session-id': str(session_id)
            }
            
            if metadata:
                upload_metadata.update(metadata)
            
            # Upload to S3 with progress tracking
            logger.info(f"Starting S3 upload for session {session_id}: {filename}")
            
            # Use boto3 client directly for progress tracking
            s3_client = self.s3_service.s3_client
            
            # Upload with progress callback
            s3_client.put_object(
                Bucket=self.s3_service.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata=upload_metadata,
                ServerSideEncryption='AES256',
                Callback=progress_callback  # This is where progress tracking happens
            )
            
            # Generate public URL
            s3_url = f"https://{self.s3_service.bucket_name}.s3.{os.getenv('AWS_DEFAULT_REGION', 'us-east-1')}.amazonaws.com/{s3_key}"
            
            logger.info(f"Successfully uploaded video to S3: {s3_key}")
            
            # Handle completion
            await progress_callback.handle_completion(
                video_id=uuid.uuid4(),  # This would come from the actual video creation
                redirect_url=f"/dashboard/videos/{session_id}/results"
            )
            
            return {
                'success': True,
                's3_key': s3_key,
                's3_url': s3_url,
                'bucket': self.s3_service.bucket_name,
                'file_size': len(file_content),
                'metadata': upload_metadata,
                'session_id': str(session_id)
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            # Handle error with progress callback
            if 'progress_callback' in locals():
                await progress_callback.handle_error(
                    error_message=f"S3 upload failed ({error_code}): {error_message}",
                    error_code=f"S3_{error_code}"
                )
            
            logger.error(f"S3 upload failed for session {session_id} ({error_code}): {error_message}")
            raise Exception(f"S3 upload failed ({error_code}): {error_message}")
            
        except Exception as e:
            # Handle error with progress callback
            if 'progress_callback' in locals():
                await progress_callback.handle_error(
                    error_message=f"Upload failed: {str(e)}",
                    error_code="UPLOAD_ERROR"
                )
            
            logger.error(f"Upload failed for session {session_id}: {str(e)}")
            raise
    
    async def upload_file_with_progress(
        self,
        file_path: str,
        filename: str,
        user_id: UUID,
        session_id: UUID,
        content_type: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload file from local path to S3 with progress tracking.
        
        Args:
            file_path: Local file path
            filename: Original filename
            user_id: User ID
            session_id: Upload session ID
            content_type: File content type
            metadata: Optional additional metadata
            
        Returns:
            Dictionary with upload results
        """
        try:
            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            return await self.upload_video_with_progress(
                file_content=file_content,
                filename=filename,
                user_id=user_id,
                session_id=session_id,
                content_type=content_type,
                metadata=metadata
            )
            
        except FileNotFoundError:
            error_message = f"File not found: {file_path}"
            logger.error(error_message)
            raise Exception(error_message)
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {str(e)}")
            raise
    
    async def upload_stream_with_progress(
        self,
        file_stream,
        filename: str,
        user_id: UUID,
        session_id: UUID,
        content_type: str,
        file_size: int,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload file stream to S3 with progress tracking.
        
        Args:
            file_stream: File stream object
            filename: Original filename
            user_id: User ID
            session_id: Upload session ID
            content_type: File content type
            file_size: Total file size in bytes
            metadata: Optional additional metadata
            
        Returns:
            Dictionary with upload results
        """
        try:
            # Initialize services if not already done
            if not self.redis_service or not self.websocket_service:
                await self.initialize_services()
            
            # Create progress callback
            progress_callback = ProgressCallback(
                session_id=session_id,
                user_id=user_id,
                total_bytes=file_size,
                filename=filename,
                content_type=content_type
            )
            
            # Initialize progress tracking
            await progress_callback.initialize_services()
            
            # Generate S3 key
            s3_key = self.s3_service.generate_dashboard_s3_key(filename, user_id, session_id)
            
            # Prepare metadata
            upload_metadata = {
                'upload-date': datetime.now(timezone.utc).isoformat(),
                'file-size': str(file_size),
                'content-type': content_type,
                'user-id': str(user_id),
                'filename': filename,
                'session-id': str(session_id)
            }
            
            if metadata:
                upload_metadata.update(metadata)
            
            # Upload stream to S3 with progress tracking
            logger.info(f"Starting S3 stream upload for session {session_id}: {filename}")
            
            s3_client = self.s3_service.s3_client
            
            # Upload stream with progress callback
            s3_client.put_object(
                Bucket=self.s3_service.bucket_name,
                Key=s3_key,
                Body=file_stream,
                ContentType=content_type,
                Metadata=upload_metadata,
                ServerSideEncryption='AES256',
                Callback=progress_callback
            )
            
            # Generate public URL
            s3_url = f"https://{self.s3_service.bucket_name}.s3.{os.getenv('AWS_DEFAULT_REGION', 'us-east-1')}.amazonaws.com/{s3_key}"
            
            logger.info(f"Successfully uploaded stream to S3: {s3_key}")
            
            # Handle completion
            await progress_callback.handle_completion(
                video_id=uuid.uuid4(),  # This would come from the actual video creation
                redirect_url=f"/dashboard/videos/{session_id}/results"
            )
            
            return {
                'success': True,
                's3_key': s3_key,
                's3_url': s3_url,
                'bucket': self.s3_service.bucket_name,
                'file_size': file_size,
                'metadata': upload_metadata,
                'session_id': str(session_id)
            }
            
        except Exception as e:
            # Handle error with progress callback
            if 'progress_callback' in locals():
                await progress_callback.handle_error(
                    error_message=f"Stream upload failed: {str(e)}",
                    error_code="STREAM_UPLOAD_ERROR"
                )
            
            logger.error(f"Stream upload failed for session {session_id}: {str(e)}")
            raise
    
    async def get_upload_progress(self, session_id: UUID) -> Optional[UploadProgress]:
        """
        Get current upload progress for a session.
        
        Args:
            session_id: Upload session ID
            
        Returns:
            Optional[UploadProgress]: Progress data or None if not found
        """
        try:
            if not self.redis_service:
                await self.initialize_services()
            
            return await self.redis_service.get_progress(session_id)
            
        except Exception as e:
            logger.error(f"Failed to get upload progress for session {session_id}: {e}")
            return None
    
    async def cancel_upload(self, session_id: UUID) -> bool:
        """
        Cancel an ongoing upload.
        
        Args:
            session_id: Upload session ID
            
        Returns:
            bool: True if cancellation successful, False otherwise
        """
        try:
            if not self.redis_service:
                await self.initialize_services()
            
            # Get current progress
            progress = await self.redis_service.get_progress(session_id)
            if not progress:
                return False
            
            # Mark as cancelled
            cancelled_progress = progress.copy(update={
                'status': ProgressStatus.CANCELLED,
                'last_updated': datetime.now(timezone.utc).isoformat()
            })
            
            # Store cancelled progress
            success = await self.redis_service.store_progress(cancelled_progress)
            
            if success and self.websocket_service:
                # Broadcast cancellation event
                await self.websocket_service.broadcast_custom_event(
                    event_type="upload_cancelled",
                    session_id=session_id,
                    user_id=progress.user_id,
                    data={
                        'session_id': str(session_id),
                        'status': 'cancelled',
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                )
            
            logger.info(f"Cancelled upload for session {session_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to cancel upload for session {session_id}: {e}")
            return False


# Global service instance
_progress_s3_uploader: Optional[ProgressS3Uploader] = None


def get_progress_s3_uploader() -> ProgressS3Uploader:
    """
    Get or create the global progress S3 uploader instance.
    
    Returns:
        ProgressS3Uploader instance
    """
    global _progress_s3_uploader
    
    if _progress_s3_uploader is None:
        _progress_s3_uploader = ProgressS3Uploader()
    
    return _progress_s3_uploader


# Convenience functions
async def upload_video_with_progress(
    file_content: bytes,
    filename: str,
    user_id: UUID,
    session_id: UUID,
    content_type: str,
    metadata: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Convenience function to upload video with progress tracking.
    
    Args:
        file_content: File content as bytes
        filename: Original filename
        user_id: User ID
        session_id: Upload session ID
        content_type: File content type
        metadata: Optional additional metadata
        
    Returns:
        Dictionary with upload results
    """
    uploader = get_progress_s3_uploader()
    return await uploader.upload_video_with_progress(
        file_content=file_content,
        filename=filename,
        user_id=user_id,
        session_id=session_id,
        content_type=content_type,
        metadata=metadata
    )


async def get_upload_progress_status(session_id: UUID) -> Optional[UploadProgress]:
    """
    Convenience function to get upload progress status.
    
    Args:
        session_id: Upload session ID
        
    Returns:
        Optional[UploadProgress]: Progress data or None if not found
    """
    uploader = get_progress_s3_uploader()
    return await uploader.get_upload_progress(session_id)


# Export main service class and convenience functions
__all__ = [
    'ProgressCallback',
    'ProgressS3Uploader',
    'get_progress_s3_uploader',
    'upload_video_with_progress',
    'get_upload_progress_status'
]
