#!/usr/bin/env python3
"""
WebSocket Event Schemas
Pydantic models for WebSocket events used for real-time upload and processing feedback
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from uuid import UUID
from enum import Enum


class WebSocketEventType(str, Enum):
    """Enumeration of WebSocket event types."""
    UPLOAD_STARTED = "upload_started"
    UPLOAD_PROGRESS = "upload_progress"
    UPLOAD_COMPLETED = "upload_completed"
    UPLOAD_FAILED = "upload_failed"
    PROCESSING_STARTED = "processing_started"
    PROCESSING_PROGRESS = "processing_progress"
    PROCESSING_COMPLETED = "processing_completed"
    PROCESSING_FAILED = "processing_failed"
    DUPLICATE_DETECTED = "duplicate_detected"
    SESSION_EXPIRED = "session_expired"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class UploadStatus(str, Enum):
    """Enumeration of upload statuses."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingStatus(str, Enum):
    """Enumeration of processing statuses."""
    PENDING = "pending"
    STARTED = "started"
    ANALYZING = "analyzing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BaseWebSocketEvent(BaseModel):
    """Base class for all WebSocket events."""
    event_type: WebSocketEventType = Field(..., description="Type of WebSocket event")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp in UTC"
    )
    event_id: UUID = Field(default_factory=lambda: UUID(), description="Unique event identifier")


class UploadStartedEvent(BaseWebSocketEvent):
    """Event fired when upload starts."""
    event_type: WebSocketEventType = Field(default=WebSocketEventType.UPLOAD_STARTED)
    upload_id: UUID = Field(..., description="Unique upload identifier")
    session_id: Optional[str] = Field(None, description="Upload session ID for chunked uploads")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="File MIME type")
    user_id: Optional[str] = Field(None, description="User ID who initiated upload")
    chunked_upload: bool = Field(False, description="Whether this is a chunked upload")
    total_chunks: Optional[int] = Field(None, description="Total number of chunks")


class UploadProgressEvent(BaseWebSocketEvent):
    """Event fired during upload progress."""
    event_type: WebSocketEventType = Field(default=WebSocketEventType.UPLOAD_PROGRESS)
    upload_id: UUID = Field(..., description="Unique upload identifier")
    session_id: Optional[str] = Field(None, description="Upload session ID")
    progress_percentage: float = Field(..., ge=0.0, le=100.0, description="Upload progress percentage")
    bytes_uploaded: int = Field(..., ge=0, description="Number of bytes uploaded")
    total_bytes: int = Field(..., ge=0, description="Total number of bytes to upload")
    upload_speed_mbps: Optional[float] = Field(None, description="Current upload speed in Mbps")
    estimated_time_remaining: Optional[int] = Field(None, description="Estimated time remaining in seconds")
    chunk_index: Optional[int] = Field(None, description="Current chunk index for chunked uploads")
    total_chunks: Optional[int] = Field(None, description="Total number of chunks")


class UploadCompletedEvent(BaseWebSocketEvent):
    """Event fired when upload completes successfully."""
    event_type: WebSocketEventType = Field(default=WebSocketEventType.UPLOAD_COMPLETED)
    upload_id: UUID = Field(..., description="Unique upload identifier")
    session_id: Optional[str] = Field(None, description="Upload session ID")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="Final file size in bytes")
    file_hash: str = Field(..., description="File content hash")
    upload_duration_seconds: float = Field(..., description="Total upload duration in seconds")
    average_speed_mbps: Optional[float] = Field(None, description="Average upload speed in Mbps")
    processing_job_id: Optional[str] = Field(None, description="Processing job ID if processing initiated")


class UploadFailedEvent(BaseWebSocketEvent):
    """Event fired when upload fails."""
    event_type: WebSocketEventType = Field(default=WebSocketEventType.UPLOAD_FAILED)
    upload_id: UUID = Field(..., description="Unique upload identifier")
    session_id: Optional[str] = Field(None, description="Upload session ID")
    filename: str = Field(..., description="Original filename")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    retry_possible: bool = Field(False, description="Whether upload can be retried")


class ProcessingInitiatedEvent(BaseWebSocketEvent):
    """Event fired when processing is initiated."""
    event_type: WebSocketEventType = Field(default=WebSocketEventType.PROCESSING_STARTED)
    upload_id: UUID = Field(..., description="Unique upload identifier")
    analysis_id: UUID = Field(..., description="Unique analysis identifier")
    processing_job_id: str = Field(..., description="Processing job ID")
    filename: str = Field(..., description="Original filename")
    file_hash: str = Field(..., description="File content hash")
    model_type: str = Field(..., description="Model type being used for analysis")
    priority: int = Field(..., ge=1, le=10, description="Processing priority")
    estimated_completion_time: Optional[datetime] = Field(None, description="Estimated completion time")
    duplicate_result: Optional[Dict[str, Any]] = Field(None, description="Duplicate detection result if applicable")


