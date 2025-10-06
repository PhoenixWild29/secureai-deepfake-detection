/**
 * Visualization Types and Interfaces
 * Work Order #48 - useResultVisualization Hook with Extended State Management
 * 
 * TypeScript/JSDoc type definitions for the state managed by useResultVisualization hook,
 * including types for confidence scores, heatmap data, export options, visualization modes,
 * and blockchain verification status.
 */

// ============================================================================
// Core Visualization Types
// ============================================================================

/**
 * Visualization mode enumeration
 * @typedef {('summary'|'detailed'|'export_preview')} VisualizationMode
 */
export const VISUALIZATION_MODES = {
  SUMMARY: 'summary',
  DETAILED: 'detailed',
  EXPORT_PREVIEW: 'export_preview'
};

/**
 * Export format enumeration
 * @typedef {('pdf'|'json'|'csv')} ExportFormat
 */
export const EXPORT_FORMATS = {
  PDF: 'pdf',
  JSON: 'json',
  CSV: 'csv'
};

/**
 * Export status enumeration
 * @typedef {('idle'|'initiating'|'processing'|'generating'|'completing'|'completed'|'failed'|'cancelled')} ExportStatus
 */
export const EXPORT_STATUS = {
  IDLE: 'idle',
  INITIATING: 'initiating',
  PROCESSING: 'processing',
  GENERATING: 'generating',
  COMPLETING: 'completing',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
};

/**
 * Blockchain verification status enumeration
 * @typedef {('pending'|'verifying'|'verified'|'failed'|'not_available')} BlockchainStatus
 */
export const BLOCKCHAIN_STATUS = {
  PENDING: 'pending',
  VERIFYING: 'verifying',
  VERIFIED: 'verified',
  FAILED: 'failed',
  NOT_AVAILABLE: 'not_available'
};

/**
 * Heatmap processing status enumeration
 * @typedef {('idle'|'loading'|'processing'|'completed'|'failed')} HeatmapStatus
 */
export const HEATMAP_STATUS = {
  IDLE: 'idle',
  LOADING: 'loading',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed'
};

// ============================================================================
// Confidence Score Types
// ============================================================================

/**
 * Confidence score cache entry
 * @typedef {Object} ConfidenceScoreCacheEntry
 * @property {number} frameNumber - Frame number (0-indexed)
 * @property {number} confidenceScore - Confidence score (0.0-1.0)
 * @property {number} timestamp - Cache timestamp
 * @property {boolean} isProcessed - Whether frame has been processed
 * @property {Array} suspiciousRegions - Suspicious regions for this frame
 */
export const ConfidenceScoreCacheEntry = {
  frameNumber: Number,
  confidenceScore: Number,
  timestamp: Number,
  isProcessed: Boolean,
  suspiciousRegions: Array
};

/**
 * Confidence score cache structure
 * @typedef {Map<number, ConfidenceScoreCacheEntry>} ConfidenceScoreCache
 */
export const ConfidenceScoreCache = Map;

// ============================================================================
// Heatmap Data Types
// ============================================================================

/**
 * Heatmap data point
 * @typedef {Object} HeatmapDataPoint
 * @property {number} x - X coordinate (0-1 normalized)
 * @property {number} y - Y coordinate (0-1 normalized)
 * @property {number} intensity - Heat intensity (0.0-1.0)
 * @property {number} confidence - Detection confidence (0.0-1.0)
 * @property {number} frameNumber - Associated frame number
 * @property {string} regionType - Type of suspicious region
 */
export const HeatmapDataPoint = {
  x: Number,
  y: Number,
  intensity: Number,
  confidence: Number,
  frameNumber: Number,
  regionType: String
};

/**
 * Heatmap dataset
 * @typedef {Object} HeatmapDataset
 * @property {Array<HeatmapDataPoint>} dataPoints - Array of heatmap data points
 * @property {number} frameCount - Total number of frames
 * @property {number} maxIntensity - Maximum intensity value
 * @property {number} minIntensity - Minimum intensity value
 * @property {Object} metadata - Additional metadata
 * @property {number} processingTime - Time taken to process heatmap
 */
export const HeatmapDataset = {
  dataPoints: Array,
  frameCount: Number,
  maxIntensity: Number,
  minIntensity: Number,
  metadata: Object,
  processingTime: Number
};

