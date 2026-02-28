/**
 * useNavigation Hook
 * 
 * Custom React hook for comprehensive navigation state management,
 * including routing integration, breadcrumb generation, data prefetching,
 * and navigation history tracking.
 */

import { useState, useEffect, useCallback, useRef, createContext, useContext } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  createNavigationEntry,
  addToNavigationHistory,
  clearNavigationHistory,
  generateNavigationBreadcrumbs,
  prefetchRouteData,
  isValidNavigationPath,
  getParentNavigationPath,
  getNavigationSuggestions,
  NavigationPerformance,
  NAVIGATION_HISTORY_LIMIT
} from '../utils/navigationUtils';

/**
 * Custom hook for navigation state management
 * @param {Object} options - Configuration options
 * @returns {Object} Navigation state and functions
 */
export const useNavigation = (options = {}) => {
  const {
    enableDataPrefetching = true,
    enableHistoryTracking = true,
    enablePerformanceTracking = true,
    maxHistoryItems = NAVIGATION_HISTORY_LIMIT,
    prefetchDelay = 100 // ms delay before prefetching
  } = options;

  // React Router hooks
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Navigation state
  const [currentPath, setCurrentPath] = useState(location.pathname);
  const [breadcrumbs, setBreadcrumbs] = useState([]);
  const [navigationHistory, setNavigationHistory] = useState([]);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);
  const [navigationError, setNavigationError] = useState(null);

  // Refs for tracking
  const prefetchTimeoutRef = useRef(null);
  const lastNavigationRef = useRef(null);

  /**
   * Updates breadcrumbs when path changes
   */
  const updateBreadcrumbs = useCallback((path, history = navigationHistory) => {
    try {
      const newBreadcrumbs = generateNavigationBreadcrumbs(path, history);
      setBreadcrumbs(newBreadcrumbs);
    } catch (error) {
      console.error('Failed to update breadcrumbs:', error);
      setNavigationError(error);
    }
  }, [navigationHistory]);

  /**
   * Adds entry to navigation history
   */
  const addToHistory = useCallback((path, label) => {
    if (!enableHistoryTracking) return;

    try {
      const entry = createNavigationEntry(path, label);
      setNavigationHistory(prev => addToNavigationHistory(prev, entry));
    } catch (error) {
      console.error('Failed to add to navigation history:', error);
    }
  }, [enableHistoryTracking]);

  /**
   * Handles navigation with data prefetching
   */
  const handleNavigate = useCallback(async (path, options = {}) => {
    const {
      replace = false,
      state = null,
      prefetch = enableDataPrefetching,
      addToHistory: addToNavHistory = true
    } = options;

    // Validate path
    if (!isValidNavigationPath(path)) {
      const error = new Error(`Invalid navigation path: ${path}`);
      setNavigationError(error);
      console.error(error);
      return;
    }

    // Don't navigate if already on the same path
    if (path === currentPath) {
      console.log('Already on target path:', path);
      return;
    }

    setIsNavigating(true);
    setNavigationError(null);

    try {
      // Start performance tracking
      if (enablePerformanceTracking) {
        NavigationPerformance.startTiming(path);
      }

      // Clear any existing prefetch timeout
      if (prefetchTimeoutRef.current) {
        clearTimeout(prefetchTimeoutRef.current);
      }

      // Prefetch data if enabled
      if (prefetch && queryClient) {
        prefetchTimeoutRef.current = setTimeout(async () => {
          try {
            await prefetchRouteData(path, queryClient);
          } catch (error) {
            console.warn('Data prefetching failed:', error);
          }
        }, prefetchDelay);
      }

      // Add to navigation history
      if (addToNavHistory) {
        const pathSegments = path.split('/').filter(segment => segment.length > 0);
        const label = pathSegments.length > 0 
          ? pathSegments[pathSegments.length - 1].replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
          : 'Home';
        
        addToHistory(path, label);
      }

      // Perform navigation
      if (replace) {
        navigate(path, { replace: true, state });
      } else {
        navigate(path, { state });
      }

      // Update current path
      setCurrentPath(path);
      lastNavigationRef.current = {
        path,
        timestamp: Date.now(),
        success: true
      };

    } catch (error) {
      console.error('Navigation failed:', error);
      setNavigationError(error);
      lastNavigationRef.current = {
        path,
        timestamp: Date.now(),
        success: false,
        error
      };
    } finally {
      setIsNavigating(false);
    }
  }, [
    currentPath,
    enableDataPrefetching,
    enablePerformanceTracking,
    prefetchDelay,
    queryClient,
    navigate,
    addToHistory
  ]);

  /**
   * Toggles sidebar collapse state
   */
  const toggleCollapse = useCallback(() => {
    setIsCollapsed(prev => !prev);
  }, []);

  /**
   * Toggles mobile menu open state
   */
  const toggleMobileMenu = useCallback(() => {
    setIsMobileMenuOpen(prev => !prev);
  }, []);

  /**
   * Closes mobile menu
   */
  const closeMobileMenu = useCallback(() => {
    setIsMobileMenuOpen(false);
  }, []);

  /**
   * Navigates to parent path
   */
  const navigateToParent = useCallback(() => {
    const parentPath = getParentNavigationPath(currentPath);
    if (parentPath !== currentPath) {
      handleNavigate(parentPath);
    }
  }, [currentPath, handleNavigate]);

  /**
   * Navigates back in history
   */
  const navigateBack = useCallback(() => {
    if (navigationHistory.length > 1) {
      const previousEntry = navigationHistory[navigationHistory.length - 2];
      handleNavigate(previousEntry.path, { replace: true });
    } else {
      // Fallback to browser back
      window.history.back();
    }
  }, [navigationHistory, handleNavigate]);

  /**
   * Clears navigation history
   */
  const clearHistory = useCallback(() => {
    setNavigationHistory(clearNavigationHistory());
  }, []);

  /**
   * Gets navigation suggestions
   */
  const getSuggestions = useCallback((limit = 5) => {
    return getNavigationSuggestions(navigationHistory, currentPath, limit);
  }, [navigationHistory, currentPath]);

  /**
   * Gets performance metrics for navigation
   */
  const getPerformanceMetrics = useCallback((path) => {
    if (!enablePerformanceTracking) return null;
    return NavigationPerformance.getTiming(path);
  }, [enablePerformanceTracking]);

  /**
   * Effect: Update state when location changes
   */
  useEffect(() => {
    const newPath = location.pathname;
    
    if (newPath !== currentPath) {
      setCurrentPath(newPath);
      
      // End performance tracking for previous navigation
      if (enablePerformanceTracking && lastNavigationRef.current?.success) {
        NavigationPerformance.endTiming(lastNavigationRef.current.path);
      }
    }
  }, [location.pathname, currentPath, enablePerformanceTracking]);

  /**
   * Effect: Update breadcrumbs when path or history changes
   */
  useEffect(() => {
    updateBreadcrumbs(currentPath, navigationHistory);
  }, [currentPath, navigationHistory, updateBreadcrumbs]);

  /**
   * Effect: Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      if (prefetchTimeoutRef.current) {
        clearTimeout(prefetchTimeoutRef.current);
      }
    };
  }, []);

  /**
   * Effect: Handle mobile menu state changes
   */
  useEffect(() => {
    // Close mobile menu when navigating
    if (isMobileMenuOpen) {
      const timer = setTimeout(() => {
        setIsMobileMenuOpen(false);
      }, 300); // Close after navigation animation

      return () => clearTimeout(timer);
    }
  }, [currentPath, isMobileMenuOpen]);

  // Return navigation state and functions
  return {
    // State
    currentPath,
    breadcrumbs,
    navigationHistory,
    isCollapsed,
    isMobileMenuOpen,
    isNavigating,
    navigationError,
    
    // Navigation functions
    handleNavigate,
    navigateToParent,
    navigateBack,
    
    // UI state functions
    toggleCollapse,
    toggleMobileMenu,
    closeMobileMenu,
    
    // History functions
    clearHistory,
    getSuggestions,
    
    // Performance functions
    getPerformanceMetrics,
    
    // Utility functions
    isValidPath: isValidNavigationPath,
    getParentPath: getParentNavigationPath,
    
    // Configuration
    config: {
      enableDataPrefetching,
      enableHistoryTracking,
      enablePerformanceTracking,
      maxHistoryItems,
      prefetchDelay
    }
  };
};

/**
 * Hook for navigation context provider
 * @param {Object} children - React children
 * @param {Object} options - Navigation options
 * @returns {JSX.Element} Navigation context provider
 */
export const NavigationProvider = ({ children, options = {} }) => {
  const navigation = useNavigation(options);
  
  return (
    <NavigationContext.Provider value={navigation}>
      {children}
    </NavigationContext.Provider>
  );
};

/**
 * Hook to use navigation context
 * @returns {Object} Navigation context value
 */
export const useNavigationContext = () => {
  const context = useContext(NavigationContext);
  if (!context) {
    throw new Error('useNavigationContext must be used within a NavigationProvider');
  }
  return context;
};

// Create navigation context
const NavigationContext = createContext(null);

export default useNavigation;
