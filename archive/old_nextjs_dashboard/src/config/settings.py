#!/usr/bin/env python3
"""
Configuration Settings for Enhanced Video Upload
Settings for upload parameters, file validation, and processing configuration
"""

import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class UploadSettings:
    """Upload configuration settings."""
    # File size limits
    max_file_size: int = 500 * 1024 * 1024  # 500MB
    min_file_size: int = 1024  # 1KB
    
    # Upload directories
    upload_dir: str = "uploads"
    temp_upload_dir: str = "temp_uploads"
    results_dir: str = "results"
    
    # Chunked upload settings
    max_chunk_size: int = 10 * 1024 * 1024  # 10MB per chunk
    max_total_chunks: int = 100  # Maximum number of chunks
    
    # Session settings
    session_timeout_hours: int = 24  # Upload session timeout
    max_concurrent_sessions: int = 10  # Per user
    
    # Supported video formats
    supported_video_formats: List[str] = None
    
    # Processing settings
    default_processing_priority: int = 5  # 1-10 scale
    max_processing_priority: int = 10
    min_processing_priority: int = 1
    
    # Deduplication settings
    enable_deduplication: bool = True
    embedding_cache_url: Optional[str] = None
    
    # WebSocket settings
    websocket_enabled: bool = True
    websocket_heartbeat_interval: int = 30  # seconds
    
    # Redis/Celery settings
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values after dataclass creation."""
        if self.supported_video_formats is None:
            self.supported_video_formats = [
                'video/mp4',
                'video/avi',
                'video/mov',
                'video/quicktime',
                'video/x-msvideo',
                'video/mkv',
                'video/x-matroska',
                'video/webm',
                'video/ogg'
            ]


@dataclass
class ValidationSettings:
    """File validation configuration settings."""
    # Content validation
    strict_content_validation: bool = True
    validate_file_integrity: bool = True
    check_magic_bytes: bool = True
    
    # Security validation
    enable_security_checks: bool = True
    scan_for_malware: bool = False
    
    # File format validation
    allowed_extensions: List[str] = None
    blocked_extensions: List[str] = None
    
    def __post_init__(self):
        """Initialize default values after dataclass creation."""
        if self.allowed_extensions is None:
            self.allowed_extensions = [
                '.mp4', '.avi', '.mov', '.mkv', '.webm', '.ogg'
            ]
        
        if self.blocked_extensions is None:
            self.blocked_extensions = [
                '.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.vbs', '.js',
                '.jar', '.php', '.asp', '.aspx', '.jsp', '.py', '.rb', '.pl',
                '.sh', '.ps1', '.psm1', '.psd1', '.ps1xml', '.psc1', '.pssc'
            ]


@dataclass
class ProcessingSettings:
    """Video processing configuration settings."""
    # Processing queue settings
    max_concurrent_jobs: int = 5
    job_timeout_minutes: int = 60
    
    # Model settings
    default_model_type: str = "resnet50"
    available_models: List[str] = None
    
    # Performance settings
    enable_gpu_acceleration: bool = True
    max_memory_usage_mb: int = 4096
    
    def __post_init__(self):
        """Initialize default values after dataclass creation."""
        if self.available_models is None:
            self.available_models = [
                'resnet50',
                'clip',
                'ensemble',
                'diffusion_aware'
            ]


class SettingsManager:
    """
    Configuration manager for loading and managing settings from environment variables.
    """
    
    def __init__(self):
        """Initialize settings manager."""
        self._upload_settings: Optional[UploadSettings] = None
        self._validation_settings: Optional[ValidationSettings] = None
        self._processing_settings: Optional[ProcessingSettings] = None
    
    def load_upload_settings(self) -> UploadSettings:
        """Load upload settings from environment variables."""
        if self._upload_settings is None:
            self._upload_settings = UploadSettings(
                max_file_size=int(os.getenv('UPLOAD_MAX_FILE_SIZE', '524288000')),  # 500MB
                min_file_size=int(os.getenv('UPLOAD_MIN_FILE_SIZE', '1024')),  # 1KB
                upload_dir=os.getenv('UPLOAD_DIR', 'uploads'),
                temp_upload_dir=os.getenv('TEMP_UPLOAD_DIR', 'temp_uploads'),
                results_dir=os.getenv('RESULTS_DIR', 'results'),
                max_chunk_size=int(os.getenv('UPLOAD_MAX_CHUNK_SIZE', '10485760')),  # 10MB
                max_total_chunks=int(os.getenv('UPLOAD_MAX_TOTAL_CHUNKS', '100')),
                session_timeout_hours=int(os.getenv('UPLOAD_SESSION_TIMEOUT_HOURS', '24')),
                max_concurrent_sessions=int(os.getenv('UPLOAD_MAX_CONCURRENT_SESSIONS', '10')),
                default_processing_priority=int(os.getenv('DEFAULT_PROCESSING_PRIORITY', '5')),
                max_processing_priority=int(os.getenv('MAX_PROCESSING_PRIORITY', '10')),
                min_processing_priority=int(os.getenv('MIN_PROCESSING_PRIORITY', '1')),
                enable_deduplication=os.getenv('ENABLE_DEDUPLICATION', 'true').lower() == 'true',
                embedding_cache_url=os.getenv('EMBEDDING_CACHE_URL'),
                websocket_enabled=os.getenv('WEBSOCKET_ENABLED', 'true').lower() == 'true',
                websocket_heartbeat_interval=int(os.getenv('WEBSOCKET_HEARTBEAT_INTERVAL', '30')),
                celery_broker_url=os.getenv('CELERY_BROKER_URL'),
                celery_result_backend=os.getenv('CELERY_RESULT_BACKEND')
            )
            
            # Parse supported video formats from environment
            supported_formats_str = os.getenv('SUPPORTED_VIDEO_FORMATS')
            if supported_formats_str:
                self._upload_settings.supported_video_formats = [
                    fmt.strip() for fmt in supported_formats_str.split(',')
                ]
        
        return self._upload_settings
    
    def load_validation_settings(self) -> ValidationSettings:
        """Load validation settings from environment variables."""
        if self._validation_settings is None:
            self._validation_settings = ValidationSettings(
                strict_content_validation=os.getenv('VALIDATION_STRICT_CONTENT', 'true').lower() == 'true',
                validate_file_integrity=os.getenv('VALIDATION_FILE_INTEGRITY', 'true').lower() == 'true',
                check_magic_bytes=os.getenv('VALIDATION_MAGIC_BYTES', 'true').lower() == 'true',
                enable_security_checks=os.getenv('VALIDATION_SECURITY_CHECKS', 'true').lower() == 'true',
                scan_for_malware=os.getenv('VALIDATION_SCAN_MALWARE', 'false').lower() == 'true'
            )
            
            # Parse allowed extensions from environment
            allowed_extensions_str = os.getenv('ALLOWED_FILE_EXTENSIONS')
            if allowed_extensions_str:
                self._validation_settings.allowed_extensions = [
                    ext.strip() for ext in allowed_extensions_str.split(',')
                ]
            
            # Parse blocked extensions from environment
            blocked_extensions_str = os.getenv('BLOCKED_FILE_EXTENSIONS')
            if blocked_extensions_str:
                self._validation_settings.blocked_extensions = [
                    ext.strip() for ext in blocked_extensions_str.split(',')
                ]
        
        return self._validation_settings
    
    def load_processing_settings(self) -> ProcessingSettings:
        """Load processing settings from environment variables."""
        if self._processing_settings is None:
            self._processing_settings = ProcessingSettings(
                max_concurrent_jobs=int(os.getenv('PROCESSING_MAX_CONCURRENT_JOBS', '5')),
                job_timeout_minutes=int(os.getenv('PROCESSING_JOB_TIMEOUT_MINUTES', '60')),
                default_model_type=os.getenv('DEFAULT_MODEL_TYPE', 'resnet50'),
                enable_gpu_acceleration=os.getenv('PROCESSING_ENABLE_GPU', 'true').lower() == 'true',
                max_memory_usage_mb=int(os.getenv('PROCESSING_MAX_MEMORY_MB', '4096'))
            )
            
            # Parse available models from environment
            available_models_str = os.getenv('AVAILABLE_MODELS')
            if available_models_str:
                self._processing_settings.available_models = [
                    model.strip() for model in available_models_str.split(',')
                ]
        
        return self._processing_settings
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings as a dictionary."""
        return {
            'upload': self.load_upload_settings(),
            'validation': self.load_validation_settings(),
            'processing': self.load_processing_settings()
        }
    
    def validate_settings(self) -> Dict[str, List[str]]:
        """
        Validate all settings and return any issues.
        
        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []
        
        try:
            upload_settings = self.load_upload_settings()
            validation_settings = self.load_validation_settings()
            processing_settings = self.load_processing_settings()
            
            # Validate upload settings
            if upload_settings.max_file_size <= 0:
                errors.append("Upload max file size must be positive")
            
            if upload_settings.max_file_size > 5 * 1024 * 1024 * 1024:  # 5GB
                warnings.append("Upload max file size is very large (>5GB)")
            
            if upload_settings.max_chunk_size <= 0:
                errors.append("Upload max chunk size must be positive")
            
            if upload_settings.max_total_chunks <= 0:
                errors.append("Upload max total chunks must be positive")
            
            if upload_settings.session_timeout_hours <= 0:
                errors.append("Upload session timeout must be positive")
            
            if not upload_settings.supported_video_formats:
                errors.append("At least one video format must be supported")
            
            # Validate processing settings
            if processing_settings.max_concurrent_jobs <= 0:
                errors.append("Processing max concurrent jobs must be positive")
            
            if processing_settings.job_timeout_minutes <= 0:
                errors.append("Processing job timeout must be positive")
            
            if processing_settings.default_model_type not in processing_settings.available_models:
                errors.append("Default model type must be in available models list")
            
            # Validate validation settings
            if not validation_settings.allowed_extensions:
                errors.append("At least one file extension must be allowed")
            
            # Check for conflicting settings
            if upload_settings.enable_deduplication and not upload_settings.embedding_cache_url:
                warnings.append("Deduplication enabled but no embedding cache URL provided")
            
            if upload_settings.websocket_enabled and not upload_settings.websocket_heartbeat_interval:
                warnings.append("WebSocket enabled but no heartbeat interval configured")
            
        except Exception as e:
            errors.append(f"Settings validation failed: {str(e)}")
        
        return {
            'errors': errors,
            'warnings': warnings
        }


# Global settings manager instance
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """Get or create the global settings manager instance."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager


