/**
 * InteractiveFrameViewer Component
 * Provides interactive image manipulation (zoom, pan, toggle overlays) for frame inspection
 */

import React, { useState, useEffect, useCallback, useRef, forwardRef, useMemo } from 'react';
import { createFrameViewerUrl } from '../../api/detectionResultsApi';
import { formatSuspiciousRegion } from '../../api/detectionResultsApi';
import styles from './InteractiveFrameViewer.module.css';

// ============================================================================
// Constants
// ============================================================================

const ZOOM_LEVELS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0];
const MIN_ZOOM = ZOOM_LEVELS[0];
const MAX_ZOOM = ZOOM_LEVELS[ZOOM_LEVELS.length - 1];
const DEFAULT_ZOOM = 1.0;
const ZOOM_STEP = 0.25;

const PAN_SENSITIVITY = 1.5;
const WHEEL_SENSITIVITY = 0.1;

// Touch/mouse interaction states
const INTERACTION_STATES = {
  NONE: 'none',
  PANNING: 'panning',
  ZOOMING: 'zooming'
};

// ============================================================================
// Component
// ============================================================================

/**
 * InteractiveFrameViewer - Interactive frame viewer with zoom, pan, and overlay controls
 * @param {Object} props - Component properties
 * @param {Object} props.frameData - Frame data object
 * @param {Object} props.settings - Viewer settings
 * @param {Function} props.onSettingsChange - Settings change callback
 * @param {boolean} props.loading - Loading state
 * @param {boolean} props.showControls - Show control buttons
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Interactive frame viewer component
 */
