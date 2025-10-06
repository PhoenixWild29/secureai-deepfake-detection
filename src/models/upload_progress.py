#!/usr/bin/env python3
"""
Upload Progress Models
Pydantic models for upload progress tracking and WebSocket communication
"""

from typing import Optional, Dict, Any, Union
from datetime import datetime, timezone
from uuid import UUID
from pydantic import BaseModel, Field, validator
from enum import Enum


class ProgressStatus(str, Enum):
    """Upload progress status enumeration"""
    UPLOADING = "uploading"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class WebSocketEventType(str, Enum):
    """WebSocket event type enumeration"""
    UPLOAD_PROGRESS = "upload_progress"
    UPLOAD_COMPLETE = "upload_complete"
    UPLOAD_ERROR = "upload_error"
    UPLOAD_CANCELLED = "upload_cancelled"


class UploadProgress(BaseModel):
    """
    Main upload progress data model.
    Represents the current state of a file upload operation.
    """
    
    # Session and identification
    session_id: UUID = Field(
        ...,
        description="Upload session ID"
    )
    
    user_id: UUID = Field(
        ...,
        description="User ID who initiated the upload"
    )
    
    # Progress metrics
    percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Upload progress percentage (0-100)"
    )
    
    bytes_uploaded: int = Field(
        ...,
        ge=0,
        description="Number of bytes uploaded"
    )
    
    total_bytes: int = Field(
        ...,
        ge=0,
        description="Total file size in bytes"
    )
    
    upload_speed: float = Field(
        ...,
        ge=0.0,
        description="Current upload speed in bytes per second"
    )
    
    # Time estimates
    estimated_completion: Optional[datetime] = Field(
        default=None,
        description="Estimated completion timestamp"
    )
    
    elapsed_time: float = Field(
        ...,
        ge=0.0,
        description="Elapsed time since upload started in seconds"
    )
    
    # Status and metadata
    status: ProgressStatus = Field(
        ...,
        description="Current upload status"
    )
    
    filename: Optional[str] = Field(
        default=None,
        description="Original filename being uploaded"
    )
    
    content_type: Optional[str] = Field(
        default=None,
        description="MIME content type of the file"
    )
    
    # Completion data (when status is COMPLETED)
    video_id: Optional[UUID] = Field(
        default=None,
        description="Video ID after successful upload"
    )
    
    analysis_id: Optional[UUID] = Field(
        default=None,
        description="Analysis ID after successful upload"
    )
    
    redirect_url: Optional[str] = Field(
        default=None,
        description="Redirect URL after successful upload"
    )
    
    # Error data (when status is ERROR)
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if upload failed"
    )
    
    error_code: Optional[str] = Field(
        default=None,
        description="Error code for programmatic handling"
    )
    
    # Timestamps
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When upload started"
    )
    
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When progress was last updated"
    )
    
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When upload completed"
    )
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional progress metadata"
    )
    
    @validator('percentage')
    def validate_percentage(cls, v, values):
        """Validate percentage calculation"""
        if 'bytes_uploaded' in values and 'total_bytes' in values:
            calculated_percentage = (values['bytes_uploaded'] / values['total_bytes']) * 100
            # Allow small tolerance for floating point precision
            if abs(v - calculated_percentage) > 0.1:
                return calculated_percentage
        return v
    
    @validator('upload_speed')
    def validate_upload_speed(cls, v, values):
        """Validate upload speed calculation"""
        if 'bytes_uploaded' in values and 'elapsed_time' in values:
            if values['elapsed_time'] > 0:
                calculated_speed = values['bytes_uploaded'] / values['elapsed_time']
                # Use calculated speed if provided speed is 0 or significantly different
                if v == 0 or abs(v - calculated_speed) > calculated_speed * 0.1:
                    return calculated_speed
        return v
    
    def calculate_estimated_completion(self) -> Optional[datetime]:
        """Calculate estimated completion time based on current progress"""
        if self.status == ProgressStatus.COMPLETED:
            return self.completed_at
        
        if self.percentage >= 100 or self.upload_speed <= 0:
            return None
        
        remaining_bytes = self.total_bytes - self.bytes_uploaded
        if remaining_bytes <= 0:
            return datetime.now(timezone.utc)
        
        estimated_seconds = remaining_bytes / self.upload_speed
        return datetime.now(timezone.utc).replace(microsecond=0) + datetime.timedelta(seconds=estimated_seconds)
    
    def update_progress(
        self,
        bytes_uploaded: int,
        upload_speed: Optional[float] = None,
        status: Optional[ProgressStatus] = None
    ) -> 'UploadProgress':
        """Update progress with new data"""
        # Calculate new percentage
        new_percentage = (bytes_uploaded / self.total_bytes) * 100 if self.total_bytes > 0 else 0
        
        # Calculate elapsed time
        elapsed_time = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        
        # Use provided upload speed or calculate from progress
        if upload_speed is None and elapsed_time > 0:
            upload_speed = bytes_uploaded / elapsed_time
        
        # Update fields
        update_data = {
            'bytes_uploaded': bytes_uploaded,
            'percentage': new_percentage,
            'upload_speed': upload_speed or self.upload_speed,
            'elapsed_time': elapsed_time,
            'last_updated': datetime.now(timezone.utc)
        }
        
        if status:
            update_data['status'] = status
            if status == ProgressStatus.COMPLETED:
                update_data['completed_at'] = datetime.now(timezone.utc)
                update_data['percentage'] = 100.0
        
        # Calculate estimated completion
        estimated_completion = self.calculate_estimated_completion()
        if estimated_completion:
            update_data['estimated_completion'] = estimated_completion
        
        return self.copy(update=update_data)


class WebSocketEvent(BaseModel):
    """
    WebSocket event model for real-time communication.
    Used for broadcasting upload progress updates.
    """
    
    event_type: WebSocketEventType = Field(
        ...,
        description="Type of WebSocket event"
    )
    
    session_id: UUID = Field(
        ...,
        description="Upload session ID"
    )
    
    user_id: UUID = Field(
        ...,
        description="User ID for targeted broadcasting"
    )
    
    data: Dict[str, Any] = Field(
        ...,
        description="Event-specific data payload"
    )
    
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the event was generated"
    )
    
    # Optional targeting
    target_connections: Optional[list[str]] = Field(
        default=None,
        description="Specific WebSocket connection IDs to target"
    )
    
    # Optional metadata
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional event metadata"
    )


class UploadProgressEvent(BaseModel):
    """
    Specific event model for upload progress updates.
    Contains progress data for WebSocket broadcasting.
    """
    
    session_id: UUID = Field(
        ...,
        description="Upload session ID"
    )
    
    percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Upload progress percentage"
    )
    
    bytes_uploaded: int = Field(
        ...,
        ge=0,
        description="Bytes uploaded"
    )
    
    total_bytes: int = Field(
        ...,
        ge=0,
        description="Total file size"
    )
    
    upload_speed: float = Field(
        ...,
        ge=0.0,
        description="Upload speed in bytes per second"
    )
    
    estimated_completion: Optional[datetime] = Field(
        default=None,
        description="Estimated completion time"
    )
    
    status: ProgressStatus = Field(
        ...,
        description="Current upload status"
    )
    
    filename: Optional[str] = Field(
        default=None,
        description="Filename being uploaded"
    )
    
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp"
    )


class UploadCompleteEvent(BaseModel):
    """
    Event model for upload completion.
    Contains completion data for WebSocket broadcasting.
    """
    
    session_id: UUID = Field(
        ...,
        description="Upload session ID"
    )
    
    video_id: UUID = Field(
        ...,
        description="Video ID after successful upload"
    )
    
    analysis_id: Optional[UUID] = Field(
        default=None,
        description="Analysis ID after successful upload"
    )
    
    redirect_url: str = Field(
        ...,
        description="Redirect URL after successful upload"
    )
    
    filename: str = Field(
        ...,
        description="Uploaded filename"
    )
    
    file_size: int = Field(
        ...,
        ge=0,
        description="File size in bytes"
    )
    
    upload_duration: float = Field(
        ...,
        ge=0.0,
        description="Total upload duration in seconds"
    )
    
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Completion timestamp"
    )


class UploadErrorEvent(BaseModel):
    """
    Event model for upload errors.
    Contains error data for WebSocket broadcasting.
    """
    
    session_id: UUID = Field(
        ...,
        description="Upload session ID"
    )
    
    error_code: str = Field(
        ...,
        description="Error code for programmatic handling"
    )
    
    error_message: str = Field(
        ...,
        description="Human-readable error message"
    )
    
    error_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    
    filename: Optional[str] = Field(
        default=None,
        description="Filename that failed to upload"
    )
    
    bytes_uploaded: int = Field(
        default=0,
        ge=0,
        description="Bytes uploaded before failure"
    )
    
    total_bytes: int = Field(
        default=0,
        ge=0,
        description="Total file size"
    )
    
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Error timestamp"
    )


