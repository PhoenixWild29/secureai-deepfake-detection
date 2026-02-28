/**
 * Frame Utility Functions
 * Helper functions for confidence scoring, color coding, and frame processing
 */

// ============================================================================
// Constants
// ============================================================================

/**
 * Confidence thresholds for color coding
 * @type {Object}
 */
export const CONFIDENCE_THRESHOLDS = {
  LOW: 0.5,      // < 0.5 = Red (High risk)
  MEDIUM: 0.8,   // 0.5 - 0.8 = Yellow (Medium risk)
  HIGH: 1.0      // > 0.8 = Green (Low risk)
};

/**
 * Default color scheme for confidence indicators
 * @type {Object}
 */
export const CONFIDENCE_COLORS = {
  LOW: '#ef4444',     // Red - High risk
  MEDIUM: '#f59e0b',  // Yellow - Medium risk  
  HIGH: '#10b981',    // Green - Low risk
  BACKGROUND: '#f3f4f6', // Light gray background
  TEXT: '#1f2937'     // Dark text
};

/**
 * Virtualization configuration
 * @type {Object}
 */
export const VIRTUALIZATION_CONFIG = {
  ROW_HEIGHT: 120,
  COL_WIDTH: 160,
  BUFFER_SIZE: 5,
  MAX_VISIBLE_ROWS: 8,
  MAX_VISIBLE_COLS: 6
};

/**
 * Navigation key mappings
 * @type {Object}
 */
export const NAVIGATION_KEYS = {
  LEFT: ['ArrowLeft', 'ArrowUp', 'a', 'A'],
  RIGHT: ['ArrowRight', 'ArrowDown', 'd', 'D'],
  HOME: ['Home'],
  END: ['End'],
  PAGE_UP: ['PageUp'],
  PAGE_DOWN: ['PageDown'],
  ZOOM_IN: ['Equal', '+'],
  ZOOM_OUT: ['Minus', '-'],
  RESET_ZOOM: ['Digit0', '0']
};

// ============================================================================
// Confidence Scoring Functions
// ============================================================================

/**
 * Parse confidence score to risk level and color
 * @param {number} confidenceScore - Confidence score (0.0 - 1.0)
 * @returns {Object} Parsed confidence information
 */
export const parseConfidenceScore = (confidenceScore) => {
  if (typeof confidenceScore !== 'number' || confidenceScore < 0 || confidenceScore > 1) {
    return {
      score: 0,
      riskLevel: 'unknown',
      color: '#6b7280',
      percentage: 0,
      description: 'Invalid confidence score'
    };
  }

  const percentage = Math.round(confidenceScore * 100);
  let riskLevel, color, description;

  if (confidenceScore >= CONFIDENCE_THRESHOLDS.HIGH) {
    riskLevel = 'high';       // Low risk (high confidence = authentic)
    color = CONFIDENCE_COLORS.HIGH;
    description = 'Likely Authentic';
  } else if (confidenceScore >= CONFIDENCE_THRESHOLDS.LOW) {
    riskLevel = 'medium';     // Medium risk
    color = CONFIDENCE_COLORS.MEDIUM;
    description = 'Uncertain';
  } else {
    riskLevel = 'low';        // High risk (low confidence = suspicious)
    color = CONFIDENCE_COLORS.LOW;
    description = 'Likely Suspicious';
  }

  return {
    score: confidenceScore,
    percentage,
    riskLevel,
    color,
    description
  };
};

/**
 * Generate CSS custom properties for confidence styling
 * @param {number} confidenceScore - Confidence score to base styling on
 * @returns {Object} CSS custom properties object
 */
export const generateConfidenceStyles = (confidenceScore) => {
  const confidenceInfo = parseConfidenceScore(confidenceScore);
  
  return {
    '--confidence-color': confidenceInfo.color,
    '--confidence-bg': `${confidenceInfo.color}20`, // 20% opacity
    '--confidence-border': confidenceInfo.color,
    '--confidence-text-color': confidenceInfo.color === CONFIDENCE_COLORS.HIGH ? '#ffffff' : '#000000'
  };
};

