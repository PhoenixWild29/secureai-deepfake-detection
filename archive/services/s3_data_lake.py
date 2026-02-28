#!/usr/bin/env python3
"""
S3 Data Lake Integration
Service for loading training data from S3 data lake with validation and preprocessing
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import json

logger = logging.getLogger(__name__)


class S3DataLakeClient:
    """
    S3 Data Lake client for training data management.
    Handles data loading, validation, and preprocessing for model training.
    """
    
    def __init__(
        self,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = 'us-east-1',
        bucket_name: Optional[str] = None
    ):
        """
        Initialize S3 data lake client.
        
        Args:
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            region_name: AWS region name
            bucket_name: Default S3 bucket name
        """
        self.aws_access_key_id = aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = aws_secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
        self.region_name = region_name or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        self.bucket_name = bucket_name or os.getenv('S3_DATA_LAKE_BUCKET')
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name
            )
            logger.info(f"S3 client initialized for region: {self.region_name}")
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        except Exception as e:
            logger.error(f"Error initializing S3 client: {str(e)}")
            raise
    
    def parse_s3_path(self, s3_path: str) -> Tuple[str, str]:
        """
        Parse S3 path into bucket and key.
        
        Args:
            s3_path: S3 URI (s3://bucket/key)
            
        Returns:
            Tuple of (bucket, key)
        """
        if not s3_path.startswith('s3://'):
            raise ValueError(f"Invalid S3 path: {s3_path}")
        
        path_parts = s3_path[5:].split('/', 1)
        bucket = path_parts[0]
        key = path_parts[1] if len(path_parts) > 1 else ''
        
        return bucket, key
    
    def validate_dataset_path(self, dataset_path: str) -> bool:
        """
        Validate that dataset path exists and is accessible.
        
        Args:
            dataset_path: S3 dataset path
            
        Returns:
            True if accessible, False otherwise
        """
        try:
            bucket, key = self.parse_s3_path(dataset_path)
            
            # Check if path exists
            response = self.s3_client.head_object(Bucket=bucket, Key=key)
            
            # Check if it's a directory (ends with /) or a file
            if key.endswith('/'):
                # List objects with prefix to check if directory has content
                response = self.s3_client.list_objects_v2(
                    Bucket=bucket,
                    Prefix=key,
                    MaxKeys=1
                )
                return 'Contents' in response
            else:
                # File exists
                return True
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.warning(f"Dataset path not found: {dataset_path}")
                return False
            else:
                logger.error(f"Error validating dataset path: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"Error validating dataset path: {str(e)}")
            return False
    
    def get_dataset_info(self, dataset_path: str) -> Dict[str, Any]:
        """
        Get dataset information and metadata.
        
        Args:
            dataset_path: S3 dataset path
            
        Returns:
            Dataset information dictionary
        """
        try:
            bucket, key = self.parse_s3_path(dataset_path)
            
            if key.endswith('/'):
                # Directory - get summary information
                response = self.s3_client.list_objects_v2(
                    Bucket=bucket,
                    Prefix=key
                )
                
                files = response.get('Contents', [])
                total_size = sum(file['Size'] for file in files)
                file_count = len(files)
                
                return {
                    'type': 'directory',
                    'path': dataset_path,
                    'file_count': file_count,
                    'total_size_bytes': total_size,
                    'total_size_mb': total_size / (1024 * 1024),
                    'files': [file['Key'] for file in files[:10]],  # First 10 files
                    'last_modified': max(file['LastModified'] for file in files) if files else None
                }
            else:
                # Single file
                response = self.s3_client.head_object(Bucket=bucket, Key=key)
                
                return {
                    'type': 'file',
                    'path': dataset_path,
                    'file_count': 1,
                    'total_size_bytes': response['ContentLength'],
                    'total_size_mb': response['ContentLength'] / (1024 * 1024),
                    'last_modified': response['LastModified'],
                    'content_type': response.get('ContentType', 'unknown')
                }
                
        except Exception as e:
            logger.error(f"Error getting dataset info: {str(e)}")
            return {}
    
    def download_dataset(
        self,
        dataset_path: str,
        local_path: Optional[str] = None,
        max_size_mb: int = 1000
    ) -> str:
        """
        Download dataset from S3 to local storage.
        
        Args:
            dataset_path: S3 dataset path
            local_path: Local download path (if None, uses temp directory)
            max_size_mb: Maximum dataset size in MB
            
        Returns:
            Local path to downloaded dataset
        """
        try:
            bucket, key = self.parse_s3_path(dataset_path)
            
            # Get dataset info to check size
            dataset_info = self.get_dataset_info(dataset_path)
            if dataset_info.get('total_size_mb', 0) > max_size_mb:
                raise ValueError(f"Dataset size ({dataset_info['total_size_mb']:.1f}MB) exceeds maximum ({max_size_mb}MB)")
            
            # Set up local path
            if local_path is None:
                temp_dir = tempfile.mkdtemp(prefix='s3_dataset_')
                local_path = os.path.join(temp_dir, os.path.basename(key))
            
            # Create local directory if needed
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            if key.endswith('/'):
                # Download directory
                self._download_directory(bucket, key, local_path)
            else:
                # Download single file
                self.s3_client.download_file(bucket, key, local_path)
            
            logger.info(f"Downloaded dataset from {dataset_path} to {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Error downloading dataset: {str(e)}")
            raise
    
    def _download_directory(self, bucket: str, prefix: str, local_dir: str):
        """
        Download entire directory from S3.
        
        Args:
            bucket: S3 bucket name
            prefix: S3 key prefix
            local_dir: Local directory path
        """
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                key = obj['Key']
                local_file_path = os.path.join(local_dir, key[len(prefix):])
                
                # Create subdirectories if needed
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                
                # Download file
                self.s3_client.download_file(bucket, key, local_file_path)
    
    def load_training_data(
        self,
        dataset_path: str,
        data_format: str = 'auto',
        sample_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Load training data from S3 dataset.
        
        Args:
            dataset_path: S3 dataset path
            data_format: Data format (csv, json, parquet, auto)
            sample_size: Sample size for large datasets
            
        Returns:
            Training data dictionary
        """
        try:
            # Download dataset locally
            local_path = self.download_dataset(dataset_path)
            
            # Determine data format
            if data_format == 'auto':
                data_format = self._detect_data_format(local_path)
            
            # Load data based on format
            if data_format == 'csv':
                data = pd.read_csv(local_path)
            elif data_format == 'json':
                data = pd.read_json(local_path)
            elif data_format == 'parquet':
                data = pd.read_parquet(local_path)
            else:
                raise ValueError(f"Unsupported data format: {data_format}")
            
            # Sample data if requested
            if sample_size and len(data) > sample_size:
                data = data.sample(n=sample_size, random_state=42)
                logger.info(f"Sampled {sample_size} rows from dataset")
            
            # Clean up local files
            if os.path.exists(local_path):
                if os.path.isfile(local_path):
                    os.remove(local_path)
                else:
                    import shutil
                    shutil.rmtree(local_path)
            
            return {
                'data': data,
                'format': data_format,
                'rows': len(data),
                'columns': list(data.columns),
                'data_types': data.dtypes.to_dict(),
                'memory_usage_mb': data.memory_usage(deep=True).sum() / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"Error loading training data: {str(e)}")
            raise
    
    def _detect_data_format(self, file_path: str) -> str:
        """
        Detect data format from file extension.
        
        Args:
            file_path: Local file path
            
        Returns:
            Detected format
        """
        extension = Path(file_path).suffix.lower()
        
        if extension == '.csv':
            return 'csv'
        elif extension == '.json':
            return 'json'
        elif extension in ['.parquet', '.pq']:
            return 'parquet'
        else:
            # Try to detect from content
            try:
                with open(file_path, 'r') as f:
                    first_line = f.readline().strip()
                    if ',' in first_line:
                        return 'csv'
                    elif first_line.startswith('{') or first_line.startswith('['):
                        return 'json'
            except:
                pass
            
            return 'csv'  # Default fallback
    
    def validate_training_data(
        self,
        data: pd.DataFrame,
        required_columns: Optional[List[str]] = None,
        min_rows: int = 100
    ) -> Dict[str, Any]:
        """
        Validate training data quality and structure.
        
        Args:
            data: Training data DataFrame
            required_columns: Required column names
            min_rows: Minimum number of rows required
            
        Returns:
            Validation results dictionary
        """
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'statistics': {}
        }
        
        try:
            # Check minimum rows
            if len(data) < min_rows:
                validation_results['errors'].append(f"Dataset has {len(data)} rows, minimum required: {min_rows}")
                validation_results['is_valid'] = False
            
            # Check required columns
            if required_columns:
                missing_columns = set(required_columns) - set(data.columns)
                if missing_columns:
                    validation_results['errors'].append(f"Missing required columns: {missing_columns}")
                    validation_results['is_valid'] = False
            
            # Check for null values
            null_counts = data.isnull().sum()
            high_null_columns = null_counts[null_counts > len(data) * 0.5].index.tolist()
            if high_null_columns:
                validation_results['warnings'].append(f"Columns with >50% null values: {high_null_columns}")
            
            # Check for duplicate rows
            duplicate_count = data.duplicated().sum()
            if duplicate_count > 0:
                validation_results['warnings'].append(f"Found {duplicate_count} duplicate rows")
            
            # Generate statistics
            validation_results['statistics'] = {
                'total_rows': len(data),
                'total_columns': len(data.columns),
                'null_counts': null_counts.to_dict(),
                'duplicate_rows': duplicate_count,
                'memory_usage_mb': data.memory_usage(deep=True).sum() / (1024 * 1024),
                'data_types': data.dtypes.to_dict()
            }
            
            logger.info(f"Data validation completed: {'Valid' if validation_results['is_valid'] else 'Invalid'}")
            
        except Exception as e:
            logger.error(f"Error validating training data: {str(e)}")
            validation_results['errors'].append(f"Validation error: {str(e)}")
            validation_results['is_valid'] = False
        
        return validation_results
    
    def upload_model_artifact(
        self,
        local_file_path: str,
        s3_path: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload model artifact to S3.
        
        Args:
            local_file_path: Local file path
            s3_path: S3 destination path
            metadata: File metadata
            
        Returns:
            S3 path of uploaded file
        """
        try:
            bucket, key = self.parse_s3_path(s3_path)
            
            # Upload file with metadata
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.upload_file(local_file_path, bucket, key, ExtraArgs=extra_args)
            
            logger.info(f"Uploaded model artifact to {s3_path}")
            return s3_path
            
        except Exception as e:
            logger.error(f"Error uploading model artifact: {str(e)}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check S3 data lake health.
        
        Returns:
            Health status information
        """
        try:
            # Test S3 connection
            if self.bucket_name:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                bucket_status = 'accessible'
            else:
                bucket_status = 'not_configured'
            
            return {
                'status': 'healthy',
                'region': self.region_name,
                'bucket_status': bucket_status,
                'bucket_name': self.bucket_name,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'region': self.region_name,
                'bucket_name': self.bucket_name,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }


# Global S3 data lake client instance
s3_data_lake = S3DataLakeClient()


# Utility functions for easy access
def validate_dataset_path(dataset_path: str) -> bool:
    """Validate S3 dataset path."""
    return s3_data_lake.validate_dataset_path(dataset_path)


def load_training_data(dataset_path: str, **kwargs) -> Dict[str, Any]:
    """Load training data from S3."""
    return s3_data_lake.load_training_data(dataset_path, **kwargs)


def get_dataset_info(dataset_path: str) -> Dict[str, Any]:
    """Get dataset information."""
    return s3_data_lake.get_dataset_info(dataset_path)


def upload_model_artifact(local_file_path: str, s3_path: str, **kwargs) -> str:
    """Upload model artifact to S3."""
    return s3_data_lake.upload_model_artifact(local_file_path, s3_path, **kwargs)


# Export
__all__ = [
    'S3DataLakeClient',
    's3_data_lake',
    'validate_dataset_path',
    'load_training_data',
    'get_dataset_info',
    'upload_model_artifact'
]
