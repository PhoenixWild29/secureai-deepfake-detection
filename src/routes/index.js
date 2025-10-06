/**
 * Route-based Lazy Loading
 * Implements lazy loading for dashboard routes and components using dynamic imports
 */

import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { measureComponentRender } from '@/utils/performanceMonitor';

// Loading component for routes
const RouteLoadingComponent: React.FC<{ routeName?: string }> = ({ routeName = 'page' }) => (
  <div className="route-loading-container">
    <div className="route-loading-spinner" />
    <p className="route-loading-text">Loading {routeName}...</p>
  </div>
);

// Error boundary for routes
class RouteErrorBoundary extends React.Component<
  { children: React.ReactNode; routeName?: string },
  { hasError: boolean; error?: Error }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error(`Route error in ${this.props.routeName}:`, error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="route-error-container">
          <div className="route-error-icon">⚠️</div>
          <h2 className="route-error-title">Page Failed to Load</h2>
          <p className="route-error-message">
            {this.state.error?.message || 'An unexpected error occurred while loading this page'}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: undefined })}
            className="route-retry-button"
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

// Lazy-loaded route components
const DashboardOverview = lazy(() => 
  import('../pages/DashboardOverview').then(module => ({
    default: module.DashboardOverview
  }))
);

const AnalyticsDashboard = lazy(() => 
  import('../components/AnalyticsDashboard/AnalyticsDashboard').then(module => ({
    default: module.default
  }))
);

const AnalysisHistory = lazy(() => 
  import('../pages/AnalysisHistory').then(module => ({
    default: module.AnalysisHistory
  }))
);

const PerformanceMetrics = lazy(() => 
  import('../pages/PerformanceMetrics').then(module => ({
    default: module.PerformanceMetrics
  }))
);

const NotificationCenter = lazy(() => 
  import('../components/NotificationCenter/NotificationCenter').then(module => ({
    default: module.default
  }))
);

const ProgressTracker = lazy(() => 
  import('../components/ComprehensiveProgressTracker').then(module => ({
    default: module.default
  }))
);

const ProcessingStageVisualization = lazy(() => 
  import('../components/ProcessingStageVisualization').then(module => ({
    default: module.default
  }))
);

const ErrorRecoveryInterface = lazy(() => 
  import('../components/ErrorRecoveryInterface').then(module => ({
    default: module.default
  }))
);

const UserSettings = lazy(() => 
  import('../pages/UserSettings').then(module => ({
    default: module.UserSettings
  }))
);

const SystemStatus = lazy(() => 
  import('../pages/SystemStatus').then(module => ({
    default: module.SystemStatus
  }))
);

// Route wrapper component
const RouteWrapper: React.FC<{
  component: React.ComponentType;
  routeName: string;
}> = ({ component: Component, routeName }) => {
  const renderTimer = React.useRef<{ end: () => number } | null>(null);

  React.useEffect(() => {
    renderTimer.current = measureComponentRender(`Route-${routeName}`);
    
    return () => {
      if (renderTimer.current) {
        renderTimer.current.end();
      }
    };
  }, [routeName]);

  return (
    <RouteErrorBoundary routeName={routeName}>
      <Suspense fallback={<RouteLoadingComponent routeName={routeName} />}>
        <Component />
      </Suspense>
    </RouteErrorBoundary>
  );
};

