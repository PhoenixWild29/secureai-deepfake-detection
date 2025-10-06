#!/usr/bin/env python3
"""
Analysis Event Models
Pydantic models for WebSocket real-time analysis updates
"""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, validator
from enum import Enum


class AnalysisStage(str, Enum):
    """Analysis processing stages."""
    INITIALIZING = "initializing"
    UPLOADING = "uploading"
    FRAME_EXTRACTION = "frame_extraction"
    FEATURE_EXTRACTION = "feature_extraction"
    MODEL_INFERENCE = "model_inference"
    POST_PROCESSING = "post_processing"
    BLOCKCHAIN_SUBMISSION = "blockchain_submission"
    COMPLETED = "completed"
    FAILED = "failed"


class EventType(str, Enum):
    """WebSocket event types."""
    STATUS_UPDATE = "status_update"
    RESULT_UPDATE = "result_update"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class StatusUpdate(BaseModel):
    """
    Status update event for real-time analysis progress.
    """
    event_type: EventType = Field(default=EventType.STATUS_UPDATE, description="Event type")
    task_id: str = Field(..., description="Celery task ID")
    analysis_id: str = Field(..., description="Analysis ID")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress percentage (0.0-1.0)")
    current_stage: AnalysisStage = Field(..., description="Current processing stage")
    message: str = Field(..., description="Status message")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Event timestamp")
    
    @validator('analysis_id')
    def validate_analysis_id(cls, v):
        """Validate analysis ID format."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('analysis_id must be a valid UUID')
    
    @validator('task_id')
    def validate_task_id(cls, v):
        """Validate task ID format."""
        if not v or len(v.strip()) == 0:
            raise ValueError('task_id cannot be empty')
        return v.strip()
    
    @validator('message')
    def validate_message(cls, v):
        """Validate message content."""
        if not v or len(v.strip()) == 0:
            raise ValueError('message cannot be empty')
        return v.strip()


class SuspiciousRegion(BaseModel):
    """
    Suspicious region detected in video analysis.
    """
    frame_number: int = Field(..., ge=0, description="Frame number")
    x: float = Field(..., ge=0.0, le=1.0, description="Normalized x coordinate")
    y: float = Field(..., ge=0.0, le=1.0, description="Normalized y coordinate")
    width: float = Field(..., ge=0.0, le=1.0, description="Normalized width")
    height: float = Field(..., ge=0.0, le=1.0, description="Normalized height")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    region_type: str = Field(..., description="Type of suspicious region")


class ResultUpdate(BaseModel):
    """
    Result update event for completed analysis.
    """
    event_type: EventType = Field(default=EventType.RESULT_UPDATE, description="Event type")
    analysis_id: str = Field(..., description="Analysis ID")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    frames_processed: int = Field(..., ge=0, description="Number of frames processed")
    total_frames: int = Field(..., ge=0, description="Total frames in video")
    suspicious_regions: List[SuspiciousRegion] = Field(default=[], description="Detected suspicious regions")
    blockchain_hash: Optional[str] = Field(None, description="Blockchain verification hash")
    processing_time_ms: int = Field(..., ge=0, description="Total processing time in milliseconds")
    is_fake: bool = Field(..., description="Whether video is detected as fake")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Event timestamp")
    
    @validator('analysis_id')
    def validate_analysis_id(cls, v):
        """Validate analysis ID format."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('analysis_id must be a valid UUID')
    
    @validator('total_frames')
    def validate_total_frames(cls, v, values):
        """Validate total frames is greater than or equal to processed frames."""
        if 'frames_processed' in values and v < values['frames_processed']:
            raise ValueError('total_frames must be >= frames_processed')
        return v
    
    @validator('blockchain_hash')
    def validate_blockchain_hash(cls, v):
        """Validate blockchain hash format."""
        if v is not None:
            if not v or len(v.strip()) == 0:
                return None
            # Basic hash validation (should be hex string)
            try:
                int(v, 16)
                return v.strip()
            except ValueError:
                raise ValueError('blockchain_hash must be a valid hexadecimal string')
        return v


class ErrorEvent(BaseModel):
    """
    Error event for analysis failures.
    """
    event_type: EventType = Field(default=EventType.ERROR, description="Event type")
    analysis_id: str = Field(..., description="Analysis ID")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error message")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Event timestamp")
    
    @validator('analysis_id')
    def validate_analysis_id(cls, v):
        """Validate analysis ID format."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('analysis_id must be a valid UUID')


class HeartbeatEvent(BaseModel):
    """
    Heartbeat event for connection health monitoring.
    """
    event_type: EventType = Field(default=EventType.HEARTBEAT, description="Event type")
    message: str = Field(default="ping", description="Heartbeat message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Event timestamp")


class WebSocketMessage(BaseModel):
    """
    Generic WebSocket message wrapper.
    """
    event_type: EventType = Field(..., description="Event type")
    data: Dict[str, Any] = Field(..., description="Event data")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Message timestamp")


class ConnectionInfo(BaseModel):
    """
    WebSocket connection information.
    """
    analysis_id: str = Field(..., description="Analysis ID")
    user_id: Optional[str] = Field(None, description="User ID")
    connected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Connection timestamp")
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last heartbeat timestamp")
    is_active: bool = Field(default=True, description="Whether connection is active")
    
    @validator('analysis_id')
    def validate_analysis_id(cls, v):
        """Validate analysis ID format."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('analysis_id must be a valid UUID')


# Utility functions for event creation
def create_status_update(
    task_id: str,
    analysis_id: str,
    progress: float,
    current_stage: AnalysisStage,
    message: str,
    estimated_completion: Optional[datetime] = None,
    error: Optional[str] = None
) -> StatusUpdate:
    """Create a status update event."""
    return StatusUpdate(
        task_id=task_id,
        analysis_id=analysis_id,
        progress=progress,
        current_stage=current_stage,
        message=message,
        estimated_completion=estimated_completion,
        error=error
    )


def create_result_update(
    analysis_id: str,
    confidence_score: float,
    frames_processed: int,
    total_frames: int,
    suspicious_regions: List[SuspiciousRegion] = None,
    blockchain_hash: Optional[str] = None,
    processing_time_ms: int = 0,
    is_fake: bool = False
) -> ResultUpdate:
    """Create a result update event."""
    return ResultUpdate(
        analysis_id=analysis_id,
        confidence_score=confidence_score,
        frames_processed=frames_processed,
        total_frames=total_frames,
        suspicious_regions=suspicious_regions or [],
        blockchain_hash=blockchain_hash,
        processing_time_ms=processing_time_ms,
        is_fake=is_fake
    )


def create_error_event(
    analysis_id: str,
    error_code: str,
    error_message: str,
    error_details: Optional[Dict[str, Any]] = None
) -> ErrorEvent:
    """Create an error event."""
    return ErrorEvent(
        analysis_id=analysis_id,
        error_code=error_code,
        error_message=error_message,
        error_details=error_details
    )


def create_heartbeat_event(message: str = "ping") -> HeartbeatEvent:
    """Create a heartbeat event."""
    return HeartbeatEvent(message=message)


# Export
__all__ = [
    'AnalysisStage',
    'EventType',
    'StatusUpdate',
    'SuspiciousRegion',
    'ResultUpdate',
    'ErrorEvent',
    'HeartbeatEvent',
    'WebSocketMessage',
    'ConnectionInfo',
    'create_status_update',
    'create_result_update',
    'create_error_event',
    'create_heartbeat_event'
]
