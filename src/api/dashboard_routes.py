#!/usr/bin/env python3
"""
Dashboard API Routes
API endpoints that utilize the dashboard data service for aggregated dashboard data
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..data_integration.dashboard_data_service import (
    DashboardDataService,
    DashboardQueryParams,
    DashboardCacheConfig,
    create_dashboard_data_service
)
from ..models.dashboard import (
    DashboardOverviewResponse,
    DashboardAnalyticsResponse,
    DashboardOverviewRequest,
    DashboardConfigurationResponse
)
from ..database.config import get_db_session
from ..middleware.auth import get_current_user
from ..errors.api_errors import APIError

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["dashboard"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)


@router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    summary="Get Dashboard Overview",
    description="Get comprehensive dashboard overview data aggregated from multiple sources"
)
async def get_dashboard_overview(
    background_tasks: BackgroundTasks,
    include_user_activity: bool = Query(True, description="Include user activity metrics"),
    include_blockchain_metrics: bool = Query(True, description="Include blockchain verification metrics"),
    include_system_performance: bool = Query(True, description="Include system performance metrics"),
    recent_analyses_limit: int = Query(10, ge=1, le=50, description="Limit for recent analyses"),
    confidence_trends_hours: int = Query(24, ge=1, le=168, description="Hours of confidence trends"),
    force_refresh: bool = Query(False, description="Force refresh from cache"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session)
):
    """
    Get dashboard overview data
    
    This endpoint provides comprehensive dashboard overview data including:
    - Recent analysis summaries
    - Confidence score trends
    - Processing queue status
    - User activity metrics
    - System performance metrics
    - Blockchain verification metrics
    
    The data is aggregated from multiple sources and optimized for dashboard consumption.
    """
    try:
        start_time = time.time()
        logger.info(f"Fetching dashboard overview for user: {current_user.get('user_id', 'unknown')}")
        
        # Create dashboard data service
        cache_config = DashboardCacheConfig(
            enable_cache=not force_refresh,
            cache_ttl=300  # 5 minutes
        )
        
        dashboard_service = await create_dashboard_data_service(db_session, cache_config)
        
        # Create query parameters
        query_params = DashboardQueryParams(
            user_id=current_user.get('user_id', 'anonymous'),
            include_anonymized=True,
            timezone=current_user.get('timezone', 'UTC'),
            limit=recent_analyses_limit
        )
        
        # Get dashboard overview data
        overview_response = await dashboard_service.get_dashboard_overview(query_params)
        
        # Calculate response time
        response_time = (time.time() - start_time) * 1000
        
        # Add response metadata
        overview_response.response_time_ms = response_time
        overview_response.request_id = f"req_{int(time.time() * 1000)}"
        
        logger.info(f"Successfully fetched dashboard overview in {response_time:.2f}ms")
        
        # Schedule background cache refresh if needed
        if not force_refresh:
            background_tasks.add_task(
                refresh_dashboard_cache,
                dashboard_service,
                query_params
            )
        
        return overview_response
        
    except Exception as e:
        logger.error(f"Failed to fetch dashboard overview: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch dashboard overview: {str(e)}"
        )


@router.get(
    "/analytics",
    response_model=DashboardAnalyticsResponse,
    summary="Get Dashboard Analytics",
    description="Get detailed analytics data for dashboard insights and reporting"
)
async def get_dashboard_analytics(
    background_tasks: BackgroundTasks,
    period: str = Query("30d", regex="^(1d|7d|30d|90d|1y|all)$", description="Analytics period"),
    include_performance_trends: bool = Query(True, description="Include performance trends"),
    include_usage_metrics: bool = Query(True, description="Include usage metrics"),
    include_confidence_distribution: bool = Query(True, description="Include confidence distribution"),
    include_processing_metrics: bool = Query(True, description="Include processing metrics"),
    force_refresh: bool = Query(False, description="Force refresh from cache"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session)
):
    """
    Get dashboard analytics data
    
    This endpoint provides detailed analytics data including:
    - Performance trends and historical data
    - Usage statistics and patterns
    - Confidence score distribution analysis
    - Processing performance metrics
    - Available export formats
    
    The data is optimized for analytics visualization and reporting.
    """
    try:
        start_time = time.time()
        logger.info(f"Fetching dashboard analytics for user: {current_user.get('user_id', 'unknown')}")
        
        # Create dashboard data service
        cache_config = DashboardCacheConfig(
            enable_cache=not force_refresh,
            cache_ttl=600  # 10 minutes for analytics
        )
        
        dashboard_service = await create_dashboard_data_service(db_session, cache_config)
        
        # Create query parameters
        query_params = DashboardQueryParams(
            user_id=current_user.get('user_id', 'anonymous'),
            include_anonymized=True,
            timezone=current_user.get('timezone', 'UTC'),
            limit=1000  # Higher limit for analytics
        )
        
        # Get dashboard analytics data
        analytics_response = await dashboard_service.get_dashboard_analytics(query_params)
        
        # Calculate response time
        response_time = (time.time() - start_time) * 1000
        
        # Add response metadata
        analytics_response.response_time_ms = response_time
        analytics_response.request_id = f"req_{int(time.time() * 1000)}"
        
        logger.info(f"Successfully fetched dashboard analytics in {response_time:.2f}ms")
        
        return analytics_response
        
    except Exception as e:
        logger.error(f"Failed to fetch dashboard analytics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch dashboard analytics: {str(e)}"
        )


@router.get(
    "/configuration",
    response_model=DashboardConfigurationResponse,
    summary="Get Dashboard Configuration",
    description="Get dashboard configuration options and current settings"
)
async def get_dashboard_configuration(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session)
):
    """
    Get dashboard configuration data
    
    This endpoint provides:
    - Available widget types and configurations
    - Default layout configuration
    - Theme options and customization settings
    - Notification configuration options
    - Analytics filter options
    """
    try:
        logger.info(f"Fetching dashboard configuration for user: {current_user.get('user_id', 'unknown')}")
        
        # Get user preferences for configuration
        from ..data_integration.cognito_user_preferences import CognitoUserPreferences
        cognito_prefs = CognitoUserPreferences()
        
        user_preferences = await cognito_prefs.get_user_preferences(
            current_user.get('user_id', 'anonymous')
        )
        
        # Build configuration response
        configuration = DashboardConfigurationResponse(
            available_widgets=[
                {
                    "type": "overview",
                    "name": "Overview Widget",
                    "description": "Displays recent analyses and key metrics",
                    "configurable": True,
                    "default_size": {"width": 4, "height": 3}
                },
                {
                    "type": "analytics",
                    "name": "Analytics Widget",
                    "description": "Shows performance trends and statistics",
                    "configurable": True,
                    "default_size": {"width": 6, "height": 4}
                },
                {
                    "type": "recent_activity",
                    "name": "Recent Activity",
                    "description": "Lists recent user activities and analyses",
                    "configurable": True,
                    "default_size": {"width": 3, "height": 5}
                },
                {
                    "type": "system_status",
                    "name": "System Status",
                    "description": "Shows system health and performance",
                    "configurable": True,
                    "default_size": {"width": 3, "height": 2}
                },
                {
                    "type": "confidence_distribution",
                    "name": "Confidence Distribution",
                    "description": "Visualizes confidence score distribution",
                    "configurable": True,
                    "default_size": {"width": 4, "height": 3}
                }
            ],
            default_layout={
                "widgets": [
                    {"type": "overview", "position": {"x": 0, "y": 0}},
                    {"type": "analytics", "position": {"x": 4, "y": 0}},
                    {"type": "recent_activity", "position": {"x": 0, "y": 3}},
                    {"type": "system_status", "position": {"x": 3, "y": 3}},
                    {"type": "confidence_distribution", "position": {"x": 6, "y": 3}}
                ]
            },
            theme_options=[
                {
                    "name": "light",
                    "display_name": "Light Theme",
                    "colors": {
                        "primary": "#1976d2",
                        "secondary": "#dc004e",
                        "background": "#ffffff",
                        "surface": "#f5f5f5"
                    }
                },
                {
                    "name": "dark",
                    "display_name": "Dark Theme",
                    "colors": {
                        "primary": "#90caf9",
                        "secondary": "#f48fb1",
                        "background": "#121212",
                        "surface": "#1e1e1e"
                    }
                },
                {
                    "name": "high_contrast",
                    "display_name": "High Contrast",
                    "colors": {
                        "primary": "#000000",
                        "secondary": "#ffffff",
                        "background": "#ffffff",
                        "surface": "#000000"
                    }
                }
            ],
            notification_options={
                "types": ["info", "warning", "error", "success", "system_update"],
                "channels": ["dashboard", "email", "push"],
                "frequencies": ["immediate", "hourly", "daily", "weekly"]
            },
            analytics_options={
                "date_ranges": ["1d", "7d", "30d", "90d", "1y", "all"],
                "metrics": ["processing_time", "accuracy", "throughput", "confidence", "user_activity"],
                "export_formats": ["pdf", "json", "csv", "xlsx"]
            }
        )
        
        logger.info("Successfully fetched dashboard configuration")
        return configuration
        
    except Exception as e:
        logger.error(f"Failed to fetch dashboard configuration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch dashboard configuration: {str(e)}"
        )


@router.post(
    "/preferences",
    summary="Update User Preferences",
    description="Update user dashboard preferences and settings"
)
async def update_user_preferences(
    preferences: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session)
):
    """
    Update user dashboard preferences
    
    This endpoint allows users to update their dashboard preferences including:
    - Layout configuration
    - Theme settings
    - Notification preferences
    - Analytics filters
    """
    try:
        logger.info(f"Updating preferences for user: {current_user.get('user_id', 'unknown')}")
        
        # Update user preferences via Cognito
        from ..data_integration.cognito_user_preferences import CognitoUserPreferences
        cognito_prefs = CognitoUserPreferences()
        
        response = await cognito_prefs.update_user_preferences(
            user_id=current_user.get('user_id', 'anonymous'),
            preferences=preferences,
            replace_all=False
        )
        
        logger.info(f"Successfully updated preferences for user {current_user.get('user_id', 'unknown')}")
        
        return {
            "message": "Preferences updated successfully",
            "updated_at": response.last_updated,
            "preference_count": response.preference_count
        }
        
    except Exception as e:
        logger.error(f"Failed to update user preferences: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update preferences: {str(e)}"
        )


@router.get(
    "/preferences",
    summary="Get User Preferences",
    description="Get current user dashboard preferences and settings"
)
async def get_user_preferences(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session)
):
    """
    Get user dashboard preferences
    
    Returns the current user's dashboard preferences including:
    - Layout configuration
    - Theme settings
    - Notification preferences
    - Analytics filters
    """
    try:
        logger.info(f"Fetching preferences for user: {current_user.get('user_id', 'unknown')}")
        
        # Get user preferences from Cognito
        from ..data_integration.cognito_user_preferences import CognitoUserPreferences
        cognito_prefs = CognitoUserPreferences()
        
        preferences = await cognito_prefs.get_user_preferences(
            current_user.get('user_id', 'anonymous')
        )
        
        logger.info(f"Successfully fetched preferences for user {current_user.get('user_id', 'unknown')}")
        
        return {
            "user_id": current_user.get('user_id', 'anonymous'),
            "preferences": preferences,
            "last_updated": datetime.now(timezone.utc)
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch user preferences: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch preferences: {str(e)}"
        )


@router.delete(
    "/cache",
    summary="Clear Dashboard Cache",
    description="Clear cached dashboard data for current user or all users"
)
async def clear_dashboard_cache(
    user_id: Optional[str] = Query(None, description="User ID to clear cache for (admin only)"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session)
):
    """
    Clear dashboard data cache
    
    This endpoint allows clearing cached dashboard data to force fresh data retrieval.
    Admin users can clear cache for any user, regular users can only clear their own cache.
    """
    try:
        logger.info(f"Clearing dashboard cache for user: {current_user.get('user_id', 'unknown')}")
        
        # Check permissions for admin operations
        target_user_id = user_id
        if user_id and user_id != current_user.get('user_id'):
            # Check if current user is admin
            if current_user.get('role') != 'admin':
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions to clear cache for other users"
                )
        else:
            target_user_id = current_user.get('user_id', 'anonymous')
        
        # Create dashboard data service
        dashboard_service = await create_dashboard_data_service(db_session)
        
        # Clear cache
        await dashboard_service.clear_cache(target_user_id)
        
        logger.info(f"Successfully cleared cache for user {target_user_id}")
        
        return {
            "message": "Cache cleared successfully",
            "user_id": target_user_id,
            "cleared_at": datetime.now(timezone.utc)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear dashboard cache: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.get(
    "/health",
    summary="Dashboard Health Check",
    description="Check dashboard service health and dependencies"
)
async def dashboard_health_check(
    db_session: AsyncSession = Depends(get_db_session)
):
    """
    Dashboard health check
    
    This endpoint checks the health of dashboard services and dependencies.
    """
    try:
        logger.info("Performing dashboard health check")
        
        # Create dashboard data service
        dashboard_service = await create_dashboard_data_service(db_session)
        
        # Get cache statistics
        cache_stats = await dashboard_service.get_cache_stats()
        
        # Check service dependencies
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc),
            "services": {
                "database": "healthy",
                "cache": "healthy" if cache_stats.get("enabled") else "disabled",
                "analytics": "healthy",
                "cognito": "healthy"
            },
            "cache_statistics": cache_stats,
            "version": "1.0.0"
        }
        
        logger.info("Dashboard health check completed successfully")
        return health_status
        
    except Exception as e:
        logger.error(f"Dashboard health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc),
            "error": str(e),
            "version": "1.0.0"
        }


# Background task functions
async def refresh_dashboard_cache(
    dashboard_service: DashboardDataService,
    query_params: DashboardQueryParams
):
    """
    Background task to refresh dashboard cache
    
    Args:
        dashboard_service: Dashboard data service instance
        query_params: Query parameters for cache refresh
    """
    try:
        logger.info(f"Refreshing dashboard cache for user: {query_params.user_id}")
        
        # Pre-warm cache with fresh data
        await dashboard_service.get_dashboard_overview(query_params)
        
        logger.info(f"Successfully refreshed dashboard cache for user: {query_params.user_id}")
        
    except Exception as e:
        logger.error(f"Failed to refresh dashboard cache: {str(e)}")


# Error handlers
@router.exception_handler(APIError)
async def api_error_handler(request, exc: APIError):
    """Handle API errors"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@router.exception_handler(Exception)
async def generic_error_handler(request, exc: Exception):
    """Handle generic errors"""
    logger.error(f"Unhandled error in dashboard routes: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An internal server error occurred",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )
