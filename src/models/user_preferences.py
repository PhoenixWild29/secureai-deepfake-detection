#!/usr/bin/env python3
"""
User Preferences Data Models
SQLModel schemas for dashboard user preferences management
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union
from uuid import uuid4, UUID
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, DateTime, JSON, Index, UniqueConstraint
from sqlalchemy.sql import func
from pydantic import BaseModel, Field as PydanticField, validator
from enum import Enum


class ThemeType(str, Enum):
    """Available theme types"""
    LIGHT = "light"
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"
    AUTO = "auto"


class NotificationFrequency(str, Enum):
    """Notification frequency options"""
    IMMEDIATE = "immediate"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    NEVER = "never"


class NotificationType(str, Enum):
    """Notification types"""
    EMAIL = "email"
    IN_APP = "in_app"
    PUSH = "push"
    SMS = "sms"


class WidgetType(str, Enum):
    """Available widget types"""
    ANALYTICS_CHART = "analytics_chart"
    DETECTION_SUMMARY = "detection_summary"
    SYSTEM_STATUS = "system_status"
    RECENT_ACTIVITY = "recent_activity"
    PERFORMANCE_METRICS = "performance_metrics"
    SECURITY_ALERTS = "security_alerts"
    COMPLIANCE_REPORTS = "compliance_reports"
    USER_ACTIVITY = "user_activity"
    BLOCKCHAIN_STATUS = "blockchain_status"
    EXPORT_HISTORY = "export_history"


class LayoutType(str, Enum):
    """Dashboard layout types"""
    GRID = "grid"
    LIST = "list"
    COMPACT = "compact"
    EXPANDED = "expanded"
    CUSTOM = "custom"


class UserRole(str, Enum):
    """User roles for role-based customization"""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    SECURITY_OFFICER = "security_officer"
    COMPLIANCE_MANAGER = "compliance_manager"
    SYSTEM_ADMIN = "system_admin"


class WidgetConfiguration(BaseModel):
    """Widget configuration model"""
    widget_id: str = PydanticField(..., description="Unique widget identifier")
    widget_type: WidgetType = PydanticField(..., description="Type of widget")
    position_x: int = PydanticField(default=0, ge=0, description="X position in grid")
    position_y: int = PydanticField(default=0, ge=0, description="Y position in grid")
    width: int = PydanticField(default=4, ge=1, le=12, description="Widget width (1-12 columns)")
    height: int = PydanticField(default=3, ge=1, le=8, description="Widget height (1-8 rows)")
    visible: bool = PydanticField(default=True, description="Widget visibility")
    refresh_interval: Optional[int] = PydanticField(default=None, ge=30, description="Auto-refresh interval in seconds")
    custom_settings: Dict[str, Any] = PydanticField(default_factory=dict, description="Widget-specific settings")
    
    @validator('widget_id')
    def validate_widget_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Widget ID cannot be empty")
        return v.strip()


class NotificationSettings(BaseModel):
    """Notification settings model"""
    enabled: bool = PydanticField(default=True, description="Enable notifications")
    types: List[NotificationType] = PydanticField(default_factory=lambda: [NotificationType.IN_APP], description="Notification types")
    frequency: NotificationFrequency = PydanticField(default=NotificationFrequency.IMMEDIATE, description="Notification frequency")
    email_address: Optional[str] = PydanticField(default=None, description="Email address for notifications")
    phone_number: Optional[str] = PydanticField(default=None, description="Phone number for SMS notifications")
    alert_types: List[str] = PydanticField(default_factory=list, description="Types of alerts to receive")
    quiet_hours: Optional[Dict[str, str]] = PydanticField(default=None, description="Quiet hours (start_time, end_time)")
    
    @validator('email_address')
    def validate_email(cls, v):
        if v is not None:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError("Invalid email format")
        return v


class ThemeSettings(BaseModel):
    """Theme settings model"""
    theme_type: ThemeType = PydanticField(default=ThemeType.LIGHT, description="Theme type")
    primary_color: str = PydanticField(default="#1976d2", description="Primary color (hex)")
    secondary_color: str = PydanticField(default="#424242", description="Secondary color (hex)")
    accent_color: str = PydanticField(default="#ff4081", description="Accent color (hex)")
    font_size: str = PydanticField(default="medium", description="Font size (small, medium, large)")
    font_family: str = PydanticField(default="system", description="Font family")
    high_contrast: bool = PydanticField(default=False, description="High contrast mode")
    reduced_motion: bool = PydanticField(default=False, description="Reduce motion for accessibility")
    
    @validator('primary_color', 'secondary_color', 'accent_color')
    def validate_hex_color(cls, v):
        import re
        hex_pattern = r'^#[0-9A-Fa-f]{6}$'
        if not re.match(hex_pattern, v):
            raise ValueError("Color must be a valid hex color (e.g., #1976d2)")
        return v.lower()


class LayoutSettings(BaseModel):
    """Layout settings model"""
    layout_type: LayoutType = PydanticField(default=LayoutType.GRID, description="Layout type")
    grid_columns: int = PydanticField(default=12, ge=6, le=24, description="Number of grid columns")
    grid_gap: int = PydanticField(default=16, ge=8, le=32, description="Grid gap in pixels")
    panel_spacing: int = PydanticField(default=8, ge=4, le=16, description="Panel spacing in pixels")
    sidebar_width: int = PydanticField(default=280, ge=200, le=400, description="Sidebar width in pixels")
    header_height: int = PydanticField(default=64, ge=48, le=96, description="Header height in pixels")
    responsive_breakpoints: Dict[str, int] = PydanticField(
        default_factory=lambda: {"mobile": 768, "tablet": 1024, "desktop": 1440},
        description="Responsive breakpoints"
    )
    auto_save: bool = PydanticField(default=True, description="Auto-save layout changes")
    snap_to_grid: bool = PydanticField(default=True, description="Snap widgets to grid")


class AccessibilitySettings(BaseModel):
    """Accessibility settings model"""
    screen_reader: bool = PydanticField(default=False, description="Screen reader support")
    keyboard_navigation: bool = PydanticField(default=True, description="Enhanced keyboard navigation")
    focus_indicators: bool = PydanticField(default=True, description="Visible focus indicators")
    color_blind_support: bool = PydanticField(default=False, description="Color blind support")
    text_scaling: float = PydanticField(default=1.0, ge=0.5, le=2.0, description="Text scaling factor")
    voice_commands: bool = PydanticField(default=False, description="Voice command support")
    alternative_text: bool = PydanticField(default=True, description="Alternative text for images")


class DashboardPreferences(BaseModel):
    """Complete dashboard preferences model"""
    widgets: List[WidgetConfiguration] = PydanticField(default_factory=list, description="Widget configurations")
    notifications: NotificationSettings = PydanticField(default_factory=NotificationSettings, description="Notification settings")
    theme: ThemeSettings = PydanticField(default_factory=ThemeSettings, description="Theme settings")
    layout: LayoutSettings = PydanticField(default_factory=LayoutSettings, description="Layout settings")
    accessibility: AccessibilitySettings = PydanticField(default_factory=AccessibilitySettings, description="Accessibility settings")
    custom_settings: Dict[str, Any] = PydanticField(default_factory=dict, description="Custom user settings")
    version: str = PydanticField(default="1.0.0", description="Preferences schema version")
    
    @validator('widgets')
    def validate_widgets(cls, v):
        widget_ids = [widget.widget_id for widget in v]
        if len(widget_ids) != len(set(widget_ids)):
            raise ValueError("Widget IDs must be unique")
        return v


# Database Models
class UserPreferences(SQLModel, table=True):
    """User preferences database model"""
    __tablename__ = "user_preferences"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(..., index=True, description="User identifier from AWS Cognito")
    preferences_data: Dict[str, Any] = Field(sa_column=Column(JSON), description="JSON preferences data")
    role: UserRole = Field(default=UserRole.VIEWER, description="User role for role-based customization")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
        description="Last update timestamp"
    )
    version: str = Field(default="1.0.0", description="Preferences schema version")
    is_active: bool = Field(default=True, description="Whether preferences are active")
    
    # Indexes
    __table_args__ = (
        Index("idx_user_preferences_user_id", "user_id"),
        Index("idx_user_preferences_role", "role"),
        Index("idx_user_preferences_updated_at", "updated_at"),
        UniqueConstraint("user_id", name="uq_user_preferences_user_id"),
    )


class UserPreferencesHistory(SQLModel, table=True):
    """User preferences history for audit trail"""
    __tablename__ = "user_preferences_history"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(..., index=True, description="User identifier")
    preferences_data: Dict[str, Any] = Field(sa_column=Column(JSON), description="JSON preferences data snapshot")
    action: str = Field(..., description="Action performed (create, update, delete)")
    changed_by: str = Field(..., description="User who made the change")
    change_reason: Optional[str] = Field(default=None, description="Reason for the change")
    version: str = Field(default="1.0.0", description="Preferences schema version")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="Change timestamp"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_user_preferences_history_user_id", "user_id"),
        Index("idx_user_preferences_history_created_at", "created_at"),
        Index("idx_user_preferences_history_action", "action"),
    )


# API Request/Response Models
class CreatePreferencesRequest(BaseModel):
    """Request model for creating user preferences"""
    preferences: DashboardPreferences = PydanticField(..., description="Dashboard preferences")
    role: Optional[UserRole] = PydanticField(default=None, description="User role (auto-detected if not provided)")
    custom_settings: Optional[Dict[str, Any]] = PydanticField(default_factory=dict, description="Additional custom settings")


class UpdatePreferencesRequest(BaseModel):
    """Request model for updating user preferences"""
    preferences: Optional[DashboardPreferences] = PydanticField(default=None, description="Updated preferences (partial update)")
    custom_settings: Optional[Dict[str, Any]] = PydanticField(default=None, description="Updated custom settings")
    change_reason: Optional[str] = PydanticField(default=None, description="Reason for the change")


class PreferencesResponse(BaseModel):
    """Response model for user preferences"""
    user_id: str = PydanticField(..., description="User identifier")
    preferences: DashboardPreferences = PydanticField(..., description="Dashboard preferences")
    role: UserRole = PydanticField(..., description="User role")
    version: str = PydanticField(..., description="Preferences schema version")
    created_at: datetime = PydanticField(..., description="Creation timestamp")
    updated_at: datetime = PydanticField(..., description="Last update timestamp")
    is_active: bool = PydanticField(..., description="Whether preferences are active")


class PreferencesSummaryResponse(BaseModel):
    """Summary response model for user preferences"""
    user_id: str = PydanticField(..., description="User identifier")
    has_preferences: bool = PydanticField(..., description="Whether user has saved preferences")
    role: UserRole = PydanticField(..., description="User role")
    last_updated: Optional[datetime] = PydanticField(default=None, description="Last update timestamp")
    widget_count: int = PydanticField(default=0, description="Number of configured widgets")
    theme_type: ThemeType = PydanticField(..., description="Current theme type")


class DefaultPreferencesResponse(BaseModel):
    """Response model for default preferences by role"""
    role: UserRole = PydanticField(..., description="User role")
    preferences: DashboardPreferences = PydanticField(..., description="Default preferences for role")
    description: str = PydanticField(..., description="Description of default preferences")


class PreferencesValidationResponse(BaseModel):
    """Response model for preferences validation"""
    is_valid: bool = PydanticField(..., description="Whether preferences are valid")
    errors: List[str] = PydanticField(default_factory=list, description="Validation errors")
    warnings: List[str] = PydanticField(default_factory=list, description="Validation warnings")
    suggestions: List[str] = PydanticField(default_factory=list, description="Improvement suggestions")


# Utility Functions
def get_default_preferences_for_role(role: UserRole) -> DashboardPreferences:
    """Get default preferences for a specific role"""
    
    if role == UserRole.ADMIN:
        return DashboardPreferences(
            widgets=[
                WidgetConfiguration(
                    widget_id="system_overview",
                    widget_type=WidgetType.SYSTEM_STATUS,
                    position_x=0, position_y=0, width=6, height=3
                ),
                WidgetConfiguration(
                    widget_id="user_management",
                    widget_type=WidgetType.USER_ACTIVITY,
                    position_x=6, position_y=0, width=6, height=3
                ),
                WidgetConfiguration(
                    widget_id="performance_metrics",
                    widget_type=WidgetType.PERFORMANCE_METRICS,
                    position_x=0, position_y=3, width=12, height=4
                )
            ],
            notifications=NotificationSettings(
                enabled=True,
                types=[NotificationType.EMAIL, NotificationType.IN_APP],
                frequency=NotificationFrequency.IMMEDIATE,
                alert_types=["system_alerts", "security_alerts", "user_alerts"]
            ),
            theme=ThemeSettings(
                theme_type=ThemeType.DARK,
                primary_color="#1976d2",
                secondary_color="#424242",
                accent_color="#ff4081"
            ),
            layout=LayoutSettings(
                layout_type=LayoutType.GRID,
                grid_columns=12,
                auto_save=True
            )
        )
    
    elif role == UserRole.SECURITY_OFFICER:
        return DashboardPreferences(
            widgets=[
                WidgetConfiguration(
                    widget_id="security_alerts",
                    widget_type=WidgetType.SECURITY_ALERTS,
                    position_x=0, position_y=0, width=8, height=4
                ),
                WidgetConfiguration(
                    widget_id="detection_summary",
                    widget_type=WidgetType.DETECTION_SUMMARY,
                    position_x=8, position_y=0, width=4, height=4
                ),
                WidgetConfiguration(
                    widget_id="recent_activity",
                    widget_type=WidgetType.RECENT_ACTIVITY,
                    position_x=0, position_y=4, width=12, height=3
                )
            ],
            notifications=NotificationSettings(
                enabled=True,
                types=[NotificationType.EMAIL, NotificationType.IN_APP, NotificationType.PUSH],
                frequency=NotificationFrequency.IMMEDIATE,
                alert_types=["security_alerts", "detection_alerts", "system_alerts"]
            ),
            theme=ThemeSettings(
                theme_type=ThemeType.DARK,
                primary_color="#d32f2f",
                secondary_color="#424242",
                accent_color="#ff9800"
            )
        )
    
    elif role == UserRole.COMPLIANCE_MANAGER:
        return DashboardPreferences(
            widgets=[
                WidgetConfiguration(
                    widget_id="compliance_reports",
                    widget_type=WidgetType.COMPLIANCE_REPORTS,
                    position_x=0, position_y=0, width=6, height=4
                ),
                WidgetConfiguration(
                    widget_id="export_history",
                    widget_type=WidgetType.EXPORT_HISTORY,
                    position_x=6, position_y=0, width=6, height=4
                ),
                WidgetConfiguration(
                    widget_id="analytics_chart",
                    widget_type=WidgetType.ANALYTICS_CHART,
                    position_x=0, position_y=4, width=12, height=3
                )
            ],
            notifications=NotificationSettings(
                enabled=True,
                types=[NotificationType.EMAIL, NotificationType.IN_APP],
                frequency=NotificationFrequency.DAILY,
                alert_types=["compliance_alerts", "export_alerts"]
            ),
            theme=ThemeSettings(
                theme_type=ThemeType.LIGHT,
                primary_color="#388e3c",
                secondary_color="#424242",
                accent_color="#ffc107"
            )
        )
    
    else:  # Default for VIEWER, ANALYST, etc.
        return DashboardPreferences(
            widgets=[
                WidgetConfiguration(
                    widget_id="detection_summary",
                    widget_type=WidgetType.DETECTION_SUMMARY,
                    position_x=0, position_y=0, width=6, height=3
                ),
                WidgetConfiguration(
                    widget_id="recent_activity",
                    widget_type=WidgetType.RECENT_ACTIVITY,
                    position_x=6, position_y=0, width=6, height=3
                )
            ],
            notifications=NotificationSettings(
                enabled=True,
                types=[NotificationType.IN_APP],
                frequency=NotificationFrequency.DAILY,
                alert_types=["detection_alerts"]
            ),
            theme=ThemeSettings(
                theme_type=ThemeType.LIGHT,
                primary_color="#1976d2",
                secondary_color="#424242",
                accent_color="#ff4081"
            )
        )


def validate_preferences(preferences: DashboardPreferences) -> PreferencesValidationResponse:
    """Validate user preferences and return validation results"""
    errors = []
    warnings = []
    suggestions = []
    
    # Validate widget configurations
    widget_ids = [widget.widget_id for widget in preferences.widgets]
    if len(widget_ids) != len(set(widget_ids)):
        errors.append("Widget IDs must be unique")
    
    # Check for overlapping widgets
    for i, widget1 in enumerate(preferences.widgets):
        for j, widget2 in enumerate(preferences.widgets):
            if i != j:
                if (widget1.position_x < widget2.position_x + widget2.width and
                    widget1.position_x + widget1.width > widget2.position_x and
                    widget1.position_y < widget2.position_y + widget2.height and
                    widget1.position_y + widget1.height > widget2.position_y):
                    errors.append(f"Widgets '{widget1.widget_id}' and '{widget2.widget_id}' overlap")
    
    # Validate notification settings
    if preferences.notifications.enabled:
        if NotificationType.EMAIL in preferences.notifications.types and not preferences.notifications.email_address:
            warnings.append("Email notifications enabled but no email address provided")
        
        if NotificationType.SMS in preferences.notifications.types and not preferences.notifications.phone_number:
            warnings.append("SMS notifications enabled but no phone number provided")
    
    # Validate accessibility settings
    if preferences.accessibility.text_scaling < 0.8:
        warnings.append("Very small text scaling may affect readability")
    elif preferences.accessibility.text_scaling > 1.5:
        warnings.append("Very large text scaling may affect layout")
    
    # Suggestions
    if len(preferences.widgets) == 0:
        suggestions.append("Consider adding some widgets to personalize your dashboard")
    
    if preferences.theme.theme_type == ThemeType.AUTO:
        suggestions.append("Auto theme will adapt to your system preferences")
    
    if not preferences.layout.auto_save:
        suggestions.append("Enable auto-save to preserve your layout changes")
    
    return PreferencesValidationResponse(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        suggestions=suggestions
    )
