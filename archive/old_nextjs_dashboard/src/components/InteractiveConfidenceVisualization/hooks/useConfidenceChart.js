/**
 * useConfidenceChart Hook
 * Custom React hook for rendering interactive confidence charts with zoom, pan, and tooltips
 */

import { useRef, useCallback, useEffect, useState } from 'react';

// ============================================================================
// Chart Configuration
// ============================================================================

const CHART_DEFAULTS = {
  // Canvas settings
  width: 800,
  height: 400,
  padding: { top: 20, right: 20, bottom: 40, left: 60 },
  
  // Visual settings
  colors: {
    primary: '#3b82f6',
    secondary: '#ef4444',
    background: '#ffffff',
    grid: '#e5e7eb',
    text: '#374151',
    tooltip: 'rgba(0, 0, 0, 0.8)'
  },
  
  // Interaction settings
  zoomSensitivity: 0.1,
  panSensitivity: 1.0,
  tooltipOffset: 10,
  
  // Animation settings
  animationDuration: 300,
  easingFunction: 'ease-out'
};

// ============================================================================
// Chart Utilities
// ============================================================================

/**
 * Calculate moving average for trend analysis
 */
const calculateMovingAverage = (data, period) => {
  if (data.length < period) return data;
  
  const result = [];
  for (let i = 0; i < data.length; i++) {
    const start = Math.max(0, i - period + 1);
    const slice = data.slice(start, i + 1);
    const average = slice.reduce((sum, point) => sum + point.confidence, 0) / slice.length;
    result.push({
      ...data[i],
      confidence: average,
      isMovingAverage: true
    });
  }
  return result;
};

/**
 * Detect peaks and valleys in confidence data
 */
const detectPeaksAndValleys = (data, threshold = 0.1) => {
  const peaks = [];
  const valleys = [];
  
  for (let i = 1; i < data.length - 1; i++) {
    const prev = data[i - 1].confidence;
    const curr = data[i].confidence;
    const next = data[i + 1].confidence;
    
    // Peak detection
    if (curr > prev && curr > next && (curr - Math.max(prev, next)) > threshold) {
      peaks.push({ ...data[i], type: 'peak' });
    }
    
    // Valley detection
    if (curr < prev && curr < next && (Math.min(prev, next) - curr) > threshold) {
      valleys.push({ ...data[i], type: 'valley' });
    }
  }
  
  return { peaks, valleys };
};

/**
 * Calculate chart dimensions and scales
 */
const calculateChartDimensions = (container, data, zoomLevel = 1, panOffset = { x: 0, y: 0 }) => {
  const rect = container.getBoundingClientRect();
  const width = rect.width || CHART_DEFAULTS.width;
  const height = rect.height || CHART_DEFAULTS.height;
  
  const chartWidth = width - CHART_DEFAULTS.padding.left - CHART_DEFAULTS.padding.right;
  const chartHeight = height - CHART_DEFAULTS.padding.top - CHART_DEFAULTS.padding.bottom;
  
  // Calculate data ranges
  const xValues = data.map(point => point.timestamp);
  const yValues = data.map(point => point.confidence);
  
  const xMin = Math.min(...xValues);
  const xMax = Math.max(...xValues);
  const yMin = Math.max(0, Math.min(...yValues) - 0.1);
  const yMax = Math.min(1, Math.max(...yValues) + 0.1);
  
  // Apply zoom and pan
  const xRange = (xMax - xMin) / zoomLevel;
  const yRange = (yMax - yMin) / zoomLevel;
  
  const xCenter = (xMin + xMax) / 2;
  const yCenter = (yMin + yMax) / 2;
  
  const xScaleMin = xCenter - xRange / 2 + panOffset.x * xRange / chartWidth;
  const xScaleMax = xCenter + xRange / 2 + panOffset.x * xRange / chartWidth;
  const yScaleMin = yCenter - yRange / 2 - panOffset.y * yRange / chartHeight;
  const yScaleMax = yCenter + yRange / 2 - panOffset.y * yRange / chartHeight;
  
  return {
    width,
    height,
    chartWidth,
    chartHeight,
    xScale: (x) => (x - xScaleMin) / (xScaleMax - xScaleMin) * chartWidth + CHART_DEFAULTS.padding.left,
    yScale: (y) => (y - yScaleMin) / (yScaleMax - yScaleMin) * chartHeight + CHART_DEFAULTS.padding.top,
    xScaleMin,
    xScaleMax,
    yScaleMin,
    yScaleMax
  };
};

