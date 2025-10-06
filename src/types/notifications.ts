/**
 * Notification Types
 * TypeScript interfaces for notification management system
 */

export interface Notification {
  /** Unique notification identifier */
  id: string;
  /** Notification type */
  type: NotificationType;
  /** Notification severity level */
  severity: NotificationSeverity;
  /** Notification title */
  title: string;
  /** Notification message */
  message: string;
  /** Detailed notification description */
  description?: string;
  /** Notification timestamp */
  timestamp: Date;
  /** Whether notification has been read */
  read: boolean;
  /** Whether notification has been dismissed */
  dismissed: boolean;
  /** Notification priority */
  priority: NotificationPriority;
  /** Notification category */
  category: NotificationCategory;
  /** Related entity ID (e.g., analysis ID) */
  entityId?: string;
  /** Related entity type */
  entityType?: EntityType;
  /** Notification actions */
  actions?: NotificationAction[];
  /** Additional notification data */
  data?: Record<string, any>;
  /** Notification metadata */
  metadata?: NotificationMetadata;
  /** Delivery methods used */
  deliveryMethods?: DeliveryMethod[];
  /** Expiration timestamp */
  expiresAt?: Date;
  /** User ID who should receive this notification */
  userId?: string;
  /** Group ID for grouped notifications */
  groupId?: string;
}

export interface NotificationAction {
  /** Action identifier */
  id: string;
  /** Action label */
  label: string;
  /** Action type */
  type: ActionType;
  /** Action URL or handler */
  url?: string;
  /** Action handler function */
  handler?: () => void;
  /** Whether action requires confirmation */
  requiresConfirmation?: boolean;
  /** Action confirmation message */
  confirmationMessage?: string;
  /** Action icon */
  icon?: string;
  /** Action style */
  style?: ActionStyle;
}

export interface NotificationMetadata {
  /** Source system that generated the notification */
  source: string;
  /** Notification version */
  version: string;
  /** Tags for categorization */
  tags?: string[];
  /** Related notification IDs */
  relatedNotifications?: string[];
  /** Notification template used */
  template?: string;
  /** Localization information */
  locale?: string;
  /** Custom metadata */
  custom?: Record<string, any>;
}

export interface NotificationPreferences {
  /** User ID */
  userId: string;
  /** Notification type preferences */
  types: Record<NotificationType, NotificationTypePreference>;
  /** Delivery method preferences */
  deliveryMethods: Record<DeliveryMethod, DeliveryMethodPreference>;
  /** Global notification settings */
  global: GlobalNotificationSettings;
  /** Quiet hours settings */
  quietHours?: QuietHoursSettings;
  /** Notification frequency settings */
  frequency?: NotificationFrequencySettings;
  /** Last updated timestamp */
  updatedAt: Date;
}

export interface NotificationTypePreference {
  /** Whether this notification type is enabled */
  enabled: boolean;
  /** Delivery methods for this type */
  deliveryMethods: DeliveryMethod[];
  /** Priority level */
  priority: NotificationPriority;
  /** Whether to show in-app */
  showInApp: boolean;
  /** Whether to send email */
  sendEmail: boolean;
  /** Whether to send webhook */
  sendWebhook: boolean;
  /** Custom settings for this type */
  custom?: Record<string, any>;
}

export interface DeliveryMethodPreference {
  /** Whether this delivery method is enabled */
  enabled: boolean;
  /** Delivery method configuration */
  config: Record<string, any>;
  /** Retry settings */
  retry?: RetrySettings;
  /** Rate limiting settings */
  rateLimit?: RateLimitSettings;
}

export interface GlobalNotificationSettings {
  /** Whether all notifications are enabled */
  enabled: boolean;
  /** Default delivery methods */
  defaultDeliveryMethods: DeliveryMethod[];
  /** Default priority */
  defaultPriority: NotificationPriority;
  /** Whether to show notification badges */
  showBadges: boolean;
  /** Whether to play notification sounds */
  playSounds: boolean;
  /** Whether to show desktop notifications */
  showDesktopNotifications: boolean;
  /** Maximum notifications to keep in history */
  maxHistoryCount: number;
  /** Auto-dismiss timeout in milliseconds */
  autoDismissTimeout?: number;
}

