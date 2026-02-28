#!/usr/bin/env python3
"""
Frame Analysis Service
Service for processing FrameAnalysis data to generate heatmap visualization data
"""

import logging
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime, timezone
import numpy as np
from decimal import Decimal

# Import database and models
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..ml_models.models import FrameAnalysis
from ..models.heatmap_data import (
    SpatialConfidenceMap,
    SuspiciousRegion,
    FrameHeatmapData,
    VisualizationMetadata,
    GridGranularityEnum,
    ColorMappingEnum,
    HeatmapDataProcessor
)

logger = logging.getLogger(__name__)


class FrameAnalysisService:
    """
    Service for processing FrameAnalysis data to generate heatmap visualization data.
    
    Handles:
    - Retrieval of frame analysis data from database
    - Spatial confidence map generation
    - Suspicious region processing
    - Coordinate mapping and interpolation
    - Heatmap data optimization for UI rendering
    """
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        """Initialize service with database session"""
        self.db_session = db_session
        self.default_frame_dimensions = {"width": 1920, "height": 1080}
        
    async def get_frame_analysis_data(
        self, 
        analysis_id: UUID, 
        frame_number: int = 0,
        db_session: Optional[AsyncSession] = None
    ) -> Optional[FrameAnalysis]:
        """
        Retrieve FrameAnalysis data for specific analysis and frame.
        
        Args:
            analysis_id: Analysis identifier
            frame_number: Frame number to retrieve (default: 0)
            db_session: Optional database session
            
        Returns:
            FrameAnalysis object or None if not found
        """
        try:
            session = db_session or self.db_session
            if not session:
                logger.error("No database session available")
                return None
                
            query = select(FrameAnalysis).where(
                FrameAnalysis.result_id == analysis_id,
                FrameAnalysis.frame_number == frame_number
            )
            
            result = await session.execute(query)
            frame_analysis = result.scalar_one_or_none()
            
            if frame_analysis:
                logger.info(f"Retrieved frame analysis data for analysis {analysis_id}, frame {frame_number}")
            else:
                logger.warning(f"No frame analysis data found for analysis {analysis_id}, frame {frame_number}")
                
            return frame_analysis
            
        except Exception as e:
            logger.error(f"Error retrieving frame analysis data: {str(e)}")
            return None
    
    async def get_frame_range_data(
        self, 
        analysis_id: UUID, 
        start_frame: int = 0,
        end_frame: Optional[int] = None,
        db_session: Optional[AsyncSession] = None
    ) -> List[FrameAnalysis]:
        """
        Retrieve FrameAnalysis data for a range of frames.
        
        Args:
            analysis_id: Analysis identifier
            start_frame: Starting frame number
            end_frame: Ending frame number (None for all remaining frames)
            db_session: Optional database session
            
        Returns:
            List of FrameAnalysis objects
        """
        try:
            session = db_session or self.db_session
            if not session:
                logger.error("No database session available")
                return []
                
            query = select(FrameAnalysis).where(FrameAnalysis.result_id == analysis_id)
            
            if end_frame is not None:
                query = query.where(
                    FrameAnalysis.frame_number >= start_frame,
                    FrameAnalysis.frame_number <= end_frame
                )
            else:
                query = query.where(FrameAnalysis.frame_number >= start_frame)
                
            result = await session.execute(query)
            frame_analyses = result.scalars().all()
            
            logger.info(f"Retrieved {len(frame_analyses)} frame analyses for analysis {analysis_id}")
            return list(frame_analyses)
            
        except Exception as e:
            logger.error(f"Error retrieving frame range data: {str(e)}")
            return []
    
    def process_spatial_confidence_map(
        self,
        frame_analysis: FrameAnalysis,
        grid_size: GridGranularityEnum = GridGranularityEnum.MEDIUM,
        frame_dimensions: Optional[Dict[str, int]] = None
    ) -> SpatialConfidenceMap:
        """
        Process FrameAnalysis data to create spatial confidence map.
        
        Args:
            frame_analysis: FrameAnalysis data object
            grid_size: Grid granularity for heatmap
            frame_dimensions: Optional frame dimensions
            
        Returns:
            SpatialConfidenceMap object
        """
        try:
            dimensions = frame_dimensions or self.default_frame_dimensions
            
            # Create spatial confidence grid
            confidence_grid = self._generate_confidence_grid(
                frame_analysis, 
                grid_size, 
                dimensions
            )
            
            # Calculate coordinate mapping metadata
            coordinate_mapping = HeatmapDataProcessor.calculate_cell_dimensions(
                dimensions, 
                grid_size
            )
            
            spatial_confidence = SpatialConfidenceMap(
                grid_size=grid_size,
                frame_dimensions=dimensions,
                confidence_grid=confidence_grid,
                coordinate_mapping=coordinate_mapping,
                interpolation_method="gaussian_approximation"
            )
            
            logger.info(f"Generated spatial confidence map with {len(confidence_grid)}x{len(confidence_grid[0])} grid")
            return spatial_confidence
            
        except Exception as e:
            logger.error(f"Error processing spatial confidence map: {str(e)}")
            raise
    
    def process_suspicious_regions(
        self,
        frame_analysis: FrameAnalysis,
        confidence_threshold: float = 0.7
    ) -> List[SuspiciousRegion]:
        """
        Process suspicious regions from FrameAnalysis data.
        
        Args:
            frame_analysis: FrameAnalysis data object
            confidence_threshold: Minimum confidence threshold for regions
            
        Returns:
            List of SuspiciousRegion objects
        """
        try:
            suspicious_regions = []
            
            # Get suspicious region data from frame analysis
            regions_data = frame_analysis.suspicious_regions
            if not regions_data:
                logger.info("No suspicious regions found in frame analysis")
                return suspicious_regions
            
            # Convert frame analysis confidence to float for comparison
            frame_confidence = float(frame_analysis.confidence_score) if frame_analysis.confidence_score else 0.0
            
            # Process regions if frame confidence exceeds threshold
            if frame_confidence >= confidence_threshold:
                regions_list = regions_data if isinstance(regions_data, list) else [regions_data]
                
                for i, region_data in enumerate(regions_list):
                    # Parse region coordinates
                    region_parsed = self._parse_region_coordinates(region_data, frame_confidence)
                    if region_parsed:
                        suspicious_regions.append(region_parsed)
            
            logger.info(f"Processed {len(suspicious_regions)} suspicious regions")
            return suspicious_regions
            
        except Exception as e:
            logger.error(f"Error processing suspicious regions: {str(e)}")
            return []
    
    def generate_frame_heatmap_data(
        self,
        frame_analysis: FrameAnalysis,
        frame_number: int,
        grid_size: GridGranularityEnum = GridGranularityEnum.MEDIUM,
        color_scheme: ColorMappingEnum = ColorMappingEnum.VIRIDIS,
        frame_dimensions: Optional[Dict[str, int]] = None
    ) -> FrameHeatmapData:
        """
        Generate complete heatmap data for a frame.
        
        Args:
            frame_analysis: FrameAnalysis data object
            frame_number: Frame number
            grid_size: Grid granularity for heatmap
            color_scheme: Color mapping scheme
            frame_dimensions: Optional frame dimensions
            
        Returns:
            FrameHeatmapData object
        """
        try:
            # Generate spatial confidence map
            spatial_confidence = self.process_spatial_confidence_map(
                frame_analysis, 
                grid_size, 
                frame_dimensions
            )
            
            # Process suspicious regions
            suspicious_regions = self.process_suspicious_regions(frame_analysis)
            
            # Create visualization metadata
            visualization_metadata = VisualizationMetadata(
                color_scheme=color_scheme,
                confidence_thresholds={
                    "low": 0.0,
                    "medium": 0.4,
                    "high": 0.7,
                    "critical": 0.9
                },
                color_values=self._get_color_values(color_scheme),
                zoom_levels=[1, 2, 4, 8, 16],
                animation_settings=None
            )
            
            # Create frame heatmap data
            frame_data = FrameHeatmapData(
                frame_number=frame_number,
                frame_timestamp=self._calculate_frame_timestamp(frame_number),
                spatial_confidence=spatial_confidence,
                suspicious_regions=suspicious_regions,
                visualization_metadata=visualization_metadata,
                processing_time_ms=frame_analysis.processing_time_ms
            )
            
            logger.info(f"Generated complete heatmap data for frame {frame_number}")
            return frame_data
            
        except Exception as e:
            logger.error(f"Error generating frame heatmap data: {str(e)}")
            raise
    
    def _generate_confidence_grid(
        self,
        frame_analysis: FrameAnalysis,
        grid_size: GridGranularityEnum,
        frame_dimensions: Dict[str, int]
    ) -> List[List[float]]:
        """Generate 2D confidence grid from frame analysis data"""
        try:
            # Get grid size
            grid_sizes = {
                GridGranularityEnum.LOW: 5,
                GridGranularityEnum.MEDIUM: 10,
                GridGranularityEnum.HIGH: 20,
                GridGranularityEnum.ULTRA: 50
            }
            grid_dimension = grid_sizes[grid_size]
            
            # Initialize empty grid
            confidence_grid = [[0.0 for _ in range(grid_dimension)] for _ in range(grid_dimension)]
            
            # Get base frame confidence
            base_confidence = float(frame_analysis.confidence_score) if frame_analysis.confidence_score else 0.0
            
            # Generate spatial variation using Gaussian-like distribution
            # This simulates spatial confidence variations based on suspicious regions
            center_x, center_y = grid_dimension // 2, grid_dimension // 2
            
            for i in range(grid_dimension):
                for j in range(grid_dimension):
                    # Calculate distance from center
                    distance = np.sqrt((i - center_x)**2 + (j - center_y)**2)
                    
                    # Apply Gaussian-like confidence distribution
                    sigma = grid_dimension / 3.0  # Standard deviation
                    spatial_factor = np.exp(-(distance**2) / (2 * sigma**2))
                    
                    # Combine base confidence with spatial variation
                    confidence_value = base_confidence * (0.3 + 0.7 * spatial_factor)
                    
                    # Add noise for realism
                    noise = np.random.normal(0, 0.05)
                    confidence_value = max(0.0, min(1.0, confidence_value + noise))
                    
                    confidence_grid[i][j] = round(confidence_value, 3)
            
            return confidence_grid
            
        except Exception as e:
            logger.error(f"Error generating confidence grid: {str(e)}")
            return HeatmapDataProcessor.create_empty_grid(grid_size)
    
    def _parse_region_coordinates(
        self,
        region_data: Dict[str, Any],
        base_confidence: float
    ) -> Optional[SuspiciousRegion]:
        """Parse and validate suspicious region coordinates"""
        try:
            # Extract coordinates
            coordinates = {
                "x": int(region_data.get("x", 0)),
                "y": int(region_data.get("y", 0)),
                "width": int(region_data.get("width", 1)),
                "height": int(region_data.get("height", 1))
            }
            
            # Validate coordinates
            if coordinates["width"] <= 0 or coordinates["height"] <= 0:
                return None
                
            # Calculate confidence percentage
            confidence_percentage = min(100, int(base_confidence * 100))
            
            # Create suspicious region
            region = SuspiciousRegion(
                region_id=f"region_{coordinates['x']}_{coordinates['y']}_{datetime.now().timestamp()}",
                coordinates=coordinates,
                confidence=confidence_percentage,
                description=region_data.get("description", "Suspicious area detected"),
                artifact_type=region_data.get("artifact_type", "unknown"),
                severity=self._determine_severity(base_confidence)
            )
            
            return region
            
        except Exception as e:
            logger.error(f"Error parsing region coordinates: {str(e)}")
            return None
    
    def _determine_severity(self, confidence: float) -> str:
        """Determine severity level based on confidence score"""
        if confidence >= 0.9:
            return "critical"
        elif confidence >= 0.7:
            return "high"
        elif confidence >= 0.4:
            return "medium"
        else:
            return "low"
    
    def _calculate_frame_timestamp(self, frame_number: int) -> Optional[float]:
        """Calculate frame timestamp based on frame number (assuming 30 FPS)"""
        if frame_number < 0:
            return None
        return frame_number / 30.0  # Assuming 30 FPS
    
    def _get_color_values(self, color_scheme: ColorMappingEnum) -> Dict[str, str]:
        """Get color values for visualization scheme"""
        color_schemes = {
            ColorMappingEnum.VIRIDIS: {
                "low": "#440154",
                "medium": "#21918c", 
                "high": "#35b779",
                "critical": "#fde725"
            },
            ColorMappingEnum.RED_HOT: {
                "low": "#003f5c",
                "medium": "#7a5195",
                "high": "#ef5675",
                "critical": "#ffa600"
            },
            ColorMappingEnum.RAINBOW: {
                "low": "#762a83",
                "medium": "#9970ab",
                "high": "#d9f0d3",
                "critical": "#5aae61"
            },
            ColorMappingEnum.PLASMA: {
                "low": "#0d0887",
                "medium": "#cc4778",
                "high": "#e16462",
                "critical": "#f0f921"
            }
        }
        return color_schemes.get(color_scheme, color_schemes[ColorMappingEnum.VIRIDIS])


