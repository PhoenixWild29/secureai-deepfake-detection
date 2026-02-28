#!/usr/bin/env python3
"""
Dashboard Cache Invalidation Module
Cache invalidation strategies for Core Detection Engine data changes to maintain data consistency
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Union, Callable
from uuid import UUID
from datetime import datetime, timezone
from enum import Enum

# Import cache manager and cache keys
from src.data_layer.cache_manager import cache_manager
from src.dashboard.cache_keys import (
    DashboardCacheType,
    get_user_cache_pattern,
    get_analytics_cache_pattern,
    get_widget_cache_pattern,
    get_cache_key_pattern
)

# Configure logging
logger = logging.getLogger(__name__)


class InvalidationTrigger(str, Enum):
    """Enumeration of cache invalidation triggers"""
    DETECTION_RESULT_CREATED = "detection_result_created"
    DETECTION_RESULT_UPDATED = "detection_result_updated"
    DETECTION_RESULT_DELETED = "detection_result_deleted"
    USER_ANALYSIS_COMPLETED = "user_analysis_completed"
    SYSTEM_STATUS_CHANGED = "system_status_changed"
    PERFORMANCE_METRICS_UPDATED = "performance_metrics_updated"
    USER_PREFERENCES_CHANGED = "user_preferences_changed"
    NOTIFICATION_CREATED = "notification_created"
    NOTIFICATION_READ = "notification_read"
    BATCH_ANALYSIS_COMPLETED = "batch_analysis_completed"
    MODEL_VERSION_UPDATED = "model_version_updated"
    TRAINING_DATA_EXPORTED = "training_data_exported"


class CacheInvalidationStrategy:
    """
    Cache invalidation strategy for maintaining data consistency.
    Handles invalidation patterns based on Core Detection Engine data changes.
    """
    
    def __init__(self):
        self.cache_manager = cache_manager
        self._invalidation_handlers: Dict[InvalidationTrigger, List[Callable]] = {}
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default invalidation handlers for common triggers"""
        self._invalidation_handlers = {
            InvalidationTrigger.DETECTION_RESULT_CREATED: [
                self._invalidate_user_overview_cache,
                self._invalidate_user_analytics_cache,
                self._invalidate_user_recent_activity_cache,
                self._invalidate_global_analytics_cache
            ],
            InvalidationTrigger.DETECTION_RESULT_UPDATED: [
                self._invalidate_user_overview_cache,
                self._invalidate_user_analytics_cache,
                self._invalidate_user_recent_activity_cache,
                self._invalidate_global_analytics_cache
            ],
            InvalidationTrigger.DETECTION_RESULT_DELETED: [
                self._invalidate_user_overview_cache,
                self._invalidate_user_analytics_cache,
                self._invalidate_user_recent_activity_cache,
                self._invalidate_global_analytics_cache
            ],
            InvalidationTrigger.USER_ANALYSIS_COMPLETED: [
                self._invalidate_user_overview_cache,
                self._invalidate_user_analytics_cache,
                self._invalidate_user_recent_activity_cache,
                self._invalidate_user_performance_metrics_cache
            ],
            InvalidationTrigger.SYSTEM_STATUS_CHANGED: [
                self._invalidate_system_status_cache,
                self._invalidate_global_overview_cache
            ],
            InvalidationTrigger.PERFORMANCE_METRICS_UPDATED: [
                self._invalidate_performance_metrics_cache,
                self._invalidate_global_analytics_cache
            ],
            InvalidationTrigger.USER_PREFERENCES_CHANGED: [
                self._invalidate_user_preferences_cache,
                self._invalidate_user_widget_cache
            ],
            InvalidationTrigger.NOTIFICATION_CREATED: [
                self._invalidate_user_notifications_cache,
                self._invalidate_user_overview_cache
            ],
            InvalidationTrigger.NOTIFICATION_READ: [
                self._invalidate_user_notifications_cache,
                self._invalidate_user_overview_cache
            ],
            InvalidationTrigger.BATCH_ANALYSIS_COMPLETED: [
                self._invalidate_global_analytics_cache,
                self._invalidate_performance_metrics_cache,
                self._invalidate_system_status_cache
            ],
            InvalidationTrigger.MODEL_VERSION_UPDATED: [
                self._invalidate_global_analytics_cache,
                self._invalidate_performance_metrics_cache,
                self._invalidate_system_status_cache
            ],
            InvalidationTrigger.TRAINING_DATA_EXPORTED: [
                self._invalidate_global_analytics_cache,
                self._invalidate_performance_metrics_cache
            ]
        }
    
    async def invalidate_cache(
        self,
        trigger: InvalidationTrigger,
        user_id: Optional[Union[str, UUID]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Invalidate cache based on trigger and context.
        
        Args:
            trigger: Type of invalidation trigger
            user_id: User identifier (if applicable)
            **kwargs: Additional context for invalidation
            
        Returns:
            Dict[str, Any]: Results of invalidation operations
        """
        logger.info(f"Cache invalidation triggered: {trigger.value}, user_id: {user_id}")
        
        results = {
            "trigger": trigger.value,
            "user_id": str(user_id) if user_id else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "invalidations": {}
        }
        
        try:
            # Get handlers for this trigger
            handlers = self._invalidation_handlers.get(trigger, [])
            
            if not handlers:
                logger.warning(f"No invalidation handlers found for trigger: {trigger.value}")
                results["error"] = f"No handlers for trigger: {trigger.value}"
                return results
            
            # Execute handlers
            for handler in handlers:
                try:
                    handler_result = await handler(user_id, **kwargs)
                    handler_name = handler.__name__
                    results["invalidations"][handler_name] = handler_result
                    
                except Exception as e:
                    handler_name = handler.__name__
                    logger.error(f"Error in invalidation handler {handler_name}: {e}")
                    results["invalidations"][handler_name] = {"error": str(e)}
            
            # Calculate summary
            total_invalidated = sum(
                inv.get("invalidated_count", 0) 
                for inv in results["invalidations"].values() 
                if isinstance(inv, dict) and "invalidated_count" in inv
            )
            results["total_invalidated"] = total_invalidated
            results["success"] = total_invalidated > 0
            
            logger.info(f"Cache invalidation completed: {total_invalidated} keys invalidated")
            
        except Exception as e:
            logger.error(f"Error in cache invalidation: {e}")
            results["error"] = str(e)
            results["success"] = False
        
        return results
    
    # Individual invalidation handlers
    async def _invalidate_user_overview_cache(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Invalidate user-specific overview cache"""
        if not user_id:
            return {"error": "user_id required for user overview invalidation"}
        
        try:
            pattern = get_cache_key_pattern(
                cache_type=DashboardCacheType.OVERVIEW,
                user_id=user_id
            )
            invalidated_count = await self.cache_manager.invalidate_pattern_async(pattern)
            
            return {
                "pattern": pattern,
                "invalidated_count": invalidated_count,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error invalidating user overview cache: {e}")
            return {"error": str(e), "success": False}
    
    async def _invalidate_user_analytics_cache(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Invalidate user-specific analytics cache"""
        if not user_id:
            return {"error": "user_id required for user analytics invalidation"}
        
        try:
            pattern = get_cache_key_pattern(
                cache_type=DashboardCacheType.ANALYTICS,
                user_id=user_id
            )
            invalidated_count = await self.cache_manager.invalidate_pattern_async(pattern)
            
            return {
                "pattern": pattern,
                "invalidated_count": invalidated_count,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error invalidating user analytics cache: {e}")
            return {"error": str(e), "success": False}
    
    async def _invalidate_user_recent_activity_cache(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Invalidate user-specific recent activity cache"""
        if not user_id:
            return {"error": "user_id required for user activity invalidation"}
        
        try:
            pattern = get_cache_key_pattern(
                cache_type=DashboardCacheType.RECENT_ACTIVITY,
                user_id=user_id
            )
            invalidated_count = await self.cache_manager.invalidate_pattern_async(pattern)
            
            return {
                "pattern": pattern,
                "invalidated_count": invalidated_count,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error invalidating user activity cache: {e}")
            return {"error": str(e), "success": False}
    
    async def _invalidate_user_performance_metrics_cache(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Invalidate user-specific performance metrics cache"""
        if not user_id:
            return {"error": "user_id required for user performance metrics invalidation"}
        
        try:
            pattern = get_cache_key_pattern(
                cache_type=DashboardCacheType.PERFORMANCE_METRICS,
                user_id=user_id
            )
            invalidated_count = await self.cache_manager.invalidate_pattern_async(pattern)
            
            return {
                "pattern": pattern,
                "invalidated_count": invalidated_count,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error invalidating user performance metrics cache: {e}")
            return {"error": str(e), "success": False}
    
    async def _invalidate_user_preferences_cache(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Invalidate user-specific preferences cache"""
        if not user_id:
            return {"error": "user_id required for user preferences invalidation"}
        
        try:
            pattern = get_cache_key_pattern(
                cache_type=DashboardCacheType.USER_PREFERENCES,
                user_id=user_id
            )
            invalidated_count = await self.cache_manager.invalidate_pattern_async(pattern)
            
            return {
                "pattern": pattern,
                "invalidated_count": invalidated_count,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error invalidating user preferences cache: {e}")
            return {"error": str(e), "success": False}
    
    async def _invalidate_user_widget_cache(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Invalidate user-specific widget cache"""
        if not user_id:
            return {"error": "user_id required for user widget invalidation"}
        
        try:
            pattern = get_cache_key_pattern(
                cache_type=DashboardCacheType.WIDGET_DATA,
                user_id=user_id
            )
            invalidated_count = await self.cache_manager.invalidate_pattern_async(pattern)
            
            return {
                "pattern": pattern,
                "invalidated_count": invalidated_count,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error invalidating user widget cache: {e}")
            return {"error": str(e), "success": False}
    
    async def _invalidate_user_notifications_cache(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Invalidate user-specific notifications cache"""
        if not user_id:
            return {"error": "user_id required for user notifications invalidation"}
        
        try:
            pattern = get_cache_key_pattern(
                cache_type=DashboardCacheType.NOTIFICATIONS,
                user_id=user_id
            )
            invalidated_count = await self.cache_manager.invalidate_pattern_async(pattern)
            
            return {
                "pattern": pattern,
                "invalidated_count": invalidated_count,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error invalidating user notifications cache: {e}")
            return {"error": str(e), "success": False}
    
    async def _invalidate_global_analytics_cache(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Invalidate global analytics cache"""
        try:
            pattern = get_analytics_cache_pattern()
            invalidated_count = await self.cache_manager.invalidate_pattern_async(pattern)
            
            return {
                "pattern": pattern,
                "invalidated_count": invalidated_count,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error invalidating global analytics cache: {e}")
            return {"error": str(e), "success": False}
    
    async def _invalidate_performance_metrics_cache(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Invalidate performance metrics cache"""
        try:
            pattern = get_cache_key_pattern(
                cache_type=DashboardCacheType.PERFORMANCE_METRICS
            )
            invalidated_count = await self.cache_manager.invalidate_pattern_async(pattern)
            
            return {
                "pattern": pattern,
                "invalidated_count": invalidated_count,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error invalidating performance metrics cache: {e}")
            return {"error": str(e), "success": False}
    
    async def _invalidate_system_status_cache(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Invalidate system status cache"""
        try:
            pattern = get_cache_key_pattern(
                cache_type=DashboardCacheType.SYSTEM_STATUS
            )
            invalidated_count = await self.cache_manager.invalidate_pattern_async(pattern)
            
            return {
                "pattern": pattern,
                "invalidated_count": invalidated_count,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error invalidating system status cache: {e}")
            return {"error": str(e), "success": False}
    
    async def _invalidate_global_overview_cache(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Invalidate global overview cache"""
        try:
            pattern = get_cache_key_pattern(
                cache_type=DashboardCacheType.OVERVIEW
            )
            invalidated_count = await self.cache_manager.invalidate_pattern_async(pattern)
            
            return {
                "pattern": pattern,
                "invalidated_count": invalidated_count,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error invalidating global overview cache: {e}")
            return {"error": str(e), "success": False}
    
    def add_custom_handler(
        self,
        trigger: InvalidationTrigger,
        handler: Callable
    ) -> None:
        """
        Add custom invalidation handler for a trigger.
        
        Args:
            trigger: Invalidation trigger
            handler: Custom handler function
        """
        if trigger not in self._invalidation_handlers:
            self._invalidation_handlers[trigger] = []
        
        self._invalidation_handlers[trigger].append(handler)
        logger.info(f"Added custom handler for trigger: {trigger.value}")
    
    def remove_custom_handler(
        self,
        trigger: InvalidationTrigger,
        handler: Callable
    ) -> bool:
        """
        Remove custom invalidation handler for a trigger.
        
        Args:
            trigger: Invalidation trigger
            handler: Handler function to remove
            
        Returns:
            bool: True if removed, False if not found
        """
        if trigger in self._invalidation_handlers:
            try:
                self._invalidation_handlers[trigger].remove(handler)
                logger.info(f"Removed custom handler for trigger: {trigger.value}")
                return True
            except ValueError:
                return False
        return False


class CoreDetectionEngineCacheInvalidator:
    """
    Cache invalidator specifically for Core Detection Engine data changes.
    Provides integration points for detection results, model updates, and system changes.
    """
    
    def __init__(self):
        self.strategy = CacheInvalidationStrategy()
    
    async def on_detection_result_created(
        self,
        user_id: Union[str, UUID],
        detection_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle cache invalidation when a new detection result is created.
        
        Args:
            user_id: User who created the detection result
            detection_result: Detection result data
            
        Returns:
            Dict[str, Any]: Invalidation results
        """
        return await self.strategy.invalidate_cache(
            InvalidationTrigger.DETECTION_RESULT_CREATED,
            user_id=user_id,
            detection_result=detection_result
        )
    
    async def on_detection_result_updated(
        self,
        user_id: Union[str, UUID],
        detection_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle cache invalidation when a detection result is updated.
        
        Args:
            user_id: User who updated the detection result
            detection_result: Updated detection result data
            
        Returns:
            Dict[str, Any]: Invalidation results
        """
        return await self.strategy.invalidate_cache(
            InvalidationTrigger.DETECTION_RESULT_UPDATED,
            user_id=user_id,
            detection_result=detection_result
        )
    
    async def on_detection_result_deleted(
        self,
        user_id: Union[str, UUID],
        detection_result_id: str
    ) -> Dict[str, Any]:
        """
        Handle cache invalidation when a detection result is deleted.
        
        Args:
            user_id: User who deleted the detection result
            detection_result_id: ID of deleted detection result
            
        Returns:
            Dict[str, Any]: Invalidation results
        """
        return await self.strategy.invalidate_cache(
            InvalidationTrigger.DETECTION_RESULT_DELETED,
            user_id=user_id,
            detection_result_id=detection_result_id
        )
    
    async def on_user_analysis_completed(
        self,
        user_id: Union[str, UUID],
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle cache invalidation when a user analysis is completed.
        
        Args:
            user_id: User who completed the analysis
            analysis_data: Analysis completion data
            
        Returns:
            Dict[str, Any]: Invalidation results
        """
        return await self.strategy.invalidate_cache(
            InvalidationTrigger.USER_ANALYSIS_COMPLETED,
            user_id=user_id,
            analysis_data=analysis_data
        )
    
    async def on_system_status_changed(
        self,
        status_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle cache invalidation when system status changes.
        
        Args:
            status_data: System status change data
            
        Returns:
            Dict[str, Any]: Invalidation results
        """
        return await self.strategy.invalidate_cache(
            InvalidationTrigger.SYSTEM_STATUS_CHANGED,
            status_data=status_data
        )
    
    async def on_performance_metrics_updated(
        self,
        metrics_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle cache invalidation when performance metrics are updated.
        
        Args:
            metrics_data: Performance metrics data
            
        Returns:
            Dict[str, Any]: Invalidation results
        """
        return await self.strategy.invalidate_cache(
            InvalidationTrigger.PERFORMANCE_METRICS_UPDATED,
            metrics_data=metrics_data
        )
    
    async def on_user_preferences_changed(
        self,
        user_id: Union[str, UUID],
        preferences_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle cache invalidation when user preferences change.
        
        Args:
            user_id: User whose preferences changed
            preferences_data: Updated preferences data
            
        Returns:
            Dict[str, Any]: Invalidation results
        """
        return await self.strategy.invalidate_cache(
            InvalidationTrigger.USER_PREFERENCES_CHANGED,
            user_id=user_id,
            preferences_data=preferences_data
        )
    
    async def on_notification_created(
        self,
        user_id: Union[str, UUID],
        notification_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle cache invalidation when a notification is created.
        
        Args:
            user_id: User who received the notification
            notification_data: Notification data
            
        Returns:
            Dict[str, Any]: Invalidation results
        """
        return await self.strategy.invalidate_cache(
            InvalidationTrigger.NOTIFICATION_CREATED,
            user_id=user_id,
            notification_data=notification_data
        )
    
    async def on_batch_analysis_completed(
        self,
        batch_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle cache invalidation when a batch analysis is completed.
        
        Args:
            batch_data: Batch analysis completion data
            
        Returns:
            Dict[str, Any]: Invalidation results
        """
        return await self.strategy.invalidate_cache(
            InvalidationTrigger.BATCH_ANALYSIS_COMPLETED,
            batch_data=batch_data
        )
    
    async def on_model_version_updated(
        self,
        model_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle cache invalidation when a model version is updated.
        
        Args:
            model_data: Model version update data
            
        Returns:
            Dict[str, Any]: Invalidation results
        """
        return await self.strategy.invalidate_cache(
            InvalidationTrigger.MODEL_VERSION_UPDATED,
            model_data=model_data
        )


# Global cache invalidator instance
cache_invalidator = CoreDetectionEngineCacheInvalidator()


# Utility functions for cache invalidation
async def invalidate_all_dashboard_cache() -> Dict[str, Any]:
    """
    Invalidate all dashboard cache entries.
    
    Returns:
        Dict[str, Any]: Results of invalidation operations
    """
    try:
        # Invalidate all dashboard-related cache keys
        dashboard_patterns = [
            "dash:*",
            "user:*",
            "analytics:*",
            "system:*",
            "widget:*",
            "metrics:*",
            "prefs:*",
            "notif:*",
            "perf:*",
            "activity:*"
        ]
        
        results = {}
        total_invalidated = 0
        
        for pattern in dashboard_patterns:
            invalidated_count = await cache_manager.invalidate_pattern_async(pattern)
            results[pattern] = invalidated_count
            total_invalidated += invalidated_count
        
        logger.info(f"Invalidated all dashboard cache: {total_invalidated} keys")
        
        return {
            "success": True,
            "total_invalidated": total_invalidated,
            "patterns": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error invalidating all dashboard cache: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def invalidate_user_dashboard_cache(user_id: Union[str, UUID]) -> Dict[str, Any]:
    """
    Invalidate all dashboard cache for a specific user.
    
    Args:
        user_id: User identifier
        
    Returns:
        Dict[str, Any]: Results of invalidation operations
    """
    try:
        pattern = get_user_cache_pattern(user_id)
        invalidated_count = await cache_manager.invalidate_pattern_async(pattern)
        
        logger.info(f"Invalidated user dashboard cache: {invalidated_count} keys for user {user_id}")
        
        return {
            "success": True,
            "user_id": str(user_id),
            "invalidated_count": invalidated_count,
            "pattern": pattern,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error invalidating user dashboard cache for user {user_id}: {e}")
        return {
            "success": False,
            "user_id": str(user_id),
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def get_invalidation_stats() -> Dict[str, Any]:
    """
    Get cache invalidation statistics and configuration.
    
    Returns:
        Dict[str, Any]: Invalidation statistics
    """
    try:
        return {
            "invalidation_triggers": {
                trigger.value: {
                    "handlers_count": len(handlers),
                    "handler_names": [handler.__name__ for handler in handlers]
                }
                for trigger, handlers in cache_invalidator.strategy._invalidation_handlers.items()
            },
            "total_triggers": len(cache_invalidator.strategy._invalidation_handlers),
            "cache_manager_status": cache_manager.health_check(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting invalidation stats: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
