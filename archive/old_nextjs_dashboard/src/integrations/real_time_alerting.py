#!/usr/bin/env python3
"""
Real-Time Alerting Integration
Integration with existing real-time alerting infrastructure for notifications
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable
import structlog
import json

from src.models.notifications import (
    CreateNotificationRequest,
    NotificationType,
    NotificationPriority,
    NotificationCategory,
    NotificationContent,
    NotificationMetadata,
    NotificationDelivery,
    DeliveryMethod
)
from src.services.notification_service import get_notification_service
from src.config.notifications_config import get_notifications_config

logger = structlog.get_logger(__name__)

# Import existing alerting components
try:
    from ai_model.morpheus_security import morpheus_monitor
    MORPHEUS_AVAILABLE = True
except ImportError:
    MORPHEUS_AVAILABLE = False
    logger.warning("Morpheus security monitoring not available")

try:
    from ai_model.detect import detect_fake
    DETECTION_AVAILABLE = True
except ImportError:
    DETECTION_AVAILABLE = False
    logger.warning("Detection engine not available")


class RealTimeAlertingConsumer:
    """
    Consumer for real-time alerting events
    Integrates with existing alerting infrastructure to create notifications
    """
    
    def __init__(self):
        """Initialize real-time alerting consumer"""
        self.config = get_notifications_config()
        self.notification_service = None
        self.event_handlers: Dict[str, Callable] = {}
        self.running = False
        self.consumer_task = None
        
        # Register default event handlers
        self._register_default_handlers()
        
        logger.info("RealTimeAlertingConsumer initialized")
    
    async def start(self):
        """Start the real-time alerting consumer"""
        if self.running:
            logger.warning("Real-time alerting consumer already running")
            return
        
        self.running = True
        self.notification_service = await get_notification_service()
        
        # Start consumer task
        self.consumer_task = asyncio.create_task(self._consumer_loop())
        
        logger.info("Real-time alerting consumer started")
    
    async def stop(self):
        """Stop the real-time alerting consumer"""
        if not self.running:
            return
        
        self.running = False
        
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Real-time alerting consumer stopped")
    
    def register_handler(self, event_type: str, handler: Callable):
        """
        Register event handler for specific event type
        
        Args:
            event_type: Type of event to handle
            handler: Async function to handle the event
        """
        self.event_handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")
    
    def _register_default_handlers(self):
        """Register default event handlers"""
        self.register_handler("analysis_completion", self._handle_analysis_completion)
        self.register_handler("security_alert", self._handle_security_alert)
        self.register_handler("system_status", self._handle_system_status)
        self.register_handler("compliance_alert", self._handle_compliance_alert)
        self.register_handler("performance_alert", self._handle_performance_alert)
        self.register_handler("user_activity", self._handle_user_activity)
        self.register_handler("maintenance", self._handle_maintenance)
        self.register_handler("blockchain_update", self._handle_blockchain_update)
        self.register_handler("export_completion", self._handle_export_completion)
        self.register_handler("training_completion", self._handle_training_completion)
    
    async def _consumer_loop(self):
        """Main consumer loop for processing events"""
        logger.info("Starting real-time alerting consumer loop")
        
        while self.running:
            try:
                # Process events from various sources
                await self._process_morpheus_events()
                await self._process_detection_events()
                await self._process_system_events()
                
                # Sleep briefly to prevent excessive CPU usage
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error("Error in consumer loop", error=str(e))
                await asyncio.sleep(5.0)  # Wait longer on error
    
    async def _process_morpheus_events(self):
        """Process events from Morpheus security monitoring"""
        if not MORPHEUS_AVAILABLE or not self.config.morpheus_integration_enabled:
            return
        
        try:
            # Get security status from Morpheus
            security_status = morpheus_monitor.get_security_status()
            
            # Check for new threats or alerts
            if security_status.get('queued_threats', 0) > 0:
                await self._handle_security_alert({
                    'source': 'morpheus_security',
                    'threat_count': security_status['queued_threats'],
                    'monitoring_active': security_status['monitoring_active'],
                    'anomaly_detector': security_status['anomaly_detector'],
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
        
        except Exception as e:
            logger.error("Error processing Morpheus events", error=str(e))
    
    async def _process_detection_events(self):
        """Process events from detection engine"""
        if not DETECTION_AVAILABLE:
            return
        
        # This would integrate with the detection engine's event system
        # For now, we'll simulate detection events
        pass
    
    async def _process_system_events(self):
        """Process system-level events"""
        # This would integrate with system monitoring
        # For now, we'll simulate system events
        pass
    
    # Event handlers
    
    async def _handle_analysis_completion(self, event_data: Dict[str, Any]):
        """Handle analysis completion events"""
        try:
            logger.info("Handling analysis completion event", event_data=event_data)
            
            # Create notification for analysis completion
            notification_request = CreateNotificationRequest(
                user_id=event_data.get('user_id'),
                type=NotificationType.ANALYSIS_COMPLETION,
                category=NotificationCategory.DETECTION,
                priority=self._determine_priority(event_data),
                content=NotificationContent(
                    title="Video Analysis Complete",
                    message=f"Your video analysis has been completed. Result: {event_data.get('result', 'Unknown')}",
                    summary=f"Analysis completed - {event_data.get('confidence', 'N/A')}% confidence",
                    action_url=event_data.get('result_url'),
                    action_text="View Results",
                    details=event_data
                ),
                metadata=NotificationMetadata(
                    source="detection_engine",
                    component="video_analysis",
                    analysis_id=event_data.get('analysis_id'),
                    video_id=event_data.get('video_id'),
                    event_id=event_data.get('event_id'),
                    tags=["analysis", "completion", "detection"]
                ),
                delivery=NotificationDelivery(
                    methods=[DeliveryMethod.IN_APP, DeliveryMethod.EMAIL],
                    priority=self._determine_priority(event_data)
                )
            )
            
            # Create notification (this would use the notification service)
            await self._create_notification(notification_request)
            
        except Exception as e:
            logger.error("Error handling analysis completion event", error=str(e))
    
    async def _handle_security_alert(self, event_data: Dict[str, Any]):
        """Handle security alert events"""
        try:
            logger.info("Handling security alert event", event_data=event_data)
            
            threat_level = event_data.get('threat_level', 'medium')
            priority = self._map_threat_level_to_priority(threat_level)
            
            notification_request = CreateNotificationRequest(
                user_id=event_data.get('user_id'),
                type=NotificationType.SECURITY_ALERT,
                category=NotificationCategory.SECURITY,
                priority=priority,
                content=NotificationContent(
                    title="Security Alert",
                    message=f"Security threat detected: {event_data.get('threat_type', 'Unknown threat')}",
                    summary=f"Threat level: {threat_level.upper()}",
                    action_url=event_data.get('alert_url'),
                    action_text="View Alert Details",
                    details=event_data
                ),
                metadata=NotificationMetadata(
                    source=event_data.get('source', 'morpheus_security'),
                    component="security_monitoring",
                    event_id=event_data.get('event_id'),
                    tags=["security", "alert", "threat", threat_level]
                ),
                delivery=NotificationDelivery(
                    methods=[DeliveryMethod.IN_APP, DeliveryMethod.EMAIL, DeliveryMethod.PUSH],
                    priority=priority
                )
            )
            
            await self._create_notification(notification_request)
            
        except Exception as e:
            logger.error("Error handling security alert event", error=str(e))
    
    async def _handle_system_status(self, event_data: Dict[str, Any]):
        """Handle system status events"""
        try:
            logger.info("Handling system status event", event_data=event_data)
            
            status = event_data.get('status', 'unknown')
            priority = self._map_system_status_to_priority(status)
            
            notification_request = CreateNotificationRequest(
                user_id=None,  # System-wide notification
                type=NotificationType.SYSTEM_STATUS,
                category=NotificationCategory.SYSTEM,
                priority=priority,
                content=NotificationContent(
                    title="System Status Update",
                    message=f"System status changed to: {status.upper()}",
                    summary=f"System is {status}",
                    action_url=event_data.get('status_url'),
                    action_text="View System Status",
                    details=event_data
                ),
                metadata=NotificationMetadata(
                    source="system_monitor",
                    component="system_status",
                    event_id=event_data.get('event_id'),
                    tags=["system", "status", status]
                ),
                delivery=NotificationDelivery(
                    methods=[DeliveryMethod.IN_APP],
                    priority=priority
                )
            )
            
            await self._create_notification(notification_request)
            
        except Exception as e:
            logger.error("Error handling system status event", error=str(e))
    
    async def _handle_compliance_alert(self, event_data: Dict[str, Any]):
        """Handle compliance alert events"""
        try:
            logger.info("Handling compliance alert event", event_data=event_data)
            
            notification_request = CreateNotificationRequest(
                user_id=event_data.get('user_id'),
                type=NotificationType.COMPLIANCE_ALERT,
                category=NotificationCategory.COMPLIANCE,
                priority=NotificationPriority.HIGH,
                content=NotificationContent(
                    title="Compliance Alert",
                    message=f"Compliance issue detected: {event_data.get('issue_type', 'Unknown issue')}",
                    summary="Compliance attention required",
                    action_url=event_data.get('compliance_url'),
                    action_text="Review Compliance",
                    details=event_data
                ),
                metadata=NotificationMetadata(
                    source="compliance_monitor",
                    component="compliance_checker",
                    event_id=event_data.get('event_id'),
                    tags=["compliance", "alert", "regulatory"]
                ),
                delivery=NotificationDelivery(
                    methods=[DeliveryMethod.IN_APP, DeliveryMethod.EMAIL],
                    priority=NotificationPriority.HIGH
                )
            )
            
            await self._create_notification(notification_request)
            
        except Exception as e:
            logger.error("Error handling compliance alert event", error=str(e))
    
    async def _handle_performance_alert(self, event_data: Dict[str, Any]):
        """Handle performance alert events"""
        try:
            logger.info("Handling performance alert event", event_data=event_data)
            
            notification_request = CreateNotificationRequest(
                user_id=None,  # System-wide notification
                type=NotificationType.PERFORMANCE_ALERT,
                category=NotificationCategory.PERFORMANCE,
                priority=NotificationPriority.MEDIUM,
                content=NotificationContent(
                    title="Performance Alert",
                    message=f"Performance issue detected: {event_data.get('issue_type', 'Unknown issue')}",
                    summary=f"Performance: {event_data.get('performance_level', 'Unknown')}",
                    action_url=event_data.get('performance_url'),
                    action_text="View Performance Metrics",
                    details=event_data
                ),
                metadata=NotificationMetadata(
                    source="performance_monitor",
                    component="performance_checker",
                    event_id=event_data.get('event_id'),
                    tags=["performance", "alert", "system"]
                ),
                delivery=NotificationDelivery(
                    methods=[DeliveryMethod.IN_APP],
                    priority=NotificationPriority.MEDIUM
                )
            )
            
            await self._create_notification(notification_request)
            
        except Exception as e:
            logger.error("Error handling performance alert event", error=str(e))
    
    async def _handle_user_activity(self, event_data: Dict[str, Any]):
        """Handle user activity events"""
        try:
            logger.info("Handling user activity event", event_data=event_data)
            
            notification_request = CreateNotificationRequest(
                user_id=event_data.get('user_id'),
                type=NotificationType.USER_ACTIVITY,
                category=NotificationCategory.USER,
                priority=NotificationPriority.LOW,
                content=NotificationContent(
                    title="User Activity",
                    message=f"User activity: {event_data.get('activity_type', 'Unknown activity')}",
                    summary=f"Activity: {event_data.get('activity_summary', 'User activity detected')}",
                    action_url=event_data.get('activity_url'),
                    action_text="View Activity",
                    details=event_data
                ),
                metadata=NotificationMetadata(
                    source="user_monitor",
                    component="activity_tracker",
                    event_id=event_data.get('event_id'),
                    tags=["user", "activity", "tracking"]
                ),
                delivery=NotificationDelivery(
                    methods=[DeliveryMethod.IN_APP],
                    priority=NotificationPriority.LOW
                )
            )
            
            await self._create_notification(notification_request)
            
        except Exception as e:
            logger.error("Error handling user activity event", error=str(e))
    
    async def _handle_maintenance(self, event_data: Dict[str, Any]):
        """Handle maintenance events"""
        try:
            logger.info("Handling maintenance event", event_data=event_data)
            
            notification_request = CreateNotificationRequest(
                user_id=None,  # System-wide notification
                type=NotificationType.MAINTENANCE,
                category=NotificationCategory.MAINTENANCE,
                priority=NotificationPriority.MEDIUM,
                content=NotificationContent(
                    title="Maintenance Notification",
                    message=f"System maintenance: {event_data.get('maintenance_type', 'Scheduled maintenance')}",
                    summary=f"Maintenance: {event_data.get('maintenance_summary', 'System maintenance in progress')}",
                    action_url=event_data.get('maintenance_url'),
                    action_text="View Maintenance Details",
                    details=event_data
                ),
                metadata=NotificationMetadata(
                    source="maintenance_scheduler",
                    component="maintenance_manager",
                    event_id=event_data.get('event_id'),
                    tags=["maintenance", "system", "scheduled"]
                ),
                delivery=NotificationDelivery(
                    methods=[DeliveryMethod.IN_APP, DeliveryMethod.EMAIL],
                    priority=NotificationPriority.MEDIUM
                )
            )
            
            await self._create_notification(notification_request)
            
        except Exception as e:
            logger.error("Error handling maintenance event", error=str(e))
    
    async def _handle_blockchain_update(self, event_data: Dict[str, Any]):
        """Handle blockchain update events"""
        try:
            logger.info("Handling blockchain update event", event_data=event_data)
            
            notification_request = CreateNotificationRequest(
                user_id=event_data.get('user_id'),
                type=NotificationType.BLOCKCHAIN_UPDATE,
                category=NotificationCategory.BLOCKCHAIN,
                priority=NotificationPriority.MEDIUM,
                content=NotificationContent(
                    title="Blockchain Update",
                    message=f"Blockchain transaction completed: {event_data.get('transaction_type', 'Unknown transaction')}",
                    summary=f"Transaction: {event_data.get('transaction_hash', 'N/A')[:16]}...",
                    action_url=event_data.get('blockchain_url'),
                    action_text="View Transaction",
                    details=event_data
                ),
                metadata=NotificationMetadata(
                    source="blockchain_monitor",
                    component="transaction_tracker",
                    event_id=event_data.get('event_id'),
                    tags=["blockchain", "transaction", "update"]
                ),
                delivery=NotificationDelivery(
                    methods=[DeliveryMethod.IN_APP],
                    priority=NotificationPriority.MEDIUM
                )
            )
            
            await self._create_notification(notification_request)
            
        except Exception as e:
            logger.error("Error handling blockchain update event", error=str(e))
    
    async def _handle_export_completion(self, event_data: Dict[str, Any]):
        """Handle export completion events"""
        try:
            logger.info("Handling export completion event", event_data=event_data)
            
            notification_request = CreateNotificationRequest(
                user_id=event_data.get('user_id'),
                type=NotificationType.EXPORT_COMPLETION,
                category=NotificationCategory.EXPORT,
                priority=NotificationPriority.LOW,
                content=NotificationContent(
                    title="Export Complete",
                    message=f"Your export has been completed: {event_data.get('export_type', 'Unknown export')}",
                    summary=f"Export: {event_data.get('file_name', 'Export file')}",
                    action_url=event_data.get('download_url'),
                    action_text="Download File",
                    details=event_data
                ),
                metadata=NotificationMetadata(
                    source="export_service",
                    component="export_manager",
                    event_id=event_data.get('event_id'),
                    tags=["export", "completion", "download"]
                ),
                delivery=NotificationDelivery(
                    methods=[DeliveryMethod.IN_APP, DeliveryMethod.EMAIL],
                    priority=NotificationPriority.LOW
                )
            )
            
            await self._create_notification(notification_request)
            
        except Exception as e:
            logger.error("Error handling export completion event", error=str(e))
    
    async def _handle_training_completion(self, event_data: Dict[str, Any]):
        """Handle training completion events"""
        try:
            logger.info("Handling training completion event", event_data=event_data)
            
            notification_request = CreateNotificationRequest(
                user_id=event_data.get('user_id'),
                type=NotificationType.TRAINING_COMPLETION,
                category=NotificationCategory.TRAINING,
                priority=NotificationPriority.MEDIUM,
                content=NotificationContent(
                    title="Training Complete",
                    message=f"Model training completed: {event_data.get('model_type', 'Unknown model')}",
                    summary=f"Training: {event_data.get('training_summary', 'Model training completed successfully')}",
                    action_url=event_data.get('training_url'),
                    action_text="View Training Results",
                    details=event_data
                ),
                metadata=NotificationMetadata(
                    source="training_service",
                    component="model_trainer",
                    event_id=event_data.get('event_id'),
                    tags=["training", "completion", "model"]
                ),
                delivery=NotificationDelivery(
                    methods=[DeliveryMethod.IN_APP],
                    priority=NotificationPriority.MEDIUM
                )
            )
            
            await self._create_notification(notification_request)
            
        except Exception as e:
            logger.error("Error handling training completion event", error=str(e))
    
    # Helper methods
    
    async def _create_notification(self, request: CreateNotificationRequest):
        """Create notification using the notification service"""
        try:
            if self.notification_service:
                # This would create the notification through the service
                # For now, we'll just log it
                logger.info(
                    "Creating notification from real-time alert",
                    type=request.type,
                    category=request.category,
                    priority=request.priority,
                    user_id=request.user_id
                )
        except Exception as e:
            logger.error("Error creating notification from real-time alert", error=str(e))
    
    def _determine_priority(self, event_data: Dict[str, Any]) -> NotificationPriority:
        """Determine notification priority from event data"""
        # Map various event indicators to priority levels
        if event_data.get('is_fake', False):
            return NotificationPriority.HIGH
        elif event_data.get('confidence', 0) > 0.8:
            return NotificationPriority.MEDIUM
        else:
            return NotificationPriority.LOW
    
    def _map_threat_level_to_priority(self, threat_level: str) -> NotificationPriority:
        """Map threat level to notification priority"""
        mapping = {
            'critical': NotificationPriority.CRITICAL,
            'high': NotificationPriority.HIGH,
            'medium': NotificationPriority.MEDIUM,
            'low': NotificationPriority.LOW
        }
        return mapping.get(threat_level.lower(), NotificationPriority.MEDIUM)
    
    def _map_system_status_to_priority(self, status: str) -> NotificationPriority:
        """Map system status to notification priority"""
        mapping = {
            'down': NotificationPriority.CRITICAL,
            'degraded': NotificationPriority.HIGH,
            'maintenance': NotificationPriority.MEDIUM,
            'up': NotificationPriority.LOW
        }
        return mapping.get(status.lower(), NotificationPriority.MEDIUM)


# Global consumer instance
_real_time_alerting_consumer: Optional[RealTimeAlertingConsumer] = None


async def get_real_time_alerting_consumer() -> RealTimeAlertingConsumer:
    """Get global real-time alerting consumer instance"""
    global _real_time_alerting_consumer
    
    if _real_time_alerting_consumer is None:
        _real_time_alerting_consumer = RealTimeAlertingConsumer()
    
    return _real_time_alerting_consumer


async def start_real_time_alerting():
    """Start the real-time alerting consumer"""
    consumer = await get_real_time_alerting_consumer()
    await consumer.start()


async def stop_real_time_alerting():
    """Stop the real-time alerting consumer"""
    consumer = await get_real_time_alerting_consumer()
    await consumer.stop()


# Event publishing functions for integration with existing systems

async def publish_analysis_completion_event(
    user_id: str,
    analysis_id: str,
    video_id: str,
    result: Dict[str, Any]
):
    """Publish analysis completion event"""
    try:
        consumer = await get_real_time_alerting_consumer()
        
        event_data = {
            'user_id': user_id,
            'analysis_id': analysis_id,
            'video_id': video_id,
            'result': result.get('is_fake', 'Unknown'),
            'confidence': result.get('confidence_score', 0),
            'event_id': str(uuid.uuid4()),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        await consumer._handle_analysis_completion(event_data)
        
    except Exception as e:
        logger.error("Error publishing analysis completion event", error=str(e))


async def publish_security_alert_event(
    threat_type: str,
    threat_level: str,
    threat_data: Dict[str, Any]
):
    """Publish security alert event"""
    try:
        consumer = await get_real_time_alerting_consumer()
        
        event_data = {
            'threat_type': threat_type,
            'threat_level': threat_level,
            'source': 'morpheus_security',
            'event_id': str(uuid.uuid4()),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **threat_data
        }
        
        await consumer._handle_security_alert(event_data)
        
    except Exception as e:
        logger.error("Error publishing security alert event", error=str(e))


async def publish_system_status_event(
    status: str,
    component: str,
    status_data: Dict[str, Any]
):
    """Publish system status event"""
    try:
        consumer = await get_real_time_alerting_consumer()
        
        event_data = {
            'status': status,
            'component': component,
            'source': 'system_monitor',
            'event_id': str(uuid.uuid4()),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **status_data
        }
        
        await consumer._handle_system_status(event_data)
        
    except Exception as e:
        logger.error("Error publishing system status event", error=str(e))
