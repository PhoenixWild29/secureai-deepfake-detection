/**
 * Notifications API Client
 * Handles API calls to the notifications backend endpoints
 */

import { authUtils } from '@/lib/auth';

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

// Types for API requests and responses
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface NotificationListResponse {
  success: boolean;
  data?: {
    notifications: any[];
    stats: any;
    total: number;
    hasMore: boolean;
  };
  error?: string;
}

export interface NotificationPreferencesResponse {
  success: boolean;
  data?: any;
  error?: string;
}

/**
 * Notifications API service class
 */
export class NotificationsApiService {
  private baseUrl: string;
  private authHeaders: Record<string, string>;

  constructor() {
    this.baseUrl = API_BASE_URL;
    this.authHeaders = authUtils.getAuthHeader();
  }

  /**
   * Get notifications for a user
   */
  async getNotifications(userId: string, filter?: any): Promise<NotificationListResponse> {
    try {
      const params = new URLSearchParams();
      if (filter) {
        Object.entries(filter).forEach(([key, value]) => {
          if (value !== undefined && value !== null) {
            if (Array.isArray(value)) {
              value.forEach(item => params.append(key, String(item)));
            } else {
              params.append(key, String(value));
            }
          }
        });
      }

      const response = await fetch(`${this.baseUrl}/api/v1/notifications/${userId}?${params.toString()}`, {
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
        error: error instanceof Error ? error.message : 'Failed to fetch notifications',
      };
    }
  }

  /**
   * Get notification history with filtering
   */
  async getNotificationHistory(userId: string, filter?: any): Promise<NotificationListResponse> {
    try {
      const params = new URLSearchParams();
      if (filter) {
        Object.entries(filter).forEach(([key, value]) => {
          if (value !== undefined && value !== null) {
            if (Array.isArray(value)) {
              value.forEach(item => params.append(key, String(item)));
            } else {
              params.append(key, String(value));
            }
          }
        });
      }

      const response = await fetch(`${this.baseUrl}/api/v1/notifications/${userId}/history?${params.toString()}`, {
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
        error: error instanceof Error ? error.message : 'Failed to fetch notification history',
      };
    }
  }

  /**
   * Mark notification as read
   */
  async markAsRead(notificationId: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/notifications/${notificationId}/read`, {
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
        error: error instanceof Error ? error.message : 'Failed to mark as read',
      };
    }
  }

  /**
   * Dismiss notification
   */
  async dismissNotification(notificationId: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/notifications/${notificationId}/dismiss`, {
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
        error: error instanceof Error ? error.message : 'Failed to dismiss notification',
      };
    }
  }

  /**
   * Archive notification
   */
  async archiveNotification(notificationId: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/notifications/${notificationId}/archive`, {
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
        error: error instanceof Error ? error.message : 'Failed to archive notification',
      };
    }
  }

  /**
   * Delete notification
   */
  async deleteNotification(notificationId: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/notifications/${notificationId}`, {
        method: 'DELETE',
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
        error: error instanceof Error ? error.message : 'Failed to delete notification',
      };
    }
  }

  /**
   * Mark all notifications as read
   */
  async markAllAsRead(userId: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/notifications/${userId}/mark-all-read`, {
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
        error: error instanceof Error ? error.message : 'Failed to mark all as read',
      };
    }
  }

  /**
   * Get user notification preferences
   */
  async getPreferences(userId: string): Promise<NotificationPreferencesResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/notifications/${userId}/preferences`, {
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
        error: error instanceof Error ? error.message : 'Failed to fetch preferences',
      };
    }
  }

  /**
   * Update user notification preferences
   */
  async updatePreferences(userId: string, preferences: any): Promise<NotificationPreferencesResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/notifications/${userId}/preferences`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...this.authHeaders,
        },
        body: JSON.stringify(preferences),
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
        error: error instanceof Error ? error.message : 'Failed to update preferences',
      };
    }
  }

  /**
   * Get notification statistics
   */
  async getStats(userId: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/notifications/${userId}/stats`, {
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
        error: error instanceof Error ? error.message : 'Failed to fetch stats',
      };
    }
  }

  /**
   * Test notification delivery
   */
  async testNotification(userId: string, type: string): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/notifications/${userId}/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.authHeaders,
        },
        body: JSON.stringify({ type }),
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
        error: error instanceof Error ? error.message : 'Failed to send test notification',
      };
    }
  }

  /**
   * Export notification history
   */
  async exportHistory(userId: string, format: string = 'csv', filter?: any): Promise<Blob> {
    try {
      const params = new URLSearchParams();
      params.append('format', format);
      if (filter) {
        Object.entries(filter).forEach(([key, value]) => {
          if (value !== undefined && value !== null) {
            if (Array.isArray(value)) {
              value.forEach(item => params.append(key, String(item)));
            } else {
              params.append(key, String(value));
            }
          }
        });
      }

      const response = await fetch(`${this.baseUrl}/api/v1/notifications/${userId}/export?${params.toString()}`, {
        method: 'GET',
        headers: {
          ...this.authHeaders,
        },
      });

      if (!response.ok) {
        throw new Error(`Export failed with status: ${response.status}`);
      }

      return await response.blob();
    } catch (error) {
      throw error instanceof Error ? error : new Error('Export failed');
    }
  }

  /**
   * Validate notification preferences
   */
  async validatePreferences(preferences: any): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/notifications/preferences/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.authHeaders,
        },
        body: JSON.stringify(preferences),
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
        error: error instanceof Error ? error.message : 'Failed to validate preferences',
      };
    }
  }
}

// Export singleton instance
export const notificationsApi = new NotificationsApiService();

// Export utility functions
export const notificationsApiUtils = {
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
