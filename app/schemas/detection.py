#!/usr/bin/env python3
"""
Detection API Schemas
Pydantic models for video detection API request/response validation and OpenAPI documentation
"""

from pydantic import BaseModel, Field, validator, model_validator
from fastapi import UploadFile
from uuid import UUID
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal


class DetectionStatus(str, Enum):
    """Enumeration of possible detection processing statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingStage(str, Enum):
    """Enumeration of processing stages for real-time status updates."""
    UPLOADING = "uploading"
    PREPROCESSING = "preprocessing"
    FRAME_EXTRACTION = "frame_extraction"
    DETECTION_ANALYSIS = "detection_analysis"
    POSTPROCESSING = "postprocessing"
    RESULT_GENERATION = "result_generation"
    BLOCKCHAIN_VERIFICATION = "blockchain_verification"
    COMPLETED = "completed"


class VideoDetectionRequest(BaseModel):
    """
    Request model for video deepfake detection.
    Includes UploadFile field for video files, options Dict for detection configuration, 
    and optional priority field with validation.
    """
    file: UploadFile = Field(..., description="The video file to be uploaded for detection. Supported formats: MP4, AVI, MOV.")
    options: Dict[str, Any] = Field(default_factory=dict, description="Detection configuration options and parameters.")
    priority: Optional[int] = Field(None, ge=1, le=10, description="Optional priority level for processing (1=lowest, 10=highest).")

    @validator('file')
    def validate_file(cls, v):
        """Validate that the uploaded file has a supported extension."""
        supported_extensions = ['.mp4', '.avi', '.mov']
        if v.filename:
            file_extension = v.filename.lower().split('.')[-1]
            if f'.{file_extension}' not in supported_extensions:
                raise ValueError(f"Unsupported file format. Supported formats: {', '.join(ext.upper() for ext in supported_extensions)}")
        return v


class DetectionResponse(BaseModel):
    """
    Response model for deepfake detection submission.
    Returns analysis_id for tracking the processing status and results.
    """
    analysis_id: UUID = Field(..., description="Unique identifier for the analysis result.")
    status: DetectionStatus = Field(..., description="Current status of the analysis.")
    message: str = Field(..., description="Human-readable status message.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the analysis was created (UTC).")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time for the analysis.")


class ProcessingStageDetails(BaseModel):
    """
    Detailed information about processing stages with completion status.
    """
    stage_name: str = Field(..., description="Name of the current processing stage")
    stage_status: str = Field(..., description="Status of the stage (active, completed, skipped, failed)")
    stage_completion_percentage: float = Field(..., ge=0.0, le=100.0, description="Stage completion percentage (0-100)")
    stage_start_time: Optional[datetime] = Field(None, description="When the stage started")
    stage_estimated_duration_seconds: Optional[float] = Field(None, ge=0.0, description="Estimated duration for this stage")
    stage_frames_processed: Optional[int] = Field(None, ge=0, description="Frames processed in this stage")
    stage_total_frames: Optional[int] = Field(None, ge=0, description="Total frames for this stage")


class FrameProgressInfo(BaseModel):
    """
    Frame-level progress information for detailed tracking.
    """
    current_frame_number: int = Field(..., ge=0, description="Current frame being processed")
    total_frames: int = Field(..., ge=1, description="Total number of frames to process")
    frames_processed: int = Field(..., ge=0, description="Number of frames already processed")
    frame_processing_rate: Optional[float] = Field(None, ge=0.0, description="Frames processed per second")
    average_frame_time_ms: Optional[float] = Field(None, ge=0.0, description="Average processing time per frame in milliseconds")
    estimated_remaining_frames: int = Field(..., ge=0, description="Estimated remaining frames to process")
    progress_trend: str = Field(default="stable", description="Progress trend (accelerating, stable, decelerating)")


class ErrorRecoveryStatus(BaseModel):
    """
    Error recovery status and retry information.
    """
    has_errors: bool = Field(default=False, description="Whether any errors have occurred")
    error_count: int = Field(default=0, ge=0, description="Total number of errors encountered")
    retry_attempts: int = Field(default=0, ge=0, description="Number of retry attempts made")
    max_retries: int = Field(default=3, ge=0, description="Maximum allowed retry attempts")
    last_error_type: Optional[str] = Field(None, description="Type of the most recent error")
    last_error_message: Optional[str] = Field(None, description="Message from the most recent error")
    last_error_timestamp: Optional[datetime] = Field(None, description="When the last error occurred")
    recovery_actions_taken: List[str] = Field(default_factory=list, description="List of recovery actions taken")
    is_recovering: bool = Field(default=False, description="Whether currently in recovery mode")


class ProcessingMetrics(BaseModel):
    """
    Overall processing metrics and performance indicators.
    """
    cpu_usage_percent: Optional[float] = Field(None, ge=0.0, le=100.0, description="CPU usage percentage")
    memory_usage_mb: Optional[float] = Field(None, ge=0.0, description="Memory usage in megabytes")
    processing_efficiency: Optional[float] = Field(None, ge=0.0, le=1.0, description="Processing efficiency score (0-1)")
    queue_wait_time_seconds: Optional[float] = Field(None, ge=0.0, description="Time spent waiting in processing queue")
    worker_id: Optional[str] = Field(None, description="ID of the worker processing this analysis")


class DetailedDetectionStatusResponse(BaseModel):
    """
    Enhanced response model for detection processing status with comprehensive progress tracking.
    Maintains backward compatibility while adding detailed progress information.
    """
    # Core identification and status
    analysis_id: UUID = Field(..., description="Unique identifier for the analysis result.")
    status: DetectionStatus = Field(..., description="Current status of the analysis.")
    
    # Legacy fields (for backward compatibility)
    progress_percentage: float = Field(..., ge=0.0, le=100.0, description="Processing progress percentage (0-100).")
    current_stage: ProcessingStage = Field(..., description="Current processing stage.")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time.")
    processing_time_seconds: Optional[float] = Field(None, ge=0.0, description="Time spent processing in seconds.")
    frames_processed: Optional[int] = Field(None, ge=0, description="Number of frames processed so far.")
    total_frames: Optional[int] = Field(None, ge=0, description="Total number of frames in the video.")
    error_message: Optional[str] = Field(None, description="Error message if processing failed.")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last status update timestamp.")
    
    # NEW: Detailed progress tracking
    processing_stage_details: Optional[ProcessingStageDetails] = Field(None, description="Detailed information about the current processing stage")
    frame_progress_info: Optional[FrameProgressInfo] = Field(None, description="Frame-level progress tracking information")
    error_recovery_status: Optional[ErrorRecoveryStatus] = Field(None, description="Error recovery status and retry information")
    processing_metrics: Optional[ProcessingMetrics] = Field(None, description="Overall processing metrics and performance indicators")
    
    # Progress intervals with historical data
    progress_history: List[Dict[str, Any]] = Field(default_factory=list, description="Historical progress data for trend analysis")
    
    @model_validator(mode='after')
    def validate_frame_consistency(self) -> 'DetailedDetectionStatusResponse':
        """Validate frame count consistency between legacy and detailed fields"""
        if self.frame_progress_info:
            if self.frames_processed != self.frame_progress_info.frames_processed:
                # Update legacy field with detailed info
                self.frames_processed = self.frame_progress_info.frames_processed
            if self.total_frames != self.frame_progress_info.total_frames:
                # Update legacy field with detailed info
                self.total_frames = self.frame_progress_info.total_frames
        return self
    
    def get_completion_estimate(self) -> Optional[datetime]:
        """Calculate estimated completion time based on frame processing rate"""
        if not self.frame_progress_info or not self.frame_progress_info.frame_processing_rate:
            return self.estimated_completion
        
        if self.frame_progress_info.frame_processing_rate <= 0:
            return None
        
        remaining_frames = self.frame_progress_info.total_frames - self.frame_progress_info.frames_processed
        if remaining_frames <= 0:
            return datetime.now(timezone.utc)
        
        time_to_completion_seconds = remaining_frames / self.frame_progress_info.frame_processing_rate
        return datetime.now(timezone.utc) + timedelta(seconds=time_to_completion_seconds)
    
    def get_confidence_score(self) -> float:
        """Calculate confidence score for progress estimates (0-1)"""
        base_confidence = 0.5  # Base confidence
        
        # Increase confidence with more processed frames
        if self.frame_progress_info and self.frame_progress_info.total_frames > 0:
            progress_ratio = self.frame_progress_info.frames_processed / self.frame_progress_info.total_frames
            base_confidence += progress_ratio * 0.3  # Up to 0.3 bonus
        
        # Increase confidence with stable processing rate
        if self.processing_metrics and self.processing_metrics.processing_efficiency:
            base_confidence += self.processing_metrics.processing_efficiency * 0.2  # Up to 0.2 bonus
        
        return min(1.0, base_confidence)


# Keep original DetectionStatusResponse for backward compatibility
class DetectionStatusResponse(BaseModel):
    """
    Response model for detection processing status.
    Provides real-time status updates with progress information.
    """
    analysis_id: UUID = Field(..., description="Unique identifier for the analysis result.")
    status: DetectionStatus = Field(..., description="Current status of the analysis.")
    progress_percentage: float = Field(..., ge=0.0, le=100.0, description="Processing progress percentage (0-100).")
    current_stage: ProcessingStage = Field(..., description="Current processing stage.")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time.")
    processing_time_seconds: Optional[float] = Field(None, ge=0.0, description="Time spent processing in seconds.")
    frames_processed: Optional[int] = Field(None, ge=0, description="Number of frames processed so far.")
    total_frames: Optional[int] = Field(None, ge=0, description="Total number of frames in the video.")
    error_message: Optional[str] = Field(None, description="Error message if processing failed.")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last status update timestamp.")


class FrameAnalysis(BaseModel):
    """
    Model for individual frame analysis results.
    """
    frame_number: int = Field(..., ge=0, description="Frame number in the video.")
    timestamp: float = Field(..., ge=0.0, description="Timestamp of the frame in seconds.")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score for this frame (0.0 = real, 1.0 = fake).")
    suspicious_regions: List[Dict[str, Any]] = Field(default_factory=list, description="List of suspicious regions detected in this frame.")
    detection_methods: List[str] = Field(default_factory=list, description="Detection methods used for this frame.")
    processing_time_ms: float = Field(..., ge=0.0, description="Processing time for this frame in milliseconds.")


class SuspiciousRegion(BaseModel):
    """
    Model for suspicious regions detected in video frames.
    """
    region_id: str = Field(..., description="Unique identifier for the suspicious region.")
    frame_number: int = Field(..., ge=0, description="Frame number where the region was detected.")
    bounding_box: Dict[str, float] = Field(..., description="Bounding box coordinates (x, y, width, height).")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score for this region.")
    detection_method: str = Field(..., description="Method used to detect this region.")
    anomaly_type: str = Field(..., description="Type of anomaly detected.")
    severity: str = Field(..., description="Severity level of the anomaly.")


class HeatmapData(BaseModel):
    """
    Heatmap visualization data for spatial analysis of suspicious regions.
    """
    width: int = Field(..., ge=1, description="Heatmap width in pixels")
    height: int = Field(..., ge=1, description="Heatmap height in pixels")
    intensity_grid: List[List[float]] = Field(..., description="2D grid of confidence intensity values")
    confidence_ranges: List[str] = Field(default_factory=lambda: ['0.0-0.25', '0.25-0.5', '0.5-0.75', '0.75-1.0'], description="Confidence value range labels")
    frame_range: Dict[str, int] = Field(..., description="Start and end frame numbers for the heatmap")


class InteractiveFrameNavigation(BaseModel):
    """
    Interactive frame navigation data for UI frame selection.
    """
    thumbnails: List[Dict[str, Any]] = Field(default_factory=list, description="Frame thumbnails and metadata")
    navigation_points: List[Dict[str, Any]] = Field(default_factory=list, description="Key navigation points (peaks, valleys)")
    confidence_timeline: List[Dict[str, Any]] = Field(default_factory=list, description="Confidence scores over time")


class EnhancedConfidenceVisualization(BaseModel):
    """
    Frame-level confidence visualization data for UI rendering.
    """
    frame_scores: List[Dict[str, Any]] = Field(default_factory=list, description="Per-frame confidence scores and metadata")
    distribution_bins: Dict[str, int] = Field(default_factory=dict, description="Confidence score distribution")
    trending_score: float = Field(..., ge=0.0, le=1.0, description="Overall trending confidence score")
    anomaly_frames: List[int] = Field(default_factory=list, description="Frame numbers with anomalous confidence scores")


class BlockchainVerificationStatus(BaseModel):
    """
    Enhanced blockchain verification status with real-time validation.
    """
    verification_status: str = Field(..., description="Current verification status")
    solana_transaction_hash: Optional[str] = Field(None, description="Solana blockchain transaction hash")
    verification_timestamp: Optional[datetime] = Field(None, description="When verification was performed")
    verification_details: Dict[str, Any] = Field(default_factory=dict, description="Additional verification metadata")
    is_tamper_proof: bool = Field(default=False, description="Whether result is tamper-proof verified")


class DownloadableReportMetadata(BaseModel):
    """
    Metadata for downloadable report generation without actual generation.
    """
    available_formats: List[str] = Field(default_factory=lambda: ['pdf', 'json', 'csv'], description="Available export formats")
    report_size_estimates: Dict[str, int] = Field(default_factory=dict, description="Estimated file sizes for each format")
    generation_time_estimates: Dict[str, float] = Field(default_factory=dict, description="Estimated generation times in seconds")
    access_permissions: Dict[str, bool] = Field(default_factory=dict, description="User permissions for report generation")


class DetectionResultsResponse(BaseModel):
    """
    Enhanced response model for comprehensive detection results with visualization data.
    Extends existing Core Detection Engine data with specialized visualization fields.
    """
    analysis_id: UUID = Field(..., description="Unique identifier for the analysis result.")
    status: DetectionStatus = Field(..., description="Final status of the analysis.")
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score for the detection (0.0 = real, 1.0 = fake).")
    detection_summary: Dict[str, Any] = Field(..., description="Summary of detection results and statistics.")
    
    # Frame-by-frame analysis
    frame_analysis: List[FrameAnalysis] = Field(default_factory=list, description="Detailed analysis for each frame.")
    suspicious_regions: List[SuspiciousRegion] = Field(default_factory=list, description="All suspicious regions detected.")
    
    # NEW: Enhanced visualization data
    heatmap_data: Optional[HeatmapData] = Field(None, description="Heatmap generation data for spatial analysis visualization")
    suspicious_region_coordinates: List[Dict[str, Any]] = Field(default_factory=list, description="Aggregated suspicious region coordinates for visualization")
    interactive_frame_navigation: Optional[InteractiveFrameNavigation] = Field(None, description="Interactive frame navigation data for UI frame selection")
    confidence_score_visualization: Optional[EnhancedConfidenceVisualization] = Field(None, description="Frame-level confidence visualization data for UI rendering")
    
    # Enhanced blockchain verification
    blockchain_verification_status: Optional[BlockchainVerificationStatus] = Field(None, description="Enhanced blockchain verification status with real-time validation")
    solana_network_status: Optional[Dict[str, Any]] = Field(None, description="Real-time Solana network status for verification")
    
    # Downloadable report metadata (without generation)
    downloadable_report_metadata: Optional[DownloadableReportMetadata] = Field(None, description="Metadata for downloadable report generation")
    
    # Processing information
    total_frames: int = Field(..., ge=0, description="Total number of frames analyzed.")
    processing_time_seconds: float = Field(..., ge=0.0, description="Total processing time in seconds.")
    detection_methods_used: List[str] = Field(default_factory=list, description="Detection methods used for analysis.")
    
    # Legacy blockchain fields (for backward compatibility)
    blockchain_hash: Optional[str] = Field(None, description="Legacy blockchain hash for tamper-proof verification of the result.")
    verification_status: Optional[str] = Field(None, description="Legacy status of blockchain verification.")
    
    # Timestamps
    created_at: datetime = Field(..., description="When the analysis was created.")
    completed_at: datetime = Field(..., description="When the analysis was completed.")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp.")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional analysis metadata and configuration.")


class DetectionErrorResponse(BaseModel):
    """
    Error response model for detection API errors.
    """
    success: bool = Field(False, description="Always false for error responses.")
    error: Dict[str, Any] = Field(..., description="Error details including code, message, and additional information.")
    analysis_id: Optional[UUID] = Field(None, description="Analysis ID if available.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Error timestamp.")


class DetectionConfig(BaseModel):
    """
    Configuration model for detection processing options.
    """
    detection_methods: List[str] = Field(
        default_factory=lambda: ["resnet50", "clip", "ensemble"],
        description="Detection methods to use for analysis."
    )
    confidence_threshold: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for detection results."
    )
    frame_sampling_rate: int = Field(
        1,
        ge=1,
        description="Frame sampling rate (1 = every frame, 2 = every other frame, etc.)."
    )
    enable_blockchain_verification: bool = Field(
        True,
        description="Whether to enable blockchain verification of results."
    )
    max_processing_time_minutes: int = Field(
        30,
        ge=1,
        le=120,
        description="Maximum processing time in minutes before timeout."
    )
    quality_threshold: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="Minimum video quality threshold for processing."
    )


class DetectionStats(BaseModel):
    """
    Statistics model for detection processing metrics.
    """
    total_analyses: int = Field(..., ge=0, description="Total number of analyses performed.")
    successful_analyses: int = Field(..., ge=0, description="Number of successful analyses.")
    failed_analyses: int = Field(..., ge=0, description="Number of failed analyses.")
    average_processing_time_seconds: float = Field(..., ge=0.0, description="Average processing time in seconds.")
    average_confidence_score: float = Field(..., ge=0.0, le=1.0, description="Average confidence score across all analyses.")
    detection_methods_performance: Dict[str, float] = Field(default_factory=dict, description="Performance metrics for each detection method.")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last statistics update.")


# Utility functions for validation
def validate_video_file(file: UploadFile) -> bool:
    """
    Validate uploaded video file format and basic properties.
    
    Args:
        file: Uploaded file object
        
    Returns:
        bool: True if file is valid
        
    Raises:
        ValueError: If file validation fails
    """
    if not file.filename:
        raise ValueError("No filename provided")
    
    # Check file extension
    supported_extensions = ['.mp4', '.avi', '.mov']
    file_extension = f".{file.filename.lower().split('.')[-1]}"
    
    if file_extension not in supported_extensions:
        raise ValueError(f"Unsupported file format '{file_extension}'. Supported formats: {', '.join(supported_extensions)}")
    
    return True


def validate_file_size(file_size: int, max_size: int = 500 * 1024 * 1024) -> bool:
    """
    Validate file size against maximum allowed size.
    
    Args:
        file_size: Size of the file in bytes
        max_size: Maximum allowed size in bytes (default: 500MB)
        
    Returns:
        bool: True if file size is valid
        
    Raises:
        ValueError: If file size exceeds limit
    """
    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        file_size_mb = file_size / (1024 * 1024)
        raise ValueError(f"File size ({file_size_mb:.1f}MB) exceeds maximum allowed size ({max_size_mb:.1f}MB)")
    
    return True


def create_detection_response(
    analysis_id: UUID,
    status: DetectionStatus = DetectionStatus.PENDING,
    message: str = "Analysis submitted successfully",
    estimated_completion: Optional[datetime] = None
) -> DetectionResponse:
    """
    Create a detection response with default values.
    
    Args:
        analysis_id: Analysis ID
        status: Detection status
        message: Status message
        estimated_completion: Optional estimated completion time
        
    Returns:
        DetectionResponse instance
    """
    return DetectionResponse(
        analysis_id=analysis_id,
        status=status,
        message=message,
        estimated_completion=estimated_completion
    )


def create_status_response(
    analysis_id: UUID,
    status: DetectionStatus,
    progress_percentage: float,
    current_stage: ProcessingStage,
    **kwargs
) -> DetectionStatusResponse:
    """
    Create a status response with provided values.
    
    Args:
        analysis_id: Analysis ID
        status: Current status
        progress_percentage: Progress percentage
        current_stage: Current processing stage
        **kwargs: Additional fields
        
    Returns:
        DetectionStatusResponse instance
    """
    return DetectionStatusResponse(
        analysis_id=analysis_id,
        status=status,
        progress_percentage=progress_percentage,
        current_stage=current_stage,
        **kwargs
    )


def create_results_response(
    analysis_id: UUID,
    overall_confidence: float,
    detection_summary: Dict[str, Any],
    **kwargs
) -> DetectionResultsResponse:
    """
    Create a results response with provided values.
    
    Args:
        analysis_id: Analysis ID
        overall_confidence: Overall confidence score
        detection_summary: Detection summary
        **kwargs: Additional fields
        
    Returns:
        DetectionResultsResponse instance
    """
    return DetectionResultsResponse(
        analysis_id=analysis_id,
        status=DetectionStatus.COMPLETED,
        overall_confidence=overall_confidence,
        detection_summary=detection_summary,
        **kwargs
    )


# History-specific models for audit trail and analysis tracking
class ProcessingStageHistory(BaseModel):
    """
    Historical record of a processing stage with timestamps and metrics.
    """
    stage_name: str = Field(..., description="Name of the processing stage")
    stage_status: str = Field(..., description="Final status of the stage (completed, failed, skipped)")
    stage_start_time: datetime = Field(..., description="When the stage started processing")
    stage_end_time: Optional[datetime] = Field(None, description="When the stage completed")
    stage_duration_seconds: Optional[float] = Field(None, ge=0.0, description="Total duration of the stage in seconds")
    stage_completion_percentage: float = Field(..., ge=0.0, le=100.0, description="Final completion percentage")
    frames_processed: Optional[int] = Field(None, ge=0, description="Number of frames processed in this stage")
    total_frames: Optional[int] = Field(None, ge=0, description="Total frames for this stage")
    processing_rate_fps: Optional[float] = Field(None, ge=0.0, description="Processing rate in frames per second")
    resource_usage: Optional[Dict[str, Any]] = Field(None, description="Resource usage metrics (CPU, memory, etc.)")
    stage_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional stage-specific metadata")


class ErrorLogEntry(BaseModel):
    """
    Detailed error log entry with context and recovery information.
    """
    error_id: str = Field(..., description="Unique identifier for this error")
    error_type: str = Field(..., description="Type of error (processing, validation, system, etc.)")
    error_code: str = Field(..., description="Specific error code")
    error_message: str = Field(..., description="Human-readable error message")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Detailed error information")
    affected_stage: Optional[str] = Field(None, description="Processing stage where error occurred")
    timestamp: datetime = Field(..., description="When the error occurred")
    severity: str = Field(default="error", description="Error severity (info, warning, error, critical)")
    recovery_action: Optional[str] = Field(None, description="Action taken to recover from error")
    stack_trace: Optional[str] = Field(None, description="Stack trace for debugging")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context information")


class RetryAttemptRecord(BaseModel):
    """
    Record of retry attempts with outcomes and timing.
    """
    retry_attempt_number: int = Field(..., ge=1, description="Retry attempt number (1, 2, 3, etc.)")
    retry_reason: str = Field(..., description="Reason for the retry attempt")
    retry_timestamp: datetime = Field(..., description="When the retry attempt was made")
    retry_duration_seconds: Optional[float] = Field(None, ge=0.0, description="Duration of the retry attempt")
    retry_outcome: str = Field(..., description="Outcome of the retry (success, failure, partial)")
    retry_error: Optional[ErrorLogEntry] = Field(None, description="Error that occurred during retry")
    retry_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional retry information")


class PerformanceMetricsHistory(BaseModel):
    """
    Historical performance metrics for analysis tracking.
    """
    timestamp: datetime = Field(..., description="When these metrics were recorded")
    total_processing_time_seconds: float = Field(..., ge=0.0, description="Total processing time")
    stage_processing_times: Dict[str, float] = Field(default_factory=dict, description="Processing time per stage")
    throughput_fps: Optional[float] = Field(None, ge=0.0, description="Overall throughput in frames per second")
    cpu_usage_percent: Optional[float] = Field(None, ge=0.0, le=100.0, description="Average CPU usage percentage")
    memory_usage_mb: Optional[float] = Field(None, ge=0.0, description="Peak memory usage in MB")
    gpu_usage_percent: Optional[float] = Field(None, ge=0.0, le=100.0, description="GPU usage percentage if applicable")
    disk_io_mb: Optional[float] = Field(None, ge=0.0, description="Disk I/O in MB")
    network_io_mb: Optional[float] = Field(None, ge=0.0, description="Network I/O in MB")
    efficiency_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Overall processing efficiency score")


class AnalysisHistoryRecord(BaseModel):
    """
    Complete historical record for an analysis with all audit trail information.
    """
    analysis_id: UUID = Field(..., description="Analysis identifier")
    record_timestamp: datetime = Field(..., description="When this history record was created")
    analysis_status: DetectionStatus = Field(..., description="Status of the analysis")
    processing_stages: List[ProcessingStageHistory] = Field(default_factory=list, description="History of processing stages")
    error_logs: List[ErrorLogEntry] = Field(default_factory=list, description="All error log entries")
    retry_attempts: List[RetryAttemptRecord] = Field(default_factory=list, description="All retry attempts")
    performance_metrics: List[PerformanceMetricsHistory] = Field(default_factory=list, description="Performance metrics over time")
    total_processing_time_seconds: Optional[float] = Field(None, ge=0.0, description="Total analysis processing time")
    total_errors: int = Field(default=0, ge=0, description="Total number of errors encountered")
    total_retries: int = Field(default=0, ge=0, description="Total number of retry attempts")
    success_rate: Optional[float] = Field(None, ge=0.0, le=1.0, description="Overall success rate")
    analysis_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional analysis metadata")


class HistoryFilterOptions(BaseModel):
    """
    Filtering options for analysis history queries.
    """
    start_date: Optional[datetime] = Field(None, description="Filter records from this date onwards")
    end_date: Optional[datetime] = Field(None, description="Filter records up to this date")
    stage_filter: Optional[List[str]] = Field(None, description="Filter by specific processing stages")
    error_type_filter: Optional[List[str]] = Field(None, description="Filter by error types")
    severity_filter: Optional[List[str]] = Field(None, description="Filter by error severity levels")
    status_filter: Optional[List[DetectionStatus]] = Field(None, description="Filter by analysis status")
    min_duration_seconds: Optional[float] = Field(None, ge=0.0, description="Minimum processing duration")
    max_duration_seconds: Optional[float] = Field(None, ge=0.0, description="Maximum processing duration")


class HistorySortOptions(BaseModel):
    """
    Sorting options for analysis history queries.
    """
    sort_field: str = Field(default="record_timestamp", description="Field to sort by")
    sort_order: str = Field(default="desc", description="Sort order (asc, desc)")


class HistoryPaginationOptions(BaseModel):
    """
    Pagination options for analysis history queries.
    """
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    page_size: int = Field(default=50, ge=1, le=1000, description="Number of records per page")
    max_records: Optional[int] = Field(None, ge=1, description="Maximum total records to return")


class AnalysisHistoryResponse(BaseModel):
    """
    Response model for analysis history endpoint with pagination and metadata.
    """
    analysis_id: UUID = Field(..., description="Analysis identifier")
    total_records: int = Field(..., ge=0, description="Total number of history records")
    current_page: int = Field(..., ge=1, description="Current page number")
    total_pages: int = Field(..., ge=1, description="Total number of pages")
    page_size: int = Field(..., ge=1, description="Records per page")
    has_next_page: bool = Field(..., description="Whether there are more pages")
    has_previous_page: bool = Field(..., description="Whether there are previous pages")
    history_records: List[AnalysisHistoryRecord] = Field(..., description="History records for current page")
    summary_metrics: Optional[Dict[str, Any]] = Field(None, description="Summary metrics across all records")
    cache_info: Optional[Dict[str, Any]] = Field(None, description="Redis cache information")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Response generation timestamp")


# Export all models and utility functions
__all__ = [
    'DetectionStatus',
    'ProcessingStage',
    'VideoDetectionRequest',
    'DetectionResponse',
    'DetectionStatusResponse',
    'DetailedDetectionStatusResponse',
    'ProcessingStageDetails',
    'FrameProgressInfo',
    'ErrorRecoveryStatus',
    'ProcessingMetrics',
    'FrameAnalysis',
    'SuspiciousRegion',
    'HeatmapData',
    'InteractiveFrameNavigation',
    'EnhancedConfidenceVisualization',
    'BlockchainVerificationStatus',
    'DownloadableReportMetadata',
    'DetectionResultsResponse',
    'DetectionErrorResponse',
    'DetectionConfig',
    'DetectionStats',
    'validate_video_file',
    'validate_file_size',
    'create_detection_response',
    'create_status_response',
    'create_results_response',
    'ProcessingStageHistory',
    'ErrorLogEntry',
    'RetryAttemptRecord',
    'PerformanceMetricsHistory',
    'AnalysisHistoryRecord',
    'HistoryFilterOptions',
    'HistorySortOptions',
    'HistoryPaginationOptions',
    'AnalysisHistoryResponse'
]