/**
 * Heatmap processing state
 * @typedef {Object} HeatmapProcessingState
 * @property {string} status - Current processing status
 * @property {number} progress - Processing progress (0-100)
 * @property {HeatmapDataset|null} data - Processed heatmap data
 * @property {Error|null} error - Processing error if any
 * @property {number} lastUpdate - Last update timestamp
 * @property {boolean} isOptimized - Whether data is optimized for performance
 */
export const HeatmapProcessingState = {
  status: String,
  progress: Number,
  data: HeatmapDataset || null,
  error: Error || null,
  lastUpdate: Number,
  isOptimized: Boolean
};

// ============================================================================
// Export State Types
// ============================================================================

/**
 * Export progress information
 * @typedef {Object} ExportProgress
 * @property {string} exportId - Unique export identifier
 * @property {string} status - Current export status
 * @property {number} progress - Export progress (0-100)
 * @property {string} message - Status message
 * @property {string|null} errorMessage - Error message if failed
 * @property {string} estimatedCompletion - Estimated completion time
 * @property {number} fileSize - Export file size in bytes
 * @property {string} fileName - Export file name
 */
export const ExportProgress = {
  exportId: String,
  status: String,
  progress: Number,
  message: String,
  errorMessage: String || null,
  estimatedCompletion: String,
  fileSize: Number,
  fileName: String
};

/**
 * Export history entry
 * @typedef {Object} ExportHistoryEntry
 * @property {string} exportId - Export identifier
 * @property {string} format - Export format used
 * @property {string} status - Final export status
 * @property {Date} createdAt - Creation timestamp
 * @property {Date|null} completedAt - Completion timestamp
 * @property {number} fileSize - File size in bytes
 * @property {string} fileName - File name
 * @property {string} downloadUrl - Download URL if available
 */
export const ExportHistoryEntry = {
  exportId: String,
  format: String,
  status: String,
  createdAt: Date,
  completedAt: Date || null,
  fileSize: Number,
  fileName: String,
  downloadUrl: String
};

/**
 * Export functionality state
 * @typedef {Object} ExportState
 * @property {boolean} isExporting - Whether export is currently in progress
 * @property {ExportProgress|null} currentExport - Current export progress
 * @property {string} selectedFormat - Currently selected export format
 * @property {Array<ExportHistoryEntry>} exportHistory - Export history
 * @property {Object} exportOptions - Current export options
 * @property {boolean} canExport - Whether user can initiate exports
 * @property {number} maxBatchSize - Maximum batch size for exports
 */
export const ExportState = {
  isExporting: Boolean,
  currentExport: ExportProgress || null,
  selectedFormat: String,
  exportHistory: Array,
  exportOptions: Object,
  canExport: Boolean,
  maxBatchSize: Number
};

// ============================================================================
// Blockchain Verification Types
// ============================================================================

/**
 * Blockchain verification details
 * @typedef {Object} BlockchainVerificationDetails
 * @property {string} status - Verification status
 * @property {number} progress - Verification progress (0-100)
 * @property {string|null} transactionHash - Blockchain transaction hash
 * @property {Date|null} verificationTimestamp - Verification completion timestamp
 * @property {string|null} blockNumber - Block number containing transaction
 * @property {number|null} gasUsed - Gas used for verification
 * @property {string|null} networkId - Blockchain network identifier
 * @property {Object|null} metadata - Additional verification metadata
 */
export const BlockchainVerificationDetails = {
  status: String,
  progress: Number,
  transactionHash: String || null,
  verificationTimestamp: Date || null,
  blockNumber: String || null,
  gasUsed: Number || null,
  networkId: String || null,
  metadata: Object || null
};

/**
 * Blockchain verification state
 * @typedef {Object} BlockchainVerificationState
 * @property {BlockchainVerificationDetails} verification - Verification details
 * @property {Date} lastUpdate - Last update timestamp
 * @property {boolean} isRealTime - Whether updates are real-time
 * @property {Array} verificationHistory - History of verification attempts
 * @property {boolean} isEnabled - Whether blockchain verification is enabled
 */
export const BlockchainVerificationState = {
  verification: BlockchainVerificationDetails,
  lastUpdate: Date,
  isRealTime: Boolean,
  verificationHistory: Array,
  isEnabled: Boolean
};

// ============================================================================
// Result Modification Types
// ============================================================================

