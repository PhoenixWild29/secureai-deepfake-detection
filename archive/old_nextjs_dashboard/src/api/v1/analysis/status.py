"""
Analysis Status API Endpoint
FastAPI endpoint for fetching analysis processing status and resource monitoring data
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import structlog
from datetime import datetime, timezone

from ..services.analysis_status_service import AnalysisStatusService
from ..models.analysis_status import (
    AnalysisStatusResponse,
    ProcessingStageResponse,
    WorkerInfoResponse,
    GPUInfoResponse,
    QueueInfoResponse,
    ResourceMetricsResponse
)
from ..auth.dependencies import get_current_user
from ..models.user import User

logger = structlog.get_logger(__name__)

# Create router
analysis_status_router = APIRouter(prefix="/api/v1/analysis", tags=["analysis-status"])

# Initialize service
analysis_status_service = AnalysisStatusService()

@analysis_status_router.get("/{analysis_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    analysis_id: str,
    include_workers: bool = Query(True, description="Include worker allocation information"),
    include_gpu: bool = Query(True, description="Include GPU utilization information"),
    include_queue: bool = Query(True, description="Include queue status information"),
    include_resources: bool = Query(True, description="Include system resource metrics"),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive analysis status including processing stages, worker allocation,
    GPU utilization, queue status, and system resource metrics.
    
    Args:
        analysis_id: Unique identifier for the analysis
        include_workers: Whether to include worker allocation information
        include_gpu: Whether to include GPU utilization information
        include_queue: Whether to include queue status information
        include_resources: Whether to include system resource metrics
        current_user: Authenticated user making the request
    
    Returns:
        AnalysisStatusResponse: Comprehensive analysis status information
    """
    try:
        logger.info(
            "Fetching analysis status",
            analysis_id=analysis_id,
            user_id=current_user.id,
            include_workers=include_workers,
            include_gpu=include_gpu,
            include_queue=include_queue,
            include_resources=include_resources
        )

        # Get analysis status from service
        analysis_status = await analysis_status_service.get_analysis_status(
            analysis_id=analysis_id,
            include_workers=include_workers,
            include_gpu=include_gpu,
            include_queue=include_queue,
            include_resources=include_resources
        )

        if not analysis_status:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis with ID {analysis_id} not found"
            )

        logger.info(
            "Analysis status retrieved successfully",
            analysis_id=analysis_id,
            current_stage=analysis_status.current_stage,
            overall_progress=analysis_status.overall_progress,
            status=analysis_status.status
        )

        return analysis_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching analysis status",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching analysis status"
        )

