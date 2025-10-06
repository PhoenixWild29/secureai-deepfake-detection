from pydantic import BaseModel, Field, validator
from fastapi import UploadFile
from uuid import UUID
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import os

class ModelType(str, Enum):
    """
    Enumeration of supported model types for training and detection.
    """
    RESNET50 = "resnet50"
    CLIP = "clip"
    ENSEMBLE = "ensemble"
    DIFFUSION_AWARE = "diffusion_aware"

class StatusEnum(str, Enum):
    """
    Enumeration of possible processing statuses.
    """
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    PENDING = "pending"

class ErrorCodeEnum(str, Enum):
    """
    Enumeration of standardized error codes for API responses.
    """
    VALIDATION_ERROR = "VALIDATION_ERROR"
    FILE_PROCESSING_ERROR = "FILE_PROCESSING_ERROR"
    MODEL_INFERENCE_ERROR = "MODEL_INFERENCE_ERROR"
    BLOCKCHAIN_ERROR = "BLOCKCHAIN_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    NOT_FOUND = "NOT_FOUND"

class DetectionDetails(BaseModel):
    """
    Structured details for detection analysis results.
    """
    confidence_per_frame: Optional[List[float]] = Field(None, description="Confidence scores for each analyzed frame.")
    frame_artifacts: Optional[List[str]] = Field(None, description="Detected artifacts or manipulation indicators per frame.")
    processing_time_seconds: Optional[float] = Field(None, description="Total processing time in seconds.")
    model_used: Optional[str] = Field(None, description="Name of the model used for detection.")

class VideoMetadata(BaseModel):
    """
    Structured metadata for video files.
    """
    source: Optional[str] = Field(None, description="Source of the video (e.g., 'upload', 'url', 'camera').")
    tags: Optional[List[str]] = Field(None, description="User-defined tags for categorization.")
    original_filename: Optional[str] = Field(None, description="Original filename before processing.")
    upload_timestamp: Optional[datetime] = Field(None, description="When the video was uploaded.")

class ErrorDetails(BaseModel):
    """
    Structured details for error context.
    """
    field_name: Optional[str] = Field(None, description="Name of the field that caused the error.")
    provided_value: Optional[Any] = Field(None, description="The invalid value that was provided.")
    expected_format: Optional[str] = Field(None, description="Description of the expected format.")
    additional_context: Optional[Dict[str, Any]] = Field(None, description="Any additional error context.")

class VideoDetectionRequest(BaseModel):
    """
    Request model for video deepfake detection.
    """
    file: UploadFile = Field(..., description="The video file to be uploaded for detection. Supported formats: MP4, AVI, MOV, MKV, WebM.")
    user_id: Optional[UUID] = Field(None, description="Optional user identifier for tracking.")
    metadata: Optional[VideoMetadata] = Field(None, description="Additional structured metadata about the video.")

    @validator('file')
    def validate_file(cls, v):
        supported_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        file_extension = os.path.splitext(v.filename)[1].lower()
        if file_extension not in supported_extensions:
            raise ValueError(f"Unsupported file format. Supported formats: {', '.join(ext.upper() for ext in supported_extensions)}")
        return v

class DetectionResponse(BaseModel):
    """
    Response model for deepfake detection results.
    """
    detection_id: UUID = Field(..., description="Unique identifier for the detection result.")
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score of deepfake detection (0.0 = real, 1.0 = fake).")
    is_fake: bool = Field(..., description="Boolean flag indicating if the video is detected as fake.")
    details: DetectionDetails = Field(..., description="Structured analysis details including frame-level information.")
    timestamp: datetime = Field(..., description="Timestamp when the detection was completed.")
    blockchain_hash: Optional[str] = Field(None, description="Solana blockchain hash for tamper-proof verification.")

class TrainingRequest(BaseModel):
    """
    Request model for initiating model training or fine-tuning.
    """
    dataset_path: str = Field(..., description="Path or URL to the training dataset (e.g., local directory or S3 bucket).")
    epochs: int = Field(50, ge=1, le=1000, description="Number of training epochs (recommended: 50-200 for convergence).")
    batch_size: int = Field(16, ge=1, le=128, description="Batch size for training (recommended: 8-32 based on GPU memory).")
    learning_rate: float = Field(0.001, gt=0.0, description="Initial learning rate for optimizer (recommended: 0.001-0.0001).")
    model_type: ModelType = Field(ModelType.ENSEMBLE, description="Type of model to train.")

    @validator('dataset_path')
    def validate_dataset_path(cls, v):
        if not v or not v.strip():
            raise ValueError("Dataset path cannot be empty")
        # Basic validation for URL or file path format
        if not (v.startswith(('http://', 'https://', 's3://')) or os.path.exists(v) or os.path.isdir(os.path.dirname(v))):
            raise ValueError("Dataset path must be a valid URL, S3 path, or existing directory")
        return v

class StatusUpdate(BaseModel):
    """
    Model for updating status during processing (e.g., via WebSocket).
    """
    detection_id: UUID = Field(..., description="Identifier of the detection process being updated.")
    status: StatusEnum = Field(..., description="Current processing status.")
    progress: float = Field(0.0, ge=0.0, le=1.0, description="Progress percentage (0.0 to 1.0).")
    message: Optional[str] = Field(None, description="Additional status message or error details.")

class ResultUpdate(BaseModel):
    """
    Model for updating detection results incrementally (e.g., per frame).
    """
    detection_id: UUID = Field(..., description="Identifier of the detection result being updated.")
    frame_number: Optional[int] = Field(None, ge=0, description="Frame number for partial updates (if applicable).")
    partial_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Intermediate detection score for the frame or segment.")
    details: Optional[DetectionDetails] = Field(None, description="Partial structured analysis details.")
    timestamp: datetime = Field(..., description="Timestamp of the update.")

class ErrorResponse(BaseModel):
    """
    Standardized error response model for API errors.
    """
    error_code: ErrorCodeEnum = Field(..., description="Unique error code for the specific error type.")
    message: str = Field(..., description="Human-readable error message.")
    details: Optional[ErrorDetails] = Field(None, description="Structured error details and context.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the error occurred (UTC).")

class PaginationInfo(BaseModel):
    """
    Pagination information for list responses.
    """
    page: int = Field(1, ge=1, description="Current page number.")
    page_size: int = Field(50, ge=1, le=1000, description="Number of items per page.")
    total_items: int = Field(..., ge=0, description="Total number of items available.")
    total_pages: int = Field(..., ge=0, description="Total number of pages available.")

class BatchDetectionResponse(BaseModel):
    """
    Response model for batch detection results with pagination.
    """
    results: List[DetectionResponse] = Field(..., description="List of detection results.")
    pagination: PaginationInfo = Field(..., description="Pagination information for the results.")

class RateLimitInfo(BaseModel):
    """
    Rate limiting information for API responses.
    """
    limit: int = Field(..., description="Maximum number of requests allowed per time window.")
    remaining: int = Field(..., description="Number of requests remaining in the current time window.")
    reset_time: datetime = Field(..., description="Time when the rate limit resets (UTC).")
    retry_after: Optional[timedelta] = Field(None, description="Time to wait before retrying (if rate limited).")

    @validator('retry_after')
    def validate_retry_after(cls, v):
        if v is not None and v.total_seconds() < 0:
            raise ValueError("retry_after must be a non-negative timedelta")
        return v