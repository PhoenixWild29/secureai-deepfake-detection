#!/usr/bin/env python3
"""
S3 Upload Helper Utilities
S3 upload helper functions with progress callbacks and automatic cleanup on failures.
"""

import os
import time
import asyncio
from typing import Optional, Callable, Dict, Any
from pathlib import Path
import boto3
from botocore.exceptions import NoCredentialsError, ClientError, BotoCoreError
from fastapi import UploadFile
# Note: aiofiles import is optional - will be handled gracefully if not available
try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

from ..models.upload_models import S3UploadResult, UploadProgress


class S3UploadError(Exception):
    """Custom exception for S3 upload errors"""
    pass


class S3ConfigurationError(Exception):
    """Custom exception for S3 configuration errors"""
    pass


class S3Helper:
    """
    S3 upload helper class with progress callbacks and cleanup functionality.
    Integrates with existing S3 infrastructure patterns.
    """
    
    def __init__(
        self,
        bucket_name: str,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        use_ssl: bool = True
    ):
        """
        Initialize S3 helper with configuration.
        
        Args:
            bucket_name: S3 bucket name
            region_name: AWS region name
            aws_access_key_id: AWS access key ID (optional, can use environment/IAM)
            aws_secret_access_key: AWS secret access key (optional, can use environment/IAM)
            use_ssl: Whether to use SSL for connections
        """
        self.bucket_name = bucket_name
        self.region_name = region_name
        
        # Initialize S3 client
        try:
            if aws_access_key_id and aws_secret_access_key:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name=region_name,
                    use_ssl=use_ssl
                )
            else:
                # Use default credentials (environment, IAM role, etc.)
                self.s3_client = boto3.client(
                    's3',
                    region_name=region_name,
                    use_ssl=use_ssl
                )
            
            # Test connection
            self._test_connection()
            
        except NoCredentialsError:
            raise S3ConfigurationError("AWS credentials not found")
        except Exception as e:
            raise S3ConfigurationError(f"S3 client initialization failed: {str(e)}")
    
    def _test_connection(self) -> bool:
        """Test S3 connection and bucket access"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise S3ConfigurationError(f"S3 bucket '{self.bucket_name}' not found")
            elif error_code == '403':
                raise S3ConfigurationError(f"Access denied to S3 bucket '{self.bucket_name}'")
            else:
                raise S3ConfigurationError(f"S3 connection test failed: {str(e)}")
        except Exception as e:
            raise S3ConfigurationError(f"S3 connection test failed: {str(e)}")
    
    async def upload_file_to_s3(
        self,
        file_path: str,
        s3_key: str,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> S3UploadResult:
        """
        Upload file to S3 with progress tracking.
        
        Args:
            file_path: Path to the file to upload
            s3_key: S3 object key (path in bucket)
            progress_callback: Optional callback function (bytes_uploaded, bytes_total, speed)
            metadata: Optional metadata to attach to the object
            content_type: Optional content type for the object
            
        Returns:
            S3UploadResult with upload status and details
        """
        try:
            if not os.path.exists(file_path):
                return S3UploadResult(
                    success=False,
                    error_message=f"File not found: {file_path}"
                )
            
            file_size = os.path.getsize(file_path)
            start_time = time.time()
            
            # Prepare upload parameters
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            if content_type:
                extra_args['ContentType'] = content_type
            
            # Create progress callback for boto3
            def progress_callback_wrapper(bytes_transferred):
                if progress_callback:
                    elapsed_time = time.time() - start_time
                    speed = bytes_transferred / elapsed_time if elapsed_time > 0 else 0
                    progress_callback(bytes_transferred, file_size, speed)
            
            # Upload file with progress tracking
            if progress_callback:
                extra_args['Callback'] = progress_callback_wrapper
            
            # Perform upload
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            upload_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Generate S3 URL
            s3_url = f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{s3_key}"
            
            return S3UploadResult(
                success=True,
                s3_key=s3_key,
                s3_url=s3_url,
                upload_time_ms=int(upload_time),
                file_size=file_size
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            # Clean up on failure
            await self.cleanup_failed_upload(s3_key)
            
            return S3UploadResult(
                success=False,
                error_message=f"S3 upload failed ({error_code}): {error_message}"
            )
            
        except Exception as e:
            # Clean up on failure
            await self.cleanup_failed_upload(s3_key)
            
            return S3UploadResult(
                success=False,
                error_message=f"Upload failed: {str(e)}"
            )
    
    async def upload_stream_to_s3(
        self,
        file_stream,
        s3_key: str,
        file_size: int,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> S3UploadResult:
        """
        Upload file stream to S3 with progress tracking.
        
        Args:
            file_stream: File stream or UploadFile object
            s3_key: S3 object key (path in bucket)
            file_size: Size of the file in bytes
            progress_callback: Optional callback function (bytes_uploaded, bytes_total, speed)
            metadata: Optional metadata to attach to the object
            content_type: Optional content type for the object
            
        Returns:
            S3UploadResult with upload status and details
        """
        try:
            start_time = time.time()
            
            # Prepare upload parameters
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            if content_type:
                extra_args['ContentType'] = content_type
            
            # Create progress callback for boto3
            def progress_callback_wrapper(bytes_transferred):
                if progress_callback:
                    elapsed_time = time.time() - start_time
                    speed = bytes_transferred / elapsed_time if elapsed_time > 0 else 0
                    progress_callback(bytes_transferred, file_size, speed)
            
            # Upload file stream with progress tracking
            if progress_callback:
                extra_args['Callback'] = progress_callback_wrapper
            
            # Perform upload
            self.s3_client.upload_fileobj(
                file_stream,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            upload_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Generate S3 URL
            s3_url = f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{s3_key}"
            
            return S3UploadResult(
                success=True,
                s3_key=s3_key,
                s3_url=s3_url,
                upload_time_ms=int(upload_time),
                file_size=file_size
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            # Clean up on failure
            await self.cleanup_failed_upload(s3_key)
            
            return S3UploadResult(
                success=False,
                error_message=f"S3 upload failed ({error_code}): {error_message}"
            )
            
        except Exception as e:
            # Clean up on failure
            await self.cleanup_failed_upload(s3_key)
            
            return S3UploadResult(
                success=False,
                error_message=f"Upload failed: {str(e)}"
            )
    
    async def upload_file_with_progress(
        self,
        file_path: str,
        s3_key: str,
        progress: UploadProgress,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> S3UploadResult:
        """
        Upload file to S3 with UploadProgress tracking.
        
        Args:
            file_path: Path to the file to upload
            s3_key: S3 object key (path in bucket)
            progress: UploadProgress object to update
            metadata: Optional metadata to attach to the object
            content_type: Optional content type for the object
            
        Returns:
            S3UploadResult with upload status and details
        """
        def progress_callback(bytes_transferred, total_bytes, speed):
            progress.update_progress(bytes_transferred, speed)
        
        result = await self.upload_file_to_s3(
            file_path=file_path,
            s3_key=s3_key,
            progress_callback=progress_callback,
            metadata=metadata,
            content_type=content_type
        )
        
        if result.success:
            progress.mark_completed()
        else:
            progress.mark_failed(result.error_message or "Upload failed")
        
        return result
    
    async def upload_stream_with_progress(
        self,
        file_stream,
        s3_key: str,
        file_size: int,
        progress: UploadProgress,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> S3UploadResult:
        """
        Upload file stream to S3 with UploadProgress tracking.
        
        Args:
            file_stream: File stream or UploadFile object
            s3_key: S3 object key (path in bucket)
            file_size: Size of the file in bytes
            progress: UploadProgress object to update
            metadata: Optional metadata to attach to the object
            content_type: Optional content type for the object
            
        Returns:
            S3UploadResult with upload status and details
        """
        def progress_callback(bytes_transferred, total_bytes, speed):
            progress.update_progress(bytes_transferred, speed)
        
        result = await self.upload_stream_to_s3(
            file_stream=file_stream,
            s3_key=s3_key,
            file_size=file_size,
            progress_callback=progress_callback,
            metadata=metadata,
            content_type=content_type
        )
        
        if result.success:
            progress.mark_completed()
        else:
            progress.mark_failed(result.error_message or "Upload failed")
        
        return result
    
    async def cleanup_failed_upload(self, s3_key: str) -> bool:
        """
        Clean up failed upload artifacts.
        
        Args:
            s3_key: S3 object key to clean up
            
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            # Try to delete the object if it was partially uploaded
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            # Object might not exist, which is fine
            return True
        except Exception:
            return False
    
    async def cleanup_local_file(self, file_path: str) -> bool:
        """
        Clean up local temporary files.
        
        Args:
            file_path: Path to the local file to clean up
            
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except Exception:
            return False
    
    async def download_file_from_s3(
        self,
        s3_key: str,
        local_path: str,
        progress_callback: Optional[Callable[[int, int, float], None]] = None
    ) -> bool:
        """
        Download file from S3 with progress tracking.
        
        Args:
            s3_key: S3 object key to download
            local_path: Local path to save the file
            progress_callback: Optional callback function (bytes_downloaded, bytes_total, speed)
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            # Get object metadata first
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            file_size = response['ContentLength']
            
            start_time = time.time()
            
            # Create progress callback for boto3
            def progress_callback_wrapper(bytes_transferred):
                if progress_callback:
                    elapsed_time = time.time() - start_time
                    speed = bytes_transferred / elapsed_time if elapsed_time > 0 else 0
                    progress_callback(bytes_transferred, file_size, speed)
            
            # Download file with progress tracking
            extra_args = {}
            if progress_callback:
                extra_args['Callback'] = progress_callback_wrapper
            
            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                local_path,
                ExtraArgs=extra_args
            )
            
            return True
            
        except ClientError as e:
            print(f"S3 download failed: {e}")
            return False
        except Exception as e:
            print(f"Download failed: {e}")
            return False
    
    def get_s3_url(self, s3_key: str, expires_in: int = 3600) -> Optional[str]:
        """
        Generate presigned URL for S3 object.
        
        Args:
            s3_key: S3 object key
            expires_in: URL expiration time in seconds
            
        Returns:
            Presigned URL or None if failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            print(f"Failed to generate presigned URL: {e}")
            return None
    
    def object_exists(self, s3_key: str) -> bool:
        """
        Check if S3 object exists.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False
        except Exception:
            return False
    
    def get_object_size(self, s3_key: str) -> Optional[int]:
        """
        Get S3 object size.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Object size in bytes or None if not found
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return response['ContentLength']
        except ClientError:
            return None
        except Exception:
            return None
    
    def list_objects(self, prefix: str = "", max_keys: int = 1000) -> list:
        """
        List objects in S3 bucket.
        
        Args:
            prefix: Object key prefix to filter
            max_keys: Maximum number of keys to return
            
        Returns:
            List of object keys
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            else:
                return []
                
        except Exception as e:
            print(f"Failed to list objects: {e}")
            return []


