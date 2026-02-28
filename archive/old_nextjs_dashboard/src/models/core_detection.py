#!/usr/bin/env python3
"""
Core Detection Engine Data Models
SQLModel classes for Video, Analysis, DetectionResult, and FrameAnalysis tables
"""

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Index, DECIMAL, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from uuid import uuid4, UUID as PyUUID
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal


class AnalysisStatus(str, Enum):
    """Analysis status enumeration"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DetectionType(str, Enum):
    """Detection type enumeration"""
    RESNET50 = "resnet50"
    CLIP = "clip"
    ENSEMBLE = "ensemble"
    DIFFUSION_AWARE = "diffusion_aware"
    LAA_NET = "laa_net"


class VideoStatus(str, Enum):
    """Video upload/processing status"""
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class Video(SQLModel, table=True):
    """
    Video table for storing video metadata and file information
    """
    __tablename__ = "videos"
    
    # Primary key
    id: PyUUID = Field(
        default_factory=uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    
    # User reference
    user_id: str = Field(
        index=True,
        description="User ID who uploaded the video"
    )
    
    # File information
    filename: str = Field(
        max_length=255,
        description="Original filename of the uploaded video"
    )
    
    file_hash: str = Field(
        max_length=64,
        index=True,
        description="SHA-256 hash of the video file for deduplication"
    )
    
    file_size: int = Field(
        ge=0,
        description="File size in bytes"
    )
    
    file_path: str = Field(
        max_length=512,
        description="Storage path to the video file"
    )
    
    # Video metadata
    duration: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(DECIMAL(10, 3)),
        description="Video duration in seconds"
    )
    
    resolution: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Video resolution (e.g., 1920x1080)"
    )
    
    codec: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Video codec information"
    )
    
    fps: Optional[int] = Field(
        default=None,
        ge=0,
        description="Frames per second"
    )
    
    # Processing status
    upload_status: VideoStatus = Field(
        default=VideoStatus.UPLOADING,
        description="Current upload/processing status"
    )
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="Additional video metadata"
    )
    
    # Audit fields
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    )
    
    # Relationships
    analyses: List["Analysis"] = Relationship(back_populates="video")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_video_user_created', 'user_id', 'created_at'),
        Index('idx_video_hash', 'file_hash'),
        Index('idx_video_status', 'upload_status'),
    )


class Analysis(SQLModel, table=True):
    """
    Analysis table for storing analysis requests and results
    """
    __tablename__ = "analyses"
    
    # Primary key
    id: PyUUID = Field(
        default_factory=uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    
    # Video reference
    video_id: PyUUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("videos.id")),
        description="Foreign key to Video table"
    )
    
    # Analysis configuration
    model_type: DetectionType = Field(
        default=DetectionType.ENSEMBLE,
        description="Type of detection model used"
    )
    
    analysis_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="Analysis configuration parameters"
    )
    
    # Status and timing
    status: AnalysisStatus = Field(
        default=AnalysisStatus.QUEUED,
        index=True,
        description="Current analysis status"
    )
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    
    started_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="When analysis started processing"
    )
    
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="When analysis completed"
    )
    
    # Performance metrics
    processing_time: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(DECIMAL(10, 3)),
        description="Total processing time in seconds"
    )
    
    confidence_score: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(DECIMAL(5, 4)),
        ge=0.0,
        le=1.0,
        description="Overall confidence score (0.0-1.0)"
    )
    
    # Error handling
    error_message: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Error message if analysis failed"
    )
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="Additional analysis metadata"
    )
    
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    )
    
    # Relationships
    video: Optional[Video] = Relationship(back_populates="analyses")
    detection_results: List["DetectionResult"] = Relationship(back_populates="analysis")
    frame_analyses: List["FrameAnalysis"] = Relationship(back_populates="analysis")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_analysis_video_id', 'video_id'),
        Index('idx_analysis_status', 'status'),
        Index('idx_analysis_created_at', 'created_at'),
        Index('idx_analysis_completed_at', 'completed_at'),
    )


class DetectionResult(SQLModel, table=True):
    """
    DetectionResult table for storing final detection results
    """
    __tablename__ = "detection_results"
    
    # Primary key
    id: PyUUID = Field(
        default_factory=uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    
    # Analysis reference
    analysis_id: PyUUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("analyses.id")),
        index=True,
        description="Foreign key to Analysis table"
    )
    
    # Detection result
    is_deepfake: bool = Field(
        description="Final detection result (True = deepfake, False = authentic)"
    )
    
    confidence: Decimal = Field(
        sa_column=Column(DECIMAL(5, 4)),
        ge=0.0,
        le=1.0,
        description="Detection confidence score (0.0-1.0)"
    )
    
    detection_type: DetectionType = Field(
        description="Type of detection method used"
    )
    
    # Detailed results
    model_scores: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="Individual model scores and predictions"
    )
    
    detection_details: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="Detailed detection information and artifacts"
    )
    
    # Blockchain verification
    blockchain_hash: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Blockchain transaction hash for verification"
    )
    
    blockchain_verified: bool = Field(
        default=False,
        description="Whether result has been verified on blockchain"
    )
    
    # Audit fields
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    
    # Relationships
    analysis: Optional[Analysis] = Relationship(back_populates="detection_results")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_detection_result_analysis_id', 'analysis_id'),
        Index('idx_detection_result_confidence', 'confidence'),
        Index('idx_detection_result_is_deepfake', 'is_deepfake'),
        Index('idx_detection_result_type', 'detection_type'),
    )


class FrameAnalysis(SQLModel, table=True):
    """
    FrameAnalysis table for storing individual frame analysis results
    """
    __tablename__ = "frame_analyses"
    
    # Primary key
    id: PyUUID = Field(
        default_factory=uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    
    # Analysis reference
    analysis_id: PyUUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("analyses.id")),
        index=True,
        description="Foreign key to Analysis table"
    )
    
    # Frame information
    frame_number: int = Field(
        ge=0,
        description="Frame number within the video (0-indexed)"
    )
    
    timestamp: Decimal = Field(
        sa_column=Column(DECIMAL(10, 3)),
        ge=0.0,
        description="Timestamp of the frame in seconds"
    )
    
    # Detection result for this frame
    is_deepfake: bool = Field(
        description="Frame-level detection result"
    )
    
    confidence: Decimal = Field(
        sa_column=Column(DECIMAL(5, 4)),
        ge=0.0,
        le=1.0,
        description="Frame-level confidence score"
    )
    
    detection_method: DetectionType = Field(
        description="Detection method used for this frame"
    )
    
    # Performance metrics
    processing_time: Decimal = Field(
        sa_column=Column(DECIMAL(8, 4)),
        ge=0.0,
        description="Processing time for this frame in seconds"
    )
    
    # Detailed frame analysis
    frame_features: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="Extracted features and analysis details for the frame"
    )
    
    artifacts_detected: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="Detected manipulation artifacts and their locations"
    )
    
    # Audit fields
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    
    # Relationships
    analysis: Optional[Analysis] = Relationship(back_populates="frame_analyses")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_frame_analysis_analysis_id', 'analysis_id'),
        Index('idx_frame_analysis_frame_number', 'frame_number'),
        Index('idx_frame_analysis_timestamp', 'timestamp'),
        Index('idx_frame_analysis_confidence', 'confidence'),
        Index('idx_frame_analysis_is_deepfake', 'is_deepfake'),
    )
