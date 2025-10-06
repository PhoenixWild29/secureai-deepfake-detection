#!/usr/bin/env python3
"""
Upload Data Models and API Schemas
Pydantic models for upload API endpoints with comprehensive validation and integration with Core Detection Engine.
"""

from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator
from fastapi import UploadFile


class UploadStatusEnum(str, Enum):
    """Upload processing status enumeration"""
    PENDING = "pending"
    UPLOADING = "uploading"
    VALIDATING = "validating"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UploadProgressStatusEnum(str, Enum):
    """Upload progress status enumeration"""
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UploadEventTypeEnum(str, Enum):
    """Upload progress event type enumeration"""
    UPLOAD_STARTED = "upload_started"
    UPLOAD_PROGRESS = "upload_progress"
    UPLOAD_COMPLETED = "upload_completed"
    UPLOAD_FAILED = "upload_failed"
    UPLOAD_CANCELLED = "upload_cancelled"


class ValidationResult(BaseModel):
    """File validation result model"""
    is_valid: bool = Field(..., description="Whether the file validation passed")
    error_message: Optional[str] = Field(default=None, description="Error message if validation failed")
    file_format: Optional[str] = Field(default=None, description="Detected file format")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    duration_seconds: Optional[float] = Field(default=None, description="Video duration in seconds")


class S3UploadResult(BaseModel):
    """S3 upload result model"""
    success: bool = Field(..., description="Whether the S3 upload was successful")
    s3_key: Optional[str] = Field(default=None, description="S3 object key if successful")
    s3_url: Optional[str] = Field(default=None, description="S3 URL if successful")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    upload_time_ms: Optional[int] = Field(default=None, description="Upload time in milliseconds")
    file_size: Optional[int] = Field(default=None, description="Uploaded file size in bytes")


class UserQuota(BaseModel):
    """User quota model"""
    user_id: UUID = Field(..., description="User ID")
    quota_limit: int = Field(..., ge=0, description="Total quota limit in bytes")
    quota_used: int = Field(default=0, ge=0, description="Quota used in bytes")
    quota_remaining: int = Field(..., ge=0, description="Remaining quota in bytes")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @model_validator(mode='after')
    def validate_quota_consistency(self):
        """Validate quota consistency"""
        if self.quota_used > self.quota_limit:
            raise ValueError("Quota used cannot exceed quota limit")
        if self.quota_remaining != (self.quota_limit - self.quota_used):
            raise ValueError("Quota remaining must equal quota limit minus quota used")
        return self


class QuotaValidationResult(BaseModel):
    """Quota validation result model"""
    is_valid: bool = Field(..., description="Whether quota validation passed")
    can_upload: bool = Field(..., description="Whether user can upload the file")
    quota_remaining: int = Field(..., ge=0, description="Remaining quota after upload")
    error_message: Optional[str] = Field(default=None, description="Error message if validation failed")


