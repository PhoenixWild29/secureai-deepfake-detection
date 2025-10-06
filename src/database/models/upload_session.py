#!/usr/bin/env python3
"""
Upload Session Database Models
SQLModel classes for tracking upload sessions and progressive upload state
"""

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Index, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from uuid import uuid4, UUID as PyUUID
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum


class UploadSessionStatus(str, Enum):
    """Enumeration of upload session statuses."""
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class UploadSession(SQLModel, table=True):
    """
    Upload Session table for tracking progressive uploads and chunked file transfers.
    """
    __tablename__ = "upload_session"
    
    # Primary key
    id: PyUUID = Field(
        default_factory=uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    
    # Session identification
    session_id: str = Field(
        max_length=128,
        unique=True,
        index=True,
        description="Unique session identifier for external references"
    )
    
    # File information
    filename: str = Field(
        max_length=255,
        description="Original filename"
    )
    
    content_type: str = Field(
        max_length=100,
        description="MIME content type"
    )
    
    file_size: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total file size in bytes"
    )
    
    file_hash: Optional[str] = Field(
        max_length=128,
        index=True,
        description="File content hash for deduplication"
    )
    
    # Upload configuration
    total_chunks: int = Field(
        ge=1,
        description="Total number of chunks for this upload"
    )
    
    chunk_size: int = Field(
        ge=1024,  # Minimum 1KB
        description="Size of each chunk in bytes"
    )
    
    chunks_received: int = Field(
        default=0,
        ge=0,
        description="Number of chunks received so far"
    )
    
    # Session status
    status: UploadSessionStatus = Field(
        default=UploadSessionStatus.ACTIVE,
        description="Current session status"
    )
    
    # User information
    user_id: Optional[str] = Field(
        max_length=128,
        index=True,
        description="User ID who initiated the upload"
    )
    
    username: Optional[str] = Field(
        max_length=100,
        description="Username for display purposes"
    )
    
    # Upload options and metadata
    upload_options: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="Upload options and configuration"
    )
    
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Processing priority (1-10)"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    
    expires_at: datetime = Field(
        description="Session expiration timestamp"
    )
    
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Timestamp when upload completed"
    )
    
    # Error information
    error_code: Optional[str] = Field(
        max_length=50,
        description="Error code if upload failed"
    )
    
    error_message: Optional[str] = Field(
        description="Error message if upload failed"
    )
    
    error_details: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSONB),
        description="Additional error details"
    )
    
    # Processing information
    upload_id: Optional[PyUUID] = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True)),
        description="Associated upload ID when completed"
    )
    
    analysis_id: Optional[PyUUID] = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True)),
        description="Associated analysis ID when processing initiated"
    )
    
    processing_job_id: Optional[str] = Field(
        max_length=128,
        description="Processing job ID if processing initiated"
    )
    
    # Progress tracking
    progress_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Upload progress percentage"
    )
    
    bytes_uploaded: int = Field(
        default=0,
        ge=0,
        description="Total bytes uploaded so far"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_upload_session_session_id", "session_id"),
        Index("idx_upload_session_user_id", "user_id"),
        Index("idx_upload_session_status", "status"),
        Index("idx_upload_session_expires_at", "expires_at"),
        Index("idx_upload_session_file_hash", "file_hash"),
        Index("idx_upload_session_created_at", "created_at"),
    )


class UploadChunk(SQLModel, table=True):
    """
    Upload Chunk table for tracking individual chunks in a session.
    """
    __tablename__ = "upload_chunk"
    
    # Primary key
    id: PyUUID = Field(
        default_factory=uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    
    # Session reference
    session_id: str = Field(
        max_length=128,
        index=True,
        description="Upload session ID"
    )
    
    # Chunk information
    chunk_index: int = Field(
        ge=0,
        description="Chunk index (0-based)"
    )
    
    chunk_size: int = Field(
        ge=0,
        description="Size of this chunk in bytes"
    )
    
    chunk_hash: Optional[str] = Field(
        max_length=128,
        description="Hash of chunk content for integrity verification"
    )
    
    # Storage information
    storage_path: Optional[str] = Field(
        max_length=512,
        description="Path where chunk is stored"
    )
    
    # Status
    received: bool = Field(
        default=False,
        description="Whether chunk has been received"
    )
    
    verified: bool = Field(
        default=False,
        description="Whether chunk integrity has been verified"
    )
    
    # Timestamps
    received_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Timestamp when chunk was received"
    )
    
    verified_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="Timestamp when chunk was verified"
    )
    
    # Error information
    error_code: Optional[str] = Field(
        max_length=50,
        description="Error code if chunk failed"
    )
    
    error_message: Optional[str] = Field(
        description="Error message if chunk failed"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_upload_chunk_session_id", "session_id"),
        Index("idx_upload_chunk_session_index", "session_id", "chunk_index"),
        Index("idx_upload_chunk_received", "received"),
        Index("idx_upload_chunk_verified", "verified"),
    )


