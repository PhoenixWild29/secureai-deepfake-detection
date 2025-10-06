#!/usr/bin/env python3
"""
Video Upload Schemas
Pydantic schemas for video upload request/response validation
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from uuid import UUID
from pydantic import BaseModel, Field, validator
from enum import Enum


class VideoUploadStatus(str, Enum):
    """Video upload status enumeration"""
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    FAILED = "failed"


class VideoFormat(str, Enum):
    """Supported video formats"""
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    MKV = "mkv"
    WEBM = "webm"


class VideoUploadRequest(BaseModel):
    """
    Request model for video file upload.
    Contains session validation and file metadata.
    """
    
    session_id: UUID = Field(
        ...,
        description="Upload session ID for validation"
    )
    
    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Original filename of the video"
    )
    
    file_size: int = Field(
        ...,
        ge=1,
        le=524288000,  # 500MB max
        description="File size in bytes"
    )
    
    content_type: str = Field(
        ...,
        description="MIME content type of the file"
    )
    
    file_hash: Optional[str] = Field(
        default=None,
        max_length=64,
        description="SHA256 hash of the file (optional, will be calculated if not provided)"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional file metadata"
    )
    
    @validator('filename')
    def validate_filename(cls, v):
        """Validate filename format"""
        if not v or not v.strip():
            raise ValueError("Filename cannot be empty")
        
        # Check for valid video extension
        allowed_extensions = [fmt.value for fmt in VideoFormat]
        if not any(v.lower().endswith(f'.{ext}') for ext in allowed_extensions):
            raise ValueError(f"Invalid video format. Allowed formats: {', '.join(allowed_extensions)}")
        
        return v.strip()
    
    @validator('content_type')
    def validate_content_type(cls, v):
        """Validate content type"""
        allowed_types = [
            'video/mp4',
            'video/avi',
            'video/quicktime',
            'video/x-msvideo',
            'video/x-matroska',
            'video/webm'
        ]
        
        if v not in allowed_types:
            raise ValueError(f"Unsupported content type. Allowed types: {', '.join(allowed_types)}")
        
        return v
    
    @validator('file_size')
    def validate_file_size(cls, v):
        """Validate file size"""
        max_size = 524288000  # 500MB
        if v > max_size:
            raise ValueError(f"File size exceeds maximum limit of {max_size // (1024*1024)}MB")
        return v


class VideoUploadResponse(BaseModel):
    """
    Response model for video upload completion.
    Contains video ID, analysis ID, and processing information.
    """
    
    video_id: UUID = Field(
        ...,
        description="Unique identifier for the uploaded video"
    )
    
    analysis_id: Optional[UUID] = Field(
        default=None,
        description="Analysis ID from Core Detection Engine"
    )
    
    upload_status: VideoUploadStatus = Field(
        ...,
        description="Current upload and processing status"
    )
    
    redirect_url: str = Field(
        ...,
        description="URL to redirect user after upload completion"
    )
    
    estimated_processing_time: Optional[int] = Field(
        default=None,
        description="Estimated processing time in seconds"
    )
    
    # File information
    filename: str = Field(
        ...,
        description="Original filename"
    )
    
    file_size: int = Field(
        ...,
        description="File size in bytes"
    )
    
    file_hash: str = Field(
        ...,
        description="SHA256 hash of the file"
    )
    
    format: VideoFormat = Field(
        ...,
        description="Video format"
    )
    
    # Storage information
    s3_key: str = Field(
        ...,
        description="S3 object key"
    )
    
    s3_url: Optional[str] = Field(
        default=None,
        description="Public S3 URL for accessing the video"
    )
    
    # Processing information
    created_at: datetime = Field(
        ...,
        description="When the video record was created"
    )
    
    uploaded_at: Optional[datetime] = Field(
        default=None,
        description="When upload completed"
    )
    
    # Analysis information
    detection_result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detection engine results (if analysis completed)"
    )
    
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Detection confidence score"
    )
    
    is_fake: Optional[bool] = Field(
        default=None,
        description="Detection result: True if fake, False if authentic"
    )
    
    processing_time: Optional[float] = Field(
        default=None,
        description="Analysis processing time in seconds"
    )
    
    # Error information
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if processing failed"
    )
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional video metadata"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class VideoUploadError(BaseModel):
    """
    Error response model for video upload failures.
    """
    
    error_code: str = Field(
        ...,
        description="Error code for programmatic handling"
    )
    
    error_message: str = Field(
        ...,
        description="Human-readable error message"
    )
    
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the error occurred"
    )
    
    # Cleanup information
    cleanup_performed: bool = Field(
        default=False,
        description="Whether cleanup operations were performed"
    )
    
    cleanup_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Details about cleanup operations"
    )


class VideoUploadProgress(BaseModel):
    """
    Progress update model for video upload tracking.
    """
    
    video_id: UUID = Field(
        ...,
        description="Video ID being processed"
    )
    
    session_id: UUID = Field(
        ...,
        description="Upload session ID"
    )
    
    status: VideoUploadStatus = Field(
        ...,
        description="Current processing status"
    )
    
    progress_percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Progress percentage (0-100)"
    )
    
    current_step: str = Field(
        ...,
        description="Current processing step"
    )
    
    estimated_time_remaining: Optional[int] = Field(
        default=None,
        description="Estimated time remaining in seconds"
    )
    
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this progress update was generated"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional progress metadata"
    )


class VideoValidationResult(BaseModel):
    """
    Video validation result model.
    """
    
    is_valid: bool = Field(
        ...,
        description="Whether the video file is valid"
    )
    
    validation_errors: List[str] = Field(
        default_factory=list,
        description="List of validation errors"
    )
    
    warnings: List[str] = Field(
        default_factory=list,
        description="List of validation warnings"
    )
    
    # File information
    filename: str = Field(
        ...,
        description="Validated filename"
    )
    
    file_size: int = Field(
        ...,
        description="Validated file size"
    )
    
    format: VideoFormat = Field(
        ...,
        description="Detected video format"
    )
    
    # Video metadata
    duration: Optional[float] = Field(
        default=None,
        description="Video duration in seconds"
    )
    
    resolution: Optional[str] = Field(
        default=None,
        description="Video resolution (e.g., '1920x1080')"
    )
    
    fps: Optional[float] = Field(
        default=None,
        description="Frames per second"
    )
    
    bitrate: Optional[int] = Field(
        default=None,
        description="Video bitrate in bits per second"
    )
    
    codec: Optional[str] = Field(
        default=None,
        description="Video codec"
    )
    
    # Validation metadata
    validation_time: float = Field(
        ...,
        description="Time taken for validation in seconds"
    )
    
    validation_method: str = Field(
        default="ffprobe",
        description="Method used for validation"
    )


class VideoAnalysisRequest(BaseModel):
    """
    Request model for initiating video analysis.
    """
    
    video_id: UUID = Field(
        ...,
        description="Video ID to analyze"
    )
    
    model_type: str = Field(
        default="resnet",
        description="Detection model type to use"
    )
    
    analysis_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Analysis configuration parameters"
    )
    
    priority: int = Field(
        default=0,
        description="Analysis priority (higher number = higher priority)"
    )


class VideoAnalysisResponse(BaseModel):
    """
    Response model for video analysis results.
    """
    
    analysis_id: UUID = Field(
        ...,
        description="Analysis ID"
    )
    
    video_id: UUID = Field(
        ...,
        description="Video ID that was analyzed"
    )
    
    status: str = Field(
        ...,
        description="Analysis status"
    )
    
    detection_result: Dict[str, Any] = Field(
        ...,
        description="Detection engine results"
    )
    
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Detection confidence score"
    )
    
    is_fake: bool = Field(
        ...,
        description="Detection result: True if fake, False if authentic"
    )
    
    processing_time: float = Field(
        ...,
        description="Analysis processing time in seconds"
    )
    
    model_used: str = Field(
        ...,
        description="Detection model used"
    )
    
    created_at: datetime = Field(
        ...,
        description="When analysis was initiated"
    )
    
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When analysis completed"
    )
    
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if analysis failed"
    )


# Common error codes for video uploads
class VideoUploadErrorCodes:
    """Standard error codes for video upload operations"""
    
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    INVALID_FILE = "INVALID_FILE"
    S3_UPLOAD_FAILED = "S3_UPLOAD_FAILED"
    DATABASE_ERROR = "DATABASE_ERROR"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    CLEANUP_FAILED = "CLEANUP_FAILED"


# Upload configuration constants
class VideoUploadConfig:
    """Video upload configuration constants"""
    
    MAX_FILE_SIZE = 524288000  # 500MB in bytes
    ALLOWED_FORMATS = ['mp4', 'avi', 'mov', 'mkv', 'webm']
    ALLOWED_CONTENT_TYPES = [
        'video/mp4',
        'video/avi',
        'video/quicktime',
        'video/x-msvideo',
        'video/x-matroska',
        'video/webm'
    ]
    S3_KEY_PREFIX = "dashboard-uploads"
    DEFAULT_MODEL_TYPE = "resnet"
    DEFAULT_ANALYSIS_PRIORITY = 0
    
    @classmethod
    def get_max_file_size_mb(cls) -> int:
        """Get max file size in MB"""
        return cls.MAX_FILE_SIZE // (1024 * 1024)
    
    @classmethod
    def get_max_file_size_gb(cls) -> float:
        """Get max file size in GB"""
        return cls.MAX_FILE_SIZE / (1024 * 1024 * 1024)
    
    @classmethod
    def is_allowed_format(cls, filename: str) -> bool:
        """Check if filename has allowed format"""
        return any(filename.lower().endswith(f'.{fmt}') for fmt in cls.ALLOWED_FORMATS)
    
    @classmethod
    def is_allowed_content_type(cls, content_type: str) -> bool:
        """Check if content type is allowed"""
        return content_type in cls.ALLOWED_CONTENT_TYPES
