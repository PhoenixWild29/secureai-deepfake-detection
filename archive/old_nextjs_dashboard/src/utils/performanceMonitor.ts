/**
 * Performance Monitoring Utilities
 * Track and report key performance metrics including TTI, LCP, CLS, and custom metrics
 */

import { getCLS, getFID, getFCP, getLCP, getTTFB, getINP } from 'web-vitals';

// Performance metric types
export interface PerformanceMetric {
  name: string;
  value: number;
  delta: number;
  id: string;
  navigationType?: string;
  rating: 'good' | 'needs-improvement' | 'poor';
  timestamp: number;
}

export interface PerformanceReport {
  metrics: PerformanceMetric[];
  userAgent: string;
  connection: string;
  timestamp: number;
  sessionId: string;
}

export interface PerformanceThresholds {
  LCP: { good: number; poor: number };
  FID: { good: number; poor: number };
  CLS: { good: number; poor: number };
  FCP: { good: number; poor: number };
  TTFB: { good: number; poor: number };
  INP: { good: number; poor: number };
}

// Default performance thresholds (in milliseconds)
const DEFAULT_THRESHOLDS: PerformanceThresholds = {
  LCP: { good: 2500, poor: 4000 },
  FID: { good: 100, poor: 300 },
  CLS: { good: 0.1, poor: 0.25 },
  FCP: { good: 1800, poor: 3000 },
  TTFB: { good: 800, poor: 1800 },
  INP: { good: 200, poor: 500 },
};

// Performance monitoring class
export class PerformanceMonitor {
  private metrics: PerformanceMetric[] = [];
  private sessionId: string;
  private thresholds: PerformanceThresholds;
  private isEnabled: boolean = true;
  private reportEndpoint?: string;
  private customMetrics: Map<string, number> = new Map();

  constructor(config: {
    thresholds?: Partial<PerformanceThresholds>;
    reportEndpoint?: string;
    enabled?: boolean;
  } = {}) {
    this.sessionId = this.generateSessionId();
    this.thresholds = { ...DEFAULT_THRESHOLDS, ...config.thresholds };
    this.reportEndpoint = config.reportEndpoint;
    this.isEnabled = config.enabled !== false;

    if (this.isEnabled && typeof window !== 'undefined') {
      this.initializeMonitoring();
    }
  }

  /**
   * Initialize performance monitoring
   */
  private initializeMonitoring(): void {
    // Monitor Core Web Vitals
    getCLS(this.handleMetric.bind(this));
    getFID(this.handleMetric.bind(this));
    getFCP(this.handleMetric.bind(this));
    getLCP(this.handleMetric.bind(this));
    getTTFB(this.handleMetric.bind(this));
    getINP(this.handleMetric.bind(this));

    // Monitor custom metrics
    this.monitorCustomMetrics();

    // Monitor resource loading
    this.monitorResourceLoading();

    // Monitor user interactions
    this.monitorUserInteractions();

    // Report metrics on page unload
    window.addEventListener('beforeunload', () => {
      this.reportMetrics();
    });

    // Report metrics periodically
    setInterval(() => {
      this.reportMetrics();
    }, 30000); // Every 30 seconds
  }