// Main dashboard routes component
export const DashboardRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Dashboard Overview */}
      <Route
        path="/"
        element={
          <RouteWrapper
            component={DashboardOverview}
            routeName="Dashboard Overview"
          />
        }
      />
      
      {/* Analytics Dashboard */}
      <Route
        path="/analytics"
        element={
          <RouteWrapper
            component={AnalyticsDashboard}
            routeName="Analytics Dashboard"
          />
        }
      />
      
      {/* Analysis History */}
      <Route
        path="/history"
        element={
          <RouteWrapper
            component={AnalysisHistory}
            routeName="Analysis History"
          />
        }
      />
      
      {/* Performance Metrics */}
      <Route
        path="/metrics"
        element={
          <RouteWrapper
            component={PerformanceMetrics}
            routeName="Performance Metrics"
          />
        }
      />
      
      {/* Notification Center */}
      <Route
        path="/notifications"
        element={
          <RouteWrapper
            component={NotificationCenter}
            routeName="Notification Center"
          />
        }
      />
      
      {/* Progress Tracker */}
      <Route
        path="/progress"
        element={
          <RouteWrapper
            component={ProgressTracker}
            routeName="Progress Tracker"
          />
        }
      />
      
      {/* Processing Stage Visualization */}
      <Route
        path="/processing"
        element={
          <RouteWrapper
            component={ProcessingStageVisualization}
            routeName="Processing Visualization"
          />
        }
      />
      
      {/* Error Recovery Interface */}
      <Route
        path="/error-recovery"
        element={
          <RouteWrapper
            component={ErrorRecoveryInterface}
            routeName="Error Recovery"
          />
        }
      />
      
      {/* User Settings */}
      <Route
        path="/settings"
        element={
          <RouteWrapper
            component={UserSettings}
            routeName="User Settings"
          />
        }
      />
      
      {/* System Status */}
      <Route
        path="/system"
        element={
          <RouteWrapper
            component={SystemStatus}
            routeName="System Status"
          />
        }
      />
      
      {/* Catch-all route */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

// Utility function to preload routes
export const preloadRoute = (routePath: string): Promise<any> => {
  const routeMap: Record<string, () => Promise<any>> = {
    '/': () => import('../pages/DashboardOverview'),
    '/analytics': () => import('../components/AnalyticsDashboard/AnalyticsDashboard'),
    '/history': () => import('../pages/AnalysisHistory'),
    '/metrics': () => import('../pages/PerformanceMetrics'),
    '/notifications': () => import('../components/NotificationCenter/NotificationCenter'),
    '/progress': () => import('../components/ComprehensiveProgressTracker'),
    '/processing': () => import('../components/ProcessingStageVisualization'),
    '/error-recovery': () => import('../components/ErrorRecoveryInterface'),
    '/settings': () => import('../pages/UserSettings'),
    '/system': () => import('../pages/SystemStatus'),
  };

  const importFn = routeMap[routePath];
  if (!importFn) {
    return Promise.reject(new Error(`Unknown route: ${routePath}`));
  }

  return importFn().catch(error => {
    console.warn(`Failed to preload route ${routePath}:`, error);
    throw error;
  });
};

// Utility function to preload multiple routes
export const preloadRoutes = (routePaths: string[]): Promise<any[]> => {
  return Promise.allSettled(
    routePaths.map(routePath => preloadRoute(routePath))
  );
};

// Hook for route preloading
export const useRoutePreloading = () => {
  const [preloadedRoutes, setPreloadedRoutes] = React.useState<Set<string>>(new Set());
  const [isPreloading, setIsPreloading] = React.useState(false);

  const preloadRoute = React.useCallback(async (routePath: string) => {
    if (preloadedRoutes.has(routePath)) {
      return;
    }

    setIsPreloading(true);
    try {
      await preloadRoute(routePath);
      setPreloadedRoutes(prev => new Set(prev).add(routePath));
    } catch (error) {
      console.warn(`Failed to preload route ${routePath}:`, error);
    } finally {
      setIsPreloading(false);
    }
  }, [preloadedRoutes]);

  const preloadRoutes = React.useCallback(async (routePaths: string[]) => {
    setIsPreloading(true);
    try {
      await preloadRoutes(routePaths);
      setPreloadedRoutes(prev => {
        const newSet = new Set(prev);
        routePaths.forEach(route => newSet.add(route));
        return newSet;
      });
    } catch (error) {
      console.warn('Failed to preload routes:', error);
    } finally {
      setIsPreloading(false);
    }
  }, []);

  return {
    preloadedRoutes,
    isPreloading,
    preloadRoute,
    preloadRoutes,
  };
};

// Route-based code splitting configuration
export const routeChunks = {
  // Core dashboard routes (loaded immediately)
  core: ['/'],
  
  // Analytics routes (preloaded on dashboard load)
  analytics: ['/analytics', '/metrics'],
  
  // Analysis routes (preloaded when user starts analysis)
  analysis: ['/history', '/progress', '/processing'],
  
  // System routes (preloaded on admin access)
  system: ['/notifications', '/error-recovery', '/system'],
  
  // User routes (preloaded on user interaction)
  user: ['/settings'],
};

// Auto-preload routes based on user behavior
export const useAutoPreloading = () => {
  const { preloadRoutes } = useRoutePreloading();

  React.useEffect(() => {
    // Preload analytics routes after dashboard loads
    const timer = setTimeout(() => {
      preloadRoutes(routeChunks.analytics);
    }, 2000);

    return () => clearTimeout(timer);
  }, [preloadRoutes]);

  // Preload analysis routes when user hovers over analysis menu
  const handleAnalysisHover = React.useCallback(() => {
    preloadRoutes(routeChunks.analysis);
  }, [preloadRoutes]);

  // Preload system routes when user hovers over admin menu
  const handleSystemHover = React.useCallback(() => {
    preloadRoutes(routeChunks.system);
  }, [preloadRoutes]);

  return {
    handleAnalysisHover,
    handleSystemHover,
  };
};

export default DashboardRoutes;
