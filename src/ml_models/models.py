#!/usr/bin/env python3
"""
ML Pipeline Data Models for SecureAI DeepFake Detection
SQLModel classes for model versioning, embedding caching, training data exports, and performance monitoring
"""

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Index, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from uuid import uuid4, UUID as PyUUID
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal


class ModelTypeEnum(str, Enum):
    """Enumeration of supported model types"""
    RESNET50 = "resnet50"
    CLIP = "clip"
    ENSEMBLE = "ensemble"


class DataClassificationEnum(str, Enum):
    """Enumeration of data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"


class ExportStatusEnum(str, Enum):
    """Enumeration of export status values"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class MLModelVersion(SQLModel, table=True):
    """
    ML Model Version table for tracking model versions, metrics, and deployment status
    """
    __tablename__ = "ml_model_version"
    
    # Primary key
    id: PyUUID = Field(
        default_factory=uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    
    # Model identification
    version: str = Field(
        max_length=50,
        unique=True,
        index=True,
        description="Model version identifier (e.g., 'v1.2.3')"
    )
    
    model_type: ModelTypeEnum = Field(
        description="Type of ML model (resnet50, clip, ensemble)"
    )
    
    # Model artifacts and data
    artifact_uri: str = Field(
        max_length=512,
        description="URI to model artifact storage location"
    )
    
    training_data_s3_path: str = Field(
        max_length=512,
        description="S3 path to training data used for this model version"
    )
    
    # Performance metrics
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="JSONB field containing model performance metrics"
    )
    
    # Deployment information
    is_production: bool = Field(
        default=False,
        description="Whether this model version is currently in production"
    )
    
    deployment_timestamp: Optional[datetime] = Field(
        default=None,
        description="Timestamp when model was deployed to production"
    )
    
    # Audit fields
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    
    created_by: PyUUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("user.id")),
        description="Foreign key to User who created this model version"
    )
    
    # Relationships
    embeddings: List["EmbeddingCache"] = Relationship(back_populates="model_version")
    performance_logs: List["ModelPerformanceLog"] = Relationship(back_populates="model_version")


class EmbeddingCache(SQLModel, table=True):
    """
    Embedding Cache table for storing video frame embeddings with vector similarity search
    """
    __tablename__ = "embedding_cache"
    
    # Primary key
    id: PyUUID = Field(
        default_factory=uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    
    # Video reference
    video_hash: str = Field(
        index=True,
        description="Foreign key to Video.file_hash for video identification"
    )
    
    frame_number: int = Field(
        ge=0,
        description="Frame number within the video (0-indexed)"
    )
    
    # Embedding vector (512 dimensions)
    embedding_vector: List[float] = Field(
        sa_column=Column(Vector(512)),
        description="512-dimensional embedding vector for the frame"
    )
    
    # Model version reference
    model_version_id: PyUUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("ml_model_version.id")),
        description="Foreign key to MLModelVersion that generated this embedding"
    )
    
    # Cache management
    redis_cache_key: str = Field(
        max_length=128,
        index=True,
        description="Redis cache key for fast lookup"
    )
    
    cache_expiry: datetime = Field(
        description="Timestamp when this cache entry expires"
    )
    
    # Audit fields
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    
    # Relationships
    model_version: Optional[MLModelVersion] = Relationship(back_populates="embeddings")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_embedding_cache_video_hash", "video_hash"),
        Index("idx_embedding_cache_redis_key", "redis_cache_key"),
        Index("idx_embedding_cache_model_version", "model_version_id"),
        Index("idx_embedding_cache_expiry", "cache_expiry"),
    )


class TrainingDataExport(SQLModel, table=True):
    """
    Training Data Export table for tracking data exports and ETL jobs
    """
    __tablename__ = "training_data_export"
    
    # Primary key
    id: PyUUID = Field(
        default_factory=uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    
    # Export identification
    export_batch_id: str = Field(
        max_length=100,
        unique=True,
        index=True,
        description="Unique identifier for the export batch"
    )
    
    s3_export_path: str = Field(
        max_length=512,
        description="S3 path where exported data is stored"
    )
    
    # Data classification
    data_classification: DataClassificationEnum = Field(
        description="Classification level of the exported data"
    )
    
    # Export statistics
    record_count: int = Field(
        ge=0,
        description="Number of records in the export"
    )
    
    date_range_start: datetime = Field(
        description="Start timestamp of data range included in export"
    )
    
    date_range_end: datetime = Field(
        description="End timestamp of data range included in export"
    )
    
    # Export status
    export_status: ExportStatusEnum = Field(
        default=ExportStatusEnum.PENDING,
        description="Current status of the export process"
    )
    
    glue_job_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="AWS Glue job ID for ETL processing"
    )
    
    # Audit fields
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_training_export_batch_id", "export_batch_id"),
        Index("idx_training_export_status", "export_status"),
        Index("idx_training_export_classification", "data_classification"),
    )


