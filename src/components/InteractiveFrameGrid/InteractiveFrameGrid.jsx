/**
 * InteractiveFrameGrid Component
 * Main grid component for frame-by-frame navigation with virtualization and advanced interactions
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import FrameThumbnail from './FrameThumbnail';
import DetailedFrameView from './DetailedFrameView';
import {
  parseConfidenceScore,
  calculateOptimalGridLayout,
  calculateNavigationIndex,
  isValidNavigationKey,
  debounceNavigation,
  calculateVisibleRange,
  calculateScrollToFrame,
  sanitizeFrameData,
  generateThumbnailUrl
} from '../../utils/frameUtils';
import styles from './InteractiveFrameGrid.module.css';

// ============================================================================
// Status Constants
// ============================================================================

const STATUS = {
  IDLE: 'idle',
  LOADING: 'loading',
  NAVIGATING: 'navigating',
  ERROR: 'error'
};

// ============================================================================
// Component
// ============================================================================

/**
 * InteractiveFrameGrid - Main interactive grid component for frame navigation
 * @param {Object} props - Component properties
 * @param {Array} props.frames - Array of frame data objects
 * @param {number} props.selectedFrameIndex - Currently selected frame index
 * @param {Function} props.onFrameSelect - Callback when frame is selected
 * @param {Function} props.onFrameNavigation - Callback for navigation events
 * @param {boolean} props.enableVirtualization - Enable virtual scrolling optimization
 * @param {number} props.maxVisibleFrames - Maximum frames visible simultaneously
 * @param {boolean} props.enableKeyboardNavigation - Enable arrow key navigation
 * @param {boolean} props.showDetailedView - Whether to show detailed frame view
 * @param {Object} props.className - CSS classes for styling
 * @param {Object} props.options - Component configuration options
 * @returns {JSX.Element} Interactive frame grid component
 */
