#!/usr/bin/env python3
"""
SecureAI DeepFake Detection API Schemas
Pydantic models for API request/response validation and automatic OpenAPI documentation generation
"""

from pydantic import BaseModel, Field, validator
from fastapi import UploadFile
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum


class ModelType(str, Enum):
    """Enumeration of supported model types for training."""
    RESNET50 = "resnet50"
    CLIP = "clip"
    ENSEMBLE = "ensemble"
    DIFFUSION_AWARE = "diffusion_aware"


class StatusEnum(str, Enum):
    """Enumeration of possible processing statuses."""
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    PENDING = "pending"


class VideoDetectionRequest(BaseModel):
    """
    Request model for video deepfake detection.
    Includes UploadFile field for video files, options Dict for detection configuration, 
    and optional priority field with validation.
    """
    file: UploadFile = Field(..., description="The video file to be uploaded for detection. Supported formats: MP4, AVI, MOV, MKV, WebM.")
    options: Dict[str, Any] = Field(default_factory=dict, description="Detection configuration options and parameters.")
    priority: Optional[int] = Field(None, ge=1, le=10, description="Optional priority level for processing (1=lowest, 10=highest).")

    @validator('file')
    def validate_file(cls, v):
        """Validate that the uploaded file has a supported extension."""
        supported_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        if v.filename:
            file_extension = v.filename.lower().split('.')[-1]
            if f'.{file_extension}' not in supported_extensions:
                raise ValueError(f"Unsupported file format. Supported formats: {', '.join(ext.upper() for ext in supported_extensions)}")
        return v


class DetectionResponse(BaseModel):
    """
    Response model for deepfake detection results.
    Includes analysis_id (UUID), status string, optional overall_confidence (0.0-1.0), 
    blockchain_hash, details Dict, processing_time_ms, and created_at timestamp.
    """
    analysis_id: UUID = Field(..., description="Unique identifier for the analysis result.")
    status: str = Field(..., description="Current status of the analysis (processing, completed, error).")
    overall_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Overall confidence score for the detection (0.0 = real, 1.0 = fake).")
    blockchain_hash: Optional[str] = Field(None, description="Blockchain hash for tamper-proof verification of the result.")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed analysis results and metadata.")
    processing_time_ms: int = Field(..., ge=0, description="Processing time in milliseconds.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the analysis was created (UTC).")


class TrainingRequest(BaseModel):
    """
    Request model for initiating model training or fine-tuning.
    Includes dataset_path string, model_type string, hyperparameters Dict, 
    and validation_threshold float (0.0-1.0) with default 0.95.
    """
    dataset_path: str = Field(..., description="Path or URL to the training dataset (e.g., local directory or S3 bucket).")
    model_type: str = Field(..., description="Type of model to train (resnet50, clip, ensemble, diffusion_aware).")
    hyperparameters: Dict[str, Any] = Field(default_factory=dict, description="Training hyperparameters and configuration options.")
    validation_threshold: float = Field(0.95, ge=0.0, le=1.0, description="Validation threshold for model performance (default: 0.95).")

    @validator('dataset_path')
    def validate_dataset_path(cls, v):
        """Validate that the dataset path is not empty."""
        if not v or not v.strip():
            raise ValueError("Dataset path cannot be empty")
        return v

    @validator('model_type')
    def validate_model_type(cls, v):
        """Validate that the model type is supported."""
        supported_types = ['resnet50', 'clip', 'ensemble', 'diffusion_aware']
        if v.lower() not in supported_types:
            raise ValueError(f"Unsupported model type. Supported types: {', '.join(supported_types)}")
        return v.lower()


class StatusUpdate(BaseModel):
    """
    Model for updating status during processing.
    Includes task_id, analysis_id (UUID), progress float (0.0-1.0), stage string, 
    message string, optional estimated_completion datetime, and optional error string.
    """
    task_id: str = Field(..., description="Unique identifier for the task being updated.")
    analysis_id: UUID = Field(..., description="Unique identifier for the analysis being updated.")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress percentage (0.0 to 1.0).")
    stage: str = Field(..., description="Current processing stage (e.g., 'uploading', 'analyzing', 'finalizing').")
    message: str = Field(..., description="Status message or description of current progress.")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time for the task.")
    error: Optional[str] = Field(None, description="Error message if the task encountered an issue.")


