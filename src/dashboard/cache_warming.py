#!/usr/bin/env python3
"""
Dashboard Cache Warming Module
Cache warming strategies for frequently accessed dashboard data to maintain sub-100ms response times
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Union, Callable
from uuid import UUID
from datetime import datetime, timezone, timedelta
from enum import Enum
import time

# Import cache manager and dashboard services
from src.data_layer.cache_manager import cache_manager
from src.dashboard.services import dashboard_service
from src.dashboard.cache_keys import (
    DashboardCacheType,
    WidgetType,
    get_cache_key_ttl
)

# Configure logging
logger = logging.getLogger(__name__)


class WarmingStrategy(str, Enum):
    """Enumeration of cache warming strategies"""
    ON_DEMAND = "on_demand"
    SCHEDULED = "scheduled"
    BACKGROUND = "background"
    USER_TRIGGERED = "user_triggered"
    SYSTEM_STARTUP = "system_startup"


class WarmingPriority(str, Enum):
    """Enumeration of cache warming priorities"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CRITICAL = "critical"


class CacheWarmingTask:
    """
    Individual cache warming task definition.
    """
    
    def __init__(
        self,
        task_id: str,
        cache_type: DashboardCacheType,
        priority: WarmingPriority = WarmingPriority.MEDIUM,
        user_id: Optional[Union[str, UUID]] = None,
        **kwargs
    ):
        self.task_id = task_id
        self.cache_type = cache_type
        self.priority = priority
        self.user_id = user_id
        self.kwargs = kwargs
        self.created_at = datetime.now(timezone.utc)
        self.status = "pending"
        self.error = None
        self.execution_time_ms = None
    
    async def execute(self) -> Dict[str, Any]:
        """
        Execute the cache warming task.
        
        Returns:
            Dict[str, Any]: Task execution results
        """
        start_time = time.time()
        self.status = "running"
        
        try:
            result = await self._warm_cache()
            self.status = "completed"
            self.execution_time_ms = (time.time() - start_time) * 1000
            
            logger.info(f"Cache warming task completed: {self.task_id}")
            return {
                "task_id": self.task_id,
                "status": "completed",
                "execution_time_ms": self.execution_time_ms,
                "result": result
            }
            
        except Exception as e:
            self.status = "failed"
            self.error = str(e)
            self.execution_time_ms = (time.time() - start_time) * 1000
            
            logger.error(f"Cache warming task failed: {self.task_id}, error: {e}")
            return {
                "task_id": self.task_id,
                "status": "failed",
                "error": str(e),
                "execution_time_ms": self.execution_time_ms
            }
    
    async def _warm_cache(self) -> Dict[str, Any]:
        """Execute the actual cache warming based on cache type"""
        if self.cache_type == DashboardCacheType.OVERVIEW:
            if not self.user_id:
                raise ValueError("user_id required for overview cache warming")
            data = await dashboard_service.get_dashboard_overview(self.user_id, force_refresh=True)
            return {"cache_type": "overview", "user_id": str(self.user_id), "data_size": len(str(data.dict()))}
        
        elif self.cache_type == DashboardCacheType.ANALYTICS:
            period = self.kwargs.get("period", "30d")
            filters = self.kwargs.get("filters")
            data = await dashboard_service.get_dashboard_analytics(
                self.user_id, period, filters, force_refresh=True
            )
            return {"cache_type": "analytics", "period": period, "data_size": len(str(data.dict()))}
        
        elif self.cache_type == DashboardCacheType.USER_PREFERENCES:
            if not self.user_id:
                raise ValueError("user_id required for preferences cache warming")
            data = await dashboard_service.get_user_preferences(self.user_id, force_refresh=True)
            return {"cache_type": "preferences", "user_id": str(self.user_id), "data_size": len(str(data.dict()))}
        
        elif self.cache_type == DashboardCacheType.SYSTEM_STATUS:
            data = await dashboard_service.get_system_status()
            return {"cache_type": "system_status", "data_size": len(str(data))}
        
        elif self.cache_type == DashboardCacheType.PERFORMANCE_METRICS:
            period = self.kwargs.get("period", "1h")
            data = await dashboard_service.get_performance_metrics(self.user_id, period)
            return {"cache_type": "performance_metrics", "period": period, "data_size": len(str(data))}
        
        elif self.cache_type == DashboardCacheType.RECENT_ACTIVITY:
            if not self.user_id:
                raise ValueError("user_id required for activity cache warming")
            limit = self.kwargs.get("limit", 10)
            data = await dashboard_service.get_recent_activity(self.user_id, limit)
            return {"cache_type": "recent_activity", "user_id": str(self.user_id), "data_size": len(str(data))}
        
        elif self.cache_type == DashboardCacheType.NOTIFICATIONS:
            if not self.user_id:
                raise ValueError("user_id required for notifications cache warming")
            data = await dashboard_service.get_notifications(self.user_id)
            return {"cache_type": "notifications", "user_id": str(self.user_id), "data_size": len(str(data))}
        
        elif self.cache_type == DashboardCacheType.WIDGET_DATA:
            if not self.user_id:
                raise ValueError("user_id required for widget cache warming")
            widget_type = self.kwargs.get("widget_type")
            if not widget_type:
                raise ValueError("widget_type required for widget cache warming")
            data = await dashboard_service.get_widget_data(self.user_id, widget_type, **self.kwargs)
            return {"cache_type": "widget_data", "widget_type": widget_type.value, "data_size": len(str(data))}
        
        else:
            raise ValueError(f"Unsupported cache type for warming: {self.cache_type}")


