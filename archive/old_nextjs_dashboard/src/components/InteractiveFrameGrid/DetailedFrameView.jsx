/**
 * DetailedFrameView Component
 * Detailed view for selected frame with zoom functionality up to 400%
 */

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { parseConfidenceScore, generateConfidenceStyles } from '../../utils/frameUtils';
import styles from './DetailedFrameView.module.css';

// ============================================================================
// Constants
// ============================================================================

const MIN_ZOOM = 0.25;  // 25%
const MAX_ZOOM = 4.0;   // 400%
const DEFAULT_ZOOM = 1.0; // 100%
const ZOOM_STEP = 0.25;
const WHEEL_SENSITIVITY = 0.001;
const DOUBLE_CLICK_ZOOM = 2.0;

const ZOOM_LEVELS = [
  { level: 0.25, label: '25%' },
  { level: 0.5, label: '50%' },
  { level: 0.75, label: '75%' },
  { level: 1.0, label: '100%' },
  { level: 1.25, label: '125%' },
  { level: 1.5, label: '150%' },
  { level: 2.0, label: '200%' },
  { level: 3.0, label: '300%' },
  { level: 4.0, label: '400%' }
];

// ============================================================================
// Component
// ============================================================================

/**
 * DetailedFrameView - Detailed frame view with advanced zoom and inspection capabilities
 * @param {Object} props - Component properties
 * @param {Object} props.frameData - Frame data object
 * @param {number} props.zoomLevel - Current zoom level (1.0 = 100%)
 * @param {Function} props.onZoomChange - Callback when zoom level changes
 * @param {Function} props.onRegionClick - Callback when suspicious region is clicked
 * @param {Object} props.panPosition - Current pan position {x, y}
 * @param {Function} props.onPanChange - Callback when pan position changes
 * @param {boolean} props.showSuspiciousRegions - Whether to highlight suspicious regions
 * @param {boolean} props.showConfidenceOverlay - Whether to show confidence overlay
 * @param {boolean} props.enableMouseWheelZoom - Enable mouse wheel zoom
 * @param {boolean} props.enableDoubleClickZoom - Enable double-click zoom
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Detailed frame view component
 */
