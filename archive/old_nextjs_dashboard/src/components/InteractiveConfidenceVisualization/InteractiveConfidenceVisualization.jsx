/**
 * InteractiveConfidenceVisualization Component
 * Advanced confidence score visualization with interactive charts and trend analysis
 * 
 * This component provides comprehensive confidence visualization including:
 * - Interactive line charts with hover tooltips and frame timestamps
 * - Trend analysis with peak/valley detection and statistical overlays
 * - Comparative confidence displays across algorithms and time periods
 * - Frame-level drill-down with coordinated navigation
 * - Zoom and pan functionality for detailed examination
 * - Exportable chart data for report generation
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useConfidenceChart } from './hooks/useConfidenceChart';
import { confidenceVisualizationDataService } from './services/confidenceVisualizationDataService';
import { frameAnalysisGridIntegration } from './integrations/frameAnalysisGridIntegration';
import { resultExportInterfaceIntegration } from './integrations/resultExportInterfaceIntegration';
import { useDetectionAnalysis } from '../hooks/useDetectionAnalysis';
import styles from './InteractiveConfidenceVisualization.module.css';

// ============================================================================
// Constants and Enums
// ============================================================================

/**
 * Chart visualization modes
 */
export const CHART_MODES = {
  LINE_CHART: 'line_chart',
  BAR_CHART: 'bar_chart',
  SCATTER_PLOT: 'scatter_plot',
  HEATMAP: 'heatmap',
  COMPARATIVE: 'comparative'
};

/**
 * Trend analysis types
 */
export const TREND_TYPES = {
  MOVING_AVERAGE: 'moving_average',
  PEAK_VALLEY: 'peak_valley',
  STATISTICAL: 'statistical',
  REGRESSION: 'regression'
};

/**
 * Default configuration
 */
const DEFAULT_CONFIG = {
  // Chart settings
  defaultMode: CHART_MODES.LINE_CHART,
  enableZoom: true,
  enablePan: true,
  enableTooltips: true,
  enableAnimation: true,
  
  // Data settings
  frameRate: 30, // FPS for timestamp calculation
  movingAveragePeriod: 10,
  confidenceThresholds: {
    low: 0.0,
    medium: 0.4,
    high: 0.7,
    critical: 0.9
  },
  
  // Performance settings
  enableVirtualization: true,
  maxDataPoints: 1000,
  animationDuration: 300,
  
  // Export settings
  exportFormats: ['json', 'csv', 'png'],
  exportResolution: { width: 1920, height: 1080 }
};

// ============================================================================
// Main Component
// ============================================================================

/**
 * InteractiveConfidenceVisualization - Advanced confidence score visualization component
 * 
 * @param {Object} props - Component properties
 * @param {string} props.analysisId - Analysis identifier for confidence data
 * @param {Array} props.frameData - Frame analysis data array
 * @param {Object} props.config - Configuration options to override defaults
 * @param {Function} props.onFrameSelect - Callback when frame is selected from chart
 * @param {Function} props.onDataExport - Callback for chart data export
 * @param {Function} props.onError - Callback for error handling
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Interactive confidence visualization component
 */
