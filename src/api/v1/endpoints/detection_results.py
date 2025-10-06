#!/usr/bin/env python3
"""
Detection Results API Endpoints
FastAPI endpoints for visualization and export functionality
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

# Import database session dependency
from ...database.config import get_db_session

# Import services
from ...services.detection_query_service import DetectionQueryService
from ...services.detection_validation_service import DetectionValidationService
from ...services.detection_serialization_service import DetectionSerializationService

# Import models
from ...models.detection_results import (
    VisualizationResultResponse,
    ExportResultRequest,
    BlockchainVerificationResponse,
    DetectionResultSearchRequest,
    ExportFormatEnum
)

# Create router
router = APIRouter(
    prefix="/detection-results",
    tags=["Detection Results"],
    responses={
        404: {"description": "Not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)


@router.get(
    "/{analysis_id}/visualization",
    response_model=VisualizationResultResponse,
    summary="Get visualization data for detection result",
    description="Retrieve comprehensive visualization data for a specific detection analysis including confidence distribution, suspicious regions summary, and blockchain verification status."
)
async def get_visualization_data(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get visualization data for a specific detection result.
    Returns enhanced data structure optimized for UI visualization.
    """
    try:
        # Initialize services
        query_service = DetectionQueryService(db)
        validation_service = DetectionValidationService(db)
        serialization_service = DetectionSerializationService()
        
        # Validate analysis ID exists
        await validation_service.validate_analysis_id(analysis_id)
        
        # Get detection result
        detection_result = await query_service.get_detection_result(analysis_id)
        if not detection_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Detection result for analysis ID {analysis_id} not found"
            )
        
        # Get frame analysis data
        frame_analyses = await query_service.get_frame_analysis_batch(
            detection_result.id, 
            limit=1000  # Get all frames for visualization
        )
        
        # Get confidence distribution
        confidence_distribution = await query_service.get_confidence_distribution(analysis_id)
        
        # Get suspicious regions summary
        suspicious_regions_summary = await query_service.get_suspicious_regions_summary(detection_result.id)
        
        # Get blockchain verification status
        blockchain_verification = await query_service.get_blockchain_verification_status(analysis_id)
        
        # Prepare visualization data
        visualization_data = {
            "analysis_id": analysis_id,
            "overall_confidence": float(detection_result.overall_confidence),
            "confidence_distribution": confidence_distribution,
            "suspicious_regions_summary": suspicious_regions_summary,
            "blockchain_verification": blockchain_verification,
            "export_formats": ["pdf", "json", "csv"],
            "heatmap_data": None,  # Optional, can be populated later
            "frame_count": detection_result.frame_count,
            "suspicious_frames_count": detection_result.suspicious_frames,
            "processing_time_ms": detection_result.processing_time_ms or 0,
            "created_at": detection_result.created_at
        }
        
        # Validate visualization data
        validation_result = await validation_service.validate_visualization_data(visualization_data)
        if not validation_result["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Visualization data validation failed: {validation_result['errors']}"
            )
        
        return VisualizationResultResponse(**visualization_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve visualization data: {str(e)}"
        )


