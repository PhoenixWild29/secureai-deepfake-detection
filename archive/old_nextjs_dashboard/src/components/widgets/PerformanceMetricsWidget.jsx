/**
 * Virtualized Performance Metrics Widget
 * Efficiently renders large datasets of performance metrics with dynamic heights
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { VariableSizeList as VariableList } from 'react-window';
import { measureComponentRender } from '@/utils/performanceMonitor';
import { getApiCache } from '@/services/api';
import styles from './PerformanceMetricsWidget.module.css';

interface PerformanceMetric {
  id: string;
  name: string;
  value: number;
  unit: string;
  timestamp: Date;
  category: 'cpu' | 'memory' | 'gpu' | 'network' | 'storage';
  trend: 'up' | 'down' | 'stable';
  threshold: {
    warning: number;
    critical: number;
  };
}

interface PerformanceMetricsWidgetProps {
  className?: string;
  height?: number;
  enableVirtualization?: boolean;
  refreshInterval?: number;
  maxItems?: number;
}

const PerformanceMetricsWidget: React.FC<PerformanceMetricsWidgetProps> = ({
  className = '',
  height = 400,
  enableVirtualization = true,
  refreshInterval = 5000,
  maxItems = 1000,
}) => {
  const renderTimer = useRef<{ end: () => number } | null>(null);
  const apiCache = getApiCache();
  
  const [metrics, setMetrics] = useState<PerformanceMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    renderTimer.current = measureComponentRender('PerformanceMetricsWidget');
    return () => {
      if (renderTimer.current) {
        renderTimer.current.end();
      }
    };
  }, []);

  const loadMetrics = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiCache.request({
        url: '/api/performance/metrics',
        method: 'GET',
        params: { limit: maxItems },
      });
      
      const newMetrics: PerformanceMetric[] = response.data.map((item: any) => ({
        id: item.id,
        name: item.name,
        value: item.value,
        unit: item.unit,
        timestamp: new Date(item.timestamp),
        category: item.category,
        trend: item.trend,
        threshold: item.threshold,
      }));
      
      setMetrics(newMetrics);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load metrics');
    } finally {
      setLoading(false);
    }
  }, [apiCache, maxItems]);

  useEffect(() => {
    loadMetrics();
    if (refreshInterval > 0) {
      const interval = setInterval(loadMetrics, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [loadMetrics, refreshInterval]);

  const getItemSize = useCallback((index: number) => {
    return 80; // Fixed height for metrics
  }, []);

  const MetricItem: React.FC<{ index: number; style: React.CSSProperties }> = ({ index, style, data }) => {
    const metric = data[index];
    
    const getCategoryColor = (category: string) => {
      switch (category) {
        case 'cpu': return '#3b82f6';
        case 'memory': return '#10b981';
        case 'gpu': return '#f59e0b';
        case 'network': return '#8b5cf6';
        case 'storage': return '#ef4444';
        default: return '#6b7280';
      }
    };

    const getTrendIcon = (trend: string) => {
      switch (trend) {
        case 'up': return '↗';
        case 'down': return '↘';
        case 'stable': return '→';
        default: return '?';
      }
    };

    const isWarning = metric.value >= metric.threshold.warning;
    const isCritical = metric.value >= metric.threshold.critical;

    return (
      <div style={style} className={styles.metricItem}>
        <div className={styles.metricHeader}>
          <div className={styles.metricName}>{metric.name}</div>
          <div className={styles.metricValue}>
            {metric.value.toFixed(2)} {metric.unit}
          </div>
        </div>
        <div className={styles.metricDetails}>
          <div className={styles.metricCategory} style={{ color: getCategoryColor(metric.category) }}>
            {metric.category.toUpperCase()}
          </div>
          <div className={styles.metricTrend}>
            {getTrendIcon(metric.trend)}
          </div>
          <div className={`${styles.metricStatus} ${isCritical ? styles.critical : isWarning ? styles.warning : styles.normal}`}>
            {isCritical ? 'Critical' : isWarning ? 'Warning' : 'Normal'}
          </div>
        </div>
      </div>
    );
  };

  if (loading && metrics.length === 0) {
    return (
      <div className={`${styles.widget} ${className}`}>
        <div className={styles.loadingContainer}>
          <div className={styles.loadingSpinner} />
          <p>Loading performance metrics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${styles.widget} ${className}`}>
        <div className={styles.errorContainer}>
          <p>{error}</p>
          <button onClick={loadMetrics}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.widget} ${className}`}>
      <div className={styles.header}>
        <h2>Performance Metrics</h2>
        <div className={styles.stats}>{metrics.length} metrics</div>
      </div>
      
      <div className={styles.listContainer} style={{ height }}>
        {enableVirtualization ? (
          <VariableList
            height={height}
            itemCount={metrics.length}
            itemSize={getItemSize}
            itemData={metrics}
          >
            {MetricItem}
          </VariableList>
        ) : (
          <div className={styles.nonVirtualizedList}>
            {metrics.map((metric, index) => (
              <MetricItem key={metric.id} index={index} style={{}} data={metrics} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PerformanceMetricsWidget;
