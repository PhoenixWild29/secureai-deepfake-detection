/**
 * Confidence Visualization Types
 * TypeScript interfaces and PropTypes for confidence visualization components
 */

// ============================================================================
// Chart Configuration Types
// ============================================================================

/**
 * Chart mode enumeration
 */
export const ChartMode = {
  LINE_CHART: 'line_chart',
  BAR_CHART: 'bar_chart',
  SCATTER_PLOT: 'scatter_plot',
  HEATMAP: 'heatmap',
  COMPARATIVE: 'comparative'
};

/**
 * Trend analysis type enumeration
 */
export const TrendType = {
  MOVING_AVERAGE: 'moving_average',
  PEAK_VALLEY: 'peak_valley',
  STATISTICAL: 'statistical',
  REGRESSION: 'regression'
};

// ============================================================================
// Data Point Types
// ============================================================================

/**
 * Confidence data point interface
 * @typedef {Object} ConfidenceDataPoint
 * @property {number} frameNumber - Frame number (0-based)
 * @property {number} confidence - Confidence score (0-1)
 * @property {number} timestamp - Timestamp in seconds
 * @property {string} algorithm - Detection algorithm identifier
 * @property {Array<SuspiciousRegion>} suspiciousRegions - Array of suspicious regions
 * @property {Object} artifacts - Artifact detection data
 * @property {number} processingTime - Processing time in milliseconds
 * @property {boolean} [isMovingAverage] - Whether this is a moving average point
 * @property {boolean} [isExponentialSmoothing] - Whether this is an exponential smoothing point
 * @property {boolean} [isLinearRegression] - Whether this is a linear regression point
 */
export const ConfidenceDataPoint = {
  frameNumber: Number,
  confidence: Number,
  timestamp: Number,
  algorithm: String,
  suspiciousRegions: Array,
  artifacts: Object,
  processingTime: Number,
  isMovingAverage: Boolean,
  isExponentialSmoothing: Boolean,
  isLinearRegression: Boolean
};

/**
 * Suspicious region interface
 * @typedef {Object} SuspiciousRegion
 * @property {string} regionId - Unique region identifier
 * @property {Object} coordinates - Region coordinates
 * @property {number} coordinates.x - X coordinate
 * @property {number} coordinates.y - Y coordinate
 * @property {number} coordinates.width - Region width
 * @property {number} coordinates.height - Region height
 * @property {number} confidence - Region confidence (0-100)
 * @property {string} description - Human-readable description
 * @property {string} artifactType - Type of artifact detected
 * @property {string} severity - Severity level (low, medium, high, critical)
 */
export const SuspiciousRegion = {
  regionId: String,
  coordinates: {
    x: Number,
    y: Number,
    width: Number,
    height: Number
  },
  confidence: Number,
  description: String,
  artifactType: String,
  severity: String
};

// ============================================================================
// Chart Configuration Types
// ============================================================================

/**
 * Chart configuration interface
 * @typedef {Object} ChartConfig
 * @property {string} mode - Chart mode
 * @property {boolean} enableZoom - Enable zoom functionality
 * @property {boolean} enablePan - Enable pan functionality
 * @property {boolean} enableTooltips - Enable hover tooltips
 * @property {boolean} enableAnimation - Enable chart animations
 * @property {number} frameRate - Frame rate for timestamp calculation
 * @property {number} movingAveragePeriod - Period for moving average calculation
 * @property {Object} confidenceThresholds - Confidence level thresholds
 * @property {number} confidenceThresholds.low - Low confidence threshold
 * @property {number} confidenceThresholds.medium - Medium confidence threshold
 * @property {number} confidenceThresholds.high - High confidence threshold
 * @property {number} confidenceThresholds.critical - Critical confidence threshold
 * @property {boolean} enableVirtualization - Enable data virtualization
 * @property {number} maxDataPoints - Maximum data points for performance
 * @property {number} animationDuration - Animation duration in milliseconds
 * @property {Array<string>} exportFormats - Supported export formats
 * @property {Object} exportResolution - Export resolution settings
 * @property {number} exportResolution.width - Export width
 * @property {number} exportResolution.height - Export height
 */
export const ChartConfig = {
  mode: String,
  enableZoom: Boolean,
  enablePan: Boolean,
  enableTooltips: Boolean,
  enableAnimation: Boolean,
  frameRate: Number,
  movingAveragePeriod: Number,
  confidenceThresholds: {
    low: Number,
    medium: Number,
    high: Number,
    critical: Number
  },
  enableVirtualization: Boolean,
  maxDataPoints: Number,
  animationDuration: Number,
  exportFormats: Array,
  exportResolution: {
    width: Number,
    height: Number
  }
};

/**
 * View settings interface
 * @typedef {Object} ViewSettings
 * @property {boolean} showGrid - Show chart grid
 * @property {boolean} showAxes - Show chart axes
 * @property {boolean} showLegend - Show chart legend
 * @property {boolean} showTooltips - Show hover tooltips
 */
