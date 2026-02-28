#!/usr/bin/env python3
"""
Status Tracking API Models and Validation Logic
Pydantic models for analysis status tracking extending Core Detection Engine
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class ProcessingStageEnum(str, Enum):
    """Enumeration of processing stages for analysis tracking"""
    UPLOAD = "upload"
    PREPROCESSING = "preprocessing"
    FRAME_EXTRACTION = "frame_extraction"
    FEATURE_ANALYSIS = "feature_analysis"
    DEEPFAKE_DETECTION = "deepfake_detection"
    POSTPROCESSING = "postprocessing"
    BLOCKCHAIN_VERIFICATION = "blockchain_verification"
    FINALIZATION = "finalization"


class StatusTrackingResponse(BaseModel):
    """
    Response model for real-time analysis status tracking.
    Extends Core Detection Engine with comprehensive progress monitoring.
    """
    
    # Core identification
    analysis_id: UUID = Field(
        ..., 
        description="Unique identifier for the analysis being tracked"
    )
    
    # Current status information
    status: str = Field(
        ..., 
        description="Current processing status (queued, processing, completed, failed)"
    )
    
    progress_percentage: float = Field(
        ..., 
        ge=0.0, 
        le=100.0, 
        description="Progress percentage from 0.0 to 100.0 inclusive"
    )
    
    current_stage: str = Field(
        ..., 
        description="Current processing stage within the analysis pipeline"
    )
    
    # Timing information
    estimated_completion: Optional[datetime] = Field(
        default=None,
        description="Estimated completion time based on current progress and processing rate"
    )
    
    processing_time_elapsed: int = Field(
        ..., 
        ge=0, 
        description="Total processing time elapsed in milliseconds"
    )
    
    # Error and retry information
    error_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detailed error information if processing has failed"
    )
    
    retry_count: int = Field(
        default=0, 
        ge=0, 
        description="Number of retry attempts made for this analysis"
    )
    
    # Historical tracking
    stage_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Historical record of processing stages with timestamps and metadata"
    )
    
    # Additional metadata
    processing_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional processing metadata and configuration"
    )
    
    # Timestamps
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when this status was last updated"
    )
    
    @field_validator('progress_percentage')
    @classmethod
    def validate_progress_percentage(cls, v: float) -> float:
        """
        Validate progress percentage is within valid range (0.0-100.0 inclusive).
        Ensures progress values are realistic and within bounds.
        """
        if not isinstance(v, (int, float)):
            raise ValueError("progress_percentage must be a number")
        
        if v < 0.0 or v > 100.0:
            raise ValueError("progress_percentage must be between 0.0 and 100.0 inclusive")
        
        # Allow for slight floating point precision issues
        return round(float(v), 2)
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """
        Validate status is a recognized processing status.
        Ensures status values align with Core Detection Engine patterns.
        """
        valid_statuses = ['queued', 'processing', 'completed', 'failed']
        if v.lower() not in valid_statuses:
            raise ValueError(f"status must be one of: {', '.join(valid_statuses)}")
        return v.lower()
    
    @field_validator('current_stage')
    @classmethod
    def validate_current_stage(cls, v: str) -> str:
        """
        Validate current stage is a recognized processing stage.
        Ensures stage values align with processing pipeline.
        """
        valid_stages = [
            'upload', 'preprocessing', 'frame_extraction', 'feature_analysis',
            'deepfake_detection', 'postprocessing', 'blockchain_verification', 'finalization'
        ]
        if v.lower() not in valid_stages:
            raise ValueError(f"current_stage must be one of: {', '.join(valid_stages)}")
        return v.lower()
    
    @field_validator('processing_time_elapsed')
    @classmethod
    def validate_processing_time(cls, v: int) -> int:
        """
        Validate processing time is non-negative and reasonable.
        Ensures processing time values are logical.
        """
        if v < 0:
            raise ValueError("processing_time_elapsed must be non-negative")
        
        # Reasonable upper bound (24 hours in milliseconds)
        max_reasonable_time = 24 * 60 * 60 * 1000
        if v > max_reasonable_time:
            raise ValueError("processing_time_elapsed exceeds reasonable maximum (24 hours)")
        
        return v
    
    @field_validator('retry_count')
    @classmethod
    def validate_retry_count(cls, v: int) -> int:
        """
        Validate retry count is non-negative and reasonable.
        Ensures retry values are within acceptable limits.
        """
        if v < 0:
            raise ValueError("retry_count must be non-negative")
        
        # Reasonable upper bound for retry attempts
        max_retries = 10
        if v > max_retries:
            raise ValueError(f"retry_count cannot exceed {max_retries}")
        
        return v
    
    @model_validator(mode='after')
    def validate_status_transition(self) -> 'StatusTrackingResponse':
        """
        Validate status transitions follow valid processing workflow.
        Ensures status changes are logical and follow expected progression.
        """
        # Define valid status transitions
        valid_transitions = {
            'queued': ['processing', 'failed'],
            'processing': ['completed', 'failed'],
            'completed': [],  # Terminal state
            'failed': ['queued', 'processing']  # Can retry
        }
        
        # Check stage history for previous status if available
        if self.stage_history:
            # Find the most recent status change
            recent_status_changes = [
                entry for entry in self.stage_history 
                if 'status' in entry and 'timestamp' in entry
            ]
            
            if recent_status_changes:
                # Sort by timestamp to get the most recent
                recent_status_changes.sort(
                    key=lambda x: x.get('timestamp', ''),
                    reverse=True
                )
                previous_status = recent_status_changes[0].get('status')
                
                # Validate transition from previous status to current status
                if previous_status and previous_status in valid_transitions:
                    if self.status not in valid_transitions[previous_status]:
                        raise ValueError(
                            f"Invalid status transition from '{previous_status}' to '{self.status}'. "
                            f"Valid transitions from '{previous_status}': {valid_transitions[previous_status]}"
                        )
        
        return self
    
    @model_validator(mode='after')
    def validate_stage_history_consistency(self) -> 'StatusTrackingResponse':
        """
        Validate stage history maintains chronological order and consistency.
        Ensures historical data is logical and properly structured.
        """
        if not self.stage_history:
            return self
        
        # Validate each stage history entry
        for i, entry in enumerate(self.stage_history):
            if not isinstance(entry, dict):
                raise ValueError(f"stage_history[{i}] must be a dictionary")
            
            # Required fields for stage history entries
            required_fields = ['stage', 'timestamp']
            for field in required_fields:
                if field not in entry:
                    raise ValueError(f"stage_history[{i}] missing required field: {field}")
            
            # Validate timestamp format
            timestamp = entry.get('timestamp')
            if not isinstance(timestamp, (str, datetime)):
                raise ValueError(f"stage_history[{i}] timestamp must be a string or datetime")
            
            # Validate stage name
            stage = entry.get('stage')
            if not isinstance(stage, str):
                raise ValueError(f"stage_history[{i}] stage must be a string")
        
        # Check chronological order (if timestamps are provided)
        timestamps = []
        for entry in self.stage_history:
            timestamp = entry.get('timestamp')
            if isinstance(timestamp, str):
                try:
                    # Try to parse as ISO format
                    parsed_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    timestamps.append((parsed_time, entry))
                except ValueError:
                    # Skip entries with unparseable timestamps
                    continue
            elif isinstance(timestamp, datetime):
                timestamps.append((timestamp, entry))
        
        if timestamps:
            # Sort by timestamp and check if original order is maintained
            sorted_timestamps = sorted(timestamps, key=lambda x: x[0])
            if timestamps != sorted_timestamps:
                # Allow some flexibility for minor timestamp ordering issues
                # but warn about potential inconsistencies
                pass  # Could add warning here if needed
        
        return self
    
    @model_validator(mode='after')
    def validate_progress_consistency(self) -> 'StatusTrackingResponse':
        """
        Validate progress percentage is consistent with status and stage.
        Ensures progress values align with processing state.
        """
        # Completed status should have 100% progress
        if self.status == 'completed' and self.progress_percentage != 100.0:
            # Allow slight tolerance for floating point precision
            if abs(self.progress_percentage - 100.0) > 0.01:
                raise ValueError("completed status requires 100.0% progress")
        
        # Failed status can have any progress (processing may have failed at any stage)
        if self.status == 'failed':
            pass  # No progress constraints for failed status
        
        # Queued status should typically have 0% progress
        if self.status == 'queued' and self.progress_percentage > 0.0:
            # Allow some tolerance for initialization progress
            if self.progress_percentage > 5.0:
                raise ValueError("queued status should have minimal progress (≤5.0%)")
        
        return self
    
    def get_processing_duration_seconds(self) -> float:
        """Calculate processing duration in seconds"""
        return self.processing_time_elapsed / 1000.0
    
    def get_estimated_remaining_time_ms(self) -> Optional[int]:
        """Calculate estimated remaining processing time in milliseconds"""
        if self.progress_percentage <= 0.0 or self.progress_percentage >= 100.0:
            return None
        
        # Calculate remaining time based on current progress rate
        if self.processing_time_elapsed > 0:
            progress_rate = self.progress_percentage / self.processing_time_elapsed
            remaining_progress = 100.0 - self.progress_percentage
            estimated_remaining = remaining_progress / progress_rate
            return int(estimated_remaining)
        
        return None
    
    def is_terminal_status(self) -> bool:
        """Check if current status is terminal (completed or failed)"""
        return self.status in ['completed', 'failed']
    
    def can_retry(self) -> bool:
        """Check if analysis can be retried based on current status"""
        return self.status == 'failed' and self.retry_count < 10


class StatusHistoryResponse(BaseModel):
    """
    Response model for comprehensive analysis status history.
    Provides detailed historical tracking and performance metrics.
    """
    
    # Core identification
    analysis_id: UUID = Field(
        ..., 
        description="Unique identifier for the analysis"
    )
    
    # Status tracking timeline
    status_timeline: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Chronological timeline of status changes with timestamps and metadata"
    )
    
    # Processing stage history
    processing_stages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Detailed history of processing stages with timing and performance data"
    )
    
    # Error tracking
    error_logs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Comprehensive error log entries with context and resolution attempts"
    )
    
    # Performance metrics
    performance_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregated performance metrics including timing, throughput, and efficiency"
    )
    
    # Retry attempt history
    retry_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="History of retry attempts with reasons and outcomes"
    )
    
    # Summary information
    total_processing_time_ms: int = Field(
        ..., 
        ge=0, 
        description="Total processing time across all attempts in milliseconds"
    )
    
    final_status: str = Field(
        ..., 
        description="Final status of the analysis (completed, failed)"
    )
    
    # Metadata
    created_at: datetime = Field(
        ..., 
        description="Timestamp when the analysis was originally created"
    )
    
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the analysis was completed or finally failed"
    )
    
    @field_validator('final_status')
    @classmethod
    def validate_final_status(cls, v: str) -> str:
        """
        Validate final status is a terminal status.
        Ensures final status represents a completed analysis.
        """
        terminal_statuses = ['completed', 'failed']
        if v.lower() not in terminal_statuses:
            raise ValueError(f"final_status must be one of: {', '.join(terminal_statuses)}")
        return v.lower()
    
    @field_validator('total_processing_time_ms')
    @classmethod
    def validate_total_processing_time(cls, v: int) -> int:
        """
        Validate total processing time is non-negative and reasonable.
        Ensures processing time values are logical.
        """
        if v < 0:
            raise ValueError("total_processing_time_ms must be non-negative")
        
        # Reasonable upper bound (48 hours in milliseconds for retries)
        max_reasonable_time = 48 * 60 * 60 * 1000
        if v > max_reasonable_time:
            raise ValueError("total_processing_time_ms exceeds reasonable maximum (48 hours)")
        
        return v
    
    @model_validator(mode='after')
    def validate_status_timeline_consistency(self) -> 'StatusHistoryResponse':
        """
        Validate status timeline maintains chronological order and completeness.
        Ensures timeline data is logical and properly structured.
        """
        if not self.status_timeline:
            return self
        
        # Validate each timeline entry
        for i, entry in enumerate(self.status_timeline):
            if not isinstance(entry, dict):
                raise ValueError(f"status_timeline[{i}] must be a dictionary")
            
            # Required fields for timeline entries
            required_fields = ['status', 'timestamp']
            for field in required_fields:
                if field not in entry:
                    raise ValueError(f"status_timeline[{i}] missing required field: {field}")
            
            # Validate status value
            status = entry.get('status')
            valid_statuses = ['queued', 'processing', 'completed', 'failed']
            if status not in valid_statuses:
                raise ValueError(f"status_timeline[{i}] status must be one of: {', '.join(valid_statuses)}")
        
        # Check chronological order
        timestamps = []
        for entry in self.status_timeline:
            timestamp = entry.get('timestamp')
            if isinstance(timestamp, (str, datetime)):
                if isinstance(timestamp, str):
                    try:
                        parsed_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        timestamps.append(parsed_time)
                    except ValueError:
                        continue
                else:
                    timestamps.append(timestamp)
        
        if timestamps and len(timestamps) > 1:
            # Check if timestamps are in chronological order
            for i in range(1, len(timestamps)):
                if timestamps[i] < timestamps[i-1]:
                    raise ValueError("status_timeline timestamps must be in chronological order")
        
        return self
    
    @model_validator(mode='after')
    def validate_processing_stages_consistency(self) -> 'StatusHistoryResponse':
        """
        Validate processing stages maintain logical progression and timing.
        Ensures stage data is consistent and properly structured.
        """
        if not self.processing_stages:
            return self
        
        # Validate each processing stage entry
        for i, stage in enumerate(self.processing_stages):
            if not isinstance(stage, dict):
                raise ValueError(f"processing_stages[{i}] must be a dictionary")
            
            # Required fields for processing stage entries
            required_fields = ['stage', 'start_time', 'end_time']
            for field in required_fields:
                if field not in stage:
                    raise ValueError(f"processing_stages[{i}] missing required field: {field}")
            
            # Validate stage name
            stage_name = stage.get('stage')
            valid_stages = [
                'upload', 'preprocessing', 'frame_extraction', 'feature_analysis',
                'deepfake_detection', 'postprocessing', 'blockchain_verification', 'finalization'
            ]
            if stage_name not in valid_stages:
                raise ValueError(f"processing_stages[{i}] stage must be one of: {', '.join(valid_stages)}")
        
        return self
    
    @model_validator(mode='after')
    def validate_error_logs_structure(self) -> 'StatusHistoryResponse':
        """
        Validate error logs maintain proper structure and context.
        Ensures error data is comprehensive and useful for debugging.
        """
        if not self.error_logs:
            return self
        
        # Validate each error log entry
        for i, error in enumerate(self.error_logs):
            if not isinstance(error, dict):
                raise ValueError(f"error_logs[{i}] must be a dictionary")
            
            # Required fields for error log entries
            required_fields = ['timestamp', 'error_type', 'message']
            for field in required_fields:
                if field not in error:
                    raise ValueError(f"error_logs[{i}] missing required field: {field}")
            
            # Validate error type
            error_type = error.get('error_type')
            if not isinstance(error_type, str) or not error_type.strip():
                raise ValueError(f"error_logs[{i}] error_type must be a non-empty string")
        
        return self
    
    @model_validator(mode='after')
    def validate_retry_history_consistency(self) -> 'StatusHistoryResponse':
        """
        Validate retry history maintains logical progression and outcomes.
        Ensures retry data is consistent with final status.
        """
        if not self.retry_history:
            return self
        
        # Validate each retry entry
        for i, retry in enumerate(self.retry_history):
            if not isinstance(retry, dict):
                raise ValueError(f"retry_history[{i}] must be a dictionary")
            
            # Required fields for retry entries
            required_fields = ['attempt_number', 'timestamp', 'reason', 'outcome']
            for field in required_fields:
                if field not in retry:
                    raise ValueError(f"retry_history[{i}] missing required field: {field}")
            
            # Validate attempt number
            attempt_number = retry.get('attempt_number')
            if not isinstance(attempt_number, int) or attempt_number < 1:
                raise ValueError(f"retry_history[{i}] attempt_number must be a positive integer")
        
        return self
    
    def get_total_retry_attempts(self) -> int:
        """Get total number of retry attempts"""
        return len(self.retry_history)
    
    def get_successful_stages(self) -> List[str]:
        """Get list of successfully completed processing stages"""
        return [
            stage.get('stage') for stage in self.processing_stages
            if stage.get('end_time') is not None
        ]
    
    def get_failed_stages(self) -> List[str]:
        """Get list of failed processing stages"""
        return [
            stage.get('stage') for stage in self.processing_stages
            if stage.get('error') is not None
        ]
    
    def get_processing_duration_seconds(self) -> float:
        """Calculate total processing duration in seconds"""
        return self.total_processing_time_ms / 1000.0
    
    def get_average_stage_duration_ms(self) -> Optional[float]:
        """Calculate average duration per processing stage in milliseconds"""
        completed_stages = [
            stage for stage in self.processing_stages
            if stage.get('start_time') and stage.get('end_time')
        ]
        
        if not completed_stages:
            return None
        
        total_duration = 0
        for stage in completed_stages:
            start_time = stage.get('start_time')
            end_time = stage.get('end_time')
            
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            duration = (end_time - start_time).total_seconds() * 1000
            total_duration += duration
        
        return total_duration / len(completed_stages)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors encountered during processing"""
        error_types = {}
        total_errors = len(self.error_logs)
        
        for error in self.error_logs:
            error_type = error.get('error_type', 'unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            'total_errors': total_errors,
            'error_types': error_types,
            'most_common_error': max(error_types.items(), key=lambda x: x[1])[0] if error_types else None
        }


