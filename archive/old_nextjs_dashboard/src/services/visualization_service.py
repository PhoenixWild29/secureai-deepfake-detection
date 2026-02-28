#!/usr/bin/env python3
"""
Visualization Service for SecureAI DeepFake Detection
Service for retrieving, processing, and caching visualization data including heatmaps,
suspicious regions, frame navigation, and confidence score visualization.
"""

import asyncio
import logging
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from uuid import UUID
from dataclasses import dataclass
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.detection import (
    HeatmapData,
    InteractiveFrameNavigation,
    EnhancedConfidenceVisualization,
    SuspiciousRegion,
    FrameAnalysis
)

logger = logging.getLogger(__name__)


@dataclass
class VisualizationCacheConfig:
    """Configuration for visualization data caching"""
    cache_ttl_seconds: int = 3600  # 1 hour
    max_cache_size_mb: int = 100   # 100MB max cache size
    cache_prefix: str = "visualization_data"


class VisualizationService:
    """
    Service for retrieving, processing, and caching visualization data.
    Maintains sub-100ms response times through Redis caching and optimized data structures.
    """
    
    def __init__(self, db_session: AsyncSession, redis_client=None):
        self.db_session = db_session
        self.redis_client = redis_client
        self.cache_config = VisualizationCacheConfig()
        
    async def get_heatmap_data(self, analysis_id: UUID) -> Optional[HeatmapData]:
        """
        Get heatmap visualization data for spatial analysis.
        Cached for sub-100ms response times.
        
        Args:
            analysis_id: Analysis ID to get heatmap data for
            
        Returns:
            HeatmapData or None if not available
        """
        cache_key = f"{self.cache_config.cache_prefix}:heatmap:{analysis_id}"
        
        # Try cache first
        if self.redis_client:
            try:
                cached_data = await self._get_from_cache(cache_key)
                if cached_data:
                    logger.debug(f"Hit heatmap cache for analysis {analysis_id}")
                    return self._deserialize_heatmap_data(cached_data)
            except Exception as e:
                logger.warning(f"Cache read failed for heatmap {analysis_id}: {e}")
        
        # Generate heatmap data
        try:
            heatmap_data = await self._generate_heatmap_data(analysis_id)
            
            # Cache the result
            if self.redis_client and heatmap_data:
                await self._set_cache(cache_key, self._serialize_heatmap_data(heatmap_data))
            
            return heatmap_data
            
        except Exception as e:
            logger.error(f"Failed to generate heatmap data for analysis {analysis_id}: {e}")
            return None
    
    async def get_suspicious_region_coordinates(self, analysis_id: UUID) -> List[Dict[str, Any]]:
        """
        Get aggregated suspicious region coordinates for visualization.
        
        Args:
            analysis_id: Analysis ID
            
        Returns:
            List of region coordinate data for visualization
        """
        cache_key = f"{self.cache_config.cache_prefix}:regions:{analysis_id}"
        
        # Try cache first
        if self.redis_client:
            try:
                cached_data = await self._get_from_cache(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            except Exception as e:
                logger.warning(f"Cache read failed for regions {analysis_id}: {e}")
        
        # Generate region coordinates
        try:
            regions_data = await self._generate_region_coordinates(analysis_id)
            
            # Cache the result
            if self.redis_client and regions_data:
                await self._set_cache(cache_key, json.dumps(regions_data))
            
            return regions_data
            
        except Exception as e:
            logger.error(f"Failed to generate region coordinates for analysis {analysis_id}: {e}")
            return []
    
    async def get_interactive_frame_navigation(self, analysis_id: UUID) -> Optional[InteractiveFrameNavigation]:
        """
        Get interactive frame navigation data for UI frame selection.
        
        Args:
            analysis_id: Analysis ID
            
        Returns:
            InteractiveFrameNavigation or None if not available
        """
        cache_key = f"{self.cache_config.cache_prefix}:navigation:{analysis_id}"
        
        # Try cache first
        if self.redis_client:
            try:
                cached_data = await self._get_from_cache(cache_key)
                if cached_data:
                    return self._deserialize_frame_navigation(cached_data)
            except Exception as e:
                logger.warning(f"Cache read failed for navigation {analysis_id}: {e}")
        
        # Generate navigation data
        try:
            navigation_data = await self._generate_frame_navigation(analysis_id)
            
            # Cache the result
            if self.redis_client and navigation_data:
                await self._set_cache(cache_key, self._serialize_frame_navigation(navigation_data))
            
            return navigation_data
            
        except Exception as e:
            logger.error(f"Failed to generate frame navigation for analysis {analysis_id}: {e}")
            return None
    
    async def get_confidence_score_visualization(self, analysis_id: UUID) -> Optional[EnhancedConfidenceVisualization]:
        """
        Get frame-level confidence visualization data for UI rendering.
        
        Args:
            analysis_id: Analysis ID
            
        Returns:
            EnhancedConfidenceVisualization or None if not available
        """
        cache_key = f"{self.cache_config.cache_prefix}:confidence:{analysis_id}"
        
        # Try cache first
        if self.redis_client:
            try:
                cached_data = await self._get_from_cache(cache_key)
                if cached_data:
                    return self._deserialize_confidence_visualization(cached_data)
            except Exception as e:
                logger.warning(f"Cache read failed for confidence {analysis_id}: {e}")
        
        # Generate confidence visualization
        try:
            confidence_data = await self._generate_confidence_visualization(analysis_id)
            
            # Cache the result
            if self.redis_client and confidence_data:
                await self._set_cache(cache_key, self._serialize_confidence_visualization(confidence_data))
            
            return confidence_data
            
        except Exception as e:
            logger.error(f"Failed to generate confidence visualization for analysis {analysis_id}: {e}")
            return None
    
    async def invalidate_visualization_cache(self, analysis_id: UUID) -> bool:
        """
        Invalidate cached visualization data for an analysis.
        
        Args:
            analysis_id: Analysis ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return True  # No cache to invalidate
        
        try:
            # Generate all possible cache keys
            cache_keys = [
                f"{self.cache_config.cache_prefix}:heatmap:{analysis_id}",
                f"{self.cache_config.cache_prefix}:regions:{analysis_id}",
                f"{self.cache_config.cache_prefix}:navigation:{analysis_id}",
                f"{self.cache_config.cache_prefix}:confidence:{analysis_id}"
            ]
            
            # Delete all keys
            deleted_count = 0
            for key in cache_keys:
                if await self.redis_client.delete(key):
                    deleted_count += 1
            
            logger.info(f"Invalidated {deleted_count} visualization cache entries for analysis {analysis_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to invalidate cache for analysis {analysis_id}: {e}")
            return False
    
    # Private helper methods
    
    async def _generate_heatmap_data(self, analysis_id: UUID) -> Optional[HeatmapData]:
        """Generate heatmap data from frame analysis"""
        try:
            # This would typically query the database for frame analysis data
            # For now, we'll simulate realistic heatmap data
            
            # Simulate video dimensions and frame data
            video_width, video_height = 1920, 1080
            
            # Generate intensity grid (simplified 10x10 grid)
            grid_size = 10
            intensity_grid = []
            
            for i in range(grid_size):
                row = []
                for j in range(grid_size):
                    # Simulate intensity based on frame position
                    intensity = np.random.normal(0.5, 0.2)
                    intensity = max(0.0, min(1.0, intensity))
                    row.append(round(intensity, 3))
                intensity_grid.append(row)
            
            heatmap_data = HeatmapData(
                width=video_width,
                height=video_height,
                intensity_grid=intensity_grid,
                confidence_ranges=['0.0-0.25', '0.25-0.5', '0.5-0.75', '0.75-1.0'],
                frame_range={'start': 0, 'end': 100}  # Simplified frame range
            )
            
            return heatmap_data
            
        except Exception as e:
            logger.error(f"Error generating heatmap data for {analysis_id}: {e}")
            return None
    
    async def _generate_region_coordinates(self, analysis_id: UUID) -> List[Dict[str, Any]]:
        """Generate suspicious region coordinates"""
        try:
            # This would typically query suspicious regions from database
            # For now, simulate realistic region coordinates
            
            regions_data = [
                {
                    'region_id': 'region_001',
                    'frame_numbers': [10, 11, 12, 13],
                    'bounding_boxes': [
                        {'x': 100, 'y': 150, 'width': 200, 'height': 100},
                        {'x': 105, 'y': 145, 'width': 195, 'height': 105},
                        {'x': 110, 'y': 140, 'width': 190, 'height': 110},
                        {'x': 115, 'y': 135, 'width': 185, 'height': 115}
                    ],
                    'average_confidence': 0.85,
                    'anomaly_type': 'face_manipulation',
                    'severity': 'high'
                },
                {
                    'region_id': 'region_002',
                    'frame_numbers': [45, 46, 47],
                    'bounding_boxes': [
                        {'x': 800, 'y': 300, 'width': 150, 'height': 150},
                        {'x': 805, 'y': 295, 'width': 145, 'height': 155},
                        {'x': 810, 'y': 290, 'width': 140, 'height': 160}
                    ],
                    'average_confidence': 0.72,
                    'anomaly_type': 'eye_blink_anomaly',
                    'severity': 'medium'
                }
            ]
            
            return regions_data
            
        except Exception as e:
            logger.error(f"Error generating region coordinates for {analysis_id}: {e}")
            return []
    
    async def _generate_frame_navigation(self, analysis_id: UUID) -> Optional[InteractiveFrameNavigation]:
        """Generate interactive frame navigation data"""
        try:
            # Simulate frame navigation data
            thumbnails = []
            navigation_points = []
            confidence_timeline = []
            
            # Generate thumbnails for key frames
            for i in range(0, 100, 10):  # Every 10th frame
                thumbnails.append({
                    'frame_number': i,
                    'thumbnail_url': f'/thumbnails/{analysis_id}/frame_{i}.jpg',
                    'timestamp': i * 0.033,  # ~30fps
                    'confidence_score': np.random.uniform(0.0, 1.0)
                })
            
            # Generate navigation points (peaks and valleys)
            navigation_points = [
                {'frame_number': 15, 'type': 'confidence_peak', 'confidence': 0.95},
                {'frame_number': 35, 'type': 'confidence_valley', 'confidence': 0.15},
                {'frame_number': 65, 'type': 'confidence_peak', 'confidence': 0.92}
            ]
            
            # Generate confidence timeline
            for i in range(100):
                confidence_timeline.append({
                    'frame_number': i,
                    'confidence_score': np.random.uniform(0.0, 1.0),
                    'timestamp': i * 0.033
                })
            
            navigation_data = InteractiveFrameNavigation(
                thumbnails=thumbnails,
                navigation_points=navigation_points,
                confidence_timeline=confidence_timeline
            )
            
            return navigation_data
            
        except Exception as e:
            logger.error(f"Error generating frame navigation for {analysis_id}: {e}")
            return None
    
    async def _generate_confidence_visualization(self, analysis_id: UUID) -> Optional[EnhancedConfidenceVisualization]:
        """Generate confidence score visualization data"""
        try:
            # Generate frame scores
            frame_scores = []
            total_frames = 100
            
            for i in range(total_frames):
                confidence = np.random.uniform(0.0, 1.0)
                frame_scores.append({
                    'frame_number': i,
                    'confidence_score': confidence,
                    'timestamp': i * 0.033,
                    'anomaly_detected': confidence > 0.8
                })
            
            # Generate distribution bins
            distribution_bins = {
                '0.0-0.2': len([f for f in frame_scores if 0.0 <= f['confidence_score'] < 0.2]),
                '0.2-0.4': len([f for f in frame_scores if 0.2 <= f['confidence_score'] < 0.4]),
                '0.4-0.6': len([f for f in frame_scores if 0.4 <= f['confidence_score'] < 0.6]),
                '0.6-0.8': len([f for f in frame_scores if 0.6 <= f['confidence_score'] < 0.8]),
                '0.8-1.0': len([f for f in frame_scores if 0.8 <= f['confidence_score'] <= 1.0])
            }
            
            # Calculate trending score (simple average)
            trending_score = sum(f['confidence_score'] for f in frame_scores) / len(frame_scores)
            
            # Find anomaly frames
            anomaly_frames = [f['frame_number'] for f in frame_scores if f['confidence_score'] > 0.8]
            
            confidence_data = EnhancedConfidenceVisualization(
                frame_scores=frame_scores,
                distribution_bins=distribution_bins,
                trending_score=trending_score,
                anomaly_frames=anomaly_frames
            )
            
            return confidence_data
            
        except Exception as e:
            logger.error(f"Error generating confidence visualization for {analysis_id}: {e}")
            return None
    
    # Cache helper methods
    
    async def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """Get data from Redis cache"""
        try:
            return await self.redis_client.get(cache_key)
        except Exception as e:
            logger.warning(f"Cache get failed for key {cache_key}: {e}")
            return None
    
    async def _set_cache(self, cache_key: str, data: str) -> bool:
        """Set data in Redis cache"""
        try:
            await self.redis_client.setex(
                cache_key, 
                self.cache_config.cache_ttl_seconds, 
                data
            )
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for key {cache_key}: {e}")
            return False
    
    # Serialization methods
    
    def _serialize_heatmap_data(self, heatmap_data: HeatmapData) -> str:
        """Serialize heatmap data for caching"""
        return json.dumps({
            'width': heatmap_data.width,
            'height': heatmap_data.height,
            'intensity_grid': heatmap_data.intensity_grid,
            'confidence_ranges': heatmap_data.confidence_ranges,
            'frame_range': heatmap_data.frame_range
        })
    
    def _deserialize_heatmap_data(self, cached_data: str) -> HeatmapData:
        """Deserialize heatmap data from cache"""
        data = json.loads(cached_data)
        return HeatmapData(**data)
    
    def _serialize_frame_navigation(self, navigation_data: InteractiveFrameNavigation) -> str:
        """Serialize frame navigation data for caching"""
        return json.dumps({
            'thumbnails': navigation_data.thumbnails,
            'navigation_points': navigation_data.navigation_points,
            'confidence_timeline': navigation_data.confidence_timeline
        })
    
    def _deserialize_frame_navigation(self, cached_data: str) -> InteractiveFrameNavigation:
        """Deserialize frame navigation data from cache"""
        data = json.loads(cached_data)
        return InteractiveFrameNavigation(**data)
    
    def _serialize_confidence_visualization(self, confidence_data: EnhancedConfidenceVisualization) -> str:
        """Serialize confidence visualization data for caching"""
        return json.dumps({
            'frame_scores': confidence_data.frame_scores,
            'distribution_bins': confidence_data.distribution_bins,
            'trending_score': confidence_data.trending_score,
            'anomaly_frames': confidence_data.anomaly_frames
        })
    
    def _deserialize_confidence_visualization(self, cached_data: str) -> EnhancedConfidenceVisualization:
        """Deserialize confidence visualization data from cache"""
        data = json.loads(cached_data)
        return EnhancedConfidenceVisualization(**data)


# Service factory function
def get_visualization_service(db_session: AsyncSession, redis_client=None) -> VisualizationService:
    """
    Factory function to create VisualizationService instance.
    
    Args:
        db_session: Database session
        redis_client: Optional Redis client for caching
        
    Returns:
        VisualizationService instance
    """
    return VisualizationService(db_session, redis_client)
