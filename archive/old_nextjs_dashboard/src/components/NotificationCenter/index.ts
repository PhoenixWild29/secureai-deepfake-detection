/**
 * Notification Center Components
 * Export all notification center components and utilities
 */

// Main Components
export { default as NotificationCenter } from './NotificationCenter';
export { default as NotificationList } from './NotificationList';
export { default as NotificationItem } from './NotificationItem';
export { default as NotificationPreferences } from './NotificationPreferences';
export { default as NotificationBadge } from './NotificationBadge';

// Re-export types for convenience
export type {
  Notification,
  NotificationAction,
  NotificationMetadata,
  NotificationPreferences,
  NotificationTypePreference,
  DeliveryMethodPreference,
  GlobalNotificationSettings,
  QuietHoursSettings,
  NotificationFrequencySettings,
  RetrySettings,
  RateLimitSettings,
  NotificationFilter,
  NotificationStats,
  WebSocketMessage,
  NotificationContextValue,
  NotificationType,
  NotificationSeverity,
  NotificationPriority,
  NotificationCategory,
  EntityType,
  DeliveryMethod,
  ActionType,
  ActionStyle,
  WebSocketMessageType,
  NotificationCenterProps,
  NotificationListProps,
  NotificationItemProps,
  NotificationPreferencesProps,
  NotificationBadgeProps,
} from '@/types/notifications';

// Re-export services and utilities
export { 
  NotificationService,
  createNotificationService,
  NotificationServiceConfig,
  NotificationServiceEvents
} from '@/services/notificationService';

export { 
  AuditLogger,
  createAuditLogger,
  auditLogger,
  AuditLogEntry,
  AuditEntity,
  AuditAction,
  AuditActionType,
  AuditLoggerConfig
} from '@/utils/auditLogger';

// Re-export context and hooks
export { 
  NotificationProvider,
  useNotificationContext 
} from '@/contexts/NotificationContext';

export { 
  useNotifications,
  UseNotificationsOptions,
  UseNotificationsReturn
} from '@/hooks/useNotifications';

// Re-export default preferences
export { DEFAULT_NOTIFICATION_PREFERENCES } from '@/types/notifications';

// Default export
export default NotificationCenter;
