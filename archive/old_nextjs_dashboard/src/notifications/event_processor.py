#!/usr/bin/env python3
"""
Event Processor for Status Tracking Integration
Service that subscribes to internal status tracking updates, validates and transforms them into 
notification events, and publishes them to Redis for real-time distribution.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable
from uuid import UUID
from datetime import datetime, timezone

from src.notifications.schemas import (
    NotificationEvent,
    StatusUpdateNotification,
    ResultUpdateNotification,
    StageTransitionNotification,
    ErrorNotification,
    CompletionNotification,
    HeartbeatNotification,
    StageProgressInfo,
    ErrorContext,
    NotificationMetadata,
    NotificationEventType,
    NotificationPriority,
    create_status_update_notification,
    create_result_update_notification,
    create_error_notification
)
from src.notifications.redis_publisher import get_notification_publisher, NotificationRedisPublisher
from app.schemas.detection import DetectionStatus, ProcessingStage
from app.services.analysis_history_service import get_analysis_history_service

logger = logging.getLogger(__name__)


class StatusEventProcessor:
    """
    Event processor that integrates status tracking with the notification system.
    Subscribes to internal status updates, transforms them into notification events,
    and publishes them to Redis for real-time distribution to WebSocket clients.
    """
    
    def __init__(self, notification_publisher: Optional[NotificationRedisPublisher] = None):
        """
        Initialize the status event processor.
        
        Args:
            notification_publisher: Optional notification publisher instance
        """
        self.notification_publisher = notification_publisher or get_notification_publisher()
        self.history_service = get_analysis_history_service()
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.running = False
        self.processing_tasks: Dict[str, asyncio.Task] = {}
        
        # Register default event handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default event handlers for common status events."""
        self.register_handler("status_update", self._handle_status_update)
        self.register_handler("result_update", self._handle_result_update)
        self.register_handler("stage_transition", self._handle_stage_transition)
        self.register_handler("error_occurred", self._handle_error_occurred)
        self.register_handler("analysis_completed", self._handle_analysis_completed)
    
    def register_handler(self, event_type: str, handler: Callable):
        """
        Register an event handler for a specific event type.
        
        Args:
            event_type: Type of event to handle
            handler: Handler function to call
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.debug(f"Registered handler for event type: {event_type}")
    
    async def process_status_update(
        self,
        analysis_id: UUID,
        status: DetectionStatus,
        progress: float,
        current_stage: ProcessingStage,
        message: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Process a status update event and publish notification.
        
        Args:
            analysis_id: Analysis identifier
            status: Current analysis status
            progress: Progress percentage (0-100)
            current_stage: Current processing stage
            message: Status message
            additional_data: Additional status data
            
        Returns:
            bool: True if successful
        """
        try:
            logger.debug(f"Processing status update for analysis {analysis_id}: {status} ({progress}%)")
            
            # Create stage progress info
            stage_progress = StageProgressInfo(
                stage_name=current_stage.value,
                stage_status="active" if status == DetectionStatus.PROCESSING else "completed",
                stage_progress_percentage=progress,
                stage_start_time=additional_data.get("stage_start_time") if additional_data else None,
                stage_estimated_duration_seconds=additional_data.get("estimated_duration"),
                frames_processed=additional_data.get("frames_processed"),
                total_frames=additional_data.get("total_frames"),
                processing_rate_fps=additional_data.get("processing_rate"),
                resource_usage=additional_data.get("resource_usage")
            )
            
            # Create status update notification
            notification = create_status_update_notification(
                analysis_id=analysis_id,
                status=status,
                overall_progress=progress,
                current_stage=current_stage,
                stage_progress=stage_progress,
                message=message
            )
            
            # Add additional data to notification
            if additional_data:
                notification.frames_processed = additional_data.get("frames_processed")
                notification.total_frames = additional_data.get("total_frames")
                notification.processing_rate_fps = additional_data.get("processing_rate")
                notification.estimated_completion = additional_data.get("estimated_completion")
                notification.processing_time_seconds = additional_data.get("processing_time")
                notification.resource_utilization = additional_data.get("resource_usage")
                notification.has_errors = additional_data.get("has_errors", False)
                notification.error_count = additional_data.get("error_count", 0)
                
                # Add last error if present
                if additional_data.get("last_error"):
                    error_data = additional_data["last_error"]
                    notification.last_error = ErrorContext(
                        error_type=error_data.get("error_type", "unknown"),
                        error_code=error_data.get("error_code", "UNKNOWN"),
                        error_severity=error_data.get("severity", "error"),
                        affected_stage=error_data.get("affected_stage"),
                        recovery_action=error_data.get("recovery_action")
                    )
            
            # Publish notification
            success = await self.notification_publisher.publish_status_update(notification)
            
            if success:
                logger.debug(f"Successfully published status update for analysis {analysis_id}")
            else:
                logger.warning(f"Failed to publish status update for analysis {analysis_id}")
            
            # Call registered handlers
            await self._call_handlers("status_update", {
                "analysis_id": analysis_id,
                "notification": notification,
                "success": success
            })
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing status update for analysis {analysis_id}: {e}")
            return False
    
    async def process_result_update(
        self,
        analysis_id: UUID,
        status: DetectionStatus,
        confidence: float,
        is_deepfake: bool,
        processing_time: float,
        frames_analyzed: int,
        result_message: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Process a result update event and publish notification.
        
        Args:
            analysis_id: Analysis identifier
            status: Final analysis status
            confidence: Overall confidence score
            is_deepfake: Whether video is classified as deepfake
            processing_time: Total processing time
            frames_analyzed: Total frames analyzed
            result_message: Result summary message
            additional_data: Additional result data
            
        Returns:
            bool: True if successful
        """
        try:
            logger.debug(f"Processing result update for analysis {analysis_id}: {status} (confidence: {confidence})")
            
            # Create result update notification
            notification = create_result_update_notification(
                analysis_id=analysis_id,
                status=status,
                overall_confidence=confidence,
                is_deepfake=is_deepfake,
                total_processing_time=processing_time,
                frames_analyzed=frames_analyzed,
                result_message=result_message
            )
            
            # Add additional data to notification
            if additional_data:
                notification.frame_results = additional_data.get("frame_results")
                notification.suspicious_regions = additional_data.get("suspicious_regions")
                notification.detection_metadata = additional_data.get("detection_metadata")
                notification.average_processing_time_per_frame = additional_data.get("avg_frame_time")
                notification.analysis_quality_score = additional_data.get("quality_score")
                notification.model_confidence = additional_data.get("model_confidence")
                notification.blockchain_verified = additional_data.get("blockchain_verified", False)
                notification.blockchain_transaction_id = additional_data.get("blockchain_tx_id")
                notification.verification_timestamp = additional_data.get("verification_timestamp")
                notification.total_errors = additional_data.get("total_errors", 0)
                notification.total_retries = additional_data.get("total_retries", 0)
                notification.detailed_summary = additional_data.get("detailed_summary")
                notification.recommendations = additional_data.get("recommendations")
            
            # Publish notification
            success = await self.notification_publisher.publish_result_update(notification)
            
            if success:
                logger.debug(f"Successfully published result update for analysis {analysis_id}")
            else:
                logger.warning(f"Failed to publish result update for analysis {analysis_id}")
            
            # Call registered handlers
            await self._call_handlers("result_update", {
                "analysis_id": analysis_id,
                "notification": notification,
                "success": success
            })
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing result update for analysis {analysis_id}: {e}")
            return False
    
    async def process_stage_transition(
        self,
        analysis_id: UUID,
        from_stage: Optional[ProcessingStage],
        to_stage: ProcessingStage,
        overall_progress: float,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Process a stage transition event and publish notification.
        
        Args:
            analysis_id: Analysis identifier
            from_stage: Previous processing stage
            to_stage: Current processing stage
            overall_progress: Overall progress percentage
            additional_data: Additional transition data
            
        Returns:
            bool: True if successful
        """
        try:
            logger.debug(f"Processing stage transition for analysis {analysis_id}: {from_stage} -> {to_stage}")
            
            # Create stage progress info for current stage
            current_stage_progress = StageProgressInfo(
                stage_name=to_stage.value,
                stage_status="active",
                stage_progress_percentage=0.0,  # New stage starts at 0%
                stage_start_time=datetime.now(timezone.utc),
                stage_estimated_duration_seconds=additional_data.get("estimated_duration") if additional_data else None,
                frames_processed=0,  # New stage starts with 0 frames
                total_frames=additional_data.get("total_frames") if additional_data else None,
                processing_rate_fps=None,
                resource_usage=additional_data.get("resource_usage") if additional_data else None
            )
            
            # Create stage transition notification
            notification = StageTransitionNotification(
                event_type=NotificationEventType.STAGE_TRANSITION,
                analysis_id=analysis_id,
                from_stage=from_stage,
                to_stage=to_stage,
                transition_timestamp=datetime.now(timezone.utc),
                previous_stage_duration=additional_data.get("previous_duration") if additional_data else None,
                previous_stage_success=additional_data.get("previous_success", True) if additional_data else True,
                previous_stage_errors=additional_data.get("previous_errors", []) if additional_data else [],
                current_stage_progress=current_stage_progress,
                estimated_stage_duration=additional_data.get("estimated_duration") if additional_data else None,
                overall_progress=overall_progress,
                metadata=NotificationMetadata(
                    notification_id=f"transition_{analysis_id}_{int(datetime.now(timezone.utc).timestamp())}",
                    source="stage_tracker",
                    priority=NotificationPriority.NORMAL,
                    broadcast_to_all=True
                )
            )
            
            # Publish notification
            success = await self.notification_publisher.publish_stage_transition(notification)
            
            if success:
                logger.debug(f"Successfully published stage transition for analysis {analysis_id}")
            else:
                logger.warning(f"Failed to publish stage transition for analysis {analysis_id}")
            
            # Call registered handlers
            await self._call_handlers("stage_transition", {
                "analysis_id": analysis_id,
                "notification": notification,
                "success": success
            })
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing stage transition for analysis {analysis_id}: {e}")
            return False
    
    async def process_error_occurred(
        self,
        analysis_id: UUID,
        error_message: str,
        error_type: str = "processing",
        error_code: str = "UNKNOWN_ERROR",
        affected_stage: Optional[ProcessingStage] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Process an error event and publish notification.
        
        Args:
            analysis_id: Analysis identifier
            error_message: Error message
            error_type: Type of error
            error_code: Specific error code
            affected_stage: Processing stage where error occurred
            additional_data: Additional error data
            
        Returns:
            bool: True if successful
        """
        try:
            logger.debug(f"Processing error for analysis {analysis_id}: {error_type} - {error_message}")
            
            # Create error context
            error_context = ErrorContext(
                error_type=error_type,
                error_code=error_code,
                error_severity=additional_data.get("severity", "error") if additional_data else "error",
                affected_stage=affected_stage.value if affected_stage else None,
                recovery_action=additional_data.get("recovery_action") if additional_data else None,
                retry_count=additional_data.get("retry_count", 0) if additional_data else 0,
                max_retries=additional_data.get("max_retries", 3) if additional_data else 3,
                context_data=additional_data.get("context_data") if additional_data else None
            )
            
            # Create error notification
            notification = create_error_notification(
                analysis_id=analysis_id,
                error_context=error_context,
                impact_level=additional_data.get("impact_level", "moderate") if additional_data else "moderate",
                current_stage=affected_stage
            )
            
            # Add additional error data
            if additional_data:
                notification.is_recoverable = additional_data.get("is_recoverable", True)
                notification.auto_recovery_attempted = additional_data.get("auto_recovery_attempted", False)
                notification.auto_recovery_successful = additional_data.get("auto_recovery_successful", False)
                notification.processing_context = additional_data.get("processing_context")
            
            # Publish notification
            success = await self.notification_publisher.publish_error_notification(notification)
            
            if success:
                logger.debug(f"Successfully published error notification for analysis {analysis_id}")
            else:
                logger.warning(f"Failed to publish error notification for analysis {analysis_id}")
            
            # Call registered handlers
            await self._call_handlers("error_occurred", {
                "analysis_id": analysis_id,
                "notification": notification,
                "success": success
            })
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing error for analysis {analysis_id}: {e}")
            return False
    
    async def process_analysis_completed(
        self,
        analysis_id: UUID,
        completion_status: DetectionStatus,
        total_processing_time: float,
        frames_processed: int,
        total_errors: int,
        total_retries: int,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Process an analysis completion event and publish notification.
        
        Args:
            analysis_id: Analysis identifier
            completion_status: Final completion status
            total_processing_time: Total processing time
            frames_processed: Total frames processed
            total_errors: Total errors encountered
            total_retries: Total retries performed
            additional_data: Additional completion data
            
        Returns:
            bool: True if successful
        """
        try:
            logger.debug(f"Processing completion for analysis {analysis_id}: {completion_status}")
            
            # Calculate success rate
            success_rate = 1.0 if completion_status == DetectionStatus.COMPLETED else 0.0
            
            # Create completion notification
            notification = CompletionNotification(
                event_type=NotificationEventType.COMPLETION_NOTIFICATION,
                analysis_id=analysis_id,
                completion_status=completion_status,
                completion_timestamp=datetime.now(timezone.utc),
                total_processing_time=total_processing_time,
                total_frames_processed=frames_processed,
                total_errors_encountered=total_errors,
                total_retries_performed=total_retries,
                success_rate=success_rate,
                average_processing_rate=additional_data.get("avg_processing_rate") if additional_data else None,
                peak_resource_usage=additional_data.get("peak_resource_usage") if additional_data else None,
                result_summary=additional_data.get("result_summary") if additional_data else None,
                metadata=NotificationMetadata(
                    notification_id=f"completion_{analysis_id}_{int(datetime.now(timezone.utc).timestamp())}",
                    source="completion_tracker",
                    priority=NotificationPriority.HIGH,
                    broadcast_to_all=True
                )
            )
            
            # Publish notification
            success = await self.notification_publisher.publish_completion_notification(notification)
            
            if success:
                logger.debug(f"Successfully published completion notification for analysis {analysis_id}")
            else:
                logger.warning(f"Failed to publish completion notification for analysis {analysis_id}")
            
            # Call registered handlers
            await self._call_handlers("analysis_completed", {
                "analysis_id": analysis_id,
                "notification": notification,
                "success": success
            })
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing completion for analysis {analysis_id}: {e}")
            return False
    
    async def _call_handlers(self, event_type: str, event_data: Dict[str, Any]):
        """
        Call all registered handlers for an event type.
        
        Args:
            event_type: Type of event
            event_data: Event data to pass to handlers
        """
        handlers = self.event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
    
    # Default event handlers
    async def _handle_status_update(self, event_data: Dict[str, Any]):
        """Default handler for status update events."""
        logger.debug(f"Status update handler called for analysis {event_data.get('analysis_id')}")
    
    async def _handle_result_update(self, event_data: Dict[str, Any]):
        """Default handler for result update events."""
        logger.debug(f"Result update handler called for analysis {event_data.get('analysis_id')}")
    
    async def _handle_stage_transition(self, event_data: Dict[str, Any]):
        """Default handler for stage transition events."""
        logger.debug(f"Stage transition handler called for analysis {event_data.get('analysis_id')}")
    
    async def _handle_error_occurred(self, event_data: Dict[str, Any]):
        """Default handler for error events."""
        logger.debug(f"Error handler called for analysis {event_data.get('analysis_id')}")
    
    async def _handle_analysis_completed(self, event_data: Dict[str, Any]):
        """Default handler for completion events."""
        logger.debug(f"Completion handler called for analysis {event_data.get('analysis_id')}")
    
    async def start_processing(self):
        """Start the event processor."""
        if not self.running:
            self.running = True
            logger.info("Status event processor started")
    
    async def stop_processing(self):
        """Stop the event processor."""
        if self.running:
            self.running = False
            # Cancel any running tasks
            for task_id, task in self.processing_tasks.items():
                if not task.done():
                    task.cancel()
            self.processing_tasks.clear()
            logger.info("Status event processor stopped")
    
    async def get_processor_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the event processor.
        
        Returns:
            Dict[str, Any]: Processor statistics
        """
        return {
            "running": self.running,
            "registered_handlers": len(self.event_handlers),
            "active_tasks": len(self.processing_tasks),
            "handler_types": list(self.event_handlers.keys()),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Factory function
def get_status_event_processor(
    notification_publisher: Optional[NotificationRedisPublisher] = None
) -> StatusEventProcessor:
    """
    Factory function to create StatusEventProcessor instance.
    
    Args:
        notification_publisher: Optional notification publisher instance
        
    Returns:
        StatusEventProcessor instance
    """
    return StatusEventProcessor(notification_publisher)


# Convenience functions for common operations
async def process_analysis_status_update(
    analysis_id: UUID,
    status: str,
    progress: float,
    stage: str,
    message: str,
    **kwargs
) -> bool:
    """
    Convenience function to process an analysis status update.
    
    Args:
        analysis_id: Analysis identifier
        status: Status string
        progress: Progress percentage
        stage: Stage string
        message: Status message
        **kwargs: Additional data
        
    Returns:
        bool: True if successful
    """
    try:
        processor = get_status_event_processor()
        return await processor.process_status_update(
            analysis_id=analysis_id,
            status=DetectionStatus(status),
            progress=progress,
            current_stage=ProcessingStage(stage),
            message=message,
            additional_data=kwargs
        )
    except Exception as e:
        logger.error(f"Error processing analysis status update: {e}")
        return False


async def process_analysis_error(
    analysis_id: UUID,
    error_message: str,
    error_type: str = "processing",
    stage: Optional[str] = None,
    **kwargs
) -> bool:
    """
    Convenience function to process an analysis error.
    
    Args:
        analysis_id: Analysis identifier
        error_message: Error message
        error_type: Error type
        stage: Affected stage
        **kwargs: Additional error data
        
    Returns:
        bool: True if successful
    """
    try:
        processor = get_status_event_processor()
        affected_stage = ProcessingStage(stage) if stage else None
        return await processor.process_error_occurred(
            analysis_id=analysis_id,
            error_message=error_message,
            error_type=error_type,
            affected_stage=affected_stage,
            additional_data=kwargs
        )
    except Exception as e:
        logger.error(f"Error processing analysis error: {e}")
        return False


async def publish_status_update_notification(
    analysis_id: UUID,
    status: str,
    progress: float,
    stage: str,
    message: str,
    **kwargs
) -> bool:
    """
    Convenience function to publish a status update notification.
    
    Args:
        analysis_id: Analysis identifier
        status: Status string
        progress: Progress percentage
        stage: Stage string
        message: Status message
        **kwargs: Additional data
        
    Returns:
        bool: True if successful
    """
    try:
        return await process_analysis_status_update(
            analysis_id=analysis_id,
            status=status,
            progress=progress,
            stage=stage,
            message=message,
            **kwargs
        )
    except Exception as e:
        logger.error(f"Error publishing status update notification: {e}")
        return False


# Export all classes and functions
__all__ = [
    'StatusEventProcessor',
    'get_status_event_processor',
    'process_analysis_status_update',
    'process_analysis_error',
    'publish_status_update_notification'
]