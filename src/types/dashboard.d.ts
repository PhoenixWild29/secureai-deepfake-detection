/**
 * Dashboard State Management Types
 * TypeScript interfaces for dashboard state management with real-time updates
 */

import { QueryKey } from '@tanstack/react-query';

// Base types
export interface BaseEntity {
  id: string;
  createdAt: Date;
  updatedAt: Date;
  version: number;
}

// Widget Configuration Types
export interface WidgetConfig extends BaseEntity {
  /** Widget type identifier */
  type: WidgetType;
  /** Widget position on dashboard */
  position: WidgetPosition;
  /** Widget size configuration */
  size: WidgetSize;
  /** Widget-specific configuration data */
  config: Record<string, any>;
  /** Whether widget is visible */
  visible: boolean;
  /** Widget display order */
  order: number;
  /** Widget title */
  title: string;
  /** Widget description */
  description?: string;
  /** Widget refresh interval in milliseconds */
  refreshInterval?: number;
  /** Widget-specific permissions */
  permissions?: string[];
  /** Widget metadata */
  metadata?: Record<string, any>;
}

export interface WidgetPosition {
  /** Grid column position */
  x: number;
  /** Grid row position */
  y: number;
  /** Grid column span */
  w: number;
  /** Grid row span */
  h: number;
}

export interface WidgetSize {
  /** Minimum width */
  minW?: number;
  /** Maximum width */
  maxW?: number;
  /** Minimum height */
  minH?: number;
  /** Maximum height */
  maxH?: number;
  /** Whether widget is resizable */
  resizable?: boolean;
  /** Whether widget is draggable */
  draggable?: boolean;
}

export type WidgetType = 
  | 'analysis_overview'
  | 'recent_analyses'
  | 'system_status'
  | 'performance_metrics'
  | 'notification_center'
  | 'user_activity'
  | 'data_export'
  | 'security_alerts'
  | 'resource_usage'
  | 'custom_chart'
  | 'data_table'
  | 'progress_tracker'
  | 'error_logs'
  | 'api_status'
  | 'custom';

// User Preferences Types
export interface UserPreferences extends BaseEntity {
  /** User ID */
  userId: string;
  /** Dashboard layout preferences */
  dashboard: DashboardPreferences;
  /** Notification preferences */
  notifications: NotificationPreferences;
  /** Theme preferences */
  theme: ThemePreferences;
  /** Display preferences */
  display: DisplayPreferences;
  /** Feature flags */
  features: FeatureFlags;
  /** Custom settings */
  custom: Record<string, any>;
}

export interface DashboardPreferences {
  /** Dashboard layout configuration */
  layout: DashboardLayout;
  /** Default widget configuration */
  defaultWidgets: WidgetConfig[];
  /** Dashboard refresh interval */
  refreshInterval: number;
  /** Auto-save preferences */
  autoSave: boolean;
  /** Dashboard theme */
  theme: string;
  /** Grid configuration */
  grid: GridConfig;
}

export interface DashboardLayout {
  /** Layout name */
  name: string;
  /** Layout description */
  description?: string;
  /** Layout configuration */
  config: Record<string, any>;
  /** Whether layout is default */
  isDefault: boolean;
  /** Layout permissions */
  permissions?: string[];
}

export interface GridConfig {
  /** Number of columns */
  columns: number;
  /** Row height in pixels */
  rowHeight: number;
  /** Margin between widgets */
  margin: [number, number];
  /** Padding around dashboard */
  padding: [number, number];
  /** Whether to compact layout */
  compact: boolean;
}

export interface NotificationPreferences {
  /** Enable notifications */
  enabled: boolean;
  /** Notification types */
  types: Record<string, boolean>;
  /** Delivery methods */
  deliveryMethods: Record<string, boolean>;
  /** Notification frequency */
  frequency: 'immediate' | 'batched' | 'digest';
  /** Quiet hours */
  quietHours?: QuietHours;
}