  /**
   * Handle performance metric
   */
  private handleMetric(metric: any): void {
    const performanceMetric: PerformanceMetric = {
      name: metric.name,
      value: metric.value,
      delta: metric.delta,
      id: metric.id,
      navigationType: metric.navigationType,
      rating: this.getRating(metric.name, metric.value),
      timestamp: Date.now(),
    };

    this.metrics.push(performanceMetric);
    this.customMetrics.set(metric.name, metric.value);

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`Performance Metric: ${metric.name}`, performanceMetric);
    }

    // Send critical metrics immediately
    if (this.isCriticalMetric(metric.name)) {
      this.sendMetric(performanceMetric);
    }
  }

  /**
   * Get performance rating based on thresholds
   */
  private getRating(metricName: string, value: number): 'good' | 'needs-improvement' | 'poor' {
    const threshold = this.thresholds[metricName as keyof PerformanceThresholds];
    if (!threshold) return 'good';

    if (value <= threshold.good) return 'good';
    if (value <= threshold.poor) return 'needs-improvement';
    return 'poor';
  }

  /**
   * Check if metric is critical and should be sent immediately
   */
  private isCriticalMetric(metricName: string): boolean {
    const criticalMetrics = ['LCP', 'FID', 'CLS', 'INP'];
    return criticalMetrics.includes(metricName);
  }

  /**
   * Monitor custom performance metrics
   */
  private monitorCustomMetrics(): void {
    // Time to Interactive (TTI) approximation
    this.measureTTI();

    // First Paint (FP)
    this.measureFirstPaint();

    // Memory usage
    this.measureMemoryUsage();

    // Network information
    this.measureNetworkInfo();

    // Device information
    this.measureDeviceInfo();
  }

  /**
   * Measure Time to Interactive (approximation)
   */
  private measureTTI(): void {
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const longTasks = entries.filter(entry => entry.duration > 50);
        
        if (longTasks.length === 0) {
          const navigationEntry = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
          const tti = navigationEntry.loadEventEnd - navigationEntry.fetchStart;
          
          this.customMetrics.set('TTI', tti);
          this.handleMetric({
            name: 'TTI',
            value: tti,
            delta: tti,
            id: 'tti-' + Date.now(),
          });
        }
      });

      observer.observe({ entryTypes: ['longtask'] });
    }
  }

  /**
   * Measure First Paint
   */
  private measureFirstPaint(): void {
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const paintEntries = entries.filter(entry => entry.name === 'first-paint');
        
        if (paintEntries.length > 0) {
          const fp = paintEntries[0].startTime;
          this.customMetrics.set('FP', fp);
          this.handleMetric({
            name: 'FP',
            value: fp,
            delta: fp,
            id: 'fp-' + Date.now(),
          });
        }
      });

      observer.observe({ entryTypes: ['paint'] });
    }
  }

  /**
   * Measure memory usage
   */
  private measureMemoryUsage(): void {
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      const memoryUsage = {
        used: memory.usedJSHeapSize,
        total: memory.totalJSHeapSize,
        limit: memory.jsHeapSizeLimit,
      };

      this.customMetrics.set('MemoryUsed', memoryUsage.used);
      this.customMetrics.set('MemoryTotal', memoryUsage.total);
      this.customMetrics.set('MemoryLimit', memoryUsage.limit);
    }
  }

  /**
   * Measure network information
   */
  private measureNetworkInfo(): void {
    if ('connection' in navigator) {
      const connection = (navigator as any).connection;
      const networkInfo = {
        effectiveType: connection.effectiveType,
        downlink: connection.downlink,
        rtt: connection.rtt,
        saveData: connection.saveData,
      };

      this.customMetrics.set('NetworkType', networkInfo.effectiveType);
      this.customMetrics.set('NetworkDownlink', networkInfo.downlink);
      this.customMetrics.set('NetworkRTT', networkInfo.rtt);
    }
  }

  /**
   * Measure device information
   */
  private measureDeviceInfo(): void {
    const deviceInfo = {
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      language: navigator.language,
      screenWidth: screen.width,
      screenHeight: screen.height,
      devicePixelRatio: window.devicePixelRatio,
      touchSupport: 'ontouchstart' in window,
    };

    this.customMetrics.set('ScreenWidth', deviceInfo.screenWidth);
    this.customMetrics.set('ScreenHeight', deviceInfo.screenHeight);
    this.customMetrics.set('DevicePixelRatio', deviceInfo.devicePixelRatio);
  }

  /**
   * Monitor resource loading performance
   */
  private monitorResourceLoading(): void {
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        
        entries.forEach(entry => {
          const resourceMetric = {
            name: 'ResourceLoad',
            value: entry.duration,
            delta: entry.duration,
            id: 'resource-' + entry.name,
            resourceType: entry.initiatorType,
            resourceSize: entry.transferSize,
          };

          this.handleMetric(resourceMetric);
        });
      });

      observer.observe({ entryTypes: ['resource'] });
    }
  }

  /**
   * Monitor user interactions
   */
  private monitorUserInteractions(): void {
    let interactionCount = 0;
    let totalInteractionTime = 0;

    const trackInteraction = (event: Event) => {
      interactionCount++;
      const startTime = performance.now();
      
      requestAnimationFrame(() => {
        const endTime = performance.now();
        const interactionTime = endTime - startTime;
        totalInteractionTime += interactionTime;

        this.handleMetric({
          name: 'UserInteraction',
          value: interactionTime,
          delta: interactionTime,
          id: 'interaction-' + Date.now(),
          interactionType: event.type,
        });
      });
    };

    // Track various user interactions
    ['click', 'keydown', 'scroll', 'touchstart'].forEach(eventType => {
      document.addEventListener(eventType, trackInteraction, { passive: true });
    });
  }

  /**
   * Measure custom performance metric
   */
  public measureCustomMetric(name: string, startTime: number): number {
    const endTime = performance.now();
    const duration = endTime - startTime;

    this.handleMetric({
      name: `Custom_${name}`,
      value: duration,
      delta: duration,
      id: `custom-${name}-${Date.now()}`,
    });

    return duration;
  }

  /**
   * Start performance measurement
   */
  public startMeasurement(name: string): () => number {
    const startTime = performance.now();
    
    return () => {
      return this.measureCustomMetric(name, startTime);
    };
  }

  /**
   * Get current metrics
   */
  public getMetrics(): PerformanceMetric[] {
    return [...this.metrics];
  }

  /**
   * Get specific metric by name
   */
  public getMetric(name: string): PerformanceMetric | undefined {
    return this.metrics.find(metric => metric.name === name);
  }

  /**
   * Get custom metrics
   */
  public getCustomMetrics(): Map<string, number> {
    return new Map(this.customMetrics);
  }

  /**
   * Generate performance report
   */
  public generateReport(): PerformanceReport {
    return {
      metrics: this.getMetrics(),
      userAgent: navigator.userAgent,
      connection: (navigator as any).connection?.effectiveType || 'unknown',
      timestamp: Date.now(),
      sessionId: this.sessionId,
    };
  }

  /**
   * Send metric to reporting endpoint
   */
  private async sendMetric(metric: PerformanceMetric): Promise<void> {
    if (!this.reportEndpoint) return;

    try {
      await fetch(this.reportEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(metric),
      });
    } catch (error) {
      console.error('Failed to send performance metric:', error);
    }
  }

  /**
   * Report all metrics
   */
  public async reportMetrics(): Promise<void> {
    if (!this.reportEndpoint) return;

    const report = this.generateReport();

    try {
      await fetch(this.reportEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(report),
      });
    } catch (error) {
      console.error('Failed to report performance metrics:', error);
    }
  }

  /**
   * Generate session ID
   */
  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Enable/disable monitoring
   */
  public setEnabled(enabled: boolean): void {
    this.isEnabled = enabled;
  }

  /**
   * Update thresholds
   */
  public updateThresholds(thresholds: Partial<PerformanceThresholds>): void {
    this.thresholds = { ...this.thresholds, ...thresholds };
  }

  /**
   * Clear metrics
   */
  public clearMetrics(): void {
    this.metrics = [];
    this.customMetrics.clear();
  }
}

