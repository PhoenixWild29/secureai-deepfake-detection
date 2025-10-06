#!/usr/bin/env python3
"""
Heatmap Visualization Data Models
Pydantic models for spatial confidence overlays and suspicious region highlighting
"""

from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime, timezone
from pydantic import BaseModel, Field, validator
from enum import Enum
import numpy as np


class ColorMappingEnum(str, Enum):
    """Predefined color mapping schemes for heatmap visualization"""
    RED_HOT = "red_hot"           # Red (high confidence) to Blue (low confidence)
    RAINBOW = "rainbow"           # Full rainbow spectrum
    VIRIDIS = "viridis"           # Yellow-green-purple
    PLASMA = "plasma"            # Purple-pink-yellow
    CUSTOM = "custom"            # User-defined mapping


class GridGranularityEnum(str, Enum):
    """Predefined grid granularity options"""
    LOW = "low"          # 5x5 grid (25 cells)
    MEDIUM = "medium"    # 10x10 grid (100 cells) - default
    HIGH = "high"        # 20x20 grid (400 cells)
    ULTRA = "ultra"      # 50x50 grid (2500 cells)


class SpatialCoordinate(BaseModel):
    """
    Spatial coordinate with confidence score for heatmap overlay
    """
    x: int = Field(ge=0, description="X coordinate (0-based)")
    y: int = Field(ge=0, description="Y coordinate (0-based)")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    pixel_density: Optional[float] = Field(None, description="Number of pixels represented")

    class Config:
        schema_extra = {
            "example": {
                "x": 150,
                "y": 200,
                "confidence": 0.85,
                "pixel_density": 1.2
            }
        }


class SuspiciousRegion(BaseModel):
    """
    Suspicious region with precise coordinate boundaries
    """
    region_id: str = Field(..., description="Unique identifier for the region")
    coordinates: Dict[str, int] = Field(..., description="Region bounding box coordinates")
    confidence: int = Field(ge=0, le=100, description="Confidence percentage (0-100)")
    description: str = Field(..., description="Human-readable description of the suspicious area")
    artifact_type: Optional[str] = Field(None, description="Type of artifact detected")
    severity: str = Field(default="medium", description="Severity level: low, medium, high, critical")

    @validator('coordinates')
    def validate_coordinates(cls, v):
        """Validate coordinate structure"""
        required_keys = ['x', 'y', 'width', 'height']
        if not all(key in v for key in required_keys):
            raise ValueError("Coordinates must include x, y, width, and height")
        if any(v[key] < 0 for key in required_keys):
            raise ValueError("All coordinates must be non-negative")
        return v

    class Config:
        schema_extra = {
            "example": {
                "region_id": "suspicious_facial_region_001",
                "coordinates": {"x": 100, "y": 150, "width": 50, "height": 40},
                "confidence": 87,
                "description": "Face manipulation artifacts detected",
                "artifact_type": "deepfake_face_synthesis",
                "severity": "high"
            }
        }