const InteractiveFrameGrid = ({
  frames = [],
  selectedFrameIndex = 0,
  onFrameSelect,
  onFrameNavigation,
  enableVirtualization = true,
  maxVisibleFrames = 50,
  enableKeyboardNavigation = true,
  showDetailedView = true,
  className = '',
  options = {}
}) => {
  // ============================================================================
  // Configuration
  // ============================================================================
  
  const defaultOptions = {
    thumbnailSize: 160,
    colsPerRow: 6,
    enableSmoothTransitions: true,
    enableConfidenceIndicators: true,
    enableSuspiciousRegionOverlays: true,
    showFrameNumbers: true,
    showConfidenceScores: true,
    autoScrollToSelection: true,
    navigationDebounceMs: 50,
    loadingTimeoutMs: 200,
    enableKeyboardShortcuts: true
  };

  const config = { ...defaultOptions, ...options };

  // ============================================================================
  // State Management
  // ============================================================================

  const [internalSelectedIndex, setInternalSelectedIndex] = useState(selectedFrameIndex);
  const [navigationState, setNavigationState] = useState({
    isNavigating: false,
    direction: null,
    lastNavigationTime: 0
  });
  const [viewportMetrics, setViewportMetrics] = useState({
    width: 800,
    height: 600,
    visibleRange: { start: 0, end: frames.length }
  });
  const [detailedViewState, setDetailedViewState] = useState({
    zoomLevel: 1.0,
    panPosition: { x: 0, y: 0 },
    showSuspiciousRegions: config.enableSuspiciousRegionOverlays,
    showConfidenceOverlay: config.enableConfidenceIndicators
  });
  const [loadingState, setLoadingState] = useState({
    loadingFrames: new Set(),
    errorFrames: new Set()
  });

  // Refs
  const gridRef = useRef(null);
  const scrollContainerRef = useRef(null);
  const keyboardTimerRef = useRef(null);

  // ============================================================================
  // Data Processing
  // ============================================================================

  const sanitizedFrames = useMemo(() => {
    return frames.map((frame, index) => ({
      ...sanitizeFrameData(frame),
      thumbnailUrl: frame.imageUrl || generateThumbnailUrl(frame.analysisId, frame.frameNumber),
      isCached: frame.isCached !== false, // Default to cached if not specified
      globalIndex: index
    }));
  }, [frames]);

  const currentSelectedFrame = useMemo(() => {
    return sanitizedFrames[internalSelectedIndex] || null;
  }, [sanitizedFrames, internalSelectedIndex]);

  const gridLayout = useMemo(() => {
    return calculateOptimalGridLayout(
      sanitizedFrames.length,
      viewportMetrics.width,
      viewportMetrics.height
    );
  }, [sanitizedFrames.length, viewportMetrics]);

  const visibleFrames = useMemo(() => {
    if (!enableVirtualization) {
      return sanitizedFrames.slice(0, maxVisibleFrames);
    }

    const range = viewportMetrics.visibleRange;
    return sanitizedFrames.slice(range.start, range.end);
  }, [enableVirtualization, sanitizedFrames, maxVisibleFrames, viewportMetrics]);

  // ============================================================================
  // Navigation and Selection Logic
  // ============================================================================

  /**
   * Handle frame selection
   */
  const handleFrameSelect = useCallback((frameData, event) => {
    const frameIndex = sanitizedFrames.findIndex(f => f.frameNumber === frameData.frameNumber);
    
    if (frameIndex >= 0 && frameIndex !== internalSelectedIndex) {
      setInternalSelectedIndex(frameIndex);
      setNavigationState(prev => ({
        ...prev,
        direction: 'none',
        lastNavigationTime: Date.now()
      }));
      
      // Scroll selected frame into view
      if (config.autoScrollToSelection && enableVirtualization) {
        setTimeout(() => scrollToFrame(frameIndex), 0);
      }
      
      onFrameSelect?.(frameData, frameIndex, event);
    }
  }, [sanitizedFrames, internalSelectedIndex, config.autoScrollToSelection, enableVirtualization, onFrameSelect]);

  /**
   * Handle keyboard navigation
   */
  const handleKeyboardNavigation = useCallback((direction) => {
    if (!enableKeyboardNavigation || sanitizedFrames.length === 0) return;

    const newIndex = calculateNavigationIndex(
      internalSelectedIndex,
      direction,
      sanitizedFrames.length,
      config.colsPerRow
    );

    if (newIndex !== internalSelectedIndex) {
      setInternalSelectedIndex(newIndex);
      setNavigationState(prev => ({
        ...prev,
        isNavigating: true,
        direction,
        lastNavigationTime: Date.now()
      }));

      // Trigger navigation event
      onFrameNavigation?.({ 
        direction, 
        fromIndex: internalSelectedIndex, 
        toIndex: newIndex,
        isKeyboardEvent: true 
      });

      // Auto-scroll to selection
      if (config.autoScrollToSelection) {
        setTimeout(() => scrollToFrame(newIndex), 0);
      }
    }
  }, [
    enableKeyboardNavigation, 
    sanitizedFrames.length, 
    internalSelectedIndex, 
    config.colsPerRow, 
    config.autoScrollToSelection, 
    onFrameNavigation
  ]);

  /**
   * Debounced navigation handler
   */
  const debouncedNavigate = useMemo(() => {
    return debounceNavigation(handleKeyboardNavigation, config.navigationDebounceMs);
  }, [handleKeyboardNavigation, config.navigationDebounceMs]);

  /**
   * Handle key press events
   */
  const handleKeyPress = useCallback((event) => {
    if (!config.enableKeyboardShortcuts) return;

    const key = event.key;
    
    // Handle navigation keys
    if (key === 'ArrowLeft' || key === 'ArrowUp' || key === 'a' || key === 'A') {
      event.preventDefault();
      const direction = (key === 'ArrowUp' || key === 'a' || key === 'A') ? 'left' : 'left';
      debouncedNavigate(direction);
    } else if (key === 'ArrowRight' || key === 'ArrowDown' || key === 'd' || key === 'D') {
      event.preventDefault();
      const direction = (key === 'ArrowDown' || key === 'd' || key === 'D') ? 'right' : 'right';
      debouncedNavigate(direction);
    } else if (key === 'Home') {
      event.preventDefault();
      debouncedNavigate('home');
    } else if (key === 'End') {
      event.preventDefault();
      debouncedNavigate('end');
    } else if (key === 'PageUp') {
      event.preventDefault();
      // Jump by several rows
      const jumpBy = config.colsPerRow * 3;
      const newIndex = Math.max(0, internalSelectedIndex - jumpBy);
      handleKeyboardNavigation('up');
    } else if (key === 'PageDown') {
      event.preventDefault();
      // Jump by several rows
      const jumpBy = config.colsPerRow * 3;
      const newIndex = Math.min(sanitizedFrames.length - 1, internalSelectedIndex + jumpBy);
      handleKeyboardNavigation('down');
    }
  }, [config, debouncedNavigate, internalSelectedIndex, sanitizedFrames.length, handleKeyboardNavigation]);

  /**
   * Scroll to specific frame
   */
  const scrollToFrame = useCallback((frameIndex) => {
    if (!enableVirtualization || !scrollContainerRef.current) return;

    const targetScrollTop = calculateScrollToFrame(
      frameIndex,
      config.colsPerRow,
      120, // Row height
      viewportMetrics.height
    );

    scrollContainerRef.current.scrollTo({
      top: targetScrollTop,
      behavior: config.enableSmoothTransitions ? 'smooth' : 'auto'
    });
  }, [enableVirtualization, config.colsPerRow, config.enableSmoothTransitions, viewportMetrics.height]);

  // ============================================================================
  // Viewport and Virtualization Management
  // ============================================================================

  /**
   * Update viewport metrics
   */
  const updateViewportMetrics = useCallback(() => {
    if (!gridRef.current) return;

    const rect = gridRef.current.getBoundingClientRect();
    setViewportMetrics(prev => {
      const newMetrics = {
        width: rect.width,
        height: rect.height,
        visibleRange: calculateVisibleRange(
          0, // scrollTop - will be updated on scroll
          rect.height,
          120, // item height
          5   // buffer size
        )
      };

      return newMetrics;
    });
  }, []);

  /**
   * Handle scroll events for virtualization
   */
  const handleScroll = useCallback((event) => {
    if (!enableVirtualization) return;

    const scrollTop = event.target.scrollTop;
    const range = calculateVisibleRange(scrollTop, viewportMetrics.height, 120, 5);
    
    setViewportMetrics(prev => ({
      ...prev,
      visibleRange: range
    }));
  }, [enableVirtualization, viewportMetrics.height]);

  // ============================================================================
  // Effects
  // ============================================================================

  // Sync with external selected index
  useEffect(() => {
    if (selectedFrameIndex !== internalSelectedIndex) {
      setInternalSelectedIndex(selectedFrameIndex);
    }
  }, [selectedFrameIndex, internalSelectedIndex]);

  // Update viewport metrics on resize
  useEffect(() => {
    updateViewportMetrics();
    
    const handleResize = () => updateViewportMetrics();
    window.addEventListener('resize', handleResize);
    
    return () => window.removeEventListener('resize', handleResize);
  }, [updateViewportMetrics]);

  // Clear navigation state after delay
  useEffect(() => {
    if (navigationState.isNavigating) {
      const timer = setTimeout(() => {
        setNavigationState(prev => ({ ...prev, isNavigating: false }));
      }, 200);
      
      return () => clearTimeout(timer);
    }
  }, [navigationState.isNavigating]);

  // ============================================================================
  // Detailed View Handlers
  // ============================================================================

  /**
   * Handle zoom change in detailed view
   */
  const handleZoomChange = useCallback((zoomLevel) => {
    setDetailedViewState(prev => ({
      ...prev,
      zoomLevel: Math.max(0.25, Math.min(4.0, zoomLevel))
    }));
  }, []);

  /**
   * Handle pan change in detailed view
   */
  const handlePanChange = useCallback((panPosition) => {
    setDetailedViewState(prev => ({
      ...prev,
      panPosition
    }));
  }, []);

  /**
   * Handle suspicious region click
   */
  const handleRegionClick = useCallback((region, frameData, event) => {
    console.log('Suspicious region clicked:', region, frameData);
    // Could emit analytics or detail view updates here
  }, []);

  // ============================================================================
  // Render Helpers
  // ============================================================================

  /**
   * Render grid header with statistics
   */
  const renderGridHeader = () => (
    <div className={styles.gridHeader}>
      <div className={styles.headerInfo}>
        <h3>Frame Analysis Grid</h3>
        <span className={styles.frameCount}>
          {sanitizedFrames.length} frames
          {internalSelectedIndex >= 0 && (
            <span> • Selected: #{sanitizedFrames[internalSelectedIndex]?.frameNumber || 'None'}</span>
          )}
        </span>
      </div>
      
      <div className={styles.headerStats}>
        {sanitizedFrames.length > 0 && (
          <>
            <div className={styles.statItem}>
              <span className={styles.statLabel}>Avg Confidence:</span>
              <span className={styles.statValue}>
                {Math.round((sanitizedFrames.reduce((sum, f) => sum + (f.confidenceScore || 0), 0) / sanitizedFrames.length) * 100)}%
              </span>
            </div>
            
            <div className={styles.statItem}>
              <span className={styles.statLabel}>Risk Distribution:</span>
              <span className={styles.statValue}>
                {sanitizedFrames.filter(f => (f.confidenceScore || 0) >= 0.8).length} Low
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );

  /**
   * Render navigation indicators
   */
  const renderNavigationIndicators = () => (
    <div className={styles.navigationIndicators}>
      {navigationState.isNavigating && (
        <div className={`${styles.navigationPrompt} ${styles[navigationState.direction]}`}>
      {navigationState.direction === 'left' && '←'}
      {navigationState.direction === 'right' && '→'}
      {navigationState.direction === 'up' && '↑'}
      {navigationState.direction === 'down' && '↓'}
        </div>
      )}
      
      <div className={styles.navigationInfo}>
        Use ← → ↑ ↓ keys to navigate
        {showDetailedView && <span> • Double-click frame for details</span>}
      </div>
    </div>
  );

  /**
   * Render frame thumbnails grid
   */
  const renderFrameGrid = () => (
    <div 
      ref={scrollContainerRef}
      className={styles.scrollContainer}
      onScroll={handleScroll}
    >
      <div 
        ref={gridRef}
        className={`${styles.frameGrid} ${enableVirtualization ? styles.virtualized : ''}`}
        onKeyDown={handleKeyPress}
        tabIndex={0}
        role="grid"
        aria-label="Interactive frame grid"
      >
        {visibleFrames.map((frameData, index) => (
          <FrameThumbnail
            key={`${frameData.frameNumber}_${frameData.globalIndex}`}
            frameData={frameData}
            isSelected={frameData.globalIndex === internalSelectedIndex}
            isLoading={loadingState.loadingFrames.has(frameData.globalIndex)}
            onClick={handleFrameSelect}
            onRegionClick={handleRegionClick}
            thumbnailSize={config.thumbnailSize}
            showConfidenceScore={config.showConfidenceScores}
            showFrameNumber={config.showFrameNumbers}
            className={`${styles.frameThumbnail} ${
              frameData.globalIndex === internalSelectedIndex ? styles.selected : ''
            }`}
          />
        ))}
      </div>
    </div>
  );

  /**
   * Render empty state
   */
  const renderEmptyState = () => (
    <div className={styles.emptyState}>
      <div className={styles.emptyIcon}>🎬</div>
      <h3>No Frames Available</h3>
      <p>Upload and process a video to begin frame analysis</p>
    </div>
  );

  // ============================================================================
  // Main Render
  // ============================================================================

  if (sanitizedFrames.length === 0) {
    return (
      <div className={`${styles.interactiveFrameGrid} ${className}`}>
        {renderEmptyState()}
      </div>
    );
  }

  return (
    <div 
      className={`${styles.interactiveFrameGrid} ${className}`}
      onKeyDown={handleKeyPress}
      tabIndex={-1} // Allow keyboard events on the container
    >
      {/* Grid Header */}
      {renderGridHeader()}

      {/* Navigation Indicators */}
      {renderNavigationIndicators()}

      {/* Main Content Area */}
      <div className={styles.gridContent}>
        {/* Frame Grid */}
        <div className={styles.gridSection}>
          {renderFrameGrid()}
        </div>

        {/* Detailed Frame View */}
        {showDetailedView && currentSelectedFrame && (
          <div className={styles.detailedSection}>
            <DetailedFrameView
              frameData={currentSelectedFrame}
              zoomLevel={detailedViewState.zoomLevel}
              onZoomChange={handleZoomChange}
              panPosition={detailedViewState.panPosition}
              onPanChange={handlePanChange}
              showSuspiciousRegions={detailedViewState.showSuspiciousRegions}
              showConfidenceOverlay={detailedViewState.showConfidenceOverlay}
              onRegionClick={handleRegionClick}
              enableMouseWheelZoom={true}
              enableDoubleClickZoom={true}
              className={styles.detailedView}
            />
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// Export
// ============================================================================

export default InteractiveFrameGrid;
