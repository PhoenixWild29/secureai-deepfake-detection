import React, { useState } from 'react';
import { 
  CheckIcon,
  XMarkIcon,
  TrashIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ArrowTopRightOnSquareIcon
} from '@heroicons/react/24/outline';
import { NotificationItemProps, NotificationAction } from '@/types/notifications';
import { auditLogger } from '@/utils/auditLogger';
import styles from './NotificationCenter.module.css';

/**
 * NotificationItem component
 * Renders individual notification items with read/unread status, timestamp, and actions
 */
export const NotificationItem: React.FC<NotificationItemProps> = ({
  notification,
  showActions = true,
  showTimestamp = true,
  showEntity = true,
  onClick,
  onAction,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isActionLoading, setIsActionLoading] = useState<string | null>(null);

  const getSeverityIcon = () => {
    switch (notification.severity) {
      case 'critical':
        return <XCircleIcon className={styles.notificationItemSeverityIconCritical} />;
      case 'high':
        return <ExclamationTriangleIcon className={styles.notificationItemSeverityIconHigh} />;
      case 'medium':
        return <InformationCircleIcon className={styles.notificationItemSeverityIconMedium} />;
      case 'low':
        return <CheckCircleIcon className={styles.notificationItemSeverityIconLow} />;
      default:
        return <InformationCircleIcon className={styles.notificationItemSeverityIconMedium} />;
    }
  };

  const getSeverityColor = () => {
    switch (notification.severity) {
      case 'critical':
        return styles.notificationItemCritical;
      case 'high':
        return styles.notificationItemHigh;
      case 'medium':
        return styles.notificationItemMedium;
      case 'low':
        return styles.notificationItemLow;
      default:
        return styles.notificationItemMedium;
    }
  };

  const getPriorityColor = () => {
    switch (notification.priority) {
      case 'urgent':
        return styles.notificationItemPriorityUrgent;
      case 'high':
        return styles.notificationItemPriorityHigh;
      case 'normal':
        return styles.notificationItemPriorityNormal;
      case 'low':
        return styles.notificationItemPriorityLow;
      default:
        return styles.notificationItemPriorityNormal;
    }
  };

  const formatTimestamp = (timestamp: Date) => {
    const now = new Date();
    const diff = now.getTime() - timestamp.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) {
      return `${days} day${days > 1 ? 's' : ''} ago`;
    } else if (hours > 0) {
      return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else if (minutes > 0) {
      return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    } else {
      return 'Just now';
    }
  };

  const handleClick = () => {
    if (onClick) {
      auditLogger.logNotificationClicked(notification);
      onClick(notification);
    }
  };

  const handleAction = async (action: NotificationAction) => {
    if (onAction) {
      setIsActionLoading(action.id);
      try {
        auditLogger.logNotificationActionTriggered(notification, action);
        await onAction(notification, action);
      } catch (error) {
        console.error('Action failed:', error);
      } finally {
        setIsActionLoading(null);
      }
    }
  };

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
  };

  const hasDetails = notification.description || notification.actions || notification.data;

  return (
    <div 
      className={`${styles.notificationItem} ${getSeverityColor()} ${getPriorityColor()} ${
        notification.read ? styles.notificationItemRead : styles.notificationItemUnread
      } ${className}`}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      aria-label={`Notification: ${notification.title}`}
    >
      {/* Main Content */}
      <div className={styles.notificationItemMain}>
        {/* Severity Icon */}
        <div className={styles.notificationItemIcon}>
          {getSeverityIcon()}
        </div>

        {/* Content */}
        <div className={styles.notificationItemContent}>
          {/* Header */}
          <div className={styles.notificationItemHeader}>
            <h4 className={styles.notificationItemTitle}>
              {notification.title}
            </h4>
            
            <div className={styles.notificationItemMeta}>
              {showTimestamp && (
                <div className={styles.notificationItemTimestamp}>
                  <ClockIcon className={styles.notificationItemTimestampIcon} />
                  <span className={styles.notificationItemTimestampText}>
                    {formatTimestamp(notification.timestamp)}
                  </span>
                </div>
              )}
              
              <div className={styles.notificationItemBadges}>
                <span className={`${styles.notificationItemBadge} ${styles.notificationItemBadgeSeverity}`}>
                  {notification.severity.toUpperCase()}
                </span>
                <span className={`${styles.notificationItemBadge} ${styles.notificationItemBadgePriority}`}>
                  {notification.priority.toUpperCase()}
                </span>
                <span className={`${styles.notificationItemBadge} ${styles.notificationItemBadgeCategory}`}>
                  {notification.category.toUpperCase()}
                </span>
              </div>
            </div>
          </div>

          {/* Message */}
          <p className={styles.notificationItemMessage}>
            {notification.message}
          </p>

          {/* Entity Information */}
          {showEntity && (notification.entityType || notification.entityId) && (
            <div className={styles.notificationItemEntity}>
              <span className={styles.notificationItemEntityLabel}>Related:</span>
              {notification.entityType && (
                <span className={styles.notificationItemEntityType}>
                  {notification.entityType.replace(/_/g, ' ').toUpperCase()}
                </span>
              )}
              {notification.entityId && (
                <span className={styles.notificationItemEntityId}>
                  {notification.entityId}
                </span>
              )}
            </div>
          )}

          {/* Expand Button */}
          {hasDetails && (
            <button
              className={styles.notificationItemExpandButton}
              onClick={(e) => {
                e.stopPropagation();
                toggleExpanded();
              }}
              aria-expanded={isExpanded}
              aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
            >
              {isExpanded ? (
                <ChevronDownIcon className={styles.notificationItemExpandIcon} />
              ) : (
                <ChevronRightIcon className={styles.notificationItemExpandIcon} />
              )}
              <span className={styles.notificationItemExpandText}>
                {isExpanded ? 'Less' : 'More'}
              </span>
            </button>
          )}
        </div>

        {/* Status Indicators */}
        <div className={styles.notificationItemStatus}>
          {!notification.read && (
            <div className={styles.notificationItemUnreadIndicator} />
          )}
          {notification.dismissed && (
            <XMarkIcon className={styles.notificationItemDismissedIcon} />
          )}
        </div>
      </div>

      {/* Expanded Details */}
      {isExpanded && hasDetails && (
        <div className={styles.notificationItemDetails}>
          {/* Description */}
          {notification.description && (
            <div className={styles.notificationItemDescription}>
              <h5 className={styles.notificationItemDescriptionTitle}>Description</h5>
              <p className={styles.notificationItemDescriptionText}>
                {notification.description}
              </p>
            </div>
          )}

          {/* Additional Data */}
          {notification.data && Object.keys(notification.data).length > 0 && (
            <div className={styles.notificationItemData}>
              <h5 className={styles.notificationItemDataTitle}>Additional Data</h5>
              <div className={styles.notificationItemDataContent}>
                <pre className={styles.notificationItemDataPre}>
                  {JSON.stringify(notification.data, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Actions */}
          {notification.actions && notification.actions.length > 0 && (
            <div className={styles.notificationItemActions}>
              <h5 className={styles.notificationItemActionsTitle}>Actions</h5>
              <div className={styles.notificationItemActionsList}>
                {notification.actions.map((action) => (
                  <button
                    key={action.id}
                    className={`${styles.notificationItemActionButton} ${
                      action.style === 'primary' ? styles.notificationItemActionButtonPrimary :
                      action.style === 'danger' ? styles.notificationItemActionButtonDanger :
                      action.style === 'success' ? styles.notificationItemActionButtonSuccess :
                      action.style === 'warning' ? styles.notificationItemActionButtonWarning :
                      styles.notificationItemActionButtonSecondary
                    }`}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAction(action);
                    }}
                    disabled={isActionLoading === action.id}
                    aria-label={action.label}
                  >
                    {isActionLoading === action.id ? (
                      <div className={styles.notificationItemActionSpinner} />
                    ) : (
                      <>
                        {action.icon && (
                          <span className={styles.notificationItemActionIcon}>
                            {action.icon}
                          </span>
                        )}
                        <span className={styles.notificationItemActionLabel}>
                          {action.label}
                        </span>
                        {action.url && (
                          <ArrowTopRightOnSquareIcon className={styles.notificationItemActionExternalIcon} />
                        )}
                      </>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Quick Actions */}
      {showActions && (
        <div className={styles.notificationItemQuickActions}>
          {!notification.read && (
            <button
              className={styles.notificationItemQuickAction}
              onClick={(e) => {
                e.stopPropagation();
                handleAction({
                  id: 'mark-read',
                  label: 'Mark as Read',
                  type: 'custom',
                  handler: () => {
                    // This will be handled by the parent component
                  },
                });
              }}
              aria-label="Mark as read"
            >
              <CheckIcon className={styles.notificationItemQuickActionIcon} />
            </button>
          )}
          
          {!notification.dismissed && (
            <button
              className={styles.notificationItemQuickAction}
              onClick={(e) => {
                e.stopPropagation();
                handleAction({
                  id: 'dismiss',
                  label: 'Dismiss',
                  type: 'dismiss',
                  handler: () => {
                    // This will be handled by the parent component
                  },
                });
              }}
              aria-label="Dismiss notification"
            >
              <XMarkIcon className={styles.notificationItemQuickActionIcon} />
            </button>
          )}
          
          <button
            className={styles.notificationItemQuickAction}
            onClick={(e) => {
              e.stopPropagation();
              handleAction({
                id: 'delete',
                label: 'Delete',
                type: 'delete',
                handler: () => {
                  // This will be handled by the parent component
                },
              });
            }}
            aria-label="Delete notification"
          >
            <TrashIcon className={styles.notificationItemQuickActionIcon} />
          </button>
        </div>
      )}
    </div>
  );
};

export default NotificationItem;