@analysis_status_router.get("/{analysis_id}/stages", response_model=list[ProcessingStageResponse])
async def get_analysis_stages(
    analysis_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed processing stages information for a specific analysis.
    
    Args:
        analysis_id: Unique identifier for the analysis
        current_user: Authenticated user making the request
    
    Returns:
        List[ProcessingStageResponse]: List of processing stages with detailed information
    """
    try:
        logger.info(
            "Fetching analysis stages",
            analysis_id=analysis_id,
            user_id=current_user.id
        )

        stages = await analysis_status_service.get_analysis_stages(analysis_id)

        if not stages:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis stages for ID {analysis_id} not found"
            )

        logger.info(
            "Analysis stages retrieved successfully",
            analysis_id=analysis_id,
            stages_count=len(stages)
        )

        return stages

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching analysis stages",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching analysis stages"
        )

@analysis_status_router.get("/workers/status", response_model=list[WorkerInfoResponse])
async def get_workers_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get current status of all Celery workers.
    
    Args:
        current_user: Authenticated user making the request
    
    Returns:
        List[WorkerInfoResponse]: List of worker information with status and metrics
    """
    try:
        logger.info(
            "Fetching workers status",
            user_id=current_user.id
        )

        workers = await analysis_status_service.get_workers_status()

        logger.info(
            "Workers status retrieved successfully",
            workers_count=len(workers)
        )

        return workers

    except Exception as e:
        logger.error(
            "Error fetching workers status",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching workers status"
        )

@analysis_status_router.get("/gpu/status", response_model=list[GPUInfoResponse])
async def get_gpu_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get current GPU utilization and status information.
    
    Args:
        current_user: Authenticated user making the request
    
    Returns:
        List[GPUInfoResponse]: List of GPU information with utilization metrics
    """
    try:
        logger.info(
            "Fetching GPU status",
            user_id=current_user.id
        )

        gpus = await analysis_status_service.get_gpu_status()

        logger.info(
            "GPU status retrieved successfully",
            gpus_count=len(gpus)
        )

        return gpus

    except Exception as e:
        logger.error(
            "Error fetching GPU status",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching GPU status"
        )

@analysis_status_router.get("/queue/status", response_model=QueueInfoResponse)
async def get_queue_status(
    queue_id: Optional[str] = Query(None, description="Specific queue ID to query"),
    current_user: User = Depends(get_current_user)
):
    """
    Get processing queue status and metrics.
    
    Args:
        queue_id: Optional specific queue ID to query
        current_user: Authenticated user making the request
    
    Returns:
        QueueInfoResponse: Queue status and metrics information
    """
    try:
        logger.info(
            "Fetching queue status",
            queue_id=queue_id,
            user_id=current_user.id
        )

        queue_info = await analysis_status_service.get_queue_status(queue_id)

        logger.info(
            "Queue status retrieved successfully",
            queue_id=queue_info.id if queue_info else None,
            position=queue_info.position if queue_info else None,
            total_items=queue_info.total_items if queue_info else None
        )

        return queue_info

    except Exception as e:
        logger.error(
            "Error fetching queue status",
            queue_id=queue_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching queue status"
        )

@analysis_status_router.get("/system/metrics", response_model=ResourceMetricsResponse)
async def get_system_metrics(
    current_user: User = Depends(get_current_user)
):
    """
    Get current system resource metrics.
    
    Args:
        current_user: Authenticated user making the request
    
    Returns:
        ResourceMetricsResponse: System resource metrics information
    """
    try:
        logger.info(
            "Fetching system metrics",
            user_id=current_user.id
        )

        metrics = await analysis_status_service.get_system_metrics()

        logger.info(
            "System metrics retrieved successfully",
            cpu_usage=metrics.system_cpu_usage if metrics else None,
            memory_usage=metrics.system_memory_usage_percentage if metrics else None
        )

        return metrics

    except Exception as e:
        logger.error(
            "Error fetching system metrics",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching system metrics"
        )

@analysis_status_router.get("/{analysis_id}/history")
async def get_analysis_history(
    analysis_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of history entries to return"),
    current_user: User = Depends(get_current_user)
):
    """
    Get historical status updates for a specific analysis.
    
    Args:
        analysis_id: Unique identifier for the analysis
        limit: Maximum number of history entries to return
        current_user: Authenticated user making the request
    
    Returns:
        Dict containing historical status updates
    """
    try:
        logger.info(
            "Fetching analysis history",
            analysis_id=analysis_id,
            limit=limit,
            user_id=current_user.id
        )

        history = await analysis_status_service.get_analysis_history(
            analysis_id=analysis_id,
            limit=limit
        )

        logger.info(
            "Analysis history retrieved successfully",
            analysis_id=analysis_id,
            history_count=len(history) if history else 0
        )

        return {
            "analysis_id": analysis_id,
            "history": history or [],
            "count": len(history) if history else 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(
            "Error fetching analysis history",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching analysis history"
        )

@analysis_status_router.get("/health")
async def health_check():
    """
    Health check endpoint for the analysis status service.
    
    Returns:
        Dict containing service health status
    """
    try:
        health_status = await analysis_status_service.health_check()
        
        return {
            "status": "healthy" if health_status else "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "analysis-status"
        }
    except Exception as e:
        logger.error(
            "Health check failed",
            error=str(e),
            exc_info=True
        )
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "analysis-status",
                "error": str(e)
            }
        )