export interface QuietHoursSettings {
  /** Whether quiet hours are enabled */
  enabled: boolean;
  /** Start time (24-hour format) */
  startTime: string;
  /** End time (24-hour format) */
  endTime: string;
  /** Days of the week (0 = Sunday, 6 = Saturday) */
  days: number[];
  /** Timezone */
  timezone: string;
  /** Whether to allow urgent notifications during quiet hours */
  allowUrgent: boolean;
}

export interface NotificationFrequencySettings {
  /** Maximum notifications per hour */
  maxPerHour: number;
  /** Maximum notifications per day */
  maxPerDay: number;
  /** Whether to group similar notifications */
  groupSimilar: boolean;
  /** Grouping timeout in milliseconds */
  groupingTimeout: number;
}

export interface RetrySettings {
  /** Maximum retry attempts */
  maxAttempts: number;
  /** Retry delay in milliseconds */
  delay: number;
  /** Retry backoff multiplier */
  backoffMultiplier: number;
}

export interface RateLimitSettings {
  /** Maximum requests per minute */
  maxPerMinute: number;
  /** Maximum requests per hour */
  maxPerHour: number;
  /** Rate limit window in milliseconds */
  windowMs: number;
}

export interface NotificationFilter {
  /** Filter by notification type */
  types?: NotificationType[];
  /** Filter by severity */
  severities?: NotificationSeverity[];
  /** Filter by priority */
  priorities?: NotificationPriority[];
  /** Filter by category */
  categories?: NotificationCategory[];
  /** Filter by read status */
  read?: boolean;
  /** Filter by dismissed status */
  dismissed?: boolean;
  /** Filter by date range */
  dateRange?: {
    start: Date;
    end: Date;
  };
  /** Filter by entity type */
  entityTypes?: EntityType[];
  /** Filter by entity ID */
  entityIds?: string[];
  /** Search query */
  searchQuery?: string;
  /** Sort order */
  sortBy?: 'timestamp' | 'priority' | 'severity' | 'title';
  /** Sort direction */
  sortDirection?: 'asc' | 'desc';
  /** Limit results */
  limit?: number;
  /** Offset for pagination */
  offset?: number;
}

export interface NotificationStats {
  /** Total notification count */
  total: number;
  /** Unread notification count */
  unread: number;
  /** Read notification count */
  read: number;
  /** Dismissed notification count */
  dismissed: number;
  /** Notifications by type */
  byType: Record<NotificationType, number>;
  /** Notifications by severity */
  bySeverity: Record<NotificationSeverity, number>;
  /** Notifications by priority */
  byPriority: Record<NotificationPriority, number>;
  /** Notifications by category */
  byCategory: Record<NotificationCategory, number>;
  /** Recent activity (last 24 hours) */
  recentActivity: number;
}

export interface WebSocketMessage {
  /** Message type */
  type: WebSocketMessageType;
  /** Message payload */
  payload: any;
  /** Message timestamp */
  timestamp: Date;
  /** Message ID */
  id: string;
}

export interface NotificationContextValue {
  /** Current notifications */
  notifications: Notification[];
  /** Notification statistics */
  stats: NotificationStats;
  /** User preferences */
  preferences: NotificationPreferences | null;
  /** Loading state */
  loading: boolean;
  /** Error state */
  error: string | null;
  /** WebSocket connection status */
  connected: boolean;
  /** Actions */
  actions: {
    markAsRead: (notificationId: string) => Promise<void>;
    markAsUnread: (notificationId: string) => Promise<void>;
    dismiss: (notificationId: string) => Promise<void>;
    delete: (notificationId: string) => Promise<void>;
    markAllAsRead: () => Promise<void>;
    dismissAll: () => Promise<void>;
    deleteAll: () => Promise<void>;
    refresh: () => Promise<void>;
    updatePreferences: (preferences: Partial<NotificationPreferences>) => Promise<void>;
    filter: (filter: NotificationFilter) => void;
    clearFilter: () => void;
  };
}

export type NotificationType = 
  | 'analysis_complete'
  | 'analysis_failed'
  | 'analysis_started'
  | 'analysis_progress'
  | 'system_error'
  | 'system_warning'
  | 'system_info'
  | 'user_action_required'
  | 'security_alert'
  | 'maintenance_notice'
  | 'feature_update'
  | 'data_export_complete'
  | 'data_export_failed'
  | 'quota_warning'
  | 'quota_exceeded'
  | 'backup_complete'
  | 'backup_failed'
  | 'integration_success'
  | 'integration_failed'
  | 'custom';

