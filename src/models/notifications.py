#!/usr/bin/env python3
"""
Notifications Data Models
SQLModel schemas for dashboard notifications management with real-time integration
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union
from uuid import uuid4, UUID
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, DateTime, JSON, Index, UniqueConstraint, Text, Boolean
from sqlalchemy.sql import func
from pydantic import BaseModel, Field as PydanticField, validator
from enum import Enum


class NotificationType(str, Enum):
    """Notification types for different categories"""
    ANALYSIS_COMPLETION = "analysis_completion"
    SYSTEM_STATUS = "system_status"
    COMPLIANCE_ALERT = "compliance_alert"
    SECURITY_ALERT = "security_alert"
    USER_ACTIVITY = "user_activity"
    MAINTENANCE = "maintenance"
    PERFORMANCE_ALERT = "performance_alert"
    BLOCKCHAIN_UPDATE = "blockchain_update"
    EXPORT_COMPLETION = "export_completion"
    TRAINING_COMPLETION = "training_completion"


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class NotificationStatus(str, Enum):
    """Notification delivery and read status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    READ = "read"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    FAILED = "failed"


class DeliveryMethod(str, Enum):
    """Notification delivery methods"""
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"
    WEBHOOK = "webhook"


class NotificationCategory(str, Enum):
    """Notification categories for filtering"""
    DETECTION = "detection"
    SECURITY = "security"
    SYSTEM = "system"
    COMPLIANCE = "compliance"
    USER = "user"
    MAINTENANCE = "maintenance"
    PERFORMANCE = "performance"
    BLOCKCHAIN = "blockchain"
    EXPORT = "export"
    TRAINING = "training"


class NotificationAction(str, Enum):
    """Available notification actions"""
    ACKNOWLEDGE = "acknowledge"
    DISMISS = "dismiss"
    MARK_READ = "mark_read"
    MARK_UNREAD = "mark_unread"
    ARCHIVE = "archive"
    RESTORE = "restore"


