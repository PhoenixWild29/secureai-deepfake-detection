/**
 * useRealTimeDashboard Hook
 * Manages live analysis progress, system status changes, and notification delivery
 * using WebSocket integration with automatic reconnection and event filtering
 */

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { 
  RealTimeEvent, 
  RealTimeEventType, 
  EventPriority,
  EventFilter,
  EventStats,
  RealTimeDashboardState,
  RealTimeDashboardActions,
  UseRealTimeDashboardReturn,
  DEFAULT_EVENT_FILTER,
  DASHBOARD_QUERY_KEYS
} from '@/types/dashboard';
import { getWebSocketService, WebSocketService, WebSocketState } from '@/services/websocketService';
import { getDashboardApiService } from '@/services/dashboardApi';
import { invalidateDashboardQueries } from '@/queryClient';

// Hook configuration
interface UseRealTimeDashboardConfig {
  userId: string;
  enableWebSocket?: boolean;
  enableEventFiltering?: boolean;
  enableDataAggregation?: boolean;
  maxEvents?: number;
  eventRetentionTime?: number;
  enablePerformanceMonitoring?: boolean;
}

// Default configuration
const DEFAULT_CONFIG: Partial<UseRealTimeDashboardConfig> = {
  enableWebSocket: true,
  enableEventFiltering: true,
  enableDataAggregation: true,
  maxEvents: 1000,
  eventRetentionTime: 24 * 60 * 60 * 1000, // 24 hours
  enablePerformanceMonitoring: true,
};

/**
 * Main real-time dashboard hook
 */
