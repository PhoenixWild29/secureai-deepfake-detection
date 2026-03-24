/**
 * Detection Results Viewer Component
 * Main component for displaying comprehensive analysis results with interactive frame analysis
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import DetectionSummary from './DetectionSummary';
import FrameThumbnailGrid from './FrameThumbnailGrid';
import InteractiveFrameViewer from './InteractiveFrameViewer';
import ConfidenceScoreIndicator from './ConfidenceScoreIndicator';
import BlockchainVerificationDisplay from './BlockchainVerificationDisplay';
import { InteractiveFrameGrid } from '../InteractiveFrameGrid';
import { detectionResultsApi } from '../../api/detectionResultsApi';
import { reportGenerationService } from '../../services/reportService';
import { blockchainService } from '../../services/blockchainService';
import styles from './DetectionResultsViewer.module.css';

// ============================================================================
// Main Component
// ============================================================================

/**
 * DetectionResultsViewer - Main component for displaying detection analysis results
 * @param {Object} props - Component properties
 * @param {string} props.analysisId - Analysis identifier for the results to display
 * @param {Function} props.onExport - Callback when report is exported (optional)
 * @param {Function} props.onError - Callback for error handling (optional)
 * @param {Object} props.options - Configuration options (optional)
 * @param {
 *  boolean: options.showExportButton,
 *  boolean: options.showBlockchainVerification,
 *  boolean: options.enableFrameViewer,
 *  string: options.viewerMode,
 *  number: options.maxThumbnails
 * } props.options - Viewer configuration options
 * @param {string} props.className - Additional CSS classes (optional)
 * @returns {JSX.Element} Detection results viewer component
 */
