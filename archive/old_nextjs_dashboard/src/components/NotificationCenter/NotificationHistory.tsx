"use client"

import React, { useState, useCallback, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  History, 
  Search, 
  Filter, 
  Calendar, 
  Clock, 
  Archive,
  Trash2,
  Download,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Eye,
  EyeOff,
  AlertTriangle,
  CheckCircle,
  Info,
  Shield,
  Wrench,
  Sparkles
} from 'lucide-react';
import type { 
  NotificationHistoryItem, 
  NotificationHistoryProps,
  NotificationFilter,
  NotificationType,
  NotificationStatus,
  NotificationPriority
} from '@/types/notifications';

// Notification type configurations
const notificationTypeConfig = {
  analysis_completion: {
    label: 'Analysis Complete',
    icon: CheckCircle,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
  },
  system_alert: {
    label: 'System Alert',
    icon: AlertTriangle,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
  },
  compliance_update: {
    label: 'Compliance Update',
    icon: Shield,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
  },
  security_alert: {
    label: 'Security Alert',
    icon: Shield,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
  },
  maintenance_notice: {
    label: 'Maintenance Notice',
    icon: Wrench,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
  },
  feature_update: {
    label: 'Feature Update',
    icon: Sparkles,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
  },
};

// Priority configurations
const priorityConfig = {
  low: { label: 'Low', color: 'text-gray-600', bgColor: 'bg-gray-100' },
  medium: { label: 'Medium', color: 'text-blue-600', bgColor: 'bg-blue-100' },
  high: { label: 'High', color: 'text-orange-600', bgColor: 'bg-orange-100' },
  critical: { label: 'Critical', color: 'text-red-600', bgColor: 'bg-red-100' },
};

// Status configurations
const statusConfig = {
  unread: { label: 'Unread', color: 'text-blue-600', bgColor: 'bg-blue-100' },
  read: { label: 'Read', color: 'text-green-600', bgColor: 'bg-green-100' },
  dismissed: { label: 'Dismissed', color: 'text-gray-600', bgColor: 'bg-gray-100' },
  archived: { label: 'Archived', color: 'text-purple-600', bgColor: 'bg-purple-100' },
};

type SortField = 'timestamp' | 'priority' | 'type' | 'status';
type SortDirection = 'asc' | 'desc';