class NotificationContent(BaseModel):
    """Notification content model"""
    title: str = PydanticField(..., min_length=1, max_length=200, description="Notification title")
    message: str = PydanticField(..., min_length=1, max_length=1000, description="Notification message")
    summary: Optional[str] = PydanticField(default=None, max_length=500, description="Brief summary")
    details: Optional[Dict[str, Any]] = PydanticField(default_factory=dict, description="Additional details")
    action_url: Optional[str] = PydanticField(default=None, description="URL for action button")
    action_text: Optional[str] = PydanticField(default=None, description="Text for action button")
    
    @validator('title')
    def validate_title(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Title cannot be empty")
        return v.strip()
    
    @validator('message')
    def validate_message(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Message cannot be empty")
        return v.strip()


class NotificationMetadata(BaseModel):
    """Notification metadata for additional context"""
    source: Optional[str] = PydanticField(default=None, description="Source system or component")
    component: Optional[str] = PydanticField(default=None, description="Specific component that generated the notification")
    event_id: Optional[str] = PydanticField(default=None, description="Related event identifier")
    analysis_id: Optional[str] = PydanticField(default=None, description="Related analysis identifier")
    video_id: Optional[str] = PydanticField(default=None, description="Related video identifier")
    user_id: Optional[str] = PydanticField(default=None, description="Related user identifier")
    tags: List[str] = PydanticField(default_factory=list, description="Notification tags")
    context: Dict[str, Any] = PydanticField(default_factory=dict, description="Additional context data")
    
    @validator('tags')
    def validate_tags(cls, v):
        # Remove duplicates and empty tags
        return list(set(tag.strip() for tag in v if tag and tag.strip()))


class NotificationDelivery(BaseModel):
    """Notification delivery configuration"""
    methods: List[DeliveryMethod] = PydanticField(default_factory=lambda: [DeliveryMethod.IN_APP], description="Delivery methods")
    priority: NotificationPriority = PydanticField(default=NotificationPriority.MEDIUM, description="Delivery priority")
    scheduled_at: Optional[datetime] = PydanticField(default=None, description="Scheduled delivery time")
    expires_at: Optional[datetime] = PydanticField(default=None, description="Notification expiration time")
    retry_count: int = PydanticField(default=0, ge=0, le=5, description="Retry count for failed deliveries")
    max_retries: int = PydanticField(default=3, ge=0, le=5, description="Maximum retry attempts")
    
    @validator('methods')
    def validate_methods(cls, v):
        if not v:
            raise ValueError("At least one delivery method must be specified")
        return list(set(v))  # Remove duplicates


# Database Models
class Notification(SQLModel, table=True):
    """Main notifications database model"""
    __tablename__ = "notifications"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: Optional[str] = Field(default=None, index=True, description="Target user ID (None for system-wide)")
    type: NotificationType = Field(..., description="Notification type")
    category: NotificationCategory = Field(..., description="Notification category")
    priority: NotificationPriority = Field(default=NotificationPriority.MEDIUM, description="Notification priority")
    status: NotificationStatus = Field(default=NotificationStatus.PENDING, description="Delivery status")
    
    # Content
    title: str = Field(..., max_length=200, description="Notification title")
    message: str = Field(sa_column=Column(Text), description="Notification message")
    summary: Optional[str] = Field(default=None, max_length=500, description="Brief summary")
    details: Dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict, description="Additional details")
    
    # Actions
    action_url: Optional[str] = Field(default=None, description="URL for action button")
    action_text: Optional[str] = Field(default=None, description="Text for action button")
    
    # Delivery
    delivery_methods: List[str] = Field(sa_column=Column(JSON), default_factory=lambda: ["in_app"], description="Delivery methods")
    scheduled_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)), description="Scheduled delivery time")
    expires_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)), description="Notification expiration time")
    
    # Metadata
    source: Optional[str] = Field(default=None, description="Source system or component")
    component: Optional[str] = Field(default=None, description="Specific component")
    event_id: Optional[str] = Field(default=None, description="Related event identifier")
    analysis_id: Optional[str] = Field(default=None, description="Related analysis identifier")
    video_id: Optional[str] = Field(default=None, description="Related video identifier")
    tags: List[str] = Field(sa_column=Column(JSON), default_factory=list, description="Notification tags")
    context: Dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict, description="Additional context")
    
    # Status tracking
    delivered_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)), description="Delivery timestamp")
    read_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)), description="Read timestamp")
    acknowledged_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)), description="Acknowledgment timestamp")
    dismissed_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)), description="Dismissal timestamp")
    
    # Retry and error handling
    retry_count: int = Field(default=0, ge=0, le=5, description="Retry count")
    max_retries: int = Field(default=3, ge=0, le=5, description="Maximum retries")
    error_message: Optional[str] = Field(default=None, description="Error message for failed deliveries")
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
        description="Last update timestamp"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_notifications_user_id", "user_id"),
        Index("idx_notifications_type", "type"),
        Index("idx_notifications_category", "category"),
        Index("idx_notifications_priority", "priority"),
        Index("idx_notifications_status", "status"),
        Index("idx_notifications_created_at", "created_at"),
        Index("idx_notifications_delivered_at", "delivered_at"),
        Index("idx_notifications_read_at", "read_at"),
        Index("idx_notifications_expires_at", "expires_at"),
        Index("idx_notifications_user_status", "user_id", "status"),
        Index("idx_notifications_type_priority", "type", "priority"),
    )


class NotificationHistory(SQLModel, table=True):
    """Notification history for audit trail"""
    __tablename__ = "notification_history"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    notification_id: UUID = Field(..., index=True, description="Reference to notification")
    user_id: Optional[str] = Field(default=None, index=True, description="User ID")
    action: NotificationAction = Field(..., description="Action performed")
    action_by: str = Field(..., description="User who performed the action")
    action_reason: Optional[str] = Field(default=None, description="Reason for action")
    previous_status: Optional[NotificationStatus] = Field(default=None, description="Previous status")
    new_status: Optional[NotificationStatus] = Field(default=None, description="New status")
    metadata: Dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict, description="Action metadata")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="Action timestamp"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_notification_history_notification_id", "notification_id"),
        Index("idx_notification_history_user_id", "user_id"),
        Index("idx_notification_history_action", "action"),
        Index("idx_notification_history_created_at", "created_at"),
    )