/**
 * Calculate confidence distribution across frames
 * @param {Array} frames - Array of frame data with confidence scores
 * @returns {Object} Distribution statistics
 */
export const calculateConfidenceDistribution = (frames) => {
  if (!frames || frames.length === 0) {
    return {
      total: 0,
      average: 0,
      distribution: { low: 0, medium: 0, high: 0 },
      percentages: { low: 0, medium: 0, high: 0 }
    };
  }

  const scores = frames.map(f => f.confidenceScore || 0).filter(score => score >= 0);
  const total = scores.length;
  const average = scores.reduce((sum, score) => sum + score, 0) / total;

  const distribution = {
    low: scores.filter(s => s < CONFIDENCE_THRESHOLDS.LOW).length,
    medium: scores.filter(s => s >= CONFIDENCE_THRESHOLDS.LOW && s < CONFIDENCE_THRESHOLDS.HIGH).length,
    high: scores.filter(s => s >= CONFIDENCE_THRESHOLDS.HIGH).length
  };

  const percentages = {
    low: Math.round((distribution.low / total) * 100),
    medium: Math.round((distribution.medium / total) * 100),
    high: Math.round((distribution.high / total) * 100)
  };

  return {
    total,
    average,
    distribution,
    percentages
  };
};

// ============================================================================
// Frame Processing Functions
// ============================================================================

/**
 * Generate thumbnail URL for frame
 * @param {string} analysisId - Analysis identifier
 * @param {number} frameNumber - Frame number
 * @param {string} size - Thumbnail size ('small', 'medium', 'large')
 * @returns {string} Thumbnail URL
 */
export const generateThumbnailUrl = (analysisId, frameNumber, size = 'medium') => {
  if (!analysisId || frameNumber === undefined) return '';
  
  const sizeMap = {
    small: '80x60',
    medium: '160x120', 
    large: '320x240'
  };
  
  return `/api/results/${analysisId}/frames/${frameNumber}/thumbnail?size=${sizeMap[size]}&quality=med`;
};

/**
 * Calculate optimal grid layout for frames
 * @param {number} totalFrames - Total number of frames
 * @param {number} containerWidth - Container width in pixels
 * @param {number} containerHeight - Container height in pixels
 * @returns {Object} Optimal grid configuration
 */
export const calculateOptimalGridLayout = (totalFrames, containerWidth, containerHeight) => {
  const aspectRatio = containerWidth / containerHeight;
  const frameAspectRatio = 4/3; // Standard video frame aspect ratio
  
  let optimalCols = Math.ceil(Math.sqrt(totalFrames * aspectRatio));
  let optimalRows = Math.ceil(totalFrames / optimalCols);

  // Ensure grid fits within container
  const maxCols = Math.floor(containerWidth / VIRTUALIZATION_CONFIG.COL_WIDTH);
  const maxRows = Math.floor(containerHeight / VIRTUALIZATION_CONFIG.ROW_HEIGHT);
  
  optimalCols = Math.min(optimalCols, maxCols);
  optimalRows = Math.min(optimalRows, maxRows);

  return {
    cols: optimalCols,
    rows: optimalRows,
    totalVisible: optimalCols * optimalRows,
    hasOverflow: totalFrames > (optimalCols * optimalRows)
  };
};

/**
 * Determine if frame should be prioritized for loading
 * @param {Object} frameData - Frame data object
 * @param {number} selectedIndex - Currently selected frame index
 * @param {number} frameIndex - Current frame index
 * @returns {boolean} Whether frame should be priority loaded
 */
export const shouldPriorityLoadFrame = (frameData, selectedIndex, frameIndex) => {
  // Priority load selected frame and nearby frames
  const distance = Math.abs(frameIndex - selectedIndex);
  return distance <= 2 || frameData.confidenceScore < CONFIDENCE_THRESHOLDS.LOW;
};

/**
 * Calculate frame loading order based on priority and proximity
 * @param {Array} frames - Array of frame data
 * @param {number} selectedIndex - Currently selected frame index
 * @returns {Array} Sorted frame indices by loading priority
 */
