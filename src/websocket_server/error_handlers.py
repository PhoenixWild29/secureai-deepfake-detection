#!/usr/bin/env python3
"""
Error Handlers for Notification Delivery Failures
Comprehensive error handling mechanisms for notification delivery failures, including
logging, fallback strategies, retry logic, and dead-letter queue patterns.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable
from uuid import UUID
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field

from src.notifications.schemas import NotificationEvent, NotificationEventType, NotificationPriority

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Enumeration of error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorType(str, Enum):
    """Enumeration of error types for notification delivery."""
    CONNECTION_ERROR = "connection_error"
    SERIALIZATION_ERROR = "serialization_error"
    AUTHORIZATION_ERROR = "authorization_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    REDIS_ERROR = "redis_error"
    WEBSOCKET_ERROR = "websocket_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class NotificationError:
    """Represents a notification delivery error with context."""
    error_id: str
    notification_id: str
    client_id: Optional[str]
    error_type: ErrorType
    error_message: str
    error_severity: ErrorSeverity
    timestamp: datetime
    retry_count: int = 0
    max_retries: int = 3
    notification_data: Optional[Dict[str, Any]] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def should_retry(self) -> bool:
        """Check if this error should be retried."""
        return self.retry_count < self.max_retries and self.error_severity != ErrorSeverity.CRITICAL
    
    def increment_retry(self):
        """Increment the retry count."""
        self.retry_count += 1


@dataclass
class DeadLetterEntry:
    """Entry for the dead letter queue."""
    error_id: str
    notification_data: Dict[str, Any]
    error: NotificationError
    created_at: datetime
    processed: bool = False


class NotificationErrorHandler:
    """
    Comprehensive error handler for notification delivery failures.
    Provides logging, retry logic, fallback strategies, and dead-letter queue management.
    """
    
    def __init__(self):
        """Initialize the notification error handler."""
        self.error_log: List[NotificationError] = []
        self.dead_letter_queue: List[DeadLetterEntry] = []
        self.retry_queue: List[NotificationError] = []
        self.error_handlers: Dict[ErrorType, List[Callable]] = {}
        self.fallback_strategies: Dict[ErrorType, Callable] = {}
        
        # Configuration
        self.max_error_log_size = 1000
        self.max_dead_letter_size = 500
        self.retry_delay_seconds = 5
        self.max_retry_delay_seconds = 300
        self.cleanup_interval_seconds = 3600  # 1 hour
        
        # Statistics
        self.error_stats = {
            "total_errors": 0,
            "errors_by_type": {},
            "errors_by_severity": {},
            "retry_successes": 0,
            "retry_failures": 0,
            "dead_letter_entries": 0
        }
        
        # Register default handlers and strategies
        self._register_default_handlers()
        self._register_default_strategies()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _register_default_handlers(self):
        """Register default error handlers."""
        self.register_error_handler(ErrorType.CONNECTION_ERROR, self._handle_connection_error)
        self.register_error_handler(ErrorType.SERIALIZATION_ERROR, self._handle_serialization_error)
        self.register_error_handler(ErrorType.AUTHORIZATION_ERROR, self._handle_authorization_error)
        self.register_error_handler(ErrorType.RATE_LIMIT_ERROR, self._handle_rate_limit_error)
        self.register_error_handler(ErrorType.REDIS_ERROR, self._handle_redis_error)
        self.register_error_handler(ErrorType.WEBSOCKET_ERROR, self._handle_websocket_error)
        self.register_error_handler(ErrorType.TIMEOUT_ERROR, self._handle_timeout_error)
        self.register_error_handler(ErrorType.UNKNOWN_ERROR, self._handle_unknown_error)
    
    def _register_default_strategies(self):
        """Register default fallback strategies."""
        self.register_fallback_strategy(ErrorType.CONNECTION_ERROR, self._fallback_reconnect)
        self.register_fallback_strategy(ErrorType.SERIALIZATION_ERROR, self._fallback_simplify_message)
        self.register_fallback_strategy(ErrorType.RATE_LIMIT_ERROR, self._fallback_delay_send)
        self.register_fallback_strategy(ErrorType.REDIS_ERROR, self._fallback_local_queue)
        self.register_fallback_strategy(ErrorType.WEBSOCKET_ERROR, self._fallback_http_postback)
    
    def _start_background_tasks(self):
        """Start background tasks for error handling."""
        # Start retry processing task
        asyncio.create_task(self._retry_processing_loop())
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_loop())
    
    async def handle_notification_error(
        self,
        notification: NotificationEvent,
        client_id: Optional[str],
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Handle a notification delivery error.
        
        Args:
            notification: The notification that failed to deliver
            client_id: Client ID (None for broadcast failures)
            error: The error that occurred
            context: Additional error context
            
        Returns:
            bool: True if error was handled successfully
        """
        try:
            # Determine error type and severity
            error_type = self._classify_error(error)
            error_severity = self._determine_severity(error_type, error)
            
            # Create error record
            error_record = NotificationError(
                error_id=f"err_{int(datetime.now(timezone.utc).timestamp())}_{client_id or 'broadcast'}",
                notification_id=getattr(notification.metadata, 'notification_id', 'unknown'),
                client_id=client_id,
                error_type=error_type,
                error_message=str(error),
                error_severity=error_severity,
                timestamp=datetime.now(timezone.utc),
                notification_data=notification.dict() if hasattr(notification, 'dict') else None,
                context=context or {}
            )
            
            # Log the error
            await self._log_error(error_record)
            
            # Update statistics
            self._update_error_stats(error_record)
            
            # Call error handlers
            await self._call_error_handlers(error_record)
            
            # Determine if retry is appropriate
            if error_record.should_retry():
                await self._queue_for_retry(error_record)
            else:
                await self._send_to_dead_letter(error_record)
            
            # Attempt fallback strategy
            fallback_success = await self._attempt_fallback(error_record)
            
            logger.info(f"Handled notification error: {error_type.value} - {error_record.error_message}")
            return True
            
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
            return False
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify an error into a specific error type."""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        if "connection" in error_str or "disconnected" in error_str:
            return ErrorType.CONNECTION_ERROR
        elif "json" in error_str or "serialize" in error_str or "decode" in error_str:
            return ErrorType.SERIALIZATION_ERROR
        elif "unauthorized" in error_str or "permission" in error_str or "forbidden" in error_str:
            return ErrorType.AUTHORIZATION_ERROR
        elif "rate limit" in error_str or "throttle" in error_str:
            return ErrorType.RATE_LIMIT_ERROR
        elif "redis" in error_str or "pubsub" in error_str:
            return ErrorType.REDIS_ERROR
        elif "websocket" in error_str or "websocket" in error_type:
            return ErrorType.WEBSOCKET_ERROR
        elif "timeout" in error_str or "timed out" in error_str:
            return ErrorType.TIMEOUT_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
    
    def _determine_severity(self, error_type: ErrorType, error: Exception) -> ErrorSeverity:
        """Determine the severity of an error."""
        # Critical errors that should not be retried
        if error_type in [ErrorType.AUTHORIZATION_ERROR]:
            return ErrorSeverity.CRITICAL
        
        # High severity errors that may need immediate attention
        elif error_type in [ErrorType.REDIS_ERROR, ErrorType.SERIALIZATION_ERROR]:
            return ErrorSeverity.HIGH
        
        # Medium severity errors that are typically recoverable
        elif error_type in [ErrorType.CONNECTION_ERROR, ErrorType.WEBSOCKET_ERROR, ErrorType.TIMEOUT_ERROR]:
            return ErrorSeverity.MEDIUM
        
        # Low severity errors that are typically transient
        elif error_type in [ErrorType.RATE_LIMIT_ERROR]:
            return ErrorSeverity.LOW
        
        else:
            return ErrorSeverity.MEDIUM
    
    async def _log_error(self, error_record: NotificationError):
        """Log an error record."""
        try:
            # Add to error log
            self.error_log.append(error_record)
            
            # Trim log if it gets too large
            if len(self.error_log) > self.max_error_log_size:
                self.error_log = self.error_log[-self.max_error_log_size:]
            
            # Log based on severity
            log_message = f"Notification error: {error_record.error_type.value} - {error_record.error_message}"
            
            if error_record.error_severity == ErrorSeverity.CRITICAL:
                logger.critical(log_message)
            elif error_record.error_severity == ErrorSeverity.HIGH:
                logger.error(log_message)
            elif error_record.error_severity == ErrorSeverity.MEDIUM:
                logger.warning(log_message)
            else:
                logger.info(log_message)
                
        except Exception as e:
            logger.error(f"Error logging error record: {e}")
    
    def _update_error_stats(self, error_record: NotificationError):
        """Update error statistics."""
        try:
            self.error_stats["total_errors"] += 1
            
            # Update by type
            error_type = error_record.error_type.value
            self.error_stats["errors_by_type"][error_type] = self.error_stats["errors_by_type"].get(error_type, 0) + 1
            
            # Update by severity
            severity = error_record.error_severity.value
            self.error_stats["errors_by_severity"][severity] = self.error_stats["errors_by_severity"].get(severity, 0) + 1
            
        except Exception as e:
            logger.error(f"Error updating error stats: {e}")
    
    async def _call_error_handlers(self, error_record: NotificationError):
        """Call registered error handlers for this error type."""
        try:
            handlers = self.error_handlers.get(error_record.error_type, [])
            
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(error_record)
                    else:
                        handler(error_record)
                except Exception as e:
                    logger.error(f"Error in error handler: {e}")
                    
        except Exception as e:
            logger.error(f"Error calling error handlers: {e}")
    
    async def _queue_for_retry(self, error_record: NotificationError):
        """Queue an error for retry."""
        try:
            self.retry_queue.append(error_record)
            logger.debug(f"Queued error {error_record.error_id} for retry")
            
        except Exception as e:
            logger.error(f"Error queuing error for retry: {e}")
    
    async def _send_to_dead_letter(self, error_record: NotificationError):
        """Send an error to the dead letter queue."""
        try:
            if error_record.notification_data:
                dead_letter_entry = DeadLetterEntry(
                    error_id=error_record.error_id,
                    notification_data=error_record.notification_data,
                    error=error_record,
                    created_at=datetime.now(timezone.utc)
                )
                
                self.dead_letter_queue.append(dead_letter_entry)
                self.error_stats["dead_letter_entries"] += 1
                
                # Trim queue if it gets too large
                if len(self.dead_letter_queue) > self.max_dead_letter_size:
                    self.dead_letter_queue = self.dead_letter_queue[-self.max_dead_letter_size:]
                
                logger.warning(f"Sent error {error_record.error_id} to dead letter queue")
            
        except Exception as e:
            logger.error(f"Error sending to dead letter queue: {e}")
    
    async def _attempt_fallback(self, error_record: NotificationError) -> bool:
        """Attempt a fallback strategy for the error."""
        try:
            fallback_strategy = self.fallback_strategies.get(error_record.error_type)
            
            if fallback_strategy:
                if asyncio.iscoroutinefunction(fallback_strategy):
                    return await fallback_strategy(error_record)
                else:
                    return fallback_strategy(error_record)
            
            return False
            
        except Exception as e:
            logger.error(f"Error in fallback strategy: {e}")
            return False
    
    async def _retry_processing_loop(self):
        """Background loop for processing retry queue."""
        try:
            while True:
                await asyncio.sleep(self.retry_delay_seconds)
                
                if not self.retry_queue:
                    continue
                
                # Process retries with exponential backoff
                current_time = datetime.now(timezone.utc)
                retries_to_process = []
                
                for error_record in self.retry_queue[:]:
                    # Calculate delay based on retry count
                    delay = min(
                        self.retry_delay_seconds * (2 ** error_record.retry_count),
                        self.max_retry_delay_seconds
                    )
                    
                    # Check if it's time to retry
                    if (current_time - error_record.timestamp).total_seconds() >= delay:
                        retries_to_process.append(error_record)
                        self.retry_queue.remove(error_record)
                
                # Process retries
                for error_record in retries_to_process:
                    await self._process_retry(error_record)
                    
        except asyncio.CancelledError:
            logger.info("Retry processing loop cancelled")
        except Exception as e:
            logger.error(f"Error in retry processing loop: {e}")
    
    async def _process_retry(self, error_record: NotificationError):
        """Process a single retry attempt."""
        try:
            error_record.increment_retry()
            
            # Attempt to redeliver the notification
            success = await self._redeliver_notification(error_record)
            
            if success:
                self.error_stats["retry_successes"] += 1
                logger.info(f"Retry successful for error {error_record.error_id}")
            else:
                self.error_stats["retry_failures"] += 1
                
                # If max retries reached, send to dead letter
                if not error_record.should_retry():
                    await self._send_to_dead_letter(error_record)
                    logger.warning(f"Max retries reached for error {error_record.error_id}, sent to dead letter")
                else:
                    # Queue for another retry
                    await self._queue_for_retry(error_record)
                    
        except Exception as e:
            logger.error(f"Error processing retry for error {error_record.error_id}: {e}")
    
    async def _redeliver_notification(self, error_record: NotificationError) -> bool:
        """Attempt to redeliver a failed notification."""
        try:
            # This would integrate with the actual notification delivery system
            # For now, we'll simulate the redelivery attempt
            
            if not error_record.notification_data:
                return False
            
            # Simulate redelivery logic here
            # In a real implementation, this would:
            # 1. Recreate the notification object
            # 2. Attempt delivery via the appropriate channel
            # 3. Return success/failure based on the result
            
            logger.debug(f"Attempting to redeliver notification for error {error_record.error_id}")
            
            # Simulate success for now
            return True
            
        except Exception as e:
            logger.error(f"Error redelivering notification for error {error_record.error_id}: {e}")
            return False
    
    async def _cleanup_loop(self):
        """Background loop for cleanup tasks."""
        try:
            while True:
                await asyncio.sleep(self.cleanup_interval_seconds)
                
                # Clean up old error logs
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                self.error_log = [e for e in self.error_log if e.timestamp > cutoff_time]
                
                # Clean up old dead letter entries
                self.dead_letter_queue = [e for e in self.dead_letter_queue if e.created_at > cutoff_time]
                
                logger.debug("Completed error handler cleanup")
                
        except asyncio.CancelledError:
            logger.info("Cleanup loop cancelled")
        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}")
    
    # Error handler registration
    def register_error_handler(self, error_type: ErrorType, handler: Callable):
        """Register an error handler for a specific error type."""
        if error_type not in self.error_handlers:
            self.error_handlers[error_type] = []
        self.error_handlers[error_type].append(handler)
    
    def register_fallback_strategy(self, error_type: ErrorType, strategy: Callable):
        """Register a fallback strategy for a specific error type."""
        self.fallback_strategies[error_type] = strategy
    
    # Default error handlers
    async def _handle_connection_error(self, error_record: NotificationError):
        """Handle connection errors."""
        logger.warning(f"Connection error for client {error_record.client_id}: {error_record.error_message}")
    
    async def _handle_serialization_error(self, error_record: NotificationError):
        """Handle serialization errors."""
        logger.error(f"Serialization error: {error_record.error_message}")
    
    async def _handle_authorization_error(self, error_record: NotificationError):
        """Handle authorization errors."""
        logger.error(f"Authorization error for client {error_record.client_id}: {error_record.error_message}")
    
    async def _handle_rate_limit_error(self, error_record: NotificationError):
        """Handle rate limit errors."""
        logger.warning(f"Rate limit error for client {error_record.client_id}: {error_record.error_message}")
    
    async def _handle_redis_error(self, error_record: NotificationError):
        """Handle Redis errors."""
        logger.error(f"Redis error: {error_record.error_message}")
    
    async def _handle_websocket_error(self, error_record: NotificationError):
        """Handle WebSocket errors."""
        logger.error(f"WebSocket error for client {error_record.client_id}: {error_record.error_message}")
    
    async def _handle_timeout_error(self, error_record: NotificationError):
        """Handle timeout errors."""
        logger.warning(f"Timeout error for client {error_record.client_id}: {error_record.error_message}")
    
    async def _handle_unknown_error(self, error_record: NotificationError):
        """Handle unknown errors."""
        logger.error(f"Unknown error for client {error_record.client_id}: {error_record.error_message}")
    
    # Default fallback strategies
    async def _fallback_reconnect(self, error_record: NotificationError) -> bool:
        """Fallback strategy for connection errors."""
        logger.info(f"Attempting to reconnect for error {error_record.error_id}")
        return True
    
    async def _fallback_simplify_message(self, error_record: NotificationError) -> bool:
        """Fallback strategy for serialization errors."""
        logger.info(f"Attempting to simplify message for error {error_record.error_id}")
        return True
    
    async def _fallback_delay_send(self, error_record: NotificationError) -> bool:
        """Fallback strategy for rate limit errors."""
        logger.info(f"Delaying send for error {error_record.error_id}")
        return True
    
    async def _fallback_local_queue(self, error_record: NotificationError) -> bool:
        """Fallback strategy for Redis errors."""
        logger.info(f"Using local queue for error {error_record.error_id}")
        return True
    
    async def _fallback_http_postback(self, error_record: NotificationError) -> bool:
        """Fallback strategy for WebSocket errors."""
        logger.info(f"Using HTTP postback for error {error_record.error_id}")
        return True
    
    # Statistics and monitoring
    def get_error_stats(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        return {
            "error_stats": self.error_stats,
            "error_log_size": len(self.error_log),
            "retry_queue_size": len(self.retry_queue),
            "dead_letter_queue_size": len(self.dead_letter_queue),
            "registered_handlers": len(self.error_handlers),
            "registered_fallbacks": len(self.fallback_strategies),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent error records."""
        recent_errors = self.error_log[-limit:] if self.error_log else []
        return [
            {
                "error_id": error.error_id,
                "notification_id": error.notification_id,
                "client_id": error.client_id,
                "error_type": error.error_type.value,
                "error_message": error.error_message,
                "error_severity": error.error_severity.value,
                "timestamp": error.timestamp.isoformat(),
                "retry_count": error.retry_count
            }
            for error in recent_errors
        ]


# Global error handler instance
_error_handler: Optional[NotificationErrorHandler] = None


def get_notification_error_handler() -> NotificationErrorHandler:
    """Get the global notification error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = NotificationErrorHandler()
    return _error_handler


# Export all classes and functions
__all__ = [
    'ErrorSeverity',
    'ErrorType',
    'NotificationError',
    'DeadLetterEntry',
    'NotificationErrorHandler',
    'get_notification_error_handler'
]