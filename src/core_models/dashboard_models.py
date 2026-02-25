#!/usr/bin/env python3
"""
Dashboard Navigation Models for SecureAI DeepFake Detection
SQLModel classes for dashboard session management, user preferences, and navigation tracking
"""

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
from uuid import uuid4, UUID as PyUUID
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum


class NavigationStyleEnum(str, Enum):
    """Enumeration of supported navigation styles"""
    SIDEBAR = "sidebar"
    TOP_NAV = "top_nav"
    BREADCRUMB = "breadcrumb"
    MINIMAL = "minimal"


class MobileNavigationStyleEnum(str, Enum):
    """Enumeration of supported mobile navigation styles"""
    BOTTOM_TAB = "bottom_tab"
    DRAWER = "drawer"
    TOP_TAB = "top_tab"
    FULL_SCREEN = "full_screen"


class ActivityTypeEnum(str, Enum):
    """Enumeration of user activity types"""
    NAVIGATION = "navigation"
    ANALYSIS = "analysis"
    SETTINGS = "settings"
    AUTHENTICATION = "authentication"
    SYSTEM = "system"


class NavigationMethodEnum(str, Enum):
    """Enumeration of navigation methods"""
    CLICK = "click"
    KEYBOARD = "keyboard"
    GESTURE = "gesture"
    AUTOMATIC = "automatic"
    DIRECT_URL = "direct_url"


class User(SQLModel, table=True):
    """
    User table for authentication and user management
    """
    __tablename__ = "user"
    __table_args__ = (
        UniqueConstraint("email", name="uq_user_email"),
        Index("idx_user_email", "email"),
        Index("idx_user_active", "is_active"),
    )

    # Primary key
    id: PyUUID = Field(
        default_factory=uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    )

    # User credentials
    email: str = Field(
        max_length=255,
        unique=True,
        index=True,
        description="User email address (unique identifier)"
    )
    password_hash: str = Field(
        max_length=255,
        description="Hashed password for authentication"
    )
    name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="User display name"
    )

    # User status
    is_active: bool = Field(
        default=True,
        description="Whether the user account is active"
    )
    is_verified: bool = Field(
        default=False,
        description="Whether the user email is verified"
    )

    # Audit fields
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="Account creation timestamp"
    )
    last_login: Optional[datetime] = Field(
        default=None,
        description="Last login timestamp"
    )

    # Relationships
    dashboard_sessions: List["DashboardSession"] = Relationship(back_populates="user")
    preferences: List["UserPreference"] = Relationship(back_populates="user")
    activities: List["UserActivity"] = Relationship(back_populates="user")


class DashboardSession(SQLModel, table=True):
    """
    Dashboard session table for storing navigation context and session state
    """
    __tablename__ = "dashboard_session"
    __table_args__ = (
        UniqueConstraint("session_token", name="uq_session_token"),
        Index("idx_session_token", "session_token"),
        Index("idx_session_user_id", "user_id"),
        Index("idx_session_expires", "expires_at"),
    )

    # Primary key
    id: PyUUID = Field(
        default_factory=uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    )

    # User association
    user_id: PyUUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("user.id")),
        description="Foreign key to User"
    )
    user: Optional[User] = Relationship(back_populates="dashboard_sessions")

    # Session metadata
    session_token: str = Field(
        max_length=255,
        unique=True,
        index=True,
        description="Unique session token for authentication"
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        description="Session expiration timestamp"
    )

    # Navigation context (JSONB) - stores navigation state
    session_context: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Navigation context including currentPath, navigationHistory, breadcrumbPreferences, sidebarCollapsed, favoriteRoutes, and lastVisitedSections"
    )

    # Audit fields
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="Session creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="Last session update timestamp"
    )
    last_activity: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="Last user activity timestamp"
    )

    # Relationships
    activities: List["UserActivity"] = Relationship(back_populates="session")

    def get_navigation_context(self) -> Dict[str, Any]:
        """Get navigation context from session_context JSONB field"""
        return self.session_context or {}

    def update_navigation_context(self, context: Dict[str, Any]) -> None:
        """Update navigation context in session_context JSONB field"""
        current_context = self.get_navigation_context()
        current_context.update(context)
        self.session_context = current_context

    def get_current_path(self) -> Optional[str]:
        """Get current navigation path from session context"""
        return self.get_navigation_context().get("currentPath")

    def get_navigation_history(self) -> List[Dict[str, Any]]:
        """Get navigation history from session context"""
        return self.get_navigation_context().get("navigationHistory", [])

    def get_favorite_routes(self) -> List[str]:
        """Get favorite routes from session context"""
        return self.get_navigation_context().get("favoriteRoutes", [])

    def is_sidebar_collapsed(self) -> bool:
        """Check if sidebar is collapsed from session context"""
        return self.get_navigation_context().get("sidebarCollapsed", False)

    def is_session_expired(self) -> bool:
        """Check if session has expired"""
        return datetime.now(timezone.utc) > self.expires_at

    def extend_session(self, hours: int = 24) -> None:
        """Extend session expiration time"""
        self.expires_at = datetime.now(timezone.utc).replace(
            hour=self.expires_at.hour + hours
        )


