/**
 * Notification Service
 * WebSocket and API service for notification management
 */

import { 
  Notification, 
  NotificationPreferences, 
  NotificationFilter, 
  NotificationStats,
  WebSocketMessage,
  WebSocketMessageType,
  DEFAULT_NOTIFICATION_PREFERENCES
} from '@/types/notifications';
import { auditLogger } from '@/utils/auditLogger';

export interface NotificationServiceConfig {
  /** WebSocket URL */
  websocketUrl: string;
  /** API base URL */
  apiBaseUrl: string;
  /** Reconnection settings */
  reconnect: {
    enabled: boolean;
    maxAttempts: number;
    delay: number;
    backoffMultiplier: number;
  };
  /** Heartbeat settings */
  heartbeat: {
    enabled: boolean;
    interval: number;
    timeout: number;
  };
  /** Request timeout */
  timeout: number;
  /** Authentication token */
  authToken?: string;
}

export interface NotificationServiceEvents {
  /** Notification received */
  onNotificationReceived?: (notification: Notification) => void;
  /** Notification updated */
  onNotificationUpdated?: (notification: Notification) => void;
  /** Notification deleted */
  onNotificationDeleted?: (notificationId: string) => void;
  /** Preferences updated */
  onPreferencesUpdated?: (preferences: NotificationPreferences) => void;
  /** Connection status changed */
  onConnectionStatusChanged?: (connected: boolean) => void;
  /** Error occurred */
  onError?: (error: Error) => void;
}

export class NotificationService {
  private config: Required<NotificationServiceConfig>;
  private events: NotificationServiceEvents;
  private websocket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private heartbeatTimer?: NodeJS.Timeout;
  private heartbeatTimeout?: NodeJS.Timeout;
  private isConnecting = false;
  private isConnected = false;

  constructor(config: Partial<NotificationServiceConfig>, events: NotificationServiceEvents = {}) {
    this.config = {
      websocketUrl: config.websocketUrl || 'ws://localhost:8000/ws/notifications',
      apiBaseUrl: config.apiBaseUrl || 'http://localhost:8000/api',
      reconnect: {
        enabled: config.reconnect?.enabled ?? true,
        maxAttempts: config.reconnect?.maxAttempts ?? 5,
        delay: config.reconnect?.delay ?? 1000,
        backoffMultiplier: config.reconnect?.backoffMultiplier ?? 2,
      },
      heartbeat: {
        enabled: config.heartbeat?.enabled ?? true,
        interval: config.heartbeat?.interval ?? 30000,
        timeout: config.heartbeat?.timeout ?? 5000,
      },
      timeout: config.timeout || 10000,
      authToken: config.authToken,
    };

    this.events = events;
  }

  /**
   * Connect to WebSocket
   */
  public async connect(): Promise<void> {
    if (this.isConnecting || this.isConnected) {
      return;
    }

    this.isConnecting = true;

    try {
      const wsUrl = this.config.authToken 
        ? `${this.config.websocketUrl}?token=${this.config.authToken}`
        : this.config.websocketUrl;

      this.websocket = new WebSocket(wsUrl);

      this.websocket.onopen = () => {
        this.isConnected = true;
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        
        auditLogger.logWebSocketConnection(true);
        this.events.onConnectionStatusChanged?.(true);
        
        if (this.config.heartbeat.enabled) {
          this.startHeartbeat();
        }
      };

      this.websocket.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.handleWebSocketMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
          auditLogger.logError(error as Error, { message: event.data });
        }
      };

      this.websocket.onclose = (event) => {
        this.isConnected = false;
        this.isConnecting = false;
        this.stopHeartbeat();
        
        auditLogger.logWebSocketConnection(false);
        this.events.onConnectionStatusChanged?.(false);

        if (this.config.reconnect.enabled && !event.wasClean) {
          this.scheduleReconnect();
        }
      };