@router.post(
    "/export",
    response_model=Dict[str, Any],
    summary="Export detection result",
    description="Export detection result in specified format (PDF, JSON, CSV) with configurable options for frame data and blockchain verification."
)
async def export_detection_result(
    export_request: ExportResultRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Export detection result in specified format.
    Returns serialized data ready for file generation.
    """
    try:
        # Initialize services
        query_service = DetectionQueryService(db)
        validation_service = DetectionValidationService(db)
        serialization_service = DetectionSerializationService()
        
        # Validate export format
        await validation_service.validate_export_format(export_request.format)
        
        # Validate export options
        options_validation = await validation_service.validate_export_options(export_request.export_options)
        if not options_validation["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Export options validation failed: {options_validation['errors']}"
            )
        
        # Validate analysis ID exists
        await validation_service.validate_analysis_id(export_request.analysis_id)
        
        # Get detection result
        detection_result = await query_service.get_detection_result(export_request.analysis_id)
        if not detection_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Detection result for analysis ID {export_request.analysis_id} not found"
            )
        
        # Prepare base result data
        result_data = {
            "analysis_id": export_request.analysis_id,
            "overall_confidence": float(detection_result.overall_confidence),
            "frame_count": detection_result.frame_count,
            "suspicious_frames": detection_result.suspicious_frames,
            "processing_time_ms": detection_result.processing_time_ms or 0,
            "created_at": detection_result.created_at,
            "blockchain_hash": detection_result.blockchain_hash
        }
        
        # Get frame data if requested
        frame_data = []
        if export_request.include_frames:
            frame_data = await query_service.get_frame_analysis_batch(
                detection_result.id, 
                limit=10000  # Large limit for export
            )
            result_data["frame_analysis"] = frame_data
        
        # Get blockchain verification if requested
        if export_request.include_blockchain:
            blockchain_verification = await query_service.get_blockchain_verification_status(export_request.analysis_id)
            result_data["blockchain_verification"] = blockchain_verification
        
        # Serialize based on format
        export_format = export_request.get_export_format_enum()
        
        if export_format == ExportFormatEnum.JSON:
            serialized_data = serialization_service.serialize_to_json(
                result_data,
                include_frames=export_request.include_frames,
                include_blockchain=export_request.include_blockchain
            )
        elif export_format == ExportFormatEnum.CSV:
            serialized_data = {
                "format": "csv",
                "data": serialization_service.prepare_csv_data(result_data, frame_data),
                "metadata": serialization_service.create_export_manifest(export_request.model_dump())
            }
        elif export_format == ExportFormatEnum.PDF:
            serialized_data = {
                "format": "pdf",
                "data": serialization_service.prepare_pdf_data(result_data, frame_data),
                "metadata": serialization_service.create_export_manifest(export_request.model_dump())
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported export format: {export_request.format}"
            )
        
        # Validate serialized data integrity
        if export_format == ExportFormatEnum.JSON:
            integrity_check = serialization_service.validate_export_data_integrity(serialized_data)
            if not integrity_check["is_valid"]:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Export data integrity check failed: {integrity_check['errors']}"
                )
        
        return serialized_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export detection result: {str(e)}"
        )


@router.get(
    "/{analysis_id}/blockchain-verification",
    response_model=BlockchainVerificationResponse,
    summary="Get blockchain verification status",
    description="Retrieve blockchain verification status and metadata for tamper-proof result validation."
)
async def get_blockchain_verification(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get blockchain verification status for a detection result.
    """
    try:
        # Initialize services
        query_service = DetectionQueryService(db)
        validation_service = DetectionValidationService(db)
        
        # Validate analysis ID exists
        await validation_service.validate_analysis_id(analysis_id)
        
        # Get blockchain verification status
        verification_data = await query_service.get_blockchain_verification_status(analysis_id)
        
        # Format response
        response_data = {
            "analysis_id": analysis_id,
            "blockchain_hash": verification_data.get("blockchain_hash"),
            "verification_status": verification_data.get("status"),
            "verification_timestamp": verification_data.get("verification_timestamp"),
            "verification_details": verification_data.get("verification_details", {}),
            "is_tamper_proof": verification_data.get("is_tamper_proof", False)
        }
        
        return BlockchainVerificationResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve blockchain verification: {str(e)}"
        )