export type NotificationSeverity = 'low' | 'medium' | 'high' | 'critical';

export type NotificationPriority = 'low' | 'normal' | 'high' | 'urgent';

export type NotificationCategory = 
  | 'analysis'
  | 'system'
  | 'security'
  | 'maintenance'
  | 'user'
  | 'data'
  | 'integration'
  | 'quota'
  | 'backup'
  | 'custom';

export type EntityType = 
  | 'analysis'
  | 'user'
  | 'system'
  | 'data'
  | 'integration'
  | 'backup'
  | 'quota'
  | 'custom';

export type DeliveryMethod = 'in_app' | 'email' | 'webhook' | 'sms' | 'push';

export type ActionType = 'navigate' | 'dismiss' | 'delete' | 'retry' | 'custom';

export type ActionStyle = 'primary' | 'secondary' | 'danger' | 'success' | 'warning';

export type WebSocketMessageType = 
  | 'notification_created'
  | 'notification_updated'
  | 'notification_deleted'
  | 'preferences_updated'
  | 'connection_status'
  | 'error'
  | 'ping'
  | 'pong';

export interface NotificationCenterProps {
  /** Whether to show the notification center */
  visible?: boolean;
  /** Callback when visibility changes */
  onVisibilityChange?: (visible: boolean) => void;
  /** Initial filter */
  initialFilter?: NotificationFilter;
  /** Whether to show preferences */
  showPreferences?: boolean;
  /** Whether to show statistics */
  showStats?: boolean;
  /** Maximum height */
  maxHeight?: string;
  /** Additional CSS classes */
  className?: string;
}

export interface NotificationListProps {
  /** Notifications to display */
  notifications: Notification[];
  /** Current filter */
  filter?: NotificationFilter;
  /** Loading state */
  loading?: boolean;
  /** Callback when filter changes */
  onFilterChange?: (filter: NotificationFilter) => void;
  /** Callback when notification is clicked */
  onNotificationClick?: (notification: Notification) => void;
  /** Callback when notification action is triggered */
  onActionTrigger?: (notification: Notification, action: NotificationAction) => void;
  /** Additional CSS classes */
  className?: string;
}

export interface NotificationItemProps {
  /** Notification to display */
  notification: Notification;
  /** Whether to show actions */
  showActions?: boolean;
  /** Whether to show timestamp */
  showTimestamp?: boolean;
  /** Whether to show entity information */
  showEntity?: boolean;
  /** Callback when notification is clicked */
  onClick?: (notification: Notification) => void;
  /** Callback when notification action is triggered */
  onAction?: (notification: Notification, action: NotificationAction) => void;
  /** Additional CSS classes */
  className?: string;
}

export interface NotificationPreferencesProps {
  /** Current preferences */
  preferences: NotificationPreferences;
  /** Callback when preferences change */
  onPreferencesChange?: (preferences: Partial<NotificationPreferences>) => void;
  /** Whether to show advanced settings */
  showAdvanced?: boolean;
  /** Additional CSS classes */
  className?: string;
}

