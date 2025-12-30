# S3 Storage Manager for SecureAI Guardian
# Handles file uploads, downloads, and management in AWS S3

import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime, timedelta
import logging
from typing import Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class S3Manager:
    """Manages S3 storage operations"""
    
    def __init__(self):
        self.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        self.uploads_bucket = os.getenv('S3_BUCKET_NAME', 'secureai-deepfake-videos')
        self.results_bucket = os.getenv('S3_RESULTS_BUCKET_NAME', 'secureai-deepfake-results')
        
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            logger.warning("AWS credentials not configured. S3 operations will fail.")
            self.s3_client = None
        else:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    region_name=self.aws_region
                )
                # Test connection
                self.s3_client.head_bucket(Bucket=self.uploads_bucket)
                logger.info(f"✅ S3 connection established. Bucket: {self.uploads_bucket}")
            except (ClientError, NoCredentialsError) as e:
                logger.error(f"❌ S3 connection failed: {e}")
                self.s3_client = None
    
    def is_available(self) -> bool:
        """Check if S3 is available and configured"""
        return self.s3_client is not None
    
    def upload_file(self, file_path: str, s3_key: str, bucket: Optional[str] = None) -> bool:
        """
        Upload a file to S3
        
        Args:
            file_path: Local file path
            s3_key: S3 object key
            bucket: Bucket name (defaults to uploads_bucket)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.error("S3 not available")
            return False
        
        bucket = bucket or self.uploads_bucket
        
        try:
            self.s3_client.upload_file(
                file_path,
                bucket,
                s3_key,
                ExtraArgs={
                    'ServerSideEncryption': 'AES256',
                    'StorageClass': 'STANDARD_IA'  # Infrequent Access for cost savings
                }
            )
            logger.info(f"✅ Uploaded {s3_key} to {bucket}")
            return True
        except ClientError as e:
            logger.error(f"❌ Failed to upload {s3_key}: {e}")
            return False
    
    def download_file(self, s3_key: str, local_path: str, bucket: Optional[str] = None) -> bool:
        """
        Download a file from S3
        
        Args:
            s3_key: S3 object key
            local_path: Local file path to save to
            bucket: Bucket name (defaults to uploads_bucket)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.error("S3 not available")
            return False
        
        bucket = bucket or self.uploads_bucket
        
        try:
            self.s3_client.download_file(bucket, s3_key, local_path)
            logger.info(f"✅ Downloaded {s3_key} from {bucket}")
            return True
        except ClientError as e:
            logger.error(f"❌ Failed to download {s3_key}: {e}")
            return False
    
    def generate_presigned_url(self, s3_key: str, expiration: int = 3600, 
                               bucket: Optional[str] = None) -> Optional[str]:
        """
        Generate a presigned URL for temporary access
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
            bucket: Bucket name (defaults to uploads_bucket)
        
        Returns:
            Presigned URL or None if failed
        """
        if not self.is_available():
            logger.error("S3 not available")
            return None
        
        bucket = bucket or self.uploads_bucket
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"❌ Failed to generate presigned URL for {s3_key}: {e}")
            return None
    
    def delete_file(self, s3_key: str, bucket: Optional[str] = None) -> bool:
        """
        Delete a file from S3
        
        Args:
            s3_key: S3 object key
            bucket: Bucket name (defaults to uploads_bucket)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.error("S3 not available")
            return False
        
        bucket = bucket or self.uploads_bucket
        
        try:
            self.s3_client.delete_object(Bucket=bucket, Key=s3_key)
            logger.info(f"✅ Deleted {s3_key} from {bucket}")
            return True
        except ClientError as e:
            logger.error(f"❌ Failed to delete {s3_key}: {e}")
            return False
    
    def list_files(self, prefix: str = '', bucket: Optional[str] = None) -> list:
        """
        List files in S3 bucket with prefix
        
        Args:
            prefix: Key prefix to filter
            bucket: Bucket name (defaults to uploads_bucket)
        
        Returns:
            List of S3 keys
        """
        if not self.is_available():
            logger.error("S3 not available")
            return []
        
        bucket = bucket or self.uploads_bucket
        
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            return []
        except ClientError as e:
            logger.error(f"❌ Failed to list files: {e}")
            return []
    
    def get_file_size(self, s3_key: str, bucket: Optional[str] = None) -> Optional[int]:
        """
        Get file size from S3
        
        Args:
            s3_key: S3 object key
            bucket: Bucket name (defaults to uploads_bucket)
        
        Returns:
            File size in bytes or None if failed
        """
        if not self.is_available():
            logger.error("S3 not available")
            return None
        
        bucket = bucket or self.uploads_bucket
        
        try:
            response = self.s3_client.head_object(Bucket=bucket, Key=s3_key)
            return response.get('ContentLength')
        except ClientError as e:
            logger.error(f"❌ Failed to get file size for {s3_key}: {e}")
            return None


# Global instance
s3_manager = S3Manager()