class SpatialConfidenceMap(BaseModel):
    """
    Spatial confidence overlay for heatmap visualization
    """
    grid_size: GridGranularityEnum = Field(default=GridGranularityEnum.MEDIUM, description="Grid granularity")
    frame_dimensions: Dict[str, int] = Field(..., description="Frame dimensions (width x height)")
    confidence_grid: List[List[float]] = Field(..., description="2D array of confidence scores")
    coordinate_mapping: Dict[str, Any] = Field(default_factory=dict, description="Mapping metadata")
    interpolation_method: str = Field(default="linear", description="Method used for coordinate interpolation")

    @validator('confidence_grid')
    def validate_confidence_grid(cls, v, values):
        """Validate confidence grid structure"""
        if not v:
            return v
        
        # Check if grid dimensions match expected size
        grid_size = values.get('grid_size', GridGranularityEnum.MEDIUM)
        expected_sizes = {
            GridGranularityEnum.LOW: 5,
            GridGranularityEnum.MEDIUM: 10,
            GridGranularityEnum.HIGH: 20,
            GridGranularityEnum.ULTRA: 50
        }
        expected_size = expected_sizes[grid_size]
        
        if len(v) != expected_size:
            raise ValueError(f"Grid height must match {expected_size} for {grid_size} granularity")
        
        for row in v:
            if len(row) != expected_size:
                raise ValueError(f"Grid width must match {expected_size} for {grid_size} granularity")
            
            # Validate confidence scores
            for score in row:
                if not isinstance(score, (int, float)) or not 0.0 <= score <= 1.0:
                    raise ValueError("All confidence scores must be floats between 0.0 and 1.0")
        
        return v

    class Config:
        schema_extra = {
            "example": {
                "grid_size": "medium",
                "frame_dimensions": {"width": 1920, "height": 1080},
                "confidence_grid": [
                    [0.1, 0.2, 0.9, 0.7, 0.3, 0.1, 0.8, 0.9, 0.4, 0.2],
                    [0.3, 0.8, 0.6, 0.4, 0.7, 0.2, 0.9, 0.3, 0.8, 0.1],
                    # ... 8 more rows for 10x10 grid
                ],
                "coordinate_mapping": {
                    "cell_width": 192.0,
                    "cell_height": 108.0,
                    "total_cells": 100
                },
                "interpolation_method": "linear"
            }
        }


class VisualizationMetadata(BaseModel):
    """
    Metadata for color mapping and UI visualization
    """
    color_scheme: ColorMappingEnum = Field(default=ColorMappingEnum.VIRIDIS, description="Color mapping scheme")
    confidence_thresholds: Dict[str, float] = Field(
        default_factory=lambda: {
            "low": 0.0,
            "medium": 0.4,
            "high": 0.7,
            "critical": 0.9
        },
        description="Confidence score thresholds for color coding"
    )
    color_values: Dict[str, str] = Field(default_factory=dict, description="Custom color values for thresholds")
    animation_settings: Optional[Dict[str, Any]] = Field(None, description="Frame animation preferences")
    zoom_levels: List[int] = Field(default_factory=lambda: [1, 2, 4, 8], description="Available zoom levels")
    
    class Config:
        schema_extra = {
            "example": {
                "color_scheme": "viridis",
                "confidence_thresholds": {
                    "low": 0.0,
                    "medium": 0.4,
                    "high": 0.7,
                    "critical": 0.9
                },
                "color_values": {
                    "low": "#440154",
                    "medium": "#21918c",
                    "high": "#35b779",
                    "critical": "#fde725"
                },
                "zoom_levels": [1, 2, 4, 8, 16]
            }
        }


class FrameHeatmapData(BaseModel):
    """
    Complete heatmap data for a single frame
    """
    frame_number: int = Field(ge=0, description="Frame number (0-based)")
    frame_timestamp: Optional[float] = Field(None, description="Frame timestamp in seconds")
    spatial_confidence: SpatialConfidenceMap = Field(..., description="Spatial confidence overlay")
    suspicious_regions: List[SuspiciousRegion] = Field(default_factory=list, description="Suspicious regions")
    visualization_metadata: VisualizationMetadata = Field(default_factory=lambda: VisualizationMetadata(), description="UI visualization data")
    processing_time_ms: Optional[int] = Field(None, description="Time taken to generate heatmap data")
    
    class Config:
        schema_extra = {
            "example": {
                "frame_number": 142,
                "frame_timestamp": 5.67,
                "spatial_confidence": {
                    "grid_size": "medium",
                    "frame_dimensions": {"width": 1920, "height": 1080},
                    "confidence_grid": [[0.1, 0.2, 0.9]],
                    "coordinate_mapping": {"cell_width": 192.0},
                    "interpolation_method": "linear"
                },
                "suspicious_regions": [
                    {
                        "region_id": "face_region_001",
                        "coordinates": {"x": 100, "y": 150, "width": 50, "height": 40},
                        "confidence": 87,
                        "description": "Face manipulation detected"
                    }
                ],
                "processing_time_ms": 25
            }
        }