/**
 * Result modification entry
 * @typedef {Object} ResultModificationEntry
 * @property {string} modificationId - Unique modification identifier
 * @property {string} type - Type of modification
 * @property {Date} timestamp - Modification timestamp
 * @property {Object} previousValue - Previous value before modification
 * @property {Object} newValue - New value after modification
 * @property {string} source - Source of modification (websocket, user, system)
 * @property {Object|null} metadata - Additional modification metadata
 */
export const ResultModificationEntry = {
  modificationId: String,
  type: String,
  timestamp: Date,
  previousValue: Object,
  newValue: Object,
  source: String,
  metadata: Object || null
};

/**
 * Result modification tracking state
 * @typedef {Object} ResultModificationState
 * @property {Array<ResultModificationEntry>} modificationHistory - History of modifications
 * @property {boolean} hasUnseenModifications - Whether there are unseen modifications
 * @property {Date} lastModificationTime - Timestamp of last modification
 * @property {boolean} isTrackingEnabled - Whether modification tracking is enabled
 * @property {number} maxHistorySize - Maximum size of modification history
 */
export const ResultModificationState = {
  modificationHistory: Array,
  hasUnseenModifications: Boolean,
  lastModificationTime: Date,
  isTrackingEnabled: Boolean,
  maxHistorySize: Number
};

// ============================================================================
// Main Visualization State Types
// ============================================================================

/**
 * Visualization options configuration
 * @typedef {Object} VisualizationOptions
 * @property {boolean} enableConfidenceCaching - Enable confidence score caching
 * @property {boolean} enableHeatmapProcessing - Enable heatmap data processing
 * @property {boolean} enableExportTracking - Enable export state tracking
 * @property {boolean} enableBlockchainMonitoring - Enable blockchain verification monitoring
 * @property {boolean} enableModificationTracking - Enable result modification tracking
 * @property {number} cacheSize - Maximum cache size for confidence scores
 * @property {number} heatmapOptimizationThreshold - Threshold for heatmap optimization
 * @property {number} debounceDelay - Debounce delay for real-time updates
 * @property {boolean} enablePerformanceOptimization - Enable performance optimizations
 */
export const VisualizationOptions = {
  enableConfidenceCaching: Boolean,
  enableHeatmapProcessing: Boolean,
  enableExportTracking: Boolean,
  enableBlockchainMonitoring: Boolean,
  enableModificationTracking: Boolean,
  cacheSize: Number,
  heatmapOptimizationThreshold: Number,
  debounceDelay: Number,
  enablePerformanceOptimization: Boolean
};

/**
 * Complete visualization state
 * @typedef {Object} VisualizationState
 * @property {string} currentMode - Current visualization mode
 * @property {ConfidenceScoreCache} confidenceCache - Confidence score cache
 * @property {HeatmapProcessingState} heatmapState - Heatmap processing state
 * @property {ExportState} exportState - Export functionality state
 * @property {BlockchainVerificationState} blockchainState - Blockchain verification state
 * @property {ResultModificationState} modificationState - Result modification tracking
 * @property {boolean} isInitialized - Whether state is initialized
 * @property {Date} lastStateUpdate - Last state update timestamp
 * @property {Object} performanceMetrics - Performance tracking metrics
 * @property {Array} errorHistory - History of errors encountered
 */
export const VisualizationState = {
  currentMode: String,
  confidenceCache: ConfidenceScoreCache,
  heatmapState: HeatmapProcessingState,
  exportState: ExportState,
  blockchainState: BlockchainVerificationState,
  modificationState: ResultModificationState,
  isInitialized: Boolean,
  lastStateUpdate: Date,
  performanceMetrics: Object,
  errorHistory: Array
};

// ============================================================================
// Hook Return Types
// ============================================================================

/**
 * Visualization state management actions
 * @typedef {Object} VisualizationActions
 * @property {Function} setVisualizationMode - Set current visualization mode
 * @property {Function} updateConfidenceCache - Update confidence score cache
 * @property {Function} processHeatmapData - Process heatmap data
 * @property {Function} initiateExport - Initiate export process
 * @property {Function} cancelExport - Cancel current export
 * @property {Function} retryExport - Retry failed export
 * @property {Function} clearExportHistory - Clear export history
 * @property {Function} refreshBlockchainStatus - Refresh blockchain verification status
 * @property {Function} markModificationsSeen - Mark modifications as seen
 * @property {Function} clearModificationHistory - Clear modification history
 * @property {Function} resetVisualizationState - Reset visualization state
 * @property {Function} optimizePerformance - Trigger performance optimization
 */
