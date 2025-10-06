/**
 * React Query Client Configuration
 * Optimized configuration for dashboard state management with caching and error handling
 */

import { QueryClient, QueryClientConfig, DefaultOptions } from '@tanstack/react-query';
import { DASHBOARD_QUERY_KEYS } from '@/types/dashboard';

// Default query options for dashboard operations
const defaultQueryOptions: DefaultOptions['queries'] = {
  // Cache time: 5 minutes
  staleTime: 5 * 60 * 1000,
  // Background refetch: 1 minute
  refetchInterval: 60 * 1000,
  // Retry configuration
  retry: (failureCount: number, error: any) => {
    // Don't retry on 4xx errors (client errors)
    if (error?.status >= 400 && error?.status < 500) {
      return false;
    }
    // Retry up to 3 times for other errors
    return failureCount < 3;
  },
  // Retry delay with exponential backoff
  retryDelay: (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex, 30000),
  // Refetch on window focus
  refetchOnWindowFocus: true,
  // Refetch on reconnect
  refetchOnReconnect: true,
  // Keep previous data while fetching
  keepPreviousData: true,
  // Network mode
  networkMode: 'online',
};

// Default mutation options for dashboard operations
const defaultMutationOptions: DefaultOptions['mutations'] = {
  // Retry mutations once
  retry: 1,
  // Retry delay
  retryDelay: 1000,
  // Network mode
  networkMode: 'online',
};

// Query client configuration
const queryClientConfig: QueryClientConfig = {
  defaultOptions: {
    queries: defaultQueryOptions,
    mutations: defaultMutationOptions,
  },
  // Query cache configuration
  queryCache: undefined, // Use default cache
  // Mutation cache configuration
  mutationCache: undefined, // Use default cache
};

// Create the query client instance
export const queryClient = new QueryClient(queryClientConfig);

// Dashboard-specific query configurations
export const dashboardQueryConfig = {
  // Widget queries
  widgets: {
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchInterval: 30 * 1000, // 30 seconds
    refetchOnWindowFocus: true,
    retry: 2,
  },
  // User preferences queries
  preferences: {
    staleTime: 10 * 60 * 1000, // 10 minutes
    refetchInterval: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false, // Don't refetch preferences on focus
    retry: 3,
  },
  // Real-time events queries
  events: {
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 10 * 1000, // 10 seconds
    refetchOnWindowFocus: true,
    retry: 1,
  },
  // System status queries
  systemStatus: {
    staleTime: 1 * 60 * 1000, // 1 minute
    refetchInterval: 15 * 1000, // 15 seconds
    refetchOnWindowFocus: true,
    retry: 2,
  },
};

// Mutation configurations for dashboard operations
export const dashboardMutationConfig = {
  // Widget mutations
  widget: {
    retry: 1,
    retryDelay: 1000,
    onError: (error: any) => {
      console.error('Widget mutation error:', error);
    },
  },
  // Preference mutations
  preference: {
    retry: 2,
    retryDelay: 2000,
    onError: (error: any) => {
      console.error('Preference mutation error:', error);
    },
  },
  // State save mutations
  saveState: {
    retry: 3,
    retryDelay: (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex, 10000),
    onError: (error: any) => {
      console.error('State save mutation error:', error);
    },
  },
};

// Cache invalidation utilities
export const invalidateDashboardQueries = {
  // Invalidate all dashboard queries
  all: () => queryClient.invalidateQueries({ queryKey: DASHBOARD_QUERY_KEYS.all }),
  
  // Invalidate widget queries
  widgets: () => queryClient.invalidateQueries({ queryKey: DASHBOARD_QUERY_KEYS.widgets() }),
  
  // Invalidate specific widget
  widget: (widgetId: string) => 
    queryClient.invalidateQueries({ queryKey: DASHBOARD_QUERY_KEYS.widget(widgetId) }),
  
  // Invalidate preference queries
  preferences: () => queryClient.invalidateQueries({ queryKey: DASHBOARD_QUERY_KEYS.preferences() }),
  
  // Invalidate user preferences
  userPreferences: (userId: string) => 
    queryClient.invalidateQueries({ queryKey: DASHBOARD_QUERY_KEYS.userPreferences(userId) }),
  
  // Invalidate event queries
  events: () => queryClient.invalidateQueries({ queryKey: DASHBOARD_QUERY_KEYS.events() }),
  
  // Invalidate real-time events
  realTimeEvents: () => queryClient.invalidateQueries({ queryKey: DASHBOARD_QUERY_KEYS.realTimeEvents() }),
};