export interface QuietHours {
  /** Start time (24-hour format) */
  start: string;
  /** End time (24-hour format) */
  end: string;
  /** Days of week (0 = Sunday) */
  days: number[];
  /** Timezone */
  timezone: string;
}

export interface ThemePreferences {
  /** Theme mode */
  mode: 'light' | 'dark' | 'auto';
  /** Primary color */
  primaryColor: string;
  /** Secondary color */
  secondaryColor: string;
  /** Font size */
  fontSize: 'small' | 'medium' | 'large';
  /** Font family */
  fontFamily: string;
  /** Custom CSS */
  customCSS?: string;
}

export interface DisplayPreferences {
  /** Language */
  language: string;
  /** Date format */
  dateFormat: string;
  /** Time format */
  timeFormat: '12h' | '24h';
  /** Number format */
  numberFormat: string;
  /** Currency */
  currency: string;
  /** Timezone */
  timezone: string;
}

export interface FeatureFlags {
  /** Enable experimental features */
  experimental: boolean;
  /** Enable beta features */
  beta: boolean;
  /** Enable debug mode */
  debug: boolean;
  /** Feature-specific flags */
  flags: Record<string, boolean>;
}

// Real-time Event Types
export interface RealTimeEvent extends BaseEntity {
  /** Event type */
  type: RealTimeEventType;
  /** Event data */
  data: Record<string, any>;
  /** Event priority */
  priority: EventPriority;
  /** Event source */
  source: string;
  /** Event target */
  target?: string;
  /** Event timestamp */
  timestamp: Date;
  /** Event metadata */
  metadata?: Record<string, any>;
}

export type RealTimeEventType = 
  | 'analysis_progress'
  | 'analysis_complete'
  | 'analysis_failed'
  | 'system_status_change'
  | 'notification_received'
  | 'user_activity'
  | 'resource_usage_update'
  | 'security_alert'
  | 'data_export_progress'
  | 'api_status_change'
  | 'widget_update'
  | 'preference_change'
  | 'error_occurred'
  | 'custom';

export type EventPriority = 'low' | 'normal' | 'high' | 'urgent';

// WebSocket Types
export interface WebSocketMessage {
  /** Message ID */
  id: string;
  /** Message type */
  type: WebSocketMessageType;
  /** Message payload */
  payload: any;
  /** Message timestamp */
  timestamp: Date;
  /** Message source */
  source?: string;
  /** Message target */
  target?: string;
}

export type WebSocketMessageType = 
  | 'event'
  | 'ping'
  | 'pong'
  | 'error'
  | 'auth'
  | 'subscribe'
  | 'unsubscribe'
  | 'config_update'
  | 'preference_update'
  | 'custom';

export interface WebSocketConfig {
  /** WebSocket URL */
  url: string;
  /** Connection timeout */
  timeout: number;
  /** Reconnection settings */
  reconnect: ReconnectConfig;
  /** Heartbeat settings */
  heartbeat: HeartbeatConfig;
  /** Authentication token */
  authToken?: string;
}

export interface ReconnectConfig {
  /** Enable automatic reconnection */
  enabled: boolean;
  /** Maximum reconnection attempts */
  maxAttempts: number;
  /** Initial delay in milliseconds */
  initialDelay: number;
  /** Maximum delay in milliseconds */
  maxDelay: number;
  /** Backoff multiplier */
  backoffMultiplier: number;
}

export interface HeartbeatConfig {
  /** Enable heartbeat */
  enabled: boolean;
  /** Heartbeat interval in milliseconds */
  interval: number;
  /** Heartbeat timeout in milliseconds */
  timeout: number;
}

// State Management Types
export interface DashboardState {
  /** Widget configurations */
  widgets: WidgetConfig[];
  /** User preferences */
  preferences: UserPreferences | null;
  /** Real-time events */
  events: RealTimeEvent[];
  /** Connection status */
  connected: boolean;
  /** Loading state */
  loading: boolean;
  /** Error state */
  error: string | null;
  /** Last updated timestamp */
  lastUpdated: Date | null;
}