export const useRealTimeDashboard = (config: UseRealTimeDashboardConfig): UseRealTimeDashboardReturn => {
  const {
    userId,
    enableWebSocket = true,
    enableEventFiltering = true,
    enableDataAggregation = true,
    maxEvents = 1000,
    eventRetentionTime = 24 * 60 * 60 * 1000,
    enablePerformanceMonitoring = true,
  } = { ...DEFAULT_CONFIG, ...config };

  // Services
  const webSocketService = getWebSocketService();
  const apiService = getDashboardApiService();
  const queryClient = useQueryClient();

  // State
  const [events, setEvents] = useState<RealTimeEvent[]>([]);
  const [filters, setFilters] = useState<EventFilter>(DEFAULT_EVENT_FILTER);
  const [connected, setConnected] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [lastEventTime, setLastEventTime] = useState<Date | null>(null);
  const [stats, setStats] = useState<EventStats>({
    total: 0,
    byType: {} as Record<RealTimeEventType, number>,
    byPriority: {} as Record<EventPriority, number>,
    bySource: {},
    eventsPerMinute: 0,
    lastEventTime: null,
  });

  // Refs
  const eventBufferRef = useRef<RealTimeEvent[]>([]);
  const statsUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const performanceStartTimeRef = useRef<number>(0);
  const eventCountRef = useRef<number>(0);

  // Set auth token
  useEffect(() => {
    const token = localStorage.getItem('auth_token'); // In real app, get from auth context
    if (token) {
      webSocketService.setAuthToken(token);
      apiService.setAuthToken(token);
    }
  }, [webSocketService, apiService]);

  // WebSocket connection management
  useEffect(() => {
    if (!enableWebSocket) {
      return;
    }

    const handleConnectionStateChange = (state: WebSocketState) => {
      setConnected(state === WebSocketState.CONNECTED);
      setReconnectAttempts(webSocketService.getStats().reconnectAttempts);
    };

    const handleError = (error: Error) => {
      console.error('WebSocket error:', error);
    };

    const handleEvent = (event: RealTimeEvent) => {
      addEvent(event);
    };

    // Add event listeners
    webSocketService.addConnectionStateListener(handleConnectionStateChange);
    webSocketService.addErrorListener(handleError);
    webSocketService.addEventListener('analysis_progress', handleEvent);
    webSocketService.addEventListener('analysis_complete', handleEvent);
    webSocketService.addEventListener('analysis_failed', handleEvent);
    webSocketService.addEventListener('system_status_change', handleEvent);
    webSocketService.addEventListener('notification_received', handleEvent);
    webSocketService.addEventListener('user_activity', handleEvent);
    webSocketService.addEventListener('resource_usage_update', handleEvent);
    webSocketService.addEventListener('security_alert', handleEvent);
    webSocketService.addEventListener('data_export_progress', handleEvent);
    webSocketService.addEventListener('api_status_change', handleEvent);
    webSocketService.addEventListener('widget_update', handleEvent);
    webSocketService.addEventListener('preference_change', handleEvent);
    webSocketService.addEventListener('error_occurred', handleEvent);

    // Connect to WebSocket
    webSocketService.connect().catch((error) => {
      console.error('Failed to connect to WebSocket:', error);
    });

    return () => {
      // Remove event listeners
      webSocketService.removeConnectionStateListener(handleConnectionStateChange);
      webSocketService.removeErrorListener(handleError);
      webSocketService.removeEventListener('analysis_progress', handleEvent);
      webSocketService.removeEventListener('analysis_complete', handleEvent);
      webSocketService.removeEventListener('analysis_failed', handleEvent);
      webSocketService.removeEventListener('system_status_change', handleEvent);
      webSocketService.removeEventListener('notification_received', handleEvent);
      webSocketService.removeEventListener('user_activity', handleEvent);
      webSocketService.removeEventListener('resource_usage_update', handleEvent);
      webSocketService.removeEventListener('security_alert', handleEvent);
      webSocketService.removeEventListener('data_export_progress', handleEvent);
      webSocketService.removeEventListener('api_status_change', handleEvent);
      webSocketService.removeEventListener('widget_update', handleEvent);
      webSocketService.removeEventListener('preference_change', handleEvent);
      webSocketService.removeEventListener('error_occurred', handleEvent);
    };
  }, [enableWebSocket, webSocketService]);

  // Event filtering and aggregation
  const filteredEvents = useMemo(() => {
    if (!enableEventFiltering) {
      return events;
    }

    return events.filter(event => {
      // Filter by type
      if (filters.types && filters.types.length > 0 && !filters.types.includes(event.type)) {
        return false;
      }

      // Filter by priority
      if (filters.priorities && filters.priorities.length > 0 && !filters.priorities.includes(event.priority)) {
        return false;
      }

      // Filter by source
      if (filters.sources && filters.sources.length > 0 && !filters.sources.includes(event.source)) {
        return false;
      }

      // Filter by date range
      if (filters.dateRange) {
        const eventTime = event.timestamp.getTime();
        const startTime = filters.dateRange.start.getTime();
        const endTime = filters.dateRange.end.getTime();
        if (eventTime < startTime || eventTime > endTime) {
          return false;
        }
      }

      // Filter by search query
      if (filters.searchQuery) {
        const searchLower = filters.searchQuery.toLowerCase();
        const eventDataStr = JSON.stringify(event.data).toLowerCase();
        const eventSourceStr = event.source.toLowerCase();
        if (!eventDataStr.includes(searchLower) && !eventSourceStr.includes(searchLower)) {
          return false;
        }
      }

      return true;
    });
  }, [events, filters, enableEventFiltering]);

  // Recent events (last 100)
  const recentEvents = useMemo(() => {
    return filteredEvents.slice(-100);
  }, [filteredEvents]);

  // Event statistics calculation
  const calculateStats = useCallback((eventList: RealTimeEvent[]): EventStats => {
    const stats: EventStats = {
      total: eventList.length,
      byType: {} as Record<RealTimeEventType, number>,
      byPriority: {} as Record<EventPriority, number>,
      bySource: {},
      eventsPerMinute: 0,
      lastEventTime: eventList.length > 0 ? eventList[eventList.length - 1].timestamp : null,
    };

    // Count by type
    eventList.forEach(event => {
      stats.byType[event.type] = (stats.byType[event.type] || 0) + 1;
    });

    // Count by priority
    eventList.forEach(event => {
      stats.byPriority[event.priority] = (stats.byPriority[event.priority] || 0) + 1;
    });

    // Count by source
    eventList.forEach(event => {
      stats.bySource[event.source] = (stats.bySource[event.source] || 0) + 1;
    });

    // Calculate events per minute (last 5 minutes)
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
    const recentEvents = eventList.filter(event => event.timestamp >= fiveMinutesAgo);
    stats.eventsPerMinute = recentEvents.length / 5;

    return stats;
  }, []);

  // Add event to buffer
  const addEvent = useCallback((event: RealTimeEvent) => {
    if (enablePerformanceMonitoring) {
      performanceStartTimeRef.current = performance.now();
      eventCountRef.current++;
    }

    setEvents(prev => {
      const newEvents = [...prev, event];
      
      // Limit events to maxEvents
      if (newEvents.length > maxEvents) {
        newEvents.splice(0, newEvents.length - maxEvents);
      }

      // Remove old events
      const cutoffTime = new Date(Date.now() - eventRetentionTime);
      const filteredEvents = newEvents.filter(event => event.timestamp >= cutoffTime);

      return filteredEvents;
    });

    setLastEventTime(event.timestamp);

    // Update statistics with debouncing
    if (statsUpdateTimeoutRef.current) {
      clearTimeout(statsUpdateTimeoutRef.current);
    }

    statsUpdateTimeoutRef.current = setTimeout(() => {
      setEvents(currentEvents => {
        const newStats = calculateStats(currentEvents);
        setStats(newStats);
        return currentEvents;
      });
    }, 1000);

    // Invalidate relevant queries based on event type
    switch (event.type) {
      case 'widget_update':
        invalidateDashboardQueries.widgets();
        break;
      case 'preference_change':
        invalidateDashboardQueries.preferences();
        break;
      case 'analysis_progress':
      case 'analysis_complete':
      case 'analysis_failed':
        invalidateDashboardQueries.events();
        break;
      case 'system_status_change':
        invalidateDashboardQueries.all();
        break;
    }

    if (enablePerformanceMonitoring) {
      const endTime = performance.now();
      const duration = endTime - performanceStartTimeRef.current;
      
      if (typeof window !== 'undefined' && window.gtag) {
        window.gtag('event', 'realtime_event_processed', {
          event_type: event.type,
          processing_time_ms: Math.round(duration),
          event_count: eventCountRef.current,
        });
      }
    }
  }, [maxEvents, eventRetentionTime, calculateStats, enablePerformanceMonitoring]);

  // Actions
  const connect = useCallback(async () => {
    try {
      await webSocketService.connect();
    } catch (error) {
      console.error('Failed to connect:', error);
      throw error;
    }
  }, [webSocketService]);

  const disconnect = useCallback(() => {
    webSocketService.disconnect();
  }, [webSocketService]);

  const updateFilters = useCallback((newFilters: Partial<EventFilter>) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
  }, []);

  const clearEvents = useCallback(() => {
    setEvents([]);
    setStats({
      total: 0,
      byType: {} as Record<RealTimeEventType, number>,
      byPriority: {} as Record<EventPriority, number>,
      bySource: {},
      eventsPerMinute: 0,
      lastEventTime: null,
    });
    eventBufferRef.current = [];
  }, []);

  const subscribe = useCallback((eventType: RealTimeEventType) => {
    webSocketService.subscribe(eventType);
  }, [webSocketService]);

  const unsubscribe = useCallback((eventType: RealTimeEventType) => {
    webSocketService.unsubscribe(eventType);
  }, [webSocketService]);

  const sendMessage = useCallback((message: Omit<any, 'id' | 'timestamp'>) => {
    webSocketService.sendMessage(message);
  }, [webSocketService]);

  // Historical events query
  const {
    data: historicalEvents = [],
    isLoading: historicalLoading,
    error: historicalError,
  } = useQuery({
    queryKey: DASHBOARD_QUERY_KEYS.realTimeEvents(),
    queryFn: () => apiService.getRealTimeEvents(filters),
    enabled: enableWebSocket,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // 1 minute
    onError: (error) => {
      console.error('Failed to fetch historical events:', error);
    },
  });

  // Event statistics query
  const {
    data: serverStats = null,
    isLoading: statsLoading,
    error: statsError,
  } = useQuery({
    queryKey: ['dashboard', 'events', 'statistics'],
    queryFn: () => apiService.getEventStatistics(),
    enabled: enableWebSocket,
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchInterval: 5 * 60 * 1000, // 5 minutes
    onError: (error) => {
      console.error('Failed to fetch event statistics:', error);
    },
  });

  // Actions object
  const actions: RealTimeDashboardActions = {
    connect,
    disconnect,
    updateFilters,
    clearEvents,
    subscribe,
    unsubscribe,
    sendMessage,
  };

  // Real-time state object
  const state: RealTimeDashboardState = {
    events: filteredEvents,
    filters,
    connected,
    reconnectAttempts,
    lastEventTime,
    stats,
  };

  // Connection status
  const connection = {
    connected,
    connecting: webSocketService.getState() === WebSocketState.CONNECTING,
    reconnectAttempts,
    lastConnected: connected ? new Date() : null,
    lastDisconnected: !connected ? new Date() : null,
  };

  // Event handling
  const eventHandling = {
    recent: recentEvents,
    filtered: filteredEvents,
    stats: serverStats || stats,
  };

  // Cleanup
  useEffect(() => {
    return () => {
      if (statsUpdateTimeoutRef.current) {
        clearTimeout(statsUpdateTimeoutRef.current);
      }
    };
  }, []);

  return {
    state,
    actions,
    connection,
    events: eventHandling,
  };
};

export default useRealTimeDashboard;
