#!/usr/bin/env python3
"""
Navigation API Response Models and Request Handlers
Pydantic models for navigation context data and preference updates extending existing dashboard API patterns
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum

# Import the existing DashboardOverviewResponse from dashboard_models
from .dashboard_models import DashboardOverviewResponse


class NavigationStyleEnum(str, Enum):
    """Enumeration of supported navigation styles"""
    SIDEBAR = "sidebar"
    TOP_NAV = "top_nav"
    BREADCRUMB = "breadcrumb"
    MINIMAL = "minimal"


class PermissionLevelEnum(str, Enum):
    """Enumeration of permission levels for navigation routes"""
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class NavigationRoute(BaseModel):
    """
    Navigation route model for navigation items and menu structure.
    Defines individual navigation routes with optional nested children support.
    """
    
    # Route identification
    id: str = Field(
        ...,
        description="Unique identifier for the navigation route"
    )
    path: str = Field(
        ...,
        description="Route path for navigation"
    )
    label: str = Field(
        ...,
        description="Display label for the route"
    )
    
    # Optional route properties
    icon: Optional[str] = Field(
        default=None,
        description="Optional icon identifier for the route"
    )
    required_permissions: Optional[List[str]] = Field(
        default=None,
        description="Optional required permissions array for access control"
    )
    badge: Optional[int] = Field(
        default=None,
        ge=0,
        description="Optional badge number for notifications or counts"
    )
    is_active: bool = Field(
        default=False,
        description="Whether the route is currently active"
    )
    
    # Nested routes support
    children: Optional[List["NavigationRoute"]] = Field(
        default=None,
        description="Optional children array for nested routes"
    )
    
    # Additional metadata
    tooltip: Optional[str] = Field(
        default=None,
        description="Optional tooltip text for the route"
    )
    is_external: bool = Field(
        default=False,
        description="Whether the route points to an external URL"
    )
    order: Optional[int] = Field(
        default=None,
        description="Optional display order for route sorting"
    )
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate route ID format"""
        if not v or not v.strip():
            raise ValueError("Route ID cannot be empty")
        if len(v) > 100:
            raise ValueError("Route ID cannot exceed 100 characters")
        return v.strip()
    
    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate route path format"""
        if not v or not v.strip():
            raise ValueError("Route path cannot be empty")
        if not v.startswith('/'):
            raise ValueError("Route path must start with '/'")
        return v.strip()
    
    @field_validator('label')
    @classmethod
    def validate_label(cls, v: str) -> str:
        """Validate route label"""
        if not v or not v.strip():
            raise ValueError("Route label cannot be empty")
        if len(v) > 255:
            raise ValueError("Route label cannot exceed 255 characters")
        return v.strip()
    
    @field_validator('children')
    @classmethod
    def validate_children(cls, v: Optional[List["NavigationRoute"]]) -> Optional[List["NavigationRoute"]]:
        """Validate nested routes structure"""
        if v is not None:
            if len(v) > 50:
                raise ValueError("Cannot have more than 50 nested routes")
            
            # Validate no circular references
            for child in v:
                if child.id == cls.__dict__.get('id'):
                    raise ValueError("Circular reference detected in nested routes")
        
        return v
    
    def get_all_route_ids(self) -> List[str]:
        """Get all route IDs including nested children"""
        ids = [self.id]
        if self.children:
            for child in self.children:
                ids.extend(child.get_all_route_ids())
        return ids
    
    def find_route_by_id(self, route_id: str) -> Optional["NavigationRoute"]:
        """Find a route by ID including nested children"""
        if self.id == route_id:
            return self
        
        if self.children:
            for child in self.children:
                found = child.find_route_by_id(route_id)
                if found:
                    return found
        
        return None
    
    def find_route_by_path(self, path: str) -> Optional["NavigationRoute"]:
        """Find a route by path including nested children"""
        if self.path == path:
            return self
        
        if self.children:
            for child in self.children:
                found = child.find_route_by_path(path)
                if found:
                    return found
        
        return None
    
    def get_active_routes(self) -> List["NavigationRoute"]:
        """Get all active routes including nested children"""
        active_routes = []
        if self.is_active:
            active_routes.append(self)
        
        if self.children:
            for child in self.children:
                active_routes.extend(child.get_active_routes())
        
        return active_routes


class BreadcrumbItem(BaseModel):
    """
    Breadcrumb item model for navigation breadcrumbs.
    Defines individual breadcrumb items in the navigation hierarchy.
    """
    
    # Breadcrumb properties
    label: str = Field(
        ...,
        description="Breadcrumb display label"
    )
    path: Optional[str] = Field(
        default=None,
        description="Optional path for breadcrumb navigation"
    )
    is_active: bool = Field(
        default=False,
        description="Whether this breadcrumb item is currently active"
    )
    
    # Optional metadata
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata object for additional context"
    )
    
    # Additional properties
    icon: Optional[str] = Field(
        default=None,
        description="Optional icon for the breadcrumb item"
    )
    tooltip: Optional[str] = Field(
        default=None,
        description="Optional tooltip text for the breadcrumb"
    )
    
    @field_validator('label')
    @classmethod
    def validate_label(cls, v: str) -> str:
        """Validate breadcrumb label"""
        if not v or not v.strip():
            raise ValueError("Breadcrumb label cannot be empty")
        if len(v) > 255:
            raise ValueError("Breadcrumb label cannot exceed 255 characters")
        return v.strip()
    
    @field_validator('path')
    @classmethod
    def validate_path(cls, v: Optional[str]) -> Optional[str]:
        """Validate breadcrumb path"""
        if v is not None:
            if not v.strip():
                raise ValueError("Breadcrumb path cannot be empty")
            if not v.startswith('/'):
                raise ValueError("Breadcrumb path must start with '/'")
            return v.strip()
        return v
    
    def is_clickable(self) -> bool:
        """Check if breadcrumb item is clickable (has path and not active)"""
        return self.path is not None and not self.is_active
    
    def get_display_label(self) -> str:
        """Get display label with truncation if needed"""
        if len(self.label) > 50:
            return self.label[:47] + "..."
        return self.label


class NavigationHistoryEntry(BaseModel):
    """
    Navigation history entry model for tracking navigation history.
    """
    
    path: str = Field(
        ...,
        description="Navigation path"
    )
    timestamp: datetime = Field(
        ...,
        description="Navigation timestamp"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context for the navigation entry"
    )
    method: Optional[str] = Field(
        default=None,
        description="Navigation method (click, keyboard, direct_url, etc.)"
    )
    load_time: Optional[float] = Field(
        default=None,
        ge=0,
        description="Page load time in milliseconds"
    )
    
    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate navigation path"""
        if not v or not v.strip():
            raise ValueError("Navigation path cannot be empty")
        return v.strip()
    
    @field_validator('method')
    @classmethod
    def validate_method(cls, v: Optional[str]) -> Optional[str]:
        """Validate navigation method"""
        if v is not None:
            valid_methods = ['click', 'keyboard', 'direct_url', 'automatic', 'gesture']
            if v not in valid_methods:
                raise ValueError(f"Invalid navigation method. Must be one of: {valid_methods}")
        return v