class ResultUpdate(BaseModel):
    """
    Model for updating detection results incrementally.
    Includes analysis_id (UUID), confidence_score float (0.0-1.0), frames_processed int, 
    total_frames int, suspicious_regions List, and optional blockchain_hash.
    """
    analysis_id: UUID = Field(..., description="Unique identifier for the analysis result being updated.")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score for the detection (0.0 = real, 1.0 = fake).")
    frames_processed: int = Field(..., ge=0, description="Number of frames that have been processed.")
    total_frames: int = Field(..., ge=0, description="Total number of frames in the video.")
    suspicious_regions: List[Dict[str, Any]] = Field(default_factory=list, description="List of suspicious regions detected in the video.")
    blockchain_hash: Optional[str] = Field(None, description="Blockchain hash for tamper-proof verification of the result.")

    @validator('frames_processed')
    def validate_frames_processed(cls, v, values):
        """Validate that frames_processed does not exceed total_frames."""
        if 'total_frames' in values and v > values['total_frames']:
            raise ValueError("frames_processed cannot exceed total_frames")
        return v


# Additional utility models for enhanced API functionality

class ErrorResponse(BaseModel):
    """
    Standardized error response model for API errors.
    """
    error_code: str = Field(..., description="Unique error code for the specific error type.")
    message: str = Field(..., description="Human-readable error message.")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details and context.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the error occurred (UTC).")


class HealthCheckResponse(BaseModel):
    """
    Response model for health check endpoint.
    """
    status: str = Field(..., description="Overall system status.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of the health check (UTC).")
    version: str = Field(..., description="API version.")
    components: Dict[str, str] = Field(default_factory=dict, description="Status of individual system components.")


class BatchProcessingRequest(BaseModel):
    """
    Request model for batch video processing.
    """
    video_files: List[UploadFile] = Field(..., description="List of video files to process in batch.")
    options: Dict[str, Any] = Field(default_factory=dict, description="Processing options for the batch.")
    priority: Optional[int] = Field(None, ge=1, le=10, description="Priority level for batch processing.")


class BatchProcessingResponse(BaseModel):
    """
    Response model for batch processing results.
    """
    batch_id: UUID = Field(..., description="Unique identifier for the batch processing job.")
    total_videos: int = Field(..., ge=0, description="Total number of videos in the batch.")
    processed_videos: int = Field(..., ge=0, description="Number of videos that have been processed.")
    failed_videos: int = Field(..., ge=0, description="Number of videos that failed processing.")
    status: str = Field(..., description="Current status of the batch processing.")
    results: List[DetectionResponse] = Field(default_factory=list, description="List of individual detection results.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the batch was created (UTC).")


# Presigned URL Upload Schemas

class PresignedUrlRequest(BaseModel):
    """
    Request model for generating presigned upload URLs.
    """
    filename: str = Field(..., min_length=1, max_length=255, description="Original filename of the file to upload.")
    content_type: str = Field(..., description="MIME content type of the file (e.g., video/mp4).")
    file_size: int = Field(..., gt=0, description="Size of the file in bytes.")
    expires_in: Optional[int] = Field(3600, ge=300, le=86400, description="URL expiration time in seconds (300-86400, default: 3600).")


class PresignedUrlResponse(BaseModel):
    """
    Response model for presigned URL generation.
    """
    success: bool = Field(..., description="Whether the request was successful.")
    data: 'PresignedUrlData' = Field(..., description="Presigned URL data and upload details.")
    warnings: Optional[List[str]] = Field(None, description="Optional warnings from file validation.")


class PresignedUrlData(BaseModel):
    """
    Data model for presigned URL response.
    """
    presigned_url: str = Field(..., description="Presigned URL for direct upload to S3.")
    upload_url: str = Field(..., description="Direct S3 upload URL.")
    s3_key: str = Field(..., description="S3 object key where the file will be stored.")
    bucket: str = Field(..., description="S3 bucket name.")
    region: str = Field(..., description="AWS region.")
    expires_at: str = Field(..., description="ISO timestamp when the URL expires.")
    expires_in: int = Field(..., description="URL expiration time in seconds.")
    required_headers: Dict[str, str] = Field(..., description="Required HTTP headers for the upload request.")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Metadata that will be attached to the S3 object.")


