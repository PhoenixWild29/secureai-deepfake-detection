#!/usr/bin/env python3
"""
Notification Schemas for Real-Time Status Tracking
Pydantic models for WebSocket notification events that extend existing patterns
and provide comprehensive progress information for real-time tracking.
"""

from pydantic import BaseModel, Field, validator
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union
from enum import Enum

# Import existing schemas for consistency
from app.schemas.detection import DetectionStatus, ProcessingStage


class NotificationEventType(str, Enum):
    """Enumeration of notification event types for real-time status tracking."""
    STATUS_UPDATE = "status_update"
    RESULT_UPDATE = "result_update"
    STAGE_TRANSITION = "stage_transition"
    ERROR_NOTIFICATION = "error_notification"
    PROGRESS_UPDATE = "progress_update"
    COMPLETION_NOTIFICATION = "completion_notification"
    HEARTBEAT = "heartbeat"


class NotificationPriority(str, Enum):
    """Enumeration of notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(str, Enum):
    """Enumeration of notification delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


class StageProgressInfo(BaseModel):
    """
    Detailed stage progress information for comprehensive status tracking.
    """
    stage_name: str = Field(..., description="Name of the current processing stage")
    stage_status: str = Field(..., description="Status of the stage (active, completed, failed, skipped)")
    stage_progress_percentage: float = Field(..., ge=0.0, le=100.0, description="Stage completion percentage")
    stage_start_time: Optional[datetime] = Field(None, description="When the stage started")
    stage_estimated_duration_seconds: Optional[float] = Field(None, ge=0.0, description="Estimated duration for this stage")
    frames_processed: Optional[int] = Field(None, ge=0, description="Number of frames processed in this stage")
    total_frames: Optional[int] = Field(None, ge=0, description="Total frames for this stage")
    processing_rate_fps: Optional[float] = Field(None, ge=0.0, description="Processing rate in frames per second")
    resource_usage: Optional[Dict[str, Any]] = Field(None, description="Resource usage metrics")


class ErrorContext(BaseModel):
    """
    Comprehensive error context for error notifications.
    """
    error_type: str = Field(..., description="Type of error (processing, validation, system, network)")
    error_code: str = Field(..., description="Specific error code")
    error_severity: str = Field(default="error", description="Error severity (info, warning, error, critical)")
    affected_stage: Optional[str] = Field(None, description="Processing stage where error occurred")
    recovery_action: Optional[str] = Field(None, description="Action taken to recover from error")
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts allowed")
    context_data: Optional[Dict[str, Any]] = Field(None, description="Additional error context")


class NotificationMetadata(BaseModel):
    """
    Metadata for notification events including delivery and tracking information.
    """
    notification_id: str = Field(..., description="Unique notification identifier")
    source: str = Field(..., description="Source of the notification (analysis_engine, status_tracker, etc.)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Notification timestamp")
    priority: NotificationPriority = Field(default=NotificationPriority.NORMAL, description="Notification priority")
    delivery_status: NotificationStatus = Field(default=NotificationStatus.PENDING, description="Delivery status")
    retry_count: int = Field(default=0, ge=0, description="Number of delivery retry attempts")
    target_clients: Optional[List[str]] = Field(None, description="Specific client IDs to target")
    broadcast_to_all: bool = Field(default=False, description="Whether to broadcast to all connected clients")
    expires_at: Optional[datetime] = Field(None, description="Notification expiration time")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracking related events")


