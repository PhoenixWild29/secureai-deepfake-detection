/**
 * ComprehensiveResultsViewer Component
 * Enhanced detection results viewer with multi-mode visualization capabilities
 * 
 * This component extends the Core Detection Engine's DetectionResultsViewer
 * to provide comprehensive analysis views including:
 * - Summary Dashboard Mode: Overall metrics and confidence distributions
 * - Detailed Analysis Mode: Frame-by-frame analysis with interactive heatmaps
 * - Export Preview Mode: Formatted view for export preparation
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { DetectionResultsViewer } from '../DetectionResultsViewer';
import { SummaryDashboardView } from './visualization/SummaryDashboardView';
import { DetailedAnalysisView } from './visualization/DetailedAnalysisView';
import { ExportPreviewMode } from './visualization/ExportPreviewMode';
import { ConfidenceScoreDashboard } from './visualization/ConfidenceScoreDashboard';
import { InteractiveHeatmap } from './visualization/InteractiveHeatmap';
import { detectionResultsService } from './services/detectionResultsService';
import { useWebSocket } from '../hooks/useWebSocket';
import { useDetectionAnalysis } from '../hooks/useDetectionAnalysis';
import styles from './ComprehensiveResultsViewer.module.css';

// ============================================================================
// Constants and Enums
// ============================================================================

/**
 * Visualization modes available in ComprehensiveResultsViewer
 */
export const VISUALIZATION_MODES = {
  SUMMARY_DASHBOARD: 'summary_dashboard',
  DETAILED_ANALYSIS: 'detailed_analysis', 
  EXPORT_PREVIEW: 'export_preview'
};

/**
 * Default configuration options
 */
const DEFAULT_CONFIG = {
  // Core configuration
  showModeToggle: true,
  showConfidenceDashboard: true,
  showInteractiveHeatmap: true,
  showBlockchainStatus: true,
  
  // Performance options
  enableVirtualization: true,
  enableRealTimeUpdates: true,
  enableCaching: true,
  
  // UI options
  defaultMode: VISUALIZATION_MODES.SUMMARY_DASHBOARD,
  animationDuration: 300,
  transitionEasing: 'ease-in-out',
  
  // Data options
  autoRefresh: true,
  refreshInterval: 5000, // milliseconds
  maxRetries: 3,
  
  // Export options
  exportFormats: ['pdf', 'json', 'csv'],
  exportPreviewMode: 'detailed'
};

// ============================================================================
// Main Component
// ============================================================================

/**
 * ComprehensiveResultsViewer - Advanced detection results viewer with multiple visualization modes
 * 
 * @param {Object} props - Component properties
 * @param {string} props.analysisId - Analysis identifier for the results to display
 * @param {string} props.initialMode - Initial visualization mode (default: SUMMARY_DASHBOARD)
 * @param {Object} props.config - Configuration options to override defaults
 * @param {Function} props.onModeChange - Callback when visualization mode changes
 * @param {Function} props.onDataLoad - Callback when detection data is loaded
 * @param {Function} props.onError - Callback for error handling
 * @param {Function} props.onExport - Callback for export actions (optional)
 * @param {string} props.className - Additional CSS classes (optional)
 * @returns {JSX.Element} Comprehensive results viewer component
 */