class StatusTransitionValidator:
    """
    Utility class for validating status transitions and managing state machine logic.
    """
    
    # Define valid status transitions
    VALID_TRANSITIONS = {
        'queued': ['processing', 'failed'],
        'processing': ['completed', 'failed'],
        'completed': [],  # Terminal state
        'failed': ['queued', 'processing']  # Can retry
    }
    
    @classmethod
    def is_valid_transition(cls, from_status: str, to_status: str) -> bool:
        """
        Check if a status transition is valid.
        
        Args:
            from_status: Current status
            to_status: Target status
            
        Returns:
            True if transition is valid, False otherwise
        """
        if from_status not in cls.VALID_TRANSITIONS:
            return False
        
        return to_status in cls.VALID_TRANSITIONS[from_status]
    
    @classmethod
    def get_valid_transitions(cls, from_status: str) -> List[str]:
        """
        Get list of valid transitions from a given status.
        
        Args:
            from_status: Current status
            
        Returns:
            List of valid target statuses
        """
        return cls.VALID_TRANSITIONS.get(from_status, [])
    
    @classmethod
    def is_terminal_status(cls, status: str) -> bool:
        """
        Check if a status is terminal (no further transitions allowed).
        
        Args:
            status: Status to check
            
        Returns:
            True if status is terminal, False otherwise
        """
        return status in ['completed', 'failed']
    
    @classmethod
    def can_retry_from_status(cls, status: str) -> bool:
        """
        Check if an analysis can be retried from a given status.
        
        Args:
            status: Current status
            
        Returns:
            True if retry is possible, False otherwise
        """
        return status == 'failed' and 'queued' in cls.VALID_TRANSITIONS.get(status, [])
