#!/usr/bin/env python3
"""
Core Models Package
SQLModel classes for the SecureAI DeepFake Detection system
"""

# Import core detection models
from .models import (
    AnalysisStatusEnum,
    Video,
    Analysis,
    DetectionResult,
    FrameAnalysis
)

# Import dashboard navigation models
from .dashboard_models import (
    NavigationStyleEnum,
    MobileNavigationStyleEnum,
    ActivityTypeEnum,
    NavigationMethodEnum,
    User,
    DashboardSession,
    UserPreference,
    UserActivity,
    NavigationHistoryEntry,
    BreadcrumbPreferences,
    LastVisitedSection,
    NavigationData,
    SessionContext
)

__all__ = [
    # Core detection models
    "AnalysisStatusEnum",
    "Video",
    "Analysis", 
    "DetectionResult",
    "FrameAnalysis",
    
    # Dashboard navigation models
    "NavigationStyleEnum",
    "MobileNavigationStyleEnum",
    "ActivityTypeEnum",
    "NavigationMethodEnum",
    "User",
    "DashboardSession",
    "UserPreference",
    "UserActivity",
    "NavigationHistoryEntry",
    "BreadcrumbPreferences",
    "LastVisitedSection",
    "NavigationData",
    "SessionContext"
]