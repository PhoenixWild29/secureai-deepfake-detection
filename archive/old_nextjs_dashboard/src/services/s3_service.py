#!/usr/bin/env python3
"""
Enhanced S3 Service for Dashboard Video Uploads
Service for handling video file uploads with dashboard-specific features and cleanup
"""

import os
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from uuid import UUID
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config

from src.services.s3_presigned_service import S3PresignedService, S3ServiceError
from src.schemas.video_upload_schema import VideoUploadConfig, VideoUploadErrorCodes

logger = logging.getLogger(__name__)


class DashboardS3Service:
    """
    Enhanced S3 service specifically for dashboard video uploads.
    Provides dashboard-specific key prefixes, cleanup operations, and error handling.
    """
    
    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initialize dashboard S3 service.
        
        Args:
            bucket_name: S3 bucket name (defaults to environment variable)
        """
        self.bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME', 'secureai-deepfake-videos')
        self.key_prefix = VideoUploadConfig.S3_KEY_PREFIX
        
        # Initialize base S3 service
        self.s3_service = S3PresignedService(bucket_name=self.bucket_name)
        
        # Initialize S3 client for direct operations
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
                config=Config(
                    signature_version='s3v4',
                    s3={'addressing_style': 'virtual'}
                )
            )
        except NoCredentialsError:
            raise S3ServiceError("AWS credentials not found")
        except Exception as e:
            raise S3ServiceError(f"S3 client initialization failed: {str(e)}")
    
    def generate_dashboard_s3_key(
        self,
        filename: str,
        user_id: UUID,
        session_id: Optional[UUID] = None
    ) -> str:
        """
        Generate S3 key for dashboard uploads with user-specific prefix.
        
        Args:
            filename: Original filename
            user_id: User ID for organization
            session_id: Optional upload session ID
            
        Returns:
            S3 key with dashboard-uploads/{user_id} prefix
        """
        # Generate unique identifier
        unique_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        
        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)
        
        # Create hash of original filename for additional uniqueness
        filename_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
        
        # Build dashboard-specific S3 key
        s3_key = f"{self.key_prefix}/{user_id}/{timestamp}/{unique_id}_{filename_hash}_{safe_filename}"
        
        # Add session ID to key if provided
        if session_id:
            s3_key = f"{self.key_prefix}/{user_id}/{session_id}/{timestamp}/{unique_id}_{filename_hash}_{safe_filename}"
        
        return s3_key
    
    def upload_video_file(
        self,
        file_content: bytes,
        filename: str,
        user_id: UUID,
        content_type: str,
        session_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload video file to S3 with dashboard-specific key structure.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            user_id: User ID
            content_type: File content type
            session_id: Optional upload session ID
            metadata: Optional additional metadata
            
        Returns:
            Dictionary with upload results
            
        Raises:
            S3ServiceError: If upload fails
        """
        try:
            # Generate S3 key
            s3_key = self.generate_dashboard_s3_key(filename, user_id, session_id)
            
            # Prepare metadata
            upload_metadata = {
                'upload-date': datetime.now(timezone.utc).isoformat(),
                'file-size': str(len(file_content)),
                'content-type': content_type,
                'user-id': str(user_id),
                'filename': filename
            }
            
            if session_id:
                upload_metadata['session-id'] = str(session_id)
            
            if metadata:
                upload_metadata.update(metadata)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata=upload_metadata,
                ServerSideEncryption='AES256'
            )
            
            # Generate public URL
            s3_url = f"https://{self.bucket_name}.s3.{os.getenv('AWS_DEFAULT_REGION', 'us-east-1')}.amazonaws.com/{s3_key}"
            
            logger.info(f"Successfully uploaded video to S3: {s3_key}")
            
            return {
                'success': True,
                's3_key': s3_key,
                's3_url': s3_url,
                'bucket': self.bucket_name,
                'file_size': len(file_content),
                'metadata': upload_metadata
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"S3 upload failed ({error_code}): {error_message}")
            raise S3ServiceError(f"S3 upload failed ({error_code}): {error_message}")
        except Exception as e:
            logger.error(f"S3 upload failed: {str(e)}")
            raise S3ServiceError(f"S3 upload failed: {str(e)}")
    
    def verify_upload(
        self,
        s3_key: str
    ) -> Dict[str, Any]:
        """
        Verify that a file was successfully uploaded to S3.
        
        Args:
            s3_key: S3 object key to verify
            
        Returns:
            Dictionary with verification details
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            return {
                'exists': True,
                'size': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag'),
                'content_type': response.get('ContentType'),
                'metadata': response.get('Metadata', {}),
                's3_url': f"https://{self.bucket_name}.s3.{os.getenv('AWS_DEFAULT_REGION', 'us-east-1')}.amazonaws.com/{s3_key}"
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return {
                    'exists': False,
                    'error': 'Object not found'
                }
            else:
                raise S3ServiceError(f"Failed to verify upload: {str(e)}")
        except Exception as e:
            raise S3ServiceError(f"Failed to verify upload: {str(e)}")
    
    def delete_video_file(
        self,
        s3_key: str
    ) -> bool:
        """
        Delete a video file from S3.
        
        Args:
            s3_key: S3 object key to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            logger.info(f"Successfully deleted video from S3: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete video from S3: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete video from S3: {str(e)}")
            return False
    
    def cleanup_failed_upload(
        self,
        s3_key: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Clean up S3 files after a failed upload operation.
        
        Args:
            s3_key: S3 object key to clean up
            error_details: Optional error details for logging
            
        Returns:
            Dictionary with cleanup results
        """
        cleanup_result = {
            's3_key': s3_key,
            'cleanup_attempted': False,
            'cleanup_successful': False,
            'error': None
        }
        
        try:
            # Attempt to delete the file
            cleanup_result['cleanup_attempted'] = True
            cleanup_result['cleanup_successful'] = self.delete_video_file(s3_key)
            
            if cleanup_result['cleanup_successful']:
                logger.info(f"Successfully cleaned up failed upload: {s3_key}")
            else:
                logger.warning(f"Failed to clean up S3 file: {s3_key}")
                cleanup_result['error'] = "Failed to delete S3 file"
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            cleanup_result['error'] = str(e)
        
        return cleanup_result
    
    def get_user_upload_stats(
        self,
        user_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get upload statistics for a user.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            Dictionary with upload statistics
        """
        try:
            # List objects with user prefix
            prefix = f"{self.key_prefix}/{user_id}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            total_size = 0
            file_count = 0
            files = []
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    total_size += obj['Size']
                    file_count += 1
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified']
                    })
            
            return {
                'user_id': str(user_id),
                'total_files': file_count,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'total_size_gb': total_size / (1024 * 1024 * 1024),
                'files': files
            }
            
        except Exception as e:
            logger.error(f"Failed to get user upload stats: {str(e)}")
            return {
                'user_id': str(user_id),
                'error': str(e),
                'total_files': 0,
                'total_size_bytes': 0
            }
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for S3 key.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        import re
        
        # Remove or replace unsafe characters
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        
        # Ensure filename doesn't start with dot
        if safe_filename.startswith('.'):
            safe_filename = 'file_' + safe_filename
        
        # Limit length
        if len(safe_filename) > 100:
            name, ext = os.path.splitext(safe_filename)
            safe_filename = name[:95] + ext
        
        return safe_filename
    
    def generate_presigned_upload_url(
        self,
        filename: str,
        user_id: UUID,
        content_type: str,
        file_size: int,
        session_id: Optional[UUID] = None,
        expires_in: int = 3600,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Generate presigned URL for direct client upload.
        
        Args:
            filename: Original filename
            user_id: User ID
            content_type: File content type
            file_size: File size in bytes
            session_id: Optional upload session ID
            expires_in: URL expiration time in seconds
            metadata: Optional additional metadata
            
        Returns:
            Dictionary with presigned URL details
        """
        # Generate S3 key
        s3_key = self.generate_dashboard_s3_key(filename, user_id, session_id)
        
        # Prepare metadata
        upload_metadata = {
            'upload-date': datetime.now(timezone.utc).isoformat(),
            'file-size': str(file_size),
            'content-type': content_type,
            'user-id': str(user_id),
            'filename': filename
        }
        
        if session_id:
            upload_metadata['session-id'] = str(session_id)
        
        if metadata:
            upload_metadata.update(metadata)
        
        # Generate presigned URL using base service
        return self.s3_service.generate_presigned_url(
            s3_key=s3_key,
            content_type=content_type,
            file_size=file_size,
            expires_in=expires_in,
            user_id=str(user_id),
            metadata=upload_metadata
        )


# Global service instance
_dashboard_s3_service: Optional[DashboardS3Service] = None


def get_dashboard_s3_service() -> DashboardS3Service:
    """
    Get or create the global dashboard S3 service instance.
    
    Returns:
        DashboardS3Service instance
    """
    global _dashboard_s3_service
    
    if _dashboard_s3_service is None:
        _dashboard_s3_service = DashboardS3Service()
    
    return _dashboard_s3_service


def upload_video_to_dashboard_s3(
    file_content: bytes,
    filename: str,
    user_id: UUID,
    content_type: str,
    session_id: Optional[UUID] = None,
    metadata: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Convenience function to upload video to dashboard S3.
    
    Args:
        file_content: File content as bytes
        filename: Original filename
        user_id: User ID
        content_type: File content type
        session_id: Optional upload session ID
        metadata: Optional additional metadata
        
    Returns:
        Dictionary with upload results
    """
    service = get_dashboard_s3_service()
    return service.upload_video_file(
        file_content=file_content,
        filename=filename,
        user_id=user_id,
        content_type=content_type,
        session_id=session_id,
        metadata=metadata
    )


def cleanup_failed_dashboard_upload(
    s3_key: str,
    error_details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function to cleanup failed dashboard upload.
    
    Args:
        s3_key: S3 object key to clean up
        error_details: Optional error details
        
    Returns:
        Dictionary with cleanup results
    """
    service = get_dashboard_s3_service()
    return service.cleanup_failed_upload(s3_key, error_details)


# Export main service class and convenience functions
__all__ = [
    'DashboardS3Service',
    'get_dashboard_s3_service',
    'upload_video_to_dashboard_s3',
    'cleanup_failed_dashboard_upload'
]
