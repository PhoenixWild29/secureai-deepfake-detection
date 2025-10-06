/**
 * DetailedAnalysisView Component
 * Comprehensive analysis view integrating existing DetectionResultsViewer with interactive heatmaps
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { DetectionResultsViewer } from '../../DetectionResultsViewer';
import { InteractiveHeatmap } from './InteractiveHeatmap';
import { ConfidenceScoreDashboard } from './ConfidenceScoreDashboard';
import styles from './DetailedAnalysisView.module.css';

// ============================================================================
// Main Component
// ============================================================================

/**
 * DetailedAnalysisView - Comprehensive frame-by-frame analysis with interactive heatmaps
 * 
 * @param {Object} props - Component properties
 * @param {string} props.analysisId - Analysis identifier
 * @param {Object} props.detectionData - Main detection results data
 * @param {Array} props.frameAnalysisData - Frame-level analysis data
 * @param {Object} props.heatmapData - Heatmap visualization data
 * @param {Object} props.blockchainStatus - Blockchain verification status
 * @param {Object} props.loadingState - Loading states for different data types
 * @param {number} props.selectedFrameIndex - Currently selected frame index
 * @param {Function} props.setSelectedFrameIndex - Frame selection callback
 * @param {number} props.zoomLevel - Current zoom level
 * @param {Function} props.setZoomLevel - Zoom level callback
 * @param {Object} props.panPosition - Current pan position
 * @param {Function} props.setPanPosition - Pan position callback
 * @param {Object} props.overlaySettings - Overlay display settings
 * @param {Function} props.setOverlaySettings - Overlay settings callback
 * @param {Object} props.config - Configuration options
 * @param {Function} props.onExport - Export callback
 * @param {Function} props.onError - Error callback
 * @param {Component} props.DetectionResultsViewer - Detection results viewer component
 * @param {Component} props.InteractiveHeatmap - Interactive heatmap component
 * @param {Component} props.ConfidenceScoreDashboard - Confidence dashboard component
 * @returns {JSX.Element} Detailed analysis view component
 */
