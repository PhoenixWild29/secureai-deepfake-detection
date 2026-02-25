#!/usr/bin/env python3
"""
Notification Service
Business logic for dashboard notifications management with real-time integration
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, text
from sqlalchemy.exc import IntegrityError
import structlog
import asyncio

from src.models.notifications import (
    Notification,
    NotificationHistory,
    UserNotificationPreferences,
    NotificationType,
    NotificationPriority,
    NotificationStatus,
    DeliveryMethod,
    NotificationCategory,
    NotificationAction,
    CreateNotificationRequest,
    UpdateNotificationRequest,
    NotificationResponse,
    NotificationListResponse,
    NotificationStatsResponse,
    NotificationPreferencesResponse,
    get_default_notification_preferences,
    validate_notification_delivery,
    should_notify_user,
    format_notification_for_delivery
)
from src.dependencies.auth import UserClaims

logger = structlog.get_logger(__name__)


class NotificationService:
    """
    Service for managing dashboard notifications
    Handles CRUD operations, delivery, filtering, and real-time integration
    """
    
    def __init__(self):
        """Initialize notification service"""
        logger.info("NotificationService initialized")
        self._delivery_queue = asyncio.Queue()
        self._processing_active = False
    
    async def create_notification(
        self,
        session: AsyncSession,
        request: CreateNotificationRequest,
        created_by: str = "system"
    ) -> NotificationResponse:
        """
        Create new notification
        
        Args:
            session: Database session
            request: Notification creation request
            created_by: User or system that created the notification
            
        Returns:
            Created notification response
        """
        try:
            logger.info(
                "Creating notification",
                type=request.type,
                category=request.category,
                priority=request.priority,
                user_id=request.user_id
            )
            
            # Validate delivery configuration
            if request.delivery and not validate_notification_delivery(request.delivery):
                raise ValueError("Invalid delivery configuration")
            
            # Create notification record
            notification = Notification(
                user_id=request.user_id,
                type=request.type,
                category=request.category,
                priority=request.priority,
                title=request.content.title,
                message=request.content.message,
                summary=request.content.summary,
                details=request.content.details,
                action_url=request.content.action_url,
                action_text=request.content.action_text,
                delivery_methods=[method.value for method in request.delivery.methods] if request.delivery else ["in_app"],
                scheduled_at=request.delivery.scheduled_at if request.delivery else None,
                expires_at=request.delivery.expires_at if request.delivery else None,
                source=request.metadata.source if request.metadata else None,
                component=request.metadata.component if request.metadata else None,
                event_id=request.metadata.event_id if request.metadata else None,
                analysis_id=request.metadata.analysis_id if request.metadata else None,
                video_id=request.metadata.video_id if request.metadata else None,
                tags=request.tags,
                context=request.metadata.context if request.metadata else {},
                max_retries=request.delivery.max_retries if request.delivery else 3
            )
            
            session.add(notification)
            await session.commit()
            await session.refresh(notification)
            
            # Create audit history record
            await self._create_history_record(
                session, notification.id, "create", created_by, None, None, NotificationStatus.PENDING
            )
            
            # Queue for delivery if not scheduled
            if not notification.scheduled_at or notification.scheduled_at <= datetime.now(timezone.utc):
                await self._queue_for_delivery(notification)
            
            logger.info(
                "Notification created successfully",
                notification_id=notification.id,
                type=notification.type
            )
            
            return self._notification_to_response(notification)
            
        except Exception as e:
            await session.rollback()
            logger.error("Failed to create notification", error=str(e))
            raise
    
    async def get_notifications(
        self,
        session: AsyncSession,
        user_claims: UserClaims,
        limit: int = 50,
        offset: int = 0,
        category: Optional[NotificationCategory] = None,
        status: Optional[NotificationStatus] = None,
        priority: Optional[NotificationPriority] = None,
        unread_only: bool = False
    ) -> NotificationListResponse:
        """
        Get notifications for user with filtering
        
        Args:
            session: Database session
            user_claims: User authentication claims
            limit: Maximum number of notifications
            offset: Number of notifications to skip
            category: Filter by category
            status: Filter by status
            priority: Filter by priority
            unread_only: Return only unread notifications
            
        Returns:
            Notification list response
        """
        try:
            user_id = user_claims.user_id
            logger.info(
                "Retrieving notifications",
                user_id=user_id,
                limit=limit,
                offset=offset,
                category=category,
                status=status,
                priority=priority,
                unread_only=unread_only
            )
            
            # Build query
            stmt = select(Notification).where(
                or_(
                    Notification.user_id == user_id,
                    Notification.user_id.is_(None)  # System-wide notifications
                )
            )
            
            # Apply filters
            if category:
                stmt = stmt.where(Notification.category == category.value)
            
            if status:
                stmt = stmt.where(Notification.status == status.value)
            
            if priority:
                stmt = stmt.where(Notification.priority == priority.value)
            
            if unread_only:
                stmt = stmt.where(
                    and_(
                        Notification.read_at.is_(None),
                        Notification.status.notin_([NotificationStatus.DISMISSED.value, NotificationStatus.FAILED.value])
                    )
                )
            
            # Filter out expired notifications
            stmt = stmt.where(
                or_(
                    Notification.expires_at.is_(None),
                    Notification.expires_at > datetime.now(timezone.utc)
                )
            )
            
            # Get total count
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total_result = await session.execute(count_stmt)
            total_count = total_result.scalar()
            
            # Get unread count
            unread_stmt = select(func.count()).where(
                and_(
                    or_(
                        Notification.user_id == user_id,
                        Notification.user_id.is_(None)
                    ),
                    Notification.read_at.is_(None),
                    Notification.status.notin_([NotificationStatus.DISMISSED.value, NotificationStatus.FAILED.value]),
                    or_(
                        Notification.expires_at.is_(None),
                        Notification.expires_at > datetime.now(timezone.utc)
                    )
                )
            )
            unread_result = await session.execute(unread_stmt)
            unread_count = unread_result.scalar()
            
            # Order and paginate
            stmt = stmt.order_by(
                func.case(
                    (Notification.priority == NotificationPriority.CRITICAL.value, 4),
                    (Notification.priority == NotificationPriority.HIGH.value, 3),
                    (Notification.priority == NotificationPriority.MEDIUM.value, 2),
                    (Notification.priority == NotificationPriority.LOW.value, 1),
                    else_=0
                ).desc(),
                Notification.created_at.desc()
            ).limit(limit).offset(offset)
            
            result = await session.execute(stmt)
            notifications = result.scalars().all()
            
            # Convert to response format
            notification_responses = [self._notification_to_response(notif) for notif in notifications]
            
            logger.info(
                "Notifications retrieved successfully",
                user_id=user_id,
                count=len(notification_responses),
                total_count=total_count,
                unread_count=unread_count
            )
            
            return NotificationListResponse(
                notifications=notification_responses,
                total_count=total_count,
                unread_count=unread_count,
                pagination={
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_count,
                    "total_pages": (total_count + limit - 1) // limit if limit > 0 else 1
                }
            )
            
        except Exception as e:
            logger.error("Failed to retrieve notifications", user_id=user_claims.user_id, error=str(e))
            raise
    
    async def update_notification_status(
        self,
        session: AsyncSession,
        user_claims: UserClaims,
        notification_id: uuid.UUID,
        request: UpdateNotificationRequest
    ) -> NotificationResponse:
        """
        Update notification status (acknowledge, dismiss, mark read, etc.)
        
        Args:
            session: Database session
            user_claims: User authentication claims
            notification_id: Notification ID
            request: Update request with action
            
        Returns:
            Updated notification response
        """
        try:
            user_id = user_claims.user_id
            logger.info(
                "Updating notification status",
                user_id=user_id,
                notification_id=notification_id,
                action=request.action
            )
            
            # Get notification
            stmt = select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    or_(
                        Notification.user_id == user_id,
                        Notification.user_id.is_(None)
                    )
                )
            )
            result = await session.execute(stmt)
            notification = result.scalar_one_or_none()
            
            if not notification:
                raise ValueError(f"Notification {notification_id} not found or access denied")
            
            # Store previous status
            previous_status = notification.status
            
            # Update based on action
            current_time = datetime.now(timezone.utc)
            
            if request.action == NotificationAction.ACKNOWLEDGE:
                notification.status = NotificationStatus.ACKNOWLEDGED
                notification.acknowledged_at = current_time
            
            elif request.action == NotificationAction.DISMISS:
                notification.status = NotificationStatus.DISMISSED
                notification.dismissed_at = current_time
            
            elif request.action == NotificationAction.MARK_READ:
                notification.status = NotificationStatus.READ
                notification.read_at = current_time
            
            elif request.action == NotificationAction.MARK_UNREAD:
                notification.status = NotificationStatus.DELIVERED
                notification.read_at = None
            
            elif request.action == NotificationAction.ARCHIVE:
                notification.status = NotificationStatus.DISMISSED
                notification.dismissed_at = current_time
            
            elif request.action == NotificationAction.RESTORE:
                notification.status = NotificationStatus.DELIVERED
                notification.dismissed_at = None
                notification.read_at = None
            
            notification.updated_at = current_time
            
            await session.commit()
            await session.refresh(notification)
            
            # Create audit history record
            await self._create_history_record(
                session, notification_id, request.action.value, user_id, 
                previous_status, notification.status, request.reason, request.metadata
            )
            
            logger.info(
                "Notification status updated successfully",
                user_id=user_id,
                notification_id=notification_id,
                action=request.action,
                new_status=notification.status
            )
            
            return self._notification_to_response(notification)
            
        except Exception as e:
            await session.rollback()
            logger.error("Failed to update notification status", user_id=user_claims.user_id, error=str(e))
            raise
    
    async def get_notification_stats(
        self,
        session: AsyncSession,
        user_claims: UserClaims
    ) -> NotificationStatsResponse:
        """
        Get notification statistics for user
        
        Args:
            session: Database session
            user_claims: User authentication claims
            
        Returns:
            Notification statistics response
        """
        try:
            user_id = user_claims.user_id
            logger.info("Getting notification statistics", user_id=user_id)
            
            # Use database function for stats
            stmt = text("SELECT get_user_notification_stats(:user_id)")
            result = await session.execute(stmt, {"user_id": user_id})
            stats_data = result.scalar()
            
            # Get recent activity (last 10 actions)
            recent_stmt = select(NotificationHistory).where(
                NotificationHistory.user_id == user_id
            ).order_by(NotificationHistory.created_at.desc()).limit(10)
            
            recent_result = await session.execute(recent_stmt)
            recent_activities = []
            
            for activity in recent_result.scalars().all():
                recent_activities.append({
                    "id": str(activity.id),
                    "action": activity.action,
                    "action_by": activity.action_by,
                    "created_at": activity.created_at.isoformat(),
                    "notification_id": str(activity.notification_id)
                })
            
            logger.info("Notification statistics retrieved successfully", user_id=user_id)
            
            return NotificationStatsResponse(
                total_notifications=stats_data.get("total_notifications", 0),
                unread_count=stats_data.get("unread_count", 0),
                pending_count=stats_data.get("pending_count", 0),
                failed_count=stats_data.get("failed_count", 0),
                category_breakdown=stats_data.get("category_breakdown", {}),
                priority_breakdown=stats_data.get("priority_breakdown", {}),
                recent_activity=recent_activities
            )
            
        except Exception as e:
            logger.error("Failed to get notification statistics", user_id=user_claims.user_id, error=str(e))
            raise
    
    async def get_user_preferences(
        self,
        session: AsyncSession,
        user_claims: UserClaims
    ) -> NotificationPreferencesResponse:
        """
        Get user notification preferences
        
        Args:
            session: Database session
            user_claims: User authentication claims
            
        Returns:
            User notification preferences response
        """
        try:
            user_id = user_claims.user_id
            logger.info("Getting user notification preferences", user_id=user_id)
            
            # Get user preferences
            stmt = select(UserNotificationPreferences).where(
                UserNotificationPreferences.user_id == user_id
            )
            result = await session.execute(stmt)
            preferences = result.scalar_one_or_none()
            
            if not preferences:
                # Return default preferences
                default_prefs = get_default_notification_preferences()
                return NotificationPreferencesResponse(
                    user_id=user_id,
                    enabled=default_prefs["enabled"],
                    delivery_methods=[DeliveryMethod(method) for method in default_prefs["delivery_methods"]],
                    enabled_categories=[NotificationCategory(cat) for cat in default_prefs["enabled_categories"]],
                    priority_filter=NotificationPriority(default_prefs["priority_filter"]),
                    quiet_hours={
                        "start": default_prefs["quiet_hours_start"],
                        "end": default_prefs["quiet_hours_end"]
                    } if default_prefs["quiet_hours_start"] else None,
                    timezone=default_prefs["timezone"],
                    digest_frequency=default_prefs["digest_frequency"],
                    updated_at=datetime.now(timezone.utc)
                )
            
            logger.info("User notification preferences retrieved successfully", user_id=user_id)
            
            return NotificationPreferencesResponse(
                user_id=user_id,
                enabled=preferences.enabled,
                delivery_methods=[DeliveryMethod(method) for method in preferences.delivery_methods],
                enabled_categories=[NotificationCategory(cat) for cat in preferences.enabled_categories],
                priority_filter=NotificationPriority(preferences.priority_filter),
                quiet_hours={
                    "start": preferences.quiet_hours_start,
                    "end": preferences.quiet_hours_end
                } if preferences.quiet_hours_start else None,
                timezone=preferences.timezone,
                digest_frequency=preferences.digest_frequency,
                updated_at=preferences.updated_at
            )
            
        except Exception as e:
            logger.error("Failed to get user notification preferences", user_id=user_claims.user_id, error=str(e))
            raise
    
    async def update_user_preferences(
        self,
        session: AsyncSession,
        user_claims: UserClaims,
        preferences_data: Dict[str, Any]
    ) -> NotificationPreferencesResponse:
        """
        Update user notification preferences
        
        Args:
            session: Database session
            user_claims: User authentication claims
            preferences_data: Updated preferences data
            
        Returns:
            Updated user notification preferences response
        """
        try:
            user_id = user_claims.user_id
            logger.info("Updating user notification preferences", user_id=user_id)
            
            # Get existing preferences
            stmt = select(UserNotificationPreferences).where(
                UserNotificationPreferences.user_id == user_id
            )
            result = await session.execute(stmt)
            preferences = result.scalar_one_or_none()
            
            if preferences:
                # Update existing preferences
                for key, value in preferences_data.items():
                    if hasattr(preferences, key):
                        setattr(preferences, key, value)
                preferences.updated_at = datetime.now(timezone.utc)
            else:
                # Create new preferences
                preferences = UserNotificationPreferences(
                    user_id=user_id,
                    enabled=preferences_data.get("enabled", True),
                    delivery_methods=preferences_data.get("delivery_methods", ["in_app"]),
                    email_address=preferences_data.get("email_address"),
                    phone_number=preferences_data.get("phone_number"),
                    enabled_categories=preferences_data.get("enabled_categories", ["detection", "security", "system"]),
                    priority_filter=preferences_data.get("priority_filter", "low"),
                    quiet_hours_start=preferences_data.get("quiet_hours_start"),
                    quiet_hours_end=preferences_data.get("quiet_hours_end"),
                    timezone=preferences_data.get("timezone", "UTC"),
                    batch_notifications=preferences_data.get("batch_notifications", False),
                    digest_frequency=preferences_data.get("digest_frequency", "immediate"),
                    auto_dismiss_after=preferences_data.get("auto_dismiss_after")
                )
                session.add(preferences)
            
            await session.commit()
            await session.refresh(preferences)
            
            logger.info("User notification preferences updated successfully", user_id=user_id)
            
            return NotificationPreferencesResponse(
                user_id=user_id,
                enabled=preferences.enabled,
                delivery_methods=[DeliveryMethod(method) for method in preferences.delivery_methods],
                enabled_categories=[NotificationCategory(cat) for cat in preferences.enabled_categories],
                priority_filter=NotificationPriority(preferences.priority_filter),
                quiet_hours={
                    "start": preferences.quiet_hours_start,
                    "end": preferences.quiet_hours_end
                } if preferences.quiet_hours_start else None,
                timezone=preferences.timezone,
                digest_frequency=preferences.digest_frequency,
                updated_at=preferences.updated_at
            )
            
        except Exception as e:
            await session.rollback()
            logger.error("Failed to update user notification preferences", user_id=user_claims.user_id, error=str(e))
            raise
    
    async def process_delivery_queue(self):
        """Process pending notifications for delivery"""
        if self._processing_active:
            return
        
        self._processing_active = True
        logger.info("Starting notification delivery processing")
        
        try:
            while True:
                try:
                    # Get notification from queue with timeout
                    notification = await asyncio.wait_for(self._delivery_queue.get(), timeout=1.0)
                    
                    # Process delivery
                    await self._deliver_notification(notification)
                    
                except asyncio.TimeoutError:
                    # No notifications to process, continue
                    continue
                except Exception as e:
                    logger.error("Error processing notification delivery", error=str(e))
                    
        finally:
            self._processing_active = False
            logger.info("Notification delivery processing stopped")
    
    async def cleanup_expired_notifications(self, session: AsyncSession) -> int:
        """Clean up expired notifications"""
        try:
            logger.info("Cleaning up expired notifications")
            
            # Use database function to clean up expired notifications
            stmt = text("SELECT cleanup_expired_notifications()")
            result = await session.execute(stmt)
            cleaned_count = result.scalar()
            
            await session.commit()
            
            logger.info(f"Cleaned up {cleaned_count} expired notifications")
            return cleaned_count
            
        except Exception as e:
            await session.rollback()
            logger.error("Failed to cleanup expired notifications", error=str(e))
            raise
    
    # Private helper methods
    
    async def _create_history_record(
        self,
        session: AsyncSession,
        notification_id: uuid.UUID,
        action: str,
        action_by: str,
        previous_status: Optional[NotificationStatus] = None,
        new_status: Optional[NotificationStatus] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Create notification history record"""
        history_record = NotificationHistory(
            notification_id=notification_id,
            action=action,
            action_by=action_by,
            action_reason=reason,
            previous_status=previous_status.value if previous_status else None,
            new_status=new_status.value if new_status else None,
            metadata=metadata or {}
        )
        
        session.add(history_record)
        await session.commit()
    
    async def _queue_for_delivery(self, notification: Notification):
        """Queue notification for delivery"""
        try:
            await self._delivery_queue.put(notification)
            logger.debug("Notification queued for delivery", notification_id=notification.id)
        except Exception as e:
            logger.error("Failed to queue notification for delivery", notification_id=notification.id, error=str(e))
    
    async def _deliver_notification(self, notification: Notification):
        """Deliver notification through configured methods"""
        try:
            logger.info("Delivering notification", notification_id=notification.id)
            
            # Check if user should receive notification
            if notification.user_id and not await self._should_deliver_to_user(notification):
                logger.info("Notification filtered by user preferences", notification_id=notification.id)
                return
            
            # Deliver through each configured method
            delivery_methods = [DeliveryMethod(method) for method in notification.delivery_methods]
            
            for method in delivery_methods:
                try:
                    await self._deliver_via_method(notification, method)
                except Exception as e:
                    logger.error(
                        "Failed to deliver notification via method",
                        notification_id=notification.id,
                        method=method.value,
                        error=str(e)
                    )
                    
                    # Increment retry count
                    notification.retry_count += 1
                    notification.error_message = str(e)
                    
                    if notification.retry_count >= notification.max_retries:
                        notification.status = NotificationStatus.FAILED
                    else:
                        notification.status = NotificationStatus.PENDING
                        # Re-queue for retry
                        await self._queue_for_delivery(notification)
                    
                    return
            
            # Mark as delivered
            notification.status = NotificationStatus.DELIVERED
            notification.delivered_at = datetime.now(timezone.utc)
            notification.error_message = None
            
            logger.info("Notification delivered successfully", notification_id=notification.id)
            
        except Exception as e:
            logger.error("Failed to deliver notification", notification_id=notification.id, error=str(e))
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)
    
    async def _should_deliver_to_user(self, notification: Notification) -> bool:
        """Check if notification should be delivered to user based on preferences"""
        if not notification.user_id:
            return True  # System-wide notifications always delivered
        
        # This would check user preferences in a real implementation
        # For now, return True (deliver all notifications)
        return True
    
    async def _deliver_via_method(self, notification: Notification, method: DeliveryMethod):
        """Deliver notification via specific method"""
        formatted_notification = format_notification_for_delivery(
            notification.__dict__, method
        )
        
        if method == DeliveryMethod.IN_APP:
            # Deliver via WebSocket (integrate with existing WebSocket infrastructure)
            await self._deliver_via_websocket(notification.user_id, formatted_notification)
        
        elif method == DeliveryMethod.EMAIL:
            # Deliver via email (integrate with email service)
            await self._deliver_via_email(notification.user_id, formatted_notification)
        
        elif method == DeliveryMethod.PUSH:
            # Deliver via push notification (integrate with push service)
            await self._deliver_via_push(notification.user_id, formatted_notification)
        
        elif method == DeliveryMethod.SMS:
            # Deliver via SMS (integrate with SMS service)
            await self._deliver_via_sms(notification.user_id, formatted_notification)
        
        elif method == DeliveryMethod.WEBHOOK:
            # Deliver via webhook (integrate with webhook service)
            await self._deliver_via_webhook(notification.user_id, formatted_notification)
    
    async def _deliver_via_websocket(self, user_id: Optional[str], notification: Dict[str, Any]):
        """Deliver notification via WebSocket"""
        # This would integrate with existing WebSocket infrastructure
        logger.info("Delivering notification via WebSocket", user_id=user_id)
        # Implementation would send to WebSocket handler
    
    async def _deliver_via_email(self, user_id: Optional[str], notification: Dict[str, Any]):
        """Deliver notification via email"""
        # This would integrate with email service
        logger.info("Delivering notification via email", user_id=user_id)
        # Implementation would send email
    
    async def _deliver_via_push(self, user_id: Optional[str], notification: Dict[str, Any]):
        """Deliver notification via push notification"""
        # This would integrate with push notification service
        logger.info("Delivering notification via push", user_id=user_id)
        # Implementation would send push notification
    
    async def _deliver_via_sms(self, user_id: Optional[str], notification: Dict[str, Any]):
        """Deliver notification via SMS"""
        # This would integrate with SMS service
        logger.info("Delivering notification via SMS", user_id=user_id)
        # Implementation would send SMS
    
    async def _deliver_via_webhook(self, user_id: Optional[str], notification: Dict[str, Any]):
        """Deliver notification via webhook"""
        # This would integrate with webhook service
        logger.info("Delivering notification via webhook", user_id=user_id)
        # Implementation would send webhook
    
    def _notification_to_response(self, notification: Notification) -> NotificationResponse:
        """Convert notification model to response"""
        return NotificationResponse(
            id=notification.id,
            user_id=notification.user_id,
            type=NotificationType(notification.type),
            category=NotificationCategory(notification.category),
            priority=NotificationPriority(notification.priority),
            status=NotificationStatus(notification.status),
            title=notification.title,
            message=notification.message,
            summary=notification.summary,
            action_url=notification.action_url,
            action_text=notification.action_text,
            tags=notification.tags,
            created_at=notification.created_at,
            delivered_at=notification.delivered_at,
            read_at=notification.read_at,
            acknowledged_at=notification.acknowledged_at,
            dismissed_at=notification.dismissed_at,
            expires_at=notification.expires_at
        )


# Global service instance
_notification_service: Optional[NotificationService] = None


async def get_notification_service() -> NotificationService:
    """Get global notification service instance"""
    global _notification_service
    
    if _notification_service is None:
        _notification_service = NotificationService()
    
    return _notification_service