class HeatmapResponse(BaseModel):
    """
    Complete response model for heatmap endpoint
    """
    analysis_id: UUID = Field(..., description="Analysis identifier")
    frame_data: FrameHeatmapData = Field(..., description="Heatmap data for requested frame")
    frame_navigation: Dict[str, int] = Field(..., description="Frame navigation metadata")
    cache_info: Dict[str, Any] = Field(default_factory=dict, description="Cache metadata")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Generation timestamp")
    response_time_ms: Optional[int] = Field(None, description="API response time")
    
    class Config:
        schema_extra = {
            "example": {
                "analysis_id": "12345678-1234-1234-1234-123456789012",
                "frame_data": {
                    "frame_number": 142,
                    "spatial_confidence": {
                        "grid_size": "medium",
                        "frame_dimensions": {"width": 1920, "height": 1080}
                    },
                    "suspicious_regions": []
                },
                "frame_navigation": {
                    "current_frame": 142,
                    "total_frames": 1500,
                    "has_next": True,
                    "has_previous": True
                },
                "cache_info": {
                    "cached": True,
                    "cache_hit": True,
                    "cache_key": "heatmap:analysis:12345678"
                },
                "response_time_ms": 45
            }
        }


class HeatmapGenerationRequest(BaseModel):
    """
    Request model for heatmap generation parameters
    """
    analysis_id: UUID = Field(..., description="Analysis identifier")
    frame_number: Optional[int] = Field(None, ge=0, description="Specific frame number (defaults to frame 0)")
    grid_size: GridGranularityEnum = Field(default=GridGranularityEnum.MEDIUM, description="Heatmap grid granularity")
    color_scheme: ColorMappingEnum = Field(default=ColorMappingEnum.VIRIDIS, description="Color mapping scheme")
    include_regions: bool = Field(default=True, description="Include suspicious region highlighting")
    force_regenerate: bool = Field(default=False, description="Force regeneration (bypass cache)")

    class Config:
        schema_extra = {
            "example": {
                "analysis_id": "12345678-1234-1234-1234-123456789012",
                "frame_number": 142,
                "grid_size": "high",
                "color_scheme": "rainbow",
                "include_regions": True,
                "force_regenerate": False
            }
        }


# Export utility functions for heatmap data processing
class HeatmapDataProcessor:
    """Utility class for processing heatmap data"""
    
    @staticmethod
    def create_empty_grid(grid_size: GridGranularityEnum) -> List[List[float]]:
        """Create empty confidence grid"""
        sizes = {
            GridGranularityEnum.LOW: 5,
            GridGranularityEnum.MEDIUM: 10,
            GridGranularityEnum.HIGH: 20,
            GridGranularityEnum.ULTRA: 50
        }
        size = sizes[grid_size]
        return [[0.0 for _ in range(size)] for _ in range(size)]
    
    @staticmethod
    def interpolate_confidence(frame_data: Dict[str, Any], grid_size: GridGranularityEnum) -> List[List[float]]:
        """Interpolate confidence scores to grid coordinates"""
        # This would implement actual interpolation logic
        # For now, return empty grid
        return HeatmapDataProcessor.create_empty_grid(grid_size)
    
    @staticmethod
    def calculate_cell_dimensions(frame_dimensions: Dict[str, int], grid_size: GridGranularityEnum) -> Dict[str, float]:
        """Calculate cell dimensions for coordinate mapping"""
        sizes = {
            GridGranularityEnum.LOW: 5,
            GridGranularityEnum.MEDIUM: 10,
            GridGranularityEnum.HIGH: 20,
            GridGranularityEnum.ULTRA: 50
        }
        
        width = frame_dimensions["width"]
        height = frame_dimensions["height"]
        grid_dimensions = sizes[grid_size]
        
        return {
            "cell_width": width / grid_dimensions,
            "cell_height": height / grid_dimensions,
            "total_cells": grid_dimensions ** 2
        }


# Export all models
__all__ = [
    'SpatialCoordinate',
    'SuspiciousRegion', 
    'SpatialConfidenceMap',
    'VisualizationMetadata',
    'FrameHeatmapData',
    'HeatmapResponse',
    'HeatmapGenerationRequest',
    'HeatmapDataProcessor',
    'ColorMappingEnum',
    'GridGranularityEnum'
]
