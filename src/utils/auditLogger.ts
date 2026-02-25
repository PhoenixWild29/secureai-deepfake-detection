/**
 * Audit Logger Utility
 * Client-side logging for user interactions with notifications
 */

import { Notification, NotificationAction } from '@/types/notifications';

export interface AuditLogEntry {
  /** Unique log entry identifier */
  id: string;
  /** Log entry timestamp */
  timestamp: Date;
  /** User ID */
  userId: string;
  /** Session ID */
  sessionId: string;
  /** Action performed */
  action: AuditAction;
  /** Target entity */
  entity: AuditEntity;
  /** Additional context */
  context?: Record<string, any>;
  /** User agent */
  userAgent: string;
  /** IP address (if available) */
  ipAddress?: string;
  /** Request ID for correlation */
  requestId?: string;
}

export interface AuditEntity {
  /** Entity type */
  type: 'notification' | 'preference' | 'system';
  /** Entity ID */
  id: string;
  /** Entity data */
  data?: Record<string, any>;
}

export interface AuditAction {
  /** Action type */
  type: AuditActionType;
  /** Action description */
  description: string;
  /** Action parameters */
  parameters?: Record<string, any>;
  /** Action result */
  result?: 'success' | 'failure' | 'partial';
  /** Error message if failed */
  error?: string;
}

export type AuditActionType = 
  | 'notification_read'
  | 'notification_unread'
  | 'notification_dismissed'
  | 'notification_deleted'
  | 'notification_action_triggered'
  | 'notification_clicked'
  | 'preference_updated'
  | 'preference_reset'
  | 'filter_applied'
  | 'filter_cleared'
  | 'search_performed'
  | 'bulk_action_performed'
  | 'notification_center_opened'
  | 'notification_center_closed'
  | 'websocket_connected'
  | 'websocket_disconnected'
  | 'error_occurred';

export interface AuditLoggerConfig {
  /** Whether logging is enabled */
  enabled: boolean;
  /** Log level */
  level: 'debug' | 'info' | 'warn' | 'error';
  /** Maximum log entries to keep in memory */
  maxEntries: number;
  /** Whether to send logs to server */
  sendToServer: boolean;
  /** Server endpoint for log submission */
  serverEndpoint?: string;
  /** Batch size for server submission */
  batchSize: number;
  /** Flush interval in milliseconds */
  flushInterval: number;
  /** Whether to include sensitive data */
  includeSensitiveData: boolean;
}

export class AuditLogger {
  private config: AuditLoggerConfig;
  private logs: AuditLogEntry[] = [];
  private sessionId: string;
  private userId: string;
  private flushTimer?: NodeJS.Timeout;

  constructor(config: Partial<AuditLoggerConfig> = {}) {
    this.config = {
      enabled: config.enabled ?? true,
      level: config.level ?? 'info',
      maxEntries: config.maxEntries ?? 1000,
      sendToServer: config.sendToServer ?? false,
      serverEndpoint: config.serverEndpoint,
      batchSize: config.batchSize ?? 10,
      flushInterval: config.flushInterval ?? 30000, // 30 seconds
      includeSensitiveData: config.includeSensitiveData ?? false,
    };

    this.sessionId = this.generateSessionId();
    this.userId = this.getCurrentUserId();

    if (this.config.sendToServer && this.config.serverEndpoint) {
      this.startFlushTimer();
    }
  }

  /**
   * Log notification read action
   */
  public logNotificationRead(notification: Notification): void {
    this.log({
      action: {
        type: 'notification_read',
        description: `User marked notification as read: ${notification.title}`,
        parameters: {
          notificationId: notification.id,
          notificationType: notification.type,
          notificationSeverity: notification.severity,
        },
        result: 'success',
      },
      entity: {
        type: 'notification',
        id: notification.id,
        data: this.sanitizeNotificationData(notification),
      },
    });
  }

  /**
   * Log notification unread action
   */
  public logNotificationUnread(notification: Notification): void {
    this.log({
      action: {
        type: 'notification_unread',
        description: `User marked notification as unread: ${notification.title}`,
        parameters: {
          notificationId: notification.id,
          notificationType: notification.type,
          notificationSeverity: notification.severity,
        },
        result: 'success',
      },
      entity: {
        type: 'notification',
        id: notification.id,
        data: this.sanitizeNotificationData(notification),
      },
    });
  }

  /**
   * Log notification dismissed action
   */
  public logNotificationDismissed(notification: Notification): void {
    this.log({
      action: {
        type: 'notification_dismissed',
        description: `User dismissed notification: ${notification.title}`,
        parameters: {
          notificationId: notification.id,
          notificationType: notification.type,
          notificationSeverity: notification.severity,
        },
        result: 'success',
      },
      entity: {
        type: 'notification',
        id: notification.id,
        data: this.sanitizeNotificationData(notification),
      },
    });
  }

