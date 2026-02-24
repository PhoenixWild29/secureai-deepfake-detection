import React, { createContext, useContext, useReducer, useEffect, useCallback, ReactNode } from 'react';
import { 
  Notification, 
  NotificationPreferences, 
  NotificationFilter, 
  NotificationStats,
  NotificationContextValue,
  DEFAULT_NOTIFICATION_PREFERENCES
} from '@/types/notifications';
import { NotificationService, createNotificationService } from '@/services/notificationService';
import { auditLogger } from '@/utils/auditLogger';

// Action types
type NotificationAction = 
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_CONNECTED'; payload: boolean }
  | { type: 'SET_NOTIFICATIONS'; payload: Notification[] }
  | { type: 'ADD_NOTIFICATION'; payload: Notification }
  | { type: 'UPDATE_NOTIFICATION'; payload: Notification }
  | { type: 'REMOVE_NOTIFICATION'; payload: string }
  | { type: 'SET_PREFERENCES'; payload: NotificationPreferences }
  | { type: 'SET_STATS'; payload: NotificationStats }
  | { type: 'SET_FILTER'; payload: NotificationFilter }
  | { type: 'CLEAR_FILTER' }
  | { type: 'MARK_AS_READ'; payload: string }
  | { type: 'MARK_AS_UNREAD'; payload: string }
  | { type: 'DISMISS'; payload: string }
  | { type: 'DELETE'; payload: string }
  | { type: 'MARK_ALL_AS_READ' }
  | { type: 'DISMISS_ALL' }
  | { type: 'DELETE_ALL' };

// State interface
interface NotificationState {
  notifications: Notification[];
  stats: NotificationStats;
  preferences: NotificationPreferences | null;
  loading: boolean;
  error: string | null;
  connected: boolean;
  filter: NotificationFilter;
}

// Initial state
const initialState: NotificationState = {
  notifications: [],
  stats: {
    total: 0,
    unread: 0,
    read: 0,
    dismissed: 0,
    byType: {} as Record<string, number>,
    bySeverity: {} as Record<string, number>,
    byPriority: {} as Record<string, number>,
    byCategory: {} as Record<string, number>,
    recentActivity: 0,
  },
  preferences: null,
  loading: false,
  error: null,
  connected: false,
  filter: {},
};

// Reducer
function notificationReducer(state: NotificationState, action: NotificationAction): NotificationState {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    
    case 'SET_CONNECTED':
      return { ...state, connected: action.payload };
    
    case 'SET_NOTIFICATIONS':
      return { ...state, notifications: action.payload };
    
    case 'ADD_NOTIFICATION':
      return { 
        ...state, 
        notifications: [action.payload, ...state.notifications],
        stats: {
          ...state.stats,
          total: state.stats.total + 1,
          unread: action.payload.read ? state.stats.unread : state.stats.unread + 1,
          read: action.payload.read ? state.stats.read + 1 : state.stats.read,
        }
      };
    
    case 'UPDATE_NOTIFICATION':
      return {
        ...state,
        notifications: state.notifications.map(n => 
          n.id === action.payload.id ? action.payload : n
        ),
        stats: {
          ...state.stats,
          unread: state.notifications.reduce((count, n) => 
            count + (n.id === action.payload.id ? (action.payload.read ? 0 : 1) : (n.read ? 0 : 1)), 0
          ),
          read: state.notifications.reduce((count, n) => 
            count + (n.id === action.payload.id ? (action.payload.read ? 1 : 0) : (n.read ? 1 : 0)), 0
          ),
        }
      };
    
    case 'REMOVE_NOTIFICATION':
      const notificationToRemove = state.notifications.find(n => n.id === action.payload);
      return {
        ...state,
        notifications: state.notifications.filter(n => n.id !== action.payload),
        stats: {
          ...state.stats,
          total: state.stats.total - 1,
          unread: notificationToRemove && !notificationToRemove.read ? state.stats.unread - 1 : state.stats.unread,
          read: notificationToRemove && notificationToRemove.read ? state.stats.read - 1 : state.stats.read,
        }
      };
    
    case 'SET_PREFERENCES':
      return { ...state, preferences: action.payload };
    
    case 'SET_STATS':
      return { ...state, stats: action.payload };
    
    case 'SET_FILTER':
      return { ...state, filter: action.payload };
    
    case 'CLEAR_FILTER':
      return { ...state, filter: {} };
    
    case 'MARK_AS_READ':
      return {
        ...state,
        notifications: state.notifications.map(n => 
          n.id === action.payload ? { ...n, read: true } : n
        ),
        stats: {
          ...state.stats,
          unread: Math.max(0, state.stats.unread - 1),
          read: state.stats.read + 1,
        }
      };
    
    case 'MARK_AS_UNREAD':
      return {
        ...state,
        notifications: state.notifications.map(n => 
          n.id === action.payload ? { ...n, read: false } : n
        ),
        stats: {
          ...state.stats,
          unread: state.stats.unread + 1,
          read: Math.max(0, state.stats.read - 1),
        }
      };
    
    case 'DISMISS':
      return {
        ...state,
        notifications: state.notifications.map(n => 
          n.id === action.payload ? { ...n, dismissed: true } : n
        ),
        stats: {
          ...state.stats,
          dismissed: state.stats.dismissed + 1,
        }
      };
    
    case 'DELETE':
      const notificationToDelete = state.notifications.find(n => n.id === action.payload);
      return {
        ...state,
        notifications: state.notifications.filter(n => n.id !== action.payload),
        stats: {
          ...state.stats,
          total: state.stats.total - 1,
          unread: notificationToDelete && !notificationToDelete.read ? state.stats.unread - 1 : state.stats.unread,
          read: notificationToDelete && notificationToDelete.read ? state.stats.read - 1 : state.stats.read,
          dismissed: notificationToDelete && notificationToDelete.dismissed ? state.stats.dismissed - 1 : state.stats.dismissed,
        }
      };
    
    case 'MARK_ALL_AS_READ':
      return {
        ...state,
        notifications: state.notifications.map(n => ({ ...n, read: true })),
        stats: {
          ...state.stats,
          unread: 0,
          read: state.stats.total,
        }
      };
    
    case 'DISMISS_ALL':
      return {
        ...state,
        notifications: state.notifications.map(n => ({ ...n, dismissed: true })),
        stats: {
          ...state.stats,
          dismissed: state.stats.total,
        }
      };
    
    case 'DELETE_ALL':
      return {
        ...state,
        notifications: [],
        stats: {
          total: 0,
          unread: 0,
          read: 0,
          dismissed: 0,
          byType: {} as Record<string, number>,
          bySeverity: {} as Record<string, number>,
          byPriority: {} as Record<string, number>,
          byCategory: {} as Record<string, number>,
          recentActivity: 0,
        }
      };
    
    default:
      return state;
  }
}

