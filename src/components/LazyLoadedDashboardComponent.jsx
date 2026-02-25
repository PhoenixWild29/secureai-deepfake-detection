/**
 * Lazy Loaded Dashboard Component
 * Demonstrates lazy loading pattern for dashboard components with loading indicators
 */

import React, { Suspense, lazy, useState, useEffect, useCallback } from 'react';
import { useInView } from 'react-intersection-observer';
import { measureComponentRender } from '@/utils/performanceMonitor';
import styles from './LazyLoadedDashboardComponent.module.css';

// Lazy-loaded components
const AnalysisHistoryWidget = lazy(() => import('../widgets/AnalysisHistoryWidget'));
const PerformanceMetricsWidget = lazy(() => import('../widgets/PerformanceMetricsWidget'));
const NotificationListWidget = lazy(() => import('../widgets/NotificationListWidget'));

// Component props
interface LazyLoadedDashboardComponentProps {
  componentType: 'analysis-history' | 'performance-metrics' | 'notification-list';
  className?: string;
  height?: number;
  enablePreloading?: boolean;
  enableErrorBoundary?: boolean;
  onLoadStart?: () => void;
  onLoadComplete?: () => void;
  onLoadError?: (error: Error) => void;
}

// Loading component
const LoadingComponent: React.FC<{ message?: string }> = ({ message = 'Loading...' }) => (
  <div className={styles.loadingContainer}>
    <div className={styles.loadingSpinner} />
    <p className={styles.loadingText}>{message}</p>
  </div>
);

// Error boundary component
class ErrorBoundary extends React.Component<
  { children: React.ReactNode; onError?: (error: Error) => void },
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
    console.error('LazyLoadedDashboardComponent error:', error, errorInfo);
    this.props.onError?.(error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className={styles.errorContainer}>
          <div className={styles.errorIcon}>⚠️</div>
          <h3 className={styles.errorTitle}>Component Failed to Load</h3>
          <p className={styles.errorMessage}>
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: undefined })}
            className={styles.retryButton}
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

// Main lazy loaded component
export const LazyLoadedDashboardComponent: React.FC<LazyLoadedDashboardComponentProps> = ({
  componentType,
  className = '',
  height = 400,
  enablePreloading = true,
  enableErrorBoundary = true,
  onLoadStart,
  onLoadComplete,
  onLoadError,
}) => {
  const renderTimer = React.useRef<{ end: () => number } | null>(null);
  
  // State
  const [isLoaded, setIsLoaded] = useState(false);
  const [loadError, setLoadError] = useState<Error | null>(null);
  const [isPreloaded, setIsPreloaded] = useState(false);

  // Intersection observer for lazy loading
  const { ref, inView } = useInView({
    threshold: 0.1,
    triggerOnce: true,
    rootMargin: '50px',
  });

  // Performance monitoring
  useEffect(() => {
    renderTimer.current = measureComponentRender('LazyLoadedDashboardComponent');
    
    return () => {
      if (renderTimer.current) {
        renderTimer.current.end();
      }
    };
  }, []);

  // Preload component when it comes into view
  useEffect(() => {
    if (inView && enablePreloading && !isPreloaded) {
      setIsPreloaded(true);
      onLoadStart?.();
    }
  }, [inView, enablePreloading, isPreloaded, onLoadStart]);

  // Handle load completion
  const handleLoadComplete = useCallback(() => {
    setIsLoaded(true);
    onLoadComplete?.();
  }, [onLoadComplete]);

  // Handle load error
  const handleLoadError = useCallback((error: Error) => {
    setLoadError(error);
    onLoadError?.(error);
  }, [onLoadError]);

  // Get component based on type
  const getComponent = () => {
    const commonProps = {
      height,
      className: styles.component,
    };

    switch (componentType) {
      case 'analysis-history':
        return <AnalysisHistoryWidget {...commonProps} />;
      case 'performance-metrics':
        return <PerformanceMetricsWidget {...commonProps} />;
      case 'notification-list':
        return <NotificationListWidget {...commonProps} />;
      default:
        throw new Error(`Unknown component type: ${componentType}`);
    }
  };

  // Get loading message based on component type
  const getLoadingMessage = () => {
    switch (componentType) {
      case 'analysis-history':
        return 'Loading analysis history...';
      case 'performance-metrics':
        return 'Loading performance metrics...';
      case 'notification-list':
        return 'Loading notifications...';
      default:
        return 'Loading component...';
    }
  };

  // Render placeholder when not in view
  if (!inView) {
    return (
      <div ref={ref} className={`${styles.placeholder} ${className}`}>
        <div className={styles.placeholderContent}>
          <div className={styles.placeholderIcon}>📊</div>
          <p className={styles.placeholderText}>
            {componentType.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase())}
          </p>
        </div>
      </div>
    );
  }

  // Render error state
  if (loadError) {
    return (
      <div className={`${styles.errorContainer} ${className}`}>
        <div className={styles.errorIcon}>❌</div>
        <h3 className={styles.errorTitle}>Failed to Load</h3>
        <p className={styles.errorMessage}>{loadError.message}</p>
        <button
          onClick={() => {
            setLoadError(null);
            setIsPreloaded(false);
          }}
          className={styles.retryButton}
        >
          Retry Loading
        </button>
      </div>
    );
  }

  // Render component with lazy loading
  const ComponentWrapper = () => {
    if (enableErrorBoundary) {
      return (
        <ErrorBoundary onError={handleLoadError}>
          <Suspense fallback={<LoadingComponent message={getLoadingMessage()} />}>
            {getComponent()}
          </Suspense>
        </ErrorBoundary>
      );
    }

    return (
      <Suspense fallback={<LoadingComponent message={getLoadingMessage()} />}>
        {getComponent()}
      </Suspense>
    );
  };

  return (
    <div ref={ref} className={`${styles.container} ${className}`}>
      <ComponentWrapper />
    </div>
  );
};

