/**
 * Navigation Utilities
 * 
 * Provides utility functions for navigation state management, breadcrumb generation,
 * data prefetching, and navigation history tracking.
 */

import { generateEnhancedBreadcrumbs, formatSegmentLabel } from './urlUtils';

/**
 * Navigation history management
 */
export const NAVIGATION_HISTORY_LIMIT = 10;

/**
 * Creates a navigation history entry
 * @param {string} path - The navigation path
 * @param {string} label - The display label
 * @param {Object} metadata - Additional metadata
 * @returns {Object} Navigation history entry
 */
export const createNavigationEntry = (path, label, metadata = {}) => ({
  path,
  label,
  timestamp: Date.now(),
  metadata: {
    ...metadata,
    userAgent: navigator.userAgent,
    referrer: document.referrer
  }
});

/**
 * Adds an entry to navigation history
 * @param {Array} history - Current navigation history
 * @param {Object} entry - New navigation entry
 * @returns {Array} Updated navigation history
 */
export const addToNavigationHistory = (history, entry) => {
  // Avoid duplicate consecutive entries
  if (history.length > 0 && history[history.length - 1].path === entry.path) {
    return history;
  }

  const newHistory = [...history, entry];
  
  // Limit history size
  if (newHistory.length > NAVIGATION_HISTORY_LIMIT) {
    return newHistory.slice(-NAVIGATION_HISTORY_LIMIT);
  }
  
  return newHistory;
};

/**
 * Gets navigation history for a specific path
 * @param {Array} history - Navigation history
 * @param {string} path - Path to search for
 * @returns {Array} Filtered history entries
 */
export const getNavigationHistoryForPath = (history, path) => {
  return history.filter(entry => entry.path.startsWith(path));
};

/**
 * Clears navigation history
 * @returns {Array} Empty history array
 */
export const clearNavigationHistory = () => [];

/**
 * Route-specific data prefetching configuration
 */
export const ROUTE_DATA_CONFIG = {
  '/upload': {
    dataKeys: ['upload-config'],
    prefetchFn: 'prefetchUploadConfig',
    priority: 'high'
  },
  '/results': {
    dataKeys: ['recent-results'],
    prefetchFn: 'prefetchRecentResults',
    priority: 'high'
  },
  '/history': {
    dataKeys: ['analysis-history'],
    prefetchFn: 'prefetchAnalysisHistory',
    priority: 'medium'
  },
  '/reports': {
    dataKeys: ['available-reports'],
    prefetchFn: 'prefetchAvailableReports',
    priority: 'medium'
  },
  '/analytics': {
    dataKeys: ['analytics-data', 'dashboard-metrics'],
    prefetchFn: 'prefetchAnalyticsData',
    priority: 'high'
  },
  '/settings': {
    dataKeys: ['user-preferences', 'system-config'],
    prefetchFn: 'prefetchSettingsData',
    priority: 'low'
  },
  '/notifications': {
    dataKeys: ['notification-history', 'notification-settings'],
    prefetchFn: 'prefetchNotificationData',
    priority: 'medium'
  },
  '/system': {
    dataKeys: ['system-status', 'performance-metrics'],
    prefetchFn: 'prefetchSystemData',
    priority: 'low'
  }
};

/**
 * Prefetches upload configuration data
 * @param {Object} queryClient - TanStack Query client
 * @returns {Promise} Prefetch promise
 */
export const prefetchUploadConfig = async (queryClient) => {
  try {
    await queryClient.prefetchQuery({
      queryKey: ['upload-config'],
      queryFn: async () => {
        // Mock implementation - replace with actual API call
        const response = await fetch('/api/upload/config');
        if (!response.ok) throw new Error('Failed to fetch upload config');
        return response.json();
      },
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 30 * 60 * 1000 // 30 minutes
    });
  } catch (error) {
    console.warn('Failed to prefetch upload config:', error);
  }
};

/**
 * Prefetches recent results data
 * @param {Object} queryClient - TanStack Query client
 * @returns {Promise} Prefetch promise
 */
export const prefetchRecentResults = async (queryClient) => {
  try {
    await queryClient.prefetchQuery({
      queryKey: ['recent-results'],
      queryFn: async () => {
        // Mock implementation - replace with actual API call
        const response = await fetch('/api/results/recent');
        if (!response.ok) throw new Error('Failed to fetch recent results');
        return response.json();
      },
      staleTime: 2 * 60 * 1000, // 2 minutes
      cacheTime: 10 * 60 * 1000 // 10 minutes
    });
  } catch (error) {
    console.warn('Failed to prefetch recent results:', error);
  }
};

/**
 * Prefetches analysis history data
 * @param {Object} queryClient - TanStack Query client
 * @returns {Promise} Prefetch promise
 */