export interface DashboardStateActions {
  /** Update widget configuration */
  updateWidget: (widgetId: string, updates: Partial<WidgetConfig>) => Promise<void>;
  /** Add new widget */
  addWidget: (widget: Omit<WidgetConfig, 'id' | 'createdAt' | 'updatedAt' | 'version'>) => Promise<void>;
  /** Remove widget */
  removeWidget: (widgetId: string) => Promise<void>;
  /** Update user preferences */
  updatePreferences: (updates: Partial<UserPreferences>) => Promise<void>;
  /** Reset preferences to default */
  resetPreferences: () => Promise<void>;
  /** Save dashboard state */
  saveState: () => Promise<void>;
  /** Load dashboard state */
  loadState: () => Promise<void>;
  /** Clear all data */
  clearState: () => Promise<void>;
}

export interface RealTimeDashboardState {
  /** Real-time events */
  events: RealTimeEvent[];
  /** Event filters */
  filters: EventFilter;
  /** Connection status */
  connected: boolean;
  /** Reconnection attempts */
  reconnectAttempts: number;
  /** Last event timestamp */
  lastEventTime: Date | null;
  /** Event statistics */
  stats: EventStats;
}

export interface EventFilter {
  /** Event types to include */
  types?: RealTimeEventType[];
  /** Event priorities to include */
  priorities?: EventPriority[];
  /** Event sources to include */
  sources?: string[];
  /** Date range filter */
  dateRange?: {
    start: Date;
    end: Date;
  };
  /** Search query */
  searchQuery?: string;
  /** Maximum events to keep */
  maxEvents?: number;
}

export interface EventStats {
  /** Total events received */
  total: number;
  /** Events by type */
  byType: Record<RealTimeEventType, number>;
  /** Events by priority */
  byPriority: Record<EventPriority, number>;
  /** Events by source */
  bySource: Record<string, number>;
  /** Events per minute */
  eventsPerMinute: number;
  /** Last event time */
  lastEventTime: Date | null;
}

export interface RealTimeDashboardActions {
  /** Connect to WebSocket */
  connect: () => Promise<void>;
  /** Disconnect from WebSocket */
  disconnect: () => void;
  /** Update event filters */
  updateFilters: (filters: Partial<EventFilter>) => void;
  /** Clear all events */
  clearEvents: () => void;
  /** Subscribe to event type */
  subscribe: (eventType: RealTimeEventType) => void;
  /** Unsubscribe from event type */
  unsubscribe: (eventType: RealTimeEventType) => void;
  /** Send message */
  sendMessage: (message: Omit<WebSocketMessage, 'id' | 'timestamp'>) => void;
}

// API Types
export interface DashboardApiResponse<T = any> {
  /** Response data */
  data: T;
  /** Response metadata */
  metadata?: {
    total?: number;
    page?: number;
    limit?: number;
    hasMore?: boolean;
  };
  /** Response timestamp */
  timestamp: Date;
}

export interface DashboardApiError {
  /** Error code */
  code: string;
  /** Error message */
  message: string;
  /** Error details */
  details?: Record<string, any>;
  /** Error timestamp */
  timestamp: Date;
  /** Request ID */
  requestId?: string;
}

// Hook Return Types
export interface UseDashboardStateReturn {
  /** Dashboard state */
  state: DashboardState;
  /** State actions */
  actions: DashboardStateActions;
  /** Loading states */
  loading: {
    widgets: boolean;
    preferences: boolean;
    saving: boolean;
  };
  /** Error states */
  errors: {
    widgets: string | null;
    preferences: string | null;
    general: string | null;
  };
  /** Optimistic updates */
  optimistic: {
    isUpdating: boolean;
    pendingUpdates: string[];
  };
}

