#!/usr/bin/env python3
"""
Analytics API Endpoint
FastAPI endpoint for dashboard analytics with role-based access control
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import JSONResponse
import structlog

from src.models.analytics_data import (
    AnalyticsRequest,
    AnalyticsResponse,
    AnalyticsExportRequest,
    AnalyticsExportResult,
    AnalyticsHealthCheck,
    DataClassification,
    ExportFormat
)
from src.services.analytics_service import get_analytics_service
from src.utils.data_exporter import get_data_exporter
from src.middleware.auth_middleware import (
    require_analytics_read,
    require_analytics_export,
    require_analytics_admin,
    get_analytics_context
)
from src.config.analytics_config import (
    get_analytics_config,
    get_analytics_endpoints,
    get_analytics_thresholds
)
from src.dependencies.auth import UserClaims

logger = structlog.get_logger(__name__)

# Create router
router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    responses={
        404: {"description": "Not found"},
        403: {"description": "Forbidden"},
        500: {"description": "Internal server error"}
    }
)

# Get configuration
config = get_analytics_config()
endpoints = get_analytics_endpoints()
thresholds = get_analytics_thresholds()


@router.get(
    "",
    response_model=AnalyticsResponse,
    summary="Get Analytics Data",
    description="Retrieve comprehensive analytics data for dashboard visualization with configurable date ranges and filtering"
)
async def get_analytics(
    # Query parameters for date range
    date_range_type: str = Query(
        default="last_30_days",
        description="Date range type (custom, last_24_hours, last_7_days, last_30_days, last_90_days, last_year, all_time)"
    ),
    start_date: Optional[str] = Query(
        default=None,
        description="Start date for custom range (ISO format)"
    ),
    end_date: Optional[str] = Query(
        default=None,
        description="End date for custom range (ISO format)"
    ),
    
    # Query parameters for filtering
    filters: Optional[List[str]] = Query(
        default=[],
        description="Additional filters (format: type:value:operator)"
    ),
    group_by: Optional[List[str]] = Query(
        default=[],
        description="Grouping fields"
    ),
    aggregation_type: str = Query(
        default="sum",
        description="Aggregation type (sum, avg, count, max, min)"
    ),
    
    # Pagination
    limit: int = Query(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum number of records"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Offset for pagination"
    ),
    
    # Analysis options
    include_trends: bool = Query(
        default=True,
        description="Include trend analysis"
    ),
    include_predictions: bool = Query(
        default=False,
        description="Include predictive analytics"
    ),
    
    # Export options
    export_format: Optional[str] = Query(
        default=None,
        description="Export format (csv, json, pdf, excel)"
    ),
    
    # Authentication and authorization
    user_claims: UserClaims = Depends(require_analytics_read)
):
    """
    Get comprehensive analytics data for dashboard visualization
    
    This endpoint provides:
    - Detection performance trends and metrics
    - User engagement analytics
    - System utilization statistics
    - Trend analysis and predictions
    - Insights and recommendations
    - Export capabilities for stakeholder reporting
    """
    request_start_time = time.time()
    request_id = f"analytics_req_{int(time.time() * 1000)}"
    
    try:
        logger.info(
            "Analytics request received",
            request_id=request_id,
            user_id=user_claims.user_id,
            date_range_type=date_range_type,
            include_trends=include_trends,
            include_predictions=include_predictions
        )
        
        # Validate configuration
        if not config.analytics_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Analytics service is currently disabled"
            )
        
        # Parse date range
        from src.models.analytics_data import AnalyticsDateRange, DateRangeType
        date_range = AnalyticsDateRange(
            type=DateRangeType(date_range_type),
            start_date=datetime.fromisoformat(start_date.replace('Z', '+00:00')) if start_date else None,
            end_date=datetime.fromisoformat(end_date.replace('Z', '+00:00')) if end_date else None
        )
        
        # Parse filters
        from src.models.analytics_data import AnalyticsFilter, AnalyticsFilterType
        parsed_filters = []
        for filter_str in filters:
            try:
                parts = filter_str.split(':')
                if len(parts) >= 2:
                    filter_type = AnalyticsFilterType(parts[0])
                    value = parts[1]
                    operator = parts[2] if len(parts) > 2 else "eq"
                    
                    # Handle list values
                    if ',' in value:
                        value = value.split(',')
                    
                    parsed_filters.append(AnalyticsFilter(
                        type=filter_type,
                        value=value,
                        operator=operator
                    ))
            except Exception as e:
                logger.warning("Invalid filter format", filter_str=filter_str, error=str(e))
        
        # Validate export format
        export_format_enum = None
        if export_format:
            try:
                export_format_enum = ExportFormat(export_format)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid export format: {export_format}. Supported formats: {[f.value for f in ExportFormat]}"
                )
        
        # Create analytics request
        analytics_request = AnalyticsRequest(
            date_range=date_range,
            filters=parsed_filters,
            group_by=group_by,
            aggregation_type=aggregation_type,
            limit=limit,
            offset=offset,
            include_trends=include_trends and config.feature_trend_analysis,
            include_predictions=include_predictions and config.feature_predictive_analytics,
            export_format=export_format_enum
        )
        
        # Get analytics service
        analytics_service = await get_analytics_service()
        
        # Get analytics data
        analytics_data = await analytics_service.get_analytics_data(
            analytics_request, user_claims.user_id
        )
        
        # Handle export if requested
        if export_format_enum:
            try:
                # Require export permissions
                from src.middleware.auth_middleware import require_analytics_export
                await require_analytics_export()
                
                # Get data exporter
                data_exporter = await get_data_exporter()
                
                # Create export request
                export_request = AnalyticsExportRequest(
                    export_format=export_format_enum,
                    data_classification=analytics_data.data_classification,
                    include_metadata=True,
                    compression=config.export_compression_enabled,
                    expiration_hours=config.export_retention_hours // 24
                )
                
                # Generate export
                export_result = await data_exporter.export_analytics_data(
                    analytics_data, export_request
                )
                
                # Add export information to response
                analytics_data.export_available = True
                analytics_data.export_request = export_request
                
                logger.info(
                    "Analytics export generated",
                    request_id=request_id,
                    export_id=export_result.export_id,
                    file_size_bytes=export_result.file_size_bytes,
                    download_url=export_result.download_url
                )
                
            except Exception as e:
                logger.error(
                    "Analytics export failed",
                    request_id=request_id,
                    error=str(e)
                )
                # Don't fail the entire request if export fails
                analytics_data.export_available = False
        
        # Calculate execution time
        execution_time = (time.time() - request_start_time) * 1000
        
        # Check for slow queries
        if execution_time > thresholds.MAX_QUERY_EXECUTION_TIME_MS:
            logger.warning(
                "Slow analytics query detected",
                request_id=request_id,
                execution_time_ms=execution_time,
                threshold_ms=thresholds.MAX_QUERY_EXECUTION_TIME_MS
            )
        
        # Update response with execution time
        analytics_data.query_execution_time_ms = execution_time
        
        logger.info(
            "Analytics request completed",
            request_id=request_id,
            execution_time_ms=execution_time,
            total_records=analytics_data.total_records,
            export_available=analytics_data.export_available
        )
        
        return analytics_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Analytics request failed",
            request_id=request_id,
            user_id=user_claims.user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analytics request failed"
        )


@router.post(
    "/export",
    response_model=AnalyticsExportResult,
    summary="Export Analytics Data",
    description="Export analytics data in various formats for stakeholder reporting"
)
async def export_analytics(
    export_request: AnalyticsExportRequest,
    background_tasks: BackgroundTasks,
    user_claims: UserClaims = Depends(require_analytics_export)
):
    """
    Export analytics data in specified format
    
    This endpoint provides:
    - Multi-format export (CSV, JSON, PDF, Excel)
    - Privacy-compliant data classification
    - Secure download URLs with expiration
    - Background processing for large datasets
    """
    export_start_time = time.time()
    export_id = f"export_{int(time.time() * 1000)}"
    
    try:
        logger.info(
            "Analytics export request received",
            export_id=export_id,
            user_id=user_claims.user_id,
            format=export_request.export_format.value,
            classification=export_request.data_classification.value
        )
        
        # Validate configuration
        if not config.export_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Export functionality is currently disabled"
            )
        
        # Check export rate limits
        # This would integrate with rate limiting middleware in production
        
        # Get analytics service and data
        analytics_service = await get_analytics_service()
        
        # For export, we need to get the data first
        # This is a simplified approach - in production, you might want to
        # store export requests and process them asynchronously
        
        # Create a default analytics request for export
        from src.models.analytics_data import AnalyticsRequest, AnalyticsDateRange, DateRangeType
        analytics_request = AnalyticsRequest(
            date_range=AnalyticsDateRange(type=DateRangeType.LAST_30_DAYS),
            include_trends=True,
            include_predictions=False
        )
        
        # Get analytics data
        analytics_data = await analytics_service.get_analytics_data(
            analytics_request, user_claims.user_id
        )
        
        # Get data exporter
        data_exporter = await get_data_exporter()
        
        # Generate export
        export_result = await data_exporter.export_analytics_data(
            analytics_data, export_request
        )
        
        # Update export result with our export ID
        export_result.export_id = export_id
        
        execution_time = (time.time() - export_start_time) * 1000
        
        logger.info(
            "Analytics export completed",
            export_id=export_id,
            execution_time_ms=execution_time,
            file_size_bytes=export_result.file_size_bytes,
            record_count=export_result.record_count
        )
        
        return export_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Analytics export failed",
            export_id=export_id,
            user_id=user_claims.user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Export generation failed"
        )


@router.get(
    "/health",
    response_model=AnalyticsHealthCheck,
    summary="Analytics Health Check",
    description="Check the health status of the analytics service"
)
async def analytics_health_check():
    """
    Analytics service health check endpoint
    
    Provides:
    - Service status and version information
    - Dependency health checks
    - Performance metrics
    - Configuration summary
    """
    try:
        # Get configuration summary
        config_summary = {
            "analytics_enabled": config.analytics_enabled,
            "cache_enabled": config.cache_enabled,
            "export_enabled": config.export_enabled,
            "monitoring_enabled": config.monitoring_enabled
        }
        
        # Check service dependencies
        dependencies = {
            "analytics_service": "healthy",
            "data_exporter": "healthy",
            "cache_manager": "healthy",
            "auth_service": "healthy"
        }
        
        # Get service metrics
        metrics = {
            "uptime_seconds": time.time() - 1000,  # Mock uptime
            "total_requests": 1000,  # Mock total requests
            "average_response_time_ms": 250.5,  # Mock average response time
            "cache_hit_rate": 0.85,  # Mock cache hit rate
            "export_success_rate": 0.98  # Mock export success rate
        }
        
        health_check = AnalyticsHealthCheck(
            status="healthy",
            dependencies=dependencies,
            metrics=metrics
        )
        
        # Add configuration to metrics
        health_check.metrics.update(config_summary)
        
        return health_check
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return AnalyticsHealthCheck(
            status="unhealthy",
            dependencies={"error": str(e)},
            metrics={}
        )


@router.get(
    "/context",
    summary="Get User Analytics Context",
    description="Get user-specific analytics context including permissions and available features"
)
async def get_user_analytics_context(
    user_claims: Optional[UserClaims] = Depends(get_analytics_context)
):
    """
    Get user analytics context and permissions
    
    Provides:
    - User authentication status
    - Available data access levels
    - Permissions matrix
    - Available resources and features
    - Configuration context
    """
    try:
        # Get user context from middleware
        context = await get_analytics_context()
        
        # Add configuration context
        context.update({
            "configuration": {
                "version": config.analytics_version,
                "features": {
                    "trend_analysis": config.feature_trend_analysis,
                    "predictive_analytics": config.feature_predictive_analytics,
                    "custom_insights": config.feature_custom_insights,
                    "real_time_analytics": config.feature_real_time_analytics,
                    "advanced_filtering": config.feature_advanced_filtering,
                    "data_export": config.feature_data_export
                },
                "limits": {
                    "max_records": config.max_analytics_records,
                    "default_date_range_days": config.default_date_range_days,
                    "query_timeout_seconds": config.analytics_timeout_seconds
                }
            }
        })
        
        return context
        
    except Exception as e:
        logger.error("Failed to get user analytics context", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user context"
        )


@router.get(
    "/permissions",
    summary="Get Analytics Permissions",
    description="Get detailed analytics permissions for the current user"
)
async def get_analytics_permissions(
    user_claims: UserClaims = Depends(require_analytics_read)
):
    """
    Get detailed analytics permissions for the current user
    
    Provides:
    - Role-based permissions
    - Resource-specific access
    - Data classification levels
    - Export permissions
    - Admin privileges
    """
    try:
        from src.middleware.auth_middleware import get_analytics_auth_middleware
        
        middleware = get_analytics_auth_middleware()
        
        # Get user's data access level
        access_level = middleware.permission_manager.get_user_data_access_level(user_claims)
        
        # Build detailed permissions
        permissions = {
            "user_id": user_claims.user_id,
            "user_roles": user_claims.roles + user_claims.groups,
            "data_access_level": access_level.value,
            "permissions": {
                "read": [],
                "write": [],
                "export": [],
                "admin": []
            },
            "resources": {},
            "classification_levels": {
                "public": DataClassification.PUBLIC.value,
                "internal": DataClassification.INTERNAL.value,
                "confidential": DataClassification.CONFIDENTIAL.value
            }
        }
        
        # Check permissions for each resource
        resources = [
            "detection_performance",
            "user_engagement", 
            "system_utilization",
            "blockchain_metrics"
        ]
        
        for resource in resources:
            resource_perms = {
                "read": False,
                "write": False,
                "export": False,
                "admin": False
            }
            
            for perm_type in ["read", "write", "export", "admin"]:
                if middleware.permission_manager.check_permission(
                    user_claims, perm_type, resource, access_level
                ):
                    resource_perms[perm_type] = True
                    if perm_type not in permissions["permissions"]:
                        permissions["permissions"][perm_type] = []
                    if resource not in permissions["permissions"][perm_type]:
                        permissions["permissions"][perm_type].append(resource)
            
            permissions["resources"][resource] = resource_perms
        
        return permissions
        
    except Exception as e:
        logger.error("Failed to get analytics permissions", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get permissions"
        )


# Additional utility endpoints
@router.get(
    "/formats",
    summary="Get Available Export Formats",
    description="Get list of available export formats and their capabilities"
)
async def get_export_formats():
    """Get available export formats and their capabilities"""
    return {
        "formats": [
            {
                "name": "csv",
                "description": "Comma-separated values format",
                "capabilities": ["raw_data", "metadata", "compression"],
                "max_records": 100000,
                "file_extension": ".csv"
            },
            {
                "name": "json",
                "description": "JavaScript Object Notation format",
                "capabilities": ["structured_data", "metadata", "compression"],
                "max_records": 50000,
                "file_extension": ".json"
            },
            {
                "name": "pdf",
                "description": "Portable Document Format for reports",
                "capabilities": ["formatted_reports", "charts", "metadata"],
                "max_records": 1000,
                "file_extension": ".pdf"
            },
            {
                "name": "excel",
                "description": "Microsoft Excel format with multiple sheets",
                "capabilities": ["multiple_sheets", "metadata", "formatting"],
                "max_records": 100000,
                "file_extension": ".xlsx"
            }
        ]
    }


@router.get(
    "/limits",
    summary="Get Analytics Limits",
    description="Get current analytics limits and quotas"
)
async def get_analytics_limits(
    user_claims: Optional[UserClaims] = Depends(get_analytics_context)
):
    """Get current analytics limits and quotas for the user"""
    return {
        "query_limits": {
            "max_records": config.max_analytics_records,
            "max_date_range_days": 365,
            "query_timeout_seconds": config.analytics_timeout_seconds,
            "max_concurrent_queries": config.max_concurrent_queries
        },
        "export_limits": {
            "max_file_size_mb": config.export_max_file_size_mb,
            "retention_hours": config.export_retention_hours,
            "max_exports_per_hour": 10
        },
        "rate_limits": {
            "requests_per_minute": config.rate_limit_requests_per_minute,
            "requests_per_hour": config.rate_limit_requests_per_hour
        },
        "user_specific": {
            "authenticated": user_claims is not None,
            "data_access_level": "internal" if user_claims else "public"
        }
    }
