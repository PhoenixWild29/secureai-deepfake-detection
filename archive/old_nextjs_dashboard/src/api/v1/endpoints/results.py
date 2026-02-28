#!/usr/bin/env python3
"""
Results Export API Endpoints
FastAPI endpoints for multi-format report generation and export functionality
"""

from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from datetime import datetime, timezone
from enum import Enum
import json
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse as FastAPIJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

# Import integration wrapper (Work Order #20)
from ...api.integration_wrapper import CacheManager, BlockchainService, AuditLogger

# Import services
from ...services.report_generator import ReportGeneratorService

# Note: Database and models imports removed for simplified integration

# Create router
router = APIRouter(
    prefix="/v1/results",
    tags=["Results Export"],
    responses={
        404: {"description": "Analysis result not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)


class ExportFormat(str, Enum):
    """Supported export formats"""
    PDF = "pdf"
    JSON = "json"
    CSV = "csv"


@router.get(
    "/{analysis_id}/export",
    summary="Export detection results",
    description="Generate and download detection results report in PDF, JSON, or CSV format with blockchain verification data",
    responses={
        200: {
            "description": "Report exported successfully",
            "content": {
                "application/pdf": {"schema": {"type": "string", "format": "binary"}},
                "application/json": {"schema": {"type": "object"}},
                "text/csv": {"schema": {"type": "string", "format": "binary"}}
            }
        },
        404: {"description": "Analysis result not found"},
        422: {"description": "Invalid export format or analysis ID"},
        500: {"description": "Report generation failed"}
    }
)
async def export_results(
    analysis_id: UUID,
    format: ExportFormat = Query(default=ExportFormat.PDF, description="Export format: pdf, json, or csv")
):
    """
    Export detection results in the specified format.
    
    Supports format negotiation through:
    1. Query parameter: ?format=pdf|json|csv
    2. Accept header: Accept: application/pdf, application/json, text/csv
    
    Returns:
    - PDF: Professional stakeholder-ready report
    - JSON: Complete machine-readable detection data
    - CSV: Tabular format for data analysis
    """
    
    # Initialize services (using simplified versions from integration wrapper)
    cache_manager = CacheManager
    report_generator = ReportGeneratorService()
    blockchain_service = BlockchainService
    audit_logger = AuditLogger
    
    try:
        # Log export request for audit trail
        await audit_logger.log_export_request(
            analysis_id=str(analysis_id),
            export_format=str(format.value),
            user_id=None,  # Will be added when auth is implemented
            request_metadata={"endpoint": f"/v1/results/{analysis_id}/export"}
        )
        
        # Retrieve cached detection results
        detection_data = await cache_manager.get_cached_detection_result(analysis_id)
        if not detection_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis result {analysis_id} not found in cache"
            )
        
        # Retrieve blockchain verification data
        blockchain_data = await blockchain_service.get_verification_status(analysis_id)
        
        # Generate format-specific export
        if format.value == ExportFormat.PDF:
            return await _generate_pdf_export(
                report_generator, 
                analysis_id, 
                detection_data, 
                blockchain_data
            )
        elif format.value == ExportFormat.JSON:
            return await _generate_json_export(
                report_generator, 
                analysis_id, 
                detection_data, 
                blockchain_data
            )
        elif format.value == ExportFormat.CSV:
            return await _generate_csv_export(
                report_generator, 
                analysis_id, 
                detection_data, 
                blockchain_data
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported export format: {format}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        # Log export failure for audit trail
        await audit_logger.log_export_failure(
            analysis_id=str(analysis_id),
            export_format=str(format.value),
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}"
        )


async def _generate_pdf_export(
    report_generator: ReportGeneratorService,
    analysis_id: UUID,
    detection_data: Dict[str, Any],
    blockchain_data: Dict[str, Any]
) -> StreamingResponse:
    """Generate PDF export with proper headers"""
    
    # Generate PDF report
    pdf_content = await report_generator.generate_pdf_report(
        analysis_id=analysis_id,
        detection_data=detection_data,
        blockchain_data=blockchain_data
    )
    
    # Create streaming response
    def generate():
        yield pdf_content
    
    filename = f"secureai_detection_report_{analysis_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return StreamingResponse(
        generate(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Filename": filename,
            "X-Analysis-ID": str(analysis_id)
        }
    )


async def _generate_json_export(
    report_generator: ReportGeneratorService,
    analysis_id: UUID,
    detection_data: Dict[str, Any],
    blockchain_data: Dict[str, Any]
) -> FastAPIJSONResponse:
    """Generate JSON export with proper headers"""
    
    # Generate JSON report
    json_data = await report_generator.generate_json_export(
        analysis_id=analysis_id,
        detection_data=detection_data,
        blockchain_data=blockchain_data
    )
    
    filename = f"secureai_detection_data_{analysis_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    return FastAPIJSONResponse(
        content=json_data,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Filename": filename,
            "X-Analysis-ID": str(analysis_id)
        }
    )


async def _generate_csv_export(
    report_generator: ReportGeneratorService,
    analysis_id: UUID,
    detection_data: Dict[str, Any],
    blockchain_data: Dict[str, Any]
) -> StreamingResponse:
    """Generate CSV export with proper headers"""
    
    # Generate CSV report
    csv_content = await report_generator.generate_csv_export(
        analysis_id=analysis_id,
        detection_data=detection_data,
        blockchain_data=blockchain_data
    )
    
    # Create streaming response
    def generate():
        yield csv_content.encode('utf-8')
    
    filename = f"secureai_detection_data_{analysis_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Filename": filename,
            "X-Analysis-ID": str(analysis_id),
            "Content-Type": "text/csv; charset=utf-8"
        }
    )


# Additional endpoint for bulk export
@router.get(
    "/bulk-export",
    summary="Bulk export multiple analysis results",
    description="Export multiple analysis results in a single ZIP archive with separate files for each analysis"
)
async def bulk_export_results(
    analysis_ids: List[UUID] = Query(description="Comma-separated list of analysis IDs"),
    format: ExportFormat = Query(default=ExportFormat.JSON, description="Export format for all files")
):
    """
    Bulk export multiple analysis results in the specified format.
    
    Returns a ZIP archive containing separate files for each analysis.
    Useful for batch processing and regulatory documentation.
    """
    
    # Initialize services (using simplified versions from integration wrapper)
    cache_manager = CacheManager
    report_generator = ReportGeneratorService()
    blockchain_service = BlockchainService
    audit_logger = AuditLogger
    
    try:
        # Log bulk export request
        await audit_logger.log_bulk_export_request(
            analysis_ids=[str(aid) for aid in analysis_ids],
            export_format=str(format.value),
            user_id=None
        )
        
        # Generate bulk report (implementation will be added to ReportGeneratorService)
        zip_content = await report_generator.generate_bulk_export(
            analysis_ids=analysis_ids,
            format=format.value,
            cache_manager=cache_manager,
            blockchain_service=blockchain_service
        )
        
        filename = f"secureai_bulk_detection_reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        def generate():
            yield zip_content.getvalue()
        
        return StreamingResponse(
            generate(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Filename": filename,
                "X-Record-Count": str(len(analysis_ids))
            }
        )
        
    except Exception as e:
        await audit_logger.log_export_failure(
            analysis_id="bulk_export",
            export_format=str(format.value),
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk export failed: {str(e)}"
        )