class StatusUpdateNotification(BaseModel):
    """
    Enhanced status update notification extending existing StatusUpdate pattern.
    Provides comprehensive progress information for real-time tracking.
    """
    event_type: NotificationEventType = Field(default=NotificationEventType.STATUS_UPDATE, description="Event type")
    analysis_id: UUID = Field(..., description="Analysis identifier")
    task_id: Optional[str] = Field(None, description="Celery task ID if applicable")
    
    # Core status information
    status: DetectionStatus = Field(..., description="Current analysis status")
    overall_progress: float = Field(..., ge=0.0, le=100.0, description="Overall progress percentage")
    current_stage: ProcessingStage = Field(..., description="Current processing stage")
    stage_progress: StageProgressInfo = Field(..., description="Detailed stage progress information")
    
    # Progress details
    frames_processed: Optional[int] = Field(None, ge=0, description="Total frames processed")
    total_frames: Optional[int] = Field(None, ge=0, description="Total frames to process")
    processing_rate_fps: Optional[float] = Field(None, ge=0.0, description="Current processing rate")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    
    # Messages and context
    message: str = Field(..., description="Human-readable status message")
    detailed_message: Optional[str] = Field(None, description="Detailed status information")
    
    # Performance metrics
    processing_time_seconds: Optional[float] = Field(None, ge=0.0, description="Total processing time so far")
    resource_utilization: Optional[Dict[str, Any]] = Field(None, description="Current resource utilization")
    
    # Error information
    has_errors: bool = Field(default=False, description="Whether any errors have occurred")
    error_count: int = Field(default=0, ge=0, description="Total number of errors encountered")
    last_error: Optional[ErrorContext] = Field(None, description="Information about the last error")
    
    # Notification metadata
    metadata: NotificationMetadata = Field(..., description="Notification metadata")
    
    @validator('overall_progress')
    def validate_overall_progress(cls, v):
        """Validate overall progress is within valid range"""
        if not (0.0 <= v <= 100.0):
            raise ValueError("Overall progress must be between 0.0 and 100.0")
        return v
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get a summary of progress information"""
        return {
            "analysis_id": str(self.analysis_id),
            "status": self.status.value,
            "overall_progress": self.overall_progress,
            "current_stage": self.current_stage.value,
            "stage_progress": self.stage_progress.stage_progress_percentage,
            "frames_processed": self.frames_processed,
            "total_frames": self.total_frames,
            "processing_rate": self.processing_rate_fps,
            "estimated_completion": self.estimated_completion.isoformat() if self.estimated_completion else None,
            "has_errors": self.has_errors,
            "error_count": self.error_count
        }


class ResultUpdateNotification(BaseModel):
    """
    Enhanced result update notification extending existing ResultUpdate pattern.
    Provides comprehensive result information for final analysis outcomes.
    """
    event_type: NotificationEventType = Field(default=NotificationEventType.RESULT_UPDATE, description="Event type")
    analysis_id: UUID = Field(..., description="Analysis identifier")
    
    # Result information
    status: DetectionStatus = Field(..., description="Final analysis status")
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    is_deepfake: bool = Field(..., description="Whether the video was classified as deepfake")
    
    # Detailed results
    frame_results: Optional[List[Dict[str, Any]]] = Field(None, description="Frame-level analysis results")
    suspicious_regions: Optional[List[Dict[str, Any]]] = Field(None, description="Detected suspicious regions")
    detection_metadata: Optional[Dict[str, Any]] = Field(None, description="Detection algorithm metadata")
    
    # Processing summary
    total_processing_time_seconds: float = Field(..., ge=0.0, description="Total processing time")
    frames_analyzed: int = Field(..., ge=0, description="Total frames analyzed")
    average_processing_time_per_frame: Optional[float] = Field(None, ge=0.0, description="Average processing time per frame")
    
    # Quality metrics
    analysis_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Quality score of the analysis")
    model_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Model confidence in the result")
    
    # Blockchain and verification
    blockchain_verified: bool = Field(default=False, description="Whether result is blockchain verified")
    blockchain_transaction_id: Optional[str] = Field(None, description="Blockchain transaction ID")
    verification_timestamp: Optional[datetime] = Field(None, description="Blockchain verification timestamp")
    
    # Error summary
    total_errors: int = Field(default=0, ge=0, description="Total errors encountered during analysis")
    total_retries: int = Field(default=0, ge=0, description="Total retry attempts")
    
    # Messages
    result_message: str = Field(..., description="Human-readable result summary")
    detailed_summary: Optional[str] = Field(None, description="Detailed result summary")
    recommendations: Optional[List[str]] = Field(None, description="Recommendations based on results")
    
    # Notification metadata
    metadata: NotificationMetadata = Field(..., description="Notification metadata")
    
    def get_result_summary(self) -> Dict[str, Any]:
        """Get a summary of result information"""
        return {
            "analysis_id": str(self.analysis_id),
            "status": self.status.value,
            "is_deepfake": self.is_deepfake,
            "overall_confidence": self.overall_confidence,
            "total_processing_time": self.total_processing_time_seconds,
            "frames_analyzed": self.frames_analyzed,
            "blockchain_verified": self.blockchain_verified,
            "total_errors": self.total_errors,
            "analysis_quality": self.analysis_quality_score
        }


class StageTransitionNotification(BaseModel):
    """
    Stage transition notification for detailed progress tracking.
    """
    event_type: NotificationEventType = Field(default=NotificationEventType.STAGE_TRANSITION, description="Event type")
    analysis_id: UUID = Field(..., description="Analysis identifier")
    
    # Transition information
    from_stage: Optional[ProcessingStage] = Field(None, description="Previous processing stage")
    to_stage: ProcessingStage = Field(..., description="Current processing stage")
    transition_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Transition timestamp")
    
    # Stage details
    previous_stage_duration: Optional[float] = Field(None, ge=0.0, description="Duration of previous stage")
    previous_stage_success: bool = Field(default=True, description="Whether previous stage completed successfully")
    previous_stage_errors: List[ErrorContext] = Field(default_factory=list, description="Errors in previous stage")
    
    # Current stage information
    current_stage_progress: StageProgressInfo = Field(..., description="Current stage progress information")
    estimated_stage_duration: Optional[float] = Field(None, ge=0.0, description="Estimated duration for current stage")
    
    # Overall progress
    overall_progress: float = Field(..., ge=0.0, le=100.0, description="Overall analysis progress")
    
    # Notification metadata
    metadata: NotificationMetadata = Field(..., description="Notification metadata")


class ErrorNotification(BaseModel):
    """
    Error notification for comprehensive error tracking and recovery.
    """
    event_type: NotificationEventType = Field(default=NotificationEventType.ERROR_NOTIFICATION, description="Event type")
    analysis_id: UUID = Field(..., description="Analysis identifier")
    
    # Error information
    error_context: ErrorContext = Field(..., description="Comprehensive error context")
    error_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Error timestamp")
    
    # Impact assessment
    impact_level: str = Field(..., description="Impact level (minor, moderate, major, critical)")
    is_recoverable: bool = Field(default=True, description="Whether the error is recoverable")
    auto_recovery_attempted: bool = Field(default=False, description="Whether auto-recovery was attempted")
    auto_recovery_successful: bool = Field(default=False, description="Whether auto-recovery was successful")
    
    # Context information
    current_stage: Optional[ProcessingStage] = Field(None, description="Processing stage where error occurred")
    processing_context: Optional[Dict[str, Any]] = Field(None, description="Processing context when error occurred")
    
    # Notification metadata
    metadata: NotificationMetadata = Field(..., description="Notification metadata")


class CompletionNotification(BaseModel):
    """
    Completion notification for final analysis status.
    """
    event_type: NotificationEventType = Field(default=NotificationEventType.COMPLETION_NOTIFICATION, description="Event type")
    analysis_id: UUID = Field(..., description="Analysis identifier")
    
    # Completion information
    completion_status: DetectionStatus = Field(..., description="Final completion status")
    completion_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Completion timestamp")
    total_processing_time: float = Field(..., ge=0.0, description="Total processing time")
    
    # Summary statistics
    total_frames_processed: int = Field(..., ge=0, description="Total frames processed")
    total_errors_encountered: int = Field(default=0, ge=0, description="Total errors encountered")
    total_retries_performed: int = Field(default=0, ge=0, description="Total retries performed")
    success_rate: float = Field(..., ge=0.0, le=1.0, description="Overall success rate")
    
    # Performance metrics
    average_processing_rate: Optional[float] = Field(None, ge=0.0, description="Average processing rate")
    peak_resource_usage: Optional[Dict[str, Any]] = Field(None, description="Peak resource usage")
    
    # Result summary
    result_summary: Optional[Dict[str, Any]] = Field(None, description="Summary of final results")
    
    # Notification metadata
    metadata: NotificationMetadata = Field(..., description="Notification metadata")


class HeartbeatNotification(BaseModel):
    """
    Heartbeat notification for connection health monitoring.
    """
    event_type: NotificationEventType = Field(default=NotificationEventType.HEARTBEAT, description="Event type")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Heartbeat timestamp")
    server_id: str = Field(..., description="Server identifier")
    active_connections: int = Field(..., ge=0, description="Number of active connections")
    system_status: str = Field(default="healthy", description="System health status")
    metadata: NotificationMetadata = Field(..., description="Notification metadata")


# Union type for all notification types
NotificationEvent = Union[
    StatusUpdateNotification,
    ResultUpdateNotification,
    StageTransitionNotification,
    ErrorNotification,
    CompletionNotification,
    HeartbeatNotification
]


# Utility functions for creating notifications
def create_status_update_notification(
    analysis_id: UUID,
    status: DetectionStatus,
    overall_progress: float,
    current_stage: ProcessingStage,
    stage_progress: StageProgressInfo,
    message: str,
    **kwargs
) -> StatusUpdateNotification:
    """Create a status update notification with default metadata."""
    metadata = NotificationMetadata(
        notification_id=f"status_{analysis_id}_{int(datetime.now(timezone.utc).timestamp())}",
        source="status_tracker",
        priority=NotificationPriority.NORMAL,
        broadcast_to_all=True
    )
    
    return StatusUpdateNotification(
        analysis_id=analysis_id,
        status=status,
        overall_progress=overall_progress,
        current_stage=current_stage,
        stage_progress=stage_progress,
        message=message,
        metadata=metadata,
        **kwargs
    )


def create_result_update_notification(
    analysis_id: UUID,
    status: DetectionStatus,
    overall_confidence: float,
    is_deepfake: bool,
    total_processing_time: float,
    frames_analyzed: int,
    result_message: str,
    **kwargs
) -> ResultUpdateNotification:
    """Create a result update notification with default metadata."""
    metadata = NotificationMetadata(
        notification_id=f"result_{analysis_id}_{int(datetime.now(timezone.utc).timestamp())}",
        source="analysis_engine",
        priority=NotificationPriority.HIGH,
        broadcast_to_all=True
    )
    
    return ResultUpdateNotification(
        analysis_id=analysis_id,
        status=status,
        overall_confidence=overall_confidence,
        is_deepfake=is_deepfake,
        total_processing_time=total_processing_time,
        frames_analyzed=frames_analyzed,
        result_message=result_message,
        metadata=metadata,
        **kwargs
    )


def create_error_notification(
    analysis_id: UUID,
    error_context: ErrorContext,
    impact_level: str,
    current_stage: Optional[ProcessingStage] = None,
    **kwargs
) -> ErrorNotification:
    """Create an error notification with default metadata."""
    metadata = NotificationMetadata(
        notification_id=f"error_{analysis_id}_{int(datetime.now(timezone.utc).timestamp())}",
        source="error_handler",
        priority=NotificationPriority.HIGH,
        broadcast_to_all=True
    )
    
    return ErrorNotification(
        analysis_id=analysis_id,
        error_context=error_context,
        impact_level=impact_level,
        current_stage=current_stage,
        metadata=metadata,
        **kwargs
    )


# Export all models and utility functions
__all__ = [
    'NotificationEventType',
    'NotificationPriority',
    'NotificationStatus',
    'StageProgressInfo',
    'ErrorContext',
    'NotificationMetadata',
    'StatusUpdateNotification',
    'ResultUpdateNotification',
    'StageTransitionNotification',
    'ErrorNotification',
    'CompletionNotification',
    'HeartbeatNotification',
    'NotificationEvent',
    'create_status_update_notification',
    'create_result_update_notification',
    'create_error_notification'
]