class DashboardCacheWarmer:
    """
    Dashboard cache warmer for maintaining sub-100ms response times.
    Implements various warming strategies and manages warming tasks.
    """
    
    def __init__(self):
        self.cache_manager = cache_manager
        self.dashboard_service = dashboard_service
        self._warming_tasks: Dict[str, CacheWarmingTask] = {}
        self._warming_queue: List[CacheWarmingTask] = []
        self._is_running = False
        self._background_task: Optional[asyncio.Task] = None
    
    async def start_background_warming(self) -> None:
        """Start background cache warming process"""
        if self._is_running:
            logger.warning("Background cache warming is already running")
            return
        
        self._is_running = True
        self._background_task = asyncio.create_task(self._background_warming_loop())
        logger.info("Started background cache warming")
    
    async def stop_background_warming(self) -> None:
        """Stop background cache warming process"""
        if not self._is_running:
            return
        
        self._is_running = False
        
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped background cache warming")
    
    async def _background_warming_loop(self) -> None:
        """Background warming loop"""
        while self._is_running:
            try:
                # Process warming queue
                await self._process_warming_queue()
                
                # Schedule periodic warming for critical data
                await self._schedule_periodic_warming()
                
                # Wait before next iteration
                await asyncio.sleep(60)  # Run every minute
                
            except Exception as e:
                logger.error(f"Error in background warming loop: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds on error
    
    async def _process_warming_queue(self) -> None:
        """Process the warming queue"""
        if not self._warming_queue:
            return
        
        # Sort by priority
        priority_order = {
            WarmingPriority.CRITICAL: 0,
            WarmingPriority.HIGH: 1,
            WarmingPriority.MEDIUM: 2,
            WarmingPriority.LOW: 3
        }
        
        self._warming_queue.sort(key=lambda task: priority_order[task.priority])
        
        # Process tasks (limit to 5 concurrent tasks)
        concurrent_tasks = []
        for task in self._warming_queue[:5]:
            concurrent_tasks.append(asyncio.create_task(task.execute()))
            self._warming_queue.remove(task)
        
        if concurrent_tasks:
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Cache warming task failed: {result}")
                else:
                    logger.debug(f"Cache warming task completed: {result}")
    
    async def _schedule_periodic_warming(self) -> None:
        """Schedule periodic warming for critical data"""
        # Warm system status every 5 minutes
        if self._should_warm_system_status():
            await self.warm_system_status()
        
        # Warm global analytics every 15 minutes
        if self._should_warm_global_analytics():
            await self.warm_global_analytics()
    
    def _should_warm_system_status(self) -> bool:
        """Check if system status should be warmed"""
        # Simple time-based check (every 5 minutes)
        return True  # Implement actual time-based logic
    
    def _should_warm_global_analytics(self) -> bool:
        """Check if global analytics should be warmed"""
        # Simple time-based check (every 15 minutes)
        return True  # Implement actual time-based logic
    
    async def warm_user_dashboard(
        self,
        user_id: Union[str, UUID],
        cache_types: Optional[List[DashboardCacheType]] = None,
        priority: WarmingPriority = WarmingPriority.MEDIUM
    ) -> Dict[str, Any]:
        """
        Warm dashboard cache for a specific user.
        
        Args:
            user_id: User identifier
            cache_types: Types of cache to warm (None for all types)
            priority: Warming priority
            
        Returns:
            Dict[str, Any]: Warming results
        """
        if cache_types is None:
            cache_types = [
                DashboardCacheType.OVERVIEW,
                DashboardCacheType.ANALYTICS,
                DashboardCacheType.USER_PREFERENCES,
                DashboardCacheType.RECENT_ACTIVITY,
                DashboardCacheType.NOTIFICATIONS
            ]
        
        results = {}
        
        for cache_type in cache_types:
            task_id = f"user_{user_id}_{cache_type.value}_{int(time.time())}"
            task = CacheWarmingTask(
                task_id=task_id,
                cache_type=cache_type,
                priority=priority,
                user_id=user_id
            )
            
            try:
                result = await task.execute()
                results[cache_type.value] = result
                
            except Exception as e:
                results[cache_type.value] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        logger.info(f"Warmed user dashboard cache for user: {user_id}")
        return results
    
    async def warm_system_status(self) -> Dict[str, Any]:
        """
        Warm system status cache.
        
        Returns:
            Dict[str, Any]: Warming results
        """
        task_id = f"system_status_{int(time.time())}"
        task = CacheWarmingTask(
            task_id=task_id,
            cache_type=DashboardCacheType.SYSTEM_STATUS,
            priority=WarmingPriority.HIGH
        )
        
        result = await task.execute()
        logger.info("Warmed system status cache")
        return result
    
    async def warm_global_analytics(
        self,
        periods: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Warm global analytics cache.
        
        Args:
            periods: Time periods to warm (None for default periods)
            
        Returns:
            Dict[str, Any]: Warming results
        """
        if periods is None:
            periods = ["30d", "7d", "1d"]
        
        results = {}
        
        for period in periods:
            task_id = f"global_analytics_{period}_{int(time.time())}"
            task = CacheWarmingTask(
                task_id=task_id,
                cache_type=DashboardCacheType.ANALYTICS,
                priority=WarmingPriority.MEDIUM,
                period=period
            )
            
            try:
                result = await task.execute()
                results[period] = result
                
            except Exception as e:
                results[period] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        logger.info("Warmed global analytics cache")
        return results
    
    async def warm_performance_metrics(
        self,
        periods: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Warm performance metrics cache.
        
        Args:
            periods: Time periods to warm (None for default periods)
            
        Returns:
            Dict[str, Any]: Warming results
        """
        if periods is None:
            periods = ["1h", "1d", "7d"]
        
        results = {}
        
        for period in periods:
            task_id = f"performance_metrics_{period}_{int(time.time())}"
            task = CacheWarmingTask(
                task_id=task_id,
                cache_type=DashboardCacheType.PERFORMANCE_METRICS,
                priority=WarmingPriority.MEDIUM,
                period=period
            )
            
            try:
                result = await task.execute()
                results[period] = result
                
            except Exception as e:
                results[period] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        logger.info("Warmed performance metrics cache")
        return results
    
    async def warm_widget_data(
        self,
        user_id: Union[str, UUID],
        widget_types: Optional[List[WidgetType]] = None
    ) -> Dict[str, Any]:
        """
        Warm widget data cache for a user.
        
        Args:
            user_id: User identifier
            widget_types: Widget types to warm (None for all types)
            
        Returns:
            Dict[str, Any]: Warming results
        """
        if widget_types is None:
            widget_types = [
                WidgetType.OVERVIEW_STATS,
                WidgetType.ANALYTICS_CHART,
                WidgetType.RECENT_ACTIVITY_FEED,
                WidgetType.SYSTEM_STATUS_PANEL,
                WidgetType.PERFORMANCE_METRICS
            ]
        
        results = {}
        
        for widget_type in widget_types:
            task_id = f"widget_{user_id}_{widget_type.value}_{int(time.time())}"
            task = CacheWarmingTask(
                task_id=task_id,
                cache_type=DashboardCacheType.WIDGET_DATA,
                priority=WarmingPriority.LOW,
                user_id=user_id,
                widget_type=widget_type
            )
            
            try:
                result = await task.execute()
                results[widget_type.value] = result
                
            except Exception as e:
                results[widget_type.value] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        logger.info(f"Warmed widget data cache for user: {user_id}")
        return results
    
    def schedule_warming_task(
        self,
        cache_type: DashboardCacheType,
        priority: WarmingPriority = WarmingPriority.MEDIUM,
        user_id: Optional[Union[str, UUID]] = None,
        **kwargs
    ) -> str:
        """
        Schedule a cache warming task for later execution.
        
        Args:
            cache_type: Type of cache to warm
            priority: Warming priority
            user_id: User identifier (if applicable)
            **kwargs: Additional task parameters
            
        Returns:
            str: Task ID
        """
        task_id = f"{cache_type.value}_{int(time.time())}_{len(self._warming_queue)}"
        
        task = CacheWarmingTask(
            task_id=task_id,
            cache_type=cache_type,
            priority=priority,
            user_id=user_id,
            **kwargs
        )
        
        self._warming_queue.append(task)
        self._warming_tasks[task_id] = task
        
        logger.info(f"Scheduled cache warming task: {task_id}")
        return task_id
    
    async def warm_on_demand(
        self,
        cache_type: DashboardCacheType,
        user_id: Optional[Union[str, UUID]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Warm cache on demand (immediate execution).
        
        Args:
            cache_type: Type of cache to warm
            user_id: User identifier (if applicable)
            **kwargs: Additional parameters
            
        Returns:
            Dict[str, Any]: Warming results
        """
        task_id = f"on_demand_{cache_type.value}_{int(time.time())}"
        task = CacheWarmingTask(
            task_id=task_id,
            cache_type=cache_type,
            priority=WarmingPriority.HIGH,
            user_id=user_id,
            **kwargs
        )
        
        result = await task.execute()
        logger.info(f"Completed on-demand cache warming: {task_id}")
        return result
    
    def get_warming_stats(self) -> Dict[str, Any]:
        """
        Get cache warming statistics.
        
        Returns:
            Dict[str, Any]: Warming statistics
        """
        return {
            "is_running": self._is_running,
            "queue_size": len(self._warming_queue),
            "total_tasks": len(self._warming_tasks),
            "completed_tasks": len([t for t in self._warming_tasks.values() if t.status == "completed"]),
            "failed_tasks": len([t for t in self._warming_tasks.values() if t.status == "failed"]),
            "running_tasks": len([t for t in self._warming_tasks.values() if t.status == "running"]),
            "pending_tasks": len([t for t in self._warming_tasks.values() if t.status == "pending"]),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific warming task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Dict[str, Any] or None: Task status
        """
        task = self._warming_tasks.get(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "cache_type": task.cache_type.value,
            "priority": task.priority.value,
            "status": task.status,
            "user_id": str(task.user_id) if task.user_id else None,
            "created_at": task.created_at.isoformat(),
            "execution_time_ms": task.execution_time_ms,
            "error": task.error
        }


# Global cache warmer instance
cache_warmer = DashboardCacheWarmer()


# Utility functions for cache warming
async def warm_dashboard_cache_on_startup() -> Dict[str, Any]:
    """
    Warm critical dashboard cache on system startup.
    
    Returns:
        Dict[str, Any]: Warming results
    """
    logger.info("Starting dashboard cache warming on system startup")
    
    results = {
        "startup_warming": {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        # Warm system status
        results["startup_warming"]["system_status"] = await cache_warmer.warm_system_status()
        
        # Warm global analytics
        results["startup_warming"]["global_analytics"] = await cache_warmer.warm_global_analytics()
        
        # Warm performance metrics
        results["startup_warming"]["performance_metrics"] = await cache_warmer.warm_performance_metrics()
        
        # Start background warming
        await cache_warmer.start_background_warming()
        
        results["success"] = True
        logger.info("Completed dashboard cache warming on system startup")
        
    except Exception as e:
        results["success"] = False
        results["error"] = str(e)
        logger.error(f"Error in startup cache warming: {e}")
    
    return results


async def warm_user_cache_on_login(user_id: Union[str, UUID]) -> Dict[str, Any]:
    """
    Warm user-specific cache when user logs in.
    
    Args:
        user_id: User identifier
        
    Returns:
        Dict[str, Any]: Warming results
    """
    logger.info(f"Warming user cache on login: {user_id}")
    
    try:
        results = await cache_warmer.warm_user_dashboard(
            user_id=user_id,
            priority=WarmingPriority.HIGH
        )
        
        logger.info(f"Completed user cache warming on login: {user_id}")
        return results
        
    except Exception as e:
        logger.error(f"Error warming user cache on login for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "user_id": str(user_id)
        }


def get_cache_warming_config() -> Dict[str, Any]:
    """
    Get cache warming configuration and recommendations.
    
    Returns:
        Dict[str, Any]: Warming configuration
    """
    return {
        "warming_strategies": {
            "on_demand": {
                "description": "Immediate cache warming for critical data",
                "use_case": "User login, critical operations",
                "priority": "HIGH"
            },
            "scheduled": {
                "description": "Periodic cache warming based on schedule",
                "use_case": "System maintenance, regular updates",
                "priority": "MEDIUM"
            },
            "background": {
                "description": "Continuous background cache warming",
                "use_case": "Maintaining cache freshness",
                "priority": "LOW"
            },
            "user_triggered": {
                "description": "Cache warming triggered by user actions",
                "use_case": "User navigation, preferences changes",
                "priority": "MEDIUM"
            },
            "system_startup": {
                "description": "Cache warming during system initialization",
                "use_case": "System startup, service restart",
                "priority": "CRITICAL"
            }
        },
        "cache_types": {
            cache_type.value: {
                "ttl_seconds": get_cache_key_ttl(cache_type),
                "warming_frequency": "varies",
                "priority": "MEDIUM"
            }
            for cache_type in DashboardCacheType
        },
        "recommendations": {
            "high_priority_warming": [
                "system_status",
                "user_overview",
                "user_preferences"
            ],
            "medium_priority_warming": [
                "analytics",
                "performance_metrics",
                "recent_activity"
            ],
            "low_priority_warming": [
                "widget_data",
                "notifications"
            ]
        },
        "performance_targets": {
            "response_time_ms": 100,
            "cache_hit_rate_percent": 85,
            "warming_success_rate_percent": 95
        }
    }
