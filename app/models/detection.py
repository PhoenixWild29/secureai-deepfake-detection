#!/usr/bin/env python3
"""
Detection API Models with Frame Analysis Extensions
Extended DetectionResponse model with comprehensive frame-by-frame analysis results
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, model_validator

from .frame_analysis import FrameAnalysisResult


class DetectionResponse(BaseModel):
    """
    Extended response model for deepfake detection results with frame-level analysis.
    
    This model provides comprehensive detection results including overall confidence,
    blockchain verification, and detailed frame-by-frame analysis for UI visualization
    and further processing.
    """
    
    analysis_id: UUID = Field(
        ..., 
        description="Unique identifier for the analysis result"
    )
    
    status: str = Field(
        ..., 
        description="Current status of the analysis (processing, completed, error)"
    )
    
    overall_confidence: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=1.0, 
        description="Overall confidence score for the detection (0.0 = real, 1.0 = fake)"
    )
    
    blockchain_hash: Optional[str] = Field(
        None, 
        description="Blockchain hash for tamper-proof verification of the result"
    )
    
    details: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Detailed analysis results and metadata"
    )
    
    processing_time_ms: int = Field(
        ..., 
        ge=0, 
        description="Processing time in milliseconds"
    )
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), 
        description="Timestamp when the analysis was created (UTC)"
    )
    
    # Frame-level analysis results
    frame_analysis: List[FrameAnalysisResult] = Field(
        default_factory=list,
        description="Comprehensive frame-by-frame analysis results including confidence scores, suspicious regions, and processing timestamps for UI visualization"
    )
    
    @field_validator('overall_confidence')
    @classmethod
    def validate_overall_confidence(cls, v: Optional[float]) -> Optional[float]:
        """Validate overall confidence is within valid range [0.0, 1.0]"""
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("overall_confidence must be within [0.0, 1.0]")
        return v
    
    @field_validator('processing_time_ms')
    @classmethod
    def validate_processing_time(cls, v: int) -> int:
        """Validate processing time is non-negative"""
        if v < 0:
            raise ValueError("processing_time_ms must be non-negative")
        return v
    
    @model_validator(mode='after')
    def validate_frame_analysis_consistency(self) -> 'DetectionResponse':
        """Validate frame analysis consistency and overall confidence calculation"""
        if not self.frame_analysis:
            return self
        
        # Validate frame sequence integrity
        sorted_frames = sorted(self.frame_analysis, key=lambda f: f.frame_number)
        expected_frame = 0
        
        for frame in sorted_frames:
            if frame.frame_number != expected_frame:
                raise ValueError(
                    f"Frame analysis must be sequential starting from 0. "
                    f"Expected frame {expected_frame}, but found {frame.frame_number}"
                )
            expected_frame += 1
        
        # Validate processing time consistency
        last_processing_time = None
        for frame in sorted_frames:
            if last_processing_time is not None:
                if frame.processing_time_ms < last_processing_time:
                    raise ValueError(
                        f"Frame processing timestamps must be non-decreasing. "
                        f"Frame {frame.frame_number} has processing_time_ms {frame.processing_time_ms} "
                        f"which is less than previous frame's {last_processing_time}"
                    )
            last_processing_time = frame.processing_time_ms
        
        # Calculate and validate overall confidence if not provided
        if self.overall_confidence is None:
            self.overall_confidence = self.calculate_overall_confidence()
        
        return self
    
    def calculate_overall_confidence(self) -> float:
        """Calculate overall confidence from frame analysis results"""
        if not self.frame_analysis:
            return 0.0
        
        total_confidence = sum(frame.confidence_score for frame in self.frame_analysis)
        return total_confidence / len(self.frame_analysis)
    
    @property
    def total_frames(self) -> int:
        """Get total number of frames analyzed"""
        return len(self.frame_analysis)
    
    @property
    def suspicious_frames_count(self) -> int:
        """Count frames with confidence score above 0.5 (suspicious threshold)"""
        return sum(1 for frame in self.frame_analysis if frame.confidence_score > 0.5)
    
    @property
    def average_processing_time_per_frame(self) -> float:
        """Calculate average processing time per frame in milliseconds"""
        if not self.frame_analysis:
            return 0.0
        
        total_time = sum(frame.processing_time_ms for frame in self.frame_analysis)
        return total_time / len(self.frame_analysis)
    
    @property
    def cached_embeddings_count(self) -> int:
        """Count frames with cached embeddings"""
        return sum(1 for frame in self.frame_analysis if frame.embedding_cached)
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate embedding cache hit rate"""
        if not self.frame_analysis:
            return 0.0
        
        cached_count = self.cached_embeddings_count
        return cached_count / len(self.frame_analysis)
    
    def get_frame_analysis_by_number(self, frame_number: int) -> Optional[FrameAnalysisResult]:
        """Get frame analysis result by frame number"""
        for frame in self.frame_analysis:
            if frame.frame_number == frame_number:
                return frame
        return None
    
    def get_suspicious_frames(self, threshold: float = 0.5) -> List[FrameAnalysisResult]:
        """Get frames with confidence score above threshold"""
        return [frame for frame in self.frame_analysis if frame.confidence_score > threshold]
    
    def get_frame_confidence_timeline(self) -> List[Dict[str, Any]]:
        """Get timeline of confidence scores for visualization"""
        return [
            {
                "frame_number": frame.frame_number,
                "confidence_score": frame.confidence_score,
                "processing_time_ms": frame.processing_time_ms,
                "embedding_cached": frame.embedding_cached
            }
            for frame in sorted(self.frame_analysis, key=lambda f: f.frame_number)
        ]
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """Get comprehensive summary statistics for the analysis"""
        return {
            "total_frames": self.total_frames,
            "suspicious_frames_count": self.suspicious_frames_count,
            "overall_confidence": self.overall_confidence,
            "average_processing_time_per_frame": self.average_processing_time_per_frame,
            "cache_hit_rate": self.cache_hit_rate,
            "cached_embeddings_count": self.cached_embeddings_count,
            "processing_time_ms": self.processing_time_ms,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "blockchain_hash": self.blockchain_hash
        }