export interface NotificationBadgeProps {
  /** Unread count */
  count: number;
  /** Whether to show count */
  showCount?: boolean;
  /** Maximum count to display */
  maxCount?: number;
  /** Badge size */
  size?: 'small' | 'medium' | 'large';
  /** Badge color */
  color?: 'red' | 'blue' | 'green' | 'yellow' | 'purple';
  /** Whether badge is pulsing */
  pulsing?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Default notification preferences
 */
export const DEFAULT_NOTIFICATION_PREFERENCES: NotificationPreferences = {
  userId: '',
  types: {
    analysis_complete: {
      enabled: true,
      deliveryMethods: ['in_app', 'email'],
      priority: 'normal',
      showInApp: true,
      sendEmail: true,
      sendWebhook: false,
    },
    analysis_failed: {
      enabled: true,
      deliveryMethods: ['in_app', 'email'],
      priority: 'high',
      showInApp: true,
      sendEmail: true,
      sendWebhook: false,
    },
    analysis_started: {
      enabled: false,
      deliveryMethods: ['in_app'],
      priority: 'low',
      showInApp: true,
      sendEmail: false,
      sendWebhook: false,
    },
    analysis_progress: {
      enabled: false,
      deliveryMethods: ['in_app'],
      priority: 'low',
      showInApp: true,
      sendEmail: false,
      sendWebhook: false,
    },
    system_error: {
      enabled: true,
      deliveryMethods: ['in_app', 'email'],
      priority: 'high',
      showInApp: true,
      sendEmail: true,
      sendWebhook: true,
    },
    system_warning: {
      enabled: true,
      deliveryMethods: ['in_app'],
      priority: 'normal',
      showInApp: true,
      sendEmail: false,
      sendWebhook: false,
    },
    system_info: {
      enabled: true,
      deliveryMethods: ['in_app'],
      priority: 'low',
      showInApp: true,
      sendEmail: false,
      sendWebhook: false,
    },
    user_action_required: {
      enabled: true,
      deliveryMethods: ['in_app', 'email'],
      priority: 'high',
      showInApp: true,
      sendEmail: true,
      sendWebhook: false,
    },
    security_alert: {
      enabled: true,
      deliveryMethods: ['in_app', 'email', 'webhook'],
      priority: 'urgent',
      showInApp: true,
      sendEmail: true,
      sendWebhook: true,
    },
    maintenance_notice: {
      enabled: true,
      deliveryMethods: ['in_app', 'email'],
      priority: 'normal',
      showInApp: true,
      sendEmail: true,
      sendWebhook: false,
    },
    feature_update: {
      enabled: true,
      deliveryMethods: ['in_app'],
      priority: 'low',
      showInApp: true,
      sendEmail: false,
      sendWebhook: false,
    },
    data_export_complete: {
      enabled: true,
      deliveryMethods: ['in_app', 'email'],
      priority: 'normal',
      showInApp: true,
      sendEmail: true,
      sendWebhook: false,
    },
    data_export_failed: {
      enabled: true,
      deliveryMethods: ['in_app', 'email'],
      priority: 'high',
      showInApp: true,
      sendEmail: true,
      sendWebhook: false,
    },
    quota_warning: {
      enabled: true,
      deliveryMethods: ['in_app', 'email'],
      priority: 'normal',
      showInApp: true,
      sendEmail: true,
      sendWebhook: false,
    },
    quota_exceeded: {
      enabled: true,
      deliveryMethods: ['in_app', 'email', 'webhook'],
      priority: 'urgent',
      showInApp: true,
      sendEmail: true,
      sendWebhook: true,
    },
    backup_complete: {
      enabled: true,
      deliveryMethods: ['in_app'],
      priority: 'low',
      showInApp: true,
      sendEmail: false,
      sendWebhook: false,
    },
    backup_failed: {
      enabled: true,
      deliveryMethods: ['in_app', 'email'],
      priority: 'high',
      showInApp: true,
      sendEmail: true,
      sendWebhook: false,
    },
    integration_success: {
      enabled: true,
      deliveryMethods: ['in_app'],
      priority: 'low',
      showInApp: true,
      sendEmail: false,
      sendWebhook: false,
    },
    integration_failed: {
      enabled: true,
      deliveryMethods: ['in_app', 'email'],
      priority: 'high',
      showInApp: true,
      sendEmail: true,
      sendWebhook: false,
    },
    custom: {
      enabled: true,
      deliveryMethods: ['in_app'],
      priority: 'normal',
      showInApp: true,
      sendEmail: false,
      sendWebhook: false,
    },
  },
  deliveryMethods: {
    in_app: {
      enabled: true,
      config: {},
    },
    email: {
      enabled: true,
      config: {},
    },
    webhook: {
      enabled: false,
      config: {},
    },
    sms: {
      enabled: false,
      config: {},
    },
    push: {
      enabled: false,
      config: {},
    },
  },
  global: {
    enabled: true,
    defaultDeliveryMethods: ['in_app'],
    defaultPriority: 'normal',
    showBadges: true,
    playSounds: true,
    showDesktopNotifications: false,
    maxHistoryCount: 1000,
    autoDismissTimeout: 5000,
  },
  updatedAt: new Date(),
};

export default Notification;