// Singleton instance
let performanceMonitorInstance: PerformanceMonitor | null = null;

/**
 * Get performance monitor singleton instance
 */
export const getPerformanceMonitor = (config?: {
  thresholds?: Partial<PerformanceThresholds>;
  reportEndpoint?: string;
  enabled?: boolean;
}): PerformanceMonitor => {
  if (!performanceMonitorInstance) {
    performanceMonitorInstance = new PerformanceMonitor(config);
  }
  return performanceMonitorInstance;
};

/**
 * Create new performance monitor instance
 */
export const createPerformanceMonitor = (config?: {
  thresholds?: Partial<PerformanceThresholds>;
  reportEndpoint?: string;
  enabled?: boolean;
}): PerformanceMonitor => {
  return new PerformanceMonitor(config);
};

/**
 * Utility function to measure component render time
 */
export const measureComponentRender = (componentName: string) => {
  const startTime = performance.now();
  
  return {
    end: () => {
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      if (process.env.NODE_ENV === 'development') {
        console.log(`Component ${componentName} render time: ${duration.toFixed(2)}ms`);
      }
      
      return duration;
    }
  };
};

/**
 * Utility function to measure API call performance
 */
export const measureApiCall = async <T>(
  apiCall: () => Promise<T>,
  endpoint: string
): Promise<T> => {
  const startTime = performance.now();
  
  try {
    const result = await apiCall();
    const duration = performance.now() - startTime;
    
    getPerformanceMonitor().handleMetric({
      name: 'APICall',
      value: duration,
      delta: duration,
      id: `api-${endpoint}-${Date.now()}`,
      endpoint,
    });
    
    return result;
  } catch (error) {
    const duration = performance.now() - startTime;
    
    getPerformanceMonitor().handleMetric({
      name: 'APICallError',
      value: duration,
      delta: duration,
      id: `api-error-${endpoint}-${Date.now()}`,
      endpoint,
    });
    
    throw error;
  }
};

/**
 * Utility function to measure scroll performance
 */
export const measureScrollPerformance = (element: HTMLElement) => {
  let scrollStartTime = 0;
  let scrollCount = 0;
  let totalScrollTime = 0;

  const handleScrollStart = () => {
    scrollStartTime = performance.now();
  };

  const handleScrollEnd = () => {
    if (scrollStartTime > 0) {
      const scrollTime = performance.now() - scrollStartTime;
      scrollCount++;
      totalScrollTime += scrollTime;

      getPerformanceMonitor().handleMetric({
        name: 'ScrollPerformance',
        value: scrollTime,
        delta: scrollTime,
        id: `scroll-${Date.now()}`,
      });

      scrollStartTime = 0;
    }
  };

  element.addEventListener('scroll', handleScrollStart, { passive: true });
  element.addEventListener('scrollend', handleScrollEnd, { passive: true });

  return () => {
    element.removeEventListener('scroll', handleScrollStart);
    element.removeEventListener('scrollend', handleScrollEnd);
  };
};

export default PerformanceMonitor;