class ProcessingProgressEvent(BaseWebSocketEvent):
    """Event fired during processing progress."""
    event_type: WebSocketEventType = Field(default=WebSocketEventType.PROCESSING_PROGRESS)
    upload_id: UUID = Field(..., description="Unique upload identifier")
    analysis_id: UUID = Field(..., description="Unique analysis identifier")
    processing_job_id: str = Field(..., description="Processing job ID")
    progress_percentage: float = Field(..., ge=0.0, le=100.0, description="Processing progress percentage")
    current_stage: str = Field(..., description="Current processing stage")
    stage_message: Optional[str] = Field(None, description="Current stage message")
    frames_processed: Optional[int] = Field(None, description="Number of frames processed")
    total_frames: Optional[int] = Field(None, description="Total number of frames")
    estimated_time_remaining: Optional[int] = Field(None, description="Estimated time remaining in seconds")
    processing_speed_fps: Optional[float] = Field(None, description="Processing speed in frames per second")


class ProcessingCompletedEvent(BaseWebSocketEvent):
    """Event fired when processing completes successfully."""
    event_type: WebSocketEventType = Field(default=WebSocketEventType.PROCESSING_COMPLETED)
    upload_id: UUID = Field(..., description="Unique upload identifier")
    analysis_id: UUID = Field(..., description="Unique analysis identifier")
    processing_job_id: str = Field(..., description="Processing job ID")
    filename: str = Field(..., description="Original filename")
    file_hash: str = Field(..., description="File content hash")
    processing_duration_seconds: float = Field(..., description="Total processing duration in seconds")
    result: Dict[str, Any] = Field(..., description="Analysis result")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Overall confidence score")
    is_fake: Optional[bool] = Field(None, description="Whether the video is detected as fake")
    blockchain_hash: Optional[str] = Field(None, description="Blockchain hash for result verification")
    frames_analyzed: Optional[int] = Field(None, description="Total number of frames analyzed")
    model_version: Optional[str] = Field(None, description="Model version used")


class ProcessingFailedEvent(BaseWebSocketEvent):
    """Event fired when processing fails."""
    event_type: WebSocketEventType = Field(default=WebSocketEventType.PROCESSING_FAILED)
    upload_id: UUID = Field(..., description="Unique upload identifier")
    analysis_id: UUID = Field(..., description="Unique analysis identifier")
    processing_job_id: str = Field(..., description="Processing job ID")
    filename: str = Field(..., description="Original filename")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    processing_duration_seconds: Optional[float] = Field(None, description="Processing duration before failure")
    retry_possible: bool = Field(False, description="Whether processing can be retried")


class DuplicateDetectedEvent(BaseWebSocketEvent):
    """Event fired when a duplicate file is detected."""
    event_type: WebSocketEventType = Field(default=WebSocketEventType.DUPLICATE_DETECTED)
    upload_id: UUID = Field(..., description="Unique upload identifier")
    filename: str = Field(..., description="Original filename")
    file_hash: str = Field(..., description="File content hash")
    duplicate_upload_id: UUID = Field(..., description="ID of the original upload")
    duplicate_analysis_id: UUID = Field(..., description="ID of the original analysis")
    cached_result: Dict[str, Any] = Field(..., description="Cached analysis result")
    processing_time_saved_seconds: Optional[float] = Field(None, description="Processing time saved by using cache")


class SessionExpiredEvent(BaseWebSocketEvent):
    """Event fired when an upload session expires."""
    event_type: WebSocketEventType = Field(default=WebSocketEventType.SESSION_EXPIRED)
    session_id: str = Field(..., description="Expired session ID")
    upload_id: Optional[UUID] = Field(None, description="Associated upload ID if any")
    filename: Optional[str] = Field(None, description="Associated filename if any")
    expired_at: datetime = Field(..., description="Session expiration timestamp")
    chunks_uploaded: Optional[int] = Field(None, description="Number of chunks uploaded before expiry")
    total_chunks: Optional[int] = Field(None, description="Total number of chunks")
    cleanup_completed: bool = Field(True, description="Whether cleanup was completed")


class WebSocketErrorEvent(BaseWebSocketEvent):
    """Event fired when a WebSocket error occurs."""
    event_type: WebSocketEventType = Field(default=WebSocketEventType.ERROR)
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    upload_id: Optional[UUID] = Field(None, description="Associated upload ID if any")
    session_id: Optional[str] = Field(None, description="Associated session ID if any")
    recoverable: bool = Field(False, description="Whether the error is recoverable")


class WebSocketHeartbeatEvent(BaseWebSocketEvent):
    """Event fired as a heartbeat to keep connection alive."""
    event_type: WebSocketEventType = Field(default=WebSocketEventType.HEARTBEAT)
    server_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Server timestamp"
    )
    connection_id: Optional[str] = Field(None, description="WebSocket connection ID")
    active_uploads: Optional[int] = Field(None, description="Number of active uploads")
    active_processing_jobs: Optional[int] = Field(None, description="Number of active processing jobs")