export const prefetchAnalysisHistory = async (queryClient) => {
  try {
    await queryClient.prefetchQuery({
      queryKey: ['analysis-history'],
      queryFn: async () => {
        // Mock implementation - replace with actual API call
        const response = await fetch('/api/analysis/history');
        if (!response.ok) throw new Error('Failed to fetch analysis history');
        return response.json();
      },
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 30 * 60 * 1000 // 30 minutes
    });
  } catch (error) {
    console.warn('Failed to prefetch analysis history:', error);
  }
};

/**
 * Prefetches available reports data
 * @param {Object} queryClient - TanStack Query client
 * @returns {Promise} Prefetch promise
 */
export const prefetchAvailableReports = async (queryClient) => {
  try {
    await queryClient.prefetchQuery({
      queryKey: ['available-reports'],
      queryFn: async () => {
        // Mock implementation - replace with actual API call
        const response = await fetch('/api/reports/available');
        if (!response.ok) throw new Error('Failed to fetch available reports');
        return response.json();
      },
      staleTime: 10 * 60 * 1000, // 10 minutes
      cacheTime: 60 * 60 * 1000 // 1 hour
    });
  } catch (error) {
    console.warn('Failed to prefetch available reports:', error);
  }
};

/**
 * Prefetches analytics data
 * @param {Object} queryClient - TanStack Query client
 * @returns {Promise} Prefetch promise
 */
export const prefetchAnalyticsData = async (queryClient) => {
  try {
    await Promise.all([
      queryClient.prefetchQuery({
        queryKey: ['analytics-data'],
        queryFn: async () => {
          const response = await fetch('/api/analytics/data');
          if (!response.ok) throw new Error('Failed to fetch analytics data');
          return response.json();
        },
        staleTime: 2 * 60 * 1000,
        cacheTime: 15 * 60 * 1000
      }),
      queryClient.prefetchQuery({
        queryKey: ['dashboard-metrics'],
        queryFn: async () => {
          const response = await fetch('/api/dashboard/metrics');
          if (!response.ok) throw new Error('Failed to fetch dashboard metrics');
          return response.json();
        },
        staleTime: 1 * 60 * 1000,
        cacheTime: 10 * 60 * 1000
      })
    ]);
  } catch (error) {
    console.warn('Failed to prefetch analytics data:', error);
  }
};

/**
 * Prefetches settings data
 * @param {Object} queryClient - TanStack Query client
 * @returns {Promise} Prefetch promise
 */
export const prefetchSettingsData = async (queryClient) => {
  try {
    await Promise.all([
      queryClient.prefetchQuery({
        queryKey: ['user-preferences'],
        queryFn: async () => {
          const response = await fetch('/api/settings/preferences');
          if (!response.ok) throw new Error('Failed to fetch user preferences');
          return response.json();
        },
        staleTime: 15 * 60 * 1000,
        cacheTime: 60 * 60 * 1000
      }),
      queryClient.prefetchQuery({
        queryKey: ['system-config'],
        queryFn: async () => {
          const response = await fetch('/api/settings/config');
          if (!response.ok) throw new Error('Failed to fetch system config');
          return response.json();
        },
        staleTime: 30 * 60 * 1000,
        cacheTime: 2 * 60 * 60 * 1000
      })
    ]);
  } catch (error) {
    console.warn('Failed to prefetch settings data:', error);
  }
};

/**
 * Prefetches notification data
 * @param {Object} queryClient - TanStack Query client
 * @returns {Promise} Prefetch promise
 */
export const prefetchNotificationData = async (queryClient) => {
  try {
    await Promise.all([
      queryClient.prefetchQuery({
        queryKey: ['notification-history'],
        queryFn: async () => {
          const response = await fetch('/api/notifications/history');
          if (!response.ok) throw new Error('Failed to fetch notification history');
          return response.json();
        },
        staleTime: 1 * 60 * 1000,
        cacheTime: 5 * 60 * 1000
      }),
      queryClient.prefetchQuery({
        queryKey: ['notification-settings'],
        queryFn: async () => {
          const response = await fetch('/api/notifications/settings');
          if (!response.ok) throw new Error('Failed to fetch notification settings');
          return response.json();
        },
        staleTime: 10 * 60 * 1000,
        cacheTime: 30 * 60 * 1000
      })
    ]);
  } catch (error) {
    console.warn('Failed to prefetch notification data:', error);
  }
};

/**
 * Prefetches system data
 * @param {Object} queryClient - TanStack Query client
 * @returns {Promise} Prefetch promise
 */
export const prefetchSystemData = async (queryClient) => {
  try {
    await Promise.all([
      queryClient.prefetchQuery({
        queryKey: ['system-status'],
        queryFn: async () => {
          const response = await fetch('/api/system/status');
          if (!response.ok) throw new Error('Failed to fetch system status');
          return response.json();
        },
        staleTime: 30 * 1000, // 30 seconds
        cacheTime: 2 * 60 * 1000 // 2 minutes
      }),
      queryClient.prefetchQuery({
        queryKey: ['performance-metrics'],
        queryFn: async () => {
          const response = await fetch('/api/system/performance');
          if (!response.ok) throw new Error('Failed to fetch performance metrics');
          return response.json();
        },
        staleTime: 1 * 60 * 1000,
        cacheTime: 5 * 60 * 1000
      })
    ]);
  } catch (error) {
    console.warn('Failed to prefetch system data:', error);
  }
};

