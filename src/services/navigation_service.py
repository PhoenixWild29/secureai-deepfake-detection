#!/usr/bin/env python3
"""
Navigation Service
Service for managing navigation context, user preferences, and role-based filtering
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
import structlog

from src.models.navigation import (
    NavigationState,
    NavigationSection,
    NavigationItem,
    NavigationItemType,
    NavigationPermission,
    CurrentRouteContext,
    NavigationPreferences,
    BreadcrumbItem,
    NavigationCacheKey,
    NavigationAnalytics
)
from src.dependencies.auth import UserClaims
from src.utils.redis_cache import get_dashboard_cache_manager
from src.config.navigation_config import get_navigation_config

logger = structlog.get_logger(__name__)


class NavigationService:
    """
    Navigation service for managing navigation context and user preferences
    """
    
    def __init__(self):
        """Initialize navigation service"""
        self.config = get_navigation_config()
        self._cache_manager = None
        self._navigation_sections_cache: Dict[str, List[NavigationSection]] = {}
        self._user_preferences_cache: Dict[str, NavigationPreferences] = {}
        
        logger.info("NavigationService initialized")
    
    async def _get_cache_manager(self):
        """Get Redis cache manager"""
        if self._cache_manager is None:
            self._cache_manager = await get_dashboard_cache_manager()
        return self._cache_manager
    
    def _get_default_navigation_sections(self) -> List[NavigationSection]:
        """Get default navigation sections"""
        return [
            NavigationSection(
                id="dashboard",
                label="Dashboard",
                icon="home",
                description="Main dashboard overview",
                order=1,
                required_permission=None,
                metadata=None,
                items=[
                    NavigationItem(
                        id="overview",
                        label="Overview",
                        path="/dashboard",
                        type=NavigationItemType.PAGE,
                        icon="home",
                        description="Dashboard overview",
                        required_permission=NavigationPermission.READ,
                        badge=None,
                        metadata=None
                    ),
                    NavigationItem(
                        id="analytics",
                        label="Analytics",
                        path="/dashboard/analytics",
                        type=NavigationItemType.PAGE,
                        icon="bar-chart",
                        description="Analytics and insights",
                        required_permission=NavigationPermission.READ,
                        badge=None,
                        metadata=None
                    )
                ]
            ),
            NavigationSection(
                id="analysis",
                label="Analysis",
                icon="search",
                description="Video analysis tools",
                order=2,
                required_permission=None,
                metadata=None,
                items=[
                    NavigationItem(
                        id="upload",
                        label="Upload Video",
                        path="/dashboard/upload",
                        type=NavigationItemType.PAGE,
                        icon="upload",
                        description="Upload video for analysis",
                        required_permission=NavigationPermission.WRITE,
                        badge=None,
                        metadata=None
                    ),
                    NavigationItem(
                        id="batch-analysis",
                        label="Batch Analysis",
                        path="/dashboard/batch",
                        type=NavigationItemType.PAGE,
                        icon="layers",
                        description="Batch video analysis",
                        required_permission=NavigationPermission.WRITE,
                        badge=None,
                        metadata=None
                    ),
                    NavigationItem(
                        id="analysis-history",
                        label="Analysis History",
                        path="/dashboard/history",
                        type=NavigationItemType.PAGE,
                        icon="history",
                        description="View analysis history",
                        required_permission=NavigationPermission.READ,
                        badge=None,
                        metadata=None
                    )
                ]
            ),
            NavigationSection(
                id="results",
                label="Results",
                icon="file-text",
                description="Analysis results and reports",
                order=3,
                required_permission=None,
                metadata=None,
                items=[
                    NavigationItem(
                        id="recent-results",
                        label="Recent Results",
                        path="/dashboard/results/recent",
                        type=NavigationItemType.PAGE,
                        icon="clock",
                        description="Recent analysis results",
                        required_permission=NavigationPermission.READ,
                        badge=None,
                        metadata=None
                    ),
                    NavigationItem(
                        id="export-results",
                        label="Export Results",
                        path="/dashboard/results/export",
                        type=NavigationItemType.PAGE,
                        icon="download",
                        description="Export analysis results",
                        required_permission=NavigationPermission.READ,
                        badge=None,
                        metadata=None
                    )
                ]
            ),
            NavigationSection(
                id="blockchain",
                label="Blockchain",
                icon="link",
                description="Blockchain verification",
                order=4,
                required_permission=None,
                metadata=None,
                items=[
                    NavigationItem(
                        id="verification",
                        label="Verification",
                        path="/dashboard/blockchain/verification",
                        type=NavigationItemType.PAGE,
                        icon="shield-check",
                        description="Blockchain verification status",
                        required_permission=NavigationPermission.READ,
                        badge=None,
                        metadata=None
                    ),
                    NavigationItem(
                        id="transactions",
                        label="Transactions",
                        path="/dashboard/blockchain/transactions",
                        type=NavigationItemType.PAGE,
                        icon="receipt",
                        description="Blockchain transaction history",
                        required_permission=NavigationPermission.READ,
                        badge=None,
                        metadata=None
                    )
                ]
            ),
            NavigationSection(
                id="settings",
                label="Settings",
                icon="settings",
                description="System and user settings",
                order=5,
                required_permission=None,
                metadata=None,
                items=[
                    NavigationItem(
                        id="user-preferences",
                        label="User Preferences",
                        path="/dashboard/settings/preferences",
                        type=NavigationItemType.PAGE,
                        icon="user",
                        description="User preferences and settings",
                        required_permission=NavigationPermission.READ,
                        badge=None,
                        metadata=None
                    ),
                    NavigationItem(
                        id="notifications",
                        label="Notifications",
                        path="/dashboard/settings/notifications",
                        type=NavigationItemType.PAGE,
                        icon="bell",
                        description="Notification preferences",
                        required_permission=NavigationPermission.READ,
                        badge=None,
                        metadata=None
                    ),
                    NavigationItem(
                        id="system-config",
                        label="System Configuration",
                        path="/dashboard/settings/system",
                        type=NavigationItemType.PAGE,
                        icon="cog",
                        description="System configuration",
                        required_permission=NavigationPermission.ADMIN,
                        required_roles=["admin", "system_admin"],
                        badge=None,
                        metadata=None
                    )
                ]
            )
        ]
    
    def _filter_navigation_by_permissions(
        self, 
        sections: List[NavigationSection], 
        user_claims: Optional[UserClaims]
    ) -> List[NavigationSection]:
        """Filter navigation sections based on user permissions"""
        if not user_claims:
            # Return only public sections for unauthenticated users
            return [
                section for section in sections 
                if not section.required_permission or section.required_permission == NavigationPermission.READ
            ]
        
        filtered_sections = []
        user_roles = set(user_claims.roles or [])
        
        for section in sections:
            # Check section-level permissions
            if self._has_permission(section, user_roles):
                # Filter section items
                filtered_items = []
                for item in section.items:
                    if self._has_permission(item, user_roles):
                        # Filter child items
                        if item.children:
                            filtered_children = [
                                child for child in item.children 
                                if self._has_permission(child, user_roles)
                            ]
                            item.children = filtered_children
                        filtered_items.append(item)
                
                # Create filtered section
                filtered_section = section.copy()
                filtered_section.items = filtered_items
                filtered_sections.append(filtered_section)
        
        return filtered_sections
    
    def _has_permission(self, item: Any, user_roles: set) -> bool:
        """Check if user has permission for navigation item"""
        # If no permission required, allow access
        if not hasattr(item, 'required_permission') or not item.required_permission:
            return True
        
        # Check role-based permissions
        if hasattr(item, 'required_roles') and item.required_roles:
            if not any(role in user_roles for role in item.required_roles):
                return False
        
        # Check permission level
        permission_levels = {
            NavigationPermission.READ: 1,
            NavigationPermission.WRITE: 2,
            NavigationPermission.ADMIN: 3,
            NavigationPermission.SYSTEM_ADMIN: 4
        }
        
        required_level = permission_levels.get(item.required_permission, 1)
        
        # Map user roles to permission levels
        user_permission_level = 1  # Default read level
        if "admin" in user_roles or "system_admin" in user_roles:
            user_permission_level = 4
        elif "analyst" in user_roles:
            user_permission_level = 2
        elif "viewer" in user_roles:
            user_permission_level = 1
        
        return user_permission_level >= required_level
    
    def _build_breadcrumbs(self, current_path: str, sections: List[NavigationSection]) -> List[BreadcrumbItem]:
        """Build breadcrumb navigation for current path"""
        breadcrumbs = []
        
        # Add home breadcrumb
        breadcrumbs.append(BreadcrumbItem(
            label="Home",
            path="/dashboard",
            is_active=current_path == "/dashboard",
            icon=None,
            metadata=None
        ))
        
        # Find matching navigation items
        for section in sections:
            for item in section.items:
                if self._matches_path(current_path, item.path):
                    breadcrumbs.append(BreadcrumbItem(
                        label=section.label,
                        path=f"/dashboard#{section.id}",
                        is_active=False,
                        icon=None,
                        metadata=None
                    ))
                    breadcrumbs.append(BreadcrumbItem(
                        label=item.label,
                        path=item.path,
                        is_active=True,
                        icon=None,
                        metadata=None
                    ))
                    break
        
        return breadcrumbs
    
    def _matches_path(self, current_path: str, item_path: str) -> bool:
        """Check if current path matches navigation item path"""
        # Exact match
        if current_path == item_path:
            return True
        
        # Check if current path starts with item path (for nested routes)
        if current_path.startswith(item_path + "/"):
            return True
        
        return False
    
    async def get_navigation_context(
        self, 
        current_path: str,
        user_claims: Optional[UserClaims] = None,
        force_refresh: bool = False
    ) -> NavigationState:
        """
        Get complete navigation context for current route
        
        Args:
            current_path: Current route path
            user_claims: User authentication claims
            force_refresh: Force refresh from cache
            
        Returns:
            Complete navigation state
        """
        start_time = time.time()
        user_id = user_claims.user_id if user_claims else "anonymous"
        
        logger.info(
            "Getting navigation context",
            user_id=user_id,
            current_path=current_path,
            force_refresh=force_refresh
        )
        
        try:
            # Check cache first
            if not force_refresh:
                cached_state = await self._get_cached_navigation_state(user_id, current_path)
                if cached_state:
                    logger.debug("Navigation context retrieved from cache", user_id=user_id)
                    return cached_state
            
            # Get user preferences
            user_preferences = await self.get_user_preferences(user_id, user_claims)
            
            # Get filtered navigation sections
            all_sections = self._get_default_navigation_sections()
            filtered_sections = self._filter_navigation_by_permissions(all_sections, user_claims)
            
            # Build current route context
            current_context = CurrentRouteContext(
                path=current_path,
                section_id=self._get_section_id_for_path(current_path, filtered_sections),
                page_id=self._get_page_id_for_path(current_path, filtered_sections),
                breadcrumbs=self._build_breadcrumbs(current_path, filtered_sections),
                page_title=self._get_page_title_for_path(current_path, filtered_sections),
                page_description=self._get_page_description_for_path(current_path, filtered_sections)
            )
            
            # Get quick actions and recent navigation
            quick_actions = await self._get_quick_actions(user_claims)
            recent_navigation = await self._get_recent_navigation(user_id)
            suggested_items = await self._get_suggested_items(user_id, current_path)
            
            # Get notifications count
            notifications_count = await self._get_notifications_count(user_id)
            
            # Build navigation state
            navigation_state = NavigationState(
                current_context=current_context,
                available_sections=filtered_sections,
                user_preferences=user_preferences,
                quick_actions=quick_actions,
                recent_navigation=recent_navigation,
                suggested_items=suggested_items,
                notifications_count=notifications_count
            )
            
            # Cache the result
            await self._cache_navigation_state(user_id, current_path, navigation_state)
            
            response_time = (time.time() - start_time) * 1000
            logger.info(
                "Navigation context retrieved successfully",
                user_id=user_id,
                response_time_ms=response_time,
                sections_count=len(filtered_sections)
            )
            
            return navigation_state
            
        except Exception as e:
            logger.error(
                "Failed to get navigation context",
                user_id=user_id,
                error=str(e)
            )
            raise
    
    async def get_user_preferences(
        self, 
        user_id: str, 
        user_claims: Optional[UserClaims] = None
    ) -> Optional[NavigationPreferences]:
        """Get user navigation preferences"""
        try:
            # Check cache first
            if user_id in self._user_preferences_cache:
                return self._user_preferences_cache[user_id]
            
            # Get from database or create default
            cache_manager = await self._get_cache_manager()
            cache_key = f"nav_prefs:{user_id}"
            
            cached_prefs = await cache_manager.get_user_preferences(user_id)
            if cached_prefs:
                prefs = NavigationPreferences.parse_obj(cached_prefs)
                self._user_preferences_cache[user_id] = prefs
                return prefs
            
            # Create default preferences
            default_prefs = NavigationPreferences(user_id=user_id)
            
            # Cache default preferences
            await cache_manager.set_user_preferences(user_id, default_prefs)
            
            self._user_preferences_cache[user_id] = default_prefs
            return default_prefs
            
        except Exception as e:
            logger.error("Failed to get user preferences", user_id=user_id, error=str(e))
            return None
    
    async def update_user_preferences(
        self, 
        user_id: str, 
        preferences: NavigationPreferences
    ) -> bool:
        """Update user navigation preferences"""
        try:
            preferences.last_updated = datetime.now(timezone.utc)
            
            # Update cache
            cache_manager = await self._get_cache_manager()
            
            await cache_manager.set_user_preferences(user_id, preferences)
            
            # Update in-memory cache
            self._user_preferences_cache[user_id] = preferences
            
            # Invalidate navigation state cache
            await self._invalidate_navigation_cache(user_id)
            
            logger.info("User preferences updated", user_id=user_id)
            return True
            
        except Exception as e:
            logger.error("Failed to update user preferences", user_id=user_id, error=str(e))
            return False
    
    async def _get_cached_navigation_state(
        self, 
        user_id: str, 
        current_path: str
    ) -> Optional[NavigationState]:
        """Get cached navigation state"""
        try:
            cache_manager = await self._get_cache_manager()
            cache_key = NavigationCacheKey(
                user_id=user_id,
                route_path=current_path,
                user_roles=[]  # Would be populated from user claims
            )
            
            cached_data = await cache_manager.get_navigation_context(cache_key)
            if cached_data:
                return cached_data
            
            return None
            
        except Exception as e:
            logger.error("Failed to get cached navigation state", error=str(e))
            return None
    
    async def _cache_navigation_state(
        self, 
        user_id: str, 
        current_path: str, 
        state: NavigationState
    ):
        """Cache navigation state"""
        try:
            cache_manager = await self._get_cache_manager()
            cache_key = NavigationCacheKey(
                user_id=user_id,
                route_path=current_path,
                user_roles=[]  # Would be populated from user claims
            )
            
            await cache_manager.set_navigation_context(cache_key, state)
            
        except Exception as e:
            logger.error("Failed to cache navigation state", error=str(e))
    
    async def _invalidate_navigation_cache(self, user_id: str):
        """Invalidate navigation cache for user"""
        try:
            cache_manager = await self._get_cache_manager()
            await cache_manager.invalidate_navigation_cache(user_id)
            
        except Exception as e:
            logger.error("Failed to invalidate navigation cache", error=str(e))
    
    def _get_section_id_for_path(self, path: str, sections: List[NavigationSection]) -> Optional[str]:
        """Get section ID for current path"""
        for section in sections:
            for item in section.items:
                if self._matches_path(path, item.path):
                    return section.id
        return None
    
    def _get_page_id_for_path(self, path: str, sections: List[NavigationSection]) -> Optional[str]:
        """Get page ID for current path"""
        for section in sections:
            for item in section.items:
                if self._matches_path(path, item.path):
                    return item.id
        return None
    
    def _get_page_title_for_path(self, path: str, sections: List[NavigationSection]) -> Optional[str]:
        """Get page title for current path"""
        for section in sections:
            for item in section.items:
                if self._matches_path(path, item.path):
                    return item.label
        return None
    
    def _get_page_description_for_path(self, path: str, sections: List[NavigationSection]) -> Optional[str]:
        """Get page description for current path"""
        for section in sections:
            for item in section.items:
                if self._matches_path(path, item.path):
                    return item.description
        return None
    
    async def _get_quick_actions(self, user_claims: Optional[UserClaims]) -> List[NavigationItem]:
        """Get quick action items"""
        quick_actions = [
            NavigationItem(
                id="quick-upload",
                label="Quick Upload",
                path="/dashboard/upload",
                type=NavigationItemType.PAGE,
                icon="upload",
                description="Quick upload action",
                required_permission=NavigationPermission.WRITE,
                badge=None,
                metadata=None
            ),
            NavigationItem(
                id="quick-analytics",
                label="Analytics",
                path="/dashboard/analytics",
                type=NavigationItemType.PAGE,
                icon="bar-chart",
                description="Quick analytics access",
                required_permission=NavigationPermission.READ,
                badge=None,
                metadata=None
            )
        ]
        
        # Filter by permissions
        if user_claims:
            user_roles = set(user_claims.roles or [])
            return [action for action in quick_actions if self._has_permission(action, user_roles)]
        
        return [action for action in quick_actions if not action.required_permission]
    
    async def _get_recent_navigation(self, user_id: str) -> List[NavigationItem]:
        """Get recent navigation items"""
        # This would typically fetch from user activity logs
        # For now, return empty list
        return []
    
    async def _get_suggested_items(self, user_id: str, current_path: str) -> List[NavigationItem]:
        """Get suggested navigation items"""
        # This would typically use ML to suggest items based on user behavior
        # For now, return empty list
        return []
    
    async def _get_notifications_count(self, user_id: str) -> int:
        """Get unread notifications count"""
        try:
            # This would integrate with the notification service
            # For now, return 0
            return 0
        except Exception as e:
            logger.error("Failed to get notifications count", error=str(e))
            return 0
    
    # Navigation History Management Methods (NEW)
    async def track_navigation_event(
        self, 
        user_id: str, 
        route_path: str, 
        route_title: str,
        user_claims: Optional[UserClaims] = None
    ) -> bool:
        """
        Track a navigation event for history and analytics
        
        Args:
            user_id: User identifier
            route_path: Route path navigated to
            route_title: Route title/name
            user_claims: User authentication claims
            
        Returns:
            True if tracking was successful
        """
        try:
            cache_manager = await self._get_cache_manager()
            
            # Get current navigation history
            history = await self.get_navigation_history(user_id)
            
            # Add new navigation event
            navigation_event = {
                "route_path": route_path,
                "route_title": route_title,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_agent": "dashboard",  # Could be enhanced with actual user agent
                "session_id": f"session_{user_id}_{int(time.time())}"  # Simple session ID
            }
            
            # Add to history (keep last 50 entries)
            history.insert(0, navigation_event)
            history = history[:50]  # Keep only last 50 entries
            
            # Update user preferences with navigation history
            preferences = await self.get_user_preferences(user_id, user_claims)
            if preferences:
                preferences.recent_items = [event["route_path"] for event in history[:10]]
                await self.update_user_preferences(user_id, preferences)
            
            # Cache navigation history
            await cache_manager.set_prefetch_data(
                "navigation_history",
                user_id,
                {"history": history, "last_updated": datetime.now(timezone.utc).isoformat()},
                ttl_seconds=self.config.navigation.cache_ttl_seconds
            )
            
            logger.debug(
                "Navigation event tracked",
                user_id=user_id,
                route_path=route_path,
                history_length=len(history)
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to track navigation event", user_id=user_id, error=str(e))
            return False
    
    async def get_navigation_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get user navigation history
        
        Args:
            user_id: User identifier
            
        Returns:
            List of navigation history entries
        """
        try:
            cache_manager = await self._get_cache_manager()
            
            # Try to get from cache first
            cached_data = await cache_manager.get_prefetch_data("navigation_history", user_id)
            if cached_data and "history" in cached_data:
                return cached_data["history"]
            
            # Get from user preferences as fallback
            preferences = await self.get_user_preferences(user_id)
            if preferences and preferences.recent_items:
                # Convert recent items to history format
                history = []
                for i, route_path in enumerate(preferences.recent_items):
                    history.append({
                        "route_path": route_path,
                        "route_title": self._get_route_title(route_path),
                        "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=i)).isoformat(),
                        "user_agent": "dashboard",
                        "session_id": f"session_{user_id}"
                    })
                return history
            
            return []
            
        except Exception as e:
            logger.error("Failed to get navigation history", user_id=user_id, error=str(e))
            return []
    
    async def get_navigation_patterns(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze user navigation patterns
        
        Args:
            user_id: User identifier
            
        Returns:
            Navigation patterns analysis
        """
        try:
            history = await self.get_navigation_history(user_id)
            
            if not history:
                return {
                    "most_visited_routes": [],
                    "navigation_frequency": {},
                    "average_session_duration": 0,
                    "common_navigation_paths": []
                }
            
            # Analyze patterns
            route_counts = {}
            route_times = {}
            
            for event in history:
                route = event["route_path"]
                route_counts[route] = route_counts.get(route, 0) + 1
                
                # Track time spent (simplified)
                timestamp = datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
                route_times[route] = route_times.get(route, 0) + 1  # Simplified time tracking
            
            # Get most visited routes
            most_visited = sorted(route_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Calculate common navigation paths
            common_paths = self._analyze_navigation_paths(history)
            
            patterns = {
                "most_visited_routes": [{"route": route, "count": count} for route, count in most_visited],
                "navigation_frequency": route_counts,
                "average_session_duration": len(history) * 2,  # Simplified calculation
                "common_navigation_paths": common_paths,
                "total_navigation_events": len(history),
                "last_analyzed": datetime.now(timezone.utc).isoformat()
            }
            
            return patterns
            
        except Exception as e:
            logger.error("Failed to analyze navigation patterns", user_id=user_id, error=str(e))
            return {}
    
    def _get_route_title(self, route_path: str) -> str:
        """Get route title from path"""
        # Simple mapping of routes to titles
        route_titles = {
            "/dashboard": "Dashboard Overview",
            "/dashboard/analytics": "Analytics",
            "/dashboard/upload": "Upload Video",
            "/dashboard/history": "Analysis History",
            "/dashboard/results": "Results",
            "/dashboard/blockchain": "Blockchain",
            "/dashboard/settings": "Settings"
        }
        
        return route_titles.get(route_path, route_path.replace("/", " ").title())
    
    def _analyze_navigation_paths(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze common navigation paths"""
        if len(history) < 2:
            return []
        
        # Find common sequences
        sequences = {}
        for i in range(len(history) - 1):
            current_route = history[i]["route_path"]
            next_route = history[i + 1]["route_path"]
            sequence = f"{current_route} -> {next_route}"
            sequences[sequence] = sequences.get(sequence, 0) + 1
        
        # Return top 3 most common sequences
        common_sequences = sorted(sequences.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return [
            {"path": sequence, "frequency": count} 
            for sequence, count in common_sequences
        ]
    
    async def get_enhanced_navigation_context(
        self, 
        current_path: str,
        user_claims: Optional[UserClaims] = None,
        include_history: bool = True,
        include_patterns: bool = True,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Get enhanced navigation context with history and patterns
        
        Args:
            current_path: Current route path
            user_claims: User authentication claims
            include_history: Include navigation history
            include_patterns: Include navigation patterns
            force_refresh: Force refresh from cache
            
        Returns:
            Enhanced navigation context
        """
        try:
            user_id = user_claims.user_id if user_claims else "anonymous"
            
            # Get basic navigation context
            navigation_state = await self.get_navigation_context(
                current_path=current_path,
                user_claims=user_claims,
                force_refresh=force_refresh
            )
            
            enhanced_context = {
                "navigation_state": navigation_state,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id
            }
            
            # Add navigation history if requested
            if include_history and user_id != "anonymous":
                history = await self.get_navigation_history(user_id)
                enhanced_context["navigation_history"] = history
                
                # Track current navigation event
                await self.track_navigation_event(
                    user_id=user_id,
                    route_path=current_path,
                    route_title=navigation_state.current_context.page_title or "Unknown",
                    user_claims=user_claims
                )
            
            # Add navigation patterns if requested
            if include_patterns and user_id != "anonymous":
                patterns = await self.get_navigation_patterns(user_id)
                enhanced_context["navigation_patterns"] = patterns
            
            logger.info(
                "Enhanced navigation context retrieved",
                user_id=user_id,
                current_path=current_path,
                include_history=include_history,
                include_patterns=include_patterns
            )
            
            return enhanced_context
            
        except Exception as e:
            logger.error(
                "Failed to get enhanced navigation context",
                user_id=user_id if 'user_id' in locals() else "unknown",
                error=str(e)
            )
            raise


# Singleton instance
_navigation_service: Optional[NavigationService] = None


async def get_navigation_service() -> NavigationService:
    """Get navigation service singleton"""
    global _navigation_service
    if _navigation_service is None:
        _navigation_service = NavigationService()
    return _navigation_service