# Union type for all WebSocket events
WebSocketEvent = (
    UploadStartedEvent |
    UploadProgressEvent |
    UploadCompletedEvent |
    UploadFailedEvent |
    ProcessingInitiatedEvent |
    ProcessingProgressEvent |
    ProcessingCompletedEvent |
    ProcessingFailedEvent |
    DuplicateDetectedEvent |
    SessionExpiredEvent |
    WebSocketErrorEvent |
    WebSocketHeartbeatEvent
)


class WebSocketMessage(BaseModel):
    """Wrapper for WebSocket messages."""
    event: WebSocketEvent = Field(..., description="WebSocket event")
    client_id: Optional[str] = Field(None, description="Client identifier")
    room: Optional[str] = Field(None, description="WebSocket room for targeted messaging")


class WebSocketConnectionInfo(BaseModel):
    """Information about a WebSocket connection."""
    connection_id: str = Field(..., description="Unique connection identifier")
    client_id: Optional[str] = Field(None, description="Client identifier")
    user_id: Optional[str] = Field(None, description="Authenticated user ID")
    connected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Connection timestamp"
    )
    last_heartbeat: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last heartbeat timestamp"
    )
    active_uploads: List[UUID] = Field(default_factory=list, description="List of active upload IDs")
    active_processing_jobs: List[str] = Field(default_factory=list, description="List of active processing job IDs")
    rooms: List[str] = Field(default_factory=list, description="List of subscribed rooms")


# Event factory functions
def create_upload_started_event(
    upload_id: UUID,
    filename: str,
    file_size: int,
    content_type: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    chunked_upload: bool = False,
    total_chunks: Optional[int] = None
) -> UploadStartedEvent:
    """Create an upload started event."""
    return UploadStartedEvent(
        upload_id=upload_id,
        session_id=session_id,
        filename=filename,
        file_size=file_size,
        content_type=content_type,
        user_id=user_id,
        chunked_upload=chunked_upload,
        total_chunks=total_chunks
    )


def create_upload_progress_event(
    upload_id: UUID,
    progress_percentage: float,
    bytes_uploaded: int,
    total_bytes: int,
    session_id: Optional[str] = None,
    upload_speed_mbps: Optional[float] = None,
    estimated_time_remaining: Optional[int] = None,
    chunk_index: Optional[int] = None,
    total_chunks: Optional[int] = None
) -> UploadProgressEvent:
    """Create an upload progress event."""
    return UploadProgressEvent(
        upload_id=upload_id,
        session_id=session_id,
        progress_percentage=progress_percentage,
        bytes_uploaded=bytes_uploaded,
        total_bytes=total_bytes,
        upload_speed_mbps=upload_speed_mbps,
        estimated_time_remaining=estimated_time_remaining,
        chunk_index=chunk_index,
        total_chunks=total_chunks
    )


def create_processing_initiated_event(
    upload_id: UUID,
    analysis_id: UUID,
    processing_job_id: str,
    filename: str,
    file_hash: str,
    model_type: str,
    priority: int,
    estimated_completion_time: Optional[datetime] = None,
    duplicate_result: Optional[Dict[str, Any]] = None
) -> ProcessingInitiatedEvent:
    """Create a processing initiated event."""
    return ProcessingInitiatedEvent(
        upload_id=upload_id,
        analysis_id=analysis_id,
        processing_job_id=processing_job_id,
        filename=filename,
        file_hash=file_hash,
        model_type=model_type,
        priority=priority,
        estimated_completion_time=estimated_completion_time,
        duplicate_result=duplicate_result
    )


def create_duplicate_detected_event(
    upload_id: UUID,
    filename: str,
    file_hash: str,
    duplicate_upload_id: UUID,
    duplicate_analysis_id: UUID,
    cached_result: Dict[str, Any],
    processing_time_saved_seconds: Optional[float] = None
) -> DuplicateDetectedEvent:
    """Create a duplicate detected event."""
    return DuplicateDetectedEvent(
        upload_id=upload_id,
        filename=filename,
        file_hash=file_hash,
        duplicate_upload_id=duplicate_upload_id,
        duplicate_analysis_id=duplicate_analysis_id,
        cached_result=cached_result,
        processing_time_saved_seconds=processing_time_saved_seconds
    )


# Export main components
__all__ = [
    'WebSocketEventType',
    'UploadStatus',
    'ProcessingStatus',
    'BaseWebSocketEvent',
    'UploadStartedEvent',
    'UploadProgressEvent',
    'UploadCompletedEvent',
    'UploadFailedEvent',
    'ProcessingInitiatedEvent',
    'ProcessingProgressEvent',
    'ProcessingCompletedEvent',
    'ProcessingFailedEvent',
    'DuplicateDetectedEvent',
    'SessionExpiredEvent',
    'WebSocketErrorEvent',
    'WebSocketHeartbeatEvent',
    'WebSocketEvent',
    'WebSocketMessage',
    'WebSocketConnectionInfo',
    'create_upload_started_event',
    'create_upload_progress_event',
    'create_processing_initiated_event',
    'create_duplicate_detected_event'
]
