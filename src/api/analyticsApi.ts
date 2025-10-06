/**
 * Analytics API Client
 * Handles API calls to the analytics backend endpoints
 */

import { authUtils } from '@/lib/auth';

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

// Types for API requests and responses
export interface ApiRequest {
  date_range: {
    type: string;
    start_date?: string;
    end_date?: string;
  };
  filters?: Array<{
    type: string;
    value: string | number | string[];
    operator: string;
  }>;
  group_by?: string[];
  aggregation_type?: string;
  limit?: number;
  offset?: number;
  include_trends?: boolean;
  include_predictions?: boolean;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface ExportRequest {
  date_range: {
    type: string;
    start_date?: string;
    end_date?: string;
  };
  filters?: Array<{
    type: string;
    value: string | number | string[];
    operator: string;
  }>;
  group_by?: string[];
  aggregation_type?: string;
  limit?: number;
  offset?: number;
  include_trends?: boolean;
  include_predictions?: boolean;
  export_format: string;
  compression?: boolean;
  password_protected?: boolean;
}

export interface HealthStatus {
  status: string;
  timestamp: string;
}

/**
 * Analytics API service class
 */
export class AnalyticsApiService {
  private baseUrl: string;
  private authHeaders: Record<string, string>;

  constructor() {
    this.baseUrl = API_BASE_URL;
    this.authHeaders = authUtils.getAuthHeader();
  }

  /**
   * Get analytics data from the backend
   */
  async getAnalyticsData(request: ApiRequest): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/dashboard/analytics`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.authHeaders,
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return {
        success: true,
        data: data,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred',
      };
    }
  }

  /**
   * Export analytics data
   */
  async exportData(request: ExportRequest): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/dashboard/analytics/export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.authHeaders,
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return {
        success: true,
        data: data,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Export failed',
      };
    }
  }

  /**
   * Get analytics health status
   */
  async getHealthStatus(): Promise<ApiResponse<HealthStatus>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/dashboard/analytics/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...this.authHeaders,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return {
        success: true,
        data: data,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Health check failed',
      };
    }
  }

  /**
   * Get analytics context (permissions, available metrics, etc.)
   */
  async getAnalyticsContext(): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/dashboard/analytics/context`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...this.authHeaders,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return {
        success: true,
        data: data,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to get analytics context',
      };
    }
  }

  /**
   * Get analytics permissions for current user
   */
  async getAnalyticsPermissions(): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/dashboard/analytics/permissions`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...this.authHeaders,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return {
        success: true,
        data: data,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to get analytics permissions',
      };
    }
  }

  /**
   * Download exported file
   */
  async downloadExport(exportId: string): Promise<Blob> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/dashboard/analytics/export/${exportId}/download`, {
        method: 'GET',
        headers: {
          ...this.authHeaders,
        },
      });

      if (!response.ok) {
        throw new Error(`Download failed with status: ${response.status}`);
      }

      return await response.blob();
    } catch (error) {
      throw error instanceof Error ? error : new Error('Download failed');
    }
  }

  /**
   * Check export status
   */
  async getExportStatus(exportId: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/dashboard/analytics/export/${exportId}/status`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...this.authHeaders,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return {
        success: true,
        data: data,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to get export status',
      };
    }
  }

  /**
   * Cancel export
   */
  async cancelExport(exportId: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/dashboard/analytics/export/${exportId}/cancel`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.authHeaders,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return {
        success: true,
        data: data,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to cancel export',
      };
    }
  }

  /**
   * Get available metrics
   */
  async getAvailableMetrics(): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/dashboard/analytics/metrics`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...this.authHeaders,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return {
        success: true,
        data: data,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to get available metrics',
      };
    }
  }

  /**
   * Get data sources
   */
  async getDataSources(): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/dashboard/analytics/sources`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...this.authHeaders,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return {
        success: true,
        data: data,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to get data sources',
      };
    }
  }

  /**
   * Validate analytics request
   */
  async validateRequest(request: ApiRequest): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/dashboard/analytics/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.authHeaders,
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return {
        success: true,
        data: data,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Request validation failed',
      };
    }
  }
}

// Export singleton instance
export const analyticsApi = new AnalyticsApiService();

// Export utility functions
export const analyticsApiUtils = {
  /**
   * Build query parameters for GET requests
   */
  buildQueryParams: (params: Record<string, any>): string => {
    const searchParams = new URLSearchParams();
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        if (Array.isArray(value)) {
          value.forEach(item => searchParams.append(key, String(item)));
        } else {
          searchParams.append(key, String(value));
        }
      }
    });

    const queryString = searchParams.toString();
    return queryString ? `?${queryString}` : '';
  },

  /**
   * Handle API response errors
   */
  handleApiError: (error: any): string => {
    if (error?.response?.data?.error) {
      return error.response.data.error;
    } else if (error?.message) {
      return error.message;
    } else if (typeof error === 'string') {
      return error;
    } else {
      return 'An unexpected error occurred';
    }
  },

  /**
   * Check if response is successful
   */
  isSuccessfulResponse: (response: ApiResponse<any>): boolean => {
    return response.success === true && response.data !== undefined;
  },

  /**
   * Get error message from response
   */
  getErrorMessage: (response: ApiResponse<any>): string => {
    return response.error || response.message || 'Unknown error occurred';
  },

  /**
   * Format API request for logging
   */
  formatRequestForLogging: (request: ApiRequest): Record<string, any> => {
    return {
      date_range: request.date_range,
      filters_count: request.filters?.length || 0,
      group_by: request.group_by || [],
      aggregation_type: request.aggregation_type || 'avg',
      limit: request.limit || 1000,
      include_trends: request.include_trends ?? true,
      include_predictions: request.include_predictions ?? false,
    };
  },

  /**
   * Retry logic for failed requests
   */
  retryRequest: async <T>(
    requestFn: () => Promise<ApiResponse<T>>,
    maxRetries: number = 3,
    delay: number = 1000
  ): Promise<ApiResponse<T>> => {
    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        const response = await requestFn();
        if (response.success) {
          return response;
        }
        lastError = new Error(response.error || 'Request failed');
      } catch (error) {
        lastError = error instanceof Error ? error : new Error('Request failed');
      }

      if (attempt < maxRetries) {
        await new Promise(resolve => setTimeout(resolve, delay * attempt));
      }
    }

    return {
      success: false,
      error: lastError?.message || 'Request failed after retries',
    };
  },
};