class UserNotificationPreferences(SQLModel, table=True):
    """User notification preferences"""
    __tablename__ = "user_notification_preferences"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(..., index=True, description="User identifier")
    
    # Delivery preferences
    enabled: bool = Field(default=True, description="Enable notifications for user")
    delivery_methods: List[str] = Field(sa_column=Column(JSON), default_factory=lambda: ["in_app"], description="Preferred delivery methods")
    email_address: Optional[str] = Field(default=None, description="Email address for notifications")
    phone_number: Optional[str] = Field(default=None, description="Phone number for SMS notifications")
    
    # Category preferences
    enabled_categories: List[str] = Field(sa_column=Column(JSON), default_factory=lambda: ["detection", "security", "system"], description="Enabled notification categories")
    priority_filter: NotificationPriority = Field(default=NotificationPriority.LOW, description="Minimum priority to receive")
    
    # Timing preferences
    quiet_hours_start: Optional[str] = Field(default=None, description="Quiet hours start time (HH:MM)")
    quiet_hours_end: Optional[str] = Field(default=None, description="Quiet hours end time (HH:MM)")
    timezone: str = Field(default="UTC", description="User timezone")
    
    # Advanced preferences
    batch_notifications: bool = Field(default=False, description="Batch notifications together")
    digest_frequency: str = Field(default="immediate", description="Digest frequency (immediate, hourly, daily)")
    auto_dismiss_after: Optional[int] = Field(default=None, description="Auto dismiss after hours")
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
        description="Last update timestamp"
    )
    
    # Constraints
    __table_args__ = (
        Index("idx_user_notification_preferences_user_id", "user_id"),
        UniqueConstraint("user_id", name="uq_user_notification_preferences_user_id"),
    )


# API Request/Response Models
class CreateNotificationRequest(BaseModel):
    """Request model for creating notifications"""
    user_id: Optional[str] = PydanticField(default=None, description="Target user ID (None for system-wide)")
    type: NotificationType = PydanticField(..., description="Notification type")
    category: NotificationCategory = PydanticField(..., description="Notification category")
    priority: NotificationPriority = PydanticField(default=NotificationPriority.MEDIUM, description="Notification priority")
    content: NotificationContent = PydanticField(..., description="Notification content")
    metadata: Optional[NotificationMetadata] = PydanticField(default_factory=NotificationMetadata, description="Notification metadata")
    delivery: Optional[NotificationDelivery] = PydanticField(default_factory=NotificationDelivery, description="Delivery configuration")
    tags: List[str] = PydanticField(default_factory=list, description="Notification tags")


class UpdateNotificationRequest(BaseModel):
    """Request model for updating notifications"""
    action: NotificationAction = PydanticField(..., description="Action to perform")
    reason: Optional[str] = PydanticField(default=None, description="Reason for action")
    metadata: Optional[Dict[str, Any]] = PydanticField(default_factory=dict, description="Additional metadata")


class NotificationResponse(BaseModel):
    """Response model for notifications"""
    id: UUID = PydanticField(..., description="Notification ID")
    user_id: Optional[str] = PydanticField(default=None, description="Target user ID")
    type: NotificationType = PydanticField(..., description="Notification type")
    category: NotificationCategory = PydanticField(..., description="Notification category")
    priority: NotificationPriority = PydanticField(..., description="Notification priority")
    status: NotificationStatus = PydanticField(..., description="Notification status")
    title: str = PydanticField(..., description="Notification title")
    message: str = PydanticField(..., description="Notification message")
    summary: Optional[str] = PydanticField(default=None, description="Brief summary")
    action_url: Optional[str] = PydanticField(default=None, description="Action URL")
    action_text: Optional[str] = PydanticField(default=None, description="Action text")
    tags: List[str] = PydanticField(default_factory=list, description="Notification tags")
    created_at: datetime = PydanticField(..., description="Creation timestamp")
    delivered_at: Optional[datetime] = PydanticField(default=None, description="Delivery timestamp")
    read_at: Optional[datetime] = PydanticField(default=None, description="Read timestamp")
    acknowledged_at: Optional[datetime] = PydanticField(default=None, description="Acknowledgment timestamp")
    dismissed_at: Optional[datetime] = PydanticField(default=None, description="Dismissal timestamp")
    expires_at: Optional[datetime] = PydanticField(default=None, description="Expiration timestamp")


class NotificationListResponse(BaseModel):
    """Response model for notification lists"""
    notifications: List[NotificationResponse] = PydanticField(..., description="List of notifications")
    total_count: int = PydanticField(..., description="Total number of notifications")
    unread_count: int = PydanticField(..., description="Number of unread notifications")
    pagination: Dict[str, Any] = PydanticField(..., description="Pagination information")


class NotificationStatsResponse(BaseModel):
    """Response model for notification statistics"""
    total_notifications: int = PydanticField(..., description="Total notifications")
    unread_count: int = PydanticField(..., description="Unread notifications")
    pending_count: int = PydanticField(..., description="Pending notifications")
    failed_count: int = PydanticField(..., description="Failed notifications")
    category_breakdown: Dict[str, int] = PydanticField(..., description="Notifications by category")
    priority_breakdown: Dict[str, int] = PydanticField(..., description="Notifications by priority")
    recent_activity: List[Dict[str, Any]] = PydanticField(..., description="Recent notification activity")