const DetailedAnalysisView = ({
  analysisId,
  detectionData,
  frameAnalysisData,
  heatmapData,
  blockchainStatus,
  loadingState,
  selectedFrameIndex,
  setSelectedFrameIndex,
  zoomLevel,
  setZoomLevel,
  panPosition,
  setPanPosition,
  overlaySettings,
  setOverlaySettings,
  config,
  onExport,
  onError,
  DetectionResultsViewer,
  InteractiveHeatmap,
  ConfidenceScoreDashboard
}) => {
  
  // ============================================================================
  // State Management
  // ============================================================================
  
  const [activePanel, setActivePanel] = useState('frames'); // 'frames', 'heatmap', 'dashboard'
  const [layerMode, setLayerMode] = useState('overlay'); // 'overlay', 'side-by-side', 'split'
  const [heatmapFilters, setHeatmapFilters] = useState({
    confidenceThreshold: 0.7,
    regionType: 'all',
    gridSize: 'medium'
  });

  // Frame navigation state
  const [frameNavigationState, setFrameNavigationState] = useState({
    autoPlay: false,
    playbackSpeed: 1,
    currentFrame: 0,
    totalFrames: 0
  });

  // Interaction state
  const [interactionMode, setInteractionMode] = useState('pan'); // 'pan', 'zoom', 'select'
  const [selectedRegions, setSelectedRegions] = useState([]);
  const [viewerSettings, setViewerSettings] = useState({
    showFrameNumbers: true,
    showTimestamps: true,
    showConfidenceOverlay: true,
    showSuspiciousRegions: true
  });

  // Refs
  const frameViewerRef = useRef({});
  const heatmapContainerRef = useRef({});
  const autoPlayIntervalRef = useRef({});

  // ============================================================================
  // Computed States and Effects
  // ============================================================================

  /**
   * Current frame data with heatmap integration
   */
  const currentFrameData = useMemo(() => {
    if (!frameAnalysisData || frameAnalysisData.length === 0) return null;
    
    const frameData = frameAnalysisData[selectedFrameIndex];
    const heatmapFrameData = heatmapData[selectedFrameIndex];
    
    return {
      ...frameData,
      heatmap: heatmapFrameData,
      hasHeatmapData: !!heatmapFrameData
    };
  }, [frameAnalysisData, selectedFrameIndex, heatmapData]);

  /**
   * Frame navigation state updates
   */
  useEffect(() => {
    if (frameAnalysisData && frameAnalysisData.length > 0) {
      setFrameNavigationState(prev => ({
        ...prev,
        currentFrame: selectedFrameIndex,
        totalFrames: frameAnalysisData.length
      }));
    }
  }, [frameAnalysisData, selectedFrameIndex]);

  /**
   * Auto-play functionality
   */
  useEffect(() => {
    if (frameNavigationState.autoPlay && !loadingState.frames) {
      autoPlayIntervalRef.current = setInterval(() => {
        setSelectedFrameIndex((prevIndex) => {
          const nextIndex = (prevIndex + 1) % frameNavigationState.totalFrames;
          return nextIndex;
        });
      }, 1000 / frameNavigationState.playbackSpeed);
      
      return () => {
        if (autoPlayIntervalRef.current) {
          clearInterval(autoPlayIntervalRef.current);
        }
      };
    }
  }, [frameNavigationState.autoPlay, frameNavigationState.playbackSpeed, frameNavigationState.totalFrames, loadingState.frames]);

  // ============================================================================
  // Interaction Handlers
  // ============================================================================

  /**
   * Handle frame selection in detection viewer
   */
  const handleFrameSelection = useCallback((frameIndex) => {
    setSelectedFrameIndex(frameIndex);
    setActivePanel('frames');
  }, [setSelectedFrameIndex]);

  /**
   * Handle heatmap region interaction
   */
  const handleHeatmapRegionClick = useCallback((regionData) => {
    setSelectedRegions(prev => {
      const exists = prev.some(region => region.region_id === regionData.region_id);
      return exists 
        ? prev.filter(region => region.region_id !== regionData.region_id)
        : [...prev, regionData];
    });
  }, []);

  /**
   * Handle zoom in/out
   */
  const handleZoom = useCallback((direction) => {
    const zoomFactor = direction === 'in' ? 1.25 : 0.8;
    const newZoomLevel = Math.min(Math.max(zoomLevel * zoomFactor, 0.5), 4.0);
    setZoomLevel(newZoomLevel);
  }, [zoomLevel, setZoomLevel]);

  /**
   * Handle pan reset
   */
  const handlePanReset = useCallback(() => {
    setPanPosition({ x: 0, y: 0 });
    setZoomLevel(1);
  }, [setPanPosition, setZoomLevel]);

  /**
   * Toggle auto-play functionality
   */
  const toggleAutoPlay = useCallback(() => {
    setFrameNavigationState(prev => ({
      ...prev,
      autoPlay: !prev.autoPlay
    }));
  }, []);

  // ============================================================================
  // Render Functions
  // ============================================================================

  /**
   * Render panel toggle controls
   */
  const renderPanelToggle = () => {
    const panels = [
      { key: 'frames', label: 'Frame Analysis', icon: '🎬' },
      { key: 'heatmap', label: 'Interactive Heatmap', icon: '🔥' },
      { key: 'dashboard', label: 'Confidence Dashboard', icon: '📊' }
    ];

    return (
      <div className={styles.panelToggle}>
        <div className={styles.panelButtons}>
          {panels.map((panel) => (
            <button
              key={panel.key}
              className={`${styles.panelButton} ${activePanel === panel.key ? styles.active : ''}`}
              onClick={() => setActivePanel(panel.key)}
              type="button"
            >
              <span className={styles.panelIcon}>{panel.icon}</span>
              <span className={styles.panelLabel}>{panel.label}</span>
            </button>
          ))}
        </div>
      </div>
    );
  };

  /**
   * Render frame navigation controls
   */
  const renderFrameNavigationControls = () => (
    <div className={styles.frameNavigationControls}>
      <div className={styles.playbackControls}>
        <button
          className={`${styles.playButton} ${frameNavigationState.autoPlay ? styles.active : ''}`}
          onClick={toggleAutoPlay}
          type="button"
        >
          {frameNavigationState.autoPlay ? '⏸️' : '▶️'}
        </button>
        
        <div className={styles.speedControl}>
          <label>Speed:</label>
          <select
            value={frameNavigationState.playbackSpeed}
            onChange={(e) => setFrameNavigationState(prev => ({
              ...prev,
              playbackSpeed: parseFloat(e.target.value)
            }))}
            className={styles.speedSelect}
          >
            <option value={0.5}>0.5x</option>
            <option value={1}>1x</option>
            <option value={2}>2x</option>
            <option value={4}>4x</option>
          </select>
        </div>
      </div>
      
      <div className={styles.frameCounter}>
        Frame {frameNavigationState.currentFrame + 1} of {frameNavigationState.totalFrames}
      </div>
      
      <div className={styles.viewerControls}>
        <button
          className={styles.viewerButton}
          onClick={() => handleZoom('out')}
          type="button"
          title="Zoom Out"
        >
          ➖
        </button>
        <button
          className={styles.viewerButton}
          onClick={() => handlePanReset()}
          type="button"
          title="Reset View"
        >
          🎯
        </button>
        <button
          className={styles.viewerButton}
          onClick={() => handleZoom('in')}
          type="button"
          title="Zoom In"
        >
          ➕
        </button>
      </div>
    </div>
  );

  /**
   * Render detection results viewer with enhanced integration
   */
  const renderDetectionResultsViewer = () => (
    <div className={styles.detectionResultsContainer}>
      <DetectionResultsViewer
        analysisId={analysisId}
        options={{
          ...config,
          viewerMode: layerMode === 'side-by-side' ? 'grid' : 'detailed',
          showConfidenceOverlay: viewerSettings.showConfidenceOverlay,
          showFrameNumbers: viewerSettings.showFrameNumbers,
          showTimestamps: viewerSettings.showTimestamps,
          enableZoomFunctionality: true,
          enableKeyboardNavigation: true
        }}
        onFrameSelected={handleFrameSelection}
        selectedFrameIndex={selectedFrameIndex}
        overlaySettings={overlaySettings}
        zoomLevel={zoomLevel}
        panPosition={panPosition}
        className={layerMode === 'overlay' ? styles.overlayMode : styles.sideBySideMode}
        onExport={onExport}
        onError={onError}
      />
    </div>
  );

  /**
   * Render interactive heatmap integration
   */
  const renderInteractiveHeatmap = () => {
    if (!currentFrameData || !currentFrameData.hasHeatmapData) {
      return (
        <div className={styles.noHeatmapData}>
          <div className={styles.noHeatmapIcon}>🔥</div>
          <h3>Heatmap Data Not Available</h3>
          <p>No interactive heatmap data found for the current frame. Loading heatmap data...</p>
          {loadingState.heatmaps && (
            <div className={styles.heatmapLoadingIndicator}>
              <div className={styles.loadingSpinner} />
              <span>Generating heatmap data...</span>
            </div>
          )}
        </div>
      );
    }

    return (
      <InteractiveHeatmap
        heatmapData={currentFrameData.heatmap}
        frameData={currentFrameData}
        frameNumber={currentFrameData.frame_number}
        gridSize={heatmapFilters.gridSize}  
        confidenceThreshold={heatmapFilters.confidenceThreshold}
        zoomLevel={zoomLevel}
        panPosition={panPosition}
        onRegionClick={handleHeatmapRegionClick}
        selectedRegions={selectedRegions}
        viewerSettings={viewerSettings}
        className={styles.heatmapContainer}
      />
    );
  };

  /**
   * Render confidence dashboard for detailed analysis
   */
  const renderConfidenceDashboard = () => (
    <div className={styles.confidenceDashboardContainer}>
      <ConfidenceScoreDashboard
        frameData={frameAnalysisData}
        currentFrame={currentFrameData}
        selectedFrameIndex={selectedFrameIndex}
        distribution={// Calculate distribution from frame data
          frameAnalysisData.reduce((acc, frame) => {
            const conf = frame.confidence_score;
            if (conf >= 0.9) acc.critical++;
            else if (conf >= 0.7) acc.high++;
            else if (conf >= 0.4) acc.medium++;
            else acc.low++;
            return acc;
          }, { low: 0, medium: 0, high: 0, critical: 0 })
        }
        animation={!loadingState.frames}
        showDetailed={true}
        height={300}
        interactive={true}
      />
    </div>
  );

  /**
   * Render layer mode controls
   */
  const renderLayerModeControls = () => (
    <div className={styles.layerModeControls}>
      <label>Display Mode:</label>
      <div className={styles.layerModeButtons}>
        {[
          { key: 'overlay', label: 'Overlay', icon: '📖' },
          { key: 'side-by-side', label: 'Side by Side', icon: '📑' },
          { key: 'split', label: 'Split View', icon: '🗂️' }
        ].map((mode) => (
          <button
            key={mode.key}
            className={`${styles.layerModeButton} ${layerMode === mode.key ? styles.active : ''}`}
            onClick={() => setLayerMode(mode.key)}
            type="button"
          >
            <span className={styles.modeIcon}>{mode.icon}</span>
            <span className={styles.modeLabel}>{mode.label}</span>
          </button>
        ))}
      </div>
    </div>
  );

  // ============================================================================
  // Main Render
  // ============================================================================

  if (loadingState.detection) {
    return (
      <div className={styles.loadingState}>
        <div className={styles.loadingSpinner} />
        <p>Loading detailed analysis data...</p>
      </div>
    );
  }

  if (!detectionData || !frameAnalysisData || frameAnalysisData.length === 0) {
    return (
      <div className={styles.errorState}>
        <div className={styles.errorIcon}>🔍</div>
        <h3>No Analysis Data Available</h3>
        <p>Unable to load frame analysis data for detailed inspection.</p>
      </div>
    );
  }

  return (
    <div className={styles.detailedAnalysisView}>
      {/* Header Controls */}
      <div className={styles.headerControls}>
        {renderPanelToggle()}
        {renderLayerModeControls()}
        {renderFrameNavigationControls()}
      </div>

      {/* Main Content Area */}
      <div className={styles.mainContent}>
        {/* Current Active Panel */}
        {activePanel === 'frames' && (
          <div className={`${styles.panelContent} ${layerMode === 'overlay' ? styles.overlayPanel : ''}`}>
            {renderDetectionResultsViewer()}
          </div>
        )}

        {activePanel === 'heatmap' && (
          <div className={styles.panelContent}>
            {renderInteractiveHeatmap()}
          </div>
        )}

        {activePanel === 'dashboard' && (
          <div className={styles.panelContent}>
            {renderConfidenceDashboard()}
          </div>
        )}
      </div>

      {/* Selected Regions Panel */}
      {selectedRegions.length > 0 && (
        <div className={styles.selectedRegionsPanel}>
          <h4>Selected Regions ({selectedRegions.length})</h4>
          <div className={styles.selectedRegionsList}>
            {selectedRegions.map((region, index) => (
              <div key={region.region_id || index} className={styles.selectedRegionItem}>
                <div className={styles.regionInfo}>
                  <span className={styles.regionId}>{region.region_id}</span>
                  <span className={styles.regionCoordinate}>
                    ({region.coordinates?.x}, {region.coordinates?.y})
                  </span>
                </div>
                <div className={styles.regionStats}>
                  <span className={styles.confidence}>{region.confidence}%</span>
                  <button
                    className={styles.removeRegionButton}
                    onClick={() => setSelectedRegions(prev => 
                      prev.filter(r => r.region_id !== region.region_id)
                    )}
                    type="button"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Debug Information */}
      {process.env.NODE_ENV === 'development' && (
        <div className={styles.debugInfo}>
          <small>
            Panel: {activePanel} | Frame: {selectedFrameIndex} | 
            Zoom: {zoomLevel.toFixed(2)}x | 
            Heatmaps: {Object.keys(heatmapData).length} | 
            Regions: {selectedRegions.length}
          </small>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Exports
// ============================================================================

export { DetailedAnalysisView };
export default DetailedAnalysisView;