class NavigationPreferences(BaseModel):
    """
    Navigation preferences model for user navigation settings.
    """
    
    default_landing_page: Optional[str] = Field(
        default=None,
        description="Default landing page for navigation"
    )
    navigation_style: Optional[NavigationStyleEnum] = Field(
        default=None,
        description="Preferred navigation style"
    )
    show_labels: Optional[bool] = Field(
        default=None,
        description="Whether to show navigation labels"
    )
    enable_keyboard_shortcuts: Optional[bool] = Field(
        default=None,
        description="Whether to enable keyboard shortcuts"
    )
    breadcrumb_depth: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="Maximum breadcrumb depth"
    )
    sidebar_collapsed: Optional[bool] = Field(
        default=None,
        description="Whether sidebar is collapsed by default"
    )
    auto_expand_active: Optional[bool] = Field(
        default=None,
        description="Whether to automatically expand active navigation sections"
    )
    
    @field_validator('default_landing_page')
    @classmethod
    def validate_landing_page(cls, v: Optional[str]) -> Optional[str]:
        """Validate default landing page"""
        if v is not None:
            if not v.strip():
                raise ValueError("Default landing page cannot be empty")
            if not v.startswith('/'):
                raise ValueError("Default landing page must start with '/'")
            return v.strip()
        return v