export default function NotificationHistory({ 
  notifications, 
  onFilter, 
  onSearch, 
  isLoading = false,
  className 
}: NotificationHistoryProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedTypes, setSelectedTypes] = useState<NotificationType[]>([]);
  const [selectedStatuses, setSelectedStatuses] = useState<NotificationStatus[]>([]);
  const [selectedPriorities, setSelectedPriorities] = useState<NotificationPriority[]>([]);
  const [dateRange, setDateRange] = useState<{ start: string; end: string }>({ start: '', end: '' });
  const [sortField, setSortField] = useState<SortField>('timestamp');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [showArchived, setShowArchived] = useState(false);
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  // Filter and sort notifications
  const filteredAndSortedNotifications = useMemo(() => {
    let filtered = notifications;

    // Filter by type
    if (selectedTypes.length > 0) {
      filtered = filtered.filter(n => selectedTypes.includes(n.type));
    }

    // Filter by status
    if (selectedStatuses.length > 0) {
      filtered = filtered.filter(n => selectedStatuses.includes(n.status));
    }

    // Filter by priority
    if (selectedPriorities.length > 0) {
      filtered = filtered.filter(n => selectedPriorities.includes(n.priority));
    }

    // Filter by date range
    if (dateRange.start && dateRange.end) {
      const startDate = new Date(dateRange.start);
      const endDate = new Date(dateRange.end);
      filtered = filtered.filter(n => {
        const notificationDate = new Date(n.timestamp);
        return notificationDate >= startDate && notificationDate <= endDate;
      });
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(n => 
        n.title.toLowerCase().includes(query) ||
        n.message.toLowerCase().includes(query) ||
        n.content?.toLowerCase().includes(query)
      );
    }

    // Filter archived items
    if (!showArchived) {
      filtered = filtered.filter(n => n.status !== 'archived');
    }

    // Sort notifications
    filtered.sort((a, b) => {
      let aValue: any, bValue: any;

      switch (sortField) {
        case 'timestamp':
          aValue = new Date(a.timestamp).getTime();
          bValue = new Date(b.timestamp).getTime();
          break;
        case 'priority':
          const priorityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
          aValue = priorityOrder[a.priority];
          bValue = priorityOrder[b.priority];
          break;
        case 'type':
          aValue = a.type;
          bValue = b.type;
          break;
        case 'status':
          const statusOrder = { unread: 4, read: 3, dismissed: 2, archived: 1 };
          aValue = statusOrder[a.status];
          bValue = statusOrder[b.status];
          break;
        default:
          aValue = a.timestamp;
          bValue = b.timestamp;
      }

      if (sortDirection === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    return filtered;
  }, [notifications, selectedTypes, selectedStatuses, selectedPriorities, dateRange, searchQuery, showArchived, sortField, sortDirection]);

  // Handle search
  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    onSearch(query);
  }, [onSearch]);

  // Handle filter changes
  const handleFilterChange = useCallback(() => {
    const filter: NotificationFilter = {
      types: selectedTypes.length > 0 ? selectedTypes : undefined,
      status: selectedStatuses.length > 0 ? selectedStatuses : undefined,
      priority: selectedPriorities.length > 0 ? selectedPriorities : undefined,
      dateRange: dateRange.start && dateRange.end ? dateRange : undefined,
      searchQuery: searchQuery.trim() || undefined,
    };
    onFilter(filter);
  }, [selectedTypes, selectedStatuses, selectedPriorities, dateRange, searchQuery, onFilter]);

  // Clear all filters
  const clearFilters = useCallback(() => {
    setSelectedTypes([]);
    setSelectedStatuses([]);
    setSelectedPriorities([]);
    setDateRange({ start: '', end: '' });
    setSearchQuery('');
    setShowArchived(false);
  }, []);

  // Toggle item expansion
  const toggleExpansion = useCallback((itemId: string) => {
    setExpandedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });
  }, []);

  // Format timestamp
  const formatTimestamp = useCallback((timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  }, []);

  // Get notification statistics
  const stats = useMemo(() => {
    const total = notifications.length;
    const unread = notifications.filter(n => n.status === 'unread').length;
    const archived = notifications.filter(n => n.status === 'archived').length;
    const byType = Object.keys(notificationTypeConfig).reduce((acc, type) => {
      acc[type as NotificationType] = notifications.filter(n => n.type === type).length;
      return acc;
    }, {} as Record<NotificationType, number>);

    return { total, unread, archived, byType };
  }, [notifications]);

  return (
    <div className={`space-y-4 ${className || ''}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Notification History</h3>
          <p className="text-sm text-gray-600">
            Search and filter through your notification history
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowArchived(!showArchived)}
            className="flex items-center gap-2"
          >
            <Archive className="h-4 w-4" />
            {showArchived ? 'Hide' : 'Show'} Archived
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {/* Export functionality */}}
            className="flex items-center gap-2"
          >
            <Download className="h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-3">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-blue-600" />
            <div>
              <p className="text-xs text-gray-600">Total</p>
              <p className="text-lg font-semibold">{stats.total}</p>
            </div>
          </div>
        </Card>
        <Card className="p-3">
          <div className="flex items-center gap-2">
            <Eye className="h-4 w-4 text-green-600" />
            <div>
              <p className="text-xs text-gray-600">Unread</p>
              <p className="text-lg font-semibold">{stats.unread}</p>
            </div>
          </div>
        </Card>
        <Card className="p-3">
          <div className="flex items-center gap-2">
            <Archive className="h-4 w-4 text-purple-600" />
            <div>
              <p className="text-xs text-gray-600">Archived</p>
              <p className="text-lg font-semibold">{stats.archived}</p>
            </div>
          </div>
        </Card>
        <Card className="p-3">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-gray-600" />
            <div>
              <p className="text-xs text-gray-600">Filtered</p>
              <p className="text-lg font-semibold">{filteredAndSortedNotifications.length}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="space-y-4">
            {/* Search */}
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search notification history..."
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowFilters(!showFilters)}
                className="flex items-center gap-2"
              >
                <Filter className="h-4 w-4" />
                Filters
                {showFilters ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={clearFilters}
                className="flex items-center gap-2"
              >
                Clear
              </Button>
            </div>

            {/* Advanced Filters */}
            {showFilters && (
              <div className="p-4 bg-gray-50 rounded-lg space-y-4">
                {/* Type Filters */}
                <div>
                  <label className="text-sm font-medium mb-2 block">Notification Types</label>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(notificationTypeConfig).map(([type, config]) => {
                      const Icon = config.icon;
                      const isSelected = selectedTypes.includes(type as NotificationType);
                      return (
                        <Button
                          key={type}
                          variant={isSelected ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => {
                            if (isSelected) {
                              setSelectedTypes(prev => prev.filter(t => t !== type));
                            } else {
                              setSelectedTypes(prev => [...prev, type as NotificationType]);
                            }
                          }}
                          className="flex items-center gap-2"
                        >
                          <Icon className="h-4 w-4" />
                          {config.label}
                          <Badge variant="secondary" className="text-xs">
                            {stats.byType[type as NotificationType]}
                          </Badge>
                        </Button>
                      );
                    })}
                  </div>
                </div>

                {/* Status Filters */}
                <div>
                  <label className="text-sm font-medium mb-2 block">Status</label>
                  <div className="flex gap-2">
                    {Object.entries(statusConfig).map(([status, config]) => {
                      const isSelected = selectedStatuses.includes(status as NotificationStatus);
                      return (
                        <Button
                          key={status}
                          variant={isSelected ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => {
                            if (isSelected) {
                              setSelectedStatuses(prev => prev.filter(s => s !== status));
                            } else {
                              setSelectedStatuses(prev => [...prev, status as NotificationStatus]);
                            }
                          }}
                        >
                          {config.label}
                        </Button>
                      );
                    })}
                  </div>
                </div>

                {/* Priority Filters */}
                <div>
                  <label className="text-sm font-medium mb-2 block">Priority</label>
                  <div className="flex gap-2">
                    {Object.entries(priorityConfig).map(([priority, config]) => {
                      const isSelected = selectedPriorities.includes(priority as NotificationPriority);
                      return (
                        <Button
                          key={priority}
                          variant={isSelected ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => {
                            if (isSelected) {
                              setSelectedPriorities(prev => prev.filter(p => p !== priority));
                            } else {
                              setSelectedPriorities(prev => [...prev, priority as NotificationPriority]);
                            }
                          }}
                        >
                          {config.label}
                        </Button>
                      );
                    })}
                  </div>
                </div>

                {/* Date Range */}
                <div>
                  <label className="text-sm font-medium mb-2 block">Date Range</label>
                  <div className="flex gap-2">
                    <input
                      type="date"
                      value={dateRange.start}
                      onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
                      className="px-3 py-2 border rounded-md text-sm"
                    />
                    <span className="flex items-center text-gray-500">to</span>
                    <input
                      type="date"
                      value={dateRange.end}
                      onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
                      className="px-3 py-2 border rounded-md text-sm"
                    />
                  </div>
                </div>

                {/* Sort Options */}
                <div>
                  <label className="text-sm font-medium mb-2 block">Sort By</label>
                  <div className="flex gap-2">
                    <select
                      value={sortField}
                      onChange={(e) => setSortField(e.target.value as SortField)}
                      className="px-3 py-2 border rounded-md text-sm"
                    >
                      <option value="timestamp">Date</option>
                      <option value="priority">Priority</option>
                      <option value="type">Type</option>
                      <option value="status">Status</option>
                    </select>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')}
                      className="flex items-center gap-1"
                    >
                      {sortDirection === 'asc' ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      {sortDirection === 'asc' ? 'Ascending' : 'Descending'}
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Notifications List */}
      <div className="space-y-2">
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <RefreshCw className="h-6 w-6 animate-spin text-gray-400" />
            <span className="ml-2 text-gray-600">Loading history...</span>
          </div>
        ) : filteredAndSortedNotifications.length === 0 ? (
          <Card className="p-8 text-center">
            <History className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <h4 className="text-lg font-medium text-gray-600 mb-2">No notifications found</h4>
            <p className="text-gray-500">Try adjusting your search criteria or filters</p>
          </Card>
        ) : (
          filteredAndSortedNotifications.map((notification) => {
            const typeConfig = notificationTypeConfig[notification.type];
            const priorityConfigItem = priorityConfig[notification.priority];
            const statusConfigItem = statusConfig[notification.status];
            const TypeIcon = typeConfig.icon;
            const isExpanded = expandedItems.has(notification.id);

            return (
              <Card key={notification.id} className="transition-all duration-200 hover:shadow-md">
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    {/* Type Icon */}
                    <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${typeConfig.bgColor}`}>
                      <TypeIcon className={`h-4 w-4 ${typeConfig.color}`} />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <h5 className="font-medium text-sm text-gray-900 truncate">
                            {notification.title}
                          </h5>
                          <Badge variant="outline" className={`text-xs ${priorityConfigItem.color} ${priorityConfigItem.bgColor}`}>
                            {priorityConfigItem.label}
                          </Badge>
                          <Badge variant="outline" className={`text-xs ${statusConfigItem.color} ${statusConfigItem.bgColor}`}>
                            {statusConfigItem.label}
                          </Badge>
                        </div>
                        <span className="text-xs text-gray-500">
                          {formatTimestamp(notification.timestamp)}
                        </span>
                      </div>

                      <p className="text-sm text-gray-700 mb-2 line-clamp-2">
                        {notification.message}
                      </p>

                      {/* Expanded Content */}
                      {isExpanded && (
                        <div className="mt-3 p-3 bg-gray-50 rounded-md">
                          {notification.content && (
                            <p className="text-sm text-gray-600 mb-3 whitespace-pre-wrap">
                              {notification.content}
                            </p>
                          )}
                          {notification.metadata && Object.keys(notification.metadata).length > 0 && (
                            <div className="mb-3">
                              <div className="flex flex-wrap gap-2">
                                {Object.entries(notification.metadata).map(([key, value]) => (
                                  <Badge key={key} variant="outline" className="text-xs">
                                    {key}: {String(value)}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          )}
                          <div className="text-xs text-gray-500">
                            <p>Created: {formatTimestamp(notification.createdAt)}</p>
                            {notification.readAt && <p>Read: {formatTimestamp(notification.readAt)}</p>}
                            {notification.dismissedAt && <p>Dismissed: {formatTimestamp(notification.dismissedAt)}</p>}
                            {notification.archivedAt && <p>Archived: {formatTimestamp(notification.archivedAt)}</p>}
                          </div>
                        </div>
                      )}

                      {/* Actions */}
                      <div className="flex items-center justify-between mt-2">
                        <div className="flex items-center gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => toggleExpansion(notification.id)}
                            className="h-6 px-2 text-xs"
                          >
                            {isExpanded ? <EyeOff className="h-3 w-3 mr-1" /> : <Eye className="h-3 w-3 mr-1" />}
                            {isExpanded ? 'Hide' : 'Show'} Details
                          </Button>
                        </div>
                        <div className="flex items-center gap-1">
                          {notification.status !== 'archived' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 px-2 text-xs text-purple-600"
                            >
                              <Archive className="h-3 w-3 mr-1" />
                              Archive
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 px-2 text-xs text-red-600"
                          >
                            <Trash2 className="h-3 w-3 mr-1" />
                            Delete
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
