#!/usr/bin/env python3
"""
Frame Analysis API Models and Validation Extensions
Pydantic models for frame-level analysis processing with comprehensive validation
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from decimal import Decimal


class FrameAnalysisResult(BaseModel):
    """
    Frame-level analysis result with comprehensive validation.
    
    This model represents individual frame analysis results with confidence scores,
    suspicious regions, artifacts, processing time, and embedding cache status.
    Includes custom validators for frame sequence and chronological processing timestamps.
    """
    
    frame_number: int = Field(
        ..., 
        ge=0, 
        description="Frame number within the video sequence (0-indexed)"
    )
    
    confidence_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence score for deepfake detection (0.0 = real, 1.0 = fake)"
    )
    
    suspicious_regions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of suspicious regions detected in the frame with coordinates and metadata"
    )
    
    artifacts: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary of detected artifacts and manipulation indicators"
    )
    
    processing_time_ms: int = Field(
        ..., 
        ge=0, 
        description="Processing time for this frame in milliseconds"
    )
    
    embedding_cached: bool = Field(
        default=False,
        description="Whether the embedding for this frame was served from cache"
    )
    
    @field_validator('confidence_score')
    @classmethod
    def validate_confidence_range(cls, v: float) -> float:
        """Validate confidence score is within valid range [0.0, 1.0]"""
        if v < 0.0 or v > 1.0:
            raise ValueError("confidence_score must be within [0.0, 1.0]")
        return v
    
    @field_validator('frame_number')
    @classmethod
    def validate_frame_number(cls, v: int) -> int:
        """Validate frame number is non-negative"""
        if v < 0:
            raise ValueError("frame_number must be non-negative")
        return v
    
    @field_validator('processing_time_ms')
    @classmethod
    def validate_processing_time(cls, v: int) -> int:
        """Validate processing time is non-negative"""
        if v < 0:
            raise ValueError("processing_time_ms must be non-negative")
        return v


class FrameAnalysisSequence(BaseModel):
    """
    Container for a sequence of frame analysis results with sequence validation.
    
    This model ensures frame numbers are sequential and processing timestamps
    maintain chronological order for accurate progress tracking.
    """
    
    frames: List[FrameAnalysisResult] = Field(
        default_factory=list,
        description="List of frame analysis results"
    )
    
    @model_validator(mode='after')
    def validate_frame_sequence(self) -> 'FrameAnalysisSequence':
        """Validate frame sequence integrity and chronological processing timestamps"""
        if not self.frames:
            return self
            
        # Sort frames by frame_number to ensure proper sequence validation
        sorted_frames = sorted(self.frames, key=lambda f: f.frame_number)
        
        # Check for sequential frame numbers starting from 0
        expected_frame = 0
        last_processing_time = None
        
        for frame in sorted_frames:
            if frame.frame_number != expected_frame:
                raise ValueError(
                    f"Frame sequence must be sequential starting from 0. "
                    f"Expected frame {expected_frame}, but found {frame.frame_number}"
                )
            
            # Validate chronological processing timestamps
            if last_processing_time is not None:
                if frame.processing_time_ms < last_processing_time:
                    raise ValueError(
                        f"Processing timestamps must be non-decreasing. "
                        f"Frame {frame.frame_number} has processing_time_ms {frame.processing_time_ms} "
                        f"which is less than previous frame's {last_processing_time}"
                    )
            
            last_processing_time = frame.processing_time_ms
            expected_frame += 1
            
        return self
    
    @property
    def total_frames(self) -> int:
        """Get total number of frames in the sequence"""
        return len(self.frames)
    
    @property
    def average_confidence(self) -> float:
        """Calculate average confidence score across all frames"""
        if not self.frames:
            return 0.0
        return sum(frame.confidence_score for frame in self.frames) / len(self.frames)
    
    @property
    def suspicious_frames_count(self) -> int:
        """Count frames with confidence score above 0.5 (suspicious threshold)"""
        return sum(1 for frame in self.frames if frame.confidence_score > 0.5)
    
    @property
    def cached_embeddings_count(self) -> int:
        """Count frames with cached embeddings"""
        return sum(1 for frame in self.frames if frame.embedding_cached)
    
    def get_frame_by_number(self, frame_number: int) -> Optional[FrameAnalysisResult]:
        """Get frame analysis result by frame number"""
        for frame in self.frames:
            if frame.frame_number == frame_number:
                return frame
        return None
    
    def get_suspicious_frames(self, threshold: float = 0.5) -> List[FrameAnalysisResult]:
        """Get frames with confidence score above threshold"""
        return [frame for frame in self.frames if frame.confidence_score > threshold]