# Convenience functions for backward compatibility with existing code
async def upload_file_to_s3(
    file_path: str,
    bucket: str,
    s3_key: str,
    progress_callback: Optional[Callable[[int, int, float], None]] = None,
    region_name: str = "us-east-1"
) -> S3UploadResult:
    """
    Upload file to S3 with progress tracking (convenience function).
    
    Args:
        file_path: Path to the file to upload
        bucket: S3 bucket name
        s3_key: S3 object key (path in bucket)
        progress_callback: Optional callback function (bytes_uploaded, bytes_total, speed)
        region_name: AWS region name
        
    Returns:
        S3UploadResult with upload status and details
    """
    try:
        s3_helper = S3Helper(bucket_name=bucket, region_name=region_name)
        return await s3_helper.upload_file_to_s3(
            file_path=file_path,
            s3_key=s3_key,
            progress_callback=progress_callback
        )
    except Exception as e:
        return S3UploadResult(
            success=False,
            error_message=f"S3 helper initialization failed: {str(e)}"
        )


async def upload_stream_to_s3(
    file_stream,
    bucket: str,
    s3_key: str,
    file_size: int,
    progress_callback: Optional[Callable[[int, int, float], None]] = None,
    region_name: str = "us-east-1"
) -> S3UploadResult:
    """
    Upload file stream to S3 with progress tracking (convenience function).
    
    Args:
        file_stream: File stream or UploadFile object
        bucket: S3 bucket name
        s3_key: S3 object key (path in bucket)
        file_size: Size of the file in bytes
        progress_callback: Optional callback function (bytes_uploaded, bytes_total, speed)
        region_name: AWS region name
        
    Returns:
        S3UploadResult with upload status and details
    """
    try:
        s3_helper = S3Helper(bucket_name=bucket, region_name=region_name)
        return await s3_helper.upload_stream_to_s3(
            file_stream=file_stream,
            s3_key=s3_key,
            file_size=file_size,
            progress_callback=progress_callback
        )
    except Exception as e:
        return S3UploadResult(
            success=False,
            error_message=f"S3 helper initialization failed: {str(e)}"
        )


def cleanup_failed_upload(s3_key: str, bucket: str, region_name: str = "us-east-1") -> bool:
    """
    Clean up failed upload artifacts (convenience function).
    
    Args:
        s3_key: S3 object key to clean up
        bucket: S3 bucket name
        region_name: AWS region name
        
    Returns:
        True if cleanup successful, False otherwise
    """
    try:
        s3_helper = S3Helper(bucket_name=bucket, region_name=region_name)
        return asyncio.run(s3_helper.cleanup_failed_upload(s3_key))
    except Exception:
        return False


def cleanup_local_file(file_path: str) -> bool:
    """
    Clean up local temporary files (convenience function).
    
    Args:
        file_path: Path to the local file to clean up
        
    Returns:
        True if cleanup successful, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        return True
    except Exception:
        return False