// Cache management utilities
export const dashboardCacheUtils = {
  // Get cached data
  getCachedData: <T>(queryKey: any[]): T | undefined => {
    return queryClient.getQueryData<T>(queryKey);
  },
  
  // Set cached data
  setCachedData: <T>(queryKey: any[], data: T) => {
    queryClient.setQueryData(queryKey, data);
  },
  
  // Remove cached data
  removeCachedData: (queryKey: any[]) => {
    queryClient.removeQueries({ queryKey });
  },
  
  // Clear all dashboard cache
  clearAll: () => {
    queryClient.clear();
  },
  
  // Prefetch dashboard data
  prefetchDashboardData: async (userId: string) => {
    await Promise.all([
      queryClient.prefetchQuery({
        queryKey: DASHBOARD_QUERY_KEYS.widgets(),
        staleTime: 5 * 60 * 1000,
      }),
      queryClient.prefetchQuery({
        queryKey: DASHBOARD_QUERY_KEYS.userPreferences(userId),
        staleTime: 10 * 60 * 1000,
      }),
    ]);
  },
};

// Error handling utilities
export const dashboardErrorHandler = {
  // Handle query errors
  handleQueryError: (error: any, queryKey: any[]) => {
    console.error(`Query error for ${queryKey.join('.')}:`, error);
    
    // Log error to monitoring service
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', 'query_error', {
        error_message: error.message,
        query_key: queryKey.join('.'),
        error_code: error.code || 'unknown',
      });
    }
  },
  
  // Handle mutation errors
  handleMutationError: (error: any, mutationKey: string) => {
    console.error(`Mutation error for ${mutationKey}:`, error);
    
    // Log error to monitoring service
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', 'mutation_error', {
        error_message: error.message,
        mutation_key: mutationKey,
        error_code: error.code || 'unknown',
      });
    }
  },
  
  // Handle network errors
  handleNetworkError: (error: any) => {
    console.error('Network error:', error);
    
    // Show user-friendly error message
    if (typeof window !== 'undefined') {
      // You can integrate with your notification system here
      console.warn('Network error occurred. Please check your connection.');
    }
  },
};

// Query client provider component
export const QueryClientProvider = ({ children }: { children: React.ReactNode }) => {
  return <>{children}</>;
};

// Hook for accessing query client
export const useQueryClient = () => {
  return queryClient;
};

// Optimistic update utilities
export const optimisticUpdateUtils = {
  // Create optimistic update
  createOptimisticUpdate: <T>(
    queryKey: any[],
    updateFn: (oldData: T | undefined) => T,
    rollbackFn: (oldData: T | undefined) => T
  ) => {
    // Cancel outgoing refetches
    queryClient.cancelQueries({ queryKey });
    
    // Snapshot previous value
    const previousData = queryClient.getQueryData<T>(queryKey);
    
    // Optimistically update
    queryClient.setQueryData(queryKey, updateFn);
    
    // Return rollback function
    return () => {
      queryClient.setQueryData(queryKey, rollbackFn(previousData));
    };
  },
  
  // Apply optimistic update with error handling
  applyOptimisticUpdate: async <T>(
    queryKey: any[],
    updateFn: (oldData: T | undefined) => T,
    mutationFn: () => Promise<any>,
    rollbackFn: (oldData: T | undefined) => T
  ) => {
    const rollback = optimisticUpdateUtils.createOptimisticUpdate(
      queryKey,
      updateFn,
      rollbackFn
    );
    
    try {
      await mutationFn();
      // Invalidate to refetch fresh data
      queryClient.invalidateQueries({ queryKey });
    } catch (error) {
      // Rollback on error
      rollback();
      throw error;
    }
  },
};

// Background sync utilities
export const backgroundSyncUtils = {
  // Enable background sync for dashboard
  enableBackgroundSync: () => {
    // Register service worker for background sync
    if ('serviceWorker' in navigator && (window.ServiceWorkerRegistration.prototype as any).sync) {
      navigator.serviceWorker.ready.then((registration) => {
        (registration as any).sync.register('dashboard-sync');
      });
    }
  },
  
  // Disable background sync
  disableBackgroundSync: () => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.ready.then((registration) => {
        (registration as any).sync.unregister('dashboard-sync');
      });
    }
  },
};

// Performance monitoring utilities
export const performanceUtils = {
  // Track query performance
  trackQueryPerformance: (queryKey: any[], startTime: number) => {
    const endTime = performance.now();
    const duration = endTime - startTime;
    
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', 'query_performance', {
        query_key: queryKey.join('.'),
        duration_ms: Math.round(duration),
        performance_category: duration > 1000 ? 'slow' : 'fast',
      });
    }
  },
  
  // Track mutation performance
  trackMutationPerformance: (mutationKey: string, startTime: number) => {
    const endTime = performance.now();
    const duration = endTime - startTime;
    
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', 'mutation_performance', {
        mutation_key: mutationKey,
        duration_ms: Math.round(duration),
        performance_category: duration > 2000 ? 'slow' : 'fast',
      });
    }
  },
};

export default queryClient;