export const calculateFrameLoadingOrder = (frames, selectedIndex) => {
  return frames
    .map((frame, index) => ({ index, frame, distance: Math.abs(index - selectedIndex) }))
    .sort((a, b) => {
      // Priority 1: Very close frames (distance <= 1)
      if (a.distance <= 1 && b.distance > 1) return -1;
      if (b.distance <= 1 && a.distance > 1) return 1;
      
      // Priority 2: Low confidence frames (suspicious content)
      const aLowConfidence = a.frame.confidenceScore < CONFIDENCE_THRESHOLDS.LOW;
      const bLowConfidence = b.frame.confidenceScore < CONFIDENCE_THRESHOLDS.LOW;
      if (aLowConfidence && !bLowConfidence) return -1;
      if (bLowConfidence && !aLowConfidence) return 1;
      
      // Priority 3: Distance from selection
      return a.distance - b.distance;
    })
    .map(item => item.index);
};

// ============================================================================
// Navigation Functions
// ============================================================================

/**
 * Calculate next frame index based on navigation direction
 * @param {number} currentIndex - Current frame index
 * @param {string} direction - Navigation direction
 * @param {number} totalFrames - Total number of frames
 * @param {number} colsPerRow - Number of columns in grid
 * @returns {number} New frame index
 */
export const calculateNavigationIndex = (currentIndex, direction, totalFrames, colsPerRow = 6) => {
  const maxIndex = totalFrames - 1;
  
  switch (direction) {
    case 'left':
      return Math.max(0, currentIndex - 1);
    case 'right':
      return Math.min(maxIndex, currentIndex + 1);
    case 'up':
      return Math.max(0, currentIndex - colsPerRow);
    case 'down':
      return Math.min(maxIndex, currentIndex + colsPerRow);
    case 'home':
      return 0;
    case 'end':
      return maxIndex;
    default:
      return currentIndex;
  }
};

/**
 * Check if navigation key is valid
 * @param {string} key - Keyboard key pressed
 * @returns {boolean} Whether key is a valid navigation key
 */
export const isValidNavigationKey = (key) => {
  return Object.values(NAVIGATION_KEYS).flat().includes(key);
};

/**
 * Debounce navigation events to prevent excessive calls
 * @param {Function} func - Function to debounce
 * @param {number} delay - Debounce delay in milliseconds
 * @returns {Function} Debounced function
 */
export const debounceNavigation = (func, delay = 100) => {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(null, args), delay);
  };
};

// ============================================================================
// Virtualization Functions
// ============================================================================

/**
 * Calculate visible range for virtual scrolling
 * @param {number} scrollTop - Current scroll position
 * @param {number} containerHeight - Container height
 * @param {number} itemHeight - Height of individual item
 * @param {number} bufferSize - Buffer size for rendering
 * @returns {Object} Visible range {start, end}
 */
export const calculateVisibleRange = (scrollTop, containerHeight, itemHeight, bufferSize = 5) => {
  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - bufferSize);
  const visibleCount = Math.ceil(containerHeight / itemHeight);
  const endIndex = Math.min(startIndex + visibleCount + bufferSize * 2, startIndex + visibleCount + bufferSize * 2);
  
  return { start: startIndex, end: endIndex };
};

/**
 * Calculate scroll position to center frame in viewport
 * @param {number} frameIndex - Frame index to center
 * @param {number} colsPerRow - Number of columns per row
 * @param {number} itemHeight - Height of individual item
 * @param {number} containerHeight - Container height
 * @returns {number} Target scroll position
 */
export const calculateScrollToFrame = (frameIndex, colsPerRow, itemHeight, containerHeight) => {
  const row = Math.floor(frameIndex / colsPerRow);
  const targetScrollTop = row * itemHeight - (containerHeight / 2);
  return Math.max(0, targetScrollTop);
};

// ============================================================================
// Performance Monitoring Functions
// ============================================================================

/**
 * Measure component performance
 * @param {Function} renderFunction - Function to measure
 * @returns {Object} Performance metrics
 */
