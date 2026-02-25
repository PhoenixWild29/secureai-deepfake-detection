import { useCallback, useMemo } from 'react';
import { 
  Notification, 
  NotificationFilter, 
  NotificationPreferences,
  NotificationType,
  NotificationSeverity,
  NotificationPriority,
  NotificationCategory,
  EntityType
} from '@/types/notifications';
import { useNotificationContext } from '@/contexts/NotificationContext';
import { auditLogger } from '@/utils/auditLogger';

export interface UseNotificationsOptions {
  /** Initial filter */
  initialFilter?: NotificationFilter;
  /** Whether to auto-refresh */
  autoRefresh?: boolean;
  /** Refresh interval in milliseconds */
  refreshInterval?: number;
}

export interface UseNotificationsReturn {
  // State
  notifications: Notification[];
  filteredNotifications: Notification[];
  stats: ReturnType<typeof useNotificationContext>['stats'];
  preferences: NotificationPreferences | null;
  loading: boolean;
  error: string | null;
  connected: boolean;
  
  // Filtering
  filter: NotificationFilter;
  setFilter: (filter: NotificationFilter) => void;
  clearFilter: () => void;
  
  // Actions
  markAsRead: (notificationId: string) => Promise<void>;
  markAsUnread: (notificationId: string) => Promise<void>;
  dismiss: (notificationId: string) => Promise<void>;
  deleteNotification: (notificationId: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  dismissAll: () => Promise<void>;
  deleteAll: () => Promise<void>;
  refresh: () => Promise<void>;
  updatePreferences: (preferences: Partial<NotificationPreferences>) => Promise<void>;
  
  // Utility functions
  getNotificationsByType: (type: NotificationType) => Notification[];
  getNotificationsBySeverity: (severity: NotificationSeverity) => Notification[];
  getNotificationsByPriority: (priority: NotificationPriority) => Notification[];
  getNotificationsByCategory: (category: NotificationCategory) => Notification[];
  getUnreadNotifications: () => Notification[];
  getReadNotifications: () => Notification[];
  getDismissedNotifications: () => Notification[];
  getNotificationsByEntity: (entityType: EntityType, entityId?: string) => Notification[];
  searchNotifications: (query: string) => Notification[];
  
  // Computed values
  unreadCount: number;
  hasUnreadNotifications: boolean;
  hasNotifications: boolean;
  isLoading: boolean;
  hasError: boolean;
  isConnected: boolean;
}

/**
 * Custom hook for notification management
 */
export const useNotifications = (options: UseNotificationsOptions = {}): UseNotificationsReturn => {
  const context = useNotificationContext();
  const { initialFilter, autoRefresh, refreshInterval = 30000 } = options;

  // Initialize filter
  const filter = initialFilter || {};

  // Computed values
  const unreadCount = useMemo(() => context.stats.unread, [context.stats.unread]);
  const hasUnreadNotifications = useMemo(() => unreadCount > 0, [unreadCount]);
  const hasNotifications = useMemo(() => context.notifications.length > 0, [context.notifications.length]);
  const isLoading = useMemo(() => context.loading, [context.loading]);
  const hasError = useMemo(() => !!context.error, [context.error]);
  const isConnected = useMemo(() => context.connected, [context.connected]);

  // Filter notifications
  const filteredNotifications = useMemo(() => {
    let filtered = [...context.notifications];

    // Filter by type
    if (filter.types && filter.types.length > 0) {
      filtered = filtered.filter(n => filter.types!.includes(n.type));
    }

    // Filter by severity
    if (filter.severities && filter.severities.length > 0) {
      filtered = filtered.filter(n => filter.severities!.includes(n.severity));
    }

    // Filter by priority
    if (filter.priorities && filter.priorities.length > 0) {
      filtered = filtered.filter(n => filter.priorities!.includes(n.priority));
    }

    // Filter by category
    if (filter.categories && filter.categories.length > 0) {
      filtered = filtered.filter(n => filter.categories!.includes(n.category));
    }

    // Filter by read status
    if (filter.read !== undefined) {
      filtered = filtered.filter(n => n.read === filter.read);
    }

    // Filter by dismissed status
    if (filter.dismissed !== undefined) {
      filtered = filtered.filter(n => n.dismissed === filter.dismissed);
    }

    // Filter by date range
    if (filter.dateRange) {
      filtered = filtered.filter(n => {
        const notificationDate = n.timestamp.getTime();
        return notificationDate >= filter.dateRange!.start.getTime() && 
               notificationDate <= filter.dateRange!.end.getTime();
      });
    }

    // Filter by entity type
    if (filter.entityTypes && filter.entityTypes.length > 0) {
      filtered = filtered.filter(n => n.entityType && filter.entityTypes!.includes(n.entityType));
    }

    // Filter by entity ID
    if (filter.entityIds && filter.entityIds.length > 0) {
      filtered = filtered.filter(n => n.entityId && filter.entityIds!.includes(n.entityId));
    }

    // Search query
    if (filter.searchQuery) {
      const query = filter.searchQuery.toLowerCase();
      filtered = filtered.filter(n => 
        n.title.toLowerCase().includes(query) ||
        n.message.toLowerCase().includes(query) ||
        (n.description && n.description.toLowerCase().includes(query))
      );
    }

    // Sort
    if (filter.sortBy) {
      filtered.sort((a, b) => {
        let comparison = 0;
        
        switch (filter.sortBy) {
          case 'timestamp':
            comparison = a.timestamp.getTime() - b.timestamp.getTime();
            break;
          case 'priority':
            const priorityOrder = { urgent: 4, high: 3, normal: 2, low: 1 };
            comparison = priorityOrder[a.priority] - priorityOrder[b.priority];
            break;
          case 'severity':
            const severityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
            comparison = severityOrder[a.severity] - severityOrder[b.severity];
            break;
          case 'title':
            comparison = a.title.localeCompare(b.title);
            break;
        }
        
        return filter.sortDirection === 'desc' ? -comparison : comparison;
      });
    }

    // Limit and offset
    if (filter.offset) {
      filtered = filtered.slice(filter.offset);
    }
    if (filter.limit) {
      filtered = filtered.slice(0, filter.limit);
    }

    return filtered;
  }, [context.notifications, filter]);

  // Enhanced actions with audit logging
  const markAsRead = useCallback(async (notificationId: string) => {
    const notification = context.notifications.find(n => n.id === notificationId);
    if (notification) {
      auditLogger.logNotificationRead(notification);
    }
    await context.actions.markAsRead(notificationId);
  }, [context.actions, context.notifications]);

  const markAsUnread = useCallback(async (notificationId: string) => {
    const notification = context.notifications.find(n => n.id === notificationId);
    if (notification) {
      auditLogger.logNotificationUnread(notification);
    }
    await context.actions.markAsUnread(notificationId);
  }, [context.actions, context.notifications]);

  const dismiss = useCallback(async (notificationId: string) => {
    const notification = context.notifications.find(n => n.id === notificationId);
    if (notification) {
      auditLogger.logNotificationDismissed(notification);
    }
    await context.actions.dismiss(notificationId);
  }, [context.actions, context.notifications]);

  const deleteNotification = useCallback(async (notificationId: string) => {
    const notification = context.notifications.find(n => n.id === notificationId);
    if (notification) {
      auditLogger.logNotificationDeleted(notification);
    }
    await context.actions.delete(notificationId);
  }, [context.actions, context.notifications]);

  const markAllAsRead = useCallback(async () => {
    await context.actions.markAllAsRead();
  }, [context.actions]);

  const dismissAll = useCallback(async () => {
    await context.actions.dismissAll();
  }, [context.actions]);

  const deleteAll = useCallback(async () => {
    await context.actions.deleteAll();
  }, [context.actions]);

  const refresh = useCallback(async () => {
    await context.actions.refresh();
  }, [context.actions]);

  const updatePreferences = useCallback(async (preferences: Partial<NotificationPreferences>) => {
    await context.actions.updatePreferences(preferences);
  }, [context.actions]);

  const setFilter = useCallback((newFilter: NotificationFilter) => {
    context.actions.filter(newFilter);
  }, [context.actions]);

  const clearFilter = useCallback(() => {
    context.actions.clearFilter();
  }, [context.actions]);

  // Utility functions
  const getNotificationsByType = useCallback((type: NotificationType) => {
    return context.notifications.filter(n => n.type === type);
  }, [context.notifications]);

  const getNotificationsBySeverity = useCallback((severity: NotificationSeverity) => {
    return context.notifications.filter(n => n.severity === severity);
  }, [context.notifications]);

  const getNotificationsByPriority = useCallback((priority: NotificationPriority) => {
    return context.notifications.filter(n => n.priority === priority);
  }, [context.notifications]);

  const getNotificationsByCategory = useCallback((category: NotificationCategory) => {
    return context.notifications.filter(n => n.category === category);
  }, [context.notifications]);

  const getUnreadNotifications = useCallback(() => {
    return context.notifications.filter(n => !n.read);
  }, [context.notifications]);

  const getReadNotifications = useCallback(() => {
    return context.notifications.filter(n => n.read);
  }, [context.notifications]);

  const getDismissedNotifications = useCallback(() => {
    return context.notifications.filter(n => n.dismissed);
  }, [context.notifications]);

  const getNotificationsByEntity = useCallback((entityType: EntityType, entityId?: string) => {
    return context.notifications.filter(n => 
      n.entityType === entityType && 
      (entityId === undefined || n.entityId === entityId)
    );
  }, [context.notifications]);

  const searchNotifications = useCallback((query: string) => {
    const lowerQuery = query.toLowerCase();
    return context.notifications.filter(n => 
      n.title.toLowerCase().includes(lowerQuery) ||
      n.message.toLowerCase().includes(lowerQuery) ||
      (n.description && n.description.toLowerCase().includes(lowerQuery))
    );
  }, [context.notifications]);

  return {
    // State
    notifications: context.notifications,
    filteredNotifications,
    stats: context.stats,
    preferences: context.preferences,
    loading: context.loading,
    error: context.error,
    connected: context.connected,
    
    // Filtering
    filter,
    setFilter,
    clearFilter,
    
    // Actions
    markAsRead,
    markAsUnread,
    dismiss,
    deleteNotification,
    markAllAsRead,
    dismissAll,
    deleteAll,
    refresh,
    updatePreferences,
    
    // Utility functions
    getNotificationsByType,
    getNotificationsBySeverity,
    getNotificationsByPriority,
    getNotificationsByCategory,
    getUnreadNotifications,
    getReadNotifications,
    getDismissedNotifications,
    getNotificationsByEntity,
    searchNotifications,
    
    // Computed values
    unreadCount,
    hasUnreadNotifications,
    hasNotifications,
    isLoading,
    hasError,
    isConnected,
  };
};

export default useNotifications;