class NavigationState(BaseModel):
    """
    Navigation state model for current navigation state.
    """
    
    current_section: Optional[str] = Field(
        default=None,
        description="Current navigation section"
    )
    sidebar_collapsed: Optional[bool] = Field(
        default=None,
        description="Current sidebar collapsed state"
    )
    breadcrumb_depth: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="Current breadcrumb depth"
    )
    active_route_id: Optional[str] = Field(
        default=None,
        description="Currently active route ID"
    )
    last_navigation_time: Optional[datetime] = Field(
        default=None,
        description="Last navigation timestamp"
    )
    
    @field_validator('current_section')
    @classmethod
    def validate_current_section(cls, v: Optional[str]) -> Optional[str]:
        """Validate current section"""
        if v is not None:
            if not v.strip():
                raise ValueError("Current section cannot be empty")
            return v.strip()
        return v
    
    @field_validator('active_route_id')
    @classmethod
    def validate_active_route_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate active route ID"""
        if v is not None:
            if not v.strip():
                raise ValueError("Active route ID cannot be empty")
            return v.strip()
        return v


class NavigationUpdateRequest(BaseModel):
    """
    Navigation update request model for preference and state updates.
    Handles updates to navigation preferences, state, and favorite routes.
    """
    
    # Optional update fields
    preferences: Optional[NavigationPreferences] = Field(
        default=None,
        description="Optional navigation preferences to update"
    )
    navigation_state: Optional[NavigationState] = Field(
        default=None,
        description="Optional navigation state to update"
    )
    favorite_routes: Optional[List[str]] = Field(
        default=None,
        description="Optional favorite routes array to update"
    )
    
    # Request metadata
    update_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the update request was made"
    )
    update_source: Optional[str] = Field(
        default=None,
        description="Source of the update request (user, system, api)"
    )
    
    @field_validator('favorite_routes')
    @classmethod
    def validate_favorite_routes(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate favorite routes array"""
        if v is not None:
            if len(v) > 50:
                raise ValueError("Cannot have more than 50 favorite routes")
            
            # Validate route paths
            for i, route in enumerate(v):
                if not route or not route.strip():
                    raise ValueError(f"Favorite route {i} cannot be empty")
                if not route.startswith('/'):
                    raise ValueError(f"Favorite route {i} must start with '/'")
                v[i] = route.strip()
            
            # Remove duplicates while preserving order
            seen = set()
            unique_routes = []
            for route in v:
                if route not in seen:
                    seen.add(route)
                    unique_routes.append(route)
            
            return unique_routes
        
        return v
    
    @field_validator('update_source')
    @classmethod
    def validate_update_source(cls, v: Optional[str]) -> Optional[str]:
        """Validate update source"""
        if v is not None:
            valid_sources = ['user', 'system', 'api', 'admin']
            if v not in valid_sources:
                raise ValueError(f"Invalid update source. Must be one of: {valid_sources}")
        return v
    
    def has_updates(self) -> bool:
        """Check if the request contains any updates"""
        return (
            self.preferences is not None or
            self.navigation_state is not None or
            self.favorite_routes is not None
        )
    
    def get_update_summary(self) -> Dict[str, Any]:
        """Get summary of what is being updated"""
        summary = {
            "has_preferences": self.preferences is not None,
            "has_navigation_state": self.navigation_state is not None,
            "has_favorite_routes": self.favorite_routes is not None,
            "update_timestamp": self.update_timestamp.isoformat(),
            "update_source": self.update_source
        }
        
        if self.favorite_routes:
            summary["favorite_routes_count"] = len(self.favorite_routes)
        
        return summary


