from pydantic import BaseModel, Field, validator
from fastapi import UploadFile
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from enum import Enum

class ModelType(str, Enum):
    """
    Enumeration of supported model types for training and detection.
    """
    RESNET50 = "resnet50"
    CLIP = "clip"
    ENSEMBLE = "ensemble"
    DIFFUSION_AWARE = "diffusion_aware"

class VideoDetectionRequest(BaseModel):
    """
    Request model for video deepfake detection.
    """
    file: UploadFile = Field(..., description="The video file to be uploaded for detection. Supported formats: MP4, AVI.")
    user_id: Optional[UUID] = Field(None, description="Optional user identifier for tracking.")
    metadata: Optional[dict] = Field(None, description="Additional metadata about the video (e.g., source, timestamp).")

    @validator('file')
    def validate_file(cls, v):
        supported_formats = ['mp4', 'avi', 'mov', 'mkv', 'webm']
        if v.filename.split('.')[-1].lower() not in supported_formats:
            raise ValueError(f"Unsupported file format. Supported formats: {', '.join(supported_formats).upper()}")
        return v

class DetectionResponse(BaseModel):
    """
    Response model for deepfake detection results.
    """
    detection_id: UUID = Field(..., description="Unique identifier for the detection result.")
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score of deepfake detection (0.0 = real, 1.0 = fake).")
    is_fake: bool = Field(..., description="Boolean flag indicating if the video is detected as fake.")
    details: dict = Field(..., description="Detailed analysis, e.g., {'frame_artifacts': [...], 'confidence_per_frame': [...]}.")
    timestamp: datetime = Field(..., description="Timestamp when the detection was completed.")
    blockchain_hash: Optional[str] = Field(None, description="Solana blockchain hash for tamper-proof verification.")

class TrainingRequest(BaseModel):
    """
    Request model for initiating model training or fine-tuning.
    """
    dataset_path: str = Field(..., description="Path or URL to the training dataset (e.g., local dir or S3 bucket).")
    epochs: int = Field(10, ge=1, le=100, description="Number of training epochs.")
    batch_size: int = Field(32, ge=1, le=128, description="Batch size for training.")
    learning_rate: float = Field(0.001, gt=0.0, description="Initial learning rate for optimizer.")
    model_type: ModelType = Field(ModelType.ENSEMBLE, description="Type of model to train.")

class StatusUpdate(BaseModel):
    """
    Model for updating status during processing (e.g., via WebSocket).
    """
    detection_id: UUID = Field(..., description="Identifier of the detection process being updated.")
    status: str = Field(..., description="Current status (e.g., 'processing', 'completed', 'error').")
    progress: float = Field(0.0, ge=0.0, le=1.0, description="Progress percentage (0.0 to 1.0).")
    message: Optional[str] = Field(None, description="Additional status message or error details.")

class ResultUpdate(BaseModel):
    """
    Model for updating detection results incrementally (e.g., per frame).
    """
    detection_id: UUID = Field(..., description="Identifier of the detection result being updated.")
    frame_number: Optional[int] = Field(None, ge=0, description="Frame number for partial updates (if applicable).")
    partial_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Intermediate detection score for the frame or segment.")
    details: Optional[dict] = Field(None, description="Partial analysis details (e.g., {'artifacts_detected': True}).")
    timestamp: datetime = Field(..., description="Timestamp of the update.")

class ErrorResponse(BaseModel):
    """
    Standardized error response model for API errors.
    """
    error_code: str = Field(..., description="Unique error code for the specific error type.")
    message: str = Field(..., description="Human-readable error message.")
    details: Optional[dict] = Field(None, description="Additional error details or context.")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the error occurred.")

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
    reset_time: datetime = Field(..., description="Time when the rate limit resets.")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retrying (if rate limited).")