  /**
   * Log notification deleted action
   */
  public logNotificationDeleted(notification: Notification): void {
    this.log({
      action: {
        type: 'notification_deleted',
        description: `User deleted notification: ${notification.title}`,
        parameters: {
          notificationId: notification.id,
          notificationType: notification.type,
          notificationSeverity: notification.severity,
        },
        result: 'success',
      },
      entity: {
        type: 'notification',
        id: notification.id,
        data: this.sanitizeNotificationData(notification),
      },
    });
  }

  /**
   * Log notification action triggered
   */
  public logNotificationActionTriggered(
    notification: Notification, 
    action: NotificationAction
  ): void {
    this.log({
      action: {
        type: 'notification_action_triggered',
        description: `User triggered notification action: ${action.label}`,
        parameters: {
          notificationId: notification.id,
          actionId: action.id,
          actionType: action.type,
          actionLabel: action.label,
        },
        result: 'success',
      },
      entity: {
        type: 'notification',
        id: notification.id,
        data: this.sanitizeNotificationData(notification),
      },
    });
  }

  /**
   * Log notification clicked
   */
  public logNotificationClicked(notification: Notification): void {
    this.log({
      action: {
        type: 'notification_clicked',
        description: `User clicked notification: ${notification.title}`,
        parameters: {
          notificationId: notification.id,
          notificationType: notification.type,
          notificationSeverity: notification.severity,
        },
        result: 'success',
      },
      entity: {
        type: 'notification',
        id: notification.id,
        data: this.sanitizeNotificationData(notification),
      },
    });
  }

  /**
   * Log preference updated
   */
  public logPreferenceUpdated(
    preferenceType: string, 
    oldValue: any, 
    newValue: any
  ): void {
    this.log({
      action: {
        type: 'preference_updated',
        description: `User updated preference: ${preferenceType}`,
        parameters: {
          preferenceType,
          oldValue: this.sanitizeValue(oldValue),
          newValue: this.sanitizeValue(newValue),
        },
        result: 'success',
      },
      entity: {
        type: 'preference',
        id: preferenceType,
        data: {
          oldValue: this.sanitizeValue(oldValue),
          newValue: this.sanitizeValue(newValue),
        },
      },
    });
  }

  /**
   * Log filter applied
   */
  public logFilterApplied(filter: Record<string, any>): void {
    this.log({
      action: {
        type: 'filter_applied',
        description: 'User applied notification filter',
        parameters: {
          filter: this.sanitizeValue(filter),
        },
        result: 'success',
      },
      entity: {
        type: 'system',
        id: 'filter',
        data: {
          filter: this.sanitizeValue(filter),
        },
      },
    });
  }

  /**
   * Log search performed
   */
  public logSearchPerformed(query: string, resultCount: number): void {
    this.log({
      action: {
        type: 'search_performed',
        description: 'User performed notification search',
        parameters: {
          query: this.sanitizeValue(query),
          resultCount,
        },
        result: 'success',
      },
      entity: {
        type: 'system',
        id: 'search',
        data: {
          query: this.sanitizeValue(query),
          resultCount,
        },
      },
    });
  }

  /**
   * Log bulk action performed
   */
  public logBulkActionPerformed(
    action: string, 
    notificationIds: string[], 
    successCount: number, 
    failureCount: number
  ): void {
    this.log({
      action: {
        type: 'bulk_action_performed',
        description: `User performed bulk action: ${action}`,
        parameters: {
          action,
          notificationCount: notificationIds.length,
          successCount,
          failureCount,
        },
        result: failureCount === 0 ? 'success' : 'partial',
      },
      entity: {
        type: 'system',
        id: 'bulk_action',
        data: {
          action,
          notificationIds: this.sanitizeValue(notificationIds),
          successCount,
          failureCount,
        },
      },
    });
  }

  /**
   * Log notification center opened
   */
  public logNotificationCenterOpened(): void {
    this.log({
      action: {
        type: 'notification_center_opened',
        description: 'User opened notification center',
        result: 'success',
      },
      entity: {
        type: 'system',
        id: 'notification_center',
      },
    });
  }

  /**
   * Log notification center closed
   */
  public logNotificationCenterClosed(): void {
    this.log({
      action: {
        type: 'notification_center_closed',
        description: 'User closed notification center',
        result: 'success',
      },
      entity: {
        type: 'system',
        id: 'notification_center',
      },
    });
  }

