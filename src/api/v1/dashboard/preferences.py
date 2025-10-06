#!/usr/bin/env python3
"""
User Preferences API Endpoint
FastAPI endpoint for dashboard user preferences management with role-based access control
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.models.user_preferences import (
    CreatePreferencesRequest,
    UpdatePreferencesRequest,
    PreferencesResponse,
    PreferencesSummaryResponse,
    DefaultPreferencesResponse,
    PreferencesValidationResponse,
    UserRole
)
from src.services.preference_service import get_preference_service
from src.config.preferences_config import (
    get_preferences_config,
    get_preferences_endpoints,
    get_preferences_roles,
    is_capability_allowed
)
from src.dependencies.auth import UserClaims
from src.database.config import get_db_session

logger = structlog.get_logger(__name__)

# Create router
router = APIRouter(
    prefix="/preferences",
    tags=["preferences"],
    responses={
        404: {"description": "Not found"},
        403: {"description": "Forbidden"},
        400: {"description": "Bad request"},
        500: {"description": "Internal server error"}
    }
)

# Get configuration
config = get_preferences_config()
endpoints = get_preferences_endpoints()


@router.post(
    "",
    response_model=PreferencesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create User Preferences",
    description="Create new user dashboard preferences with role-based customization"
)
async def create_user_preferences(
    request: CreatePreferencesRequest,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_db_session),
    user_claims: UserClaims = Depends(require_preferences_access)
):
    """
    Create new user dashboard preferences
    
    This endpoint allows authenticated users to create personalized dashboard preferences including:
    - Widget configuration and layout
    - Theme selection and customization
    - Notification settings
    - Accessibility options
    - Role-based customization options
    
    The preferences are validated for data integrity and user authorization before storage.
    """
    try:
        logger.info(
            "Creating user preferences",
            user_id=user_claims.user_id,
            role=request.role
        )
        
        # Check configuration
        if not config.preferences_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User preferences functionality is currently disabled"
            )
        
        # Check user capabilities
        if not is_capability_allowed(user_claims.roles[0] if user_claims.roles else "viewer", "widget_customization"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create preferences"
            )
        
        # Get preference service
        preference_service = await get_preference_service()
        
        # Create preferences
        preferences_response = await preference_service.create_user_preferences(
            db_session, user_claims, request
        )
        
        # Add background task for audit logging if enabled
        if config.audit_logging_enabled:
            background_tasks.add_task(
                log_preferences_action,
                user_claims.user_id,
                "create",
                preferences_response.dict()
            )
        
        logger.info(
            "User preferences created successfully",
            user_id=user_claims.user_id,
            preferences_id=preferences_response.user_id
        )
        
        return preferences_response
        
    except ValueError as e:
        logger.warning(
            "Invalid preferences data",
            user_id=user_claims.user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(
            "Failed to create user preferences",
            user_id=user_claims.user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create preferences"
        )


@router.get(
    "",
    response_model=PreferencesResponse,
    summary="Get User Preferences",
    description="Retrieve current user dashboard preferences with authentication validation"
)
async def get_user_preferences(
    include_inactive: bool = Query(default=False, description="Include inactive preferences"),
    db_session: AsyncSession = Depends(get_db_session),
    user_claims: UserClaims = Depends(require_preferences_access)
):
    """
    Get current user dashboard preferences
    
    This endpoint retrieves the user's current dashboard preferences including:
    - Widget configurations and positions
    - Theme and layout settings
    - Notification preferences
    - Accessibility options
    - Custom settings
    
    If no preferences exist, returns a 404 status.
    """
    try:
        logger.info(
            "Retrieving user preferences",
            user_id=user_claims.user_id,
            include_inactive=include_inactive
        )
        
        # Check configuration
        if not config.preferences_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User preferences functionality is currently disabled"
            )
        
        # Get preference service
        preference_service = await get_preference_service()
        
        # Retrieve preferences
        preferences_response = await preference_service.get_user_preferences(
            db_session, user_claims, include_inactive
        )
        
        if not preferences_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No preferences found for user"
            )
        
        logger.info(
            "User preferences retrieved successfully",
            user_id=user_claims.user_id,
            has_preferences=True
        )
        
        return preferences_response
        
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(
            "Failed to retrieve user preferences",
            user_id=user_claims.user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve preferences"
        )


@router.put(
    "",
    response_model=PreferencesResponse,
    summary="Update User Preferences",
    description="Update existing user dashboard preferences with validation and authorization"
)
async def update_user_preferences(
    request: UpdatePreferencesRequest,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_db_session),
    user_claims: UserClaims = Depends(require_preferences_access)
):
    """
    Update existing user dashboard preferences
    
    This endpoint allows users to update their dashboard preferences with:
    - Partial updates (only specified fields are updated)
    - Data validation and integrity checks
    - Role-based authorization
    - Audit trail logging
    
    Supports both complete preference updates and partial field updates.
    """
    try:
        logger.info(
            "Updating user preferences",
            user_id=user_claims.user_id,
            has_preferences_update=request.preferences is not None,
            has_custom_settings_update=request.custom_settings is not None
        )
        
        # Check configuration
        if not config.preferences_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User preferences functionality is currently disabled"
            )
        
        # Check user capabilities
        if not is_capability_allowed(user_claims.roles[0] if user_claims.roles else "viewer", "widget_customization"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to update preferences"
            )
        
        # Get preference service
        preference_service = await get_preference_service()
        
        # Update preferences
        preferences_response = await preference_service.update_user_preferences(
            db_session, user_claims, request
        )
        
        # Add background task for audit logging if enabled
        if config.audit_logging_enabled:
            background_tasks.add_task(
                log_preferences_action,
                user_claims.user_id,
                "update",
                preferences_response.dict()
            )
        
        logger.info(
            "User preferences updated successfully",
            user_id=user_claims.user_id
        )
        
        return preferences_response
        
    except ValueError as e:
        logger.warning(
            "Invalid preferences update data",
            user_id=user_claims.user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(
            "Failed to update user preferences",
            user_id=user_claims.user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete User Preferences",
    description="Delete user dashboard preferences (soft delete with audit trail)"
)
async def delete_user_preferences(
    reason: Optional[str] = Query(default=None, description="Reason for deletion"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db_session: AsyncSession = Depends(get_db_session),
    user_claims: UserClaims = Depends(require_preferences_access)
):
    """
    Delete user dashboard preferences
    
    This endpoint performs a soft delete of user preferences:
    - Sets is_active flag to False
    - Preserves data for audit and recovery purposes
    - Logs deletion action with reason
    - Maintains referential integrity
    
    Preferences can be restored from history if needed.
    """
    try:
        logger.info(
            "Deleting user preferences",
            user_id=user_claims.user_id,
            reason=reason
        )
        
        # Check configuration
        if not config.preferences_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User preferences functionality is currently disabled"
            )
        
        # Get preference service
        preference_service = await get_preference_service()
        
        # Delete preferences
        success = await preference_service.delete_user_preferences(
            db_session, user_claims, reason
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No preferences found to delete"
            )
        
        # Add background task for audit logging if enabled
        if config.audit_logging_enabled:
            background_tasks.add_task(
                log_preferences_action,
                user_claims.user_id,
                "delete",
                {"reason": reason}
            )
        
        logger.info(
            "User preferences deleted successfully",
            user_id=user_claims.user_id
        )
        
        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content=None
        )
        
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(
            "Failed to delete user preferences",
            user_id=user_claims.user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete preferences"
        )


@router.get(
    "/defaults",
    response_model=DefaultPreferencesResponse,
    summary="Get Default Preferences",
    description="Get default dashboard preferences for user's role"
)
async def get_default_preferences(
    user_claims: UserClaims = Depends(require_preferences_access)
):
    """
    Get default preferences for user's role
    
    This endpoint returns role-based default preferences including:
    - Widget configurations appropriate for the role
    - Theme and layout settings
    - Notification preferences
    - Role-specific customization options
    
    Useful for new users or preference reset functionality.
    """
    try:
        logger.info(
            "Getting default preferences",
            user_id=user_claims.user_id,
            roles=user_claims.roles
        )
        
        # Check configuration
        if not config.preferences_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User preferences functionality is currently disabled"
            )
        
        # Get preference service
        preference_service = await get_preference_service()
        
        # Get default preferences
        default_response = await preference_service.get_default_preferences(user_claims)
        
        logger.info(
            "Default preferences retrieved successfully",
            user_id=user_claims.user_id,
            role=default_response.role
        )
        
        return default_response
        
    except Exception as e:
        logger.error(
            "Failed to get default preferences",
            user_id=user_claims.user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get default preferences"
        )


@router.post(
    "/validate",
    response_model=PreferencesValidationResponse,
    summary="Validate Preferences",
    description="Validate user preferences data without saving"
)
async def validate_preferences(
    preferences_data: Dict[str, Any],
    user_claims: UserClaims = Depends(require_preferences_access)
):
    """
    Validate user preferences data
    
    This endpoint validates preferences data without saving:
    - Checks data structure and format
    - Validates widget configurations
    - Verifies theme and layout settings
    - Provides detailed error messages and suggestions
    
    Useful for client-side validation before saving preferences.
    """
    try:
        logger.info(
            "Validating preferences data",
            user_id=user_claims.user_id
        )
        
        # Check configuration
        if not config.preferences_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User preferences functionality is currently disabled"
            )
        
        # Import here to avoid circular imports
        from src.models.user_preferences import DashboardPreferences
        
        # Parse preferences data
        try:
            preferences = DashboardPreferences(**preferences_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid preferences data format: {str(e)}"
            )
        
        # Get preference service
        preference_service = await get_preference_service()
        
        # Validate preferences
        validation_response = await preference_service.validate_user_preferences(preferences)
        
        logger.info(
            "Preferences validation completed",
            user_id=user_claims.user_id,
            is_valid=validation_response.is_valid,
            error_count=len(validation_response.errors)
        )
        
        return validation_response
        
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(
            "Failed to validate preferences",
            user_id=user_claims.user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate preferences"
        )


@router.get(
    "/summary",
    response_model=PreferencesSummaryResponse,
    summary="Get Preferences Summary",
    description="Get summary information about user preferences"
)
async def get_preferences_summary(
    db_session: AsyncSession = Depends(get_db_session),
    user_claims: UserClaims = Depends(require_preferences_access)
):
    """
    Get user preferences summary
    
    This endpoint returns a summary of user preferences including:
    - Whether preferences exist
    - User role and theme type
    - Widget count and last update time
    - Quick overview without full preference data
    
    Useful for dashboard overview and preference status checks.
    """
    try:
        logger.info(
            "Getting preferences summary",
            user_id=user_claims.user_id
        )
        
        # Check configuration
        if not config.preferences_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User preferences functionality is currently disabled"
            )
        
        # Get preference service
        preference_service = await get_preference_service()
        
        # Get summary
        summary_response = await preference_service.get_preferences_summary(
            db_session, user_claims
        )
        
        logger.info(
            "Preferences summary retrieved successfully",
            user_id=user_claims.user_id,
            has_preferences=summary_response.has_preferences
        )
        
        return summary_response
        
    except Exception as e:
        logger.error(
            "Failed to get preferences summary",
            user_id=user_claims.user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get preferences summary"
        )


@router.get(
    "/history",
    summary="Get Preferences History",
    description="Get user preferences change history with pagination"
)
async def get_preferences_history(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of records"),
    offset: int = Query(default=0, ge=0, description="Number of records to skip"),
    db_session: AsyncSession = Depends(get_db_session),
    user_claims: UserClaims = Depends(require_preferences_access)
):
    """
    Get user preferences change history
    
    This endpoint returns the history of preferences changes including:
    - Change timestamps and actions
    - User who made the changes
    - Change reasons and version information
    - Widget and theme information for each change
    
    Supports pagination for large history datasets.
    """
    try:
        logger.info(
            "Getting preferences history",
            user_id=user_claims.user_id,
            limit=limit,
            offset=offset
        )
        
        # Check configuration
        if not config.preferences_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User preferences functionality is currently disabled"
            )
        
        # Check feature flag
        if not config.feature_preferences_history:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Preferences history feature is disabled"
            )
        
        # Get preference service
        preference_service = await get_preference_service()
        
        # Get history
        history_records = await preference_service.get_preferences_history(
            db_session, user_claims, limit, offset
        )
        
        logger.info(
            "Preferences history retrieved successfully",
            user_id=user_claims.user_id,
            record_count=len(history_records)
        )
        
        return {
            "user_id": user_claims.user_id,
            "history": history_records,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(history_records),
                "has_more": len(history_records) == limit
            }
        }
        
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(
            "Failed to get preferences history",
            user_id=user_claims.user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get preferences history"
        )


@router.post(
    "/restore/{history_id}",
    response_model=PreferencesResponse,
    summary="Restore Preferences",
    description="Restore preferences from history record"
)
async def restore_preferences_from_history(
    history_id: uuid.UUID,
    reason: Optional[str] = Query(default=None, description="Reason for restoration"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db_session: AsyncSession = Depends(get_db_session),
    user_claims: UserClaims = Depends(require_preferences_access)
):
    """
    Restore preferences from history record
    
    This endpoint allows users to restore their preferences from a previous state:
    - Validates the history record exists and belongs to the user
    - Validates the restored preferences data
    - Creates a new audit record for the restoration
    - Supports rollback functionality
    
    Useful for recovering from accidental changes or reverting to preferred settings.
    """
    try:
        logger.info(
            "Restoring preferences from history",
            user_id=user_claims.user_id,
            history_id=history_id,
            reason=reason
        )
        
        # Check configuration
        if not config.preferences_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User preferences functionality is currently disabled"
            )
        
        # Check feature flag
        if not config.feature_preferences_history:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Preferences history feature is disabled"
            )
        
        # Check user capabilities
        if not is_capability_allowed(user_claims.roles[0] if user_claims.roles else "viewer", "widget_customization"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to restore preferences"
            )
        
        # Get preference service
        preference_service = await get_preference_service()
        
        # Restore preferences
        preferences_response = await preference_service.restore_preferences_from_history(
            db_session, user_claims, history_id, reason
        )
        
        # Add background task for audit logging if enabled
        if config.audit_logging_enabled:
            background_tasks.add_task(
                log_preferences_action,
                user_claims.user_id,
                "restore",
                {"history_id": str(history_id), "reason": reason}
            )
        
        logger.info(
            "Preferences restored successfully",
            user_id=user_claims.user_id,
            history_id=history_id
        )
        
        return preferences_response
        
    except ValueError as e:
        logger.warning(
            "Invalid restoration request",
            user_id=user_claims.user_id,
            history_id=history_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(
            "Failed to restore preferences",
            user_id=user_claims.user_id,
            history_id=history_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore preferences"
        )


# Additional utility endpoints
@router.get(
    "/capabilities",
    summary="Get User Capabilities",
    description="Get user capabilities for preferences management"
)
async def get_user_capabilities(
    user_claims: UserClaims = Depends(require_preferences_access)
):
    """Get user capabilities for preferences management"""
    try:
        roles_config = get_preferences_roles()
        user_role = user_claims.roles[0] if user_claims.roles else "viewer"
        
        capabilities = roles_config.ROLE_CAPABILITIES.get(user_role, [])
        
        return {
            "user_id": user_claims.user_id,
            "role": user_role,
            "capabilities": capabilities,
            "features_enabled": {
                "widget_customization": config.feature_widget_customization,
                "theme_selection": config.feature_theme_selection,
                "layout_customization": config.feature_layout_customization,
                "notification_settings": config.feature_notification_settings,
                "accessibility_options": config.feature_accessibility_options,
                "custom_settings": config.feature_custom_settings,
                "preferences_history": config.feature_preferences_history,
                "preferences_export": config.feature_preferences_export,
                "preferences_import": config.feature_preferences_import
            }
        }
        
    except Exception as e:
        logger.error("Failed to get user capabilities", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get capabilities"
        )


@router.get(
    "/health",
    summary="Preferences Health Check",
    description="Check the health status of the preferences service"
)
async def preferences_health_check():
    """Check preferences service health"""
    try:
        return {
            "service": "user_preferences",
            "status": "healthy" if config.preferences_enabled else "disabled",
            "version": config.preferences_version,
            "features": {
                "widget_customization": config.feature_widget_customization,
                "theme_selection": config.feature_theme_selection,
                "layout_customization": config.feature_layout_customization,
                "notification_settings": config.feature_notification_settings,
                "accessibility_options": config.feature_accessibility_options,
                "preferences_history": config.feature_preferences_history
            },
            "configuration": {
                "validation_enabled": config.validation_enabled,
                "audit_logging_enabled": config.audit_logging_enabled,
                "role_based_customization": config.role_based_customization,
                "cache_enabled": config.cache_enabled
            }
        }
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "service": "user_preferences",
            "status": "unhealthy",
            "error": str(e)
        }


# Authentication dependency
async def require_preferences_access(user_claims: UserClaims) -> UserClaims:
    """
    Dependency to require user preferences access
    
    This dependency ensures that only authenticated users can access preferences endpoints.
    Additional role-based checks are performed in individual endpoints as needed.
    """
    if not user_claims or not user_claims.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for preferences access"
        )
    
    return user_claims


# Background task functions
async def log_preferences_action(user_id: str, action: str, data: Dict[str, Any]):
    """Background task to log preferences actions for audit purposes"""
    try:
        logger.info(
            "Preferences action logged",
            user_id=user_id,
            action=action,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Here you would implement actual audit logging
        # For example, sending to an audit service or database
        
    except Exception as e:
        logger.error(
            "Failed to log preferences action",
            user_id=user_id,
            action=action,
            error=str(e)
        )