class UserPreference(SQLModel, table=True):
    """
    User preferences table for storing navigation and dashboard preferences
    """
    __tablename__ = "user_preference"
    __table_args__ = (
        Index("idx_preference_user_id", "user_id"),
    )

    # Primary key
    id: PyUUID = Field(
        default_factory=uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    )

    # User association
    user_id: PyUUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("user.id")),
        description="Foreign key to User"
    )
    user: Optional[User] = Relationship(back_populates="preferences")

    # Navigation preferences
    default_landing_page: str = Field(
        default="/dashboard",
        max_length=255,
        description="Default landing page for user navigation"
    )
    navigation_style: NavigationStyleEnum = Field(
        default=NavigationStyleEnum.SIDEBAR,
        description="Preferred navigation style"
    )
    show_navigation_labels: bool = Field(
        default=True,
        description="Whether to show navigation labels"
    )
    enable_keyboard_shortcuts: bool = Field(
        default=True,
        description="Whether to enable keyboard shortcuts for navigation"
    )
    mobile_navigation_style: MobileNavigationStyleEnum = Field(
        default=MobileNavigationStyleEnum.BOTTOM_TAB,
        description="Preferred mobile navigation style"
    )
    accessibility_mode: bool = Field(
        default=False,
        description="Whether accessibility mode is enabled"
    )
    custom_navigation_order: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(ARRAY(String)),
        description="Custom navigation menu order"
    )

    # Additional dashboard preferences
    theme_preference: Optional[str] = Field(
        default=None,
        max_length=50,
        description="User's preferred theme (light/dark/auto)"
    )
    language_preference: Optional[str] = Field(
        default=None,
        max_length=10,
        description="User's preferred language (ISO 639-1 code)"
    )
    timezone_preference: Optional[str] = Field(
        default=None,
        max_length=50,
        description="User's preferred timezone"
    )

    # Audit fields
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="Preference creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="Last preference update timestamp"
    )

    def get_navigation_preferences(self) -> Dict[str, Any]:
        """Get all navigation-related preferences"""
        return {
            "default_landing_page": self.default_landing_page,
            "navigation_style": self.navigation_style,
            "show_navigation_labels": self.show_navigation_labels,
            "enable_keyboard_shortcuts": self.enable_keyboard_shortcuts,
            "mobile_navigation_style": self.mobile_navigation_style,
            "accessibility_mode": self.accessibility_mode,
            "custom_navigation_order": self.custom_navigation_order or []
        }

    def update_navigation_preference(self, key: str, value: Any) -> None:
        """Update a specific navigation preference"""
        if hasattr(self, key):
            setattr(self, key, value)
            self.updated_at = datetime.now(timezone.utc)

    def is_accessibility_enabled(self) -> bool:
        """Check if accessibility features are enabled"""
        return self.accessibility_mode

    def get_custom_navigation_order(self) -> List[str]:
        """Get custom navigation order or return empty list"""
        return self.custom_navigation_order or []