  /**
   * Log WebSocket connection status
   */
  public logWebSocketConnection(connected: boolean): void {
    this.log({
      action: {
        type: connected ? 'websocket_connected' : 'websocket_disconnected',
        description: `WebSocket ${connected ? 'connected' : 'disconnected'}`,
        result: 'success',
      },
      entity: {
        type: 'system',
        id: 'websocket',
      },
    });
  }

  /**
   * Log error occurrence
   */
  public logError(error: Error, context?: Record<string, any>): void {
    this.log({
      action: {
        type: 'error_occurred',
        description: `Error occurred: ${error.message}`,
        parameters: {
          errorMessage: error.message,
          errorStack: error.stack,
          context: this.sanitizeValue(context),
        },
        result: 'failure',
        error: error.message,
      },
      entity: {
        type: 'system',
        id: 'error',
        data: {
          errorMessage: error.message,
          errorStack: error.stack,
          context: this.sanitizeValue(context),
        },
      },
    });
  }

  /**
   * Get all logs
   */
  public getLogs(): AuditLogEntry[] {
    return [...this.logs];
  }

  /**
   * Clear all logs
   */
  public clearLogs(): void {
    this.logs = [];
  }

  /**
   * Export logs as JSON
   */
  public exportLogs(): string {
    return JSON.stringify(this.logs, null, 2);
  }

  /**
   * Update configuration
   */
  public updateConfig(config: Partial<AuditLoggerConfig>): void {
    this.config = { ...this.config, ...config };
    
    if (this.config.sendToServer && this.config.serverEndpoint && !this.flushTimer) {
      this.startFlushTimer();
    } else if (!this.config.sendToServer && this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = undefined;
    }
  }

  /**
   * Flush logs to server
   */
  public async flushLogs(): Promise<void> {
    if (!this.config.sendToServer || !this.config.serverEndpoint || this.logs.length === 0) {
      return;
    }

    try {
      const logsToSend = this.logs.splice(0, this.config.batchSize);
      
      await fetch(this.config.serverEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          logs: logsToSend,
          sessionId: this.sessionId,
          userId: this.userId,
        }),
      });
    } catch (error) {
      console.error('Failed to flush audit logs:', error);
      // Re-add logs to the beginning of the array
      this.logs.unshift(...this.logs);
    }
  }

  /**
   * Core logging method
   */
  private log(entry: Omit<AuditLogEntry, 'id' | 'timestamp' | 'userId' | 'sessionId' | 'userAgent'>): void {
    if (!this.config.enabled) {
      return;
    }

    const logEntry: AuditLogEntry = {
      id: this.generateId(),
      timestamp: new Date(),
      userId: this.userId,
      sessionId: this.sessionId,
      userAgent: navigator.userAgent,
      ...entry,
    };

    this.logs.push(logEntry);

    // Remove old logs if we exceed the maximum
    if (this.logs.length > this.config.maxEntries) {
      this.logs = this.logs.slice(-this.config.maxEntries);
    }

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.log('Audit Log:', logEntry);
    }
  }

  /**
   * Generate unique ID
   */
  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Generate session ID
   */
  private generateSessionId(): string {
    return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get current user ID
   */
  private getCurrentUserId(): string {
    // This would typically come from your authentication system
    return 'anonymous';
  }

  /**
   * Start flush timer
   */
  private startFlushTimer(): void {
    this.flushTimer = setInterval(() => {
      this.flushLogs();
    }, this.config.flushInterval);
  }

  /**
   * Sanitize notification data
   */
  private sanitizeNotificationData(notification: Notification): Record<string, any> {
    if (!this.config.includeSensitiveData) {
      return {
        id: notification.id,
        type: notification.type,
        severity: notification.severity,
        priority: notification.priority,
        category: notification.category,
        timestamp: notification.timestamp,
        read: notification.read,
        dismissed: notification.dismissed,
      };
    }
    return notification;
  }

  /**
   * Sanitize value
   */
  private sanitizeValue(value: any): any {
    if (!this.config.includeSensitiveData) {
      if (typeof value === 'string' && value.length > 100) {
        return value.substring(0, 100) + '...';
      }
      if (typeof value === 'object' && value !== null) {
        const sanitized: any = {};
        for (const [key, val] of Object.entries(value)) {
          if (key.toLowerCase().includes('password') || 
              key.toLowerCase().includes('token') || 
              key.toLowerCase().includes('secret')) {
            sanitized[key] = '[REDACTED]';
          } else {
            sanitized[key] = this.sanitizeValue(val);
          }
        }
        return sanitized;
      }
    }
    return value;
  }
}

/**
 * Create audit logger instance
 */
export const createAuditLogger = (config?: Partial<AuditLoggerConfig>): AuditLogger => {
  return new AuditLogger(config);
};

/**
 * Default audit logger instance
 */
export const auditLogger = createAuditLogger();

export default AuditLogger;