const ComprehensiveResultsViewer = ({
  analysisId,
  initialMode = VISUALIZATION_MODES.SUMMARY_DASHBOARD,
  config = {},
  onModeChange,
  onDataLoad,
  onError,
  onExport,
  className = ''
}) => {
  
  // ============================================================================
  // Configuration
  // ============================================================================
  
  const mergedConfig = useMemo(() => ({
    ...DEFAULT_CONFIG,
    ...config
  }), [config]);

  // ============================================================================
  // State Management
  // ============================================================================

  // Visualization mode state
  const [visualizationMode, setVisualizationMode] = useState(initialMode);
  const [isTransitioning, setIsTransitioning] = useState(false);
  
  // Detection data state
  const [detectionData, setDetectionData] = useState(null);
  const [frameAnalysisData, setFrameAnalysisData] = useState([]);
  const [heatmapData, setHeatmapData] = useState({});
  const [blockchainStatus, setBlockchainStatus] = useState(null);
  
  // Loading and error states
  const [loadingState, setLoadingState] = useState({
    detection: true,
    frames: false,
    heatmaps: false,
    blockchain: false,
    refreshing: false
  });
  
  const [errorState, setErrorState] = useState({
    hasError: false,
    message: null,
    errorType: null,
    retryCount: 0
  });
  
  // Performance and cache states
  const [cacheStatus, setCacheStatus] = useState({
    hits: 0,
    misses: 0,
    hitRate: 0,
    lastUpdated: null
  });
  
  // UI interaction states
  const [selectedFrameIndex, setSelectedFrameIndex] = useState(0);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panPosition, setPanPosition] = useState({ x: 0, y: 0 });
  const [overlaySettings, setOverlaySettings] = useState({
    showSuspiciousRegions: true,
    showConfidenceOverlay: true,
    opacity: 0.7
  });

  // Refs
  const viewerContainerRef = useRef(null);
  const modeTransitionRef = useRef(null);
  const refreshTimeoutRef = useRef(null);
  
  // ============================================================================
  // WebSocket Integration
  // ============================================================================
  
  // Initialize WebSocket for real-time blockchain updates
  const { 
    connectionState, 
    lastMessage, 
    sendMessage,
    reconnect 
  } = useWebSocket(`${process.env.REACT_APP_WEBSOCKET_URL || 'ws://localhost:8000'}/ws/analysis/${analysisId}`, {
    reconnectAttempts: mergedConfig.maxRetries,
    reconnectInterval: 5000
  });

  // Initialize detection analysis hook
  const detectionAnalysis = useDetectionAnalysis({
    analysisId,
    enableRealTimeUpdates: mergedConfig.enableRealTimeUpdates,
    autoRefresh: mergedConfig.autoRefresh,
    refreshInterval: mergedConfig.refreshInterval
  });

  // ============================================================================
  // Data Loading Effects
  // ============================================================================

  // Load detection data when analysisId changes
  useEffect(() => {
    if (analysisId) {
      loadDetectionData();
    }
  }, [analysisId]);

  // Handle WebSocket blockchain status updates
  useEffect(() => {
    if (lastMessage && lastMessage.type === 'blockchain_status_update') {
      setBlockchainStatus(prevStatus => ({
        ...prevStatus,
        ...lastMessage.data,
        lastUpdated: new Date().toISOString()
      }));
    }
  }, [lastMessage]);

  // Auto-refresh data if enabled
  useEffect(() => {
    if (mergedConfig.autoRefresh && mergedConfig.refreshInterval > 0) {
      refreshTimeoutRef.current = setInterval(() => {
        refreshDetectionData();
      }, mergedConfig.refreshInterval);
      
      return () => {
        if (refreshTimeoutRef.current) {
          clearInterval(refreshTimeoutRef.current);
        }
      };
    }
  }, [mergedConfig.autoRefresh, mergedConfig.refreshInterval]);

  // ============================================================================
  // Data Loading Functions
  // ============================================================================

  /**
   * Load comprehensive detection data
   */
  const loadDetectionData = useCallback(async () => {
    if (!analysisId) return;

    setLoadingState(prev => ({ ...prev, detection: true }));
    setErrorState({ hasError: false, message: null, errorType: null, retryCount: 0 });

    try {
      const startTime = performance.now();
      
      // Load detection results with caching
      const detectionResults = await detectionResultsService.getDetectionResultsWithCache(
        analysisId,
        { enableCache: mergedConfig.enableCaching }
      );
      
      // Load frame analysis data
      const frameData = await detectionResultsService.getFrameAnalysisData(analysisId);
      
      // Load blockchain verification status
      const blockchainData = await detectionResultsService.getBlockchainVerificationStatus(analysisId);
      
      // Update state with loaded data
      setDetectionData(detectionResults);
      setFrameAnalysisData(frameData || []);
      setBlockchainStatus(blockchainData);
      
      // Track cache performance
      const loadTime = performance.now() - startTime;
      setCacheStatus(prev => ({
        ...prev,
        hitRate: loadTime < 100 ? (prev.hits + 1) / (prev.hits + prev.misses + 1) : prev.hitRate,
        lastUpdated: new Date().toISOString()
      }));
      
      setLoadingState(prev => ({ ...prev, detection: false }));
      
      // Notify parent components
      onDataLoad && onDataLoad(detectionResults, frameData, blockchainData);
      
      // Load heatmap data if in detailed analysis mode
      if (visualizationMode === VISUALIZATION_MODES.DETAILED_ANALYSIS) {
        loadHeatmapData(frameData, detectionResults);
        console.log('Heatmap data loading initiated');
      }
      
    } catch (error) {
      handleError('detection_load_failed', error.message, error);
    }
  }, [analysisId, mergedConfig.enableCaching, onDataLoad]);

  /**
   * Load heatmap data for interactive visualization
   */
  const loadHeatmapData = useCallback(async (frameData, detectionResults) => {
    if (!frameData || frameData.length === 0) return;
    
    setLoadingState(prev => ({ ...prev, heatmaps: true }));
    
    try {
      console.log('Loading heatmap data: Starting heatmap visualization integration');
      const heatmapPromises = frameData.slice(0, 10).map(async (frame, index) => {
        try {
          const heatmapResponse = await fetch(
            `/api/v1/results/${analysisId}/heatmap?frame_number=${index}&grid_size=medium&color_scheme=viridis`
          );
          
          if (!heatmapResponse.ok) {
            throw new Error(`Heatmap API request failed: ${heatmapResponse.status}`);
          }
          
          const heatmapData = await heatmapResponse.json();
          console.log(`Heatmap data loaded for frame ${index}:`, heatmapData);
          
          return {
            frameIndex: index,
            frameNumber: frame.frame_number,
            heatmapData: heatmapData.frame_data
          };
        } catch (error) {
          console.warn(`Failed to load heatmap for frame ${index}:`, error.message);
          return null;
        }
      });
      
      const heatmapResults = await Promise.all(heatmapPromises);
      const validHeatmaps = heatmapResults.filter(result => result !== null);
      
      const heatmapMap = {};
      validHeatmaps.forEach(({ frameIndex, frameNumber, heatmapData }) => {
        heatmapMap[frameIndex] = { frameNumber, heatmapData, loadedAt: new Date().toISOString() };
      });
      
      setHeatmapData(heatmapMap);
      console.log(`Heatmap data loaded successfully: ${validHeatmaps.length} frames processed`);
      
      setLoadingState(prev => ({ ...prev, heatmaps: false }));
      
    } catch (error) {
      console.error('Heatmap loading error:', error);
      setLoadingState(prev => ({ ...prev, heatmaps: false }));
      // Don't throw error - heatmaps are enhancement, not core functionality
    }
  }, [analysisId]);

  /**
   * Refresh detection data without full reload
   */
  const refreshDetectionData = useCallback(async () => {
    if (loadingState.refreshing) return;
    
    setLoadingState(prev => ({ ...prev, refreshing: true }));
    
    try {
      // Refresh without full reload
      const refreshedData = await detectionResultsService.refreshDetectionResults(analysisId);
      
      if (refreshedData) {
        setDetectionData(refreshedData);
        setCacheStatus(prev => ({
          ...prev,
          lastUpdated: new Date().toISOString()
        }));
      }
    } catch (error) {
      console.warn('Refresh failed:', error.message);
    } finally {
      setLoadingState(prev => ({ ...prev, refreshing: false }));
    }
  }, [analysisId, loadingState.refreshing]);

  // ============================================================================
  // Mode Management Functions
  // ============================================================================

  /**
   * Change visualization mode with smooth transition
   */
  const changeVisualizationMode = useCallback((newMode) => {
    if (newMode === visualizationMode) return;
    
    setIsTransitioning(true);
    
    // Validate mode
    if (!Object.values(VISUALIZATION_MODES).includes(newMode)) {
      console.warn(`Invalid visualization mode: ${newMode}`);
      setIsTransitioning(false);
      return;
    }
    
    // Update mode
    setVisualizationMode(newMode);
    
    // Notify parent component
    onModeChange && onModeChange(newMode, visualizationMode);
    
    // Load additional data if needed
    if (newMode === VISUALIZATION_MODES.DETAILED_ANALYSIS && Object.keys(heatmapData).length === 0) {
      loadHeatmapData(frameAnalysisData, detectionData);
    }
    
    // Complete transition after animation
    setTimeout(() => {
      setIsTransitioning(false);
    }, mergedConfig.animationDuration);
    
  }, [visualizationMode, onModeChange, mergedConfig.animationDuration, heatmapData, frameAnalysisData, detectionData]);

  // ============================================================================
  // Error Handling
  // ============================================================================

  /**
   * Handle errors with retry logic and user notification
   */
  const handleError = useCallback((errorType, message, originalError) => {
    const retryCount = errorState.retryCount + 1;
    
    setErrorState({
      hasError: true,
      message,
      errorType,
      retryCount
    });
    
    setLoadingState(prev => ({
      detection: false,
      frames: false,
      heatmaps: false,
      blockchain: false,
      refreshing: false
    }));
    
    // Notify parent component
    onError && onError(errorType, message, originalError, retryCount);
    
    // Auto-retry for certain error types
    if (retryCount < mergedConfig.maxRetries && ['network', 'timeout'].includes(errorType)) {
      setTimeout(() => {
        loadDetectionData();
      }, 3000 * retryCount); // Exponential backoff
    }
    
    console.error(`ComprehensiveResultsViewer Error [${errorType}]:`, message, originalError);
  }, [errorState.retryCount, mergedConfig.maxRetries, onError]);

  /**
   * Retry after error
   */
  const retryOperation = useCallback(() => {
    setErrorState({ hasError: false, message: null, errorType: null, retryCount: errorState.retryCount });
    loadDetectionData();
  }, [errorState.retryCount]);

  // ============================================================================
  // Render Functions
  // ============================================================================

  /**
   * Render mode toggle controls
   */
  const renderModeToggle = () => {
    if (!mergedConfig.showModeToggle) return null;
    
    return (
      <div className={styles.modeToggle}>
        <div className={styles.toggleContainer}>
          {Object.entries(VISUALIZATION_MODES).map(([key, mode]) => (
            <button
              key={mode}
              className={`${styles.modeButton} ${visualizationMode === mode ? styles.active : ''}`}
              onClick={() => changeVisualizationMode(mode)}
              disabled={isTransitioning}
              type="button"
            >
              {key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </button>
          ))}
        </div>
        
        {mergedConfig.showBlockchainStatus && blockchainStatus && (
          <div className={styles.blockchainIndicator}>
            <span className={styles.statusLabel}>Blockchain:</span>
            <span className={`${styles.statusValue} ${styles[blockchainStatus.status]}`}>
              {blockchainStatus.status}
            </span>
          </div>
        )}
      </div>
    );
  };

  /**
   * Render loading state
   */
  const renderLoadingState = () => (
    <div className={styles.loadingContainer}>
      <div className={styles.loadingSpinner} />
      <div className={styles.loadingMessage}>
        {loadingState.detection && 'Loading detection results...'}
        {loadingState.frames && 'Loading frame analysis...'}
        {loadingState.heatmaps && 'Loading heatmap data...'}
        {loadingState.blockchain && 'Verifying blockchain status...'}
      </div>
    </div>
  );

  /**
   * Render error state
   */
  const renderErrorState = () => (
    <div className={styles.errorContainer}>
      <div className={styles.errorIcon}>⚠️</div>
      <div className={styles.errorMessage}>{errorState.message}</div>
      <div className={styles.errorActions}>
        <button 
          className={styles.retryButton}
          onClick={retryOperation}
          type="button"
        >
          Retry ({mergedConfig.maxRetries - errorState.retryCount} attempts remaining)
        </button>
      </div>
    </div>
  );

  /**
   * Render visualization mode content
   */
  const renderVisualizationContent = () => {
    const commonProps = {
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
      config: mergedConfig,
      onExport,
      onError
    };

    switch (visualizationMode) {
      case VISUALIZATION_MODES.SUMMARY_DASHBOARD:
        return (
          <SummaryDashboardView
            {...commonProps}
            ConfidenceScoreDashboard={ConfidenceScoreDashboard}
          />
        );
        
      case VISUALIZATION_MODES.DETAILED_ANALYSIS:
        return (
          <DetailedAnalysisView
            {...commonProps}
            DetectionResultsViewer={DetectionResultsViewer}
            InteractiveHeatmap={InteractiveHeatmap}
            ConfidenceScoreDashboard={ConfidenceScoreDashboard}
          />
        );
        
      case VISUALIZATION_MODES.EXPORT_PREVIEW:
        return (
          <ExportPreviewMode
            {...commonProps}
            exportFormats={mergedConfig.exportFormats}
            exportPreviewMode={mergedConfig.exportPreviewMode}
          />
        );
        
      default:
        return renderErrorState();
    }
  };

  // ============================================================================
  // Main Render
  // ============================================================================

  // Show loading state for initial data load
  if (loadingState.detection && !detectionData) {
    return renderLoadingState();
  }

  // Show error state if critical error occurred
  if (errorState.hasError && errorState.errorType === 'critical') {
    return renderErrorState();
  }

  return (
    <div 
      ref={viewerContainerRef}
      className={`${styles.comprehensiveViewer} ${className}`}
    >
      {/* Mode Toggle Header */}
      {renderModeToggle()}
      
      {/* Loading Overlay */}
      {loadingState.detection || loadingState.refreshing ? (
        <div className={styles.loadingOverlay}>
          <div className={styles.loadingSpinner} />
        </div>
      ) : null}
      
      {/* Visualization Content */}
      <div 
        ref={modeTransitionRef}
        className={`${styles.visualizationContent} ${isTransitioning ? styles.transitioning : ''}`}
      >
        {renderVisualizationContent()}
      </div>
      
      {/* Performance Indicator */}
      {process.env.NODE_ENV === 'development' && (
        <div className={styles.debugInfo}>
          <small>
            Cache Hit Rate: {(cacheStatus.hitRate * 100).toFixed(1)}% | 
            Mode: {visualizationMode} | 
            Frames: {frameAnalysisData.length} | 
            Heatmaps: {Object.keys(heatmapData).length}
          </small>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Exports
// ============================================================================

export { VISUALIZATION_MODES };
export default ComprehensiveResultsViewer;