export const measurePerformance = async (renderFunction) => {
  const startTime = performance.now();
  const startMemory = performance.memory ? performance.memory.usedJSHeapSize : 0;
  
  await renderFunction();
  
  const endTime = performance.now();
  const endMemory = performance.memory ? performance.memory.usedJSHeapSize : 0;
  
  return {
    renderTime: endTime - startTime,
    memoryUsed: (endMemory - startMemory) / 1024 / 1024, // Convert to MB
    timestamp: endTime
  };
};

/**
 * Validate performance thresholds
 * @param {Object} metrics - Performance metrics
 * @returns {Object} Validation results
 */
export const validatePerformanceThresholds = (metrics) => {
  return {
    renderTimeOk: metrics.renderTime <= 16, // 60fps target
    memoryUsageOk: metrics.memoryUsed <= 10, // 10MB threshold
    overallPerformanceOk: metrics.renderTime <= 16 && metrics.memoryUsed <= 10
  };
};

// ============================================================================
// Animation Functions
// ============================================================================

/**
 * Generate smooth interpolation for frame transitions
 * @param {number} startValue - Starting value
 * @param {number} endValue - Ending value
 * @param {number} progress - Progress (0-1)
 * @returns {number} Interpolated value
 */
export const smoothInterpolate = (startValue, endValue, progress) => {
  const easedProgress = 1 - Math.pow(1 - progress, 3); // Cubic ease-out
  return startValue + (endValue - startValue) * easedProgress;
};

/**
 * Generate CSS transform for frame transition
 * @param {number} progress - Animation progress (0-1)
 * @param {string} direction - Direction ('left', 'right')
 * @returns {string} CSS transform value
 */
export const generateFrameTransform = (progress, direction) => {
  const offset = direction === 'left' ? -100 : 100;
  const translateX = offset * (1 - progress);
  
  return `translateX(${translateX}%)`;
};

// ============================================================================
// Data Validation Functions
// ============================================================================

/**
 * Validate frame data object
 * @param {Object} frameData - Frame data to validate
 * @returns {Object} Validation result
 */
export const validateFrameData = (frameData) => {
  const errors = [];
  
  if (!frameData || typeof frameData !== 'object') {
    errors.push('Frame data must be a valid object');
    return { isValid: false, errors };
  }
  
  if (typeof frameData.frameNumber !== 'number' || frameData.frameNumber < 0) {
    errors.push('Frame number must be a non-negative number');
  }
  
  if (typeof frameData.confidenceScore !== 'number' || 
      frameData.confidenceScore < 0 || frameData.confidenceScore > 1) {
    errors.push('Confidence score must be a number between 0 and 1');
  }
  
  if (!frameData.imageUrl || typeof frameData.imageUrl !== 'string') {
    errors.push('Image URL must be a valid string');
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
};

/**
 * Sanitize frame data for display
 * @param {Object} frameData - Raw frame data
 * @returns {Object} Sanitized frame data
 */
export const sanitizeFrameData = (frameData) => {
  return {
    frameNumber: frameData.frameNumber || 0,
    imageUrl: frameData.imageUrl || '',
    confidenceScore: Math.max(0, Math.min(1, frameData.confidenceScore || 0)),
    suspiciousRegions: frameData.suspiciousRegions || [],
    artifacts: frameData.artifacts || {},
    processingTimeMs: frameData.processingTimeMs || 0,
    isCached: Boolean(frameData.isCached),
    timestamp: frameData.timestamp || new Date().toISOString()
  };
};

// ============================================================================
// Export Default Configurations
// ============================================================================

export const DEFAULT_CONFIG = {
  thumbnailSize: 160,
  maxZoomLevel: 4.0,
  zoomStep: 0.25,
  enableKeyboardNavigation: true,
  enableMouseWheelZoom: true,
  enableDoubleClickZoom: true,
  enableTouchGestures: true,
  showFrameNumbers: true,
  showConfidenceScores: true,
  navigationDebounceMs: 100,
  autoScrollToSelection: true,
  loadingIndicatorType: 'spinner'
};
