#!/usr/bin/env python3
"""
User Preferences Service
Enhanced service for managing user preferences including navigation history
"""

import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import structlog

from src.models.navigation import NavigationPreferences
from src.dependencies.auth import UserClaims
from src.utils.redis_cache import get_dashboard_cache_manager
from src.config.navigation_config import get_navigation_config

logger = structlog.get_logger(__name__)


class UserPreferencesService:
    """
    Enhanced user preferences service for navigation history management
    """
    
    def __init__(self):
        """Initialize user preferences service"""
        self.config = get_navigation_config()
        self._cache_manager = None
        self._preferences_cache: Dict[str, NavigationPreferences] = {}
        
        logger.info("UserPreferencesService initialized")
    
    async def _get_cache_manager(self):
        """Get Redis cache manager"""
        if self._cache_manager is None:
            self._cache_manager = await get_dashboard_cache_manager()
        return self._cache_manager
    
    async def get_user_preferences(
        self, 
        user_id: str, 
        user_claims: Optional[UserClaims] = None
    ) -> Optional[NavigationPreferences]:
        """
        Get user navigation preferences with enhanced caching
        
        Args:
            user_id: User identifier
            user_claims: User authentication claims
            
        Returns:
            User navigation preferences or None
        """
        try:
            # Check in-memory cache first
            if user_id in self._preferences_cache:
                logger.debug("User preferences retrieved from memory cache", user_id=user_id)
                return self._preferences_cache[user_id]
            
            # Get from Redis cache
            cache_manager = await self._get_cache_manager()
            cached_prefs = await cache_manager.get_user_preferences(user_id)
            
            if cached_prefs:
                # Parse and cache in memory
                prefs = NavigationPreferences.parse_obj(cached_prefs)
                self._preferences_cache[user_id] = prefs
                logger.debug("User preferences retrieved from Redis cache", user_id=user_id)
                return prefs
            
            # Create default preferences if none exist
            default_prefs = NavigationPreferences(user_id=user_id)
            
            # Cache default preferences
            await cache_manager.set_user_preferences(user_id, default_prefs)
            self._preferences_cache[user_id] = default_prefs
            
            logger.info("Default user preferences created", user_id=user_id)
            return default_prefs
            
        except Exception as e:
            logger.error("Failed to get user preferences", user_id=user_id, error=str(e))
            return None
    
    async def update_user_preferences(
        self, 
        user_id: str, 
        preferences: NavigationPreferences
    ) -> bool:
        """
        Update user navigation preferences with enhanced persistence
        
        Args:
            user_id: User identifier
            preferences: Updated preferences
            
        Returns:
            True if successful, False otherwise
        """
        try:
            preferences.last_updated = datetime.now(timezone.utc)
            
            # Update Redis cache
            cache_manager = await self._get_cache_manager()
            await cache_manager.set_user_preferences(user_id, preferences)
            
            # Update in-memory cache
            self._preferences_cache[user_id] = preferences
            
            logger.info("User preferences updated successfully", user_id=user_id)
            return True
            
        except Exception as e:
            logger.error("Failed to update user preferences", user_id=user_id, error=str(e))
            return False
    
    async def add_navigation_history_item(
        self, 
        user_id: str, 
        route_path: str, 
        route_title: str
    ) -> bool:
        """
        Add a navigation history item to user preferences
        
        Args:
            user_id: User identifier
            route_path: Route path navigated to
            route_title: Route title
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current preferences
            preferences = await self.get_user_preferences(user_id)
            if not preferences:
                logger.warning("Could not get user preferences for history update", user_id=user_id)
                return False
            
            # Add to recent items (keep last 20)
            if route_path not in preferences.recent_items:
                preferences.recent_items.insert(0, route_path)
                preferences.recent_items = preferences.recent_items[:20]
            else:
                # Move to front if already exists
                preferences.recent_items.remove(route_path)
                preferences.recent_items.insert(0, route_path)
                preferences.recent_items = preferences.recent_items[:20]
            
            # Update preferences
            success = await self.update_user_preferences(user_id, preferences)
            
            if success:
                logger.debug(
                    "Navigation history item added",
                    user_id=user_id,
                    route_path=route_path,
                    recent_items_count=len(preferences.recent_items)
                )
            
            return success
            
        except Exception as e:
            logger.error("Failed to add navigation history item", user_id=user_id, error=str(e))
            return False
    
    async def add_favorite_item(
        self, 
        user_id: str, 
        item_id: str
    ) -> bool:
        """
        Add a navigation item to user favorites
        
        Args:
            user_id: User identifier
            item_id: Navigation item ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            preferences = await self.get_user_preferences(user_id)
            if not preferences:
                return False
            
            if item_id not in preferences.favorite_items:
                preferences.favorite_items.append(item_id)
                success = await self.update_user_preferences(user_id, preferences)
                
                if success:
                    logger.debug("Favorite item added", user_id=user_id, item_id=item_id)
                
                return success
            
            return True  # Already in favorites
            
        except Exception as e:
            logger.error("Failed to add favorite item", user_id=user_id, error=str(e))
            return False
    
    async def remove_favorite_item(
        self, 
        user_id: str, 
        item_id: str
    ) -> bool:
        """
        Remove a navigation item from user favorites
        
        Args:
            user_id: User identifier
            item_id: Navigation item ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            preferences = await self.get_user_preferences(user_id)
            if not preferences:
                return False
            
            if item_id in preferences.favorite_items:
                preferences.favorite_items.remove(item_id)
                success = await self.update_user_preferences(user_id, preferences)
                
                if success:
                    logger.debug("Favorite item removed", user_id=user_id, item_id=item_id)
                
                return success
            
            return True  # Not in favorites
            
        except Exception as e:
            logger.error("Failed to remove favorite item", user_id=user_id, error=str(e))
            return False
    
    async def update_navigation_preferences(
        self, 
        user_id: str, 
        sidebar_collapsed: Optional[bool] = None,
        sidebar_width: Optional[int] = None,
        show_breadcrumbs: Optional[bool] = None,
        show_page_titles: Optional[bool] = None,
        navigation_style: Optional[str] = None
    ) -> bool:
        """
        Update specific navigation preferences
        
        Args:
            user_id: User identifier
            sidebar_collapsed: Whether sidebar is collapsed
            sidebar_width: Sidebar width in pixels
            show_breadcrumbs: Whether to show breadcrumbs
            show_page_titles: Whether to show page titles
            navigation_style: Navigation style preference
            
        Returns:
            True if successful, False otherwise
        """
        try:
            preferences = await self.get_user_preferences(user_id)
            if not preferences:
                return False
            
            # Update only provided fields
            if sidebar_collapsed is not None:
                preferences.sidebar_collapsed = sidebar_collapsed
            if sidebar_width is not None:
                preferences.sidebar_width = sidebar_width
            if show_breadcrumbs is not None:
                preferences.show_breadcrumbs = show_breadcrumbs
            if show_page_titles is not None:
                preferences.show_page_titles = show_page_titles
            if navigation_style is not None:
                preferences.navigation_style = navigation_style
            
            success = await self.update_user_preferences(user_id, preferences)
            
            if success:
                logger.info("Navigation preferences updated", user_id=user_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to update navigation preferences", user_id=user_id, error=str(e))
            return False
    
    async def get_navigation_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get navigation statistics for user
        
        Args:
            user_id: User identifier
            
        Returns:
            Navigation statistics
        """
        try:
            preferences = await self.get_user_preferences(user_id)
            if not preferences:
                return {}
            
            # Calculate statistics
            stats = {
                "total_favorite_items": len(preferences.favorite_items),
                "total_recent_items": len(preferences.recent_items),
                "sidebar_collapsed": preferences.sidebar_collapsed,
                "sidebar_width": preferences.sidebar_width,
                "show_breadcrumbs": preferences.show_breadcrumbs,
                "show_page_titles": preferences.show_page_titles,
                "navigation_style": preferences.navigation_style,
                "last_updated": preferences.last_updated.isoformat(),
                "preferences_age_days": (datetime.now(timezone.utc) - preferences.last_updated).days
            }
            
            # Add recent items analysis
            if preferences.recent_items:
                stats["most_recent_item"] = preferences.recent_items[0]
                stats["recent_items_unique_count"] = len(set(preferences.recent_items))
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get navigation statistics", user_id=user_id, error=str(e))
            return {}
    
    async def clear_navigation_history(self, user_id: str) -> bool:
        """
        Clear user navigation history
        
        Args:
            user_id: User identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            preferences = await self.get_user_preferences(user_id)
            if not preferences:
                return False
            
            preferences.recent_items = []
            success = await self.update_user_preferences(user_id, preferences)
            
            if success:
                logger.info("Navigation history cleared", user_id=user_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to clear navigation history", user_id=user_id, error=str(e))
            return False
    
    async def export_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Export user preferences for backup or migration
        
        Args:
            user_id: User identifier
            
        Returns:
            Exported preferences data
        """
        try:
            preferences = await self.get_user_preferences(user_id)
            if not preferences:
                return {}
            
            export_data = {
                "user_id": user_id,
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "preferences": preferences.dict(),
                "statistics": await self.get_navigation_statistics(user_id)
            }
            
            logger.info("User preferences exported", user_id=user_id)
            return export_data
            
        except Exception as e:
            logger.error("Failed to export user preferences", user_id=user_id, error=str(e))
            return {}
    
    async def import_user_preferences(
        self, 
        user_id: str, 
        preferences_data: Dict[str, Any]
    ) -> bool:
        """
        Import user preferences from backup or migration
        
        Args:
            user_id: User identifier
            preferences_data: Preferences data to import
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if "preferences" not in preferences_data:
                logger.error("Invalid preferences data format", user_id=user_id)
                return False
            
            # Parse preferences
            preferences = NavigationPreferences.parse_obj(preferences_data["preferences"])
            preferences.user_id = user_id  # Ensure correct user ID
            preferences.last_updated = datetime.now(timezone.utc)
            
            # Update preferences
            success = await self.update_user_preferences(user_id, preferences)
            
            if success:
                logger.info("User preferences imported successfully", user_id=user_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to import user preferences", user_id=user_id, error=str(e))
            return False


# Singleton instance
_user_preferences_service: Optional[UserPreferencesService] = None


async def get_user_preferences_service() -> UserPreferencesService:
    """Get user preferences service singleton"""
    global _user_preferences_service
    if _user_preferences_service is None:
        _user_preferences_service = UserPreferencesService()
    return _user_preferences_service
