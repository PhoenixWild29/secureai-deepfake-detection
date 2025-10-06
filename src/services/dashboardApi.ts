/**
 * Dashboard API Service
 * Handles API calls for dashboard state persistence, widget configurations, and user preferences
 */

import { 
  WidgetConfig, 
  UserPreferences, 
  DashboardApiResponse, 
  DashboardApiError,
  DashboardState,
  RealTimeEvent,
  EventFilter
} from '@/types/dashboard';

// API configuration
interface ApiConfig {
  baseUrl: string;
  timeout: number;
  retries: number;
  retryDelay: number;
}

const DEFAULT_API_CONFIG: ApiConfig = {
  baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api',
  timeout: 10000,
  retries: 3,
  retryDelay: 1000,
};

// HTTP methods
type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

// Request options
interface RequestOptions {
  method: HttpMethod;
  headers?: Record<string, string>;
  body?: any;
  timeout?: number;
  retries?: number;
}

// API error class
export class DashboardApiError extends Error {
  public code: string;
  public status: number;
  public details?: Record<string, any>;
  public requestId?: string;

  constructor(
    message: string,
    code: string = 'UNKNOWN_ERROR',
    status: number = 500,
    details?: Record<string, any>,
    requestId?: string
  ) {
    super(message);
    this.name = 'DashboardApiError';
    this.code = code;
    this.status = status;
    this.details = details;
    this.requestId = requestId;
  }
}

// Dashboard API service class
export class DashboardApiService {
  private config: ApiConfig;
  private authToken: string | null = null;

  constructor(config: Partial<ApiConfig> = {}) {
    this.config = { ...DEFAULT_API_CONFIG, ...config };
  }

  /**
   * Set authentication token
   */
  public setAuthToken(token: string): void {
    this.authToken = token;
  }

  /**
   * Clear authentication token
   */
  public clearAuthToken(): void {
    this.authToken = null;
  }

  // Widget API methods

  /**
   * Get all widgets for user
   */
  public async getWidgets(userId: string): Promise<WidgetConfig[]> {
    const response = await this.request<DashboardApiResponse<WidgetConfig[]>>({
      method: 'GET',
      url: `/dashboard/widgets?userId=${userId}`,
    });
    return response.data;
  }

  /**
   * Get specific widget
   */
  public async getWidget(widgetId: string): Promise<WidgetConfig> {
    const response = await this.request<DashboardApiResponse<WidgetConfig>>({
      method: 'GET',
      url: `/dashboard/widgets/${widgetId}`,
    });
    return response.data;
  }

  /**
   * Create new widget
   */
  public async createWidget(widget: Omit<WidgetConfig, 'id' | 'createdAt' | 'updatedAt' | 'version'>): Promise<WidgetConfig> {
    const response = await this.request<DashboardApiResponse<WidgetConfig>>({
      method: 'POST',
      url: '/dashboard/widgets',
      body: widget,
    });
    return response.data;
  }

  /**
   * Update widget
   */
  public async updateWidget(widgetId: string, updates: Partial<WidgetConfig>): Promise<WidgetConfig> {
    const response = await this.request<DashboardApiResponse<WidgetConfig>>({
      method: 'PUT',
      url: `/dashboard/widgets/${widgetId}`,
      body: updates,
    });
    return response.data;
  }

  /**
   * Delete widget
   */
  public async deleteWidget(widgetId: string): Promise<void> {
    await this.request<DashboardApiResponse<void>>({
      method: 'DELETE',
      url: `/dashboard/widgets/${widgetId}`,
    });
  }

  /**
   * Reorder widgets
   */
  public async reorderWidgets(widgetIds: string[]): Promise<void> {
    await this.request<DashboardApiResponse<void>>({
      method: 'PATCH',
      url: '/dashboard/widgets/reorder',
      body: { widgetIds },
    });
  }

  // User Preferences API methods

  /**
   * Get user preferences
   */
  public async getUserPreferences(userId: string): Promise<UserPreferences> {
    const response = await this.request<DashboardApiResponse<UserPreferences>>({
      method: 'GET',
      url: `/dashboard/preferences/${userId}`,
    });
    return response.data;
  }