export interface UseRealTimeDashboardReturn {
  /** Real-time state */
  state: RealTimeDashboardState;
  /** Real-time actions */
  actions: RealTimeDashboardActions;
  /** Connection status */
  connection: {
    connected: boolean;
    connecting: boolean;
    reconnectAttempts: number;
    lastConnected: Date | null;
    lastDisconnected: Date | null;
  };
  /** Event handling */
  events: {
    recent: RealTimeEvent[];
    filtered: RealTimeEvent[];
    stats: EventStats;
  };
}

// Query Keys
export const DASHBOARD_QUERY_KEYS = {
  all: ['dashboard'] as const,
  widgets: () => [...DASHBOARD_QUERY_KEYS.all, 'widgets'] as const,
  widget: (id: string) => [...DASHBOARD_QUERY_KEYS.widgets(), id] as const,
  preferences: () => [...DASHBOARD_QUERY_KEYS.all, 'preferences'] as const,
  userPreferences: (userId: string) => [...DASHBOARD_QUERY_KEYS.preferences(), userId] as const,
  events: () => [...DASHBOARD_QUERY_KEYS.all, 'events'] as const,
  realTimeEvents: () => [...DASHBOARD_QUERY_KEYS.events(), 'realtime'] as const,
} as const;

// Default Values
export const DEFAULT_WIDGET_CONFIG: Partial<WidgetConfig> = {
  visible: true,
  order: 0,
  refreshInterval: 30000,
  permissions: [],
  metadata: {},
};

export const DEFAULT_USER_PREFERENCES: Partial<UserPreferences> = {
  dashboard: {
    layout: {
      name: 'default',
      description: 'Default dashboard layout',
      config: {},
      isDefault: true,
    },
    defaultWidgets: [],
    refreshInterval: 60000,
    autoSave: true,
    theme: 'light',
    grid: {
      columns: 12,
      rowHeight: 60,
      margin: [10, 10],
      padding: [20, 20],
      compact: true,
    },
  },
  notifications: {
    enabled: true,
    types: {},
    deliveryMethods: {},
    frequency: 'immediate',
  },
  theme: {
    mode: 'light',
    primaryColor: '#3b82f6',
    secondaryColor: '#64748b',
    fontSize: 'medium',
    fontFamily: 'Inter',
  },
  display: {
    language: 'en',
    dateFormat: 'MM/dd/yyyy',
    timeFormat: '12h',
    numberFormat: 'en-US',
    currency: 'USD',
    timezone: 'UTC',
  },
  features: {
    experimental: false,
    beta: false,
    debug: false,
    flags: {},
  },
  custom: {},
};

export const DEFAULT_WEB_SOCKET_CONFIG: WebSocketConfig = {
  url: 'ws://localhost:8000/ws/dashboard',
  timeout: 10000,
  reconnect: {
    enabled: true,
    maxAttempts: 5,
    initialDelay: 1000,
    maxDelay: 30000,
    backoffMultiplier: 2,
  },
  heartbeat: {
    enabled: true,
    interval: 30000,
    timeout: 5000,
  },
};

export const DEFAULT_EVENT_FILTER: EventFilter = {
  maxEvents: 1000,
};

// Utility Types
export type DashboardQueryKey = QueryKey;
export type DashboardMutationKey = string;
export type DashboardCacheKey = string;

export interface DashboardCacheConfig {
  /** Cache TTL in milliseconds */
  ttl: number;
  /** Cache key prefix */
  prefix: string;
  /** Cache version */
  version: string;
  /** Cache invalidation patterns */
  invalidationPatterns: string[];
}

export interface DashboardOptimisticUpdate<T = any> {
  /** Update ID */
  id: string;
  /** Update type */
  type: 'create' | 'update' | 'delete';
  /** Update data */
  data: T;
  /** Rollback data */
  rollback: T;
  /** Update timestamp */
  timestamp: Date;
  /** Update status */
  status: 'pending' | 'success' | 'error' | 'rolled_back';
}

export default DashboardState;
