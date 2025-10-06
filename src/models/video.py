#!/usr/bin/env python3
"""
Video Database Models for SecureAI DeepFake Detection
"""

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from uuid import uuid4, UUID as PyUUID
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum


class VideoStatusEnum(str, Enum):
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    FAILED = "failed"


class VideoFormatEnum(str, Enum):
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    MKV = "mkv"
    WEBM = "webm"


class Video(SQLModel, table=True):
    """Video table for storing video metadata and analysis tracking"""
    __tablename__ = "videos"
    
    id: PyUUID = Field(
        default_factory=uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    
    filename: str = Field(max_length=255, index=True)
    file_hash: str = Field(max_length=64, unique=True, index=True)
    file_size: int = Field(ge=0)
    format: VideoFormatEnum = Field()
    
    s3_key: str = Field(max_length=512, unique=True, index=True)
    s3_bucket: str = Field(max_length=128)
    s3_url: Optional[str] = Field(default=None, max_length=512)
    
    user_id: PyUUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("users.id")),
        index=True
    )
    
    upload_session_id: Optional[PyUUID] = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True)),
        index=True
    )
    
    analysis_id: Optional[PyUUID] = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True)),
        index=True
    )
    
    status: VideoStatusEnum = Field(
        default=VideoStatusEnum.UPLOADING,
        index=True
    )
    
    duration: Optional[float] = Field(default=None)
    resolution: Optional[str] = Field(default=None, max_length=20)
    fps: Optional[float] = Field(default=None)
    
    detection_result: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB)
    )
    
    confidence_score: Optional[float] = Field(
        default=None,
        sa_column=Column(DECIMAL(5, 4))
    )
    
    is_fake: Optional[bool] = Field(default=None)
    processing_time: Optional[float] = Field(default=None)
    error_message: Optional[str] = Field(default=None, max_length=1000)
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        index=True
    )
    
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    )
    
    uploaded_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )
    
    analyzed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB)
    )
    
    dashboard_context: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB)
    )
    
    __table_args__ = (
        Index('idx_videos_user_status', 'user_id', 'status'),
        Index('idx_videos_file_hash', 'file_hash'),
        Index('idx_videos_s3_key', 's3_key'),
    )