  /**
   * Update user preferences
   */
  public async updateUserPreferences(userId: string, updates: Partial<UserPreferences>): Promise<UserPreferences> {
    const response = await this.request<DashboardApiResponse<UserPreferences>>({
      method: 'PUT',
      url: `/dashboard/preferences/${userId}`,
      body: updates,
    });
    return response.data;
  }

  /**
   * Reset user preferences to default
   */
  public async resetUserPreferences(userId: string): Promise<UserPreferences> {
    const response = await this.request<DashboardApiResponse<UserPreferences>>({
      method: 'POST',
      url: `/dashboard/preferences/${userId}/reset`,
    });
    return response.data;
  }

  // Dashboard State API methods

  /**
   * Save dashboard state
   */
  public async saveDashboardState(userId: string, state: Partial<DashboardState>): Promise<void> {
    await this.request<DashboardApiResponse<void>>({
      method: 'POST',
      url: `/dashboard/state/${userId}`,
      body: state,
    });
  }

  /**
   * Load dashboard state
   */
  public async loadDashboardState(userId: string): Promise<DashboardState> {
    const response = await this.request<DashboardApiResponse<DashboardState>>({
      method: 'GET',
      url: `/dashboard/state/${userId}`,
    });
    return response.data;
  }

  /**
   * Clear dashboard state
   */
  public async clearDashboardState(userId: string): Promise<void> {
    await this.request<DashboardApiResponse<void>>({
      method: 'DELETE',
      url: `/dashboard/state/${userId}`,
    });
  }

  // Real-time Events API methods

  /**
   * Get real-time events
   */
  public async getRealTimeEvents(filter?: EventFilter): Promise<RealTimeEvent[]> {
    const params = new URLSearchParams();
    if (filter) {
      if (filter.types) params.append('types', filter.types.join(','));
      if (filter.priorities) params.append('priorities', filter.priorities.join(','));
      if (filter.sources) params.append('sources', filter.sources.join(','));
      if (filter.dateRange) {
        params.append('start', filter.dateRange.start.toISOString());
        params.append('end', filter.dateRange.end.toISOString());
      }
      if (filter.searchQuery) params.append('search', filter.searchQuery);
      if (filter.maxEvents) params.append('limit', filter.maxEvents.toString());
    }

    const response = await this.request<DashboardApiResponse<RealTimeEvent[]>>({
      method: 'GET',
      url: `/dashboard/events?${params.toString()}`,
    });
    return response.data;
  }

  /**
   * Get event statistics
   */
  public async getEventStatistics(): Promise<Record<string, any>> {
    const response = await this.request<DashboardApiResponse<Record<string, any>>>({
      method: 'GET',
      url: '/dashboard/events/statistics',
    });
    return response.data;
  }

  // System Status API methods

  /**
   * Get system status
   */
  public async getSystemStatus(): Promise<Record<string, any>> {
    const response = await this.request<DashboardApiResponse<Record<string, any>>>({
      method: 'GET',
      url: '/dashboard/system/status',
    });
    return response.data;
  }

  /**
   * Get resource usage
   */
  public async getResourceUsage(): Promise<Record<string, any>> {
    const response = await this.request<DashboardApiResponse<Record<string, any>>>({
      method: 'GET',
      url: '/dashboard/system/resources',
    });
    return response.data;
  }

  // Batch operations

  /**
   * Batch update widgets
   */
  public async batchUpdateWidgets(updates: Array<{ id: string; updates: Partial<WidgetConfig> }>): Promise<WidgetConfig[]> {
    const response = await this.request<DashboardApiResponse<WidgetConfig[]>>({
      method: 'PATCH',
      url: '/dashboard/widgets/batch',
      body: { updates },
    });
    return response.data;
  }

  /**
   * Batch delete widgets
   */
  public async batchDeleteWidgets(widgetIds: string[]): Promise<void> {
    await this.request<DashboardApiResponse<void>>({
      method: 'DELETE',
      url: '/dashboard/widgets/batch',
      body: { widgetIds },
    });
  }