class UploadProgressLog(SQLModel, table=True):
    """
    Upload Progress Log table for tracking detailed progress history.
    """
    __tablename__ = "upload_progress_log"
    
    # Primary key
    id: PyUUID = Field(
        default_factory=uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    
    # Session reference
    session_id: str = Field(
        max_length=128,
        index=True,
        description="Upload session ID"
    )
    
    # Progress information
    progress_percentage: float = Field(
        ge=0.0,
        le=100.0,
        description="Progress percentage at this point"
    )
    
    bytes_uploaded: int = Field(
        ge=0,
        description="Bytes uploaded at this point"
    )
    
    chunks_received: int = Field(
        ge=0,
        description="Number of chunks received at this point"
    )
    
    # Performance metrics
    upload_speed_mbps: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Upload speed in Mbps"
    )
    
    estimated_time_remaining: Optional[int] = Field(
        default=None,
        ge=0,
        description="Estimated time remaining in seconds"
    )
    
    # Context
    event_type: str = Field(
        max_length=50,
        description="Type of progress event"
    )
    
    event_message: Optional[str] = Field(
        description="Event message or description"
    )
    
    # Timestamp
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_upload_progress_session_id", "session_id"),
        Index("idx_upload_progress_timestamp", "timestamp"),
        Index("idx_upload_progress_event_type", "event_type"),
    )


# Utility functions for session management
class UploadSessionManager:
    """Utility class for managing upload sessions."""
    
    @staticmethod
    def create_session(
        session_id: str,
        filename: str,
        content_type: str,
        total_chunks: int,
        chunk_size: int,
        file_size: Optional[int] = None,
        file_hash: Optional[str] = None,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        upload_options: Optional[Dict[str, Any]] = None,
        priority: int = 5,
        timeout_hours: int = 24
    ) -> UploadSession:
        """
        Create a new upload session.
        
        Args:
            session_id: Unique session identifier
            filename: Original filename
            content_type: MIME content type
            total_chunks: Total number of chunks
            chunk_size: Size of each chunk
            file_size: Total file size (optional)
            file_hash: File content hash (optional)
            user_id: User ID (optional)
            username: Username (optional)
            upload_options: Upload options (optional)
            priority: Processing priority (default: 5)
            timeout_hours: Session timeout in hours (default: 24)
            
        Returns:
            UploadSession instance
        """
        expires_at = datetime.now(timezone.utc) + timedelta(hours=timeout_hours)
        
        return UploadSession(
            session_id=session_id,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            file_hash=file_hash,
            total_chunks=total_chunks,
            chunk_size=chunk_size,
            user_id=user_id,
            username=username,
            upload_options=upload_options or {},
            priority=priority,
            expires_at=expires_at
        )
    
    @staticmethod
    def update_session_progress(
        session: UploadSession,
        chunks_received: int,
        bytes_uploaded: int
    ) -> UploadSession:
        """
        Update session progress.
        
        Args:
            session: Upload session to update
            chunks_received: Number of chunks received
            bytes_uploaded: Number of bytes uploaded
            
        Returns:
            Updated UploadSession instance
        """
        session.chunks_received = chunks_received
        session.bytes_uploaded = bytes_uploaded
        session.last_updated = datetime.now(timezone.utc)
        
        # Calculate progress percentage
        if session.file_size and session.file_size > 0:
            session.progress_percentage = min(100.0, (bytes_uploaded / session.file_size) * 100.0)
        elif session.total_chunks > 0:
            session.progress_percentage = min(100.0, (chunks_received / session.total_chunks) * 100.0)
        
        # Update status if complete
        if chunks_received >= session.total_chunks:
            session.status = UploadSessionStatus.COMPLETED
            session.completed_at = datetime.now(timezone.utc)
            session.progress_percentage = 100.0
        
        return session
    
    @staticmethod
    def mark_session_failed(
        session: UploadSession,
        error_code: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> UploadSession:
        """
        Mark session as failed.
        
        Args:
            session: Upload session to mark as failed
            error_code: Error code
            error_message: Error message
            error_details: Additional error details (optional)
            
        Returns:
            Updated UploadSession instance
        """
        session.status = UploadSessionStatus.FAILED
        session.error_code = error_code
        session.error_message = error_message
        session.error_details = error_details or {}
        session.last_updated = datetime.now(timezone.utc)
        
        return session
    
    @staticmethod
    def is_session_expired(session: UploadSession) -> bool:
        """
        Check if session has expired.
        
        Args:
            session: Upload session to check
            
        Returns:
            True if expired, False otherwise
        """
        return datetime.now(timezone.utc) > session.expires_at
    
    @staticmethod
    def extend_session(session: UploadSession, hours: int = 24) -> UploadSession:
        """
        Extend session expiration time.
        
        Args:
            session: Upload session to extend
            hours: Hours to extend (default: 24)
            
        Returns:
            Updated UploadSession instance
        """
        session.expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        session.last_updated = datetime.now(timezone.utc)
        
        return session


# Export main components
__all__ = [
    'UploadSessionStatus',
    'UploadSession',
    'UploadChunk',
    'UploadProgressLog',
    'UploadSessionManager'
]