export const ViewSettings = {
  showGrid: Boolean,
  showAxes: Boolean,
  showLegend: Boolean,
  showTooltips: Boolean
};

/**
 * Trend analysis configuration interface
 * @typedef {Object} TrendAnalysis
 * @property {string} type - Trend analysis type
 * @property {boolean} enabled - Whether trend analysis is enabled
 * @property {Object} parameters - Trend analysis parameters
 * @property {number} parameters.period - Period for moving average
 * @property {number} parameters.threshold - Threshold for peak/valley detection
 * @property {number} [parameters.alpha] - Alpha for exponential smoothing
 */
export const TrendAnalysis = {
  type: String,
  enabled: Boolean,
  parameters: {
    period: Number,
    threshold: Number,
    alpha: Number
  }
};

// ============================================================================
// Data Processing Types
// ============================================================================

/**
 * Processed confidence data interface
 * @typedef {Object} ProcessedConfidenceData
 * @property {Array<ConfidenceDataPoint>} rawData - Raw confidence data
 * @property {Array<ConfidenceDataPoint>} processedData - Processed confidence data
 * @property {ConfidenceStatistics} statistics - Calculated statistics
 * @property {ConfidenceMetadata} metadata - Data metadata
 */
export const ProcessedConfidenceData = {
  rawData: Array,
  processedData: Array,
  statistics: Object, // ConfidenceStatistics
  metadata: Object // ConfidenceMetadata
};

/**
 * Confidence statistics interface
 * @typedef {Object} ConfidenceStatistics
 * @property {number} mean - Mean confidence value
 * @property {number} median - Median confidence value
 * @property {number} standardDeviation - Standard deviation
 * @property {Object} distribution - Confidence distribution
 * @property {number} distribution.low - Low confidence count
 * @property {number} distribution.medium - Medium confidence count
 * @property {number} distribution.high - High confidence count
 * @property {number} distribution.critical - Critical confidence count
 * @property {Object} trends - Trend analysis results
 * @property {number} trends.increasing - Percentage of increasing trends
 * @property {number} trends.decreasing - Percentage of decreasing trends
 * @property {number} trends.stable - Percentage of stable trends
 * @property {Array<ConfidenceDataPoint>} peaks - Detected peaks
 * @property {Array<ConfidenceDataPoint>} valleys - Detected valleys
 * @property {number} min - Minimum confidence value
 * @property {number} max - Maximum confidence value
 * @property {number} range - Confidence range
 */
export const ConfidenceStatistics = {
  mean: Number,
  median: Number,
  standardDeviation: Number,
  distribution: {
    low: Number,
    medium: Number,
    high: Number,
    critical: Number
  },
  trends: {
    increasing: Number,
    decreasing: Number,
    stable: Number
  },
  peaks: Array,
  valleys: Array,
  min: Number,
  max: Number,
  range: Number
};

/**
 * Confidence metadata interface
 * @typedef {Object} ConfidenceMetadata
 * @property {string} analysisId - Analysis identifier
 * @property {number} totalFrames - Total number of frames
 * @property {number} processedFrames - Number of processed frames
 * @property {Object} timeRange - Time range information
 * @property {number} timeRange.start - Start time in seconds
 * @property {number} timeRange.end - End time in seconds
 * @property {Object} confidenceRange - Confidence range information
 * @property {number} confidenceRange.min - Minimum confidence value
 * @property {number} confidenceRange.max - Maximum confidence value
 * @property {number} frameRate - Frame rate
 * @property {Object} processingOptions - Processing options used
 */
export const ConfidenceMetadata = {
  analysisId: String,
  totalFrames: Number,
  processedFrames: Number,
  timeRange: {
    start: Number,
    end: Number
  },
  confidenceRange: {
    min: Number,
    max: Number
  },
  frameRate: Number,
  processingOptions: Object
};

// ============================================================================
// Chart Interaction Types
// ============================================================================

/**
 * Chart interaction event interface
 * @typedef {Object} ChartInteractionEvent
 * @property {string} type - Event type
 * @property {ConfidenceDataPoint} dataPoint - Associated data point
 * @property {Object} mousePosition - Mouse position
 * @property {number} mousePosition.x - X coordinate
 * @property {number} mousePosition.y - Y coordinate
 * @property {Object} chartPosition - Chart position
 * @property {number} chartPosition.x - X coordinate in chart space
 * @property {number} chartPosition.y - Y coordinate in chart space
 */
export const ChartInteractionEvent = {
  type: String,
  dataPoint: Object, // ConfidenceDataPoint
  mousePosition: {
    x: Number,
    y: Number
  },
  chartPosition: {
    x: Number,
    y: Number
  }
};

