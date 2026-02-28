/**
 * FrameProgressVisualization Component
 * Real-time visualization for frame-level processing updates during video analysis
 * Extends Core Detection Engine progress tracking with interactive frame displays
 */

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import styles from './FrameProgressVisualization.css';

// ============================================================================
// Constants
// ============================================================================

const FRAME_UPDATE_THROTTLE_MS = 100; // 100ms response time requirement
const MAX_THUMBNAILS_DISPLAY = 50; // Performance optimization
const HEATMAP_COLORS = {
  low: '#10b981',    // Green
  medium: '#f59e0b', // Yellow
  high: '#ef4444'     // Red
};

const CONFIDENCE_THRESHOLDS = {
  low: 0.3,
  medium: 0.7
};

// ============================================================================
// Component
// ============================================================================

/**
 * FrameProgressVisualization - Real-time frame analysis visualization
 * @param {Object} props - Component properties
 * @param {string} props.analysisId - Analysis identifier
 * @param {string} props.websocketUrl - WebSocket URL for real-time updates
 * @param {Function} props.onFrameUpdate - Callback for frame updates (optional)
 * @param {Object} props.options - Configuration options (optional)
 * @returns {JSX.Element} Frame progress visualization component
 */
const FrameProgressVisualization = ({
  analysisId,
  websocketUrl = 'ws://localhost:8000/ws',
  onFrameUpdate,
  options = {}
}) => {
  // ============================================================================
  // Configuration
  // ============================================================================
  
  const config = {
    maxThumbnails: MAX_THUMBNAILS_DISPLAY,
    enableHeatmaps: true,
    enableConfidenceOverlays: true,
    enableSmoothAnimations: true,
    showFrameNumbers: true,
    showSuspiciousRegions: true,
    ...options
  };

  // ============================================================================
  // State Management
  // ============================================================================

  const [frameData, setFrameData] = useState([]);
  const [currentProcessingFrame, setCurrentProcessingFrame] = useState(0);
  const [totalFrames, setTotalFrames] = useState(0);
  const [processingRate, setProcessingRate] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdateTime, setLastUpdateTime] = useState(Date.now());
  const [heatmapData, setHeatmapData] = useState(new Map());
  
  // WebSocket state
  const [wsError, setWsError] = useState(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  // Refs
  const wsRef = useRef(null);
  const updateTimeoutRef = useRef(null);
  const thumbsContainerRef = useRef(null);
  const frameStatsCache = useRef(new Map());

  // ============================================================================
  // WebSocket Connection Management
  // ============================================================================

  /**
   * Initialize WebSocket connection for real-time frame updates
   */
  const initializeWebSocket = useCallback(() => {
    if (!analysisId) return;

    const wsUrl = `${websocketUrl}/frame-progress/${analysisId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('FrameProgressWebSocket connected');
      setIsConnected(true);
      setWsError(null);
      setReconnectAttempts(0);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleFrameUpdate(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('FrameProgressWebSocket error:', error);
      setWsError(error);
      setIsConnected(false);
    };

    ws.onclose = () => {
      console.log('FrameProgressWebSocket disconnected');
      setIsConnected(false);
      
      // Attempt reconnection if not manually closed
      if (reconnectAttempts < 3) {
        setTimeout(() => {
          setReconnectAttempts(prev => prev + 1);
          initializeWebSocket();
        }, 2000 * Math.pow(2, reconnectAttempts)); // Exponential backoff
      }
    };

    wsRef.current = ws;
  }, [analysisId, websocketUrl, reconnectAttempts]);

  /**
   * Handle incoming frame update data
   * @param {Object} data - Frame update data
   */
  const handleFrameUpdate = useCallback((data) => {
    const now = Date.now();
    
    // Throttle updates to meet 100ms requirement
    if (updateTimeoutRef.current) {
      clearTimeout(updateTimeoutRef.current);
    }

    updateTimeoutRef.current = setTimeout(() => {
      processFrameUpdate(data, now);
    }, FRAME_UPDATE_THROTTLE_MS);
  }, []);

  /**
   * Process frame update with throttling
   * @param {Object} data - Frame update data
   * @param {number} timestamp - Update timestamp
   */
  const processFrameUpdate = useCallback((data, timestamp) => {
    setLastUpdateTime(timestamp);

    // Update processing metrics
    if (data.frame_number !== undefined) {
      setCurrentProcessingFrame(data.frame_number);
    }

    if (data.total_frames !== undefined) {
      setTotalFrames(data.total_frames);
    }

    if (data.processing_rate !== undefined) {
      setProcessingRate(data.processing_rate);
    }

    // Process frame analysis data
    if (data.frame_analysis) {
      const frameAnalysis = data.frame_analysis;
      
        // Update frame data array
        setFrameData(prev => {
        const updated = [...prev];
        const existingIndex = updated.findIndex(f => f.frame_number === frameAnalysis.frame_number);
        
        const frameInfo = {
          frame_number: frameAnalysis.frame_number,
          confidence_score: frameAnalysis.confidence_score || 0,
          suspicious_regions: frameAnalysis.suspicious_regions || [],
          artifacts: frameAnalysis.artifacts || [],
          processing_time_ms: frameAnalysis.processing_time_ms || 0,
          thumbnail_url: frameAnalysis.thumbnail_url,
          updated_at: timestamp
        };

        if (existingIndex >= 0) {
          updated[existingIndex] = frameInfo;
        } else {
          updated.push(frameInfo);
          // Keep only recent frames for performance
          if (updated.length > config.maxThumbnails) {
            updated.splice(0, updated.length - config.maxThumbnails);
          }
        }

        // Sort by frame number
        updated.sort((a, b) => a.frame_number - b.frame_number);
        
        return updated;
      });

      // Update heatmap data for suspicious regions
      if (frameAnalysis.suspicious_regions?.length > 0) {
        setHeatmapData(prev => {
          const updated = new Map(prev);
          frameAnalysis.suspicious_regions.forEach(region => {
            updated.set(`${frameAnalysis.frame_number}_${region.id}`, {
              ...region,
              timestamp,
              confidence: frameAnalysis.confidence_score
            });
          });
          return updated;
        });
      }

      // Callback for external components
      onFrameUpdate?.(frameAnalysis);
    }
  }, [config.maxThumbnails, onFrameUpdate]);

  // ============================================================================
  // WebSocket Connection Effects
  // ============================================================================

  useEffect(() => {
    if (analysisId) {
      initializeWebSocket();
    }

    return () => {
      if (updateTimeoutRef.current) {
        clearTimeout(updateTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [analysisId, initializeWebSocket]);

  // ============================================================================
  // Render Helpers
  // ============================================================================

  /**
   * Render confidence score overlay
   */
  const renderConfidenceOverlay = useCallback((frameData) => {
    if (!config.enableConfidenceOverlays) return null;

    const confidence = frameData.confidence_score || 0;
    const percentage = Math.round(confidence * 100);
    
    let color = HEATMAP_COLORS.high;
    if (confidence <= CONFIDENCE_THRESHOLDS.low) {
      color = HEATMAP_COLORS.low;
    } else if (confidence <= CONFIDENCE_THRESHOLDS.medium) {
      color = HEATMAP_COLORS.medium;
    }

    return (
      <div 
        className={styles.confidenceOverlay}
        style={{ 
          backgroundColor: `${color}20`,
          borderColor: color
        }}
      >
        <span className={styles.confidenceScore}>
          {percentage}%
        </span>
        <div 
          className={styles.confidenceBar}
          style={{ 
            width: `${percentage}%`,
            backgroundColor: color
          }}
        />
      </div>
    );
  }, [config.enableConfidenceOverlays]);

  /**
   * Render suspicious regions heatmap
   */
  const renderSuspiciousRegions = useCallback((regions) => {
    if (!regions?.length || !config.showSuspiciousRegions) return null;

    return (
      <div className={styles.suspiciousRegions}>
        {regions.map((region, index) => {
          const confidence = region.confidence || 0;
          let color = HEATMAP_COLORS.high;
          if (confidence <= CONFIDENCE_THRESHOLDS.low) {
            color = HEATMAP_COLORS.low;
          } else if (confidence <= CONFIDENCE_THRESHOLDS.medium) {
            color = HEATMAP_COLORS.medium;
          }

          return (
            <div
              key={region.id || index}
              className={styles.suspiciousRegion}
              style={{
                left: `${region.x || 0}px`,
                top: `${region.y || 0}px`,
                width: `${region.width || 20}px`,
                height: `${region.height || 20}px`,
                backgroundColor: `${color}60`,
                border: `2px solid ${color}`
              }}
              title={`Suspicious Region ${index + 1}: ${Math.round(confidence * 100)}% confidence`}
            />
          );
        })}
      </div>
    );
  }, [config.showSuspiciousRegions]);

  /**
   * Render individual frame thumbnail
   */
  const renderFrameThumbnail = useCallback((frame) => {
    const isProcessing = frame.frame_number === currentProcessingFrame;
    const animatedClass = `${config.enableSmoothAnimations ? styles.animated : ''} ${isProcessing ? styles.currentlyProcessing : ''}`;
    
    return (
      <div 
        key={frame.frame_number}
        className={`${styles.frameThumbnail} ${animatedClass}`}
        data-frame-number={frame.frame_number}
      >
        {/* Frame Thumbnail */}
        {frame.thumbnail_url ? (
          <img 
            src={frame.thumbnail_url}
            alt={`Frame ${frame.frame_number}`}
            className={styles.thumbnailImage}
            loading="lazy"
          />
        ) : (
          <div className={styles.thumbnailPlaceholder}>
            <span className={styles.frameNumberLabel}>
              {frame.frame_number}
            </span>
          </div>
        )}

        {/* Confidence Overlay */}
        {renderConfidenceOverlay(frame)}

        {/* Suspicious Regions */}
        {renderSuspiciousRegions(frame.suspicious_regions)}

        {/* Frame Number */}
        {config.showFrameNumbers && (
          <div className={styles.frameIndicator}>
            <span className={styles.frameNumberText}>
              {frame.frame_number}
            </span>
          </div>
        )}

        {/* Processing Indicator */}
        {isProcessing && (
          <div className={styles.processingIndicator}>
            <div className={styles.processingSpinner} />
          </div>
        )}
      </div>
    );
  }, [currentProcessingFrame, config, renderConfidenceOverlay, renderSuspiciousRegions]);

  /**
   * Render processing statistics
   */
  const renderProcessingStats = useCallback(() => (
    <div className={styles.processingStats}>
      <div className={styles.statItem}>
        <label>Current Frame:</label>
        <span>{currentProcessingFrame}</span>
      </div>
      
      <div className={styles.statItem}>
        <label>Total Frames:</label>
        <span>{totalFrames}</span>
      </div>
      
      <div className={styles.statItem}>
        <label>Progress:</label>
        <span>{totalFrames > 0 ? Math.round((currentProcessingFrame / totalFrames) * 100) : 0}%</span>
      </div>
      
      <div className={styles.statItem}>
        <label>Processing Rate:</label>
        <span>{processingRate.toFixed(1)} fps</span>
      </div>
      
      <div className={styles.statItem}>
        <label>Connection:</label>
        <span className={`${styles.connectionStatus} ${isConnected ? styles.connected : styles.disconnected}`}>
          {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
        </span>
      </div>
    </div>
  ), [currentProcessingFrame, totalFrames, processingRate, isConnected]);

  /**
   * Render progress bar
   */
  const renderProgressBar = useCallback(() => {
    const progressPercentage = totalFrames > 0 ? (currentProcessingFrame / totalFrames) * 100 : 0;
    
    return (
      <div className={styles.progressContainer}>
        <div className={styles.progressBar}>
          <div 
            className={styles.progressFill}
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
        <span className={styles.progressText}>
          {Math.round(progressPercentage)}% Complete
        </span>
      </div>
    );
  }, [currentProcessingFrame, totalFrames]);

  // ============================================================================
  // Memoized Computed Values
  // ============================================================================

  // Recent frames for efficient rendering
  const recentFrames = useMemo(() => {
    return frameData.slice(-config.maxThumbnails);
  }, [frameData, config.maxThumbnails]);

  // Average confidence score
  const averageConfidence = useMemo(() => {
    if (frameData.length === 0) return 0;
    
    const totalConfidence = frameData.reduce((sum, frame) => sum + (frame.confidence_score || 0), 0);
    return totalConfidence / frameData.length;
  }, [frameData]);

  // ============================================================================
  // Main Render
  // ============================================================================

  return (
    <div className={styles.frameProgressVisualization}>
      {/* Header with Stats */}
      <div className={styles.header}>
        <h3>Real-Time Frame Analysis</h3>
        {renderProcessingStats()}
      </div>

      {/* Progress Bar */}
      {renderProgressBar()}

      {/* Frame Thumbnails Grid */}
      <div 
        ref={thumbsContainerRef}
        className={styles.thumbnailsContainer}
      >
        {recentFrames.length > 0 ? (
          <div className={styles.thumbnailsGrid}>
            {recentFrames.map(renderFrameThumbnail)}
          </div>
        ) : (
          <div className={styles.noFramesMessage}>
            <div className={styles.noFramesIcon}>🎬</div>
            <p>Waiting for frame processing to begin...</p>
          </div>
        )}
      </div>

      {/* Connection Status */}
      {wsError && (
        <div className={styles.connectionError}>
          <span className={styles.errorIcon}>⚠️</span>
          <span>Connection error: {wsError.message}</span>
          {reconnectAttempts > 0 && (
            <span className={styles.reconnectInfo}>
            (Reconnecting... {reconnectAttempts}/3)
            </span>
          )}
        </div>
      )}

      {/* Summary Stats */}
      <div className={styles.summaryStats}>
        <div className={styles.summaryItem}>
          <label>Frames Analyzed:</label>
          <span>{frameData.length}</span>
        </div>
        
        <div className={styles.summaryItem}>
          <label>Average Confidence:</label>
          <span className={styles.confidenceDisplay}>
            {Math.round(averageConfidence * 100)}%
          </span>
        </div>
        
        <div className={styles.summaryItem}>
          <label>Last Update:</label>
          <span>{new Date(lastUpdateTime).toLocaleTimeString()}</span>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// Export
// ============================================================================

export default FrameProgressVisualization;