const InteractiveConfidenceVisualization = ({
  analysisId,
  frameData = [],
  config = {},
  onFrameSelect,
  onDataExport,
  onError,
  className = ''
}) => {
  
  // ============================================================================
  // Configuration and State
  // ============================================================================
  
  const mergedConfig = useMemo(() => ({
    ...DEFAULT_CONFIG,
    ...config
  }), [config]);

  // Chart state
  const [chartMode, setChartMode] = useState(mergedConfig.defaultMode);
  const [selectedTimeRange, setSelectedTimeRange] = useState(null);
  const [selectedFrames, setSelectedFrames] = useState([]);
  const [hoveredDataPoint, setHoveredDataPoint] = useState(null);
  
  // Trend analysis state
  const [trendAnalysis, setTrendAnalysis] = useState({
    type: TREND_TYPES.MOVING_AVERAGE,
    enabled: true,
    parameters: {
      period: mergedConfig.movingAveragePeriod,
      threshold: 0.1
    }
  });
  
  // View state
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [viewSettings, setViewSettings] = useState({
    showGrid: true,
    showAxes: true,
    showLegend: true,
    showTooltips: mergedConfig.enableTooltips
  });

  // Data state
  const [confidenceData, setConfidenceData] = useState([]);
  const [processedData, setProcessedData] = useState(null);
  const [loadingState, setLoadingState] = useState({
    data: true,
    processing: false,
    rendering: false
  });

  // Refs
  const chartContainerRef = useRef(null);
  const chartInstanceRef = useRef(null);
  const animationFrameRef = useRef(null);

  // ============================================================================
  // Data Processing and Caching
  // ============================================================================

  /**
   * Process frame data into confidence visualization format
   */
  const processConfidenceData = useCallback(async (rawFrameData) => {
    if (!rawFrameData || rawFrameData.length === 0) return null;

    setLoadingState(prev => ({ ...prev, processing: true }));

    try {
      const processed = await confidenceVisualizationDataService.processFrameData(
        rawFrameData,
        {
          frameRate: mergedConfig.frameRate,
          confidenceThresholds: mergedConfig.confidenceThresholds,
          enableVirtualization: mergedConfig.enableVirtualization,
          maxDataPoints: mergedConfig.maxDataPoints
        }
      );

      setProcessedData(processed);
      setLoadingState(prev => ({ ...prev, processing: false }));
      
      return processed;
    } catch (error) {
      console.error('Error processing confidence data:', error);
      setLoadingState(prev => ({ ...prev, processing: false }));
      onError && onError('data_processing_failed', error.message);
      return null;
    }
  }, [mergedConfig, onError]);

  /**
   * Load and cache confidence data
   */
  const loadConfidenceData = useCallback(async () => {
    if (!analysisId) return;

    setLoadingState(prev => ({ ...prev, data: true }));

    try {
      // Try to get cached data first
      let data = await confidenceVisualizationDataService.getCachedConfidenceData(analysisId);
      
      if (!data) {
        // Generate data from frame analysis
        data = await processConfidenceData(frameData);
        
        if (data) {
          // Cache the processed data
          await confidenceVisualizationDataService.cacheConfidenceData(analysisId, data);
        }
      }

      if (data) {
        setConfidenceData(data.rawData || []);
        setProcessedData(data);
      }

      setLoadingState(prev => ({ ...prev, data: false }));
    } catch (error) {
      console.error('Error loading confidence data:', error);
      setLoadingState(prev => ({ ...prev, data: false }));
      onError && onError('data_load_failed', error.message);
    }
  }, [analysisId, frameData, processConfidenceData, onError]);

  // ============================================================================
  // Chart Integration
  // ============================================================================

  /**
   * Initialize chart with processed data
   */
  const initializeChart = useCallback(async () => {
    if (!processedData || !chartContainerRef.current) return;

    setLoadingState(prev => ({ ...prev, rendering: true }));

    try {
      const chartInstance = await useConfidenceChart({
        container: chartContainerRef.current,
        data: processedData,
        mode: chartMode,
        config: {
          ...mergedConfig,
          zoomLevel,
          panOffset,
          viewSettings,
          trendAnalysis
        },
        onDataPointClick: handleDataPointClick,
        onDataPointHover: handleDataPointHover,
        onZoomChange: setZoomLevel,
        onPanChange: setPanOffset,
        onTimeRangeSelect: setSelectedTimeRange
      });

      chartInstanceRef.current = chartInstance;
      setLoadingState(prev => ({ ...prev, rendering: false }));
    } catch (error) {
      console.error('Error initializing chart:', error);
      setLoadingState(prev => ({ ...prev, rendering: false }));
      onError && onError('chart_init_failed', error.message);
    }
  }, [processedData, chartMode, mergedConfig, zoomLevel, panOffset, viewSettings, trendAnalysis, onError]);

  /**
   * Update chart when data or settings change
   */
  const updateChart = useCallback(async () => {
    if (!chartInstanceRef.current) return;

    try {
      await chartInstanceRef.current.update({
        data: processedData,
        mode: chartMode,
        config: {
          ...mergedConfig,
          zoomLevel,
          panOffset,
          viewSettings,
          trendAnalysis
        }
      });
    } catch (error) {
      console.error('Error updating chart:', error);
      onError && onError('chart_update_failed', error.message);
    }
  }, [processedData, chartMode, mergedConfig, zoomLevel, panOffset, viewSettings, trendAnalysis, onError]);

  // ============================================================================
  // Event Handlers
  // ============================================================================

  /**
   * Handle data point click for frame navigation
   */
  const handleDataPointClick = useCallback((dataPoint) => {
    if (!dataPoint || !onFrameSelect) return;

    const frameNumber = dataPoint.frameNumber;
    const timestamp = dataPoint.timestamp;

    // Update selected frames
    setSelectedFrames(prev => {
      const exists = prev.includes(frameNumber);
      return exists 
        ? prev.filter(f => f !== frameNumber)
        : [...prev, frameNumber];
    });

    // Notify parent component for frame navigation
    onFrameSelect({
      frameNumber,
      timestamp,
      confidence: dataPoint.confidence,
      dataPoint
    });

    // Integrate with FrameAnalysisGrid
    frameAnalysisGridIntegration.navigateToFrame(frameNumber, {
      highlight: true,
      scrollIntoView: true
    });
  }, [onFrameSelect]);

  /**
   * Handle data point hover for tooltips
   */
  const handleDataPointHover = useCallback((dataPoint) => {
    setHoveredDataPoint(dataPoint);
  }, []);

  /**
   * Handle chart mode change
   */
  const handleChartModeChange = useCallback((newMode) => {
    setChartMode(newMode);
  }, []);

  /**
   * Handle trend analysis toggle
   */
  const handleTrendAnalysisToggle = useCallback((enabled) => {
    setTrendAnalysis(prev => ({ ...prev, enabled }));
  }, []);

  /**
   * Handle export request
   */
  const handleExport = useCallback(async (format = 'json') => {
    if (!processedData || !onDataExport) return;

    try {
      const exportData = await resultExportInterfaceIntegration.prepareChartData(
        processedData,
        {
          format,
          resolution: mergedConfig.exportResolution,
          includeMetadata: true,
          includeTrendAnalysis: trendAnalysis.enabled
        }
      );

      onDataExport(exportData, format);
    } catch (error) {
      console.error('Error exporting chart data:', error);
      onError && onError('export_failed', error.message);
    }
  }, [processedData, onDataExport, mergedConfig.exportResolution, trendAnalysis.enabled, onError]);

  // ============================================================================
  // Effects
  // ============================================================================

  // Load data when analysisId or frameData changes
  useEffect(() => {
    loadConfidenceData();
  }, [loadConfidenceData]);

  // Initialize chart when processed data is available
  useEffect(() => {
    if (processedData) {
      initializeChart();
    }
  }, [processedData, initializeChart]);

  // Update chart when settings change
  useEffect(() => {
    if (chartInstanceRef.current) {
      updateChart();
    }
  }, [chartMode, zoomLevel, panOffset, viewSettings, trendAnalysis, updateChart]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy();
      }
    };
  }, []);

  // ============================================================================
  // Render Functions
  // ============================================================================

  /**
   * Render chart mode selector
   */
  const renderChartModeSelector = () => (
    <div className={styles.chartModeSelector}>
      <label>Chart Mode:</label>
      <div className={styles.modeButtons}>
        {Object.entries(CHART_MODES).map(([key, mode]) => (
          <button
            key={mode}
            className={`${styles.modeButton} ${chartMode === mode ? styles.active : ''}`}
            onClick={() => handleChartModeChange(mode)}
            type="button"
          >
            {key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
          </button>
        ))}
      </div>
    </div>
  );

  /**
   * Render trend analysis controls
   */
  const renderTrendAnalysisControls = () => (
    <div className={styles.trendAnalysisControls}>
      <label className={styles.checkboxLabel}>
        <input
          type="checkbox"
          checked={trendAnalysis.enabled}
          onChange={(e) => handleTrendAnalysisToggle(e.target.checked)}
          className={styles.checkbox}
        />
        Enable Trend Analysis
      </label>
      
      {trendAnalysis.enabled && (
        <div className={styles.trendParameters}>
          <label>
            Period:
            <input
              type="number"
              min="3"
              max="50"
              value={trendAnalysis.parameters.period}
              onChange={(e) => setTrendAnalysis(prev => ({
                ...prev,
                parameters: {
                  ...prev.parameters,
                  period: parseInt(e.target.value)
                }
              }))}
              className={styles.numberInput}
            />
          </label>
        </div>
      )}
    </div>
  );

  /**
   * Render view settings controls
   */
  const renderViewSettings = () => (
    <div className={styles.viewSettings}>
      <h4>View Settings</h4>
      <div className={styles.settingGroup}>
        <label className={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={viewSettings.showGrid}
            onChange={(e) => setViewSettings(prev => ({ ...prev, showGrid: e.target.checked }))}
            className={styles.checkbox}
          />
          Show Grid
        </label>
        
        <label className={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={viewSettings.showAxes}
            onChange={(e) => setViewSettings(prev => ({ ...prev, showAxes: e.target.checked }))}
            className={styles.checkbox}
          />
          Show Axes
        </label>
        
        <label className={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={viewSettings.showTooltips}
            onChange={(e) => setViewSettings(prev => ({ ...prev, showTooltips: e.target.checked }))}
            className={styles.checkbox}
          />
          Show Tooltips
        </label>
      </div>
    </div>
  );

  /**
   * Render export controls
   */
  const renderExportControls = () => (
    <div className={styles.exportControls}>
      <h4>Export</h4>
      <div className={styles.exportButtons}>
        {mergedConfig.exportFormats.map(format => (
          <button
            key={format}
            onClick={() => handleExport(format)}
            className={styles.exportButton}
            type="button"
          >
            Export {format.toUpperCase()}
          </button>
        ))}
      </div>
    </div>
  );

  /**
   * Render loading state
   */
  const renderLoadingState = () => (
    <div className={styles.loadingContainer}>
      <div className={styles.loadingSpinner} />
      <div className={styles.loadingMessage}>
        {loadingState.data && 'Loading confidence data...'}
        {loadingState.processing && 'Processing data...'}
        {loadingState.rendering && 'Rendering chart...'}
      </div>
    </div>
  );

  /**
   * Render error state
   */
  const renderErrorState = () => (
    <div className={styles.errorContainer}>
      <div className={styles.errorIcon}>📊</div>
      <h3>Chart Rendering Error</h3>
      <p>Unable to render confidence visualization. Please check your data and try again.</p>
    </div>
  );

  // ============================================================================
  // Main Render
  // ============================================================================

  if (loadingState.data || loadingState.processing) {
    return renderLoadingState();
  }

  if (!processedData) {
    return renderErrorState();
  }

  return (
    <div className={`${styles.interactiveConfidenceVisualization} ${className}`}>
      {/* Header Controls */}
      <div className={styles.headerControls}>
        <div className={styles.controlsRow}>
          {renderChartModeSelector()}
          {renderTrendAnalysisControls()}
        </div>
        
        <div className={styles.controlsRow}>
          {renderViewSettings()}
          {renderExportControls()}
        </div>
      </div>

      {/* Chart Container */}
      <div className={styles.chartContainer}>
        <div 
          ref={chartContainerRef}
          className={styles.chartCanvas}
        />
        
        {/* Loading overlay for chart updates */}
        {loadingState.rendering && (
          <div className={styles.chartLoadingOverlay}>
            <div className={styles.loadingSpinner} />
          </div>
        )}
      </div>

      {/* Data Point Info */}
      {hoveredDataPoint && (
        <div className={styles.dataPointInfo}>
          <h4>Data Point Details</h4>
          <div className={styles.dataPointDetails}>
            <div><strong>Frame:</strong> {hoveredDataPoint.frameNumber}</div>
            <div><strong>Confidence:</strong> {(hoveredDataPoint.confidence * 100).toFixed(1)}%</div>
            <div><strong>Timestamp:</strong> {hoveredDataPoint.timestamp.toFixed(2)}s</div>
            {hoveredDataPoint.algorithm && (
              <div><strong>Algorithm:</strong> {hoveredDataPoint.algorithm}</div>
            )}
          </div>
        </div>
      )}

      {/* Selected Frames Summary */}
      {selectedFrames.length > 0 && (
        <div className={styles.selectedFramesSummary}>
          <h4>Selected Frames ({selectedFrames.length})</h4>
          <div className={styles.selectedFramesList}>
            {selectedFrames.slice(0, 10).map(frameNumber => (
              <span key={frameNumber} className={styles.selectedFrame}>
                Frame {frameNumber}
              </span>
            ))}
            {selectedFrames.length > 10 && (
              <span className={styles.moreFrames}>
                +{selectedFrames.length - 10} more
              </span>
            )}
          </div>
        </div>
      )}

      {/* Debug Information */}
      {process.env.NODE_ENV === 'development' && (
        <div className={styles.debugInfo}>
          <small>
            Mode: {chartMode} | Data Points: {confidenceData.length} | 
            Zoom: {zoomLevel.toFixed(2)}x | Selected: {selectedFrames.length} frames
          </small>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Exports
// ============================================================================

export { CHART_MODES, TREND_TYPES };
export default InteractiveConfidenceVisualization;