  // Health check

  /**
   * Check API health
   */
  public async healthCheck(): Promise<{ status: string; timestamp: Date }> {
    const response = await this.request<DashboardApiResponse<{ status: string; timestamp: Date }>>({
      method: 'GET',
      url: '/dashboard/health',
    });
    return response.data;
  }

  // Private methods

  private async request<T>(options: RequestOptions & { url: string }): Promise<T> {
    const { method, url, headers = {}, body, timeout = this.config.timeout, retries = this.config.retries } = options;
    
    const requestHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      ...headers,
    };

    // Add authentication header if token is available
    if (this.authToken) {
      requestHeaders['Authorization'] = `Bearer ${this.authToken}`;
    }

    const requestOptions: RequestInit = {
      method,
      headers: requestHeaders,
      signal: AbortSignal.timeout(timeout),
    };

    if (body && method !== 'GET') {
      requestOptions.body = JSON.stringify(body);
    }

    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const response = await fetch(`${this.config.baseUrl}${url}`, requestOptions);
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new DashboardApiError(
            errorData.message || `HTTP ${response.status}: ${response.statusText}`,
            errorData.code || 'HTTP_ERROR',
            response.status,
            errorData.details,
            response.headers.get('X-Request-ID') || undefined
          );
        }

        const data = await response.json();
        return data as T;

      } catch (error) {
        lastError = error as Error;
        
        // Don't retry on client errors (4xx)
        if (error instanceof DashboardApiError && error.status >= 400 && error.status < 500) {
          throw error;
        }

        // Don't retry on last attempt
        if (attempt === retries) {
          break;
        }

        // Wait before retry
        await this.delay(this.config.retryDelay * Math.pow(2, attempt));
      }
    }

    throw lastError || new DashboardApiError('Request failed after all retries');
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Singleton instance
let dashboardApiServiceInstance: DashboardApiService | null = null;

/**
 * Get dashboard API service singleton instance
 */
export const getDashboardApiService = (config?: Partial<ApiConfig>): DashboardApiService => {
  if (!dashboardApiServiceInstance) {
    dashboardApiServiceInstance = new DashboardApiService(config);
  }
  return dashboardApiServiceInstance;
};

/**
 * Create new dashboard API service instance
 */
export const createDashboardApiService = (config?: Partial<ApiConfig>): DashboardApiService => {
  return new DashboardApiService(config);
};

/**
 * Destroy dashboard API service singleton
 */
export const destroyDashboardApiService = (): void => {
  dashboardApiServiceInstance = null;
};

// Utility functions

/**
 * Handle API errors with user-friendly messages
 */
export const handleApiError = (error: unknown): string => {
  if (error instanceof DashboardApiError) {
    switch (error.code) {
      case 'UNAUTHORIZED':
        return 'Please log in to continue';
      case 'FORBIDDEN':
        return 'You do not have permission to perform this action';
      case 'NOT_FOUND':
        return 'The requested resource was not found';
      case 'VALIDATION_ERROR':
        return 'Please check your input and try again';
      case 'RATE_LIMITED':
        return 'Too many requests. Please wait a moment and try again';
      case 'SERVER_ERROR':
        return 'Server error. Please try again later';
      default:
        return error.message || 'An unexpected error occurred';
    }
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  return 'An unexpected error occurred';
};

/**
 * Check if error is retryable
 */
export const isRetryableError = (error: unknown): boolean => {
  if (error instanceof DashboardApiError) {
    // Don't retry client errors (4xx)
    if (error.status >= 400 && error.status < 500) {
      return false;
    }
    // Retry server errors (5xx) and network errors
    return true;
  }
  
  // Retry other errors (network, timeout, etc.)
  return true;
};

/**
 * Get retry delay with exponential backoff
 */
export const getRetryDelay = (attempt: number, baseDelay: number = 1000, maxDelay: number = 30000): number => {
  const delay = baseDelay * Math.pow(2, attempt);
  return Math.min(delay, maxDelay);
};

export default DashboardApiService;