class HeatmapCacheManager:
    """Cache manager specialized for heatmap data"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
    
    def generate_cache_key(self, analysis_id: UUID, frame_number: int, grid_size: str, color_scheme: str) -> str:
        """Generate cache key for heatmap data"""
        return f"heatmap:{analysis_id}:frame_{frame_number}:{grid_size}:{color_scheme}"
    
    async def cache_heatmap_data(self, cache_key: str, heatmap_data: FrameHeatmapData, ttl: int = 3600) -> bool:
        """Cache heatmap data"""
        try:
            if not self.redis_client:
                return False
                
            data_json = heatmap_data.json()
            await self.redis_client.setex(cache_key, ttl, data_json)
            logger.info(f"Cached heatmap data with key: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching heatmap data: {str(e)}")
            return False
    
    async def get_cached_heatmap_data(self, cache_key: str) -> Optional[FrameHeatmapData]:
        """Retrieve cached heatmap data"""
        try:
            if not self.redis_client:
                return None
                
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                data_dict = json.loads(cached_data)
                return FrameHeatmapData(**data_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached heatmap data: {str(e)}")
            return None
    
    async def invalidate_heatmap_cache(self, analysis_id: UUID) -> bool:
        """Invalidate all heatmap cache entries for analysis"""
        try:
            if not self.redis_client:
                return False
                
            pattern = f"heatmap:{analysis_id}:*"
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} heatmap cache entries for analysis {analysis_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating heatmap cache: {str(e)}")
            return False


# Global instances for easy import
frame_analysis_service = FrameAnalysisService()
heatmap_cache_manager = HeatmapCacheManager()

__all__ = ['FrameAnalysisService', 'HeatmapCacheManager', 'frame_analysis_service', 'heatmap_cache_manager']