def get_upload_settings() -> UploadSettings:
    """Get upload settings."""
    return get_settings_manager().load_upload_settings()


def get_validation_settings() -> ValidationSettings:
    """Get validation settings."""
    return get_settings_manager().load_validation_settings()


def get_processing_settings() -> ProcessingSettings:
    """Get processing settings."""
    return get_settings_manager().load_processing_settings()


def validate_all_settings() -> Dict[str, List[str]]:
    """Validate all settings."""
    return get_settings_manager().validate_settings()


def get_all_settings() -> Dict[str, Any]:
    """Get all settings."""
    return get_settings_manager().get_all_settings()


# Environment variable documentation
ENVIRONMENT_VARIABLES = {
    'UPLOAD_MAX_FILE_SIZE': 'Maximum file size in bytes (default: 524288000 = 500MB)',
    'UPLOAD_MIN_FILE_SIZE': 'Minimum file size in bytes (default: 1024 = 1KB)',
    'UPLOAD_DIR': 'Directory for uploaded files (default: uploads)',
    'TEMP_UPLOAD_DIR': 'Directory for temporary upload files (default: temp_uploads)',
    'RESULTS_DIR': 'Directory for processing results (default: results)',
    'UPLOAD_MAX_CHUNK_SIZE': 'Maximum chunk size in bytes (default: 10485760 = 10MB)',
    'UPLOAD_MAX_TOTAL_CHUNKS': 'Maximum number of chunks per upload (default: 100)',
    'UPLOAD_SESSION_TIMEOUT_HOURS': 'Upload session timeout in hours (default: 24)',
    'UPLOAD_MAX_CONCURRENT_SESSIONS': 'Maximum concurrent sessions per user (default: 10)',
    'DEFAULT_PROCESSING_PRIORITY': 'Default processing priority 1-10 (default: 5)',
    'MAX_PROCESSING_PRIORITY': 'Maximum processing priority (default: 10)',
    'MIN_PROCESSING_PRIORITY': 'Minimum processing priority (default: 1)',
    'ENABLE_DEDUPLICATION': 'Enable file deduplication (default: true)',
    'EMBEDDING_CACHE_URL': 'URL for embedding cache service',
    'WEBSOCKET_ENABLED': 'Enable WebSocket notifications (default: true)',
    'WEBSOCKET_HEARTBEAT_INTERVAL': 'WebSocket heartbeat interval in seconds (default: 30)',
    'CELERY_BROKER_URL': 'Celery broker URL (Redis)',
    'CELERY_RESULT_BACKEND': 'Celery result backend URL',
    'SUPPORTED_VIDEO_FORMATS': 'Comma-separated list of supported MIME types',
    'VALIDATION_STRICT_CONTENT': 'Enable strict content validation (default: true)',
    'VALIDATION_FILE_INTEGRITY': 'Enable file integrity validation (default: true)',
    'VALIDATION_MAGIC_BYTES': 'Enable magic bytes validation (default: true)',
    'VALIDATION_SECURITY_CHECKS': 'Enable security checks (default: true)',
    'VALIDATION_SCAN_MALWARE': 'Enable malware scanning (default: false)',
    'ALLOWED_FILE_EXTENSIONS': 'Comma-separated list of allowed extensions',
    'BLOCKED_FILE_EXTENSIONS': 'Comma-separated list of blocked extensions',
    'PROCESSING_MAX_CONCURRENT_JOBS': 'Maximum concurrent processing jobs (default: 5)',
    'PROCESSING_JOB_TIMEOUT_MINUTES': 'Processing job timeout in minutes (default: 60)',
    'DEFAULT_MODEL_TYPE': 'Default model type for processing (default: resnet50)',
    'PROCESSING_ENABLE_GPU': 'Enable GPU acceleration (default: true)',
    'PROCESSING_MAX_MEMORY_MB': 'Maximum memory usage in MB (default: 4096)',
    'AVAILABLE_MODELS': 'Comma-separated list of available models'
}


def print_environment_variables():
    """Print documentation for environment variables."""
    print("Environment Variables for Enhanced Video Upload Configuration:")
    print("=" * 60)
    for var, description in ENVIRONMENT_VARIABLES.items():
        print(f"{var}: {description}")
    print("=" * 60)


# Export main components
__all__ = [
    'UploadSettings',
    'ValidationSettings',
    'ProcessingSettings',
    'SettingsManager',
    'get_upload_settings',
    'get_validation_settings',
    'get_processing_settings',
    'validate_all_settings',
    'get_all_settings',
    'print_environment_variables'
]