export const VisualizationActions = {
  setVisualizationMode: Function,
  updateConfidenceCache: Function,
  processHeatmapData: Function,
  initiateExport: Function,
  cancelExport: Function,
  retryExport: Function,
  clearExportHistory: Function,
  refreshBlockchainStatus: Function,
  markModificationsSeen: Function,
  clearModificationHistory: Function,
  resetVisualizationState: Function,
  optimizePerformance: Function
};

/**
 * useResultVisualization hook return value
 * @typedef {Object} UseResultVisualizationReturn
 * @property {VisualizationState} visualizationState - Current visualization state
 * @property {VisualizationActions} actions - Visualization state management actions
 * @property {Object} detectionAnalysis - Core detection analysis state (from useDetectionAnalysis)
 * @property {boolean} isLoading - Whether visualization is loading
 * @property {Error|null} error - Current error if any
 * @property {Object} performanceMetrics - Performance tracking metrics
 * @property {Function} refresh - Refresh all visualization data
 * @property {Function} cleanup - Cleanup function for component unmount
 */
export const UseResultVisualizationReturn = {
  visualizationState: VisualizationState,
  actions: VisualizationActions,
  detectionAnalysis: Object,
  isLoading: Boolean,
  error: Error || null,
  performanceMetrics: Object,
  refresh: Function,
  cleanup: Function
};

// ============================================================================
// Error Types
// ============================================================================

/**
 * Visualization error types
 * @typedef {('cache_error'|'heatmap_error'|'export_error'|'blockchain_error'|'websocket_error'|'performance_error')} VisualizationErrorType
 */
export const VISUALIZATION_ERROR_TYPES = {
  CACHE_ERROR: 'cache_error',
  HEATMAP_ERROR: 'heatmap_error',
  EXPORT_ERROR: 'export_error',
  BLOCKCHAIN_ERROR: 'blockchain_error',
  WEBSOCKET_ERROR: 'websocket_error',
  PERFORMANCE_ERROR: 'performance_error'
};

/**
 * Visualization error structure
 * @typedef {Object} VisualizationError
 * @property {string} type - Error type
 * @property {string} message - Error message
 * @property {Error|null} originalError - Original error object
 * @property {Date} timestamp - Error timestamp
 * @property {Object|null} context - Additional error context
 * @property {boolean} isRecoverable - Whether error is recoverable
 * @property {Function|null} recoveryAction - Recovery action if available
 */
export const VisualizationError = {
  type: String,
  message: String,
  originalError: Error || null,
  timestamp: Date,
  context: Object || null,
  isRecoverable: Boolean,
  recoveryAction: Function || null
};

// ============================================================================
// Performance Metrics Types
// ============================================================================

/**
 * Performance metrics tracking
 * @typedef {Object} PerformanceMetrics
 * @property {number} renderCount - Number of component renders
 * @property {number} stateUpdateCount - Number of state updates
 * @property {number} cacheHitRate - Cache hit rate percentage
 * @property {number} averageRenderTime - Average render time in milliseconds
 * @property {number} memoryUsage - Current memory usage in bytes
 * @property {Array} renderTimes - History of render times
 * @property {Date} lastOptimization - Last performance optimization timestamp
 * @property {Object} optimizationStats - Optimization statistics
 */
export const PerformanceMetrics = {
  renderCount: Number,
  stateUpdateCount: Number,
  cacheHitRate: Number,
  averageRenderTime: Number,
  memoryUsage: Number,
  renderTimes: Array,
  lastOptimization: Date,
  optimizationStats: Object
};

// ============================================================================
// Default Configuration
// ============================================================================

/**
 * Default visualization options
 */
export const DEFAULT_VISUALIZATION_OPTIONS = {
  enableConfidenceCaching: true,
  enableHeatmapProcessing: true,
  enableExportTracking: true,
  enableBlockchainMonitoring: true,
  enableModificationTracking: true,
  cacheSize: 1000,
  heatmapOptimizationThreshold: 10000,
  debounceDelay: 300,
  enablePerformanceOptimization: true
};

/**
 * Default visualization state
 */
