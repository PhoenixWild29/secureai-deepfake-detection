#!/usr/bin/env python3
"""
API Schemas Package
Pydantic models for API request/response validation
"""

from .dashboard_models import (
    DashboardOverviewResponse,
    DashboardAnalyticsResponse,
    UserPreferencesRequest,
    DashboardConfigurationResponse,
    DashboardWidgetType,
    NotificationType,
    ThemeType
)

from .navigation_models import (
    NavigationContextResponse,
    NavigationRoute,
    BreadcrumbItem,
    NavigationUpdateRequest,
    NavigationHistoryEntry,
    NavigationPreferences,
    NavigationState,
    NavigationStyleEnum,
    PermissionLevelEnum
)

__all__ = [
    # Dashboard models
    "DashboardOverviewResponse",
    "DashboardAnalyticsResponse",
    "UserPreferencesRequest",
    "DashboardConfigurationResponse",
    "DashboardWidgetType",
    "NotificationType",
    "ThemeType",
    
    # Navigation models
    "NavigationContextResponse",
    "NavigationRoute",
    "BreadcrumbItem",
    "NavigationUpdateRequest",
    "NavigationHistoryEntry",
    "NavigationPreferences",
    "NavigationState",
    "NavigationStyleEnum",
    "PermissionLevelEnum"
]
