#!/usr/bin/env python3
"""
Heatmap Visualization Data API Endpoints
FastAPI endpoints for spatial confidence overlays and suspicious region highlighting
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timezone
import time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

# Import database session dependency
from ...database.config import get_db_session

# Import integration wrapper (Work Order #29)
from ...api.heatmap_integration_wrapper import cache_manager, frame_analysis_service
from ...models.heatmap_data import \
    HeatmapResponse, \
    FrameHeatmapData, \
    GridGranularityEnum, \
    ColorMappingEnum, \
    HeatmapGenerationRequest

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/v1/results",
    tags=["Heatmap Visualization"],
    responses={
        404: {"description": "Analysis or frame data not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)


@router.get(
    "/{analysis_id}/heatmap",
    response_model=HeatmapResponse,
    summary="Get heatmap visualization data",
    description="Generate spatial confidence overlays and suspicious region highlighting data for interactive UI heatmap visualization",
    responses={
        200: {
            "description": "Heatmap data generated successfully",
            "content": {
                "application/json": {
                    "schema": HeatmapResponse.schema()
                }
            }
        },
        404: {"description": "Analysis result or frame data not found"},
        422: {"description": "Invalid frame number or grid size"},
        500: {"description": "Heatmap generation failed"}
    }
)
async def get_heatmap_data(
    analysis_id: UUID,
    frame_number: int = Query(default=0, ge=0, description="Frame number to generate heatmap for"),
    grid_size: GridGranularityEnum = Query(default=GridGranularityEnum.MEDIUM, description="Grid granularity for heatmap"),
    color_scheme: ColorMappingEnum = Query(default=ColorMappingEnum.VIRIDIS, description="Color mapping scheme"),
    include_regions: bool = Query(default=True, description="Include suspicious region highlighting"),
    cache_duration: int = Query(default=3600, ge=60, le=86400, description="Cache duration in seconds"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Generate heatmap visualization data for a specific analysis and frame.
    
    This endpoint processes Core Detection Engine FrameAnalysis data to generate:
    - Spatial confidence overlays with coordinate-based confidence mapping
    - suspicious region highlighting with precise coordinate boundaries
    - Frame navigation metadata for UI navigation
    - Color mapping and visualization metadata
    
    Args:
        analysis_id: Analysis identifier
        frame_number: Frame number (0-based indexing)
        grid_size: Grid granularity (low=5x5, medium=10x10, high=20x20, ultra=50x50)
        color_scheme: Color mapping scheme for visualization
        include_regions: Whether to include suspicious region data
        cache_duration: Cache duration in seconds (60-86400)
        db: Database session
        
    Returns:
        HeatmapResponse: Complete heatmap visualization data
        
    Exceptions:
        HTTPException 404: Analysis result not found
        HTTPException 422: Invalid parameters
        HTTPException 500: Heatmap generation failed
    """
    
    start_time = time.time()
    
    try:
        logger.info(f"Generating heatmap data for analysis {analysis_id}, frame {frame_number}")
        
        # Check cache first for sub-100ms response times
        cache_key_components = {
            "analysis_id": analysis_id,
            "frame_number": frame_number,
            "grid_size": grid_size.value,
            "color_scheme": color_scheme.value
        }
        
        cached_data = await cache_manager.get_cached_heatmap_data(
            cache_key_components["analysis_id"],
            cache_key_components["frame_number"], 
            cache_key_components["grid_size"],
            cache_key_components["color_scheme"]
        )
        
        frame_data: Optional[FrameHeatmapData] = None
        cache_hit = False
        
        if cached_data:
            # Use cached data
            frame_data = FrameHeatmapData(**cached_data)
            cache_hit = True
            logger.info(f"Served heatmap data from cache for analysis {analysis_id}, frame {frame_number}")
        else:
            # Generate new heatmap data
            logger.info(f"Generating new heatmap data for analysis {analysis_id}, frame {frame_number}")
            
            # Get frame analysis data from database  
            frame_analysis = await frame_analysis_service.get_frame_analysis_data(
                analysis_id, 
                frame_number
            )
            
            if not frame_analysis:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Frame analysis data not found for analysis {analysis_id}, frame {frame_number}"
                )
            
            # Generate heatmap data
            frame_data = frame_analysis_service.generate_frame_heatmap_data(
                frame_analysis=frame_analysis,
                frame_number=frame_number,
                grid_size=grid_size.value,
                color_scheme=color_scheme.value,
                frame_dimensions={"width": 1920, "height": 1080}  # Default dimensions
            )
            
            # Cache the generated data
            cache_data = frame_data.dict()
            await cache_manager.cache_heatmap_data(
                cache_key_components["analysis_id"],
                cache_key_components["frame_number"],
                cache_key_components["grid_size"], 
                cache_key_components["color_scheme"],
                cache_data,
                cache_duration
            )
            
            logger.info(f"Generated and cached heatmap data for analysis {analysis_id}, frame {frame_number}")
        
        # Get total frame count for navigation metadata
        total_frames = await _get_total_frame_count(analysis_id, db)
        
        # Generate navigation metadata
        frame_navigation = {
            "current_frame": frame_number,
            "total_frames": total_frames,
            "has_next": frame_number < total_frames - 1 if total_frames > 0 else False,
            "has_previous": frame_number > 0,
            "next_frame": frame_number + 1 if frame_number < total_frames - 1 else None,
            "previous_frame": frame_number - 1 if frame_number > 0 else None
        }
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Build response
        heatmap_response = HeatmapResponse(
            analysis_id=analysis_id,
            frame_data=frame_data,
            frame_navigation=frame_navigation,
            cache_info={
                "cached": cache_hit,
                "cache_hit": cache_hit,
                "cache_key": f"heatmap:{analysis_id}:frame_{frame_number}:{grid_size.value}:{color_scheme.value}",
                "cache_duration": cache_duration,
                "response_time_ms": response_time_ms
            },
            generated_at=datetime.now(timezone.utc),
            response_time_ms=response_time_ms
        )
        
        logger.info(f"Heatmap data generated successfully for analysis {analysis_id}, frame {frame_number} (response_time: {response_time_ms}ms)")
        return heatmap_response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Heatmap generation failed for analysis {analysis_id}, frame {frame_number}: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@router.get(
    "/{analysis_id}/heatmap/bulk",
    summary="Get bulk heatmap data for multiple frames",
    description="Generate heatmap data for multiple frames in sequence for animation or batch visualization"
)
async def get_bulk_heatmap_data(
    analysis_id: UUID,
    start_frame: int = Query(default=0, ge=0, description="Starting frame number"),
    end_frame: int = Query(default=9, ge=0, description="Ending frame number"),
    frame_step: int = Query(default=1, ge=1, description="Frame step size"),
    grid_size: GridGranularityEnum = Query(default=GridGranularityEnum.MEDIUM, description="Grid granularity"),
    color_scheme: ColorMappingEnum = Query(default=ColorMappingEnum.VIRIDIS, description="Color mapping scheme"),
    include_regions: bool = Query(default=True, description="Include suspicious region highlighting"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Generate heatmap data for multiple frames in sequence.
    
    Returns data for frames in the range [start_frame:end_frame:step],
    optimized for animation or batch visualization scenarios.
    """
    
    try:
        logger.info(f"Generating bulk heatmap data for analysis {analysis_id}, frames {start_frame}-{end_frame}")
        
        start_time = time.time()
        frame_data_list = []
        
        # Generate heatmap data for each frame in range
        for frame_num in range(start_frame, end_frame + 1, frame_step):
            try:
                # Check cache first
                cached_data = await cache_manager.get_cached_heatmap_data(
                    analysis_id, frame_num, grid_size.value, color_scheme.value
                )
                
                if cached_data:
                    frame_data = FrameHeatmapData(**cached_data)
                    frame_data_list.append(frame_data)
                    continue
                
                # Generate data if not cached
                frame_analysis = await frame_analysis_service.get_frame_analysis_data(
                    analysis_id, frame_num
                )
                
                if frame_analysis:
                    frame_data = frame_analysis_service.generate_frame_heatmap_data(
                        frame_analysis=frame_analysis,
                        frame_number=frame_num,
                        grid_size=grid_size.value,
                        color_scheme=color_scheme.value
                    )
                    frame_data_list.append(frame_data)
                    
                    # Cache generated data
                    await cache_manager.cache_heatmap_data(
                        analysis_id, frame_num, grid_size.value, color_scheme.value,
                        frame_data.dict(), 3600
                    )
                    
            except Exception as e:
                logger.warning(f"Failed to generate heatmap data for frame {frame_num}: {str(e)}")
                continue
        
        # Calculate response metrics
        total_response_time_ms = int((time.time() - start_time) * 1000)
        
        return JSONResponse(
            content={
                "analysis_id": str(analysis_id),
                "frame_range": {
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                    "frame_step": frame_step
                },
                "frames_processed": len(frame_data_list),
                "total_frames_requested": (end_frame - start_frame) // frame_step + 1,
                "frame_data": [frame.dict() for frame in frame_data_list],
                "bulk_generation_time_ms": total_response_time_ms,
                "average_time_per_frame_ms": total_response_time_ms // max(len(frame_data_list), 1),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Bulk heatmap generation failed for analysis {analysis_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk heatmap generation failed: {str(e)}"
        )


@router.get(
    "/{analysis_id}/heatmap/invalidate",
    summary="Invalidate heatmap cache",
    description="Invalidate cached heatmap data for an analysis (useful when FrameAnalysis data is updated)"
)
async def invalidate_heatmap_cache(
    analysis_id: UUID,
    frame_number: Optional[int] = Query(default=None, description="Specific frame to invalidate (all frames if not specified)")
):
    """
    Invalidate cached heatmap data for an analysis.
    
    This endpoint should be called when FrameAnalysis data is updated
    to ensure fresh heatmap generation.
    """
    
    try:
        logger.info(f"Invalidating heatmap cache for analysis {analysis_id}")
        
        if frame_number is not None:
            # Invalidate specific frame
            success = await cache_manager.invalidate_heatmap_cache_for_frame(analysis_id, frame_number)
            detail = f"Heatmap cache invalidated for analysis {analysis_id}, frame {frame_number}"
        else:
            # Invalidate all frames for analysis
            success = await cache_manager.invalidate_heatmap_cache(analysis_id)
            detail = f"Heatmap cache invalidated for all frames in analysis {analysis_id}"
        
        if success:
            return JSONResponse(
                content={
                    "analysis_id": str(analysis_id),
                    "frame_number": frame_number,
                    "status": "invalidated",
                    "message": detail,
                    "invalidated_at": datetime.now(timezone.utc).isoformat()
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to invalidate heatmap cache"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error invalidating heatmap cache for analysis {analysis_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache invalidation failed: {str(e)}"
        )


# Helper functions
async def _get_total_frame_count(analysis_id: UUID, db: AsyncSession) -> int:
    """Get total frame count for an analysis"""
    try:
        from sqlalchemy import select, func
        from ...ml_models.models import FrameAnalysis
        
        query = select(func.count(FrameAnalysis.frame_number)).where(
            FrameAnalysis.result_id == analysis_id
        )
        result = await db.execute(query)
        count = result.scalar() or 0
        
        return max(count, 0)  # Ensure non-negative
        
    except Exception as e:
        logger.error(f"Error getting total frame count for analysis {analysis_id}: {str(e)}")
        return 0


# Export router for inclusion in main API
__all__ = ['router']