/**
 * Chart dimensions interface
 * @typedef {Object} ChartDimensions
 * @property {number} width - Chart width
 * @property {number} height - Chart height
 * @property {number} chartWidth - Chart content width
 * @property {number} chartHeight - Chart content height
 * @property {Function} xScale - X-axis scale function
 * @property {Function} yScale - Y-axis scale function
 * @property {number} xScaleMin - X-axis minimum value
 * @property {number} xScaleMax - X-axis maximum value
 * @property {number} yScaleMin - Y-axis minimum value
 * @property {number} yScaleMax - Y-axis maximum value
 */
export const ChartDimensions = {
  width: Number,
  height: Number,
  chartWidth: Number,
  chartHeight: Number,
  xScale: Function,
  yScale: Function,
  xScaleMin: Number,
  xScaleMax: Number,
  yScaleMin: Number,
  yScaleMax: Number
};

// ============================================================================
// Export Types
// ============================================================================

/**
 * Export data interface
 * @typedef {Object} ExportData
 * @property {string} exportId - Unique export identifier
 * @property {string} timestamp - Export timestamp
 * @property {string} format - Export format
 * @property {Object} chartData - Chart data
 * @property {ConfidenceMetadata} [metadata] - Optional metadata
 * @property {ConfidenceStatistics} [statistics] - Optional statistics
 * @property {Array<ConfidenceDataPoint>} [rawData] - Optional raw data
 * @property {Object} exportSettings - Export settings
 */
export const ExportData = {
  exportId: String,
  timestamp: String,
  format: String,
  chartData: Object,
  metadata: Object, // ConfidenceMetadata
  statistics: Object, // ConfidenceStatistics
  rawData: Array, // Array<ConfidenceDataPoint>
  exportSettings: Object
};

/**
 * Export result interface
 * @typedef {Object} ExportResult
 * @property {string} format - Export format
 * @property {string} data - Export data (string or data URL)
 * @property {Blob} blob - Export blob
 * @property {number} size - Export size in bytes
 * @property {string} mimeType - MIME type
 * @property {Object} [resolution] - Export resolution (for images)
 * @property {number} [resolution.width] - Export width
 * @property {number} [resolution.height] - Export height
 */
export const ExportResult = {
  format: String,
  data: String,
  blob: Object, // Blob
  size: Number,
  mimeType: String,
  resolution: {
    width: Number,
    height: Number
  }
};

// ============================================================================
// Component Props Types
// ============================================================================

/**
 * InteractiveConfidenceVisualization component props
 * @typedef {Object} InteractiveConfidenceVisualizationProps
 * @property {string} analysisId - Analysis identifier
 * @property {Array<ConfidenceDataPoint>} [frameData] - Frame data array
 * @property {ChartConfig} [config] - Chart configuration
 * @property {Function} [onFrameSelect] - Frame selection callback
 * @property {Function} [onDataExport] - Data export callback
 * @property {Function} [onError] - Error callback
 * @property {string} [className] - Additional CSS classes
 */
export const InteractiveConfidenceVisualizationProps = {
  analysisId: String,
  frameData: Array, // Array<ConfidenceDataPoint>
  config: Object, // ChartConfig
  onFrameSelect: Function,
  onDataExport: Function,
  onError: Function,
  className: String
};

/**
 * useConfidenceChart hook options
 * @typedef {Object} UseConfidenceChartOptions
 * @property {HTMLElement} container - Chart container element
 * @property {Array<ConfidenceDataPoint>} data - Chart data
 * @property {string} mode - Chart mode
 * @property {ChartConfig} config - Chart configuration
 * @property {Function} [onDataPointClick] - Data point click handler
 * @property {Function} [onDataPointHover] - Data point hover handler
 * @property {Function} [onZoomChange] - Zoom change handler
 * @property {Function} [onPanChange] - Pan change handler
 * @property {Function} [onTimeRangeSelect] - Time range selection handler
 */
export const UseConfidenceChartOptions = {
  container: Object, // HTMLElement
  data: Array, // Array<ConfidenceDataPoint>
  mode: String,
  config: Object, // ChartConfig
  onDataPointClick: Function,
  onDataPointHover: Function,
  onZoomChange: Function,
  onPanChange: Function,
  onTimeRangeSelect: Function
};

// ============================================================================
// Export All Types
// ============================================================================

export default {
  // Enums
  ChartMode,
  TrendType,
  
  // Data Types
  ConfidenceDataPoint,
  SuspiciousRegion,
  ProcessedConfidenceData,
  ConfidenceStatistics,
  ConfidenceMetadata,
  
  // Configuration Types
  ChartConfig,
  ViewSettings,
  TrendAnalysis,
  
  // Interaction Types
  ChartInteractionEvent,
  ChartDimensions,
  
  // Export Types
  ExportData,
  ExportResult,
  
  // Component Props
  InteractiveConfidenceVisualizationProps,
  UseConfidenceChartOptions
};
