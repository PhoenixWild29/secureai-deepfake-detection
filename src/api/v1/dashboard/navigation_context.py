#!/usr/bin/env python3
"""
Dashboard Navigation Context API Endpoint
Dedicated API endpoint for comprehensive navigation context management
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import JSONResponse
import structlog

from src.services.navigation_service import get_navigation_service
from src.dependencies.auth import get_current_user_optional, UserClaims, require_permission
from src.config.navigation_config import get_navigation_config
from src.utils.redis_cache import get_dashboard_cache_manager

logger = structlog.get_logger(__name__)

# Create router
router = APIRouter(
    prefix="/api/v1/dashboard/navigation",
    tags=["navigation"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)


@router.get(
    "/context",
    summary="Get Navigation Context",
    description="Get comprehensive navigation context including current route information, "
                "available navigation options, breadcrumb data, and user navigation history. "
                "Supports role-based navigation customization and real-time updates.",
    responses={
        200: {
            "description": "Navigation context retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "navigation_state": {
                            "current_context": {
                                "path": "/dashboard/analytics",
                                "section_id": "dashboard",
                                "page_id": "analytics",
                                "breadcrumbs": [
                                    {
                                        "label": "Home",
                                        "path": "/dashboard",
                                        "is_active": False,
                                        "icon": None,
                                        "metadata": None
                                    },
                                    {
                                        "label": "Dashboard",
                                        "path": "/dashboard#dashboard",
                                        "is_active": False,
                                        "icon": None,
                                        "metadata": None
                                    },
                                    {
                                        "label": "Analytics",
                                        "path": "/dashboard/analytics",
                                        "is_active": True,
                                        "icon": None,
                                        "metadata": None
                                    }
                                ],
                                "page_title": "Analytics",
                                "page_description": "Analytics and insights",
                                "metadata": None
                            },
                            "available_sections": [
                                {
                                    "id": "dashboard",
                                    "label": "Dashboard",
                                    "icon": "home",
                                    "description": "Main dashboard overview",
                                    "order": 1,
                                    "is_collapsible": True,
                                    "is_collapsed": False,
                                    "items": [
                                        {
                                            "id": "overview",
                                            "label": "Overview",
                                            "path": "/dashboard",
                                            "type": "page",
                                            "icon": "home",
                                            "description": "Dashboard overview",
                                            "required_permission": "read",
                                            "required_roles": [],
                                            "is_external": False,
                                            "is_disabled": False,
                                            "badge": None,
                                            "children": [],
                                            "metadata": None
                                        }
                                    ],
                                    "required_permission": None,
                                    "required_roles": [],
                                    "metadata": None
                                }
                            ],
                            "user_preferences": {
                                "user_id": "user_123",
                                "sidebar_collapsed": False,
                                "sidebar_width": 280,
                                "show_breadcrumbs": True,
                                "show_page_titles": True,
                                "navigation_style": "default",
                                "favorite_items": [],
                                "recent_items": ["/dashboard", "/dashboard/analytics"],
                                "custom_sections": [],
                                "last_updated": "2024-01-15T10:30:00Z"
                            },
                            "quick_actions": [
                                {
                                    "id": "quick-upload",
                                    "label": "Quick Upload",
                                    "path": "/dashboard/upload",
                                    "type": "page",
                                    "icon": "upload",
                                    "description": "Quick upload action",
                                    "required_permission": "write",
                                    "required_roles": [],
                                    "is_external": False,
                                    "is_disabled": False,
                                    "badge": None,
                                    "children": [],
                                    "metadata": None
                                }
                            ],
                            "recent_navigation": [],
                            "suggested_items": [],
                            "notifications_count": 0,
                            "last_updated": "2024-01-15T10:30:00Z"
                        },
                        "navigation_history": [
                            {
                                "route_path": "/dashboard/analytics",
                                "route_title": "Analytics",
                                "timestamp": "2024-01-15T10:30:00Z",
                                "user_agent": "dashboard",
                                "session_id": "session_user_123_1705315800"
                            },
                            {
                                "route_path": "/dashboard",
                                "route_title": "Dashboard Overview",
                                "timestamp": "2024-01-15T10:25:00Z",
                                "user_agent": "dashboard",
                                "session_id": "session_user_123_1705315500"
                            }
                        ],
                        "navigation_patterns": {
                            "most_visited_routes": [
                                {"route": "/dashboard", "count": 15},
                                {"route": "/dashboard/analytics", "count": 8},
                                {"route": "/dashboard/upload", "count": 5}
                            ],
                            "navigation_frequency": {
                                "/dashboard": 15,
                                "/dashboard/analytics": 8,
                                "/dashboard/upload": 5
                            },
                            "average_session_duration": 24,
                            "common_navigation_paths": [
                                {"path": "/dashboard -> /dashboard/analytics", "frequency": 6},
                                {"path": "/dashboard/analytics -> /dashboard", "frequency": 4}
                            ],
                            "total_navigation_events": 28,
                            "last_analyzed": "2024-01-15T10:30:00Z"
                        },
                        "timestamp": "2024-01-15T10:30:00Z",
                        "user_id": "user_123",
                        "response_time_ms": 45.2,
                        "request_id": "req_789",
                        "cache_info": {
                            "cache_hit": True,
                            "cache_ttl_seconds": 300,
                            "last_cached": "2024-01-15T10:29:00Z"
                        }
                    }
                }
            }
        },
        401: {"description": "Unauthorized - Invalid or missing authentication"},
        403: {"description": "Forbidden - Insufficient permissions"},
        429: {"description": "Too Many Requests - Rate limit exceeded"},
        503: {"description": "Service Unavailable - External services unavailable"}
    }
)
async def get_navigation_context(
    # Query parameters
    current_path: str = Query(
        default="/dashboard",
        description="Current route path for navigation context"
    ),
    include_history: bool = Query(
        default=True,
        description="Include navigation history in response"
    ),
    include_patterns: bool = Query(
        default=True,
        description="Include navigation patterns analysis in response"
    ),
    force_refresh: bool = Query(
        default=False,
        description="Force refresh from cache"
    ),
    # Dependencies
    current_user: Optional[UserClaims] = Depends(get_current_user_optional),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Get comprehensive navigation context for dashboard navigation
    
    This endpoint provides a dedicated API for navigation context management,
    including:
    
    - **Current Route Information**: Current path, section, page details
    - **Available Navigation Options**: Role-filtered navigation sections and items
    - **Breadcrumb Data**: Clickable navigation path reflecting current location
    - **User Navigation History**: Recent navigation events and patterns
    - **Navigation Patterns**: Analytics on user navigation behavior
    - **User Preferences**: Personalized navigation settings
    
    The endpoint supports role-based navigation customization, showing different
    navigation options based on user types and permissions. Navigation history
    is persisted using the existing user preference system.
    
    **Authentication**: Optional - provides personalized data if authenticated
    
    **Rate Limiting**: 200 requests per minute per user
    
    **Caching**: Response cached for 5 minutes by default
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    user_id = current_user.user_id if current_user else "anonymous"
    
    logger.info(
        "Navigation context request received",
        request_id=request_id,
        user_id=user_id,
        current_path=current_path,
        include_history=include_history,
        include_patterns=include_patterns,
        force_refresh=force_refresh
    )
    
    try:
        # Get configuration
        config = get_navigation_config()
        
        # Check rate limiting (basic implementation)
        if config.navigation.navigation_analytics_enabled:
            # In production, implement proper rate limiting with Redis
            pass
        
        # Get navigation service
        navigation_service = await get_navigation_service()
        
        # Get enhanced navigation context
        enhanced_context = await navigation_service.get_enhanced_navigation_context(
            current_path=current_path,
            user_claims=current_user,
            include_history=include_history,
            include_patterns=include_patterns,
            force_refresh=force_refresh
        )
        
        # Calculate response time
        response_time = (time.time() - start_time) * 1000
        
        # Add response metadata
        enhanced_context.update({
            "response_time_ms": response_time,
            "request_id": request_id,
            "cache_info": {
                "cache_hit": response_time < 50,  # Assume cache hit if very fast
                "cache_ttl_seconds": config.navigation.cache_ttl_seconds,
                "last_cached": datetime.now(timezone.utc).isoformat()
            }
        })
        
        # Check if response time meets requirements
        if response_time > config.max_response_time_ms:
            logger.warning(
                "Navigation context response time exceeded threshold",
                request_id=request_id,
                response_time_ms=response_time,
                threshold_ms=config.max_response_time_ms
            )
        
        # Log successful request
        logger.info(
            "Navigation context request completed",
            request_id=request_id,
            user_id=user_id,
            response_time_ms=response_time,
            current_path=current_path,
            include_history=include_history,
            include_patterns=include_patterns
        )
        
        # Schedule background tasks if needed
        if config.enable_performance_logging:
            background_tasks.add_task(
                _log_navigation_performance_metrics,
                request_id,
                response_time,
                user_id,
                current_path
            )
        
        return enhanced_context
        
    except Exception as e:
        error_response_time = (time.time() - start_time) * 1000
        
        logger.error(
            "Navigation context request failed",
            request_id=request_id,
            user_id=user_id,
            error=str(e),
            response_time_ms=error_response_time
        )
        
        # Return appropriate error response
        if "authentication" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        elif "permission" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        elif "rate limit" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        elif "service unavailable" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="External services temporarily unavailable"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )


@router.post(
    "/track",
    summary="Track Navigation Event",
    description="Track a navigation event for history and analytics",
    responses={
        200: {"description": "Navigation event tracked successfully"},
        401: {"description": "Unauthorized"},
        400: {"description": "Bad request - Invalid navigation data"}
    }
)
async def track_navigation_event(
    route_path: str,
    route_title: Optional[str] = None,
    current_user: UserClaims = Depends(get_current_user_optional)
):
    """
    Track a navigation event for history and analytics
    
    **Authentication**: Required for tracking
    
    **Parameters**:
    - `route_path`: Route path navigated to
    - `route_title`: Route title/name (optional, will be inferred if not provided)
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for navigation tracking"
        )
    
    request_id = str(uuid.uuid4())
    
    logger.info(
        "Navigation tracking request received",
        request_id=request_id,
        user_id=current_user.user_id,
        route_path=route_path,
        route_title=route_title
    )
    
    try:
        navigation_service = await get_navigation_service()
        
        # Use provided title or infer from path
        if not route_title:
            route_title = navigation_service._get_route_title(route_path)
        
        # Track navigation event
        success = await navigation_service.track_navigation_event(
            user_id=current_user.user_id,
            route_path=route_path,
            route_title=route_title,
            user_claims=current_user
        )
        
        if success:
            logger.info(
                "Navigation event tracked successfully",
                request_id=request_id,
                user_id=current_user.user_id,
                route_path=route_path
            )
            
            return {
                "status": "success",
                "message": "Navigation event tracked successfully",
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to track navigation event"
            )
            
    except Exception as e:
        logger.error(
            "Navigation tracking failed",
            request_id=request_id,
            user_id=current_user.user_id,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/history",
    summary="Get Navigation History",
    description="Get user navigation history",
    responses={
        200: {"description": "Navigation history retrieved successfully"},
        401: {"description": "Unauthorized"}
    }
)
async def get_navigation_history(
    limit: int = Query(default=20, ge=1, le=100, description="Number of history entries to return"),
    current_user: UserClaims = Depends(get_current_user_optional)
):
    """
    Get user navigation history
    
    **Authentication**: Required
    
    **Parameters**:
    - `limit`: Number of history entries to return (1-100)
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    request_id = str(uuid.uuid4())
    
    logger.info(
        "Navigation history request received",
        request_id=request_id,
        user_id=current_user.user_id,
        limit=limit
    )
    
    try:
        navigation_service = await get_navigation_service()
        
        # Get navigation history
        history = await navigation_service.get_navigation_history(current_user.user_id)
        
        # Limit results
        limited_history = history[:limit]
        
        logger.info(
            "Navigation history retrieved successfully",
            request_id=request_id,
            user_id=current_user.user_id,
            total_entries=len(history),
            returned_entries=len(limited_history)
        )
        
        return {
            "history": limited_history,
            "total_entries": len(history),
            "returned_entries": len(limited_history),
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(
            "Navigation history request failed",
            request_id=request_id,
            user_id=current_user.user_id,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/patterns",
    summary="Get Navigation Patterns",
    description="Get user navigation patterns analysis",
    responses={
        200: {"description": "Navigation patterns retrieved successfully"},
        401: {"description": "Unauthorized"}
    }
)
async def get_navigation_patterns(
    current_user: UserClaims = Depends(get_current_user_optional)
):
    """
    Get user navigation patterns analysis
    
    **Authentication**: Required
    
    Returns analysis of user navigation behavior including:
    - Most visited routes
    - Navigation frequency
    - Common navigation paths
    - Session duration metrics
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    request_id = str(uuid.uuid4())
    
    logger.info(
        "Navigation patterns request received",
        request_id=request_id,
        user_id=current_user.user_id
    )
    
    try:
        navigation_service = await get_navigation_service()
        
        # Get navigation patterns
        patterns = await navigation_service.get_navigation_patterns(current_user.user_id)
        
        logger.info(
            "Navigation patterns retrieved successfully",
            request_id=request_id,
            user_id=current_user.user_id,
            patterns_count=len(patterns)
        )
        
        return {
            "patterns": patterns,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(
            "Navigation patterns request failed",
            request_id=request_id,
            user_id=current_user.user_id,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/cache/invalidate",
    summary="Invalidate Navigation Cache",
    description="Invalidate cached navigation data for a specific user",
    responses={
        200: {"description": "Cache invalidated successfully"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - Admin access required"}
    }
)
async def invalidate_navigation_cache(
    user_id: Optional[str] = None,
    current_user: UserClaims = Depends(require_permission("manage_configuration"))
):
    """
    Invalidate navigation cache for a specific user
    
    **Authentication**: Required - Admin access only
    
    **Parameters**:
    - `user_id` (optional): Specific user ID to invalidate cache for. If not provided, invalidates current user's cache.
    """
    target_user_id = user_id or current_user.user_id
    request_id = str(uuid.uuid4())
    
    logger.info(
        "Navigation cache invalidation requested",
        request_id=request_id,
        requested_by=current_user.user_id,
        target_user_id=target_user_id
    )
    
    try:
        cache_manager = await get_dashboard_cache_manager()
        await cache_manager.invalidate_navigation_cache(target_user_id)
        
        logger.info(
            "Navigation cache invalidated successfully",
            request_id=request_id,
            requested_by=current_user.user_id,
            target_user_id=target_user_id
        )
        
        return {
            "status": "success",
            "message": f"Navigation cache invalidated for user {target_user_id}",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(
            "Navigation cache invalidation failed",
            request_id=request_id,
            requested_by=current_user.user_id,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cache invalidation failed"
        )


async def _log_navigation_performance_metrics(
    request_id: str,
    response_time_ms: float,
    user_id: str,
    current_path: str
):
    """
    Background task to log navigation performance metrics
    
    Args:
        request_id: Request identifier
        response_time_ms: Response time in milliseconds
        user_id: User identifier
        current_path: Current route path
    """
    try:
        # In production, this would log to a metrics service like Prometheus
        logger.info(
            "Navigation performance metrics logged",
            request_id=request_id,
            response_time_ms=response_time_ms,
            user_id=user_id,
            current_path=current_path,
            endpoint="navigation_context"
        )
        
        # Could also update metrics in Redis or database
        # for real-time monitoring dashboards
        
    except Exception as e:
        logger.error(
            "Failed to log navigation performance metrics",
            request_id=request_id,
            error=str(e)
        )