class PresignedPostRequest(BaseModel):
    """
    Request model for generating presigned POST URLs.
    """
    filename: str = Field(..., min_length=1, max_length=255, description="Original filename of the file to upload.")
    content_type: str = Field(..., description="MIME content type of the file (e.g., video/mp4).")
    file_size: int = Field(..., gt=0, description="Size of the file in bytes.")
    expires_in: Optional[int] = Field(3600, ge=300, le=86400, description="URL expiration time in seconds (300-86400, default: 3600).")


class PresignedPostResponse(BaseModel):
    """
    Response model for presigned POST generation.
    """
    success: bool = Field(..., description="Whether the request was successful.")
    data: 'PresignedPostData' = Field(..., description="Presigned POST data and upload details.")
    warnings: Optional[List[str]] = Field(None, description="Optional warnings from file validation.")


class PresignedPostData(BaseModel):
    """
    Data model for presigned POST response.
    """
    presigned_post: Dict[str, Any] = Field(..., description="Presigned POST form data for multipart upload.")
    upload_url: str = Field(..., description="S3 POST endpoint URL.")
    s3_key: str = Field(..., description="S3 object key where the file will be stored.")
    bucket: str = Field(..., description="S3 bucket name.")
    region: str = Field(..., description="AWS region.")
    expires_at: str = Field(..., description="ISO timestamp when the POST data expires.")
    expires_in: int = Field(..., description="POST data expiration time in seconds.")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Metadata that will be attached to the S3 object.")


class UploadVerificationResponse(BaseModel):
    """
    Response model for upload verification.
    """
    success: bool = Field(..., description="Whether the verification was successful.")
    data: 'UploadVerificationData' = Field(..., description="Upload verification results.")


class UploadVerificationData(BaseModel):
    """
    Data model for upload verification results.
    """
    exists: bool = Field(..., description="Whether the file exists in S3.")
    size: Optional[int] = Field(None, description="File size in bytes if it exists.")
    last_modified: Optional[str] = Field(None, description="ISO timestamp of last modification if it exists.")
    etag: Optional[str] = Field(None, description="ETag of the file if it exists.")
    content_type: Optional[str] = Field(None, description="Content type of the file if it exists.")
    metadata: Optional[Dict[str, str]] = Field(None, description="File metadata if it exists.")
    s3_url: Optional[str] = Field(None, description="Direct S3 URL to the file if it exists.")
    error: Optional[str] = Field(None, description="Error message if verification failed.")


class UploadConfigResponse(BaseModel):
    """
    Response model for upload configuration.
    """
    success: bool = Field(..., description="Whether the request was successful.")
    data: 'UploadConfigData' = Field(..., description="Upload configuration details.")


class UploadConfigData(BaseModel):
    """
    Data model for upload configuration.
    """
    max_file_size: int = Field(..., description="Maximum allowed file size in bytes.")
    max_file_size_formatted: str = Field(..., description="Human-readable maximum file size.")
    allowed_content_types: List[str] = Field(..., description="List of allowed MIME content types.")
    allowed_extensions: List[str] = Field(..., description="List of allowed file extensions.")
    default_url_expiration: int = Field(..., description="Default URL expiration time in seconds.")
    min_url_expiration: int = Field(..., description="Minimum allowed URL expiration time in seconds.")
    max_url_expiration: int = Field(..., description="Maximum allowed URL expiration time in seconds.")
    bucket_region: str = Field(..., description="S3 bucket region.")
    supports_presigned_urls: bool = Field(..., description="Whether presigned URLs are supported.")
    supports_presigned_posts: bool = Field(..., description="Whether presigned POSTs are supported.")


# Update forward references
PresignedUrlResponse.model_rebuild()
PresignedPostResponse.model_rebuild()
UploadVerificationResponse.model_rebuild()
UploadConfigResponse.model_rebuild()
