import React, { useState, useMemo } from 'react';
import { 
  MagnifyingGlassIcon,
  FunnelIcon,
  AdjustmentsHorizontalIcon,
  XMarkIcon,
  CheckIcon,
  TrashIcon,
  ClockIcon,
  ChevronDownIcon,
  ChevronUpIcon
} from '@heroicons/react/24/outline';
import { 
  NotificationListProps, 
  NotificationFilter, 
  NotificationType,
  NotificationSeverity,
  NotificationPriority,
  NotificationCategory,
  EntityType
} from '@/types/notifications';
import { auditLogger } from '@/utils/auditLogger';
import NotificationItem from './NotificationItem';
import styles from './NotificationCenter.module.css';

/**
 * NotificationList component
 * Displays the list of notifications with filtering and search functionalities
 */
export const NotificationList: React.FC<NotificationListProps> = ({
  notifications,
  filter: initialFilter = {},
  loading = false,
  onFilterChange,
  onNotificationClick,
  onActionTrigger,
  className = '',
}) => {
  const [searchQuery, setSearchQuery] = useState(initialFilter.searchQuery || '');
  const [showFilters, setShowFilters] = useState(false);
  const [localFilter, setLocalFilter] = useState<NotificationFilter>(initialFilter);

  // Available filter options
  const notificationTypes: NotificationType[] = [
    'analysis_complete', 'analysis_failed', 'analysis_started', 'analysis_progress',
    'system_error', 'system_warning', 'system_info', 'user_action_required',
    'security_alert', 'maintenance_notice', 'feature_update', 'data_export_complete',
    'data_export_failed', 'quota_warning', 'quota_exceeded', 'backup_complete',
    'backup_failed', 'integration_success', 'integration_failed', 'custom'
  ];

  const severities: NotificationSeverity[] = ['low', 'medium', 'high', 'critical'];
  const priorities: NotificationPriority[] = ['low', 'normal', 'high', 'urgent'];
  const categories: NotificationCategory[] = [
    'analysis', 'system', 'security', 'maintenance', 'user', 'data',
    'integration', 'quota', 'backup', 'custom'
  ];
  const entityTypes: EntityType[] = [
    'analysis', 'user', 'system', 'data', 'integration', 'backup', 'quota', 'custom'
  ];

  // Apply filters
  const filteredNotifications = useMemo(() => {
    let filtered = [...notifications];

    // Apply search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(n => 
        n.title.toLowerCase().includes(query) ||
        n.message.toLowerCase().includes(query) ||
        (n.description && n.description.toLowerCase().includes(query))
      );
    }

    // Apply other filters
    if (localFilter.types && localFilter.types.length > 0) {
      filtered = filtered.filter(n => localFilter.types!.includes(n.type));
    }

    if (localFilter.severities && localFilter.severities.length > 0) {
      filtered = filtered.filter(n => localFilter.severities!.includes(n.severity));
    }

    if (localFilter.priorities && localFilter.priorities.length > 0) {
      filtered = filtered.filter(n => localFilter.priorities!.includes(n.priority));
    }

    if (localFilter.categories && localFilter.categories.length > 0) {
      filtered = filtered.filter(n => localFilter.categories!.includes(n.category));
    }

    if (localFilter.read !== undefined) {
      filtered = filtered.filter(n => n.read === localFilter.read);
    }

    if (localFilter.dismissed !== undefined) {
      filtered = filtered.filter(n => n.dismissed === localFilter.dismissed);
    }

    if (localFilter.entityTypes && localFilter.entityTypes.length > 0) {
      filtered = filtered.filter(n => n.entityType && localFilter.entityTypes!.includes(n.entityType));
    }

    if (localFilter.entityIds && localFilter.entityIds.length > 0) {
      filtered = filtered.filter(n => n.entityId && localFilter.entityIds!.includes(n.entityId));
    }

    if (localFilter.dateRange) {
      filtered = filtered.filter(n => {
        const notificationDate = n.timestamp.getTime();
        return notificationDate >= localFilter.dateRange!.start.getTime() && 
               notificationDate <= localFilter.dateRange!.end.getTime();
      });
    }

    // Sort
    if (localFilter.sortBy) {
      filtered.sort((a, b) => {
        let comparison = 0;
        
        switch (localFilter.sortBy) {
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
        
        return localFilter.sortDirection === 'desc' ? -comparison : comparison;
      });
    }

    return filtered;
  }, [notifications, searchQuery, localFilter]);

  // Update filter
  const updateFilter = (newFilter: Partial<NotificationFilter>) => {
    const updatedFilter = { ...localFilter, ...newFilter };
    setLocalFilter(updatedFilter);
    onFilterChange?.(updatedFilter);
  };

  // Clear all filters
  const clearFilters = () => {
    setSearchQuery('');
    setLocalFilter({});
    onFilterChange?.({});
  };

  // Handle search
  const handleSearch = (query: string) => {
    setSearchQuery(query);
    updateFilter({ searchQuery: query });
    auditLogger.logSearchPerformed(query, filteredNotifications.length);
  };

  // Handle notification click
  const handleNotificationClick = (notification: any) => {
    if (onNotificationClick) {
      auditLogger.logNotificationClicked(notification);
      onNotificationClick(notification);
    }
  };

  // Handle action trigger
  const handleActionTrigger = (notification: any, action: any) => {
    if (onActionTrigger) {
      auditLogger.logNotificationActionTriggered(notification, action);
      onActionTrigger(notification, action);
    }
  };

  // Get active filter count
  const getActiveFilterCount = () => {
    let count = 0;
    if (localFilter.types && localFilter.types.length > 0) count++;
    if (localFilter.severities && localFilter.severities.length > 0) count++;
    if (localFilter.priorities && localFilter.priorities.length > 0) count++;
    if (localFilter.categories && localFilter.categories.length > 0) count++;
    if (localFilter.read !== undefined) count++;
    if (localFilter.dismissed !== undefined) count++;
    if (localFilter.entityTypes && localFilter.entityTypes.length > 0) count++;
    if (localFilter.entityIds && localFilter.entityIds.length > 0) count++;
    if (localFilter.dateRange) count++;
    return count;
  };

  const activeFilterCount = getActiveFilterCount();

  return (
    <div className={`${styles.notificationList} ${className}`}>
      {/* Header */}
      <div className={styles.notificationListHeader}>
        <div className={styles.notificationListTitle}>
          <h3 className={styles.notificationListTitleText}>Notifications</h3>
          <span className={styles.notificationListCount}>
            {filteredNotifications.length} of {notifications.length}
          </span>
        </div>

        <div className={styles.notificationListActions}>
          <button
            className={`${styles.notificationListActionButton} ${
              showFilters ? styles.notificationListActionButtonActive : ''
            }`}
            onClick={() => setShowFilters(!showFilters)}
            aria-pressed={showFilters}
          >
            <FunnelIcon className={styles.notificationListActionIcon} />
            <span className={styles.notificationListActionText}>Filters</span>
            {activeFilterCount > 0 && (
              <span className={styles.notificationListActionBadge}>
                {activeFilterCount}
              </span>
            )}
          </button>

          {activeFilterCount > 0 && (
            <button
              className={styles.notificationListActionButton}
              onClick={clearFilters}
              aria-label="Clear all filters"
            >
              <XMarkIcon className={styles.notificationListActionIcon} />
              <span className={styles.notificationListActionText}>Clear</span>
            </button>
          )}
        </div>
      </div>

      {/* Search */}
      <div className={styles.notificationListSearch}>
        <MagnifyingGlassIcon className={styles.notificationListSearchIcon} />
        <input
          type="text"
          placeholder="Search notifications..."
          value={searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          className={styles.notificationListSearchInput}
        />
      </div>

      {/* Filters */}
      {showFilters && (
        <div className={styles.notificationListFilters}>
          {/* Types */}
          <div className={styles.notificationListFilterGroup}>
            <label className={styles.notificationListFilterLabel}>Types</label>
            <div className={styles.notificationListFilterOptions}>
              {notificationTypes.map(type => (
                <label key={type} className={styles.notificationListFilterOption}>
                  <input
                    type="checkbox"
                    checked={localFilter.types?.includes(type) || false}
                    onChange={(e) => {
                      const types = localFilter.types || [];
                      const newTypes = e.target.checked
                        ? [...types, type]
                        : types.filter(t => t !== type);
                      updateFilter({ types: newTypes.length > 0 ? newTypes : undefined });
                    }}
                    className={styles.notificationListFilterCheckbox}
                  />
                  <span className={styles.notificationListFilterOptionText}>
                    {type.replace(/_/g, ' ').toUpperCase()}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Severities */}
          <div className={styles.notificationListFilterGroup}>
            <label className={styles.notificationListFilterLabel}>Severities</label>
            <div className={styles.notificationListFilterOptions}>
              {severities.map(severity => (
                <label key={severity} className={styles.notificationListFilterOption}>
                  <input
                    type="checkbox"
                    checked={localFilter.severities?.includes(severity) || false}
                    onChange={(e) => {
                      const severities = localFilter.severities || [];
                      const newSeverities = e.target.checked
                        ? [...severities, severity]
                        : severities.filter(s => s !== severity);
                      updateFilter({ severities: newSeverities.length > 0 ? newSeverities : undefined });
                    }}
                    className={styles.notificationListFilterCheckbox}
                  />
                  <span className={styles.notificationListFilterOptionText}>
                    {severity.toUpperCase()}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Priorities */}
          <div className={styles.notificationListFilterGroup}>
            <label className={styles.notificationListFilterLabel}>Priorities</label>
            <div className={styles.notificationListFilterOptions}>
              {priorities.map(priority => (
                <label key={priority} className={styles.notificationListFilterOption}>
                  <input
                    type="checkbox"
                    checked={localFilter.priorities?.includes(priority) || false}
                    onChange={(e) => {
                      const priorities = localFilter.priorities || [];
                      const newPriorities = e.target.checked
                        ? [...priorities, priority]
                        : priorities.filter(p => p !== priority);
                      updateFilter({ priorities: newPriorities.length > 0 ? newPriorities : undefined });
                    }}
                    className={styles.notificationListFilterCheckbox}
                  />
                  <span className={styles.notificationListFilterOptionText}>
                    {priority.toUpperCase()}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Categories */}
          <div className={styles.notificationListFilterGroup}>
            <label className={styles.notificationListFilterLabel}>Categories</label>
            <div className={styles.notificationListFilterOptions}>
              {categories.map(category => (
                <label key={category} className={styles.notificationListFilterOption}>
                  <input
                    type="checkbox"
                    checked={localFilter.categories?.includes(category) || false}
                    onChange={(e) => {
                      const categories = localFilter.categories || [];
                      const newCategories = e.target.checked
                        ? [...categories, category]
                        : categories.filter(c => c !== category);
                      updateFilter({ categories: newCategories.length > 0 ? newCategories : undefined });
                    }}
                    className={styles.notificationListFilterCheckbox}
                  />
                  <span className={styles.notificationListFilterOptionText}>
                    {category.toUpperCase()}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Status */}
          <div className={styles.notificationListFilterGroup}>
            <label className={styles.notificationListFilterLabel}>Status</label>
            <div className={styles.notificationListFilterOptions}>
              <label className={styles.notificationListFilterOption}>
                <input
                  type="checkbox"
                  checked={localFilter.read === false}
                  onChange={(e) => {
                    updateFilter({ read: e.target.checked ? false : undefined });
                  }}
                  className={styles.notificationListFilterCheckbox}
                />
                <span className={styles.notificationListFilterOptionText}>UNREAD</span>
              </label>
              <label className={styles.notificationListFilterOption}>
                <input
                  type="checkbox"
                  checked={localFilter.read === true}
                  onChange={(e) => {
                    updateFilter({ read: e.target.checked ? true : undefined });
                  }}
                  className={styles.notificationListFilterCheckbox}
                />
                <span className={styles.notificationListFilterOptionText}>READ</span>
              </label>
              <label className={styles.notificationListFilterOption}>
                <input
                  type="checkbox"
                  checked={localFilter.dismissed === true}
                  onChange={(e) => {
                    updateFilter({ dismissed: e.target.checked ? true : undefined });
                  }}
                  className={styles.notificationListFilterCheckbox}
                />
                <span className={styles.notificationListFilterOptionText}>DISMISSED</span>
              </label>
            </div>
          </div>

          {/* Sort */}
          <div className={styles.notificationListFilterGroup}>
            <label className={styles.notificationListFilterLabel}>Sort By</label>
            <div className={styles.notificationListFilterSort}>
              <select
                value={localFilter.sortBy || 'timestamp'}
                onChange={(e) => updateFilter({ sortBy: e.target.value as any })}
                className={styles.notificationListFilterSelect}
              >
                <option value="timestamp">Timestamp</option>
                <option value="priority">Priority</option>
                <option value="severity">Severity</option>
                <option value="title">Title</option>
              </select>
              <button
                className={styles.notificationListFilterSortButton}
                onClick={() => updateFilter({ 
                  sortDirection: localFilter.sortDirection === 'asc' ? 'desc' : 'asc' 
                })}
                aria-label={`Sort ${localFilter.sortDirection === 'asc' ? 'descending' : 'ascending'}`}
              >
                {localFilter.sortDirection === 'asc' ? (
                  <ChevronUpIcon className={styles.notificationListFilterSortIcon} />
                ) : (
                  <ChevronDownIcon className={styles.notificationListFilterSortIcon} />
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className={styles.notificationListLoading}>
          <div className={styles.notificationListLoadingSpinner} />
          <p className={styles.notificationListLoadingText}>Loading notifications...</p>
        </div>
      )}

      {/* Notifications */}
      <div className={styles.notificationListContent}>
        {filteredNotifications.length === 0 ? (
          <div className={styles.notificationListEmpty}>
            <div className={styles.notificationListEmptyIcon}>
              <ClockIcon />
            </div>
            <h4 className={styles.notificationListEmptyTitle}>No notifications found</h4>
            <p className={styles.notificationListEmptyText}>
              {searchQuery || activeFilterCount > 0
                ? 'Try adjusting your search or filters'
                : 'You\'re all caught up! No new notifications.'
              }
            </p>
          </div>
        ) : (
          <div className={styles.notificationListItems}>
            {filteredNotifications.map((notification) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
                showActions={true}
                showTimestamp={true}
                showEntity={true}
                onClick={handleNotificationClick}
                onAction={handleActionTrigger}
                className={styles.notificationListItem}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default NotificationList;