export const DEFAULT_VISUALIZATION_STATE = {
  currentMode: VISUALIZATION_MODES.SUMMARY,
  confidenceCache: new Map(),
  heatmapState: {
    status: HEATMAP_STATUS.IDLE,
    progress: 0,
    data: null,
    error: null,
    lastUpdate: Date.now(),
    isOptimized: false
  },
  exportState: {
    isExporting: false,
    currentExport: null,
    selectedFormat: EXPORT_FORMATS.PDF,
    exportHistory: [],
    exportOptions: {},
    canExport: true,
    maxBatchSize: 10
  },
  blockchainState: {
    verification: {
      status: BLOCKCHAIN_STATUS.PENDING,
      progress: 0,
      transactionHash: null,
      verificationTimestamp: null,
      blockNumber: null,
      gasUsed: null,
      networkId: null,
      metadata: null
    },
    lastUpdate: Date.now(),
    isRealTime: true,
    verificationHistory: [],
    isEnabled: true
  },
  modificationState: {
    modificationHistory: [],
    hasUnseenModifications: false,
    lastModificationTime: null,
    isTrackingEnabled: true,
    maxHistorySize: 100
  },
  isInitialized: false,
  lastStateUpdate: Date.now(),
  performanceMetrics: {
    renderCount: 0,
    stateUpdateCount: 0,
    cacheHitRate: 0,
    averageRenderTime: 0,
    memoryUsage: 0,
    renderTimes: [],
    lastOptimization: null,
    optimizationStats: {}
  },
  errorHistory: []
};

// ============================================================================
// Type Guards and Validators
// ============================================================================

/**
 * Type guard for visualization mode
 * @param {any} mode - Value to check
 * @returns {boolean} Whether value is a valid visualization mode
 */
export const isValidVisualizationMode = (mode) => {
  return Object.values(VISUALIZATION_MODES).includes(mode);
};

/**
 * Type guard for export format
 * @param {any} format - Value to check
 * @returns {boolean} Whether value is a valid export format
 */
export const isValidExportFormat = (format) => {
  return Object.values(EXPORT_FORMATS).includes(format);
};

/**
 * Type guard for blockchain status
 * @param {any} status - Value to check
 * @returns {boolean} Whether value is a valid blockchain status
 */
export const isValidBlockchainStatus = (status) => {
  return Object.values(BLOCKCHAIN_STATUS).includes(status);
};

/**
 * Validate visualization options
 * @param {Object} options - Options to validate
 * @returns {Object} Validated options with defaults
 */
export const validateVisualizationOptions = (options = {}) => {
  return {
    ...DEFAULT_VISUALIZATION_OPTIONS,
    ...options,
    // Ensure numeric values are valid
    cacheSize: Math.max(100, Math.min(10000, options.cacheSize || DEFAULT_VISUALIZATION_OPTIONS.cacheSize)),
    heatmapOptimizationThreshold: Math.max(1000, Math.min(100000, options.heatmapOptimizationThreshold || DEFAULT_VISUALIZATION_OPTIONS.heatmapOptimizationThreshold)),
    debounceDelay: Math.max(100, Math.min(1000, options.debounceDelay || DEFAULT_VISUALIZATION_OPTIONS.debounceDelay))
  };
};

// ============================================================================
// Export All Types
// ============================================================================

export default {
  // Enumerations
  VISUALIZATION_MODES,
  EXPORT_FORMATS,
  EXPORT_STATUS,
  BLOCKCHAIN_STATUS,
  HEATMAP_STATUS,
  VISUALIZATION_ERROR_TYPES,
  
  // Type Definitions
  ConfidenceScoreCacheEntry,
  HeatmapDataPoint,
  HeatmapDataset,
  HeatmapProcessingState,
  ExportProgress,
  ExportHistoryEntry,
  ExportState,
  BlockchainVerificationDetails,
  BlockchainVerificationState,
  ResultModificationEntry,
  ResultModificationState,
  VisualizationOptions,
  VisualizationState,
  VisualizationActions,
  UseResultVisualizationReturn,
  VisualizationError,
  PerformanceMetrics,
  
  // Defaults
  DEFAULT_VISUALIZATION_OPTIONS,
  DEFAULT_VISUALIZATION_STATE,
  
  // Validators
  isValidVisualizationMode,
  isValidExportFormat,
  isValidBlockchainStatus,
  validateVisualizationOptions
};