// ============================================================================
// Main Hook
// ============================================================================

/**
 * useConfidenceChart - Custom hook for interactive confidence chart rendering
 * 
 * @param {Object} options - Chart configuration options
 * @param {HTMLElement} options.container - DOM container for the chart
 * @param {Array} options.data - Confidence data array
 * @param {string} options.mode - Chart mode (line_chart, bar_chart, etc.)
 * @param {Object} options.config - Chart configuration
 * @param {Function} options.onDataPointClick - Data point click handler
 * @param {Function} options.onDataPointHover - Data point hover handler
 * @param {Function} options.onZoomChange - Zoom change handler
 * @param {Function} options.onPanChange - Pan change handler
 * @param {Function} options.onTimeRangeSelect - Time range selection handler
 * @returns {Object} Chart instance with methods
 */
export const useConfidenceChart = ({
  container,
  data = [],
  mode = 'line_chart',
  config = {},
  onDataPointClick,
  onDataPointHover,
  onZoomChange,
  onPanChange,
  onTimeRangeSelect
}) => {
  
  // ============================================================================
  // State and Refs
  // ============================================================================
  
  const canvasRef = useRef(null);
  const ctxRef = useRef(null);
  const animationRef = useRef(null);
  const isDraggingRef = useRef(false);
  const lastMousePosRef = useRef({ x: 0, y: 0 });
  
  const [isInitialized, setIsInitialized] = useState(false);

  // ============================================================================
  // Chart Rendering Functions
  // ============================================================================

  /**
   * Initialize canvas and context
   */
  const initializeCanvas = useCallback(() => {
    if (!container) return false;

    // Create canvas element
    const canvas = document.createElement('canvas');
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.display = 'block';
    
    // Set up high DPI rendering
    const dpr = window.devicePixelRatio || 1;
    const rect = container.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    
    // Clear container and add canvas
    container.innerHTML = '';
    container.appendChild(canvas);
    
    canvasRef.current = canvas;
    ctxRef.current = ctx;
    
    return true;
  }, [container]);

  /**
   * Render grid lines
   */
  const renderGrid = useCallback((ctx, dimensions, config) => {
    if (!config.showGrid) return;

    const { chartWidth, chartHeight, xScaleMin, xScaleMax, yScaleMin, yScaleMax } = dimensions;
    
    ctx.strokeStyle = CHART_DEFAULTS.colors.grid;
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 2]);

    // Vertical grid lines
    const xSteps = 10;
    for (let i = 0; i <= xSteps; i++) {
      const x = CHART_DEFAULTS.padding.left + (chartWidth / xSteps) * i;
      ctx.beginPath();
      ctx.moveTo(x, CHART_DEFAULTS.padding.top);
      ctx.lineTo(x, CHART_DEFAULTS.padding.top + chartHeight);
      ctx.stroke();
    }

    // Horizontal grid lines
    const ySteps = 8;
    for (let i = 0; i <= ySteps; i++) {
      const y = CHART_DEFAULTS.padding.top + (chartHeight / ySteps) * i;
      ctx.beginPath();
      ctx.moveTo(CHART_DEFAULTS.padding.left, y);
      ctx.lineTo(CHART_DEFAULTS.padding.left + chartWidth, y);
      ctx.stroke();
    }

    ctx.setLineDash([]);
  }, []);

  /**
   * Render axes
   */
  const renderAxes = useCallback((ctx, dimensions, config) => {
    if (!config.showAxes) return;

    const { chartWidth, chartHeight, xScaleMin, xScaleMax, yScaleMin, yScaleMax } = dimensions;
    
    ctx.strokeStyle = CHART_DEFAULTS.colors.text;
    ctx.lineWidth = 2;

    // X-axis
    ctx.beginPath();
    ctx.moveTo(CHART_DEFAULTS.padding.left, CHART_DEFAULTS.padding.top + chartHeight);
    ctx.lineTo(CHART_DEFAULTS.padding.left + chartWidth, CHART_DEFAULTS.padding.top + chartHeight);
    ctx.stroke();

    // Y-axis
    ctx.beginPath();
    ctx.moveTo(CHART_DEFAULTS.padding.left, CHART_DEFAULTS.padding.top);
    ctx.lineTo(CHART_DEFAULTS.padding.left, CHART_DEFAULTS.padding.top + chartHeight);
    ctx.stroke();

    // Axis labels
    ctx.fillStyle = CHART_DEFAULTS.colors.text;
    ctx.font = '12px -apple-system, BlinkMacSystemFont, sans-serif';
    ctx.textAlign = 'center';
    
    // X-axis label
    ctx.fillText('Time (seconds)', CHART_DEFAULTS.padding.left + chartWidth / 2, CHART_DEFAULTS.padding.top + chartHeight + 30);
    
    // Y-axis label
    ctx.save();
    ctx.translate(20, CHART_DEFAULTS.padding.top + chartHeight / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Confidence Score', 0, 0);
    ctx.restore();
  }, []);

  /**
   * Render line chart
   */
  const renderLineChart = useCallback((ctx, data, dimensions, config) => {
    if (data.length < 2) return;

    const { xScale, yScale } = dimensions;
    
    // Main confidence line
    ctx.strokeStyle = CHART_DEFAULTS.colors.primary;
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    data.forEach((point, index) => {
      const x = xScale(point.timestamp);
      const y = yScale(point.confidence);
      
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    
    ctx.stroke();

    // Data points
    ctx.fillStyle = CHART_DEFAULTS.colors.primary;
    data.forEach(point => {
      const x = xScale(point.timestamp);
      const y = yScale(point.confidence);
      
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, 2 * Math.PI);
      ctx.fill();
    });

    // Trend analysis overlay
    if (config.trendAnalysis?.enabled) {
      const movingAverage = calculateMovingAverage(data, config.trendAnalysis.parameters.period);
      
      ctx.strokeStyle = CHART_DEFAULTS.colors.secondary;
      ctx.lineWidth = 1;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      
      movingAverage.forEach((point, index) => {
        const x = xScale(point.timestamp);
        const y = yScale(point.confidence);
        
        if (index === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });
      
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }, []);

  /**
   * Render bar chart
   */
  const renderBarChart = useCallback((ctx, data, dimensions, config) => {
    if (data.length === 0) return;

    const { xScale, yScale, chartHeight } = dimensions;
    const barWidth = Math.max(2, (xScale(data[1]?.timestamp || 1) - xScale(data[0]?.timestamp || 0)) * 0.8);
    
    data.forEach(point => {
      const x = xScale(point.timestamp) - barWidth / 2;
      const y = yScale(point.confidence);
      const height = CHART_DEFAULTS.padding.top + chartHeight - y;
      
      // Color based on confidence level
      let color = CHART_DEFAULTS.colors.primary;
      if (point.confidence >= 0.9) color = '#ef4444';
      else if (point.confidence >= 0.7) color = '#f59e0b';
      else if (point.confidence >= 0.4) color = '#3b82f6';
      else color = '#10b981';
      
      ctx.fillStyle = color;
      ctx.fillRect(x, y, barWidth, height);
    });
  }, []);

  /**
   * Render scatter plot
   */
  const renderScatterPlot = useCallback((ctx, data, dimensions, config) => {
    if (data.length === 0) return;

    const { xScale, yScale } = dimensions;
    
    data.forEach(point => {
      const x = xScale(point.timestamp);
      const y = yScale(point.confidence);
      
      // Color and size based on confidence
      const size = 3 + (point.confidence * 5);
      const alpha = 0.3 + (point.confidence * 0.7);
      
      ctx.fillStyle = `rgba(59, 130, 246, ${alpha})`;
      ctx.beginPath();
      ctx.arc(x, y, size, 0, 2 * Math.PI);
      ctx.fill();
      
      // Border
      ctx.strokeStyle = CHART_DEFAULTS.colors.primary;
      ctx.lineWidth = 1;
      ctx.stroke();
    });
  }, []);

  /**
   * Render tooltip
   */
  const renderTooltip = useCallback((ctx, dataPoint, mousePos) => {
    if (!dataPoint || !config.showTooltips) return;

    const tooltipWidth = 200;
    const tooltipHeight = 80;
    const x = Math.min(mousePos.x + CHART_DEFAULTS.tooltipOffset, ctx.canvas.width - tooltipWidth);
    const y = Math.max(mousePos.y - tooltipHeight - CHART_DEFAULTS.tooltipOffset, 0);

    // Tooltip background
    ctx.fillStyle = CHART_DEFAULTS.colors.tooltip;
    ctx.fillRect(x, y, tooltipWidth, tooltipHeight);

    // Tooltip text
    ctx.fillStyle = 'white';
    ctx.font = '12px -apple-system, BlinkMacSystemFont, sans-serif';
    ctx.textAlign = 'left';
    
    const lines = [
      `Frame: ${dataPoint.frameNumber}`,
      `Confidence: ${(dataPoint.confidence * 100).toFixed(1)}%`,
      `Time: ${dataPoint.timestamp.toFixed(2)}s`
    ];
    
    lines.forEach((line, index) => {
      ctx.fillText(line, x + 10, y + 20 + (index * 18));
    });
  }, [config.showTooltips]);

  /**
   * Main render function
   */
  const render = useCallback(() => {
    if (!ctxRef.current || !data.length) return;

    const ctx = ctxRef.current;
    const canvas = canvasRef.current;
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Calculate dimensions
    const dimensions = calculateChartDimensions(container, data, config.zoomLevel, config.panOffset);
    
    // Render chart elements
    renderGrid(ctx, dimensions, config);
    renderAxes(ctx, dimensions, config);
    
    // Render chart based on mode
    switch (mode) {
      case 'line_chart':
        renderLineChart(ctx, data, dimensions, config);
        break;
      case 'bar_chart':
        renderBarChart(ctx, data, dimensions, config);
        break;
      case 'scatter_plot':
        renderScatterPlot(ctx, data, dimensions, config);
        break;
      default:
        renderLineChart(ctx, data, dimensions, config);
    }
    
    // Render tooltip if hovering
    if (config.hoveredDataPoint) {
      renderTooltip(ctx, config.hoveredDataPoint, config.mousePosition);
    }
  }, [data, mode, config, container, renderGrid, renderAxes, renderLineChart, renderBarChart, renderScatterPlot, renderTooltip]);

  // ============================================================================
  // Event Handlers
  // ============================================================================

  /**
   * Handle mouse events for interaction
   */
  const handleMouseEvent = useCallback((event) => {
    if (!canvasRef.current) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;

    // Find nearest data point
    const nearestPoint = findNearestDataPoint(mouseX, mouseY, data);
    
    if (nearestPoint && onDataPointHover) {
      onDataPointHover(nearestPoint);
    }

    // Handle dragging for pan
    if (isDraggingRef.current) {
      const deltaX = mouseX - lastMousePosRef.current.x;
      const deltaY = mouseY - lastMousePosRef.current.y;
      
      if (onPanChange) {
        onPanChange(prev => ({
          x: prev.x + deltaX,
          y: prev.y + deltaY
        }));
      }
    }

    lastMousePosRef.current = { x: mouseX, y: mouseY };
  }, [data, onDataPointHover, onPanChange]);

  /**
   * Handle click events
   */
  const handleClick = useCallback((event) => {
    if (!canvasRef.current) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;

    const nearestPoint = findNearestDataPoint(mouseX, mouseY, data);
    
    if (nearestPoint && onDataPointClick) {
      onDataPointClick(nearestPoint);
    }
  }, [data, onDataPointClick]);

  /**
   * Handle wheel events for zoom
   */
  const handleWheel = useCallback((event) => {
    event.preventDefault();
    
    const delta = event.deltaY > 0 ? 1 + CHART_DEFAULTS.zoomSensitivity : 1 - CHART_DEFAULTS.zoomSensitivity;
    const newZoomLevel = Math.max(0.1, Math.min(10, config.zoomLevel * delta));
    
    if (onZoomChange) {
      onZoomChange(newZoomLevel);
    }
  }, [config.zoomLevel, onZoomChange]);

  /**
   * Find nearest data point to mouse position
   */
  const findNearestDataPoint = useCallback((mouseX, mouseY, data) => {
    if (!data.length) return null;

    const dimensions = calculateChartDimensions(container, data, config.zoomLevel, config.panOffset);
    let nearestPoint = null;
    let minDistance = Infinity;

    data.forEach(point => {
      const x = dimensions.xScale(point.timestamp);
      const y = dimensions.yScale(point.confidence);
      
      const distance = Math.sqrt((mouseX - x) ** 2 + (mouseY - y) ** 2);
      
      if (distance < minDistance && distance < 20) { // 20px threshold
        minDistance = distance;
        nearestPoint = point;
      }
    });

    return nearestPoint;
  }, [container, config.zoomLevel, config.panOffset]);

  // ============================================================================
  // Chart Instance Methods
  // ============================================================================

  const chartInstanceMethods = useMemo(() => ({
    /**
     * Initialize the chart
     */
    init: async () => {
      if (!initializeCanvas()) {
        throw new Error('Failed to initialize canvas');
      }

      // Add event listeners
      if (canvasRef.current) {
        canvasRef.current.addEventListener('mousemove', handleMouseEvent);
        canvasRef.current.addEventListener('click', handleClick);
        canvasRef.current.addEventListener('wheel', handleWheel);
        canvasRef.current.addEventListener('mousedown', () => { isDraggingRef.current = true; });
        canvasRef.current.addEventListener('mouseup', () => { isDraggingRef.current = false; });
        canvasRef.current.addEventListener('mouseleave', () => { isDraggingRef.current = false; });
      }

      setIsInitialized(true);
      return true;
    },

    /**
     * Update chart data and configuration
     */
    update: async (newConfig) => {
      if (!isInitialized) return;
      
      // Update configuration
      Object.assign(config, newConfig);
      
      // Re-render
      render();
    },

    /**
     * Destroy chart and cleanup
     */
    destroy: () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      
      if (canvasRef.current) {
        canvasRef.current.removeEventListener('mousemove', handleMouseEvent);
        canvasRef.current.removeEventListener('click', handleClick);
        canvasRef.current.removeEventListener('wheel', handleWheel);
      }
      
      setIsInitialized(false);
    },

    /**
     * Get chart data for export
     */
    getExportData: () => ({
      data,
      mode,
      config,
      dimensions: calculateChartDimensions(container, data, config.zoomLevel, config.panOffset)
    })
  }), [isInitialized, data, mode, config, container, initializeCanvas, handleMouseEvent, handleClick, handleWheel, render]);

  // ============================================================================
  // Effects
  // ============================================================================

  // Initialize chart when container is available
  useEffect(() => {
    if (container && !isInitialized) {
      chartInstanceMethods.init();
    }
  }, [container, isInitialized, chartInstanceMethods]);

  // Re-render when data or config changes
  useEffect(() => {
    if (isInitialized) {
      render();
    }
  }, [isInitialized, render]);

  // ============================================================================
  // Return
  // ============================================================================

  return chartInstanceMethods;
};

export default useConfidenceChart;
