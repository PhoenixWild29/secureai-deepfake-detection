#!/usr/bin/env python3
"""
Detection Results Display Data Models
Pydantic models for visualization and export functionality extending Core Detection Engine
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class ExportFormatEnum(str, Enum):
    """Supported export formats for detection results"""
    PDF = "pdf"
    JSON = "json"
    CSV = "csv"


class BlockchainVerificationStatus(str, Enum):
    """Blockchain verification status"""
    VERIFIED = "verified"
    PENDING = "pending"
    FAILED = "failed"
    NOT_AVAILABLE = "not_available"


class VisualizationResultResponse(BaseModel):
    """
    Enhanced response model for visualization and display of detection results.
    Extends Core Detection Engine data with visualization-specific fields.
    """
    
    # Core identification
    analysis_id: UUID = Field(
        ..., 
        description="Unique identifier for the analysis result from Core Detection Engine"
    )
    
    # Confidence metrics
    overall_confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Overall confidence score for the detection (0.0 = real, 1.0 = fake)"
    )
    
    confidence_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Distribution of confidence scores across predefined bins for visualization"
    )
    
    # Visualization data
    suspicious_regions_summary: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Aggregated summary of suspicious regions across all frames for visualization"
    )
    
    blockchain_verification: Dict[str, Any] = Field(
        default_factory=dict,
        description="Blockchain verification status and metadata for tamper-proof validation"
    )
    
    # Export capabilities
    export_formats: List[str] = Field(
        default=["pdf", "json", "csv"],
        description="Available export formats for this detection result"
    )
    
    # Optional visualization data
    heatmap_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional heatmap visualization data for spatial analysis"
    )
    
    # Metadata
    frame_count: int = Field(
        ..., 
        ge=0, 
        description="Total number of frames analyzed"
    )
    
    suspicious_frames_count: int = Field(
        ..., 
        ge=0, 
        description="Total number of frames flagged as suspicious"
    )
    
    processing_time_ms: int = Field(
        ..., 
        ge=0, 
        description="Total processing time in milliseconds"
    )
    
    created_at: datetime = Field(
        ..., 
        description="Timestamp when the analysis was created"
    )
    
    @field_validator('confidence_distribution')
    @classmethod
    def validate_confidence_distribution(cls, v: Dict[str, int]) -> Dict[str, int]:
        """Validate confidence distribution bins are properly formatted"""
        if not isinstance(v, dict):
            raise ValueError("confidence_distribution must be a dictionary")
        
        # Validate bin names are standard confidence ranges
        valid_bins = ['0.0-0.2', '0.2-0.4', '0.4-0.6', '0.6-0.8', '0.8-1.0']
        for bin_name in v.keys():
            if bin_name not in valid_bins:
                raise ValueError(f"Invalid confidence bin '{bin_name}'. Valid bins: {valid_bins}")
        
        # Validate counts are non-negative
        for count in v.values():
            if not isinstance(count, int) or count < 0:
                raise ValueError("All confidence distribution counts must be non-negative integers")
        
        return v
    
    @field_validator('export_formats')
    @classmethod
    def validate_export_formats(cls, v: List[str]) -> List[str]:
        """Validate export formats are supported"""
        supported_formats = ['pdf', 'json', 'csv']
        for format_name in v:
            if format_name not in supported_formats:
                raise ValueError(f"Unsupported export format '{format_name}'. Supported: {supported_formats}")
        return v
    
    @model_validator(mode='after')
    def validate_frame_counts(self) -> 'VisualizationResultResponse':
        """Validate frame count consistency"""
        if self.suspicious_frames_count > self.frame_count:
            raise ValueError("suspicious_frames_count cannot exceed frame_count")
        return self
    
    def get_confidence_percentage(self) -> float:
        """Calculate confidence as percentage"""
        return self.overall_confidence * 100.0
    
    def get_suspicious_percentage(self) -> float:
        """Calculate percentage of frames that are suspicious"""
        if self.frame_count == 0:
            return 0.0
        return (self.suspicious_frames_count / self.frame_count) * 100.0
    
    def get_processing_time_seconds(self) -> float:
        """Convert processing time to seconds"""
        return self.processing_time_ms / 1000.0


class ExportResultRequest(BaseModel):
    """
    Request model for exporting detection results in various formats.
    Provides flexible configuration for export functionality.
    """
    
    # Core identification
    analysis_id: UUID = Field(
        ..., 
        description="Unique identifier for the analysis result to export"
    )
    
    # Export configuration
    format: str = Field(
        ..., 
        description="Export format (pdf, json, csv)"
    )
    
    include_frames: bool = Field(
        default=True,
        description="Whether to include detailed frame-level analysis in the export"
    )
    
    include_blockchain: bool = Field(
        default=True,
        description="Whether to include blockchain verification data in the export"
    )
    
    export_options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional export-specific options and parameters"
    )
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate export format is supported"""
        supported_formats = ['pdf', 'json', 'csv']
        if v.lower() not in supported_formats:
            raise ValueError(f"Unsupported export format '{v}'. Supported formats: {supported_formats}")
        return v.lower()
    
    @field_validator('export_options')
    @classmethod
    def validate_export_options(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate export options are reasonable"""
        if not isinstance(v, dict):
            raise ValueError("export_options must be a dictionary")
        
        # Validate common export options
        if 'page_size' in v and v['page_size'] not in ['A4', 'Letter', 'Legal']:
            raise ValueError("page_size must be one of: A4, Letter, Legal")
        
        if 'include_timestamps' in v and not isinstance(v['include_timestamps'], bool):
            raise ValueError("include_timestamps must be a boolean")
        
        if 'compression_level' in v:
            level = v['compression_level']
            if not isinstance(level, int) or level < 0 or level > 9:
                raise ValueError("compression_level must be an integer between 0 and 9")
        
        return v
    
    def get_export_format_enum(self) -> ExportFormatEnum:
        """Get export format as enum"""
        return ExportFormatEnum(self.format.lower())
    
    def should_include_detailed_data(self) -> bool:
        """Determine if detailed frame data should be included"""
        return self.include_frames
    
    def should_include_blockchain_data(self) -> bool:
        """Determine if blockchain data should be included"""
        return self.include_blockchain
    
    def get_export_metadata(self) -> Dict[str, Any]:
        """Get export metadata including request parameters"""
        return {
            "analysis_id": str(self.analysis_id),
            "format": self.format,
            "include_frames": self.include_frames,
            "include_blockchain": self.include_blockchain,
            "export_options": self.export_options,
            "request_timestamp": datetime.now(timezone.utc).isoformat()
        }


class BlockchainVerificationResponse(BaseModel):
    """
    Response model for blockchain verification status and metadata.
    """
    
    analysis_id: UUID = Field(
        ..., 
        description="Unique identifier for the analysis result"
    )
    
    blockchain_hash: Optional[str] = Field(
        default=None,
        description="Blockchain transaction hash for verification"
    )
    
    verification_status: BlockchainVerificationStatus = Field(
        ..., 
        description="Current verification status"
    )
    
    verification_timestamp: Optional[datetime] = Field(
        default=None,
        description="Timestamp when verification was performed"
    )
    
    verification_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional verification details and metadata"
    )
    
    is_tamper_proof: bool = Field(
        default=False,
        description="Whether the result is tamper-proof verified"
    )
    
    @model_validator(mode='after')
    def validate_verification_status(self) -> 'BlockchainVerificationResponse':
        """Validate verification status consistency"""
        if self.verification_status == BlockchainVerificationStatus.VERIFIED:
            if not self.blockchain_hash:
                raise ValueError("blockchain_hash is required when status is verified")
            if not self.verification_timestamp:
                raise ValueError("verification_timestamp is required when status is verified")
        
        return self


class DetectionResultSearchRequest(BaseModel):
    """
    Request model for searching and filtering detection results.
    """
    
    # Search criteria
    min_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score for filtering"
    )
    
    max_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Maximum confidence score for filtering"
    )
    
    min_frames: Optional[int] = Field(
        default=None,
        ge=0,
        description="Minimum number of frames for filtering"
    )
    
    max_frames: Optional[int] = Field(
        default=None,
        ge=0,
        description="Maximum number of frames for filtering"
    )
    
    # Time-based filtering
    start_date: Optional[datetime] = Field(
        default=None,
        description="Start date for time-based filtering"
    )
    
    end_date: Optional[datetime] = Field(
        default=None,
        description="End date for time-based filtering"
    )
    
    # Pagination
    limit: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum number of results to return"
    )
    
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of results to skip"
    )
    
    # Sorting
    sort_by: str = Field(
        default="created_at",
        description="Field to sort by (created_at, overall_confidence, frame_count)"
    )
    
    sort_order: str = Field(
        default="desc",
        description="Sort order (asc, desc)"
    )
    
    @field_validator('sort_by')
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        """Validate sort field is supported"""
        valid_fields = ['created_at', 'overall_confidence', 'frame_count', 'suspicious_frames']
        if v not in valid_fields:
            raise ValueError(f"Invalid sort field '{v}'. Valid fields: {valid_fields}")
        return v
    
    @field_validator('sort_order')
    @classmethod
    def validate_sort_order(cls, v: str) -> str:
        """Validate sort order"""
        if v.lower() not in ['asc', 'desc']:
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v.lower()
    
    @model_validator(mode='after')
    def validate_confidence_range(self) -> 'DetectionResultSearchRequest':
        """Validate confidence range is logical"""
        if (self.min_confidence is not None and 
            self.max_confidence is not None and 
            self.min_confidence > self.max_confidence):
            raise ValueError("min_confidence cannot be greater than max_confidence")
        return self
    
    @model_validator(mode='after')
    def validate_frame_range(self) -> 'DetectionResultSearchRequest':
        """Validate frame range is logical"""
        if (self.min_frames is not None and 
            self.max_frames is not None and 
            self.min_frames > self.max_frames):
            raise ValueError("min_frames cannot be greater than max_frames")
        return self
    
    @model_validator(mode='after')
    def validate_date_range(self) -> 'DetectionResultSearchRequest':
        """Validate date range is logical"""
        if (self.start_date is not None and 
            self.end_date is not None and 
            self.start_date > self.end_date):
            raise ValueError("start_date cannot be greater than end_date")
        return self
