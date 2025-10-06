/**
 * TypeScript Definition File for Detection Types
 * Defines interfaces and types for InteractiveFrameGrid components
 */

// ============================================================================
// Frame Data Types
// ============================================================================

/**
 * @typedef {Object} FrameData
 * @property {number} frameNumber - Frame number in the video sequence (0-indexed)
 * @property {string} imageUrl - URL or data URI for frame thumbnail image
 * @property {number} confidenceScore - Detection confidence score (0.0 - 1.0)
 * @property {SuspiciousRegion[]} suspiciousRegions - Array of suspicious areas detected
 * @property {Object} artifacts - Additional artifacts detected in frame
 * @property {number} processingTimeMs - Time to process this frame in milliseconds
 * @property {boolean} isCached - Whether frame image is cached or needs loading
 * @property {string} timestamp - ISO timestamp of analysis
 */

/**
 * @typedef {Object} SuspiciousRegion
 * @property {string} id - Unique identifier for the region
 * @property {number} x - X coordinate of top-left corner
 * @property {number} y - Y coordinate of top-left corner
 * @property {number} width - Width of suspicious region
 * @property {number} height - Height of suspicious region
 * @property {number} confidence - Confidence score for this region (0.0 - 1.0)
 * @property {string} regionType - Type of suspicious region ('face', 'background', 'noise', etc.)
 * @property {Object} metadata - Additional metadata for the region
 */

// ============================================================================
// Interactive Grid Types
// ============================================================================

/**
 * @typedef {Object} InteractiveFrameGridProps
 * @property {FrameData[]} frames - Array of frame data to display
 * @property {number} selectedFrameIndex - Currently selected frame index
 * @property {Function} onFrameSelect - Callback when frame is selected
 * @property {Function} onFrameNavigation - Callback for navigation events
 * @property {boolean} enableVirtualization - Enable virtual scrolling optimization
 * @property {number} maxVisibleFrames - Maximum frames visible simultaneously
 * @property {Object} className - CSS classes for styling
 * @property {Object} options - Component configuration options
 */

/**
 * @typedef {Object} FrameThumbnailProps
 * @property {FrameData} frameData - Data for the frame to display
 * @property {boolean} isSelected - Whether this frame is currently selected
 * @property {boolean} isLoading - Whether frame image is currently loading
 * @property {Function} onClick - Callback when thumbnail is clicked
 * @property {Function} onLoad - Callback when image loads successfully
 * @property {Function} onError - Callback when image fails to load
 * @property {number} thumbnailSide - Size of thumbnail in pixels
 */

/**
 * @typedef {Object} DetailedFrameViewProps
 * @property {FrameData} frameData - Data for the frame to display
 * @property {number} zoomLevel - Current zoom level (1.0 = 100%, max 4.0 = 400%)
 * @property {Function} onZoomChange - Callback when zoom level changes
 * @property {boolean} showSuspiciousRegions - Whether to highlight suspicious regions
 * @property {boolean} showConfidenceOverlay - Whether to show confidence overlay
 * @property {Function} onRegionClick - Callback when suspicious region is clicked
 * @property {Object} panPosition - Current pan position {x, y}
 * @property {Function} onPanChange - Callback when pan position changes
 */

// ============================================================================
// Navigation Types
// ============================================================================

/**
 * @typedef {Object} NavigationState
 * @property {number} selectedFrameIndex - Currently selected frame index
 * @property {number} scrollPosition - Current scroll position in grid
 * @property {boolean} isKeyboardNavigating - Whether user is using keyboard navigation
 * @property {number} lastNavigationTime - Timestamp of last navigation action
 * @property {string} navigationDirection - Last direction of navigation ('left', 'right', 'up', 'down')
 */

/**
 * @typedef {Object} ZoomState
 * @property {number} level - Current zoom level (1.0 - 4.0)
 * @property {boolean} isZooming - Whether currently zooming
 * @property {Object} center - Zoom center point {x, y}
 * @property {number} minZoom - Minimum allowed zoom level
 * @property {number} maxZoom - Maximum allowed zoom level
 */

// ============================================================================
// Performance Types
// ============================================================================

