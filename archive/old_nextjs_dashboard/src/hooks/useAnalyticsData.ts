/**
 * useAnalyticsData Hook
 * Custom hook for managing analytics data fetching, caching, and state
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { analyticsService, type AnalyticsRequest, type AnalyticsResponse, type ExportOptions, type ExportResult } from '@/services/analyticsService';

export interface UseAnalyticsDataOptions {
  dateRange: string;
  customDateRange?: { start: Date | null; end: Date | null };
  includeTrends?: boolean;
  includePredictions?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
  enabled?: boolean;
}

export interface UseAnalyticsDataReturn {
  analyticsData: AnalyticsResponse | null;
  isLoading: boolean;
  error: string | null;
  refreshData: () => Promise<void>;
  exportData: (format: string, options?: Partial<ExportOptions>) => Promise<ExportResult>;
  lastRefresh: Date | null;
  isExporting: boolean;
  exportError: string | null;
  dataFreshness: {
    status: 'fresh' | 'stale' | 'very_stale';
    color: string;
    message: string;
  };
}

export function useAnalyticsData(options: UseAnalyticsDataOptions): UseAnalyticsDataReturn {
  const {
    dateRange,
    customDateRange,
    includeTrends = true,
    includePredictions = false,
    autoRefresh = false,
    refreshInterval = 300000, // 5 minutes
    enabled = true,
  } = options;

  // State management
  const [analyticsData, setAnalyticsData] = useState<AnalyticsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  // Refs for cleanup
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);

  // Calculate data freshness
  const dataFreshness = analyticsData ? analyticsService.getDataFreshnessStatus(analyticsData.data_freshness_minutes) : {
    status: 'very_stale' as const,
    color: 'text-red-600',
    message: 'No data available',
  };

  // Fetch analytics data
  const fetchAnalyticsData = useCallback(async () => {
    if (!enabled) return;

    setIsLoading(true);
    setError(null);

    try {
      const request: AnalyticsRequest = {
        dateRange: dateRange as any,
        customDateRange,
        includeTrends,
        includePredictions,
      };

      // Validate request
      if (!analyticsService.validateDateRange(request.dateRange, request.customDateRange)) {
        throw new Error('Invalid date range provided');
      }

      const data = await analyticsService.getAnalyticsData(request);
      
      if (mountedRef.current) {
        setAnalyticsData(data);
        setLastRefresh(new Date());
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : 'Failed to fetch analytics data');
      }
    } finally {
      if (mountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [enabled, dateRange, customDateRange, includeTrends, includePredictions]);

  // Refresh data function
  const refreshData = useCallback(async () => {
    await fetchAnalyticsData();
  }, [fetchAnalyticsData]);

  // Export data function
  const exportData = useCallback(async (format: string, options?: Partial<ExportOptions>): Promise<ExportResult> => {
    setIsExporting(true);
    setExportError(null);

    try {
      const exportOptions: ExportOptions = {
        format: format as any,
        dateRange: dateRange as any,
        customDateRange,
        includeTrends,
        includePredictions,
        ...options,
      };

      const result = await analyticsService.exportData(exportOptions);
      
      if (mountedRef.current) {
        setIsExporting(false);
      }
      
      return result;
    } catch (err) {
      if (mountedRef.current) {
        setExportError(err instanceof Error ? err.message : 'Export failed');
        setIsExporting(false);
      }
      throw err;
    }
  }, [dateRange, customDateRange, includeTrends, includePredictions]);

  // Set up auto-refresh
  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      refreshTimeoutRef.current = setTimeout(() => {
        if (mountedRef.current) {
          fetchAnalyticsData();
        }
      }, refreshInterval);

      return () => {
        if (refreshTimeoutRef.current) {
          clearTimeout(refreshTimeoutRef.current);
        }
      };
    }
  }, [autoRefresh, refreshInterval, fetchAnalyticsData]);

  // Initial data fetch
  useEffect(() => {
    fetchAnalyticsData();
  }, [fetchAnalyticsData]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
    };
  }, []);

  return {
    analyticsData,
    isLoading,
    error,
    refreshData,
    exportData,
    lastRefresh,
    isExporting,
    exportError,
    dataFreshness,
  };
}

// Additional utility hooks

/**
 * Hook for analytics data with real-time updates
 */
export function useAnalyticsDataRealtime(options: UseAnalyticsDataOptions & { 
  websocketUrl?: string;
  updateInterval?: number;
}) {
  const analyticsHook = useAnalyticsData({
    ...options,
    autoRefresh: true,
    refreshInterval: options.updateInterval || 30000, // 30 seconds for real-time
  });

  // WebSocket connection for real-time updates
  useEffect(() => {
    if (!options.websocketUrl) return;

    const ws = new WebSocket(options.websocketUrl);
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'analytics_update') {
          analyticsHook.refreshData();
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      ws.close();
    };
  }, [options.websocketUrl, analyticsHook.refreshData]);

  return analyticsHook;
}

/**
 * Hook for analytics data with caching
 */
export function useAnalyticsDataCached(options: UseAnalyticsDataOptions & {
  cacheKey?: string;
  cacheDuration?: number;
}) {
  const cacheKey = options.cacheKey || `analytics-${options.dateRange}`;
  const cacheDuration = options.cacheDuration || 300000; // 5 minutes

  const analyticsHook = useAnalyticsData(options);

  // Check cache on mount
  useEffect(() => {
    const cachedData = localStorage.getItem(cacheKey);
    const cacheTimestamp = localStorage.getItem(`${cacheKey}-timestamp`);
    
    if (cachedData && cacheTimestamp) {
      const cacheAge = Date.now() - parseInt(cacheTimestamp);
      
      if (cacheAge < cacheDuration) {
        try {
          const parsedData = JSON.parse(cachedData);
          setAnalyticsData(parsedData);
          setLastRefresh(new Date(parseInt(cacheTimestamp)));
        } catch (err) {
          console.error('Failed to parse cached data:', err);
        }
      }
    }
  }, [cacheKey, cacheDuration]);

  // Save to cache when data changes
  useEffect(() => {
    if (analyticsHook.analyticsData) {
      localStorage.setItem(cacheKey, JSON.stringify(analyticsHook.analyticsData));
      localStorage.setItem(`${cacheKey}-timestamp`, Date.now().toString());
    }
  }, [analyticsHook.analyticsData, cacheKey]);

  return analyticsHook;
}

/**
 * Hook for analytics data with error recovery
 */
export function useAnalyticsDataWithRecovery(options: UseAnalyticsDataOptions & {
  maxRetries?: number;
  retryDelay?: number;
}) {
  const maxRetries = options.maxRetries || 3;
  const retryDelay = options.retryDelay || 1000;

  const analyticsHook = useAnalyticsData(options);
  const [retryCount, setRetryCount] = useState(0);

  // Retry logic
  useEffect(() => {
    if (analyticsHook.error && retryCount < maxRetries) {
      const timeout = setTimeout(() => {
        setRetryCount(prev => prev + 1);
        analyticsHook.refreshData();
      }, retryDelay * Math.pow(2, retryCount)); // Exponential backoff

      return () => clearTimeout(timeout);
    }
  }, [analyticsHook.error, retryCount, maxRetries, retryDelay, analyticsHook.refreshData]);

  // Reset retry count on successful fetch
  useEffect(() => {
    if (analyticsHook.analyticsData && retryCount > 0) {
      setRetryCount(0);
    }
  }, [analyticsHook.analyticsData, retryCount]);

  return {
    ...analyticsHook,
    retryCount,
    maxRetries,
    canRetry: retryCount < maxRetries,
  };
}
