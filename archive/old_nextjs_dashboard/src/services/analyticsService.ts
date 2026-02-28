/**
 * Analytics Service for Frontend
 * Handles analytics data fetching, processing, and export functionality
 */

import { analyticsApi } from '@/api/analyticsApi';
import { authUtils } from '@/lib/auth';

// Types for analytics data
export type DateRangeType = 
  | 'last_7_days' 
  | 'last_30_days' 
  | 'last_90_days' 
  | 'last_year' 
  | 'custom';

export type ExportFormat = 'pdf' | 'csv' | 'excel' | 'json';

export interface CustomDateRange {
  start: Date | null;
  end: Date | null;
}

export interface AnalyticsRequest {
  dateRange: DateRangeType;
  customDateRange?: CustomDateRange;
  includeTrends?: boolean;
  includePredictions?: boolean;
  filters?: AnalyticsFilter[];
  groupBy?: string[];
  aggregationType?: 'sum' | 'avg' | 'count' | 'max' | 'min';
  limit?: number;
  offset?: number;
}

export interface AnalyticsFilter {
  type: string;
  value: string | number | string[];
  operator: string;
}

export interface DetectionPerformanceMetric {
  metric_name: string;
  value: number;
  unit: string;
  timestamp: string;
  confidence_interval?: {
    lower: number;
    upper: number;
  };
  metadata?: Record<string, any>;
}

export interface UserEngagementMetric {
  user_id: string;
  metric_name: string;
  value: number;
  timestamp: string;
  session_id?: string;
  feature_used?: string;
  duration_seconds?: number;
}

export interface SystemUtilizationMetric {
  resource_type: string;
  metric_name: string;
  value: number;
  unit: string;
  timestamp: string;
  node_id?: string;
  threshold_warning?: number;
  threshold_critical?: number;
}

export interface TrendAnalysis {
  metric_name: string;
  trend_direction: 'increasing' | 'decreasing' | 'stable' | 'volatile';
  change_percentage: number;
  period_start: string;
  period_end: string;
  data_points: number[];
  correlation_coefficient?: number;
  significance_level?: number;
}

export interface PredictiveAnalytics {
  metric_name: string;
  predicted_value: number;
  confidence_score: number;
  prediction_date: string;
  model_used: string;
  historical_accuracy: number;
  prediction_interval: {
    lower: number;
    upper: number;
  };
}

export interface AnalyticsInsight {
  insight_id: string;
  title: string;
  description: string;
  insight_type: string;
  severity: 'info' | 'warning' | 'critical';
  affected_metrics: string[];
  recommended_actions: string[];
  confidence: number;
  created_at: string;
}

export interface AnalyticsResponse {
  request_id: string;
  timestamp: string;
  detection_performance: DetectionPerformanceMetric[];
  user_engagement: UserEngagementMetric[];
  system_utilization: SystemUtilizationMetric[];
  trends: TrendAnalysis[];
  predictions: PredictiveAnalytics[];
  insights: AnalyticsInsight[];
  total_records: number;
  date_range: {
    type: DateRangeType;
    start_date?: string;
    end_date?: string;
  };
  filters_applied: AnalyticsFilter[];
  data_classification: 'public' | 'internal' | 'confidential';
  export_available: boolean;
  export_formats: ExportFormat[];
  query_execution_time_ms: number;
  cache_hit: boolean;
  data_freshness_minutes: number;
}

export interface ExportOptions {
  format: ExportFormat;
  dateRange: DateRangeType;
  customDateRange?: CustomDateRange;
  includeTrends?: boolean;
  includePredictions?: boolean;
  filters?: AnalyticsFilter[];
  compression?: boolean;
  passwordProtected?: boolean;
}

export interface ExportResult {
  export_id: string;
  download_url: string;
  expires_at: string;
  file_size_bytes: number;
  status: 'pending' | 'completed' | 'failed';
}

/**
 * Analytics Service Class
 */
