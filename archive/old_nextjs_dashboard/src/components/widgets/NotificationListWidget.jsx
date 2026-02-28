/**
 * Virtualized Notification List Widget
 * Efficiently renders large datasets of notifications with dynamic heights
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { VariableSizeList as VariableList } from 'react-window';
import { measureComponentRender } from '@/utils/performanceMonitor';
import { getApiCache } from '@/services/api';
import styles from './NotificationListWidget.module.css';

interface Notification {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'warning' | 'error' | 'success';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  timestamp: Date;
  read: boolean;
  source: string;
  actions?: Array<{
    label: string;
    action: string;
  }>;
}

interface NotificationListWidgetProps {
  className?: string;
  height?: number;
  enableVirtualization?: boolean;
  refreshInterval?: number;
  maxItems?: number;
  onNotificationClick?: (notification: Notification) => void;
}

const NotificationListWidget: React.FC<NotificationListWidgetProps> = ({
  className = '',
  height = 400,
  enableVirtualization = true,
  refreshInterval = 10000,
  maxItems = 1000,
  onNotificationClick,
}) => {
  const renderTimer = useRef<{ end: () => number } | null>(null);
  const apiCache = getApiCache();
  
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    renderTimer.current = measureComponentRender('NotificationListWidget');
    return () => {
      if (renderTimer.current) {
        renderTimer.current.end();
      }
    };
  }, []);

  const loadNotifications = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiCache.request({
        url: '/api/notifications',
        method: 'GET',
        params: { limit: maxItems },
      });
      
      const newNotifications: Notification[] = response.data.map((item: any) => ({
        id: item.id,
        title: item.title,
        message: item.message,
        type: item.type,
        priority: item.priority,
        timestamp: new Date(item.timestamp),
        read: item.read,
        source: item.source,
        actions: item.actions,
      }));
      
      setNotifications(newNotifications);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load notifications');
    } finally {
      setLoading(false);
    }
  }, [apiCache, maxItems]);

  useEffect(() => {
    loadNotifications();
    if (refreshInterval > 0) {
      const interval = setInterval(loadNotifications, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [loadNotifications, refreshInterval]);

  const getItemSize = useCallback((index: number) => {
    const notification = notifications[index];
    const baseHeight = 80;
    const messageHeight = Math.ceil(notification.message.length / 50) * 20;
    const actionsHeight = notification.actions ? notification.actions.length * 30 : 0;
    return baseHeight + messageHeight + actionsHeight;
  }, [notifications]);

  const NotificationItem: React.FC<{ index: number; style: React.CSSProperties }> = ({ index, style, data }) => {
    const notification = data[index];
    
    const getTypeColor = (type: string) => {
      switch (type) {
        case 'info': return '#3b82f6';
        case 'warning': return '#f59e0b';
        case 'error': return '#ef4444';
        case 'success': return '#10b981';
        default: return '#6b7280';
      }
    };

    const getPriorityIcon = (priority: string) => {
      switch (priority) {
        case 'urgent': return '🔴';
        case 'high': return '🟠';
        case 'medium': return '🟡';
        case 'low': return '🟢';
        default: return '⚪';
      }
    };

    const handleClick = () => {
      onNotificationClick?.(notification);
    };

    return (
      <div style={style} className={`${styles.notificationItem} ${notification.read ? styles.read : styles.unread}`}>
        <div className={styles.notificationHeader}>
          <div className={styles.notificationIcon} style={{ color: getTypeColor(notification.type) }}>
            {getPriorityIcon(notification.priority)}
          </div>
          <div className={styles.notificationInfo}>
            <h3 className={styles.notificationTitle}>{notification.title}</h3>
            <p className={styles.notificationSource}>{notification.source}</p>
          </div>
          <div className={styles.notificationTime}>
            {notification.timestamp.toLocaleTimeString()}
          </div>
        </div>
        
        <div className={styles.notificationMessage}>
          {notification.message}
        </div>
        
        {notification.actions && notification.actions.length > 0 && (
          <div className={styles.notificationActions}>
            {notification.actions.map((action, actionIndex) => (
              <button
                key={actionIndex}
                className={styles.actionButton}
                onClick={(e) => {
                  e.stopPropagation();
                  // Handle action
                }}
              >
                {action.label}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  };

  if (loading && notifications.length === 0) {
    return (
      <div className={`${styles.widget} ${className}`}>
        <div className={styles.loadingContainer}>
          <div className={styles.loadingSpinner} />
          <p>Loading notifications...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${styles.widget} ${className}`}>
        <div className={styles.errorContainer}>
          <p>{error}</p>
          <button onClick={loadNotifications}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.widget} ${className}`}>
      <div className={styles.header}>
        <h2>Notifications</h2>
        <div className={styles.stats}>
          {notifications.filter(n => !n.read).length} unread
        </div>
      </div>
      
      <div className={styles.listContainer} style={{ height }}>
        {enableVirtualization ? (
          <VariableList
            height={height}
            itemCount={notifications.length}
            itemSize={getItemSize}
            itemData={notifications}
          >
            {NotificationItem}
          </VariableList>
        ) : (
          <div className={styles.nonVirtualizedList}>
            {notifications.map((notification, index) => (
              <NotificationItem key={notification.id} index={index} style={{}} data={notifications} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default NotificationListWidget;
