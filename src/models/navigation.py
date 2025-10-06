#!/usr/bin/env python3
"""
Navigation Context Data Models
Pydantic models for navigation state, breadcrumbs, and user preferences
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator


class NavigationItemType(str, Enum):
    """Navigation item types"""
    SECTION = "section"
    PAGE = "page"
    MODAL = "modal"
    EXTERNAL = "external"


class NavigationPermission(str, Enum):
    """Navigation permission levels"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    SYSTEM_ADMIN = "system_admin"


class BreadcrumbItem(BaseModel):
    """Breadcrumb navigation item"""
    label: str = Field(..., description="Display label for breadcrumb")
    path: str = Field(..., description="Navigation path/URL")
    is_active: bool = Field(default=False, description="Whether this is the current page")
    icon: Optional[str] = Field(None, description="Icon identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class NavigationItem(BaseModel):
    """Individual navigation item"""
    id: str = Field(..., description="Unique navigation item identifier")
    label: str = Field(..., description="Display label")
    path: str = Field(..., description="Navigation path/URL")
    type: NavigationItemType = Field(..., description="Navigation item type")
    icon: Optional[str] = Field(None, description="Icon identifier")
    description: Optional[str] = Field(None, description="Item description")
    required_permission: Optional[NavigationPermission] = Field(None, description="Required permission level")
    required_roles: List[str] = Field(default_factory=list, description="Required user roles")
    is_external: bool = Field(default=False, description="Whether this is an external link")
    is_disabled: bool = Field(default=False, description="Whether this item is disabled")
    badge: Optional[str] = Field(None, description="Badge text/count")
    children: List['NavigationItem'] = Field(default_factory=list, description="Child navigation items")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        # Allow recursive models
        orm_mode = True


class NavigationSection(BaseModel):
    """Navigation section/group"""
    id: str = Field(..., description="Unique section identifier")
    label: str = Field(..., description="Section display label")
    icon: Optional[str] = Field(None, description="Section icon")
    description: Optional[str] = Field(None, description="Section description")
    order: int = Field(default=0, description="Display order")
    is_collapsible: bool = Field(default=True, description="Whether section can be collapsed")
    is_collapsed: bool = Field(default=False, description="Whether section is currently collapsed")
    items: List[NavigationItem] = Field(default_factory=list, description="Navigation items in this section")
    required_permission: Optional[NavigationPermission] = Field(None, description="Required permission level")
    required_roles: List[str] = Field(default_factory=list, description="Required user roles")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class CurrentRouteContext(BaseModel):
    """Current route context information"""
    path: str = Field(..., description="Current route path")
    section_id: Optional[str] = Field(None, description="Current navigation section ID")
    page_id: Optional[str] = Field(None, description="Current page ID")
    breadcrumbs: List[BreadcrumbItem] = Field(default_factory=list, description="Breadcrumb navigation")
    page_title: Optional[str] = Field(None, description="Current page title")
    page_description: Optional[str] = Field(None, description="Current page description")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional route metadata")


class NavigationPreferences(BaseModel):
    """User navigation preferences"""
    user_id: str = Field(..., description="User identifier")
    sidebar_collapsed: bool = Field(default=False, description="Whether sidebar is collapsed")
    sidebar_width: int = Field(default=280, ge=200, le=400, description="Sidebar width in pixels")
    show_breadcrumbs: bool = Field(default=True, description="Whether to show breadcrumbs")
    show_page_titles: bool = Field(default=True, description="Whether to show page titles")
    navigation_style: str = Field(default="default", description="Navigation style preference")
    favorite_items: List[str] = Field(default_factory=list, description="Favorite navigation item IDs")
    recent_items: List[str] = Field(default_factory=list, description="Recently accessed item IDs")
    custom_sections: List[NavigationSection] = Field(default_factory=list, description="Custom navigation sections")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")


class NavigationState(BaseModel):
    """Complete navigation state"""
    current_context: CurrentRouteContext = Field(..., description="Current route context")
    available_sections: List[NavigationSection] = Field(default_factory=list, description="Available navigation sections")
    user_preferences: Optional[NavigationPreferences] = Field(None, description="User navigation preferences")
    quick_actions: List[NavigationItem] = Field(default_factory=list, description="Quick action items")
    recent_navigation: List[NavigationItem] = Field(default_factory=list, description="Recent navigation history")
    suggested_items: List[NavigationItem] = Field(default_factory=list, description="Suggested navigation items")
    notifications_count: int = Field(default=0, ge=0, description="Unread notifications count")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")


class PrefetchTarget(BaseModel):
    """Data prefetch target"""
    route_path: str = Field(..., description="Target route path")
    data_sources: List[str] = Field(..., description="Data sources to prefetch from")
    priority: int = Field(default=1, ge=1, le=10, description="Prefetch priority (1=highest)")
    estimated_load_time_ms: int = Field(default=100, ge=0, description="Estimated load time in milliseconds")
    cache_ttl_seconds: int = Field(default=300, ge=60, description="Cache TTL in seconds")
    dependencies: List[str] = Field(default_factory=list, description="Route dependencies")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional prefetch metadata")


class PrefetchStrategy(BaseModel):
    """Prefetch strategy configuration"""
    enabled: bool = Field(default=True, description="Whether prefetching is enabled")
    max_concurrent_prefetches: int = Field(default=3, ge=1, le=10, description="Maximum concurrent prefetches")
    prefetch_threshold_ms: int = Field(default=50, ge=0, le=200, description="Response time threshold for triggering prefetch")
    user_pattern_analysis: bool = Field(default=True, description="Whether to analyze user navigation patterns")
    route_mapping: Dict[str, PrefetchTarget] = Field(default_factory=dict, description="Route to prefetch target mapping")
    global_cache_ttl_seconds: int = Field(default=300, ge=60, description="Global cache TTL in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional strategy metadata")


class NavigationAnalytics(BaseModel):
    """Navigation analytics data"""
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    navigation_patterns: Dict[str, int] = Field(default_factory=dict, description="Navigation pattern frequencies")
    most_visited_routes: List[str] = Field(default_factory=list, description="Most visited routes")
    average_session_duration_minutes: float = Field(default=0, ge=0, description="Average session duration")
    bounce_rate: float = Field(default=0, ge=0, le=1, description="Bounce rate")
    conversion_rate: float = Field(default=0, ge=0, le=1, description="Conversion rate")
    last_analyzed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last analysis timestamp")


class NavigationContextResponse(BaseModel):
    """Navigation context API response"""
    navigation_state: NavigationState = Field(..., description="Complete navigation state")
    prefetch_strategy: PrefetchStrategy = Field(..., description="Prefetch strategy configuration")
    analytics: Optional[NavigationAnalytics] = Field(None, description="Navigation analytics data")
    cache_info: Dict[str, Any] = Field(default_factory=dict, description="Cache information")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    request_id: str = Field(..., description="Request identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Response timestamp")


# Update forward references
NavigationItem.model_rebuild()


class NavigationCacheKey(BaseModel):
    """Navigation cache key structure"""
    user_id: str = Field(..., description="User identifier")
    route_path: str = Field(..., description="Current route path")
    user_roles: List[str] = Field(default_factory=list, description="User roles")
    cache_version: str = Field(default="v1", description="Cache version")
    
    def to_key(self) -> str:
        """Convert to Redis cache key"""
        roles_str = "_".join(sorted(self.user_roles)) if self.user_roles else "no_roles"
        return f"nav:{self.user_id}:{self.route_path}:{roles_str}:{self.cache_version}"


class NavigationPerformanceMetrics(BaseModel):
    """Navigation performance metrics"""
    cache_hit_rate: float = Field(default=0, ge=0, le=1, description="Cache hit rate")
    average_response_time_ms: float = Field(default=0, ge=0, description="Average response time")
    prefetch_success_rate: float = Field(default=0, ge=0, le=1, description="Prefetch success rate")
    navigation_load_time_ms: float = Field(default=0, ge=0, description="Navigation load time")
    user_satisfaction_score: float = Field(default=0, ge=0, le=5, description="User satisfaction score")
    last_measured: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last measurement timestamp")