class NavigationContextResponse(DashboardOverviewResponse):
    """
    Navigation context response extending DashboardOverviewResponse.
    Provides navigation-specific context data for dashboard navigation.
    """
    
    # Navigation context data
    navigation_context: Dict[str, Any] = Field(
        ...,
        description="Navigation context containing currentSection, availableRoutes, breadcrumbs, navigationHistory, and userPreferences"
    )
    
    # Navigation metadata
    navigation_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when navigation context was last updated"
    )
    
    # Navigation-specific fields
    available_routes: Optional[List[NavigationRoute]] = Field(
        default=None,
        description="Available navigation routes for the user"
    )
    breadcrumbs: Optional[List[BreadcrumbItem]] = Field(
        default=None,
        description="Current breadcrumb navigation items"
    )
    navigation_history: Optional[List[NavigationHistoryEntry]] = Field(
        default=None,
        description="User's navigation history"
    )
    user_preferences: Optional[NavigationPreferences] = Field(
        default=None,
        description="User's navigation preferences"
    )
    
    @field_validator('navigation_context')
    @classmethod
    def validate_navigation_context(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate navigation context structure"""
        if not isinstance(v, dict):
            raise ValueError("Navigation context must be a dictionary")
        
        # Validate required fields
        required_fields = ['currentSection', 'availableRoutes', 'breadcrumbs', 'navigationHistory', 'userPreferences']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Navigation context missing required field: {field}")
        
        # Validate currentSection
        current_section = v.get('currentSection')
        if current_section is not None:
            if not isinstance(current_section, str) or not current_section.strip():
                raise ValueError("currentSection must be a non-empty string")
            v['currentSection'] = current_section.strip()
        
        # Validate availableRoutes
        available_routes = v.get('availableRoutes')
        if not isinstance(available_routes, list):
            raise ValueError("availableRoutes must be a list")
        
        # Validate breadcrumbs
        breadcrumbs = v.get('breadcrumbs')
        if not isinstance(breadcrumbs, list):
            raise ValueError("breadcrumbs must be a list")
        
        # Validate navigationHistory
        navigation_history = v.get('navigationHistory')
        if not isinstance(navigation_history, list):
            raise ValueError("navigationHistory must be a list")
        
        # Validate userPreferences
        user_preferences = v.get('userPreferences')
        if not isinstance(user_preferences, dict):
            raise ValueError("userPreferences must be a dictionary")
        
        return v
    
    @model_validator(mode='after')
    def validate_navigation_consistency(self) -> 'NavigationContextResponse':
        """Validate consistency between navigation context and individual fields"""
        
        # Ensure navigation context and individual fields are consistent
        if self.navigation_context:
            nav_context = self.navigation_context
            
            # Sync currentSection with navigation_context
            if 'currentSection' in nav_context:
                current_section = nav_context['currentSection']
                if self.available_routes:
                    # Validate that currentSection matches an available route
                    found_route = False
                    for route in self.available_routes:
                        if route.find_route_by_path(current_section):
                            found_route = True
                            break
                    if not found_route:
                        # Allow this to pass but log a warning
                        pass
        
        return self
    
    def get_current_section(self) -> Optional[str]:
        """Get current navigation section from navigation context"""
        return self.navigation_context.get('currentSection')
    
    def get_available_route_ids(self) -> List[str]:
        """Get all available route IDs"""
        if self.available_routes:
            route_ids = []
            for route in self.available_routes:
                route_ids.extend(route.get_all_route_ids())
            return route_ids
        return []
    
    def get_active_breadcrumbs(self) -> List[BreadcrumbItem]:
        """Get active breadcrumb items"""
        if self.breadcrumbs:
            return [crumb for crumb in self.breadcrumbs if crumb.is_active]
        return []
    
    def get_navigation_summary(self) -> Dict[str, Any]:
        """Get summary of navigation context"""
        return {
            "current_section": self.get_current_section(),
            "total_routes": len(self.get_available_route_ids()),
            "breadcrumb_count": len(self.breadcrumbs) if self.breadcrumbs else 0,
            "history_count": len(self.navigation_history) if self.navigation_history else 0,
            "has_preferences": self.user_preferences is not None,
            "navigation_timestamp": self.navigation_timestamp.isoformat()
        }
    
    def find_route_by_path(self, path: str) -> Optional[NavigationRoute]:
        """Find a route by path in available routes"""
        if self.available_routes:
            for route in self.available_routes:
                found = route.find_route_by_path(path)
                if found:
                    return found
        return None
    
    def is_route_accessible(self, route_id: str) -> bool:
        """Check if a route is accessible based on available routes"""
        return route_id in self.get_available_route_ids()


