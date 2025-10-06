#!/usr/bin/env python3
"""
Core Detection Data Models with Blockchain Integration
SQLModel classes for video storage, analysis tracking, detection results, and frame-level analysis.
"""

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, CheckConstraint, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from uuid import uuid4, UUID as PyUUID
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum
from decimal import Decimal


class AnalysisStatusEnum(str, Enum):
	QUEUED = "queued"
	PROCESSING = "processing"
	COMPLETED = "completed"
	FAILED = "failed"


class Video(SQLModel, table=True):
	"""
	Video table: uploaded video metadata and ownership
	"""
	__tablename__ = "video"
	__table_args__ = (
		UniqueConstraint("file_hash", name="uq_video_file_hash"),
		Index("idx_video_file_hash", "file_hash"),
	)

	# Primary key
	id: PyUUID = Field(
		default_factory=uuid4,
		sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
	)

	# File metadata
	filename: str = Field(max_length=255, description="Original filename of the uploaded video")
	file_hash: str = Field(max_length=64, description="SHA256 or similar hash of the file contents (dedupe key)")
	file_size: int = Field(ge=0, description="Size of the video file in bytes")
	format: str = Field(max_length=10, description="Short format string (e.g., mp4, avi)")
	s3_key: Optional[str] = Field(default=None, max_length=512, description="S3 object key or storage path")

	# Audit / ownership
	upload_timestamp: datetime = Field(
		default_factory=lambda: datetime.now(timezone.utc),
		sa_column=Column(DateTime(timezone=True), server_default=func.now())
	)
	user_id: Optional[PyUUID] = Field(
		default=None,
		sa_column=Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True),
		description="Foreign key to User who uploaded the video"
	)

	# Relationships
	analyses: List["Analysis"] = Relationship(back_populates="video")


class Analysis(SQLModel, table=True):
	"""
	Analysis table: tracks processing lifecycle for a video
	"""
	__tablename__ = "analysis"
	__table_args__ = (
		Index("idx_analysis_video_id", "video_id"),
		Index("idx_analysis_status", "status"),
	)

	# Primary key
	id: PyUUID = Field(
		default_factory=uuid4,
		sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
	)

	# Foreign key to Video
	video_id: PyUUID = Field(
		sa_column=Column(UUID(as_uuid=True), ForeignKey("video.id")),
		description="Foreign key to Video being analyzed"
	)
	video: Optional[Video] = Relationship(back_populates="analyses")

	# Processing status
	status: AnalysisStatusEnum = Field(default=AnalysisStatusEnum.QUEUED, description="Current analysis status")
	model_version: Optional[str] = Field(default=None, max_length=50, description="Model version used for analysis")

	# Timestamps
	created_at: datetime = Field(
		default_factory=lambda: datetime.now(timezone.utc),
		sa_column=Column(DateTime(timezone=True), server_default=func.now())
	)
	started_at: Optional[datetime] = Field(default=None, description="When analysis started")
	completed_at: Optional[datetime] = Field(default=None, description="When analysis completed")

	# Error and metrics
	error_message: Optional[str] = Field(default=None, sa_column=Column(Text), description="Error details if failed")
	processing_time_ms: Optional[int] = Field(default=None, ge=0, description="Processing time in milliseconds")

	# Relationships
	results: List["DetectionResult"] = Relationship(back_populates="analysis")


class DetectionResult(SQLModel, table=True):
	"""
	Detection result for an analysis with blockchain hash and aggregated metrics
	"""
	__tablename__ = "detection_result"

	# Primary key
	id: PyUUID = Field(
		default_factory=uuid4,
		sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
	)

	# Foreign key to Analysis
	analysis_id: PyUUID = Field(
		sa_column=Column(UUID(as_uuid=True), ForeignKey("analysis.id")),
		description="Foreign key to Analysis"
	)
	analysis: Optional[Analysis] = Relationship(back_populates="results")

	# Scores and counts
	overall_confidence: Decimal = Field(
		ge=0.0,
		le=1.0,
		description="Overall confidence (0.0..1.0)",
	)
	frame_count: int = Field(ge=0, description="Total frames analyzed")
	suspicious_frames: int = Field(ge=0, description="Number of frames flagged as suspicious")

	# Blockchain and metadata
	blockchain_hash: str = Field(max_length=64, description="Blockchain transaction hash for verification")
	artifacts_detected: Optional[dict] = Field(default=None, sa_column=Column(JSONB), description="Detected artifacts summary")
	processing_metadata: Optional[dict] = Field(default=None, sa_column=Column(JSONB), description="Additional processing metadata")

	# Audit
	created_at: datetime = Field(
		default_factory=lambda: datetime.now(timezone.utc),
		sa_column=Column(DateTime(timezone=True), server_default=func.now())
	)

	# Constraints
	__table_args__ = (
		UniqueConstraint("blockchain_hash", name="uq_result_blockchain_hash"),
		CheckConstraint("overall_confidence >= 0.0 AND overall_confidence <= 1.0", name="ck_overall_conf_range"),
		Index("idx_result_analysis_id", "analysis_id"),
	)


class FrameAnalysis(SQLModel, table=True):
	"""
	Frame-level analysis details for a detection result
	"""
	__tablename__ = "frame_analysis"
	__table_args__ = (
		Index("idx_frame_result_id", "result_id"),
		Index("idx_frame_frame_number", "frame_number"),
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
	result: Optional[DetectionResult] = Relationship()

	# Frame metrics
	frame_number: int = Field(ge=0, description="Frame number")
	confidence_score: Decimal = Field(ge=0.0, le=1.0, description="Confidence score for the frame (0.0..1.0)")
	suspicious_regions: Optional[dict] = Field(default=None, sa_column=Column(JSONB), description="Region annotations for suspicious areas")
	artifacts: Optional[dict] = Field(default=None, sa_column=Column(JSONB), description="Artifacts detected at frame-level")
	processing_time_ms: Optional[int] = Field(default=None, ge=0, description="Processing time for this frame in ms")
