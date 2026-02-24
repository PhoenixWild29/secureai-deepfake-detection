import React, { useState, useEffect } from 'react';
import { 
  BellIcon,
  XMarkIcon,
  CogIcon,
  ChartBarIcon,
  AdjustmentsHorizontalIcon,
  ChevronDownIcon,
  ChevronUpIcon
} from '@heroicons/react/24/outline';
import { 
  NotificationCenterProps, 
  NotificationFilter,
  Notification,
  NotificationAction
} from '@/types/notifications';
import { useNotifications } from '@/hooks/useNotifications';
import { auditLogger } from '@/utils/auditLogger';
import NotificationList from './NotificationList';
import NotificationPreferences from './NotificationPreferences';
import NotificationBadge from './NotificationBadge';
import styles from './NotificationCenter.module.css';

/**
 * NotificationCenter component
 * Main component to orchestrate notification display, history, and preferences
 */
export const NotificationCenter: React.FC<NotificationCenterProps> = ({
  visible = false,
  onVisibilityChange,
  initialFilter = {},
  showPreferences = true,
  showStats = true,
  maxHeight = '600px',
  className = '',
}) => {
  const [activeTab, setActiveTab] = useState<'notifications' | 'preferences' | 'stats'>('notifications');
  const [isCollapsed, setIsCollapsed] = useState(false);
  
  const {
    notifications,
    filteredNotifications,
    stats,
    preferences,
    loading,
    error,
    connected,
    filter,
    setFilter,
    clearFilter,
    markAsRead,
    markAsUnread,
    dismiss,
    deleteNotification,
    markAllAsRead,
    dismissAll,
    deleteAll,
    refresh,
    updatePreferences,
    unreadCount,
    hasUnreadNotifications,
    hasNotifications,
    isLoading,
    hasError,
    isConnected,
  } = useNotifications({ initialFilter });

  // Log visibility changes
  useEffect(() => {
    if (visible) {
      auditLogger.logNotificationCenterOpened();
    } else {
      auditLogger.logNotificationCenterClosed();
    }
  }, [visible]);

  // Handle visibility change
  const handleVisibilityChange = (newVisible: boolean) => {
    if (onVisibilityChange) {
      onVisibilityChange(newVisible);
    }
  };

  // Handle notification click
  const handleNotificationClick = (notification: Notification) => {
    if (!notification.read) {
      markAsRead(notification.id);
    }
  };

  // Handle notification action
  const handleNotificationAction = async (notification: Notification, action: NotificationAction) => {
    try {
      switch (action.type) {
        case 'navigate':
          if (action.url) {
            window.open(action.url, '_blank');
          }
          break;
        case 'dismiss':
          await dismiss(notification.id);
          break;
        case 'delete':
          await deleteNotification(notification.id);
          break;
        case 'retry':
          // Handle retry logic
          break;
        case 'custom':
          if (action.handler) {
            await action.handler();
          }
          break;
      }
    } catch (error) {
      console.error('Action failed:', error);
    }
  };

  // Handle filter change
  const handleFilterChange = (newFilter: NotificationFilter) => {
    setFilter(newFilter);
  };

  // Handle preferences change
  const handlePreferencesChange = async (newPreferences: Partial<typeof preferences>) => {
    if (preferences) {
      await updatePreferences(newPreferences);
    }
  };

  // Toggle collapse
  const toggleCollapse = () => {
    setIsCollapsed(!isCollapsed);
  };

  // Get tab configuration
  const tabs = [
    { 
      id: 'notifications' as const, 
      label: 'Notifications', 
      icon: BellIcon, 
      badge: unreadCount > 0 ? unreadCount : undefined,
      show: true 
    },
    { 
      id: 'preferences' as const, 
      label: 'Preferences', 
      icon: CogIcon, 
      show: showPreferences 
    },
    { 
      id: 'stats' as const, 
      label: 'Statistics', 
      icon: ChartBarIcon, 
      show: showStats 
    },
  ].filter(tab => tab.show);

  const activeTabConfig = tabs.find(tab => tab.id === activeTab) || tabs[0];

  if (!visible) {
    return null;
  }

  return (
    <div className={`${styles.notificationCenter} ${className}`}>
      {/* Header */}
      <div className={styles.notificationCenterHeader}>
        <div className={styles.notificationCenterTitle}>
          <BellIcon className={styles.notificationCenterIcon} />
          <h2 className={styles.notificationCenterTitleText}>Notifications</h2>
          {hasUnreadNotifications && (
            <NotificationBadge 
              count={unreadCount} 
              size="small" 
              className={styles.notificationCenterBadge}
            />
          )}
        </div>

        <div className={styles.notificationCenterActions}>
          {/* Connection Status */}
          <div className={`${styles.notificationCenterStatus} ${
            isConnected ? styles.notificationCenterStatusConnected : styles.notificationCenterStatusDisconnected
          }`}>
            <div className={styles.notificationCenterStatusIndicator} />
            <span className={styles.notificationCenterStatusText}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          {/* Collapse Toggle */}
          <button
            className={styles.notificationCenterActionButton}
            onClick={toggleCollapse}
            aria-label={isCollapsed ? 'Expand' : 'Collapse'}
          >
            {isCollapsed ? (
              <ChevronUpIcon className={styles.notificationCenterActionIcon} />
            ) : (
              <ChevronDownIcon className={styles.notificationCenterActionIcon} />
            )}
          </button>

          {/* Close Button */}
          <button
            className={styles.notificationCenterActionButton}
            onClick={() => handleVisibilityChange(false)}
            aria-label="Close notification center"
          >
            <XMarkIcon className={styles.notificationCenterActionIcon} />
          </button>
        </div>
      </div>

      {/* Error State */}
      {hasError && (
        <div className={styles.notificationCenterError}>
          <div className={styles.notificationCenterErrorIcon}>
            <XMarkIcon />
          </div>
          <div className={styles.notificationCenterErrorContent}>
            <h4 className={styles.notificationCenterErrorTitle}>Error</h4>
            <p className={styles.notificationCenterErrorMessage}>{error}</p>
          </div>
          <button
            className={styles.notificationCenterErrorRetry}
            onClick={refresh}
            disabled={isLoading}
          >
            Retry
          </button>
        </div>
      )}

      {/* Content */}
      {!isCollapsed && (
        <div className={styles.notificationCenterContent} style={{ maxHeight }}>
          {/* Tabs */}
          {tabs.length > 1 && (
            <div className={styles.notificationCenterTabs}>
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    className={`${styles.notificationCenterTab} ${
                      activeTab === tab.id ? styles.notificationCenterTabActive : ''
                    }`}
                    onClick={() => setActiveTab(tab.id)}
                    aria-pressed={activeTab === tab.id}
                  >
                    <Icon className={styles.notificationCenterTabIcon} />
                    <span className={styles.notificationCenterTabLabel}>{tab.label}</span>
                    {tab.badge && (
                      <span className={styles.notificationCenterTabBadge}>
                        {tab.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}

          {/* Tab Content */}
          <div className={styles.notificationCenterTabContent}>
            {activeTab === 'notifications' && (
              <NotificationList
                notifications={notifications}
                filter={filter}
                loading={loading}
                onFilterChange={handleFilterChange}
                onNotificationClick={handleNotificationClick}
                onActionTrigger={handleNotificationAction}
                className={styles.notificationCenterNotificationList}
              />
            )}

            {activeTab === 'preferences' && preferences && (
              <NotificationPreferences
                preferences={preferences}
                onPreferencesChange={handlePreferencesChange}
                showAdvanced={true}
                className={styles.notificationCenterPreferences}
              />
            )}

            {activeTab === 'stats' && (
              <div className={styles.notificationCenterStats}>
                <h3 className={styles.notificationCenterStatsTitle}>Notification Statistics</h3>
                
                <div className={styles.notificationCenterStatsGrid}>
                  <div className={styles.notificationCenterStat}>
                    <div className={styles.notificationCenterStatValue}>{stats.total}</div>
                    <div className={styles.notificationCenterStatLabel}>Total</div>
                  </div>
                  
                  <div className={styles.notificationCenterStat}>
                    <div className={styles.notificationCenterStatValue}>{stats.unread}</div>
                    <div className={styles.notificationCenterStatLabel}>Unread</div>
                  </div>
                  
                  <div className={styles.notificationCenterStat}>
                    <div className={styles.notificationCenterStatValue}>{stats.read}</div>
                    <div className={styles.notificationCenterStatLabel}>Read</div>
                  </div>
                  
                  <div className={styles.notificationCenterStat}>
                    <div className={styles.notificationCenterStatValue}>{stats.dismissed}</div>
                    <div className={styles.notificationCenterStatLabel}>Dismissed</div>
                  </div>
                </div>

                <div className={styles.notificationCenterStatsActions}>
                  <button
                    className={styles.notificationCenterStatsAction}
                    onClick={markAllAsRead}
                    disabled={stats.unread === 0 || isLoading}
                  >
                    Mark All as Read
                  </button>
                  
                  <button
                    className={styles.notificationCenterStatsAction}
                    onClick={dismissAll}
                    disabled={!hasNotifications || isLoading}
                  >
                    Dismiss All
                  </button>
                  
                  <button
                    className={`${styles.notificationCenterStatsAction} ${styles.notificationCenterStatsActionDanger}`}
                    onClick={deleteAll}
                    disabled={!hasNotifications || isLoading}
                  >
                    Delete All
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className={styles.notificationCenterFooter}>
        <div className={styles.notificationCenterFooterInfo}>
          <span className={styles.notificationCenterFooterLabel}>
            {filteredNotifications.length} of {notifications.length} notifications
          </span>
        </div>
        
        <div className={styles.notificationCenterFooterActions}>
          <button
            className={styles.notificationCenterFooterAction}
            onClick={refresh}
            disabled={isLoading}
            aria-label="Refresh notifications"
          >
            <AdjustmentsHorizontalIcon className={styles.notificationCenterFooterActionIcon} />
            Refresh
          </button>
        </div>
      </div>
    </div>
  );
};

export default NotificationCenter;