const DetailedFrameView = ({
  frameData,
  zoomLevel = DEFAULT_ZOOM,
  onZoomChange,
  onRegionClick,
  panPosition = { x: 0, y: 0 },
  onPanChange,
  showSuspiciousRegions = true,
  showConfidenceOverlay = true,
  enableMouseWheelZoom = true,
  enableDoubleClickZoom = true,
  className = ''
}) => {
  // ============================================================================
  // State Management
  // ============================================================================

  const [isPanning, setIsPanning] = useState(false);
  const [lastPanPoint, setLastPanPoint] = useState({ x: 0, y: 0 });
  const [imageLoaded, setImageLoaded] = useState(false);
  const [zoomCenter, setZoomCenter] = useState({ x: 0, y: 0 });
  const [isZooming, setIsZooming] = useState(false);
  
  // Internal zoom state for smooth transitions
  const [internalZoom, setInternalZoom] = useState(zoomLevel);
  const [zoomDirection, setZoomDirection] = useState(1);

  // Refs
  const containerRef = useRef(null);
  const imageRef = useRef(null);
  const overlayRef = useRef(null);

  // ============================================================================
  // Computed Values
  // ============================================================================

  const confidenceInfo = useMemo(() => {
    return parseConfidenceScore(frameData?.confidenceScore || 0);
  }, [frameData?.confidenceScore]);

  const confidenceStyles = useMemo(() => {
    return generateConfidenceStyles(frameData?.confidenceScore || 0);
  }, [frameData?.confidenceScore]);

  const frameStyle = useMemo(() => ({
    ...confidenceStyles,
    transform: `scale(${internalZoom}) translate(${panPosition.x}px, ${panPosition.y}px)`,
    transformOrigin: `${zoomCenter.x}px ${zoomCenter.y}px`
  }), [internalZoom, panPosition, zoomCenter, confidenceStyles]);

  // ============================================================================
  // Effects
  // ============================================================================

  // Sync internal zoom with prop changes
  useEffect(() => {
    setInternalZoom(zoomLevel);
  }, [zoomLevel]);

  // Auto-fit frame when switching frames
  useEffect(() => {
    if (frameData && imageLoaded) {
      handleZoomToFit();
    }
  }, [frameData?.frameNumber, imageLoaded]);

  // ============================================================================
  // Event Handlers
  // ============================================================================

  /**
   * Handle mouse wheel zoom
   */
  const handleWheel = useCallback((event) => {
    if (!enableMouseWheelZoom) return;

    event.preventDefault();
    
    const delta = event.deltaY * WHEEL_SENSITIVITY;
    const rect = containerRef.current.getBoundingClientRect();
    const centerX = event.clientX - rect.left;
    const centerY = event.clientY - rect.top;
    
    setZoomCenter({ x: centerX, y: centerY });
    setZoomDirection(delta > 0 ? -1 : 1);
    setIsZooming(true);
    
    const newZoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, internalZoom + delta));
    setInternalZoom(newZoom);
    onZoomChange?.(newZoom);
  }, [enableMouseWheelZoom, internalZoom, onZoomChange]);

  /**
   * Handle double-click zoom
   */
  const handleDoubleClick = useCallback((event) => {
    if (!enableDoubleClickZoom) return;

    event.preventDefault();
    
    const rect = containerRef.current.getBoundingClientRect();
    const centerX = event.clientX - rect.left;
    const centerY = event.clientY - rect.top;
    
    setZoomCenter({ x: centerX, y: centerY });
    
    const targetZoom = internalZoom > 1.5 ? DEFAULT_ZOOM : DOUBLE_CLICK_ZOOM;
    setInternalZoom(targetZoom);
    setIsZooming(true);
    onZoomChange?.(targetZoom);
  }, [enableDoubleClickZoom, internalZoom, onZoomChange]);

  /**
   * Handle mouse down for panning
   */
  const handleMouseDown = useCallback((event) => {
    if (event.button !== 0) return;

    event.preventDefault();
    setIsPanning(true);
    setLastPanPoint({ x: event.clientX, y: event.clientY });
    
    // Disable text selection during pan
    document.body.style.userSelect = 'none';
  }, []);

  /**
   * Handle mouse move for panning
   */
  const handleMouseMove = useCallback((event) => {
    if (!isPanning) return;

    event.preventDefault();
    
    const deltaX = event.clientX - lastPanPoint.x;
    const deltaY = event.clientY - lastPanPoint.y;
    
    const newPanX = panPosition.x + deltaX;
    const newPanY = panPosition.y + deltaY;
    
    onPanChange?.({ x: newPanX, y: newPanY });
    setLastPanPoint({ x: event.clientX, y: event.clientY });
  }, [isPanning, lastPanPoint, panPosition, onPanChange]);

  /**
   * Handle mouse up to end panning
   */
  const handleMouseUp = useCallback(() => {
    if (isPanning) {
      setIsPanning(false);
      document.body.style.userSelect = '';
    }
  }, [isPanning]);

  /**
   * Handle keyboard shortcuts
   */
  const handleKeyDown = useCallback((event) => {
    if (!containerRef.current || containerRef.current !== document.activeElement) return;

    switch (event.key) {
      case '+':
      case '=':
        event.preventDefault();
        handleZoomIn();
        break;
      case '-':
        event.preventDefault();
        handleZoomOut();
        break;
      case '0':
        event.preventDefault();
        handleZoomReset();
        break;
      case 'c':
        event.preventDefault();
        handleZoomToFit();
        break;
      case 'ArrowLeft':
      case 'ArrowRight':
      case 'ArrowUp':
      case 'ArrowDown':
        if (internalZoom > 1.0) {
          handlePanWithKeyboard(event);
        }
        break;
    }
  }, [internalZoom]);

  /**
   * Handle zoom in
   */
  const handleZoomIn = useCallback(() => {
    const newZoom = Math.min(MAX_ZOOM, internalZoom + ZOOM_STEP);
    setInternalZoom(newZoom);
    onZoomChange?.(newZoom);
  }, [internalZoom, onZoomChange]);

  /**
   * Handle zoom out
   */
  const handleZoomOut = useCallback(() => {
    const newZoom = Math.max(MIN_ZOOM, internalZoom - ZOOM_STEP);
    setInternalZoom(newZoom);
    onZoomChange?.(newZoom);
  }, [internalZoom, onZoomChange]);

  /**
   * Handle zoom reset
   */
  const handleZoomReset = useCallback(() => {
    setInternalZoom(DEFAULT_ZOOM);
    onZoomChange?.(DEFAULT_ZOOM);
    onPanChange?.({ x: 0, y: 0 });
  }, [onZoomChange, onPanChange]);

  /**
   * Handle zoom to fit
   */
  const handleZoomToFit = useCallback(() => {
    if (!containerRef.current || !imageRef.current) return;

    const containerRect = containerRef.current.getBoundingClientRect();
    const imageRect = imageRef.current.getBoundingClientRect();
    
    const scaleX = (containerRect.width - 40) / imageRect.width; // 20px padding each side
    const scaleY = (containerRect.height - 40) / imageRect.height;
    const zoomToFit = Math.min(scaleX, scaleY);
    
    setInternalZoom(zoomToFit);
    onZoomChange?.(zoomToFit);
    onPanChange?.({ x: 0, y: 0 });
  }, [onZoomChange, onPanChange]);

  /**
   * Handle suspicious region click
   */
  const handleRegionClick = useCallback((region, event) => {
    event.stopPropagation();
    onRegionClick?.(region, frameData, event);
  }, [frameData, onRegionClick]);

  /**
   * Handle pan with keyboard
   */
  const handlePanWithKeyboard = useCallback((event) => {
    const panDistance = 50 / internalZoom; // Pan distance relative to zoom level
    
    let deltaX = 0, deltaY = 0;
    
    switch (event.key) {
      case 'ArrowLeft': deltaX = -panDistance; break;
      case 'ArrowRight': deltaX = panDistance; break;
      case 'ArrowUp': deltaY = -panDistance; break;
      case 'ArrowDown': deltaY = panDistance; break;
    }
    
    if (deltaX !== 0 || deltaY !== 0) {
      onPanChange?.({
        x: panPosition.x + deltaX,
        y: panPosition.y + deltaY
      });
    }
  }, [internalZoom, panPosition, onPanChange]);

  // ============================================================================
  // Render Helpers
  // ============================================================================

  /**
   * Render control panel
   */
  const renderControlPanel = () => (
    <div className={styles.controlPanel}>
      <div className={styles.zoomControls}>
        <button 
          onClick={handleZoomOut}
          disabled={internalZoom <= MIN_ZOOM}
          className={styles.controlButton}
          title="Zoom Out (-)"
        >
          🔍−
        </button>
        
        <span className={styles.zoomIndicator}>
          {Math.round(internalZoom * 100)}%
        </span>
        
        <button 
          onClick={handleZoomIn}
          disabled={internalZoom >= MAX_ZOOM}
          className={styles.controlButton}
          title="Zoom In (+)"
        >
          🔍+
        </button>
      </div>

      <div className={styles.resetControls}>
        <button 
          onClick={handleZoomReset}
          className={styles.controlButton}
          title="Reset Zoom (0)"
        >
          🎯
        </button>
        
        <button 
          onClick={handleZoomToFit}
          className={styles.controlButton}
          title="Zoom to Fit (C)"
        >
          📐
        </button>
      </div>

      <div className={styles.zoomLevels}>
        {ZOOM_LEVELS.map(level => (
          <button
            key={level.level}
            onClick={() => {
              setInternalZoom(level.level);
              onZoomChange?.(level.level);
            }}
            className={`${styles.zoomLevelButton} ${Math.abs(internalZoom - level.level) < 0.1 ? styles.active : ''}`}
            title={`${level.label} zoom`}
          >
            {level.label}
          </button>
        ))}
      </div>
    </div>
  );

  /**
   * Render confidence information
   */
  const renderConfidenceInfo = () => {
    if (!showConfidenceOverlay || !frameData) return null;

    return (
      <div className={styles.confidenceInfo}>
        <div className={styles.confidenceDetails}>
          <span className={styles.frameLabel}>Frame {frameData.frameNumber}</span>
          <span className={`${styles.confidenceScore} ${styles[confidenceInfo.riskLevel]}`}>
            {confidenceInfo.description}: {confidenceInfo.percentage}%
          </span>
        </div>
      </div>
    );
  };

  /**
   * Render frame image with overlay
   */
  const renderFrameImage = () => {
    if (!frameData?.imageUrl) {
      return (
        <div className={styles.noImagePlaceholder}>
          <div className={styles.placeholderIcon}>🖼️</div>
          <span>No frame image available</span>
        </div>
      );
    }

    return (
      <div className={styles.imageContainer} ref={overlayRef}>
        <img
          ref={imageRef}
          src={frameData.imageUrl}
          alt={`Frame ${frameData.frameNumber || 0}`}
          className={`${styles.frameImage} ${imageLoaded ? styles.loaded : ''}`}
          onLoad={() => setImageLoaded(true)}
          draggable={false}
        />

        {/* Suspicious Regions Overlay */}
        {showSuspiciousRegions && frameData.suspiciousRegions?.length > 0 && (
          <div className={styles.suspiciousRegionsOverlay}>
            {frameData.suspiciousRegions.map((region, index) => (
              <div
                key={region.id || index}
                className={styles.suspiciousRegionMarker}
                style={{
                  left: `${region.x}px`,
                  top: `${region.y}px`,
                  width: `${region.width}px`,
                  height: `${region.height}px`,
                  borderColor: confidenceInfo.color
                }}
                onClick={(e) => handleRegionClick(region, e)}
                title={`Suspicious Region ${index + 1}: ${Math.round((region.confidence || 0) * 100)}% confidence`}
              >
                <div className={styles.regionLabel}>
                  {index + 1}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  /**
   * Render frame statistics
   */
  const renderFrameStatistics = () => {
    if (!frameData) return null;

    return (
      <div className={styles.frameStatistics}>
        <div className={styles.statItem}>
          <label>Confidence Score:</label>
          <span>{confidenceInfo.percentage}%</span>
        </div>
        
        {frameData.suspiciousRegions?.length > 0 && (
          <div className={styles.statItem}>
            <label>Suspicious Regions:</label>
            <span>{frameData.suspiciousRegions.length}</span>
          </div>
        )}
        
        {frameData.processingTimeMs && (
          <div className={styles.statItem}>
            <label>Processing Time:</label>
            <span>{frameData.processingTimeMs}ms</span>
          </div>
        )}
        
        <div className={styles.statItem}>
          <label>Risk Level:</label>
          <span className={`${styles.riskLevel} ${styles[confidenceInfo.riskLevel]}`}>
            {confidenceInfo.description}
          </span>
        </div>
      </div>
    );
  };

  /**
   * Render keyboard shortcuts help
   */
  const renderKeyboardShortcuts = () => (
    <div className={styles.keyboardShortcuts}>
      <details>
        <summary>Keyboard Shortcuts</summary>
        <div className={styles.shortcutsList}>
          <div><kbd>+ / -</kbd> Zoom In/Out</div>
          <div><kbd>0</kbd> Reset Zoom</div>
          <div><kbd>C</kbd> Zoom to Fit</div>
          <div><kbd>Arrow Keys</kbd> Pan when zoomed</div>
          <div><kbd>Double-click</kbd> Quick zoom</div>
          <div><kbd>Mouse Wheel</kbd> Zoom</div>
        </div>
      </details>
    </div>
  );

  // ============================================================================
  // Main Render
  // ============================================================================

  if (!frameData) {
    return (
      <div className={`${styles.detailedFrameView} ${className}`}>
        <div className={styles.noFrameSelected}>
          <div className={styles.noFrameIcon}>🔍</div>
          <h3>No Frame Selected</h3>
          <p>Select a frame from the grid to view detailed analysis</p>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className={`${styles.detailedFrameView} ${className} ${isPanning ? styles.panning : ''}`}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onDoubleClick={handleDoubleClick}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="img"
      aria-label={`Detailed view of frame ${frameData.frameNumber}`}
    >
      {/* Control Panel */}
      {renderControlPanel()}

      {/* Confidence Information */}
      {renderConfidenceInfo()}

      {/* Frame Image with Overlays */}
      <div className={styles.frameViewport}>
        <div 
          className={styles.frameContainer}
          style={frameStyle}
        >
          {renderFrameImage()}
        </div>
      </div>

      {/* Frame Statistics */}
      {renderFrameStatistics()}

      {/* Keyboard Shortcuts Help */}
      {renderKeyboardShortcuts()}
    </div>
  );
};

// ============================================================================
// Export
// ============================================================================

export default DetailedFrameView;