/**
 * @typedef {Object} PerformanceMetrics
 * @property {number} renderTime - Time to render component in ms
 * @property {number} imageLoadTime - Average time to load cached images
 * @property {number} navigationLatency - Time for navigation actions in ms
 * @property {number} memoryUsage - Current memory usage in MB
 * @property {number} frameRate - Current frame rate for animations
 */

/**
 * @typedef {Object} VirtualizationConfig
 * @property {number} rowHeight - Height of each grid row in pixels
 * @property {number} colWidth - Width of each grid column in pixels
 * @property {number} bufferSize - Extra items to render outside viewport
 * @property {boolean} enableHorizontalVirtualization - Enable horizontal virtual scrolling
 * @property {boolean} enableVerticalVirtualization - Enable vertical virtual scrolling
 */

// ============================================================================
// Color Coding Types
// ============================================================================

/**
 * @typedef {Object} ConfidenceColorScheme
 * @property {string} low - Color for low confidence (< 0.5)
 * @property {string} medium - Color for medium confidence (0.5 - 0.8)
 * @property {string} high - Color for high confidence (> 0.8)
 * @property {string} background - Background color for score indicators
 * @property {string} text - Text color for score displays
 */

// ============================================================================
// Event Types
// ============================================================================

/**
 * @typedef {Object} FrameSelectEvent
 * @property {number} frameIndex - Index of selected frame
 * @property {FrameData} frameData - Data of selected frame
 * @property {boolean} isKeyboardSelection - Whether selection was via keyboard
 * @property {number} timestamp - Event timestamp
 */

/**
 * @typedef {Object} FrameNavigationEvent
 * @property {string} direction - Navigation direction ('left', 'right', 'up', 'down', 'first', 'last')
 * @property {number} fromIndex - Previous frame index
 * @property {number} toIndex - New frame index
 * @property {boolean} isKeyboardEvent - Whether event originated from keyboard
 * @property {number} timestamp - Event timestamp
 */

/**
 * @typedef {Object} ZoomEvent
 * @property {number} fromLevel - Previous zoom level
 * @property {number} toLevel - New zoom level
 * @property {Object} center - Zoom center point
 * @property {number} timestamp - Event timestamp
 */

// ============================================================================
// Configuration Types
// ============================================================================

/**
 * @typedef {Object} InteractiveFrameGridConfig
 * @property {boolean} enableKeyboardNavigation - Enable arrow key navigation
 * @property {boolean} enableMouseWheelZoom - Enable mouse wheel zoom
 * @property {boolean} enableDoubleClickZoom - Enable double-click to zoom
 * @property {boolean} enableTouchGestures - Enable touch/gesture support
 * @property {number} maxZoomLevel - Maximum zoom level (default 4.0)
 * @property {number} zoomStep - Zoom step size for controls
 * @property {number} navigationDebounceMs - Debounce time for navigation events
 * @property {boolean} autoScrollToSelection - Auto-scroll to keep selection visible
 * @property {number} thumbnailSize - Default thumbnail size in pixels
 * @property {boolean} showFrameNumbers - Whether to display frame numbers
 * @property {boolean} showConfidenceScores - Whether to display confidence scores
 * @property {string} loadingIndicatorType - Type of loading indicator ('spinner', 'skeleton', 'none')
 */

// ============================================================================
// Export schema for documentation
// ============================================================================

/**
 * Export object with all type definitions for reference
 * @type {Object}
 */
export const TypeDefinitions = {
  FrameData: 'Object with frame image, confidence, regions, and metadata',
  SuspiciousRegion: 'Object representing detected suspicious area in frame',
  InteractiveFrameGridProps: 'Props interface for main InteractiveFrameGrid component',
  FrameThumbnailProps: 'Props interface for individual FrameThumbnail component',
  DetailedFrameViewProps: 'Props interface for DetailedFrameView component',
  NavigationState: 'State object for managing frame navigation',
  ZoomState: 'State object for managing zoom functionality',
  PerformanceMetrics: 'Metrics for tracking component performance',
  VirtualizationConfig: 'Configuration for virtualization settings',
  ConfidenceColorScheme: 'Color scheme for confidence score visualization',
  FrameSelectEvent: 'Event data for frame selection',
  FrameNavigationEvent: 'Event data for frame navigation',
  ZoomEvent: 'Event data for zoom actions',
  InteractiveFrameGridConfig: 'Configuration object for component behavior'
};