@router.get(
    "/search",
    response_model=List[Dict[str, Any]],
    summary="Search detection results",
    description="Search and filter detection results by confidence score, frame count, and date range with pagination support."
)
async def search_detection_results(
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence score"),
    max_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Maximum confidence score"),
    min_frames: Optional[int] = Query(None, ge=0, description="Minimum frame count"),
    max_frames: Optional[int] = Query(None, ge=0, description="Maximum frame count"),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Search detection results with various filters and pagination.
    """
    try:
        # Initialize services
        query_service = DetectionQueryService(db)
        validation_service = DetectionValidationService(db)
        
        # Validate search parameters
        search_validation = await validation_service.validate_search_parameters(
            min_confidence=min_confidence,
            max_confidence=max_confidence,
            min_frames=min_frames,
            max_frames=max_frames,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        if not search_validation["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Search parameters validation failed: {search_validation['errors']}"
            )
        
        # Perform search based on criteria
        if min_confidence is not None or max_confidence is not None:
            results = await query_service.search_results_by_confidence(
                min_confidence=min_confidence,
                max_confidence=max_confidence,
                limit=limit,
                offset=offset
            )
        elif min_frames is not None or max_frames is not None:
            results = await query_service.get_results_by_frame_count(
                min_frames=min_frames,
                max_frames=max_frames,
                limit=limit,
                offset=offset
            )
        elif start_date is not None or end_date is not None:
            results = await query_service.get_results_by_date_range(
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                offset=offset
            )
        else:
            results = await query_service.get_recent_results(limit=limit, offset=offset)
        
        # Serialize results
        serialized_results = []
        for result in results:
            serialized_result = {
                "analysis_id": result.analysis_id,
                "overall_confidence": float(result.overall_confidence),
                "frame_count": result.frame_count,
                "suspicious_frames": result.suspicious_frames,
                "processing_time_ms": result.processing_time_ms or 0,
                "created_at": result.created_at.isoformat(),
                "blockchain_hash": result.blockchain_hash,
                "has_blockchain_verification": bool(result.blockchain_hash)
            }
            serialized_results.append(serialized_result)
        
        return serialized_results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search detection results: {str(e)}"
        )


@router.get(
    "/recent",
    response_model=List[Dict[str, Any]],
    summary="Get recent detection results",
    description="Retrieve recent detection results with pagination support."
)
async def get_recent_results(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get recent detection results ordered by creation time.
    """
    try:
        # Initialize services
        query_service = DetectionQueryService(db)
        
        # Get recent results
        results = await query_service.get_recent_results(limit=limit, offset=offset)
        
        # Serialize results
        serialized_results = []
        for result in results:
            serialized_result = {
                "analysis_id": result.analysis_id,
                "overall_confidence": float(result.overall_confidence),
                "frame_count": result.frame_count,
                "suspicious_frames": result.suspicious_frames,
                "processing_time_ms": result.processing_time_ms or 0,
                "created_at": result.created_at.isoformat(),
                "blockchain_hash": result.blockchain_hash,
                "has_blockchain_verification": bool(result.blockchain_hash)
            }
            serialized_results.append(serialized_result)
        
        return serialized_results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve recent results: {str(e)}"
        )


@router.get(
    "/statistics",
    response_model=Dict[str, Any],
    summary="Get detection statistics",
    description="Retrieve overall detection statistics for dashboard and analytics."
)
async def get_detection_statistics(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get overall detection statistics.
    """
    try:
        # Initialize services
        query_service = DetectionQueryService(db)
        
        # Get statistics
        statistics = await query_service.get_detection_statistics()
        
        return statistics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


@router.get(
    "/high-confidence",
    response_model=List[Dict[str, Any]],
    summary="Get high confidence results",
    description="Retrieve high confidence detection results for quality analysis."
)
async def get_high_confidence_results(
    threshold: float = Query(0.8, ge=0.0, le=1.0, description="Confidence threshold"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get high confidence detection results.
    """
    try:
        # Initialize services
        query_service = DetectionQueryService(db)
        
        # Get high confidence results
        results = await query_service.get_high_confidence_results(threshold=threshold, limit=limit)
        
        # Serialize results
        serialized_results = []
        for result in results:
            serialized_result = {
                "analysis_id": result.analysis_id,
                "overall_confidence": float(result.overall_confidence),
                "frame_count": result.frame_count,
                "suspicious_frames": result.suspicious_frames,
                "processing_time_ms": result.processing_time_ms or 0,
                "created_at": result.created_at.isoformat(),
                "blockchain_hash": result.blockchain_hash,
                "has_blockchain_verification": bool(result.blockchain_hash)
            }
            serialized_results.append(serialized_result)
        
        return serialized_results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve high confidence results: {str(e)}"
        )