const InteractiveFrameViewer = forwardRef(({
  frameData,
  settings = {},
  onSettingsChange,
  loading = false,
  showControls = true,
  className = ''
}, ref) => {
  // ============================================================================
  // State Management
  // ============================================================================

  const [currentZoom, setCurrentZoom] = useState(DEFAULT_ZOOM);
  const [panPosition, setPanPosition] = useState({ x: 0, y: 0 });
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [interactionState, setInteractionState] = useState(INTERACTION_STATES.NONE);
  const [lastPointerPos, setLastPointerPos] = useState({ x: 0, y: 0 });
  
  // Settings with defaults
  const [viewerSettings, setViewerSettings] = useState({
    showOverlays: true,
    showSuspiciousRegions: true,
    overlayOpacity: 0.7,
    ...settings
  });

  // Refs
  const containerRef = useRef(null);
  const imageRef = useRef(null);
  const overlaysRef = useRef(null);
  const scrollTimeoutRef = useRef(null);

  // Combine props ref with internal ref
  React.useImperativeHandle(ref, () => ({
    ...containerRef.current,
    resetView: handleResetView,
    zoomToFit: handleZoomToFit,
    setZoomLevel: handleZoomChange
  }));

  // ============================================================================
  // Frame Data Processing
  // ============================================================================

  const processedFrameData = useMemo(() => {
    if (!frameData) return null;

    const suspiciousRegions = frameData.suspiciousRegions?.map(formatSuspiciousRegion) || [];
    const confidence = frameData.confidence || 0;
    
    return {
      ...frameData,
      suspiciousRegions,
      confidenceLevel: confidence <= 0.3 ? 'low' : confidence <= 0.7 ? 'medium' : 'high',
      regionCount: suspiciousRegions.length
    };
  }, [frameData]);

  // ============================================================================
  // Effects
  // ============================================================================

  // Initialize zoom and pan on frame change
  useEffect(() => {
    if (processedFrameData) {
      setCurrentZoom(DEFAULT_ZOOM);
      setPanPosition({ x: 0, y: 0 });
      setImageLoaded(false);
      setImageError(false);
    }
  }, [processedFrameData?.frameNumber]);

  // ============================================================================
  // Event Handlers
  // ============================================================================

  /**
   * Handle wheel zoom
   */
  const handleWheel = useCallback((event) => {
    if (!processedFrameData || loading) return;

    event.preventDefault();
    
    const delta = event.deltaY * -WHEEL_SENSITIVITY;
    const rect = containerRef.current.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;
    
    // Calculate zoom center relative to image center
    const imageRect = imageRef.current?.getBoundingClientRect();
    if (!imageRect) return;
    
    const imageCenterX = imageRect.left + imageRect.width / 2;
    const imageCenterY = imageRect.top + imageRect.height / 2;
    const zoomCenterX = mouseX - imageCenterX;
    const zoomCenterY = mouseY - imageCenterY;
    
    // Apply zoom
    const newZoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, currentZoom + delta));
    const zoomFactor = newZoom / currentZoom;
    
    // Adjust pan to maintain zoom center
    const newPanX = (panPosition.x - zoomCenterX) * zoomFactor + zoomCenterX + panPosition.x * (1 - zoomFactor);
    const newPanY = (panPosition.y - zoomCenterY) * zoomFactor + zoomCenterY + panPosition.y * (1 - zoomFactor);
    
    setCurrentZoom(newZoom);
    setPanPosition({ x: newPanX, y: newPanY });
  }, [processedFrameData, loading, currentZoom, panPosition]);

  /**
   * Handle pointer down for panning
   */
  const handlePointerDown = useCallback((event) => {
    if (!processedFrameData || loading || event.button !== 0) return;

    event.preventDefault();
    setInteractionState(INTERACTION_STATES.PANNING);
    
    const rect = containerRef.current.getBoundingClientRect();
    setLastPointerPos({ x: event.clientX, y: event.clientY });
  }, [processedFrameData, loading]);

  /**
   * Handle pointer move for panning
   */
  const handlePointerMove = useCallback((event) => {
    if (interactionState !== INTERACTION_STATES.PANNING) return;

    event.preventDefault();
    
    const deltaX = (event.clientX - lastPointerPos.x) * PAN_SENSITIVITY;
    const deltaY = (event.clientY - lastPointerPos.y) * PAN_SENSITIVITY;
    
    setPanPosition(prev => ({
      x: prev.x + deltaX,
      y: prev.y + deltaY
    }));
    
    setLastPointerPos({ x: event.clientX, y: event.clientY });
  }, [interactionState, lastPointerPos]);

  /**
   * Handle pointer up to end panning
   */
  const handlePointerUp = useCallback(() => {
    if (interactionState === INTERACTION_STATES.PANNING) {
      setInteractionState(INTERACTION_STATES.NONE);
    }
  }, [interactionState]);

  /**
   * Handle keyboard shortcuts
   */
  const handleKeyDown = useCallback((event) => {
    if (!processedFrameData || loading) return;

    switch (event.key) {
      case '+':
      case '=':
        event.preventDefault();
        handleZoomChange(Math.min(MAX_ZOOM, currentZoom + ZOOM_STEP));
        break;
      case '-':
        event.preventDefault();
        handleZoomChange(Math.max(MIN_ZOOM, currentZoom - ZOOM_STEP));
        break;
      case '0':
        event.preventDefault();
        handleResetView();
        break;
      case 'f':
        event.preventDefault();
        handleZoomToFit();
        break;
      case 'o':
        event.preventDefault();
        toggleOverlays();
        break;
      case 'r':
        event.preventDefault();
        toggleSuspiciousRegions();
        break;
    }
  }, [processedFrameData, loading, currentZoom]);

  // ============================================================================
  // Control Functions
  // ============================================================================

  /**
   * Handle zoom change
   */
  const handleZoomChange = useCallback((newZoom) => {
    setCurrentZoom(Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, newZoom)));
  }, []);

  /**
   * Handle settings change
   */
  const handleSettingsChange = useCallback((newSettings) => {
    const updatedSettings = { ...viewerSettings, ...newSettings };
    setViewerSettings(updatedSettings);
    onSettingsChange?.(updatedSettings);
  }, [viewerSettings, onSettingsChange]);

  /**
   * Reset view to default
   */
  const handleResetView = useCallback(() => {
    setCurrentZoom(DEFAULT_ZOOM);
    setPanPosition({ x: 0, y: 0 });
  }, []);

  /**
   * Zoom to fit image in container
   */
  const handleZoomToFit = useCallback(() => {
    if (!containerRef.current || !imageRef.current) return;
    
    const containerRect = containerRef.current.getBoundingClientRect();
    const imageRect = imageRef.current.getBoundingClientRect();
    
    const scaleX = containerRect.width / imageRect.width;
    const scaleY = containerRect.height / imageRect.height;
    const scale = Math.min(scaleX, scaleY) * 0.9; // 90% to add some padding
    
    setCurrentZoom(DEFAULT_ZOOM * scale);
    setPanPosition({ x: 0, y: 0 });
  }, []);

  /**
   * Toggle overlays visibility
   */
  const toggleOverlays = useCallback(() => {
    handleSettingsChange({ showOverlays: !viewerSettings.showOverlays });
  }, [viewerSettings.showOverlays, handleSettingsChange]);

  /**
   * Toggle suspicious regions visibility
   */
  const toggleSuspiciousRegions = useCallback(() => {
    handleSettingsChange({ showSuspiciousRegions: !viewerSettings.showSuspiciousRegions });
  }, [viewerSettings.showSuspiciousRegions, handleSettingsChange]);

  // ============================================================================
  // Render Helpers
  // ============================================================================

  /**
   * Render suspicious regions overlay
   */
  const renderSuspiciousRegions = () => {
    if (!processedFrameData?.suspiciousRegions?.length || !viewerSettings.showSuspiciousRegions) {
      return null;
    }

    return (
      <div 
        ref={overlaysRef}
        className={styles.suspiciousRegions}
        style={{ opacity: viewerSettings.overlayOpacity }}
      >
        {processedFrameData.suspiciousRegions.map((region, index) => (
          <div
            key={`${region.id || index}`}
            className={styles.suspiciousRegion}
            style={{
              left: `${region.x}px`,
              top: `${region.y}px`,
              width: `${region.width}px`,
              height: `${region.height}px`
            }}
            title={`Region ${index + 1}: ${Math.round(region.confidence * 100)}% confidence`}
          />
        ))}
      </div>
    );
  };

  /**
   * Render frame information overlay
   */
  const renderFrameInfo = () => {
    if (!processedFrameData) return null;

    return (
      <div className={styles.frameInfoOverlay}>
        <div className={styles.frameInfoItem}>
          <label>Frame:</label>
          <span>{processedFrameData.frameNumber}</span>
        </div>
        <div className={styles.frameInfoItem}>
          <label>Confidence:</label>
          <span className={`${styles.confidenceLevel} ${styles[processedFrameData.confidenceLevel]}`}>
            {Math.round(processedFrameData.confidence * 100)}%
          </span>
        </div>
        {processedFrameData.regionCount > 0 && (
          <div className={styles.frameInfoItem}>
            <label>Suspicious Regions:</label>
            <span>{processedFrameData.regionCount}</span>
          </div>
        )}
      </div>
    );
  };

  /**
   * Render control buttons
   */
  const renderControlButtons = () => {
    if (!showControls) return null;

    return (
      <div className={styles.controlButtons}>
        <button
          onClick={() => handleZoomChange(currentZoom - ZOOM_STEP)}
          disabled={currentZoom <= MIN_ZOOM}
          className={styles.controlButton}
          title="Zoom Out"
        >
          🔍-
        </button>
        
        <button
          onClick={handleResetView}
          className={styles.controlButton}
          title="Reset View"
        >
          🎯
        </button>
        
        <button
          onClick={() => handleZoomChange(currentZoom + ZOOM_STEP)}
          disabled={currentZoom >= MAX_ZOOM}
          className={styles.controlButton}
          title="Zoom In"
        >
          🔍+
        </button>
        
        <button
          onClick={handleZoomToFit}
          className={styles.controlButton}
          title="Fit to Screen"
        >
          📐
        </button>
        
        <div className={styles.controlSeparator} />
        
        <button
          onClick={toggleOverlays}
          className={`${styles.controlButton} ${viewerSettings.showOverlays ? styles.active : ''}`}
          title="Toggle Overlays"
        >
          {viewerSettings.showOverlays ? '👁️' : '👁️‍🗨️'}
        </button>
        
        <button
          onClick={toggleSuspiciousRegions}
          className={`${styles.controlButton} ${viewerSettings.showSuspiciousRegions ? styles.active : ''}`}
          title="Toggle Suspicious Regions"
        >
          {viewerSettings.showSuspiciousRegions ? '🚩' : '🚩'}
        </button>
      </div>
    );
  };

  /**
   * Render keyboard shortcuts info
   */
  const renderKeyboardShortcuts = () => (
    <div className={styles.keyboardShortcuts}>
      <h4>Shortcuts:</h4>
      <div className={styles.shortcutsList}>
        <span>+/−: Zoom</span>
        <span>0: Reset</span>
        <span>F: Fit</span>
        <span>O: Overlays</span>
        <span>R: Regions</span>
      </div>
    </div>
  );

  // ============================================================================
  // Main Render
  // ============================================================================

  if (!processedFrameData) {
    return (
      <div className={`${styles.interactiveFrameViewer} ${className}`}>
        <div className={styles.noFrameSelected}>
          <div className={styles.noFrameIcon}>🖼️</div>
          <h3>No Frame Selected</h3>
          <p>Select a frame from the grid to view details</p>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className={`${styles.interactiveFrameViewer} ${className}`}
      onWheel={handleWheel}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="img"
      aria-label={`Frame ${processedFrameData.frameNumber} viewer`}
    >
      {/* Loading State */}
      {loading && (
        <div className={styles.loadingOverlay}>
          <div className={styles.loadingSpinner} />
          <span>Loading frame...</span>
        </div>
      )}

      {/* Error State */}
      {imageError && (
        <div className={styles.errorOverlay}>
          <div className={styles.errorIcon}>❌</div>
          <span>Failed to load frame image</span>
        </div>
      )}

      {/* Main Image */}
      <div 
        className={styles.imageContainer}
        style={{
          transform: `scale(${currentZoom}) translate(${panPosition.x}px, ${panPosition.y}px)`,
          transformOrigin: 'center'
        }}
      >
        <img
          ref={imageRef}
          src={createFrameViewerUrl(
            processedFrameData.analysisId,
            processedFrameData.frameNumber,
            'high'
          )}
          alt={`Frame ${processedFrameData.frameNumber}`}
          className={styles.frameImage}
          onLoad={() => setImageLoaded(true)}
          onError={() => setImageError(true)}
          style={{
            opacity: imageLoaded ? 1 : 0
          }}
        />

        {/* Suspicious Regions Overlay */}
        {renderSuspiciousRegions()}
      </div>

      {/* Frame Information */}
      {renderFrameInfo()}

      {/* Control Buttons */}
      {renderControlButtons()}

      {/* Keyboard Shortcuts Info */}
      {renderKeyboardShortcuts()}

      {/* Zoom Indicator */}
      <div className={styles.zoomIndicator}>
        {Math.round(currentZoom * 100)}%
      </div>
    </div>
  );
});

// ============================================================================
// Display Name
// ============================================================================

InteractiveFrameViewer.displayName = 'InteractiveFrameViewer';

// ============================================================================
// Export
// ============================================================================

export default InteractiveFrameViewer;
