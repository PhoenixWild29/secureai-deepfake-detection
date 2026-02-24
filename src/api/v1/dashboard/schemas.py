#!/usr/bin/env python3
"""
Dashboard Upload Session Schemas
Pydantic schemas for upload session management API endpoints
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from uuid import UUID
from pydantic import BaseModel, Field, validator


class DashboardContext(BaseModel):
    """
    Dashboard context information for upload sessions.
    Provides context about where the upload is initiated from.
    """
    
    source_section: str = Field(
        ...,
        description="Dashboard section where upload was initiated (e.g., 'video_analysis', 'batch_upload', 'training_data')"
    )
    
    workflow_type: str = Field(
        ...,
        description="Type of workflow being used (e.g., 'single_upload', 'batch_upload', 'training_upload')"
    )
    
    user_preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="User-specific preferences and settings for the upload session"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata for the upload session"
    )
    
    @validator('source_section')
    def validate_source_section(cls, v):
        """Validate source section is not empty"""
        if not v or not v.strip():
            raise ValueError("Source section cannot be empty")
        return v.strip()
    
    @validator('workflow_type')
    def validate_workflow_type(cls, v):
        """Validate workflow type is supported"""
        supported_types = ['single_upload', 'batch_upload', 'training_upload', 'analysis_upload']
        if v not in supported_types:
            raise ValueError(f"Unsupported workflow type. Supported types: {', '.join(supported_types)}")
        return v


class UploadSessionInitiateRequest(BaseModel):
    """
    Request model for initiating an upload session.
    Contains dashboard context and upload preferences.
    """
    
    dashboard_context: DashboardContext = Field(
        ...,
        description="Dashboard context information for the upload session"
    )
    
    expected_file_size: Optional[int] = Field(
        default=None,
        ge=1,
        le=524288000,  # 500MB max
        description="Expected file size in bytes (optional, for quota pre-validation)"
    )
    
    file_format: Optional[str] = Field(
        default=None,
        description="Expected file format (optional, for validation)"
    )
    
    @validator('file_format')
    def validate_file_format(cls, v):
        """Validate file format if provided"""
        if v is not None:
            allowed_formats = ['mp4', 'avi', 'mov', 'mkv', 'webm']
            if v.lower() not in allowed_formats:
                raise ValueError(f"Unsupported file format. Allowed formats: {', '.join(allowed_formats)}")
            return v.lower()
        return v


class UploadSessionResponse(BaseModel):
    """
    Response model for upload session initiation.
    Contains session details and upload information.
    """
    
    session_id: UUID = Field(
        ...,
        description="Unique session identifier for the upload"
    )
    
    upload_url: str = Field(
        ...,
        description="Pre-signed URL for direct file upload to storage"
    )
    
    max_file_size: int = Field(
        ...,
        description="Maximum allowed file size in bytes (500MB)"
    )
    
    allowed_formats: List[str] = Field(
        ...,
        description="List of allowed file formats"
    )
    
    remaining_quota: int = Field(
        ...,
        description="User's remaining upload quota in bytes"
    )
    
    quota_limit: int = Field(
        ...,
        description="User's total upload quota limit in bytes"
    )
    
    session_expires_at: datetime = Field(
        ...,
        description="Timestamp when the upload session expires (UTC)"
    )
    
    dashboard_context: DashboardContext = Field(
        ...,
        description="Dashboard context for this upload session"
    )
    
    upload_instructions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Instructions for using the upload URL"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class UploadSessionStatus(BaseModel):
    """
    Status information for an upload session.
    Used for session validation and status checks.
    """
    
    session_id: UUID = Field(
        ...,
        description="Session identifier"
    )
    
    user_id: UUID = Field(
        ...,
        description="User who owns this session"
    )
    
    status: str = Field(
        ...,
        description="Session status (active, expired, completed, failed)"
    )
    
    created_at: datetime = Field(
        ...,
        description="When the session was created"
    )
    
    expires_at: datetime = Field(
        ...,
        description="When the session expires"
    )
    
    dashboard_context: DashboardContext = Field(
        ...,
        description="Original dashboard context"
    )
    
    upload_url: Optional[str] = Field(
        default=None,
        description="Upload URL (may be None if session expired)"
    )
    
    is_expired: bool = Field(
        ...,
        description="Whether the session has expired"
    )
    
    is_valid: bool = Field(
        ...,
        description="Whether the session is valid for uploads"
    )


class UploadSessionValidationRequest(BaseModel):
    """
    Request model for validating an upload session.
    Used to check session ownership and validity.
    """
    
    session_id: UUID = Field(
        ...,
        description="Session identifier to validate"
    )
    
    user_id: UUID = Field(
        ...,
        description="User ID claiming ownership of the session"
    )


class UploadSessionValidationResponse(BaseModel):
    """
    Response model for upload session validation.
    Contains validation results and session information.
    """
    
    is_valid: bool = Field(
        ...,
        description="Whether the session is valid"
    )
    
    is_owner: bool = Field(
        ...,
        description="Whether the user owns this session"
    )
    
    session_status: Optional[UploadSessionStatus] = Field(
        default=None,
        description="Session status information (if valid)"
    )
    
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if validation failed"
    )


class UploadQuotaInfo(BaseModel):
    """
    User upload quota information.
    Used in session responses and quota validation.
    """
    
    quota_limit: int = Field(
        ...,
        description="Total quota limit in bytes"
    )
    
    quota_used: int = Field(
        ...,
        description="Quota used in bytes"
    )
    
    quota_remaining: int = Field(
        ...,
        description="Remaining quota in bytes"
    )
    
    quota_limit_gb: float = Field(
        ...,
        description="Quota limit in GB"
    )
    
    quota_used_gb: float = Field(
        ...,
        description="Quota used in GB"
    )
    
    quota_remaining_gb: float = Field(
        ...,
        description="Remaining quota in GB"
    )
    
    usage_percentage: float = Field(
        ...,
        description="Quota usage percentage"
    )
    
    reset_date: datetime = Field(
        ...,
        description="When the quota resets"
    )


class UploadSessionError(BaseModel):
    """
    Error response model for upload session operations.
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


# Common error codes for upload sessions
class UploadSessionErrorCodes:
    """Standard error codes for upload session operations"""
    
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    INVALID_REQUEST = "INVALID_REQUEST"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    SESSION_CREATION_FAILED = "SESSION_CREATION_FAILED"
    REDIS_CONNECTION_ERROR = "REDIS_CONNECTION_ERROR"
    QUOTA_VALIDATION_FAILED = "QUOTA_VALIDATION_FAILED"


# Upload configuration constants
class UploadConfig:
    """Upload configuration constants"""
    
    MAX_FILE_SIZE = 524288000  # 500MB in bytes
    ALLOWED_FORMATS = ['mp4', 'avi', 'mov', 'mkv', 'webm']
    SESSION_TTL_SECONDS = 3600  # 1 hour
    REDIS_SESSION_PREFIX = "upload_session"
    UPLOAD_URL_TTL_SECONDS = 3600  # 1 hour for pre-signed URLs
    
    @classmethod
    def get_max_file_size_mb(cls) -> int:
        """Get max file size in MB"""
        return cls.MAX_FILE_SIZE // (1024 * 1024)
    
    @classmethod
    def get_max_file_size_gb(cls) -> float:
        """Get max file size in GB"""
        return cls.MAX_FILE_SIZE / (1024 * 1024 * 1024)
