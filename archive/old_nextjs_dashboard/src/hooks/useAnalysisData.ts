/**
 * Custom hook for fetching and managing dashboard analysis data
 * Provides centralized data fetching for dashboard components with caching and error handling
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { dashboardApi } from '@/services/dashboardApi';
import type { 
  AnalysisSummary, 
  PerformanceMetrics, 
  UserStats, 
  SystemStats,
  ApiResponse 
} from '@/services/dashboardApi';

interface UseAnalysisDataOptions {
  autoRefresh?: boolean;
  refreshInterval?: number; // in milliseconds
  cacheTimeout?: number; // in milliseconds
}

interface UseAnalysisDataReturn {
  // Data
  analyses: AnalysisSummary[];
  metrics: PerformanceMetrics | null;
  userStats: UserStats | null;
  systemStats: SystemStats | null;
  
  // Loading states
  isLoading: boolean;
  isLoadingAnalyses: boolean;
  isLoadingMetrics: boolean;
  isLoadingUserStats: boolean;
  isLoadingSystemStats: boolean;
  
  // Error states
  error: string | null;
  analysesError: string | null;
  metricsError: string | null;
  userStatsError: string | null;
  systemStatsError: string | null;
  
  // Actions
  refreshData: () => Promise<void>;
  refreshAnalyses: () => Promise<void>;
  refreshMetrics: () => Promise<void>;
  refreshUserStats: () => Promise<void>;
  refreshSystemStats: () => Promise<void>;
  
  // Cache info
  lastUpdated: Date | null;
  cacheAge: number; // in milliseconds
}

export function useAnalysisData(options: UseAnalysisDataOptions = {}): UseAnalysisDataReturn {
  const {
    autoRefresh = false,
    refreshInterval = 30000, // 30 seconds
    cacheTimeout = 60000, // 1 minute
  } = options;

  // State management
  const [analyses, setAnalyses] = useState<AnalysisSummary[]>([]);
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [userStats, setUserStats] = useState<UserStats | null>(null);
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null);

  // Loading states
  const [isLoadingAnalyses, setIsLoadingAnalyses] = useState(false);
  const [isLoadingMetrics, setIsLoadingMetrics] = useState(false);
  const [isLoadingUserStats, setIsLoadingUserStats] = useState(false);
  const [isLoadingSystemStats, setIsLoadingSystemStats] = useState(false);

  // Error states
  const [analysesError, setAnalysesError] = useState<string | null>(null);
  const [metricsError, setMetricsError] = useState<string | null>(null);
  const [userStatsError, setUserStatsError] = useState<string | null>(null);
  const [systemStatsError, setSystemStatsError] = useState<string | null>(null);

  // Cache management
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const cacheTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Computed loading state
  const isLoading = isLoadingAnalyses || isLoadingMetrics || isLoadingUserStats || isLoadingSystemStats;

  // Computed error state
  const error = analysesError || metricsError || userStatsError || systemStatsError;

  // Computed cache age
  const cacheAge = lastUpdated ? Date.now() - lastUpdated.getTime() : Infinity;

  // Fetch analyses
  const fetchAnalyses = useCallback(async (): Promise<void> => {
    setIsLoadingAnalyses(true);
    setAnalysesError(null);

    try {
      const response: ApiResponse<AnalysisSummary[]> = await dashboardApi.getAnalysisHistory(10);
      
      if (response.success && response.data) {
        setAnalyses(response.data);
      } else {
        throw new Error(response.error || 'Failed to fetch analyses');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch analyses';
      setAnalysesError(errorMessage);
      console.error('Error fetching analyses:', errorMessage);
    } finally {
      setIsLoadingAnalyses(false);
    }
  }, []);

  // Fetch performance metrics
  const fetchMetrics = useCallback(async (): Promise<void> => {
    setIsLoadingMetrics(true);
    setMetricsError(null);

    try {
      const response: ApiResponse<PerformanceMetrics> = await dashboardApi.getPerformanceMetrics();
      
      if (response.success && response.data) {
        setMetrics(response.data);
      } else {
        throw new Error(response.error || 'Failed to fetch performance metrics');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch performance metrics';
      setMetricsError(errorMessage);
      console.error('Error fetching metrics:', errorMessage);
    } finally {
      setIsLoadingMetrics(false);
    }
  }, []);

  // Fetch user stats
  const fetchUserStats = useCallback(async (): Promise<void> => {
    setIsLoadingUserStats(true);
    setUserStatsError(null);

    try {
      const response: ApiResponse<UserStats> = await dashboardApi.getUserStats();
      
      if (response.success && response.data) {
        setUserStats(response.data);
      } else {
        throw new Error(response.error || 'Failed to fetch user stats');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch user stats';
      setUserStatsError(errorMessage);
      console.error('Error fetching user stats:', errorMessage);
    } finally {
      setIsLoadingUserStats(false);
    }
  }, []);

  // Fetch system stats
  const fetchSystemStats = useCallback(async (): Promise<void> => {
    setIsLoadingSystemStats(true);
    setSystemStatsError(null);

    try {
      const response: ApiResponse<SystemStats> = await dashboardApi.getSystemStats();
      
      if (response.success && response.data) {
        setSystemStats(response.data);
      } else {
        throw new Error(response.error || 'Failed to fetch system stats');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch system stats';
      setSystemStatsError(errorMessage);
      console.error('Error fetching system stats:', errorMessage);
    } finally {
      setIsLoadingSystemStats(false);
    }
  }, []);

  // Fetch all data
  const fetchAllData = useCallback(async (): Promise<void> => {
    // Fetch all data in parallel
    await Promise.all([
      fetchAnalyses(),
      fetchMetrics(),
      fetchUserStats(),
      fetchSystemStats(),
    ]);

    setLastUpdated(new Date());
  }, [fetchAnalyses, fetchMetrics, fetchUserStats, fetchSystemStats]);

  // Refresh functions
  const refreshData = useCallback(async (): Promise<void> => {
    await fetchAllData();
  }, [fetchAllData]);

  const refreshAnalyses = useCallback(async (): Promise<void> => {
    await fetchAnalyses();
  }, [fetchAnalyses]);

  const refreshMetrics = useCallback(async (): Promise<void> => {
    await fetchMetrics();
  }, [fetchMetrics]);

  const refreshUserStats = useCallback(async (): Promise<void> => {
    await fetchUserStats();
  }, [fetchUserStats]);

  const refreshSystemStats = useCallback(async (): Promise<void> => {
    await fetchSystemStats();
  }, [fetchSystemStats]);

  // Auto-refresh setup
  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      refreshIntervalRef.current = setInterval(() => {
        // Only refresh if cache is older than cacheTimeout
        if (cacheAge > cacheTimeout) {
          fetchAllData();
        }
      }, refreshInterval);

      return () => {
        if (refreshIntervalRef.current) {
          clearInterval(refreshIntervalRef.current);
        }
      };
    }
  }, [autoRefresh, refreshInterval, cacheTimeout, cacheAge, fetchAllData]);

  // Cache timeout setup
  useEffect(() => {
    if (cacheTimeout > 0 && lastUpdated) {
      cacheTimeoutRef.current = setTimeout(() => {
        // Mark cache as expired
        console.log('Dashboard data cache expired');
      }, cacheTimeout);

      return () => {
        if (cacheTimeoutRef.current) {
          clearTimeout(cacheTimeoutRef.current);
        }
      };
    }
  }, [cacheTimeout, lastUpdated]);

  // Initial data fetch
  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
      if (cacheTimeoutRef.current) {
        clearTimeout(cacheTimeoutRef.current);
      }
    };
  }, []);

  return {
    // Data
    analyses,
    metrics,
    userStats,
    systemStats,
    
    // Loading states
    isLoading,
    isLoadingAnalyses,
    isLoadingMetrics,
    isLoadingUserStats,
    isLoadingSystemStats,
    
    // Error states
    error,
    analysesError,
    metricsError,
    userStatsError,
    systemStatsError,
    
    // Actions
    refreshData,
    refreshAnalyses,
    refreshMetrics,
    refreshUserStats,
    refreshSystemStats,
    
    // Cache info
    lastUpdated,
    cacheAge,
  };
}

export default useAnalysisData;