class ProgressResponse(BaseModel):
    """
    API response model for progress retrieval endpoint.
    """
    
    session_id: UUID = Field(
        ...,
        description="Upload session ID"
    )
    
    percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Upload progress percentage"
    )
    
    bytes_uploaded: int = Field(
        ...,
        ge=0,
        description="Bytes uploaded"
    )
    
    total_bytes: int = Field(
        ...,
        ge=0,
        description="Total file size"
    )
    
    upload_speed: float = Field(
        ...,
        ge=0.0,
        description="Upload speed in bytes per second"
    )
    
    estimated_completion: Optional[datetime] = Field(
        default=None,
        description="Estimated completion time"
    )
    
    status: ProgressStatus = Field(
        ...,
        description="Current upload status"
    )
    
    filename: Optional[str] = Field(
        default=None,
        description="Filename being uploaded"
    )
    
    # Completion data
    video_id: Optional[UUID] = Field(
        default=None,
        description="Video ID if completed"
    )
    
    analysis_id: Optional[UUID] = Field(
        default=None,
        description="Analysis ID if completed"
    )
    
    redirect_url: Optional[str] = Field(
        default=None,
        description="Redirect URL if completed"
    )
    
    # Error data
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if failed"
    )
    
    error_code: Optional[str] = Field(
        default=None,
        description="Error code if failed"
    )
    
    # Timestamps
    started_at: datetime = Field(
        ...,
        description="When upload started"
    )
    
    last_updated: datetime = Field(
        ...,
        description="When progress was last updated"
    )
    
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When upload completed"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


# Utility functions for progress operations
def create_upload_progress(
    session_id: UUID,
    user_id: UUID,
    total_bytes: int,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> UploadProgress:
    """
    Create a new upload progress instance.
    
    Args:
        session_id: Upload session ID
        user_id: User ID
        total_bytes: Total file size in bytes
        filename: Optional filename
        content_type: Optional content type
        metadata: Optional additional metadata
        
    Returns:
        UploadProgress instance
    """
    return UploadProgress(
        session_id=session_id,
        user_id=user_id,
        total_bytes=total_bytes,
        filename=filename,
        content_type=content_type,
        metadata=metadata,
        percentage=0.0,
        bytes_uploaded=0,
        upload_speed=0.0,
        elapsed_time=0.0,
        status=ProgressStatus.UPLOADING
    )


def create_progress_event(
    progress: UploadProgress
) -> WebSocketEvent:
    """
    Create a WebSocket progress event from upload progress.
    
    Args:
        progress: Upload progress instance
        
    Returns:
        WebSocketEvent for progress update
    """
    progress_data = UploadProgressEvent(
        session_id=progress.session_id,
        percentage=progress.percentage,
        bytes_uploaded=progress.bytes_uploaded,
        total_bytes=progress.total_bytes,
        upload_speed=progress.upload_speed,
        estimated_completion=progress.estimated_completion,
        status=progress.status,
        filename=progress.filename
    )
    
    return WebSocketEvent(
        event_type=WebSocketEventType.UPLOAD_PROGRESS,
        session_id=progress.session_id,
        user_id=progress.user_id,
        data=progress_data.dict()
    )


def create_complete_event(
    progress: UploadProgress,
    video_id: UUID,
    analysis_id: Optional[UUID] = None,
    redirect_url: str = "/dashboard/videos"
) -> WebSocketEvent:
    """
    Create a WebSocket completion event from upload progress.
    
    Args:
        progress: Upload progress instance
        video_id: Video ID after successful upload
        analysis_id: Optional analysis ID
        redirect_url: Redirect URL
        
    Returns:
        WebSocketEvent for upload completion
    """
    complete_data = UploadCompleteEvent(
        session_id=progress.session_id,
        video_id=video_id,
        analysis_id=analysis_id,
        redirect_url=redirect_url,
        filename=progress.filename or "unknown",
        file_size=progress.total_bytes,
        upload_duration=progress.elapsed_time
    )
    
    return WebSocketEvent(
        event_type=WebSocketEventType.UPLOAD_COMPLETE,
        session_id=progress.session_id,
        user_id=progress.user_id,
        data=complete_data.dict()
    )


def create_error_event(
    progress: UploadProgress,
    error_code: str,
    error_message: str,
    error_details: Optional[Dict[str, Any]] = None
) -> WebSocketEvent:
    """
    Create a WebSocket error event from upload progress.
    
    Args:
        progress: Upload progress instance
        error_code: Error code
        error_message: Error message
        error_details: Optional error details
        
    Returns:
        WebSocketEvent for upload error
    """
    error_data = UploadErrorEvent(
        session_id=progress.session_id,
        error_code=error_code,
        error_message=error_message,
        error_details=error_details,
        filename=progress.filename,
        bytes_uploaded=progress.bytes_uploaded,
        total_bytes=progress.total_bytes
    )
    
    return WebSocketEvent(
        event_type=WebSocketEventType.UPLOAD_ERROR,
        session_id=progress.session_id,
        user_id=progress.user_id,
        data=error_data.dict()
    )


# Export main classes and utility functions
__all__ = [
    'UploadProgress',
    'WebSocketEvent',
    'UploadProgressEvent',
    'UploadCompleteEvent',
    'UploadErrorEvent',
    'ProgressResponse',
    'ProgressStatus',
    'WebSocketEventType',
    'create_upload_progress',
    'create_progress_event',
    'create_complete_event',
    'create_error_event'
]