/**
 * Main data prefetching function
 * @param {string} path - Target route path
 * @param {Object} queryClient - TanStack Query client
 * @returns {Promise} Prefetch promise
 */
export const prefetchRouteData = async (path, queryClient) => {
  if (!queryClient) {
    console.warn('Query client not available for prefetching');
    return;
  }

  // Find matching route configuration
  const routeConfig = Object.entries(ROUTE_DATA_CONFIG).find(([routePath]) => 
    path.startsWith(routePath)
  );

  if (!routeConfig) {
    console.log(`No prefetch configuration found for path: ${path}`);
    return;
  }

  const [routePath, config] = routeConfig;
  const prefetchFn = window[config.prefetchFn] || eval(config.prefetchFn);

  if (typeof prefetchFn !== 'function') {
    console.warn(`Prefetch function ${config.prefetchFn} not found`);
    return;
  }

  try {
    console.log(`Prefetching data for route: ${routePath}`);
    await prefetchFn(queryClient);
    console.log(`Successfully prefetched data for route: ${routePath}`);
  } catch (error) {
    console.error(`Failed to prefetch data for route ${routePath}:`, error);
  }
};

/**
 * Enhanced breadcrumb generation with navigation context
 * @param {string} pathname - Current pathname
 * @param {Array} navigationHistory - Navigation history
 * @returns {Array} Enhanced breadcrumb items
 */
export const generateNavigationBreadcrumbs = (pathname, navigationHistory = []) => {
  const breadcrumbs = generateEnhancedBreadcrumbs(pathname);
  
  // Add navigation context to breadcrumbs
  return breadcrumbs.map(breadcrumb => {
    const historyEntry = navigationHistory.find(entry => entry.path === breadcrumb.path);
    
    return {
      ...breadcrumb,
      navigationContext: {
        lastVisited: historyEntry?.timestamp,
        visitCount: navigationHistory.filter(entry => entry.path === breadcrumb.path).length,
        isFrequent: navigationHistory.filter(entry => entry.path === breadcrumb.path).length > 3
      }
    };
  });
};

/**
 * Validates if a path is navigable
 * @param {string} path - Path to validate
 * @returns {boolean} True if path is valid
 */
export const isValidNavigationPath = (path) => {
  if (!path || typeof path !== 'string') {
    return false;
  }
  
  // Basic validation - should start with / and not contain invalid characters
  return /^\/[a-zA-Z0-9\-_\/]*$/.test(path);
};

/**
 * Gets the parent path of a given path
 * @param {string} path - Current path
 * @returns {string} Parent path
 */
export const getParentNavigationPath = (path) => {
  if (path === '/' || path === '') {
    return '/';
  }
  
  const segments = path.split('/').filter(segment => segment.length > 0);
  if (segments.length <= 1) {
    return '/';
  }
  
  return '/' + segments.slice(0, -1).join('/');
};

/**
 * Gets navigation suggestions based on history and current path
 * @param {Array} navigationHistory - Navigation history
 * @param {string} currentPath - Current path
 * @param {number} limit - Maximum number of suggestions
 * @returns {Array} Navigation suggestions
 */
export const getNavigationSuggestions = (navigationHistory, currentPath, limit = 5) => {
  // Get frequent paths (visited more than once)
  const frequentPaths = navigationHistory
    .filter(entry => entry.path !== currentPath)
    .reduce((acc, entry) => {
      const existing = acc.find(item => item.path === entry.path);
      if (existing) {
        existing.count++;
        existing.lastVisited = Math.max(existing.lastVisited, entry.timestamp);
      } else {
        acc.push({
          path: entry.path,
          label: entry.label,
          count: 1,
          lastVisited: entry.timestamp
        });
      }
      return acc;
    }, [])
    .filter(item => item.count > 1)
    .sort((a, b) => b.count - a.count || b.lastVisited - a.lastVisited)
    .slice(0, limit);

  return frequentPaths;
};

/**
 * Navigation performance tracking
 */
export const NavigationPerformance = {
  startTiming: (path) => {
    performance.mark(`navigation-start-${path}`);
  },
  
  endTiming: (path) => {
    performance.mark(`navigation-end-${path}`);
    performance.measure(
      `navigation-${path}`,
      `navigation-start-${path}`,
      `navigation-end-${path}`
    );
  },
  
  getTiming: (path) => {
    const measures = performance.getEntriesByName(`navigation-${path}`, 'measure');
    return measures.length > 0 ? measures[measures.length - 1].duration : null;
  }
};
