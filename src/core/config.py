#!/usr/bin/env python3
"""
Upload Session Configuration
Configuration settings for upload session management and Redis integration
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import timedelta


@dataclass
class RedisConfig:
    """Redis configuration for upload sessions"""
    
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    decode_responses: bool = True
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True
    max_connections: int = 20
    health_check_interval: int = 30
    
    @classmethod
    def from_env(cls) -> 'RedisConfig':
        """Create Redis config from environment variables"""
        return cls(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD'),
            socket_timeout=int(os.getenv('REDIS_SOCKET_TIMEOUT', '5')),
            socket_connect_timeout=int(os.getenv('REDIS_SOCKET_CONNECT_TIMEOUT', '5')),
            retry_on_timeout=os.getenv('REDIS_RETRY_ON_TIMEOUT', 'true').lower() == 'true',
            max_connections=int(os.getenv('REDIS_MAX_CONNECTIONS', '20')),
            health_check_interval=int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', '30'))
        )


@dataclass
class UploadSessionConfig:
    """Upload session configuration"""
    
    # File upload limits
    max_file_size_bytes: int = 524288000  # 500MB
    allowed_formats: Optional[list] = None
    
    # Session management
    session_ttl_seconds: int = 3600  # 1 hour
    redis_session_prefix: str = "upload_session"
    
    # Upload URL settings
    upload_url_ttl_seconds: int = 3600  # 1 hour for pre-signed URLs
    
    # Quota settings
    default_quota_limit_bytes: int = 10737418240  # 10GB
    quota_reset_period_days: int = 30
    
    # Dashboard settings
    supported_source_sections: Optional[list] = None
    supported_workflow_types: Optional[list] = None
    
    def __post_init__(self):
        """Initialize default values after dataclass creation"""
        if self.allowed_formats is None:
            self.allowed_formats = ['mp4', 'avi', 'mov', 'mkv', 'webm']
        
        if self.supported_source_sections is None:
            self.supported_source_sections = [
                'video_analysis',
                'batch_upload', 
                'training_data',
                'model_validation',
                'content_verification'
            ]
        
        if self.supported_workflow_types is None:
            self.supported_workflow_types = [
                'single_upload',
                'batch_upload',
                'training_upload',
                'analysis_upload',
                'validation_upload'
            ]
    
    @classmethod
    def from_env(cls) -> 'UploadSessionConfig':
        """Create upload session config from environment variables"""
        return cls(
            max_file_size_bytes=int(os.getenv('UPLOAD_MAX_FILE_SIZE', '524288000')),
            session_ttl_seconds=int(os.getenv('UPLOAD_SESSION_TTL', '3600')),
            upload_url_ttl_seconds=int(os.getenv('UPLOAD_URL_TTL', '3600')),
            default_quota_limit_bytes=int(os.getenv('UPLOAD_DEFAULT_QUOTA', '10737418240')),
            quota_reset_period_days=int(os.getenv('UPLOAD_QUOTA_RESET_DAYS', '30'))
        )
    
    @property
    def max_file_size_mb(self) -> int:
        """Get max file size in MB"""
        return self.max_file_size_bytes // (1024 * 1024)
    
    @property
    def max_file_size_gb(self) -> float:
        """Get max file size in GB"""
        return self.max_file_size_bytes / (1024 * 1024 * 1024)
    
    @property
    def default_quota_limit_gb(self) -> float:
        """Get default quota limit in GB"""
        return self.default_quota_limit_bytes / (1024 * 1024 * 1024)
    
    @property
    def session_ttl_timedelta(self) -> timedelta:
        """Get session TTL as timedelta"""
        return timedelta(seconds=self.session_ttl_seconds)
    
    @property
    def upload_url_ttl_timedelta(self) -> timedelta:
        """Get upload URL TTL as timedelta"""
        return timedelta(seconds=self.upload_url_ttl_seconds)


@dataclass
class ProgressTrackingConfig:
    """Progress tracking configuration for uploads"""
    
    # Progress tracking settings
    progress_ttl_seconds: int = 3600  # 1 hour TTL for progress data
    progress_update_interval: float = 0.5  # Update every 500ms
    progress_prefix: str = "upload_progress"
    
    # WebSocket settings
    websocket_max_connections_per_user: int = 5
    websocket_max_connections_total: int = 1000
    websocket_ping_interval: int = 30  # seconds
    websocket_ping_timeout: int = 10  # seconds
    
    # Performance settings
    progress_batch_size: int = 100
    progress_cleanup_interval: int = 300  # 5 minutes
    
    @classmethod
    def from_env(cls) -> 'ProgressTrackingConfig':
        """Create progress tracking config from environment variables"""
        return cls(
            progress_ttl_seconds=int(os.getenv('PROGRESS_TTL_SECONDS', '3600')),
            progress_update_interval=float(os.getenv('PROGRESS_UPDATE_INTERVAL', '0.5')),
            progress_prefix=os.getenv('PROGRESS_PREFIX', 'upload_progress'),
            websocket_max_connections_per_user=int(os.getenv('WEBSOCKET_MAX_CONNECTIONS_PER_USER', '5')),
            websocket_max_connections_total=int(os.getenv('WEBSOCKET_MAX_CONNECTIONS_TOTAL', '1000')),
            websocket_ping_interval=int(os.getenv('WEBSOCKET_PING_INTERVAL', '30')),
            websocket_ping_timeout=int(os.getenv('WEBSOCKET_PING_TIMEOUT', '10')),
            progress_batch_size=int(os.getenv('PROGRESS_BATCH_SIZE', '100')),
            progress_cleanup_interval=int(os.getenv('PROGRESS_CLEANUP_INTERVAL', '300'))
        )


@dataclass
class StorageConfig:
    """Storage configuration for uploads"""
    
    # Storage type
    use_s3: bool = True
    use_local_storage: bool = False
    
    # S3 settings
    s3_bucket_name: str = "secureai-deepfake-videos"
    s3_region: str = "us-east-1"
    s3_access_key_id: Optional[str] = None
    s3_secret_access_key: Optional[str] = None
    
    # Local storage settings
    local_upload_folder: str = "uploads"
    local_temp_folder: str = "temp_uploads"
    
    @classmethod
    def from_env(cls) -> 'StorageConfig':
        """Create storage config from environment variables"""
        use_s3 = os.getenv('USE_S3', 'true').lower() == 'true'
        use_local = os.getenv('USE_LOCAL_STORAGE', 'false').lower() == 'true'
        
        return cls(
            use_s3=use_s3,
            use_local_storage=use_local,
            s3_bucket_name=os.getenv('S3_BUCKET_NAME', 'secureai-deepfake-videos'),
            s3_region=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
            s3_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            s3_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            local_upload_folder=os.getenv('LOCAL_UPLOAD_FOLDER', 'uploads'),
            local_temp_folder=os.getenv('LOCAL_TEMP_FOLDER', 'temp_uploads')
        )


class UploadSessionSettings:
    """Main configuration class for upload session management"""
    
    def __init__(self):
        self.redis = RedisConfig.from_env()
        self.upload_session = UploadSessionConfig.from_env()
        self.storage = StorageConfig.from_env()
        self.progress_tracking = ProgressTrackingConfig.from_env()
    
    def get_redis_config_dict(self) -> Dict[str, Any]:
        """Get Redis configuration as dictionary"""
        return {
            'host': self.redis.host,
            'port': self.redis.port,
            'db': self.redis.db,
            'password': self.redis.password,
            'decode_responses': self.redis.decode_responses,
            'socket_timeout': self.redis.socket_timeout,
            'socket_connect_timeout': self.redis.socket_connect_timeout,
            'retry_on_timeout': self.redis.retry_on_timeout,
            'max_connections': self.redis.max_connections,
            'health_check_interval': self.redis.health_check_interval
        }
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate configuration and return validation results"""
        validation_results = {
            'redis': {
                'host_configured': bool(self.redis.host),
                'port_valid': 1 <= self.redis.port <= 65535,
                'db_valid': 0 <= self.redis.db <= 15
            },
            'upload_session': {
                'max_file_size_valid': self.upload_session.max_file_size_bytes > 0,
                'session_ttl_valid': self.upload_session.session_ttl_seconds > 0,
                'allowed_formats_configured': len(self.upload_session.allowed_formats) > 0,
                'quota_limit_valid': self.upload_session.default_quota_limit_bytes > 0
            },
            'storage': {
                's3_configured': self.storage.use_s3 and bool(self.storage.s3_bucket_name),
                'local_configured': self.storage.use_local_storage and bool(self.storage.local_upload_folder),
                'at_least_one_storage': self.storage.use_s3 or self.storage.use_local_storage
            },
            'progress_tracking': {
                'progress_ttl_valid': self.progress_tracking.progress_ttl_seconds > 0,
                'update_interval_valid': self.progress_tracking.progress_update_interval > 0,
                'websocket_limits_valid': (
                    self.progress_tracking.websocket_max_connections_per_user > 0 and
                    self.progress_tracking.websocket_max_connections_total > 0
                ),
                'cleanup_interval_valid': self.progress_tracking.progress_cleanup_interval > 0
            }
        }
        
        # Overall validation
        validation_results['overall_valid'] = all(
            all(section.values()) for section in validation_results.values()
            if isinstance(section, dict)
        )
        
        return validation_results