// Higher-order component for lazy loading
export const withLazyLoading = <P extends object>(
  Component: React.ComponentType<P>,
  options: {
    fallback?: React.ComponentType;
    errorBoundary?: boolean;
    preload?: boolean;
  } = {}
) => {
  const LazyComponent = React.lazy(() => Promise.resolve({ default: Component }));
  
  return React.forwardRef<any, P>((props, ref) => {
    const { ref: inViewRef, inView } = useInView({
      threshold: 0.1,
      triggerOnce: true,
      rootMargin: '50px',
    });

    if (!inView) {
      return (
        <div ref={inViewRef} className={styles.placeholder}>
          <div className={styles.placeholderContent}>
            <div className={styles.placeholderIcon}>⏳</div>
            <p className={styles.placeholderText}>Loading...</p>
          </div>
        </div>
      );
    }

    const FallbackComponent = options.fallback || LoadingComponent;

    if (options.errorBoundary) {
      return (
        <ErrorBoundary>
          <Suspense fallback={<FallbackComponent />}>
            <Component {...props} ref={ref} />
          </Suspense>
        </ErrorBoundary>
      );
    }

    return (
      <Suspense fallback={<FallbackComponent />}>
        <Component {...props} ref={ref} />
      </Suspense>
    );
  });
};

// Hook for lazy loading
export const useLazyLoading = (options: {
  threshold?: number;
  rootMargin?: string;
  triggerOnce?: boolean;
} = {}) => {
  const { ref, inView } = useInView({
    threshold: options.threshold || 0.1,
    rootMargin: options.rootMargin || '50px',
    triggerOnce: options.triggerOnce !== false,
  });

  return { ref, inView };
};

// Utility for preloading components
export const preloadComponent = (componentImport: () => Promise<any>) => {
  return componentImport().catch(error => {
    console.warn('Failed to preload component:', error);
  });
};

// Utility for batch preloading
export const preloadComponents = (componentImports: (() => Promise<any>)[]) => {
  return Promise.allSettled(
    componentImports.map(importFn => preloadComponent(importFn))
  );
};

export default LazyLoadedDashboardComponent;