      this.websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        auditLogger.logError(new Error('WebSocket error'), { error });
        this.events.onError?.(new Error('WebSocket connection error'));
      };

    } catch (error) {
      this.isConnecting = false;
      auditLogger.logError(error as Error, { action: 'websocket_connect' });
      throw error;
    }
  }

  /**
   * Disconnect from WebSocket
   */
  public disconnect(): void {
    if (this.websocket) {
      this.websocket.close(1000, 'Client disconnect');
      this.websocket = null;
    }
    
    this.stopHeartbeat();
    this.isConnected = false;
    this.isConnecting = false;
  }

  /**
   * Get notifications with filter
   */
  public async getNotifications(filter: NotificationFilter = {}): Promise<Notification[]> {
    try {
      const params = new URLSearchParams();
      
      if (filter.types) params.append('types', filter.types.join(','));
      if (filter.severities) params.append('severities', filter.severities.join(','));
      if (filter.priorities) params.append('priorities', filter.priorities.join(','));
      if (filter.categories) params.append('categories', filter.categories.join(','));
      if (filter.read !== undefined) params.append('read', filter.read.toString());
      if (filter.dismissed !== undefined) params.append('dismissed', filter.dismissed.toString());
      if (filter.dateRange) {
        params.append('start', filter.dateRange.start.toISOString());
        params.append('end', filter.dateRange.end.toISOString());
      }
      if (filter.entityTypes) params.append('entityTypes', filter.entityTypes.join(','));
      if (filter.entityIds) params.append('entityIds', filter.entityIds.join(','));
      if (filter.searchQuery) params.append('search', filter.searchQuery);
      if (filter.sortBy) params.append('sortBy', filter.sortBy);
      if (filter.sortDirection) params.append('sortDirection', filter.sortDirection);
      if (filter.limit) params.append('limit', filter.limit.toString());
      if (filter.offset) params.append('offset', filter.offset.toString());

      const response = await this.fetchWithTimeout(
        `${this.config.apiBaseUrl}/notifications?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch notifications: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return data.map((notification: any) => this.transformNotification(notification));

    } catch (error) {
      auditLogger.logError(error as Error, { action: 'get_notifications', filter });
      throw error;
    }
  }

  /**
   * Get notification statistics
   */
  public async getNotificationStats(): Promise<NotificationStats> {
    try {
      const response = await this.fetchWithTimeout(`${this.config.apiBaseUrl}/notifications/stats`);

      if (!response.ok) {
        throw new Error(`Failed to fetch notification stats: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return this.transformNotificationStats(data);

    } catch (error) {
      auditLogger.logError(error as Error, { action: 'get_notification_stats' });
      throw error;
    }
  }

  /**
   * Get user preferences
   */
  public async getPreferences(): Promise<NotificationPreferences> {
    try {
      const response = await this.fetchWithTimeout(`${this.config.apiBaseUrl}/notifications/preferences`);

      if (!response.ok) {
        if (response.status === 404) {
          // Return default preferences if none exist
          return DEFAULT_NOTIFICATION_PREFERENCES;
        }
        throw new Error(`Failed to fetch preferences: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return this.transformPreferences(data);

    } catch (error) {
      auditLogger.logError(error as Error, { action: 'get_preferences' });
      throw error;
    }
  }

  /**
   * Update user preferences
   */
  public async updatePreferences(preferences: Partial<NotificationPreferences>): Promise<NotificationPreferences> {
    try {
      const response = await this.fetchWithTimeout(
        `${this.config.apiBaseUrl}/notifications/preferences`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(preferences),
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to update preferences: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      const updatedPreferences = this.transformPreferences(data);
      
      this.events.onPreferencesUpdated?.(updatedPreferences);
      return updatedPreferences;

    } catch (error) {
      auditLogger.logError(error as Error, { action: 'update_preferences', preferences });
      throw error;
    }
  }

  /**
   * Mark notification as read
   */
  public async markAsRead(notificationId: string): Promise<void> {
    try {
      const response = await this.fetchWithTimeout(
        `${this.config.apiBaseUrl}/notifications/${notificationId}/read`,
        { method: 'POST' }
      );

      if (!response.ok) {
        throw new Error(`Failed to mark notification as read: ${response.status} ${response.statusText}`);
      }

    } catch (error) {
      auditLogger.logError(error as Error, { action: 'mark_as_read', notificationId });
      throw error;
    }
  }

  /**
   * Mark notification as unread
   */
  public async markAsUnread(notificationId: string): Promise<void> {
    try {
      const response = await this.fetchWithTimeout(
        `${this.config.apiBaseUrl}/notifications/${notificationId}/unread`,
        { method: 'POST' }
      );

      if (!response.ok) {
        throw new Error(`Failed to mark notification as unread: ${response.status} ${response.statusText}`);
      }

    } catch (error) {
      auditLogger.logError(error as Error, { action: 'mark_as_unread', notificationId });
      throw error;
    }
  }

  /**
   * Dismiss notification
   */
  public async dismiss(notificationId: string): Promise<void> {
    try {
      const response = await this.fetchWithTimeout(
        `${this.config.apiBaseUrl}/notifications/${notificationId}/dismiss`,
        { method: 'POST' }
      );

      if (!response.ok) {
        throw new Error(`Failed to dismiss notification: ${response.status} ${response.statusText}`);
      }

    } catch (error) {
      auditLogger.logError(error as Error, { action: 'dismiss_notification', notificationId });
      throw error;
    }
  }

  /**
   * Delete notification
   */
  public async delete(notificationId: string): Promise<void> {
    try {
      const response = await this.fetchWithTimeout(
        `${this.config.apiBaseUrl}/notifications/${notificationId}`,
        { method: 'DELETE' }
      );

      if (!response.ok) {
        throw new Error(`Failed to delete notification: ${response.status} ${response.statusText}`);
      }

    } catch (error) {
      auditLogger.logError(error as Error, { action: 'delete_notification', notificationId });
      throw error;
    }
  }

  /**
   * Mark all notifications as read
   */
  public async markAllAsRead(): Promise<void> {
    try {
      const response = await this.fetchWithTimeout(
        `${this.config.apiBaseUrl}/notifications/mark-all-read`,
        { method: 'POST' }
      );

      if (!response.ok) {
        throw new Error(`Failed to mark all notifications as read: ${response.status} ${response.statusText}`);
      }

    } catch (error) {
      auditLogger.logError(error as Error, { action: 'mark_all_as_read' });
      throw error;
    }
  }

  /**
   * Dismiss all notifications
   */
  public async dismissAll(): Promise<void> {
    try {
      const response = await this.fetchWithTimeout(
        `${this.config.apiBaseUrl}/notifications/dismiss-all`,
        { method: 'POST' }
      );

      if (!response.ok) {
        throw new Error(`Failed to dismiss all notifications: ${response.status} ${response.statusText}`);
      }

    } catch (error) {
      auditLogger.logError(error as Error, { action: 'dismiss_all' });
      throw error;
    }
  }

  /**
   * Delete all notifications
   */
  public async deleteAll(): Promise<void> {
    try {
      const response = await this.fetchWithTimeout(
        `${this.config.apiBaseUrl}/notifications/delete-all`,
        { method: 'DELETE' }
      );

      if (!response.ok) {
        throw new Error(`Failed to delete all notifications: ${response.status} ${response.statusText}`);
      }

    } catch (error) {
      auditLogger.logError(error as Error, { action: 'delete_all' });
      throw error;
    }
  }

  /**
   * Get connection status
   */
  public isWebSocketConnected(): boolean {
    return this.isConnected && this.websocket?.readyState === WebSocket.OPEN;
  }

  /**
   * Send WebSocket message
   */
  public sendWebSocketMessage(type: WebSocketMessageType, payload: any): void {
    if (!this.isWebSocketConnected()) {
      throw new Error('WebSocket is not connected');
    }

    const message: WebSocketMessage = {
      id: this.generateId(),
      type,
      payload,
      timestamp: new Date(),
    };

    this.websocket!.send(JSON.stringify(message));
  }

  /**
   * Handle WebSocket message
   */
  private handleWebSocketMessage(message: WebSocketMessage): void {
    switch (message.type) {
      case 'notification_created':
        this.events.onNotificationReceived?.(this.transformNotification(message.payload));
        break;
      case 'notification_updated':
        this.events.onNotificationUpdated?.(this.transformNotification(message.payload));
        break;
      case 'notification_deleted':
        this.events.onNotificationDeleted?.(message.payload.id);
        break;
      case 'preferences_updated':
        this.events.onPreferencesUpdated?.(this.transformPreferences(message.payload));
        break;
      case 'ping':
        this.sendWebSocketMessage('pong', { timestamp: new Date() });
        break;
      case 'error':
        this.events.onError?.(new Error(message.payload.message));
        break;
      default:
        console.warn('Unknown WebSocket message type:', message.type);
    }
  }

  /**
   * Schedule reconnection
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.reconnect.maxAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    const delay = this.config.reconnect.delay * Math.pow(this.config.reconnect.backoffMultiplier, this.reconnectAttempts);
    
    setTimeout(() => {
      this.reconnectAttempts++;
      this.connect();
    }, delay);
  }

  /**
   * Start heartbeat
   */
  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(() => {
      this.sendWebSocketMessage('ping', { timestamp: new Date() });
      
      this.heartbeatTimeout = setTimeout(() => {
        console.warn('Heartbeat timeout, reconnecting...');
        this.disconnect();
        this.connect();
      }, this.config.heartbeat.timeout);
    }, this.config.heartbeat.interval);
  }

  /**
   * Stop heartbeat
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = undefined;
    }
    
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = undefined;
    }
  }

  /**
   * Fetch with timeout
   */
  private async fetchWithTimeout(url: string, options: RequestInit = {}): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          ...options.headers,
          ...(this.config.authToken && { Authorization: `Bearer ${this.config.authToken}` }),
        },
      });

      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }

  /**
   * Transform notification from API
   */
  private transformNotification(data: any): Notification {
    return {
      id: data.id,
      type: data.type,
      severity: data.severity,
      title: data.title,
      message: data.message,
      description: data.description,
      timestamp: new Date(data.timestamp),
      read: data.read,
      dismissed: data.dismissed,
      priority: data.priority,
      category: data.category,
      entityId: data.entity_id,
      entityType: data.entity_type,
      actions: data.actions?.map((action: any) => ({
        id: action.id,
        label: action.label,
        type: action.type,
        url: action.url,
        requiresConfirmation: action.requires_confirmation,
        confirmationMessage: action.confirmation_message,
        icon: action.icon,
        style: action.style,
      })),
      data: data.data,
      metadata: data.metadata,
      deliveryMethods: data.delivery_methods,
      expiresAt: data.expires_at ? new Date(data.expires_at) : undefined,
      userId: data.user_id,
      groupId: data.group_id,
    };
  }

  /**
   * Transform preferences from API
   */
  private transformPreferences(data: any): NotificationPreferences {
    return {
      userId: data.user_id,
      types: data.types,
      deliveryMethods: data.delivery_methods,
      global: data.global,
      quietHours: data.quiet_hours,
      frequency: data.frequency,
      updatedAt: new Date(data.updated_at),
    };
  }

  /**
   * Transform notification stats from API
   */
  private transformNotificationStats(data: any): NotificationStats {
    return {
      total: data.total,
      unread: data.unread,
      read: data.read,
      dismissed: data.dismissed,
      byType: data.by_type,
      bySeverity: data.by_severity,
      byPriority: data.by_priority,
      byCategory: data.by_category,
      recentActivity: data.recent_activity,
    };
  }

  /**
   * Generate unique ID
   */
  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}

/**
 * Create notification service instance
 */
export const createNotificationService = (
  config?: Partial<NotificationServiceConfig>,
  events?: NotificationServiceEvents
): NotificationService => {
  return new NotificationService(config, events);
};

export default NotificationService;