class ModelPerformanceLog(SQLModel, table=True):
    """
    Model Performance Log table for tracking model performance metrics and anomalies
    """
    __tablename__ = "model_performance_log"
    
    # Primary key
    id: PyUUID = Field(
        default_factory=uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    
    # Model version reference
    model_version_id: PyUUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("ml_model_version.id")),
        description="Foreign key to MLModelVersion being evaluated"
    )
    
    # Performance metrics
    detection_accuracy: Decimal = Field(
        sa_column=Column(DECIMAL(5, 4)),
        ge=0.0,
        le=1.0,
        description="Detection accuracy (0.0 to 1.0)"
    )
    
    false_positive_rate: Decimal = Field(
        sa_column=Column(DECIMAL(5, 4)),
        ge=0.0,
        le=1.0,
        description="False positive rate (0.0 to 1.0)"
    )
    
    processing_latency_ms: int = Field(
        ge=0,
        description="Average processing latency in milliseconds"
    )
    
    # Anomaly detection
    anomaly_flag: bool = Field(
        default=False,
        description="Whether this performance log indicates an anomaly"
    )
    
    # Evaluation context
    evaluation_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="Timestamp when evaluation was performed"
    )
    
    evaluation_dataset_size: int = Field(
        ge=0,
        description="Size of dataset used for evaluation"
    )
    
    # Relationships
    model_version: Optional[MLModelVersion] = Relationship(back_populates="performance_logs")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_performance_log_model_version", "model_version_id"),
        Index("idx_performance_log_timestamp", "evaluation_timestamp"),
        Index("idx_performance_log_anomaly", "anomaly_flag"),
    )


class FrameAnalysis(SQLModel, table=True):
	"""
	Frame-level analysis details for a detection result
	"""
	__tablename__ = "frame_analysis"
	__table_args__ = (
		Index("idx_frame_result_id", "result_id"),
		Index("idx_frame_frame_number", "frame_number"),
		Index("idx_frame_result_frame", "result_id", "frame_number"),
	)

	# Primary key
	id: PyUUID = Field(
		default_factory=uuid4,
		sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
	)

	# Foreign key to DetectionResult
	result_id: PyUUID = Field(
		sa_column=Column(UUID(as_uuid=True), ForeignKey("detection_result.id")),
		description="Foreign key to DetectionResult"
	)
	result: Optional["DetectionResult"] = Relationship()

	# Frame metrics
	frame_number: int = Field(ge=0, description="Frame number")
	confidence_score: Decimal = Field(ge=0.0, le=1.0, description="Confidence score for the frame (0.0..1.0)")
	suspicious_regions: Optional[dict] = Field(default=None, sa_column=Column(JSONB), description="Region annotations for suspicious areas")
	artifacts: Optional[dict] = Field(default=None, sa_column=Column(JSONB), description="Artifacts detected at frame-level")
	processing_time_ms: Optional[int] = Field(default=None, ge=0, description="Processing time for this frame in ms")


# Add relationships to MLModelVersion (defined in the class itself)
# MLModelVersion.embeddings: List[EmbeddingCache] = Relationship(back_populates="model_version")
# MLModelVersion.performance_logs: List[ModelPerformanceLog] = Relationship(back_populates="model_version")


# Utility functions for model operations
class ModelOperations:
    """Utility class for common model operations"""
    
    @staticmethod
    def create_model_version(
        version: str,
        model_type: ModelTypeEnum,
        artifact_uri: str,
        training_data_s3_path: str,
        created_by: PyUUID,
        metrics: Optional[Dict[str, Any]] = None
    ) -> MLModelVersion:
        """Create a new model version"""
        return MLModelVersion(
            version=version,
            model_type=model_type,
            artifact_uri=artifact_uri,
            training_data_s3_path=training_data_s3_path,
            created_by=created_by,
            metrics=metrics or {}
        )
    
    @staticmethod
    def create_embedding_cache(
        video_hash: str,
        frame_number: int,
        embedding_vector: List[float],
        model_version_id: PyUUID,
        redis_cache_key: str,
        cache_expiry: datetime
    ) -> EmbeddingCache:
        """Create a new embedding cache entry"""
        return EmbeddingCache(
            video_hash=video_hash,
            frame_number=frame_number,
            embedding_vector=embedding_vector,
            model_version_id=model_version_id,
            redis_cache_key=redis_cache_key,
            cache_expiry=cache_expiry
        )
    
    @staticmethod
    def create_training_export(
        export_batch_id: str,
        s3_export_path: str,
        data_classification: DataClassificationEnum,
        record_count: int,
        date_range_start: datetime,
        date_range_end: datetime,
        glue_job_id: Optional[str] = None
    ) -> TrainingDataExport:
        """Create a new training data export"""
        return TrainingDataExport(
            export_batch_id=export_batch_id,
            s3_export_path=s3_export_path,
            data_classification=data_classification,
            record_count=record_count,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            glue_job_id=glue_job_id
        )
    
    @staticmethod
    def create_performance_log(
        model_version_id: PyUUID,
        detection_accuracy: Decimal,
        false_positive_rate: Decimal,
        processing_latency_ms: int,
        evaluation_dataset_size: int,
        anomaly_flag: bool = False
    ) -> ModelPerformanceLog:
        """Create a new performance log entry"""
        return ModelPerformanceLog(
            model_version_id=model_version_id,
            detection_accuracy=detection_accuracy,
            false_positive_rate=false_positive_rate,
            processing_latency_ms=processing_latency_ms,
            evaluation_dataset_size=evaluation_dataset_size,
            anomaly_flag=anomaly_flag
        )