class NotificationPreferencesResponse(BaseModel):
    """Response model for user notification preferences"""
    user_id: str = PydanticField(..., description="User ID")
    enabled: bool = PydanticField(..., description="Notifications enabled")
    delivery_methods: List[DeliveryMethod] = PydanticField(..., description="Preferred delivery methods")
    enabled_categories: List[NotificationCategory] = PydanticField(..., description="Enabled categories")
    priority_filter: NotificationPriority = PydanticField(..., description="Minimum priority filter")
    quiet_hours: Optional[Dict[str, str]] = PydanticField(default=None, description="Quiet hours")
    timezone: str = PydanticField(..., description="User timezone")
    digest_frequency: str = PydanticField(..., description="Digest frequency")
    updated_at: datetime = PydanticField(..., description="Last update timestamp")


# Utility Functions
def get_default_notification_preferences() -> Dict[str, Any]:
    """Get default notification preferences"""
    return {
        "enabled": True,
        "delivery_methods": ["in_app"],
        "enabled_categories": ["detection", "security", "system"],
        "priority_filter": "low",
        "quiet_hours_start": None,
        "quiet_hours_end": None,
        "timezone": "UTC",
        "batch_notifications": False,
        "digest_frequency": "immediate",
        "auto_dismiss_after": None
    }


def validate_notification_delivery(delivery: NotificationDelivery) -> bool:
    """Validate notification delivery configuration"""
    if not delivery.methods:
        return False
    
    if delivery.scheduled_at and delivery.scheduled_at <= datetime.now(timezone.utc):
        return False
    
    if delivery.expires_at and delivery.expires_at <= datetime.now(timezone.utc):
        return False
    
    if delivery.scheduled_at and delivery.expires_at and delivery.scheduled_at >= delivery.expires_at:
        return False
    
    return True


def should_notify_user(user_preferences: Dict[str, Any], notification: Dict[str, Any]) -> bool:
    """Check if notification should be sent to user based on preferences"""
    if not user_preferences.get("enabled", True):
        return False
    
    # Check category filter
    enabled_categories = user_preferences.get("enabled_categories", [])
    if notification.get("category") not in enabled_categories:
        return False
    
    # Check priority filter
    user_min_priority = user_preferences.get("priority_filter", "low")
    notification_priority = notification.get("priority", "medium")
    
    priority_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    if priority_levels.get(notification_priority, 2) < priority_levels.get(user_min_priority, 1):
        return False
    
    # Check quiet hours
    quiet_start = user_preferences.get("quiet_hours_start")
    quiet_end = user_preferences.get("quiet_hours_end")
    if quiet_start and quiet_end:
        current_time = datetime.now().time()
        start_time = datetime.strptime(quiet_start, "%H:%M").time()
        end_time = datetime.strptime(quiet_end, "%H:%M").time()
        
        if start_time <= end_time:
            # Same day quiet hours
            if start_time <= current_time <= end_time:
                return False
        else:
            # Overnight quiet hours
            if current_time >= start_time or current_time <= end_time:
                return False
    
    return True


def format_notification_for_delivery(notification: Dict[str, Any], delivery_method: DeliveryMethod) -> Dict[str, Any]:
    """Format notification for specific delivery method"""
    formatted = {
        "id": str(notification["id"]),
        "type": notification["type"],
        "category": notification["category"],
        "priority": notification["priority"],
        "title": notification["title"],
        "message": notification["message"],
        "summary": notification.get("summary"),
        "action_url": notification.get("action_url"),
        "action_text": notification.get("action_text"),
        "created_at": notification["created_at"].isoformat() if isinstance(notification["created_at"], datetime) else notification["created_at"],
        "tags": notification.get("tags", [])
    }
    
    # Add delivery method specific formatting
    if delivery_method == DeliveryMethod.EMAIL:
        formatted["subject"] = f"[{notification['priority'].upper()}] {notification['title']}"
        formatted["html_content"] = f"<h2>{notification['title']}</h2><p>{notification['message']}</p>"
    
    elif delivery_method == DeliveryMethod.PUSH:
        formatted["badge"] = 1
        formatted["sound"] = "default"
        formatted["data"] = notification.get("metadata", {})
    
    elif delivery_method == DeliveryMethod.WEBHOOK:
        formatted["payload"] = {
            "notification": formatted,
            "metadata": notification.get("metadata", {}),
            "delivery_method": delivery_method.value
        }
    
    return formatted
