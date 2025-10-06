/**
 * AnalysisProgressTracker Component
 * Component for tracking and displaying video analysis progress with real-time updates
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useDetectionAnalysis } from '../../hooks/useDetectionAnalysis';
import { useWebSocketEvents } from '../../hooks/useWebSocketEvents';
import { formatTimeRemaining, formatFileSize } from '../../utils/videoProcessing';
import styles from './AnalysisProgressTracker.module.css';

/**
 * AnalysisProgressTracker - Component for tracking analysis progress
 * @param {Object} props - Component props
 * @param {string} props.analysisId - Analysis ID to track
 * @param {string} props.uploadId - Upload ID
 * @param {string} props.filename - Original filename
 * @param {Function} props.onAnalysisComplete - Callback when analysis completes
 * @param {Function} props.onAnalysisError - Callback when analysis fails
 * @param {Function} props.onRetry - Callback for retry action
 * @param {Object} props.options - Analysis options
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Analysis progress tracker component
 */
const AnalysisProgressTracker = ({
  analysisId,
  uploadId,
  filename,
  onAnalysisComplete,
  onAnalysisError,
  onRetry,
  options = {},
  className = ''
}) => {
  // Analysis state management
  const {
    analysisState,
    analysisProgress,
    analysisResult,
    error,
    retryCount,
    isRetrying,
    startAnalysis,
    retryAnalysis,
    cancelAnalysis
  } = useDetectionAnalysis(analysisId, options);

  // WebSocket events for real-time updates
  const {
    isConnected,
    connectionState,
    subscribe,
    unsubscribe,
    sendMessage
  } = useWebSocketEvents({
    url: options.websocketUrl || 'ws://localhost:8000/ws',
    enableReconnection: true,
    heartbeatInterval: 30000
  });

  // Component state
  const [currentStage, setCurrentStage] = useState('initializing');
  const [stageProgress, setStageProgress] = useState(0);
  const [estimatedTimeRemaining, setEstimatedTimeRemaining] = useState(null);
  const [framesProcessed, setFramesProcessed] = useState(0);
  const [totalFrames, setTotalFrames] = useState(0);
  const [processingSpeed, setProcessingSpeed] = useState(0);
  const [startTime, setStartTime] = useState(null);

  // Refs
  const progressIntervalRef = useRef(null);
  const lastUpdateTimeRef = useRef(Date.now());

  // ============================================================================
  // WebSocket Event Handlers
  // ============================================================================

  /**
   * Handle processing progress updates
   */
  const handleProcessingProgress = useCallback((event) => {
    if (event.analysis_id === analysisId) {
      setCurrentStage(event.current_stage || 'processing');
      setStageProgress(event.progress_percentage || 0);
      setEstimatedTimeRemaining(event.estimated_time_remaining);
      
      if (event.frames_processed !== undefined) {
        setFramesProcessed(event.frames_processed);
      }
      
      if (event.total_frames !== undefined) {
        setTotalFrames(event.total_frames);
      }
      
      if (event.processing_speed_fps !== undefined) {
        setProcessingSpeed(event.processing_speed_fps);
      }

      lastUpdateTimeRef.current = Date.now();
    }
  }, [analysisId]);

  /**
   * Handle processing completion
   */
  const handleProcessingComplete = useCallback((event) => {
    if (event.analysis_id === analysisId) {
      setCurrentStage('completed');
      setStageProgress(100);
      setEstimatedTimeRemaining(0);
      onAnalysisComplete?.(event.result);
    }
  }, [analysisId, onAnalysisComplete]);

  /**
   * Handle processing failure
   */
  const handleProcessingFailed = useCallback((event) => {
    if (event.analysis_id === analysisId) {
      setCurrentStage('failed');
      onAnalysisError?.(event);
    }
  }, [analysisId, onAnalysisError]);

  // ============================================================================
  // Effects
  // ============================================================================

  // Subscribe to WebSocket events
  useEffect(() => {
    if (isConnected && analysisId) {
      // Subscribe to analysis-specific events
      subscribe('processing_progress', handleProcessingProgress);
      subscribe('processing_completed', handleProcessingComplete);
      subscribe('processing_failed', handleProcessingFailed);

      return () => {
        unsubscribe('processing_progress', handleProcessingProgress);
        unsubscribe('processing_completed', handleProcessingComplete);
        unsubscribe('processing_failed', handleProcessingFailed);
      };
    }
  }, [isConnected, analysisId, subscribe, unsubscribe, handleProcessingProgress, handleProcessingComplete, handleProcessingFailed]);

  // Start analysis when component mounts
  useEffect(() => {
    if (analysisId && analysisState === 'idle') {
      setStartTime(Date.now());
      startAnalysis();
    }
  }, [analysisId, analysisState, startAnalysis]);

  // Update time estimates
  useEffect(() => {
    if (analysisState === 'processing' && stageProgress > 0) {
      progressIntervalRef.current = setInterval(() => {
        const now = Date.now();
        const timeSinceLastUpdate = now - lastUpdateTimeRef.current;
        
        // If no updates for 30 seconds, assume processing is stuck
        if (timeSinceLastUpdate > 30000) {
          console.warn('No progress updates received for 30 seconds');
        }
      }, 5000);
    } else {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }
    }

    return () => {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
    };
  }, [analysisState, stageProgress]);

  // ============================================================================
  // Event Handlers
  // ============================================================================

  /**
   * Handle retry analysis
   */
  const handleRetry = useCallback(() => {
    setCurrentStage('initializing');
    setStageProgress(0);
    setEstimatedTimeRemaining(null);
    setFramesProcessed(0);
    setTotalFrames(0);
    setProcessingSpeed(0);
    setStartTime(Date.now());
    retryAnalysis();
    onRetry?.();
  }, [retryAnalysis, onRetry]);

  /**
   * Handle cancel analysis
   */
  const handleCancel = useCallback(() => {
    cancelAnalysis();
    setCurrentStage('cancelled');
  }, [cancelAnalysis]);

  // ============================================================================
  // Render Helpers
  // ============================================================================

  /**
   * Get stage display information
   */
  const getStageInfo = (stage) => {
    const stages = {
      'initializing': { label: 'Initializing', description: 'Setting up analysis environment' },
      'preprocessing': { label: 'Preprocessing', description: 'Preparing video for analysis' },
      'analyzing': { label: 'Analyzing', description: 'Running deepfake detection algorithms' },
      'postprocessing': { label: 'Post-processing', description: 'Finalizing results' },
      'completed': { label: 'Complete', description: 'Analysis finished successfully' },
      'failed': { label: 'Failed', description: 'Analysis encountered an error' },
      'cancelled': { label: 'Cancelled', description: 'Analysis was cancelled' }
    };
    
    return stages[stage] || { label: stage, description: 'Processing...' };
  };

  /**
   * Get stage icon
   */
  const getStageIcon = (stage) => {
    const icons = {
      'initializing': '⚙️',
      'preprocessing': '🔄',
      'analyzing': '🔍',
      'postprocessing': '📊',
      'completed': '✅',
      'failed': '❌',
      'cancelled': '⏹️'
    };
    
    return icons[stage] || '⏳';
  };

  /**
   * Render processing progress
   */
  const renderProcessingProgress = () => {
    const stageInfo = getStageInfo(currentStage);
    const elapsedTime = startTime ? (Date.now() - startTime) / 1000 : 0;

    return (
      <div className={styles.processingProgress}>
        <div className={styles.progressHeader}>
          <div className={styles.stageInfo}>
            <span className={styles.stageIcon}>{getStageIcon(currentStage)}</span>
            <div>
              <h3>{stageInfo.label}</h3>
              <p>{stageInfo.description}</p>
            </div>
          </div>
          <div className={styles.progressPercentage}>
            {Math.round(stageProgress)}%
          </div>
        </div>

        <div className={styles.progressBar}>
          <div 
            className={styles.progressFill}
            style={{ width: `${stageProgress}%` }}
          />
        </div>

        <div className={styles.progressDetails}>
          <div className={styles.timeInfo}>
            <span>Elapsed: {formatTimeRemaining(elapsedTime)}</span>
            {estimatedTimeRemaining && (
              <span>Remaining: {formatTimeRemaining(estimatedTimeRemaining)}</span>
            )}
          </div>
          
          {(framesProcessed > 0 || totalFrames > 0) && (
            <div className={styles.frameInfo}>
              <span>Frames: {framesProcessed}/{totalFrames}</span>
              {processingSpeed > 0 && (
                <span>Speed: {processingSpeed.toFixed(1)} fps</span>
              )}
            </div>
          )}
        </div>

        {analysisState === 'processing' && (
          <button 
            className={styles.cancelButton}
            onClick={handleCancel}
          >
            Cancel Analysis
          </button>
        )}
      </div>
    );
  };

  /**
   * Render analysis result
   */
  const renderAnalysisResult = () => {
    if (!analysisResult) return null;

    const isFake = analysisResult.is_fake || false;
    const confidence = analysisResult.confidence_score || analysisResult.authenticity_score || 0;
    const confidencePercent = Math.round(confidence * 100);

    return (
      <div className={styles.analysisResult}>
        <div className={`${styles.resultHeader} ${isFake ? styles.resultFake : styles.resultReal}`}>
          <div className={styles.resultIcon}>
            {isFake ? '🚨' : '✅'}
          </div>
          <div className={styles.resultInfo}>
            <h3>{isFake ? 'Potential Deepfake Detected' : 'Authentic Video'}</h3>
            <p>Confidence: {confidencePercent}%</p>
          </div>
        </div>

        <div className={styles.resultDetails}>
          <div className={styles.detailItem}>
            <span className={styles.detailLabel}>Analysis ID:</span>
            <span className={styles.detailValue}>{analysisId}</span>
          </div>
          
          <div className={styles.detailItem}>
            <span className={styles.detailLabel}>Processing Time:</span>
            <span className={styles.detailValue}>
              {analysisResult.processing_time_seconds ? 
                `${analysisResult.processing_time_seconds.toFixed(2)}s` : 
                'N/A'
              }
            </span>
          </div>

          {analysisResult.model_type && (
            <div className={styles.detailItem}>
              <span className={styles.detailLabel}>Model:</span>
              <span className={styles.detailValue}>{analysisResult.model_type}</span>
            </div>
          )}

          {analysisResult.blockchain_hash && (
            <div className={styles.detailItem}>
              <span className={styles.detailLabel}>Verification Hash:</span>
              <span className={styles.detailValue}>
                <code>{analysisResult.blockchain_hash.substring(0, 16)}...</code>
              </span>
            </div>
          )}
        </div>

        <div className={styles.resultActions}>
          <button 
            className={styles.viewDetailsButton}
            onClick={() => onAnalysisComplete?.(analysisResult)}
          >
            View Detailed Results
          </button>
          <button 
            className={styles.newAnalysisButton}
            onClick={() => window.location.reload()}
          >
            Analyze Another Video
          </button>
        </div>
      </div>
    );
  };

  /**
   * Render error state
   */
  const renderError = () => {
    if (!error) return null;

    return (
      <div className={styles.errorContainer}>
        <div className={styles.errorIcon}>❌</div>
        <div className={styles.errorContent}>
          <h3>Analysis Failed</h3>
          <p>{error.message || 'An unexpected error occurred during analysis'}</p>
          
          {retryCount < (options.maxRetries || 3) && (
            <button 
              className={styles.retryButton}
              onClick={handleRetry}
              disabled={isRetrying}
            >
              {isRetrying ? 'Retrying...' : 'Retry Analysis'}
            </button>
          )}
        </div>
      </div>
    );
  };

  /**
   * Render connection status
   */
  const renderConnectionStatus = () => {
    if (isConnected) return null;

    return (
      <div className={styles.connectionStatus}>
        <div className={styles.connectionIcon}>
          {connectionState === 'connecting' ? '🔄' : '⚠️'}
        </div>
        <div className={styles.connectionContent}>
          <p>
            {connectionState === 'connecting' ? 
              'Connecting to real-time updates...' : 
              'Connection lost. Attempting to reconnect...'
            }
          </p>
        </div>
      </div>
    );
  };

  // ============================================================================
  // Main Render
  // ============================================================================

  return (
    <div className={`${styles.analysisTracker} ${className}`}>
      <div className={styles.header}>
        <h2>Analysis Progress</h2>
        <div className={styles.analysisInfo}>
          <span className={styles.filename}>{filename}</span>
          <span className={styles.analysisId}>ID: {analysisId}</span>
        </div>
      </div>

      {renderConnectionStatus()}

      {analysisState === 'processing' && renderProcessingProgress()}
      
      {analysisState === 'completed' && renderAnalysisResult()}
      
      {error && renderError()}

      {analysisState === 'idle' && (
        <div className={styles.waiting}>
          <div className={styles.spinner} />
          <p>Preparing analysis...</p>
        </div>
      )}
    </div>
  );
};

export default AnalysisProgressTracker;
