#!/usr/bin/env python3
"""
S3 Presigned URL Service
Service for generating secure S3 presigned URLs for direct client uploads
"""

import os
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config

from ..errors.api_errors import S3ServiceError, ConfigurationError


class S3PresignedService:
    """
    Service for generating S3 presigned URLs for secure direct uploads.
    Integrates with existing S3 infrastructure and provides secure URL generation.
    """
    
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        region: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None
    ):
        """
        Initialize S3 presigned service.
        
        Args:
            bucket_name: S3 bucket name (defaults to environment variable)
            region: AWS region (defaults to environment variable)
            aws_access_key_id: AWS access key (defaults to environment variable)
            aws_secret_access_key: AWS secret key (defaults to environment variable)
        """
        self.bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME', 'secureai-deepfake-videos')
        self.region = region or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        try:
            # Initialize S3 client
            if aws_access_key_id and aws_secret_access_key:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name=self.region,
                    config=Config(
                        signature_version='s3v4',
                        s3={
                            'addressing_style': 'virtual'
                        }
                    )
                )
            else:
                # Use default credentials (environment, IAM role, etc.)
                self.s3_client = boto3.client(
                    's3',
                    region_name=self.region,
                    config=Config(
                        signature_version='s3v4',
                        s3={
                            'addressing_style': 'virtual'
                        }
                    )
                )
            
            # Test connection
            self._test_connection()
            
        except NoCredentialsError:
            raise ConfigurationError("AWS credentials not found. Please configure AWS credentials.")
        except Exception as e:
            raise ConfigurationError(f"S3 client initialization failed: {str(e)}")
    
    def _test_connection(self) -> bool:
        """Test S3 connection and bucket access."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise ConfigurationError(f"S3 bucket '{self.bucket_name}' not found")
            elif error_code == '403':
                raise ConfigurationError(f"Access denied to S3 bucket '{self.bucket_name}'")
            else:
                raise ConfigurationError(f"S3 connection test failed: {str(e)}")
        except Exception as e:
            raise ConfigurationError(f"S3 connection test failed: {str(e)}")
    
    def generate_s3_key(
        self,
        filename: str,
        user_id: Optional[str] = None,
        prefix: str = "uploads"
    ) -> str:
        """
        Generate a secure, unique S3 key for file upload.
        
        Args:
            filename: Original filename
            user_id: Optional user ID for organization
            prefix: S3 key prefix (default: "uploads")
            
        Returns:
            Unique S3 key
        """
        # Generate unique identifier
        unique_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        
        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)
        
        # Create hash of original filename for additional uniqueness
        filename_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
        
        # Build S3 key
        if user_id:
            s3_key = f"{prefix}/{user_id}/{timestamp}/{unique_id}_{filename_hash}_{safe_filename}"
        else:
            s3_key = f"{prefix}/{timestamp}/{unique_id}_{filename_hash}_{safe_filename}"
        
        return s3_key
    
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
    
    def generate_presigned_url(
        self,
        s3_key: str,
        content_type: str,
        file_size: int,
        expires_in: int = 3600,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Generate presigned URL for PUT operation.
        
        Args:
            s3_key: S3 object key
            content_type: File content type
            file_size: File size in bytes
            expires_in: URL expiration time in seconds (default: 1 hour)
            user_id: Optional user ID for metadata
            metadata: Optional additional metadata
            
        Returns:
            Dictionary with presigned URL and upload details
        """
        try:
            # Prepare metadata
            upload_metadata = {
                'upload-date': datetime.utcnow().isoformat(),
                'file-size': str(file_size),
                'content-type': content_type
            }
            
            if user_id:
                upload_metadata['user-id'] = user_id
            
            if metadata:
                upload_metadata.update(metadata)
            
            # Prepare presigned URL parameters
            presigned_params = {
                'Bucket': self.bucket_name,
                'Key': s3_key,
                'ContentType': content_type,
                'Metadata': upload_metadata,
                'ServerSideEncryption': 'AES256'
            }
            
            # Add content length constraint if file size is specified
            if file_size > 0:
                presigned_params['ContentLength'] = file_size
            
            # Generate presigned URL
            presigned_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params=presigned_params,
                ExpiresIn=expires_in
            )
            
            # Calculate expiration timestamp
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Prepare response
            response = {
                'presigned_url': presigned_url,
                'upload_url': f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}",
                's3_key': s3_key,
                'bucket': self.bucket_name,
                'region': self.region,
                'expires_at': expires_at.isoformat() + 'Z',
                'expires_in': expires_in,
                'required_headers': {
                    'Content-Type': content_type,
                    'Content-Length': str(file_size)
                },
                'metadata': upload_metadata
            }
            
            return response
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            raise S3ServiceError(f"Failed to generate presigned URL ({error_code}): {error_message}")
        except Exception as e:
            raise S3ServiceError(f"Failed to generate presigned URL: {str(e)}")
    
    def generate_presigned_post(
        self,
        s3_key: str,
        content_type: str,
        file_size: int,
        expires_in: int = 3600,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Generate presigned POST for multipart uploads.
        
        Args:
            s3_key: S3 object key
            content_type: File content type
            file_size: File size in bytes
            expires_in: URL expiration time in seconds (default: 1 hour)
            user_id: Optional user ID for metadata
            metadata: Optional additional metadata
            
        Returns:
            Dictionary with presigned POST data
        """
        try:
            # Prepare metadata
            upload_metadata = {
                'upload-date': datetime.utcnow().isoformat(),
                'file-size': str(file_size),
                'content-type': content_type
            }
            
            if user_id:
                upload_metadata['user-id'] = user_id
            
            if metadata:
                upload_metadata.update(metadata)
            
            # Prepare presigned POST conditions
            conditions = [
                {'Content-Type': content_type},
                {'Content-Length': file_size},
                {'x-amz-server-side-encryption': 'AES256'}
            ]
            
            # Add metadata conditions
            for key, value in upload_metadata.items():
                conditions.append({f'x-amz-meta-{key}': value})
            
            # Generate presigned POST
            presigned_post = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=s3_key,
                Fields={
                    'Content-Type': content_type,
                    'Content-Length': file_size,
                    'x-amz-server-side-encryption': 'AES256',
                    **{f'x-amz-meta-{key}': value for key, value in upload_metadata.items()}
                },
                Conditions=conditions,
                ExpiresIn=expires_in
            )
            
            # Calculate expiration timestamp
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Prepare response
            response = {
                'presigned_post': presigned_post,
                'upload_url': f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/",
                's3_key': s3_key,
                'bucket': self.bucket_name,
                'region': self.region,
                'expires_at': expires_at.isoformat() + 'Z',
                'expires_in': expires_in,
                'metadata': upload_metadata
            }
            
            return response
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            raise S3ServiceError(f"Failed to generate presigned POST ({error_code}): {error_message}")
        except Exception as e:
            raise S3ServiceError(f"Failed to generate presigned POST: {str(e)}")
    
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
                's3_url': f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
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
    
    def delete_object(
        self,
        s3_key: str
    ) -> bool:
        """
        Delete an object from S3.
        
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
            return True
        except ClientError:
            return False
        except Exception:
            return False


# Global service instance
_s3_presigned_service: Optional[S3PresignedService] = None


def get_s3_presigned_service() -> S3PresignedService:
    """
    Get or create the global S3 presigned service instance.
    
    Returns:
        S3PresignedService instance
    """
    global _s3_presigned_service
    
    if _s3_presigned_service is None:
        _s3_presigned_service = S3PresignedService()
    
    return _s3_presigned_service


def create_presigned_upload_url(
    filename: str,
    content_type: str,
    file_size: int,
    user_id: Optional[str] = None,
    expires_in: int = 3600,
    metadata: Optional[Dict[str, str]] = None,
    use_post: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to create presigned upload URL.
    
    Args:
        filename: Original filename
        content_type: File content type
        file_size: File size in bytes
        user_id: Optional user ID
        expires_in: URL expiration time in seconds
        metadata: Optional additional metadata
        use_post: Whether to use presigned POST instead of PUT
        
    Returns:
        Dictionary with upload URL details
    """
    service = get_s3_presigned_service()
    
    # Generate S3 key
    s3_key = service.generate_s3_key(filename, user_id)
    
    # Generate presigned URL or POST
    if use_post:
        return service.generate_presigned_post(
            s3_key=s3_key,
            content_type=content_type,
            file_size=file_size,
            expires_in=expires_in,
            user_id=user_id,
            metadata=metadata
        )
    else:
        return service.generate_presigned_url(
            s3_key=s3_key,
            content_type=content_type,
            file_size=file_size,
            expires_in=expires_in,
            user_id=user_id,
            metadata=metadata
        )


# Export main service class and convenience function
__all__ = [
    'S3PresignedService',
    'get_s3_presigned_service',
    'create_presigned_upload_url'
]