class UserActivity(SQLModel, table=True):
    """
    User activity table for tracking navigation and system interactions
    """
    __tablename__ = "user_activity"
    __table_args__ = (
        Index("idx_activity_user_id", "user_id"),
        Index("idx_activity_type", "activity_type"),
        Index("idx_activity_created_at", "created_at"),
        Index("idx_activity_session_id", "session_id"),
    )

    # Primary key
    id: PyUUID = Field(
        default_factory=uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    )

    # User association
    user_id: PyUUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("user.id")),
        description="Foreign key to User"
    )
    user: Optional[User] = Relationship(back_populates="activities")

    # Session association (optional)
    session_id: Optional[PyUUID] = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True), ForeignKey("dashboard_session.id")),
        description="Foreign key to DashboardSession (optional)"
    )
    session: Optional[DashboardSession] = Relationship(back_populates="activities")

    # Activity metadata
    activity_type: ActivityTypeEnum = Field(
        description="Type of user activity"
    )
    activity_data: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Activity-specific data including navigationData for navigation activities"
    )

    # Additional metadata
    ip_address: Optional[str] = Field(
        default=None,
        max_length=45,
        description="IP address of the user (IPv4 or IPv6)"
    )
    user_agent: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="User agent string from the request"
    )

    # Audit fields
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="Activity timestamp"
    )

    def get_navigation_data(self) -> Optional[Dict[str, Any]]:
        """Get navigation data for navigation-type activities"""
        if self.activity_type == ActivityTypeEnum.NAVIGATION:
            return self.activity_data
        return None

    def get_activity_summary(self) -> Dict[str, Any]:
        """Get summary of activity data"""
        return {
            "id": str(self.id),
            "activity_type": self.activity_type,
            "created_at": self.created_at.isoformat(),
            "session_id": str(self.session_id) if self.session_id else None,
            "data": self.activity_data or {}
        }

    def is_navigation_activity(self) -> bool:
        """Check if this is a navigation activity"""
        return self.activity_type == ActivityTypeEnum.NAVIGATION

    def get_navigation_performance(self) -> Optional[Dict[str, Any]]:
        """Get navigation performance metrics if available"""
        if self.is_navigation_activity() and self.activity_data:
            nav_data = self.activity_data.get("navigationData", {})
            return {
                "from_path": nav_data.get("fromPath"),
                "to_path": nav_data.get("toPath"),
                "navigation_method": nav_data.get("navigationMethod"),
                "load_time": nav_data.get("loadTime"),
                "prefetch_hit": nav_data.get("prefetchHit"),
                "timestamp": nav_data.get("timestamp")
            }
        return None


# Navigation Context Data Models (for type hints and validation)
class NavigationHistoryEntry(SQLModel):
    """Model for navigation history entries"""
    path: str = Field(description="Navigation path")
    timestamp: datetime = Field(description="Navigation timestamp")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class BreadcrumbPreferences(SQLModel):
    """Model for breadcrumb preferences"""
    show_breadcrumbs: bool = Field(default=True, description="Whether to show breadcrumbs")
    max_depth: int = Field(default=5, ge=1, le=10, description="Maximum breadcrumb depth")
    separator: str = Field(default=">", max_length=10, description="Breadcrumb separator")


class LastVisitedSection(SQLModel):
    """Model for last visited section tracking"""
    path: str = Field(description="Section path")
    timestamp: datetime = Field(description="Visit timestamp")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class NavigationData(SQLModel):
    """Model for navigation activity data"""
    from_path: Optional[str] = Field(default=None, description="Source navigation path")
    to_path: str = Field(description="Target navigation path")
    navigation_method: NavigationMethodEnum = Field(description="Method used for navigation")
    load_time: Optional[float] = Field(default=None, ge=0, description="Page load time in milliseconds")
    prefetch_hit: Optional[bool] = Field(default=None, description="Whether prefetch cache was hit")
    timestamp: datetime = Field(description="Navigation timestamp")


class SessionContext(SQLModel):
    """Model for complete session context"""
    current_path: Optional[str] = Field(default=None, description="Current navigation path")
    navigation_history: List[NavigationHistoryEntry] = Field(default_factory=list, description="Navigation history")
    breadcrumb_preferences: Optional[BreadcrumbPreferences] = Field(default=None, description="Breadcrumb settings")
    sidebar_collapsed: bool = Field(default=False, description="Whether sidebar is collapsed")
    favorite_routes: List[str] = Field(default_factory=list, description="List of favorite routes")
    last_visited_sections: Dict[str, LastVisitedSection] = Field(default_factory=dict, description="Last visited sections")

    def add_navigation_entry(self, path: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Add a new navigation history entry"""
        entry = NavigationHistoryEntry(
            path=path,
            timestamp=datetime.now(timezone.utc),
            context=context
        )
        self.navigation_history.append(entry)
        # Keep only last 50 entries to prevent unlimited growth
        if len(self.navigation_history) > 50:
            self.navigation_history = self.navigation_history[-50:]

    def add_favorite_route(self, path: str) -> None:
        """Add a route to favorites"""
        if path not in self.favorite_routes:
            self.favorite_routes.append(path)
            # Keep only last 20 favorites
            if len(self.favorite_routes) > 20:
                self.favorite_routes = self.favorite_routes[-20:]

    def remove_favorite_route(self, path: str) -> None:
        """Remove a route from favorites"""
        if path in self.favorite_routes:
            self.favorite_routes.remove(path)

    def update_last_visited_section(self, path: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Update last visited section"""
        section = LastVisitedSection(
            path=path,
            timestamp=datetime.now(timezone.utc),
            context=context
        )
        self.last_visited_sections[path] = section
        # Keep only last 100 sections to prevent unlimited growth
        if len(self.last_visited_sections) > 100:
            # Remove oldest entries
            sorted_sections = sorted(
                self.last_visited_sections.items(),
                key=lambda x: x[1].timestamp
            )
            self.last_visited_sections = dict(sorted_sections[-100:])