const DetectionResultsViewer = ({
  analysisId,
  onExport,
  onError,
  options = {},
  className = ''
}) => {
  // ============================================================================
  // Configuration
  // ============================================================================
  
  const defaultOptions = {
    showExportButton: true,
    showBlockchainVerification: true,
    enableFrameViewer: true,
    viewerMode: 'grid', // 'grid', 'detailed', 'summary'
    maxThumbnails: 100,
    thumbnailSize: '200x150',
    frameViewerQuality: 'high',
    autoLoadThumbnails: true,
    enableVirtualization: true,
    enableInteractiveGrid: true, // Enable new InteractiveFrameGrid
    enableKeyboardNavigation: true,
    enableZoomFunctionality: true
  };
  
  const config = { ...defaultOptions, ...options };

  // ============================================================================
  // State Management
  // ============================================================================

  // Core data state
  const [detectionData, setDetectionData] = useState(null);
  const [frameThumbnails, setFrameThumbnails] = useState([]);
  const [loadingState, setLoadingState] = useState({
    analysis: true,
    thumbnails: false,
    blockchain: false,
    export: false
  });
  
  // View state
  const [selectedFrameIndex, setSelectedFrameIndex] = useState(0);
  const [viewerMode, setViewerMode] = useState(config.viewerMode);
  const [viewerFilters, setViewerFilters] = useState({
    showHighConfidenceOnly: false,
    riskLevelFilter: 'all', // 'all', 'low', 'medium', 'high'
    frameRange: null // { start: number, end: number }
  });

  // Interactive frame viewer state
  const [frameViewerSettings, setFrameViewerSettings] = useState({
    zoomLevel: 1.0,
    panPosition: { x: 0, y: 0 },
    showOverlays: true,
    showSuspiciousRegions: true,
    overlayOpacity: 0.7
  });

  // Error state
  const [errorState, setErrorState] = useState({
    hasError: false,
    message: null,
    details: null
  });

  // Refs
  const thumbnailGridRef = useRef(null);
  const frameViewerRef = useRef(null);
  const viewerContainerRef = useRef(null);

  // ============================================================================
  // Data Loading Effects
  // ============================================================================

  // Load main detection data
  useEffect(() => {
    loadDetectionData();
  }, [analysisId]);

  // Load blockchain verification when main data is available
  useEffect(() => {
    if (detectionData && config.showBlockchainVerification) {
      loadBlockchainVerification();
    }
  }, [detectionData, config.showBlockchainVerification]);

  // Load initial thumbnails when main data is available
  useEffect(() => {
    if (detectionData && config.autoLoadThumbnails) {
      loadInitialThumbnails();
    }
  }, [detectionData, config.autoLoadThumbnails]);

  // ============================================================================
  // Data Loading Functions
  // ============================================================================

  /**
   * Load main detection analysis data
   */
  const loadDetectionData = useCallback(async () => {
    if (!analysisId) return;

    setLoadingState(prev => ({ ...prev, analysis: true }));
    setErrorState({ hasError: false, message: null, details: null });

    try {
      const [mainResult, frameData] = await Promise.all([
        detectionResultsApi.getDetectionResult(analysisId),
        detectionResultsApi.getFrameAnalysisData(analysisId)
      ]);

      const detectionResult = {
        ...mainResult,
        frameConfidences: frameData
      };

      setDetectionData(detectionResult);
      
      // Reset frame selection if needed
      if (detectionResult.totalFrames > 0 && selectedFrameIndex >= detectionResult.totalFrames) {
        setSelectedFrameIndex(0);
      }

    } catch (error) {
      console.error('Failed to load detection data:', error);
      setErrorState({
        hasError: true,
        message: 'Failed to load analysis results',
        details: error.message || error
      });
      onError?.(error);
    } finally {
      setLoadingState(prev => ({ ...prev, analysis: false }));
    }
  }, [analysisId, selectedFrameIndex, onError]);

  /**
   * Load initial frame thumbnails
   */
  const loadInitialThumbnails = useCallback(async () => {
    if (!detectionData?.totalFrames) return;

    setLoadingState(prev => ({ ...prev, thumbnails: true }));

    try {
      const maxFrames = Math.min(config.maxThumbnails, detectionData.totalFrames);
      const frameNumbers = Array.from({ length: maxFrames }, (_, i) => i);
      
      const thumbnailPromises = frameNumbers.map(frameNumber => 
        loadFrameThumbnail(frameNumber)
      );

      const thumbnails = await Promise.all(thumbnailPromises);
      setFrameThumbnails(thumbnails.filter(Boolean));

    } catch (error) {
      console.error('Failed to load initial thumbnails:', error);
      setErrorState(prev => ({
        ...prev,
        hasError: true,
        message: 'Failed to load frame thumbnails',
        details: error.message
      }));
    } finally {
      setLoadingState(prev => ({ ...prev, thumbnails: false }));
    }
  }, [detectionData, config.maxThumbnails]);

  /**
   * Load blockchain verification status
   */
  const loadBlockchainVerification = useCallback(async () => {
    setLoadingState(prev => ({ ...prev, blockchain: true }));

    try {
      const verificationStatus = await blockchainService.getVerificationStatus(analysisId);
      
      setDetectionData(prev => ({
        ...prev,
        blockchainVerification: verificationStatus
      }));

    } catch (error) {
      console.error('Failed to load blockchain verification:', error);
      console.warn('Blockchain verification unavailable, continuing without verification data');
    } finally {
      setLoadingState(prev => ({ ...prev, blockchain: false }));
    }
  }, [analysisId]);

  /**
   * Load single frame thumbnail
   */
  const loadFrameThumbnail = useCallback(async (frameNumber) => {
    try {
      const thumbnailData = await detectionResultsApi.getFrameThumbnail(analysisId, frameNumber, {
        quality: 'medium',
        size: config.thumbnailSize
      });

      return {
        frameNumber,
        thumbnailUrl: thumbnailData,
        confidence: detectionData?.confidencePerFrame?.[frameNumber] || 0,
        isSelected: frameNumber === selectedFrameIndex
      };
    } catch (error) {
      console.error(`Failed to load thumbnail for frame ${frameNumber}:`, error);
      return null;
    }
  }, [analysisId, config.thumbnailSize, detectionData?.confidencePerFrame, selectedFrameIndex]);

  // ============================================================================
  // Derived State and Computed Values
  // ============================================================================

  // Filtered thumbnails based on viewer filters
  const filteredThumbnails = useMemo(() => {
    if (!frameThumbnails.length) return [];

    let filtered = [...frameThumbnails];

    // Apply risk level filter
    if (viewerFilters.riskLevelFilter !== 'all') {
      filtered = filtered.filter(thumb => {
        const confidence = thumb.confidence || 0;
        switch (viewerFilters.riskLevelFilter) {
          case 'low': return confidence <= 0.3;
          case 'medium': return confidence > 0.3 && confidence <= 0.7;
          case 'high': return confidence > 0.7;
          default: return true;
        }
      });
    }

    // Apply high confidence filter
    if (viewerFilters.showHighConfidenceOnly) {
      filtered = filtered.filter(thumb => thumb.confidence > 0.5);
    }

    // Apply frame range filter
    if (viewerFilters.frameRange) {
      const { start, end } = viewerFilters.frameRange;
      filtered = filtered.filter(thumb => 
        thumb.frameNumber >= start && thumb.frameNumber <= end
      );
    }

    return filtered;
  }, [frameThumbnails, viewerFilters]);

  // Current frame data for frame viewer
  const currentFrameData = useMemo(() => {
    if (!detectionData || filteredThumbnails.length === 0) return null;

    const selectedThumbnail = filteredThumbnails.find(thumb => thumb.frameNumber === selectedFrameIndex);
    if (!selectedThumbnail) return null;

    return {
      frameNumber: selectedFrameIndex,
      thumbnailUrl: selectedThumbnail.thumbnailUrl,
      confidence: selectedThumbnail.confidence || 0,
      isSelected: true,
      suspiciousRegions: detectionData.suspiciousRegions?.filter(
        region => region.frameNumber === selectedFrameIndex
      ) || []
    };
  }, [detectionData, filteredThumbnails, selectedFrameIndex]);

  // Analysis confidence summary
  const confidenceSummary = useMemo(() => {
    if (!detectionData?.confidencePerFrame) return null;

    const confidences = detectionData.confidencePerFrame;
    const meanConfidence = confidences.reduce((sum, conf) => sum + conf, 0) / confidences.length;
    const maxConfidence = Math.max(...confidences);
    const minConfidence = Math.min(...confidences);

    return {
      overall: detectionData.confidenceScore,
      mean: meanConfidence,
      max: maxConfidence,
      min: minConfidence,
      distribution: {
        lowRisk: confidences.filter(c => c <= 0.3).length,
        mediumRisk: confidences.filter(c => c > 0.3 && c <= 0.7).length,
        highRisk: confidences.filter(c => c > 0.7).length
      }
    };
  }, [detectionData]);

  // ============================================================================
  // Event Handlers
  // ============================================================================

  /**
   * Handle frame selection from thumbnail grid
   */
  const handleFrameSelect = useCallback((frameNumber) => {
    setSelectedFrameIndex(frameNumber);
    
    // Update thumbnails to reflect selection
    setFrameThumbnails(thumbnails => 
      thumbnails.map(thumb => ({
        ...thumb,
        isSelected: thumb.frameNumber === frameNumber
      }));
  }, []);

  /**
   * Handle viewer mode change
   */
  const handleViewerModeChange = useCallback((newMode) => {
    setViewerMode(newMode);
    
    // Reset viewer settings when changing modes
    if (newMode === 'grid') {
      setFrameViewerSettings(prev => ({
        ...prev,
        zoomLevel: 1.0,
        panPosition: { x: 0, y: 0 }
      }));
    }
  }, []);

  /**
   * Handle filter changes
   */
  const handleFilterChange = useCallback((newFilters) => {
    setViewerFilters(prev => ({ ...prev, ...newFilters }));
  }, []);

  /**
   * Handle frame viewer settings change
   */
  const handleFrameViewerSettingsChange = useCallback((newSettings) => {
    setFrameViewerSettings(prev => ({ ...prev, ...newSettings }));
  }, []);

  /**
   * Handle report export
   */
  const handleExportReport = useCallback(async (exportType = 'standard') => {
    if (!detectionData) return;

    setLoadingState(prev => ({ ...prev, export: true }));

    try {
      const exportOptions = {
        format: exportType,
        includeFrameDetails: viewerMode === 'detailed',
        includeSuspiciousRegions: frameViewerSettings.showSuspiciousRegions,
        includeThumbnails: true,
        includeBlockchainVerification: true,
        maxFramesDisplayed: config.maxThumbnails
      };

      const reportResult = await reportGenerationService.generateDetectionReport({
        analysisId,
        options: exportOptions
      });

      // Download the report
      const reportBlob = await reportGenerationService.downloadReport(
        reportResult.reportId,
        reportResult.downloadUrl
      );

      const filename = `detection_report_${analysisId}_${new Date().toISOString().split('T')[0]}.pdf`;
      reportGenerationService.downloadReportFile(reportBlob, filename);

      onExport?.(reportResult);

      // Show success message
      console.log('Report exported successfully');

    } catch (error) {
      console.error('Export failed:', error);
      setErrorState(prev => ({
        ...prev,
        hasError: true,
        message: 'Failed to export report',
        details: error.message
      }));
    } finally {
      setLoadingState(prev => ({ ...prev, export: false }));
    }
  }, [detectionData, viewerMode, frameViewerSettings, config.maxThumbnails, analysisId, onExport]);

  // ============================================================================
  // Render Loading States
  // ============================================================================

  if (loadingState.analysis) {
    return (
      <div className={`${styles.detectionResultsViewer} ${className}`}>
        <div className={styles.loadingContainer}>
          <div className={styles.loadingSpinner} />
          <h3>Loading Analysis Results</h3>
          <p>Please wait while we fetch the detection results...</p>
        </div>
      </div>
    );
  }

  if (errorState.hasError) {
    return (
      <div className={`${styles.detectionResultsViewer} ${className}`}>
        <div className={styles.errorContainer}>
          <div className={styles.errorIcon}>❌</div>
          <h3>Error Loading Results</h3>
          <p>{errorState.message}</p>
          {errorState.details && (
            <details className={styles.errorDetails}>
              <summary>Technical Details</summary>
              <pre>{errorState.details}</pre>
            </details>
          )}
          <button 
            className={styles.retryButton}
            onClick={loadDetectionData}
            disabled={loadingState.analysis}
          >
            Retry Loading
          </button>
        </div>
      </div>
    );
  }

  if (!detectionData) {
    return (
      <div className={`${styles.detectionResultsViewer} ${className}`}>
        <div className={styles.noDataContainer}>
          <h3>No Analysis Data Available</h3>
          <p>The requested analysis could not be found or has not been completed.</p>
        </div>
      </div>
    );
  }

  // ============================================================================
  // Main Render
  // ============================================================================

  return (
    <div className={`${styles.detectionResultsViewer} ${className}`} ref={viewerContainerRef}>
      {/* Header with export controls */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h2>Deepfake Detection Results</h2>
          <div className={styles.analysisInfo}>
            <span className={styles.analysisId}>Analysis ID: {analysisId}</span>
            <span className={styles.frameCount}>Frames: {detectionData.totalFrames}</span>
          </div>
        </div>
        
        <div className={styles.headerRight}>
          <div className={styles.viewerModes}>
            <button 
              className={`${styles.modeButton} ${viewerMode === 'summary' ? styles.active : ''}`}
              onClick={() => handleViewerModeChange('summary')}
            >
              Summary
            </button>
            <button 
              className={`${styles.modeButton} ${viewerMode === 'grid' ? styles.active : ''}`}
              onClick={() => handleViewerModeChange('grid')}
            >
              Frame Grid
            </button>
            <button 
              className={`${styles.modeButton} ${viewerMode === 'detailed' ? styles.active : ''}`}
              onClick={() => handleViewerModeChange('detailed')}
              disabled={!config.enableFrameViewer}
            >
              Detailed View
            </button>
          </div>

          {config.showExportButton && (
            <button 
              className={styles.exportButton}
              onClick={() => handleExportReport()}
              disabled={loadingState.export}
            >
              {loadingState.export ? 'Exporting...' : 'Export Report'}
            </button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className={styles.contentArea}>
        {/* Left Panel - Summary and Controls */}
        <div className={styles.leftPanel}>
          <DetectionSummary 
            analysisData={detectionData}
            confidenceSummary={confidenceSummary}
            className={styles.summarySection}
          />

          {config.showBlockchainVerification && (
            <BlockchainVerificationDisplay
              verificationData={detectionData.blockchainVerification}
              loading={loadingState.blockchain}
              className={styles.blockchainSection}
            />
          )}

          <ConfidenceScoreIndicator
            confidenceScore={detectionData.confidenceScore}
            confidenceSummary={confidenceSummary}
            className={styles.confidenceSection}
          />
        </div>

        {/* Right Panel - Frame Viewer */}
        <div className={styles.rightPanel}>
          {viewerMode === 'summary' && (
            <div className={styles.summaryMode}>
              <h3>Analysis Overview</h3>
              <div className={styles.summaryGrid}>
                <div className={styles.summaryItem}>
                  <label>Overall Result:</label>
                  <span className={detectionData.isFake ? styles.fakeResult : styles.authenticResult}>
                    {detectionData.isFake ? 'Deepfake Detected' : 'Authentic Video'}
                  </span>
                </div>
                <div className={styles.summaryItem}>
                  <label>Confidence Score:</label>
                  <span>{Math.round(detectionData.confidenceScore * 100)}%</span>
                </div>
                <div className={styles.summaryItem}>
                  <label>Processing Time:</label>
                  <span>{detectionData.processingTime.toFixed(2)}s</span>
                </div>
                <div className={styles.summaryItem}>
                  <label>Model Used:</label>
                  <span>{detectionData.modelUsed}</span>
                </div>
              </div>
            </div>
          )}

          {viewerMode === 'grid' && (
            config.enableInteractiveGrid ? (
              <InteractiveFrameGrid
                frames={filteredThumbnails}
                selectedFrameIndex={selectedFrameIndex}
                onFrameSelect={handleFrameSelect}
                onFrameNavigation={(event) => {
                  console.log('Frame navigation:', event);
                  // Handle navigation analytics or logging
                }}
                enableVirtualization={config.enableVirtualization}
                enableKeyboardNavigation={config.enableKeyboardNavigation}
                showDetailedView={config.enableZoomFunctionality}
                maxVisibleFrames={config.maxThumbnails}
                options={{
                  thumbnailSize: 160,
                  colsPerRow: 6,
                  enableSmoothTransitions: true,
                  enableConfidenceIndicators: true,
                  enableSuspiciousRegionOverlays: true,
                  showFrameNumbers: true,
                  showConfidenceScores: true,
                  autoScrollToSelection: true,
                  enableKeyboardShortcuts: true
                }}
                className={styles.interactiveGrid}
              />
            ) : (
              <FrameThumbnailGrid
                ref={thumbnailGridRef}
                thumbnails={filteredThumbnails}
                selectedFrameIndex={selectedFrameIndex}
                onFrameSelect={handleFrameSelect}
                loading={loadingState.thumbnails}
                filters={viewerFilters}
                onFilterChange={handleFilterChange}
                maxThumbnails={config.maxThumbnails}
                enableVirtualization={config.enableVirtualization}
                className={styles.thumbnailGrid}
              />
            )
          )}

          {(viewerMode === 'detailed' || (viewerMode === 'grid' && currentFrameData)) && (
            <InteractiveFrameViewer
              ref={frameViewerRef}
              frameData={currentFrameData}
              settings={frameViewerSettings}
              onSettingsChange={handleFrameViewerSettingsChange}
              loading={loadingState.thumbnails}
              showControls={true}
              className={styles.frameViewer}
            />
          )}
        </div>
      </div>

      {/* Loading Overlays */}
      {loadingState.thumbnails && viewerMode === 'grid' && (
        <div className={styles.loadingOverlay}>
          <div className={styles.loadingSpinner} />
          <span>Loading thumbnails...</span>
        </div>
      )}

      {loadingState.export && (
        <div className={styles.exportOverlay}>
          <div className={styles.loadingSpinner} />
          <span>Generating report...</span>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Export
// ============================================================================

export default DetectionResultsViewer;