export class AnalyticsService {
  private baseUrl: string;
  private authHeaders: Record<string, string>;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    this.authHeaders = authUtils.getAuthHeader();
  }

  /**
   * Get analytics data based on request parameters
   */
  async getAnalyticsData(request: AnalyticsRequest): Promise<AnalyticsResponse> {
    try {
      // Convert frontend request to backend API format
      const apiRequest = this.convertToApiRequest(request);
      
      const response = await analyticsApi.getAnalyticsData(apiRequest);
      
      if (!response.success || !response.data) {
        throw new Error(response.error || 'Failed to fetch analytics data');
      }

      return response.data;
    } catch (error) {
      console.error('Analytics service error:', error);
      throw error instanceof Error ? error : new Error('Failed to fetch analytics data');
    }
  }

  /**
   * Export analytics data
   */
  async exportData(options: ExportOptions): Promise<ExportResult> {
    try {
      const apiRequest = this.convertToApiRequest({
        dateRange: options.dateRange,
        customDateRange: options.customDateRange,
        includeTrends: options.includeTrends,
        includePredictions: options.includePredictions,
        filters: options.filters,
      });

      const response = await analyticsApi.exportData({
        ...apiRequest,
        export_format: options.format,
        compression: options.compression,
        password_protected: options.passwordProtected,
      });

      if (!response.success || !response.data) {
        throw new Error(response.error || 'Failed to export data');
      }

      return response.data;
    } catch (error) {
      console.error('Export service error:', error);
      throw error instanceof Error ? error : new Error('Failed to export data');
    }
  }

  /**
   * Get analytics health status
   */
  async getHealthStatus(): Promise<{ status: string; timestamp: string }> {
    try {
      const response = await analyticsApi.getHealthStatus();
      
      if (!response.success || !response.data) {
        throw new Error(response.error || 'Failed to get health status');
      }

      return response.data;
    } catch (error) {
      console.error('Health check error:', error);
      throw error instanceof Error ? error : new Error('Failed to get health status');
    }
  }

  /**
   * Convert frontend request format to backend API format
   */
  private convertToApiRequest(request: AnalyticsRequest): any {
    const { customDateRange, ...rest } = request;

    // Calculate date range for API
    let startDate: string | undefined;
    let endDate: string | undefined;

    if (request.dateRange === 'custom' && customDateRange?.start && customDateRange?.end) {
      startDate = customDateRange.start.toISOString();
      endDate = customDateRange.end.toISOString();
    }

    return {
      date_range: {
        type: request.dateRange,
        start_date: startDate,
        end_date: endDate,
      },
      filters: request.filters || [],
      group_by: request.groupBy || [],
      aggregation_type: request.aggregationType || 'avg',
      limit: request.limit || 1000,
      offset: request.offset || 0,
      include_trends: request.includeTrends ?? true,
      include_predictions: request.includePredictions ?? false,
    };
  }

  /**
   * Validate date range
   */
  validateDateRange(dateRange: DateRangeType, customDateRange?: CustomDateRange): boolean {
    if (dateRange === 'custom') {
      if (!customDateRange?.start || !customDateRange?.end) {
        return false;
      }
      
      if (customDateRange.start >= customDateRange.end) {
        return false;
      }

      // Check if date range is not too far in the past (max 2 years)
      const twoYearsAgo = new Date();
      twoYearsAgo.setFullYear(twoYearsAgo.getFullYear() - 2);
      
      if (customDateRange.start < twoYearsAgo) {
        return false;
      }
    }

    return true;
  }

  /**
   * Get available export formats based on data classification
   */
  getAvailableExportFormats(dataClassification: string): ExportFormat[] {
    switch (dataClassification) {
      case 'public':
        return ['pdf', 'csv', 'json'];
      case 'internal':
        return ['pdf', 'csv', 'excel', 'json'];
      case 'confidential':
        return ['pdf', 'excel']; // More secure formats for confidential data
      default:
        return ['pdf', 'csv'];
    }
  }

  /**
   * Format analytics data for display
   */
  formatMetricValue(value: number, unit: string): string {
    if (unit === 'percent') {
      return `${value.toFixed(1)}%`;
    } else if (unit === 'seconds') {
      if (value < 60) {
        return `${value.toFixed(1)}s`;
      } else {
        const minutes = Math.floor(value / 60);
        const seconds = value % 60;
        return `${minutes}m ${seconds.toFixed(0)}s`;
      }
    } else if (unit === 'count') {
      return value.toLocaleString();
    } else {
      return value.toFixed(2);
    }
  }

  /**
   * Get trend direction color
   */
  getTrendDirectionColor(direction: string): string {
    switch (direction) {
      case 'increasing':
        return 'text-green-600';
      case 'decreasing':
        return 'text-red-600';
      case 'stable':
        return 'text-blue-600';
      case 'volatile':
        return 'text-yellow-600';
      default:
        return 'text-gray-600';
    }
  }

  /**
   * Get severity color
   */
  getSeverityColor(severity: string): string {
    switch (severity) {
      case 'critical':
        return 'text-red-600 bg-red-100';
      case 'warning':
        return 'text-yellow-600 bg-yellow-100';
      case 'info':
        return 'text-blue-600 bg-blue-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  }

  /**
   * Calculate data freshness status
   */
  getDataFreshnessStatus(freshnessMinutes: number): {
    status: 'fresh' | 'stale' | 'very_stale';
    color: string;
    message: string;
  } {
    if (freshnessMinutes <= 5) {
      return {
        status: 'fresh',
        color: 'text-green-600',
        message: 'Data is current',
      };
    } else if (freshnessMinutes <= 60) {
      return {
        status: 'stale',
        color: 'text-yellow-600',
        message: 'Data is slightly outdated',
      };
    } else {
      return {
        status: 'very_stale',
        color: 'text-red-600',
        message: 'Data is outdated',
      };
    }
  }
}

// Export singleton instance
export const analyticsService = new AnalyticsService();

// Export utility functions
export const analyticsUtils = {
  /**
   * Format timestamp for display
   */
  formatTimestamp: (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));

    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
    return date.toLocaleDateString();
  },

  /**
   * Get date range label
   */
  getDateRangeLabel: (dateRange: DateRangeType, customDateRange?: CustomDateRange): string => {
    switch (dateRange) {
      case 'last_7_days':
        return 'Last 7 Days';
      case 'last_30_days':
        return 'Last 30 Days';
      case 'last_90_days':
        return 'Last 90 Days';
      case 'last_year':
        return 'Last Year';
      case 'custom':
        if (customDateRange?.start && customDateRange?.end) {
          const start = customDateRange.start.toLocaleDateString();
          const end = customDateRange.end.toLocaleDateString();
          return `${start} - ${end}`;
        }
        return 'Custom Range';
      default:
        return 'Unknown Range';
    }
  },

  /**
   * Calculate percentage change
   */
  calculatePercentageChange: (oldValue: number, newValue: number): number => {
    if (oldValue === 0) return newValue > 0 ? 100 : 0;
    return ((newValue - oldValue) / oldValue) * 100;
  },

  /**
   * Get trend icon
   */
  getTrendIcon: (direction: string): string => {
    switch (direction) {
      case 'increasing':
        return '↗';
      case 'decreasing':
        return '↘';
      case 'stable':
        return '→';
      case 'volatile':
        return '↔';
      default:
        return '?';
    }
  },
};