# Global configuration instance
upload_settings = UploadSessionSettings()


# Configuration validation functions
def validate_upload_configuration() -> bool:
    """Validate upload session configuration"""
    validation_results = upload_settings.validate_configuration()
    return validation_results['overall_valid']


def get_configuration_summary() -> Dict[str, Any]:
    """Get configuration summary for debugging"""
    return {
        'redis': {
            'host': upload_settings.redis.host,
            'port': upload_settings.redis.port,
            'db': upload_settings.redis.db,
            'max_connections': upload_settings.redis.max_connections
        },
        'upload_session': {
            'max_file_size_mb': upload_settings.upload_session.max_file_size_mb,
            'max_file_size_gb': upload_settings.upload_session.max_file_size_gb,
            'session_ttl_hours': upload_settings.upload_session.session_ttl_seconds / 3600,
            'allowed_formats': upload_settings.upload_session.allowed_formats,
            'default_quota_gb': upload_settings.upload_session.default_quota_limit_gb
        },
        'storage': {
            'use_s3': upload_settings.storage.use_s3,
            'use_local': upload_settings.storage.use_local_storage,
            's3_bucket': upload_settings.storage.s3_bucket_name if upload_settings.storage.use_s3 else None,
            'local_folder': upload_settings.storage.local_upload_folder if upload_settings.storage.use_local_storage else None
        },
        'progress_tracking': {
            'progress_ttl_hours': upload_settings.progress_tracking.progress_ttl_seconds / 3600,
            'update_interval_ms': upload_settings.progress_tracking.progress_update_interval * 1000,
            'progress_prefix': upload_settings.progress_tracking.progress_prefix,
            'websocket_max_per_user': upload_settings.progress_tracking.websocket_max_connections_per_user,
            'websocket_max_total': upload_settings.progress_tracking.websocket_max_connections_total,
            'cleanup_interval_minutes': upload_settings.progress_tracking.progress_cleanup_interval / 60
        },
        'validation': upload_settings.validate_configuration()
    }