class DashboardUploadRequest(BaseModel):
    """
    Request model for dashboard video uploads with comprehensive validation.
    Extends existing upload patterns with dashboard context and enhanced validation.
    """
    
    # File upload fields
    file: UploadFile = Field(..., description="Video file to upload for deepfake detection")
    user_id: Optional[UUID] = Field(default=None, description="User ID for upload tracking and quota management")
    
    # Upload options
    priority: Optional[int] = Field(default=5, ge=1, le=10, description="Upload priority (1=lowest, 10=highest)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional upload metadata")
    
    # Dashboard context (JSON serialization support)
    dashboard_context: Optional[Dict[str, Any]] = Field(default=None, description="Dashboard navigation context for upload tracking")
    
    # Upload settings
    auto_analyze: bool = Field(default=True, description="Whether to automatically start deepfake analysis after upload")
    store_in_s3: bool = Field(default=True, description="Whether to store file in S3 for distributed access")
    
    # File validation settings
    validate_content: bool = Field(default=True, description="Whether to validate video content integrity")
    check_duplicates: bool = Field(default=True, description="Whether to check for duplicate files using hash")
    
    @field_validator('file')
    @classmethod
    def validate_file(cls, v: UploadFile) -> UploadFile:
        """Validate uploaded file basic properties"""
        if not v.filename:
            raise ValueError("Uploaded file must have a filename")
        
        # Check file extension
        allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        file_extension = v.filename.lower().split('.')[-1] if '.' in v.filename else ''
        if f'.{file_extension}' not in allowed_extensions:
            raise ValueError(f"Unsupported file format. Supported formats: {', '.join(ext.upper() for ext in allowed_extensions)}")
        
        return v
    
    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate metadata structure"""
        if v is not None:
            # Ensure metadata doesn't exceed reasonable size
            metadata_str = str(v)
            if len(metadata_str) > 10000:  # 10KB limit for metadata
                raise ValueError("Metadata size exceeds maximum limit of 10KB")
        return v


class DashboardUploadResponse(BaseModel):
    """
    Response model for dashboard upload results.
    Provides comprehensive upload status and file information.
    """
    
    # Upload identification
    upload_id: UUID = Field(default_factory=uuid4, description="Unique upload identifier")
    video_id: UUID = Field(..., description="Associated video record ID in Core Detection Engine")
    
    # Upload status
    status: UploadStatusEnum = Field(..., description="Upload processing status")
    message: str = Field(..., description="Upload status message")
    
    # File information
    filename: str = Field(..., description="Original filename of uploaded video")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    file_hash: str = Field(..., description="File content hash for duplicate detection")
    format: str = Field(..., description="Detected video format")
    
    # Storage information
    storage_location: str = Field(..., description="Storage location (local/s3)")
    s3_key: Optional[str] = Field(default=None, description="S3 object key if stored in S3")
    s3_url: Optional[str] = Field(default=None, description="S3 URL if stored in S3")
    
    # Processing information
    analysis_id: Optional[UUID] = Field(default=None, description="Analysis ID if auto_analyze enabled")
    processing_time_ms: Optional[int] = Field(default=None, ge=0, description="Upload processing time in milliseconds")
    
    # Validation results
    validation_result: Optional[ValidationResult] = Field(default=None, description="File validation results")
    
    # Timestamps
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Additional context
    dashboard_context: Optional[Dict[str, Any]] = Field(default=None, description="Dashboard context from request")


class UploadSession(BaseModel):
    """
    Upload session model for tracking upload progress and context.
    Manages multiple file uploads within a single session with quota tracking.
    """
    
    # Session identification
    session_id: UUID = Field(default_factory=uuid4, description="Unique session identifier")
    user_id: UUID = Field(..., description="User ID for the upload session")
    
    # Upload tracking
    total_files: int = Field(default=0, ge=0, description="Total files in session")
    completed_files: int = Field(default=0, ge=0, description="Successfully completed uploads")
    failed_files: int = Field(default=0, ge=0, description="Failed uploads")
    cancelled_files: int = Field(default=0, ge=0, description="Cancelled uploads")
    
    # Quota management
    quota_remaining: int = Field(..., ge=0, description="Remaining upload quota in bytes")
    quota_limit: int = Field(..., ge=0, description="Total quota limit in bytes")
    quota_used: int = Field(default=0, ge=0, description="Quota used in this session")
    
    # Dashboard context (JSON serialization support)
    dashboard_context: Optional[Dict[str, Any]] = Field(default=None, description="Dashboard navigation context")
    
    # Session metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = Field(default=None, description="Session expiration time")
    
    # Session settings
    auto_analyze: bool = Field(default=True, description="Whether to auto-analyze uploaded files")
    store_in_s3: bool = Field(default=True, description="Whether to store files in S3")
    
    @model_validator(mode='after')
    def validate_session_consistency(self):
        """Validate session consistency"""
        if self.completed_files + self.failed_files + self.cancelled_files > self.total_files:
            raise ValueError("Total completed/failed/cancelled files cannot exceed total files")
        
        if self.quota_used > self.quota_limit:
            raise ValueError("Quota used cannot exceed quota limit")
        
        if self.quota_remaining != (self.quota_limit - self.quota_used):
            raise ValueError("Quota remaining must equal quota limit minus quota used")
        
        return self
    
    def add_file_to_session(self, file_size: int) -> bool:
        """Add a file to the session and update quota"""
        if self.quota_remaining < file_size:
            return False
        
        self.total_files += 1
        self.quota_used += file_size
        self.quota_remaining -= file_size
        self.last_activity = datetime.now(timezone.utc)
        return True
    
    def mark_file_completed(self) -> None:
        """Mark a file as completed"""
        self.completed_files += 1
        self.last_activity = datetime.now(timezone.utc)
    
    def mark_file_failed(self) -> None:
        """Mark a file as failed"""
        self.failed_files += 1
        self.last_activity = datetime.now(timezone.utc)
    
    def mark_file_cancelled(self) -> None:
        """Mark a file as cancelled"""
        self.cancelled_files += 1
        self.last_activity = datetime.now(timezone.utc)
    
    def get_session_progress(self) -> Dict[str, Any]:
        """Get session progress summary"""
        return {
            "session_id": str(self.session_id),
            "total_files": self.total_files,
            "completed_files": self.completed_files,
            "failed_files": self.failed_files,
            "cancelled_files": self.cancelled_files,
            "completion_percentage": (self.completed_files / self.total_files * 100) if self.total_files > 0 else 0,
            "quota_remaining": self.quota_remaining,
            "quota_used": self.quota_used,
            "quota_percentage": (self.quota_used / self.quota_limit * 100) if self.quota_limit > 0 else 0
        }


class UploadProgress(BaseModel):
    """
    Upload progress model for tracking individual file upload progress.
    Provides detailed progress information for real-time updates.
    """
    
    # Progress identification
    upload_id: UUID = Field(..., description="Upload identifier")
    session_id: UUID = Field(..., description="Session identifier")
    
    # Progress metrics
    percentage: float = Field(..., ge=0.0, le=100.0, description="Upload percentage (0-100)")
    bytes_uploaded: int = Field(..., ge=0, description="Bytes uploaded so far")
    bytes_total: int = Field(..., ge=0, description="Total bytes to upload")
    
    # Speed and timing
    upload_speed: Optional[float] = Field(default=None, ge=0, description="Upload speed in bytes/second")
    estimated_completion: Optional[datetime] = Field(default=None, description="Estimated completion time")
    time_elapsed: Optional[float] = Field(default=None, ge=0, description="Time elapsed in seconds")
    
    # Status
    status: UploadProgressStatusEnum = Field(..., description="Current progress status")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    
    # File information
    filename: str = Field(..., description="Filename being uploaded")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    
    # Timestamps
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @model_validator(mode='after')
    def validate_progress_consistency(self):
        """Validate progress consistency"""
        if self.bytes_uploaded > self.bytes_total:
            raise ValueError("Bytes uploaded cannot exceed bytes total")
        
        if self.bytes_total > 0:
            calculated_percentage = (self.bytes_uploaded / self.bytes_total) * 100
            if abs(calculated_percentage - self.percentage) > 0.1:  # Allow small floating point differences
                raise ValueError("Percentage must match bytes uploaded / bytes total")
        
        return self
    
    def update_progress(self, bytes_uploaded: int, upload_speed: Optional[float] = None) -> None:
        """Update upload progress"""
        self.bytes_uploaded = bytes_uploaded
        self.percentage = (bytes_uploaded / self.bytes_total) * 100 if self.bytes_total > 0 else 0
        self.upload_speed = upload_speed
        self.updated_at = datetime.now(timezone.utc)
        
        # Calculate estimated completion if we have speed
        if upload_speed and upload_speed > 0:
            remaining_bytes = self.bytes_total - bytes_uploaded
            remaining_seconds = remaining_bytes / upload_speed
            self.estimated_completion = datetime.now(timezone.utc).replace(microsecond=0) + \
                datetime.timedelta(seconds=remaining_seconds)
        
        # Calculate time elapsed
        elapsed = self.updated_at - self.started_at
        self.time_elapsed = elapsed.total_seconds()
    
    def mark_completed(self) -> None:
        """Mark upload as completed"""
        self.bytes_uploaded = self.bytes_total
        self.percentage = 100.0
        self.status = UploadProgressStatusEnum.COMPLETED
        self.updated_at = datetime.now(timezone.utc)
        
        # Calculate final time elapsed
        elapsed = self.updated_at - self.started_at
        self.time_elapsed = elapsed.total_seconds()
    
    def mark_failed(self, error_message: str) -> None:
        """Mark upload as failed"""
        self.status = UploadProgressStatusEnum.FAILED
        self.error_message = error_message
        self.updated_at = datetime.now(timezone.utc)
        
        # Calculate time elapsed
        elapsed = self.updated_at - self.started_at
        self.time_elapsed = elapsed.total_seconds()
    
    def mark_cancelled(self) -> None:
        """Mark upload as cancelled"""
        self.status = UploadProgressStatusEnum.CANCELLED
        self.updated_at = datetime.now(timezone.utc)
        
        # Calculate time elapsed
        elapsed = self.updated_at - self.started_at
        self.time_elapsed = elapsed.total_seconds()


class UploadProgressEvent(BaseModel):
    """
    Upload progress event model for WebSocket compatibility.
    Provides real-time progress updates for dashboard integration.
    """
    
    # Event identification
    event_type: UploadEventTypeEnum = Field(..., description="Type of progress event")
    upload_id: UUID = Field(..., description="Upload identifier")
    session_id: UUID = Field(..., description="Session identifier")
    user_id: Optional[UUID] = Field(default=None, description="User ID for event routing")
    
    # Progress data
    progress: UploadProgress = Field(..., description="Current progress information")
    
    # Event metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    
    # Additional context
    dashboard_context: Optional[Dict[str, Any]] = Field(default=None, description="Dashboard context for event routing")
    
    def to_websocket_message(self) -> Dict[str, Any]:
        """Convert to WebSocket message format"""
        return {
            "type": "upload_progress",
            "event_type": self.event_type,
            "event_id": str(self.event_id),
            "upload_id": str(self.upload_id),
            "session_id": str(self.session_id),
            "user_id": str(self.user_id) if self.user_id else None,
            "timestamp": self.timestamp.isoformat(),
            "progress": {
                "percentage": self.progress.percentage,
                "bytes_uploaded": self.progress.bytes_uploaded,
                "bytes_total": self.progress.bytes_total,
                "upload_speed": self.progress.upload_speed,
                "estimated_completion": self.progress.estimated_completion.isoformat() if self.progress.estimated_completion else None,
                "status": self.progress.status,
                "filename": self.progress.filename,
                "error_message": self.progress.error_message
            },
            "dashboard_context": self.dashboard_context
        }


