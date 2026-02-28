#!/usr/bin/env python3
"""
Core Detection Engine Cache Integration
Integration points for cache invalidation with Core Detection Engine data updates
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Union, List
from uuid import UUID
from datetime import datetime, timezone

# Import cache invalidation and metrics
from src.dashboard.cache_invalidation import cache_invalidator, InvalidationTrigger
from src.monitoring.cache_metrics import record_dashboard_cache_operation, DashboardCacheType

# Configure logging
logger = logging.getLogger(__name__)


class DetectionEngineCacheIntegration:
    """
    Integration layer between Core Detection Engine and dashboard cache system.
    Handles cache invalidation when detection data changes.
    """
    
    def __init__(self):
        self.cache_invalidator = cache_invalidator
        self._integration_enabled = True
    
    def enable_integration(self) -> None:
        """Enable cache invalidation integration"""
        self._integration_enabled = True
        logger.info("Core Detection Engine cache integration enabled")
    
    def disable_integration(self) -> None:
        """Disable cache invalidation integration"""
        self._integration_enabled = False
        logger.info("Core Detection Engine cache integration disabled")
    
    async def on_detection_completed(
        self,
        detection_id: Union[str, UUID],
        user_id: Optional[Union[str, UUID]],
        detection_result: Dict[str, Any],
        processing_time_ms: int
    ) -> None:
        """
        Handle cache invalidation when a detection is completed.
        
        Args:
            detection_id: Unique detection identifier
            user_id: User who initiated the detection
            detection_result: Detection result data
            processing_time_ms: Processing time in milliseconds
        """
        if not self._integration_enabled:
            return
        
        try:
            logger.info(f"Processing detection completion: {detection_id}")
            
            # Record cache operation metrics
            record_dashboard_cache_operation(
                operation="detection_completed",
                cache_type=DashboardCacheType.OVERVIEW,
                user_id=user_id,
                response_time_ms=processing_time_ms,
                success=True,
                detection_id=str(detection_id)
            )
            
            # Invalidate user-specific caches
            if user_id:
                invalidation_result = await self.cache_invalidator.on_detection_result_created(
                    user_id=user_id,
                    detection_result={
                        "detection_id": str(detection_id),
                        "result": detection_result,
                        "processing_time_ms": processing_time_ms,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                
                logger.info(f"Cache invalidation completed for user {user_id}: {invalidation_result.get('total_invalidated', 0)} keys")
            
            # Invalidate global analytics cache
            global_invalidation_result = await self.cache_invalidator.on_user_analysis_completed(
                user_id=user_id or "anonymous",
                analysis_data={
                    "detection_id": str(detection_id),
                    "result": detection_result,
                    "processing_time_ms": processing_time_ms,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            
            logger.info(f"Global cache invalidation completed: {global_invalidation_result.get('total_invalidated', 0)} keys")
            
        except Exception as e:
            logger.error(f"Error in detection completion cache integration: {e}")
            # Record error metrics
            record_dashboard_cache_operation(
                operation="detection_completed",
                cache_type=DashboardCacheType.OVERVIEW,
                user_id=user_id,
                response_time_ms=processing_time_ms,
                success=False,
                error=str(e)
            )
    
    async def on_detection_updated(
        self,
        detection_id: Union[str, UUID],
        user_id: Optional[Union[str, UUID]],
        updated_result: Dict[str, Any]
    ) -> None:
        """
        Handle cache invalidation when a detection result is updated.
        
        Args:
            detection_id: Unique detection identifier
            user_id: User who owns the detection
            updated_result: Updated detection result data
        """
        if not self._integration_enabled:
            return
        
        try:
            logger.info(f"Processing detection update: {detection_id}")
            
            # Record cache operation metrics
            record_dashboard_cache_operation(
                operation="detection_updated",
                cache_type=DashboardCacheType.OVERVIEW,
                user_id=user_id,
                success=True,
                detection_id=str(detection_id)
            )
            
            # Invalidate user-specific caches
            if user_id:
                invalidation_result = await self.cache_invalidator.on_detection_result_updated(
                    user_id=user_id,
                    detection_result={
                        "detection_id": str(detection_id),
                        "result": updated_result,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                
                logger.info(f"Cache invalidation completed for user {user_id}: {invalidation_result.get('total_invalidated', 0)} keys")
            
        except Exception as e:
            logger.error(f"Error in detection update cache integration: {e}")
            record_dashboard_cache_operation(
                operation="detection_updated",
                cache_type=DashboardCacheType.OVERVIEW,
                user_id=user_id,
                success=False,
                error=str(e)
            )
    
    async def on_detection_deleted(
        self,
        detection_id: Union[str, UUID],
        user_id: Optional[Union[str, UUID]]
    ) -> None:
        """
        Handle cache invalidation when a detection result is deleted.
        
        Args:
            detection_id: Unique detection identifier
            user_id: User who owns the detection
        """
        if not self._integration_enabled:
            return
        
        try:
            logger.info(f"Processing detection deletion: {detection_id}")
            
            # Record cache operation metrics
            record_dashboard_cache_operation(
                operation="detection_deleted",
                cache_type=DashboardCacheType.OVERVIEW,
                user_id=user_id,
                success=True,
                detection_id=str(detection_id)
            )
            
            # Invalidate user-specific caches
            if user_id:
                invalidation_result = await self.cache_invalidator.on_detection_result_deleted(
                    user_id=user_id,
                    detection_result_id=str(detection_id)
                )
                
                logger.info(f"Cache invalidation completed for user {user_id}: {invalidation_result.get('total_invalidated', 0)} keys")
            
        except Exception as e:
            logger.error(f"Error in detection deletion cache integration: {e}")
            record_dashboard_cache_operation(
                operation="detection_deleted",
                cache_type=DashboardCacheType.OVERVIEW,
                user_id=user_id,
                success=False,
                error=str(e)
            )
    
    async def on_batch_analysis_completed(
        self,
        batch_id: Union[str, UUID],
        batch_results: List[Dict[str, Any]],
        total_processing_time_ms: int
    ) -> None:
        """
        Handle cache invalidation when a batch analysis is completed.
        
        Args:
            batch_id: Unique batch identifier
            batch_results: List of batch analysis results
            total_processing_time_ms: Total processing time for the batch
        """
        if not self._integration_enabled:
            return
        
        try:
            logger.info(f"Processing batch analysis completion: {batch_id}")
            
            # Record cache operation metrics
            record_dashboard_cache_operation(
                operation="batch_completed",
                cache_type=DashboardCacheType.ANALYTICS,
                response_time_ms=total_processing_time_ms,
                success=True,
                batch_id=str(batch_id),
                results_count=len(batch_results)
            )
            
            # Invalidate global analytics and performance metrics
            invalidation_result = await self.cache_invalidator.on_batch_analysis_completed(
                batch_data={
                    "batch_id": str(batch_id),
                    "results": batch_results,
                    "total_processing_time_ms": total_processing_time_ms,
                    "results_count": len(batch_results),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            
            logger.info(f"Batch cache invalidation completed: {invalidation_result.get('total_invalidated', 0)} keys")
            
        except Exception as e:
            logger.error(f"Error in batch analysis completion cache integration: {e}")
            record_dashboard_cache_operation(
                operation="batch_completed",
                cache_type=DashboardCacheType.ANALYTICS,
                response_time_ms=total_processing_time_ms,
                success=False,
                error=str(e)
            )
    
    async def on_system_status_changed(
        self,
        status_data: Dict[str, Any]
    ) -> None:
        """
        Handle cache invalidation when system status changes.
        
        Args:
            status_data: System status change data
        """
        if not self._integration_enabled:
            return
        
        try:
            logger.info("Processing system status change")
            
            # Record cache operation metrics
            record_dashboard_cache_operation(
                operation="system_status_changed",
                cache_type=DashboardCacheType.SYSTEM_STATUS,
                success=True,
                status_data=status_data
            )
            
            # Invalidate system status and global overview caches
            invalidation_result = await self.cache_invalidator.on_system_status_changed(status_data)
            
            logger.info(f"System status cache invalidation completed: {invalidation_result.get('total_invalidated', 0)} keys")
            
        except Exception as e:
            logger.error(f"Error in system status change cache integration: {e}")
            record_dashboard_cache_operation(
                operation="system_status_changed",
                cache_type=DashboardCacheType.SYSTEM_STATUS,
                success=False,
                error=str(e)
            )
    
    async def on_performance_metrics_updated(
        self,
        metrics_data: Dict[str, Any]
    ) -> None:
        """
        Handle cache invalidation when performance metrics are updated.
        
        Args:
            metrics_data: Performance metrics data
        """
        if not self._integration_enabled:
            return
        
        try:
            logger.info("Processing performance metrics update")
            
            # Record cache operation metrics
            record_dashboard_cache_operation(
                operation="metrics_updated",
                cache_type=DashboardCacheType.PERFORMANCE_METRICS,
                success=True,
                metrics_data=metrics_data
            )
            
            # Invalidate performance metrics and global analytics caches
            invalidation_result = await self.cache_invalidator.on_performance_metrics_updated(metrics_data)
            
            logger.info(f"Performance metrics cache invalidation completed: {invalidation_result.get('total_invalidated', 0)} keys")
            
        except Exception as e:
            logger.error(f"Error in performance metrics update cache integration: {e}")
            record_dashboard_cache_operation(
                operation="metrics_updated",
                cache_type=DashboardCacheType.PERFORMANCE_METRICS,
                success=False,
                error=str(e)
            )
    
    async def on_user_preferences_changed(
        self,
        user_id: Union[str, UUID],
        preferences_data: Dict[str, Any]
    ) -> None:
        """
        Handle cache invalidation when user preferences change.
        
        Args:
            user_id: User identifier
            preferences_data: Updated preferences data
        """
        if not self._integration_enabled:
            return
        
        try:
            logger.info(f"Processing user preferences change: {user_id}")
            
            # Record cache operation metrics
            record_dashboard_cache_operation(
                operation="preferences_changed",
                cache_type=DashboardCacheType.USER_PREFERENCES,
                user_id=user_id,
                success=True,
                preferences_data=preferences_data
            )
            
            # Invalidate user preferences and widget caches
            invalidation_result = await self.cache_invalidator.on_user_preferences_changed(
                user_id=user_id,
                preferences_data=preferences_data
            )
            
            logger.info(f"User preferences cache invalidation completed for user {user_id}: {invalidation_result.get('total_invalidated', 0)} keys")
            
        except Exception as e:
            logger.error(f"Error in user preferences change cache integration: {e}")
            record_dashboard_cache_operation(
                operation="preferences_changed",
                cache_type=DashboardCacheType.USER_PREFERENCES,
                user_id=user_id,
                success=False,
                error=str(e)
            )
    
    async def on_notification_created(
        self,
        user_id: Union[str, UUID],
        notification_data: Dict[str, Any]
    ) -> None:
        """
        Handle cache invalidation when a notification is created.
        
        Args:
            user_id: User identifier
            notification_data: Notification data
        """
        if not self._integration_enabled:
            return
        
        try:
            logger.info(f"Processing notification creation: {user_id}")
            
            # Record cache operation metrics
            record_dashboard_cache_operation(
                operation="notification_created",
                cache_type=DashboardCacheType.NOTIFICATIONS,
                user_id=user_id,
                success=True,
                notification_data=notification_data
            )
            
            # Invalidate user notifications and overview caches
            invalidation_result = await self.cache_invalidator.on_notification_created(
                user_id=user_id,
                notification_data=notification_data
            )
            
            logger.info(f"Notification cache invalidation completed for user {user_id}: {invalidation_result.get('total_invalidated', 0)} keys")
            
        except Exception as e:
            logger.error(f"Error in notification creation cache integration: {e}")
            record_dashboard_cache_operation(
                operation="notification_created",
                cache_type=DashboardCacheType.NOTIFICATIONS,
                user_id=user_id,
                success=False,
                error=str(e)
            )
    
    async def on_model_version_updated(
        self,
        model_data: Dict[str, Any]
    ) -> None:
        """
        Handle cache invalidation when a model version is updated.
        
        Args:
            model_data: Model version update data
        """
        if not self._integration_enabled:
            return
        
        try:
            logger.info("Processing model version update")
            
            # Record cache operation metrics
            record_dashboard_cache_operation(
                operation="model_updated",
                cache_type=DashboardCacheType.SYSTEM_STATUS,
                success=True,
                model_data=model_data
            )
            
            # Invalidate global analytics, performance metrics, and system status caches
            invalidation_result = await self.cache_invalidator.on_model_version_updated(model_data)
            
            logger.info(f"Model version cache invalidation completed: {invalidation_result.get('total_invalidated', 0)} keys")
            
        except Exception as e:
            logger.error(f"Error in model version update cache integration: {e}")
            record_dashboard_cache_operation(
                operation="model_updated",
                cache_type=DashboardCacheType.SYSTEM_STATUS,
                success=False,
                error=str(e)
            )


# Global integration instance
detection_cache_integration = DetectionEngineCacheIntegration()


# Decorator for automatic cache invalidation
def with_cache_invalidation(operation_type: str):
    """
    Decorator to automatically handle cache invalidation for detection operations.
    
    Args:
        operation_type: Type of operation (detection_completed, detection_updated, etc.)
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            # Execute the original function
            result = await func(*args, **kwargs)
            
            # Handle cache invalidation based on operation type
            try:
                if operation_type == "detection_completed":
                    detection_id = kwargs.get("detection_id") or result.get("id")
                    user_id = kwargs.get("user_id")
                    detection_result = result
                    processing_time_ms = kwargs.get("processing_time_ms", 0)
                    
                    await detection_cache_integration.on_detection_completed(
                        detection_id=detection_id,
                        user_id=user_id,
                        detection_result=detection_result,
                        processing_time_ms=processing_time_ms
                    )
                
                elif operation_type == "detection_updated":
                    detection_id = kwargs.get("detection_id")
                    user_id = kwargs.get("user_id")
                    updated_result = result
                    
                    if detection_id and user_id:
                        await detection_cache_integration.on_detection_updated(
                            detection_id=detection_id,
                            user_id=user_id,
                            updated_result=updated_result
                        )
                
                elif operation_type == "batch_completed":
                    batch_id = kwargs.get("batch_id")
                    batch_results = result.get("results", [])
                    total_processing_time_ms = kwargs.get("total_processing_time_ms", 0)
                    
                    if batch_id:
                        await detection_cache_integration.on_batch_analysis_completed(
                            batch_id=batch_id,
                            batch_results=batch_results,
                            total_processing_time_ms=total_processing_time_ms
                        )
                
            except Exception as e:
                logger.error(f"Error in cache invalidation decorator: {e}")
            
            return result
        
        def sync_wrapper(*args, **kwargs):
            # Execute the original function
            result = func(*args, **kwargs)
            
            # Handle cache invalidation asynchronously
            try:
                if operation_type == "detection_completed":
                    detection_id = kwargs.get("detection_id") or result.get("id")
                    user_id = kwargs.get("user_id")
                    detection_result = result
                    processing_time_ms = kwargs.get("processing_time_ms", 0)
                    
                    # Schedule async cache invalidation
                    asyncio.create_task(
                        detection_cache_integration.on_detection_completed(
                            detection_id=detection_id,
                            user_id=user_id,
                            detection_result=detection_result,
                            processing_time_ms=processing_time_ms
                        )
                    )
                
            except Exception as e:
                logger.error(f"Error in cache invalidation decorator: {e}")
            
            return result
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Utility functions for integration
async def initialize_detection_cache_integration() -> Dict[str, Any]:
    """
    Initialize the detection cache integration.
    
    Returns:
        Dict[str, Any]: Initialization results
    """
    try:
        detection_cache_integration.enable_integration()
        
        return {
            "success": True,
            "message": "Detection cache integration initialized",
            "integration_enabled": detection_cache_integration._integration_enabled,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error initializing detection cache integration: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def get_integration_status() -> Dict[str, Any]:
    """
    Get the current status of detection cache integration.
    
    Returns:
        Dict[str, Any]: Integration status
    """
    return {
        "integration_enabled": detection_cache_integration._integration_enabled,
        "cache_invalidator_status": "active",
        "supported_operations": [
            "detection_completed",
            "detection_updated", 
            "detection_deleted",
            "batch_completed",
            "system_status_changed",
            "performance_metrics_updated",
            "user_preferences_changed",
            "notification_created",
            "model_version_updated"
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