// Context
const NotificationContext = createContext<NotificationContextValue | null>(null);

// Provider props
interface NotificationProviderProps {
  children: ReactNode;
  serviceConfig?: {
    websocketUrl?: string;
    apiBaseUrl?: string;
    authToken?: string;
  };
}

// Provider component
export const NotificationProvider: React.FC<NotificationProviderProps> = ({ 
  children, 
  serviceConfig 
}) => {
  const [state, dispatch] = useReducer(notificationReducer, initialState);
  const [service, setService] = React.useState<NotificationService | null>(null);

  // Initialize service
  useEffect(() => {
    const notificationService = createNotificationService(serviceConfig, {
      onNotificationReceived: (notification) => {
        dispatch({ type: 'ADD_NOTIFICATION', payload: notification });
      },
      onNotificationUpdated: (notification) => {
        dispatch({ type: 'UPDATE_NOTIFICATION', payload: notification });
      },
      onNotificationDeleted: (notificationId) => {
        dispatch({ type: 'REMOVE_NOTIFICATION', payload: notificationId });
      },
      onPreferencesUpdated: (preferences) => {
        dispatch({ type: 'SET_PREFERENCES', payload: preferences });
      },
      onConnectionStatusChanged: (connected) => {
        dispatch({ type: 'SET_CONNECTED', payload: connected });
      },
      onError: (error) => {
        dispatch({ type: 'SET_ERROR', payload: error.message });
      },
    });

    setService(notificationService);
    
    // Connect to WebSocket
    notificationService.connect().catch(error => {
      console.error('Failed to connect to notification service:', error);
      dispatch({ type: 'SET_ERROR', payload: error.message });
    });

    return () => {
      notificationService.disconnect();
    };
  }, [serviceConfig]);

  // Load initial data
  useEffect(() => {
    if (!service) return;

    const loadInitialData = async () => {
      try {
        dispatch({ type: 'SET_LOADING', payload: true });
        
        const [notifications, stats, preferences] = await Promise.all([
          service.getNotifications(),
          service.getNotificationStats(),
          service.getPreferences(),
        ]);

        dispatch({ type: 'SET_NOTIFICATIONS', payload: notifications });
        dispatch({ type: 'SET_STATS', payload: stats });
        dispatch({ type: 'SET_PREFERENCES', payload: preferences });
        
      } catch (error) {
        console.error('Failed to load initial data:', error);
        dispatch({ type: 'SET_ERROR', payload: (error as Error).message });
      } finally {
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    };

    loadInitialData();
  }, [service]);

  // Actions
  const markAsRead = useCallback(async (notificationId: string) => {
    if (!service) return;
    
    try {
      await service.markAsRead(notificationId);
      dispatch({ type: 'MARK_AS_READ', payload: notificationId });
      
      const notification = state.notifications.find(n => n.id === notificationId);
      if (notification) {
        auditLogger.logNotificationRead(notification);
      }
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
      dispatch({ type: 'SET_ERROR', payload: (error as Error).message });
    }
  }, [service, state.notifications]);

  const markAsUnread = useCallback(async (notificationId: string) => {
    if (!service) return;
    
    try {
      await service.markAsUnread(notificationId);
      dispatch({ type: 'MARK_AS_UNREAD', payload: notificationId });
      
      const notification = state.notifications.find(n => n.id === notificationId);
      if (notification) {
        auditLogger.logNotificationUnread(notification);
      }
    } catch (error) {
      console.error('Failed to mark notification as unread:', error);
      dispatch({ type: 'SET_ERROR', payload: (error as Error).message });
    }
  }, [service, state.notifications]);

  const dismiss = useCallback(async (notificationId: string) => {
    if (!service) return;
    
    try {
      await service.dismiss(notificationId);
      dispatch({ type: 'DISMISS', payload: notificationId });
      
      const notification = state.notifications.find(n => n.id === notificationId);
      if (notification) {
        auditLogger.logNotificationDismissed(notification);
      }
    } catch (error) {
      console.error('Failed to dismiss notification:', error);
      dispatch({ type: 'SET_ERROR', payload: (error as Error).message });
    }
  }, [service, state.notifications]);

  const deleteNotification = useCallback(async (notificationId: string) => {
    if (!service) return;
    
    try {
      await service.delete(notificationId);
      dispatch({ type: 'DELETE', payload: notificationId });
      
      const notification = state.notifications.find(n => n.id === notificationId);
      if (notification) {
        auditLogger.logNotificationDeleted(notification);
      }
    } catch (error) {
      console.error('Failed to delete notification:', error);
      dispatch({ type: 'SET_ERROR', payload: (error as Error).message });
    }
  }, [service, state.notifications]);

  const markAllAsRead = useCallback(async () => {
    if (!service) return;
    
    try {
      await service.markAllAsRead();
      dispatch({ type: 'MARK_ALL_AS_READ' });
      
      const unreadNotifications = state.notifications.filter(n => !n.read);
      unreadNotifications.forEach(notification => {
        auditLogger.logNotificationRead(notification);
      });
    } catch (error) {
      console.error('Failed to mark all notifications as read:', error);
      dispatch({ type: 'SET_ERROR', payload: (error as Error).message });
    }
  }, [service, state.notifications]);

  const dismissAll = useCallback(async () => {
    if (!service) return;
    
    try {
      await service.dismissAll();
      dispatch({ type: 'DISMISS_ALL' });
      
      const activeNotifications = state.notifications.filter(n => !n.dismissed);
      activeNotifications.forEach(notification => {
        auditLogger.logNotificationDismissed(notification);
      });
    } catch (error) {
      console.error('Failed to dismiss all notifications:', error);
      dispatch({ type: 'SET_ERROR', payload: (error as Error).message });
    }
  }, [service, state.notifications]);

  const deleteAll = useCallback(async () => {
    if (!service) return;
    
    try {
      await service.deleteAll();
      dispatch({ type: 'DELETE_ALL' });
      
      state.notifications.forEach(notification => {
        auditLogger.logNotificationDeleted(notification);
      });
    } catch (error) {
      console.error('Failed to delete all notifications:', error);
      dispatch({ type: 'SET_ERROR', payload: (error as Error).message });
    }
  }, [service, state.notifications]);

  const refresh = useCallback(async () => {
    if (!service) return;
    
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      
      const [notifications, stats] = await Promise.all([
        service.getNotifications(state.filter),
        service.getNotificationStats(),
      ]);

      dispatch({ type: 'SET_NOTIFICATIONS', payload: notifications });
      dispatch({ type: 'SET_STATS', payload: stats });
      
    } catch (error) {
      console.error('Failed to refresh notifications:', error);
      dispatch({ type: 'SET_ERROR', payload: (error as Error).message });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, [service, state.filter]);

  const updatePreferences = useCallback(async (preferences: Partial<NotificationPreferences>) => {
    if (!service) return;
    
    try {
      const updatedPreferences = await service.updatePreferences(preferences);
      dispatch({ type: 'SET_PREFERENCES', payload: updatedPreferences });
      
      auditLogger.logPreferenceUpdated('notification_preferences', state.preferences, updatedPreferences);
    } catch (error) {
      console.error('Failed to update preferences:', error);
      dispatch({ type: 'SET_ERROR', payload: (error as Error).message });
    }
  }, [service, state.preferences]);

  const filter = useCallback((filter: NotificationFilter) => {
    dispatch({ type: 'SET_FILTER', payload: filter });
    auditLogger.logFilterApplied(filter);
  }, []);

  const clearFilter = useCallback(() => {
    dispatch({ type: 'CLEAR_FILTER' });
  }, []);

  // Context value
  const contextValue: NotificationContextValue = {
    notifications: state.notifications,
    stats: state.stats,
    preferences: state.preferences,
    loading: state.loading,
    error: state.error,
    connected: state.connected,
    actions: {
      markAsRead,
      markAsUnread,
      dismiss,
      delete: deleteNotification,
      markAllAsRead,
      dismissAll,
      deleteAll,
      refresh,
      updatePreferences,
      filter,
      clearFilter,
    },
  };

  return (
    <NotificationContext.Provider value={contextValue}>
      {children}
    </NotificationContext.Provider>
  );
};

// Hook to use notification context
export const useNotificationContext = (): NotificationContextValue => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotificationContext must be used within a NotificationProvider');
  }
  return context;
};

export default NotificationContext;
