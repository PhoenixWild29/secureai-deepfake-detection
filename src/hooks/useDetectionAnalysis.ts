/**
 * Detection Analysis Hook
 * Custom React hook for managing video analysis state and lifecycle
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { ANALYSIS_STAGES } from '../utils/websocketTypes';

// TypeScript interfaces for type safety
interface AnalysisOptions {
  websocketUrl?: string;
  maxRetries?: number;
  timeout?: number;
  enableBlockchain?: boolean;
  modelType?: string;
  customParams?: Record<string, any>;
}

interface AnalysisResult {
  is_fake: boolean;
  confidence_score: number;
  authenticity_score: number;
  model_type: string;
  processing_time_seconds: number;
  blockchain_hash: string;
  suspicious_regions: any[];
  metadata: {
    frames_processed: number;
    total_frames: number;
    analysis_id: string;
    frame_details?: any[];
    confidence_per_frame?: number[];
    frame_artifacts?: Record<string, any>;
  };
}

/**
 * Analysis state enumeration
 * @typedef {('idle'|'processing'|'completed'|'failed'|'cancelled')} AnalysisState
 */
export const ANALYSIS_STATES = {
  IDLE: 'idle',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
};

/**
 * Analysis options configuration
 * @typedef {Object} AnalysisOptions
 * @property {string} websocketUrl - WebSocket URL for real-time updates
 * @property {number} maxRetries - Maximum retry attempts (default: 3)
 * @property {number} timeout - Analysis timeout in seconds (default: 300)
 * @property {boolean} enableBlockchain - Enable blockchain verification (default: true)
 * @property {string} modelType - Model type to use (default: 'ensemble')
 * @property {Object} customParams - Custom analysis parameters
 */

/**
 * Analysis result structure
 * @typedef {Object} AnalysisResult
 * @property {boolean} is_fake - Whether video is detected as fake
 * @property {number} confidence_score - Confidence score (0.0-1.0)
 * @property {number} authenticity_score - Authenticity score (0.0-1.0)
 * @property {string} model_type - Model used for analysis
 * @property {number} processing_time_seconds - Processing time in seconds
 * @property {string} blockchain_hash - Blockchain verification hash
 * @property {Array} suspicious_regions - Detected suspicious regions
 * @property {Object} metadata - Additional analysis metadata
 */

/**
 * Frame-specific data structure
 * @typedef {Object} FrameData
 * @property {number} frameNumber - Frame number in video sequence (0-indexed)
 * @property {number} confidenceScore - Frame-specific confidence score (0.0-1.0)
 * @property {Array} suspiciousRegions - Suspicious regions detected in this frame
 * @property {number} processingTimeMs - Time to process this frame in milliseconds
 * @property {Object} artifacts - Additional artifacts detected in frame
 * @property {boolean} isProcessed - Whether frame has been fully processed
 * @property {number} timestamp - Frame analysis timestamp
 */

/**
 * Frame-level navigation state
 * @typedef {Object} FrameNavigationState
 * @property {number} currentFrame - Currently selected/focused frame index
 * @property {number} totalFrames - Total number of frames in video
 * @property {number} frameProgress - Frame processing progress (0-100)
 * @property {Map} frameConfidenceCache - Cache of confidence scores by frame
 * @property {Map} suspiciousRegionCache - Cache of suspicious regions by frame
 * @property {boolean} isNavigating - Whether user is actively navigating frames
 */

/**
 * Detection analysis hook return value
 * @typedef {Object} DetectionAnalysisReturn
 * @property {string} analysisState - Current analysis state
 * @property {number} analysisProgress - Analysis progress (0-100)
 * @property {AnalysisResult|null} analysisResult - Analysis result
 * @property {Error|null} error - Analysis error
 * @property {number} retryCount - Current retry count
 * @property {boolean} isRetrying - Whether currently retrying
 * @property {Function} startAnalysis - Start analysis function
 * @property {Function} retryAnalysis - Retry analysis function
 * @property {Function} cancelAnalysis - Cancel analysis function
 * @property {Function} handleProgressUpdate - Handle progress updates from WebSocket
 * @property {Function} handleResultUpdate - Handle result updates from WebSocket
 * @property {Function} handleErrorEvent - Handle error event from WebSocket
 * @property {Function} getCurrentStageName - Get current analysis stage display name
 * @property {Function} getAnalysisDuration - Get analysis duration in seconds
 * @property {Function} canRetry - Check if analysis can be retried
 * 
 * Frame-level state and functions (new in this work order)
 * @property {number} currentFrame - Currently selected frame index
 * @property {number} totalFrames - Total number of frames in video
 * @property {number} frameProgress - Frame processing progress (0-100)
 * @property {Function} nextFrame - Navigate to next frame
 * @property {Function} previousFrame - Navigate to previous frame
 * @property {Function} goToFrame - Navigate to specific frame
 * @property {Function} getFrameConfidence - Get confidence score for specific frame
 * @property {Function} getFrameSuspiciousRegions - Get suspicious regions for specific frame
 * @property {Function} getFrameData - Get complete frame data object
 * @property {Function} getFrameNavigationState - Get current frame navigation state
 */

/**
 * Custom hook for detection analysis management
 * @param {string} analysisId - Analysis ID
 * @param {AnalysisOptions} options - Analysis options
 * @returns {DetectionAnalysisReturn} - Detection analysis hook return value
 */
export const useDetectionAnalysis = (analysisId: string, options: AnalysisOptions = {}) => {
  const {
    websocketUrl = 'ws://localhost:8000/ws',
    maxRetries = 3,
    timeout = 300,
    enableBlockchain = true,
    modelType = 'ensemble',
    customParams = {}
  } = options || {};

  // State management
  const [analysisState, setAnalysisState] = useState(ANALYSIS_STATES.IDLE);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);

  // Frame-level state management (new in Work Order #18)
  const [currentFrame, setCurrentFrame] = useState(0);
  const [totalFrames, setTotalFrames] = useState(0);
  const [frameProgress, setFrameProgress] = useState(0);
  const [isNavigating, setIsNavigating] = useState(false);

  // Refs for persistent data
  const analysisTimeoutRef = useRef<number | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const currentStageRef = useRef(ANALYSIS_STAGES.INITIALIZING);

  // Frame-level refs for optimized updates (new in Work Order #18)
  const frameConfidenceCacheRef = useRef(new Map());
  const suspiciousRegionCacheRef = useRef(new Map());
  const frameDataCacheRef = useRef(new Map());
  const frameNavigationStateRef = useRef({
    currentFrame: 0,
    totalFrames: 0,
    frameProgress: 0,
    isNavigating: false,
    lastUpdateTime: Date.now()
  });

  /**
   * Start analysis process
   */
  const startAnalysis = useCallback(async () => {
    if (!analysisId) {
      setError(new Error('Analysis ID is required'));
      return;
    }

    try {
      setAnalysisState(ANALYSIS_STATES.PROCESSING);
      setAnalysisProgress(0);
      setAnalysisResult(null);
      setError(null);
      setIsRetrying(false);
      startTimeRef.current = Date.now();
      currentStageRef.current = ANALYSIS_STAGES.INITIALIZING;

      // Start analysis timeout
      analysisTimeoutRef.current = setTimeout(() => {
        setError(new Error('Analysis timeout exceeded'));
        setAnalysisState(ANALYSIS_STATES.FAILED);
      }, timeout * 1000);

      // Make API call to start analysis
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          analysis_id: analysisId,
          model_type: modelType,
          enable_blockchain: enableBlockchain,
          custom_params: customParams
        })
      });

      if (!response.ok) {
        throw new Error(`Analysis failed: ${response.statusText}`);
      }

      const result = await response.json();
      
      // If analysis completes immediately
      if (result.status === 'completed') {
        setAnalysisResult(result);
        setAnalysisState(ANALYSIS_STATES.COMPLETED);
        setAnalysisProgress(100);
        if (analysisTimeoutRef.current) clearTimeout(analysisTimeoutRef.current);
      }

    } catch (error) {
      console.error('Analysis start error:', error);
      setError(error);
      setAnalysisState(ANALYSIS_STATES.FAILED);
      if (analysisTimeoutRef.current) clearTimeout(analysisTimeoutRef.current);
    }
  }, [analysisId, modelType, enableBlockchain, customParams, timeout]);

  /**
   * Retry analysis
   */
  const retryAnalysis = useCallback(async () => {
    if (retryCount >= maxRetries) {
      setError(new Error('Maximum retry attempts exceeded'));
      return;
    }

    setIsRetrying(true);
    setRetryCount(prev => prev + 1);
    
    // Wait a bit before retrying
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    await startAnalysis();
    setIsRetrying(false);
  }, [retryCount, maxRetries, startAnalysis]);

  /**
   * Cancel analysis
   */
  const cancelAnalysis = useCallback(async () => {
    try {
      // Make API call to cancel analysis
      await fetch(`/api/analyze/${analysisId}/cancel`, {
        method: 'POST'
      });

      setAnalysisState(ANALYSIS_STATES.CANCELLED);
      if (analysisTimeoutRef.current) clearTimeout(analysisTimeoutRef.current);
    } catch (error) {
      console.error('Analysis cancel error:', error);
      setError(error);
    }
  }, [analysisId]);

  /**
   * Handle progress updates from WebSocket
   */
  const handleProgressUpdate = useCallback((event) => {
    if (event.analysis_id === analysisId) {
      setAnalysisProgress(event.progress * 100);
      currentStageRef.current = event.current_stage;
      
      // Frame-level progress update (new in Work Order #18)
      if (event.frames_processed !== undefined && event.total_frames !== undefined) {
        const frameProgressValue = event.total_frames > 0 ? 
          (event.frames_processed / event.total_frames) * 100 : 0;
        setFrameProgress(frameProgressValue);
        setTotalFrames(event.total_frames);
        
        // Update frame cache with processed frame data
        if (event.frame_data && event.frame_data.frame_number !== undefined) {
          const frameNumber = event.frame_data.frame_number;
          frameConfidenceCacheRef.current.set(frameNumber, event.frame_data.confidence_score);
          if (event.frame_data.suspicious_regions) {
            suspiciousRegionCacheRef.current.set(frameNumber, event.frame_data.suspicious_regions);
          }
          
          // Store complete frame data
          frameDataCacheRef.current.set(frameNumber, {
            frameNumber,
            confidenceScore: event.frame_data.confidence_score,
            suspiciousRegions: event.frame_data.suspicious_regions || [],
            processingTimeMs: event.frame_data.processing_time_ms || 0,
            artifacts: event.frame_data.artifacts || {},
            isProcessed: true,
            timestamp: Date.now()
          });
        }
        
        // Update frame navigation state ref
        frameNavigationStateRef.current = {
          ...frameNavigationStateRef.current,
          totalFrames: event.total_frames,
          frameProgress: frameProgressValue,
          lastUpdateTime: Date.now()
        };
      }
      
      // Update state based on stage
      if (event.current_stage === ANALYSIS_STAGES.COMPLETED) {
        setAnalysisState(ANALYSIS_STATES.COMPLETED);
        if (analysisTimeoutRef.current) clearTimeout(analysisTimeoutRef.current);
      } else if (event.current_stage === ANALYSIS_STAGES.FAILED) {
        setAnalysisState(ANALYSIS_STATES.FAILED);
        setError(new Error(event.message || 'Analysis failed'));
        if (analysisTimeoutRef.current) clearTimeout(analysisTimeoutRef.current);
      }
    }
  }, [analysisId]);

  /**
   * Handle result updates from WebSocket
   */
  const handleResultUpdate = useCallback((event) => {
    if (event.analysis_id === analysisId) {
      setAnalysisResult({
        is_fake: event.is_fake,
        confidence_score: event.confidence_score,
        authenticity_score: 1 - event.confidence_score,
        model_type: event.model_type || modelType,
        processing_time_seconds: event.processing_time_ms / 1000,
        blockchain_hash: event.blockchain_hash,
        suspicious_regions: event.suspicious_regions || [],
        metadata: {
          frames_processed: event.frames_processed,
          total_frames: event.total_frames,
          analysis_id: event.analysis_id,
          // Enhanced metadata with frame data (new in Work Order #18)
          frame_details: event.frame_details || [],
          confidence_per_frame: event.confidence_per_frame || [],
          frame_artifacts: event.frame_artifacts || {}
        }
      });
      
      // Update frame-level state on completion (new in Work Order #18)
      if (event.total_frames !== undefined) {
        setTotalFrames(event.total_frames);
        setFrameProgress(100);
        
        // Cache final frame data if provided
        if (event.confidence_per_frame && Array.isArray(event.confidence_per_frame)) {
          event.confidence_per_frame.forEach((score, frameIndex) => {
            frameConfidenceCacheRef.current.set(frameIndex, score);
          });
        }
        
        if (event.frame_details && Array.isArray(event.frame_details)) {
          event.frame_details.forEach((frameDetail) => {
            if (frameDetail.frame_number !== undefined) {
              frameDataCacheRef.current.set(frameDetail.frame_number, {
                frameNumber: frameDetail.frame_number,
                confidenceScore: frameDetail.confidence_score || 0,
                suspiciousRegions: frameDetail.suspicious_regions || [],
                processingTimeMs: frameDetail.processing_time_ms || 0,
                artifacts: frameDetail.artifacts || {},
                isProcessed: true,
                timestamp: Date.now()
              });
            }
          });
        }
        
        // Update final frame navigation state
        frameNavigationStateRef.current = {
          ...frameNavigationStateRef.current,
          totalFrames: event.total_frames,
          frameProgress: 100,
          lastUpdateTime: Date.now()
        };
      }
      
      setAnalysisState(ANALYSIS_STATES.COMPLETED);
      setAnalysisProgress(100);
      if (analysisTimeoutRef.current) clearTimeout(analysisTimeoutRef.current);
    }
  }, [analysisId, modelType]);

  /**
   * Handle error events from WebSocket
   */
  const handleErrorEvent = useCallback((event) => {
    if (event.analysis_id === analysisId) {
      setError(new Error(event.error_message));
      setAnalysisState(ANALYSIS_STATES.FAILED);
      if (analysisTimeoutRef.current) clearTimeout(analysisTimeoutRef.current);
    }
  }, [analysisId]);

  /**
   * Get current analysis stage display name
   */
  const getCurrentStageName = useCallback(() => {
    const stageNames = {
      [ANALYSIS_STAGES.INITIALIZING]: 'Initializing',
      [ANALYSIS_STAGES.UPLOADING]: 'Uploading',
      [ANALYSIS_STAGES.FRAME_EXTRACTION]: 'Extracting Frames',
      [ANALYSIS_STAGES.FEATURE_EXTRACTION]: 'Extracting Features',
      [ANALYSIS_STAGES.MODEL_INFERENCE]: 'Running Analysis',
      [ANALYSIS_STAGES.POST_PROCESSING]: 'Post Processing',
      [ANALYSIS_STAGES.BLOCKCHAIN_SUBMISSION]: 'Submitting to Blockchain',
      [ANALYSIS_STAGES.COMPLETED]: 'Completed',
      [ANALYSIS_STAGES.FAILED]: 'Failed'
    };
    
    return stageNames[currentStageRef.current] || 'Processing';
  }, []);

  // ============================================================================
  // Frame Navigation Functions (new in Work Order #18)
  // ============================================================================

  /**
   * Navigate to next frame
   */
  const nextFrame = useCallback(() => {
    if (totalFrames > 0 && currentFrame < totalFrames - 1) {
      const newFrame = currentFrame + 1;
      setCurrentFrame(newFrame);
      setIsNavigating(true);
      
      // Update ref for optimized tracking
      frameNavigationStateRef.current = {
        ...frameNavigationStateRef.current,
        currentFrame: newFrame,
        isNavigating: true,
        lastUpdateTime: Date.now()
      };
      
      // Reset navigation flag after delay
      setTimeout(() => setIsNavigating(false), 200);
    }
  }, [currentFrame, totalFrames]);

  /**
   * Navigate to previous frame
   */
  const previousFrame = useCallback(() => {
    if (currentFrame > 0) {
      const newFrame = currentFrame - 1;
      setCurrentFrame(newFrame);
      setIsNavigating(true);
      
      // Update ref for optimized tracking
      frameNavigationStateRef.current = {
        ...frameNavigationStateRef.current,
        currentFrame: newFrame,
        isNavigating: true,
        lastUpdateTime: Date.now()
      };
      
      // Reset navigation flag after delay
      setTimeout(() => setIsNavigating(false), 200);
    }
  }, [currentFrame]);

  /**
   * Navigate to specific frame
   */
  const goToFrame = useCallback((targetFrame) => {
    const frameNumber = typeof targetFrame === 'number' ? targetFrame : parseInt(targetFrame, 10);
    
    if (!isNaN(frameNumber) && frameNumber >= 0 && frameNumber < totalFrames) {
      setCurrentFrame(frameNumber);
      setIsNavigating(true);
      
      // Update ref for optimized tracking
      frameNavigationStateRef.current = {
        ...frameNavigationStateRef.current,
        currentFrame: frameNumber,
        isNavigating: true,
        lastUpdateTime: Date.now()
      };
      
      // Reset navigation flag after delay
      setTimeout(() => setIsNavigating(false), 200);
    }
  }, [totalFrames]);

  /**
   * Get confidence score for specific frame with caching
   */
  const getFrameConfidence = useCallback((frameNumber) => {
    return frameConfidenceCacheRef.current.get(frameNumber) || null;
  }, []);

  /**
   * Get suspicious regions for specific frame with caching
   */
  const getFrameSuspiciousRegions = useCallback((frameNumber) => {
    return suspiciousRegionCacheRef.current.get(frameNumber) || [];
  }, []);

  /**
   * Get complete frame data object
   */
  const getFrameDataComplete = useCallback((frameNumber) => {
    return frameDataCacheRef.current.get(frameNumber) || null;
  }, []);

  /**
   * Get current frame navigation state
   */
  const getFrameNavigationState = useCallback(() => {
    return {
      currentFrame: frameNavigationStateRef.current.currentFrame,
      totalFrames: frameNavigationStateRef.current.totalFrames,
      frameProgress: frameNavigationStateRef.current.frameProgress,
      isNavigating: frameNavigationStateRef.current.isNavigating,
      lastUpdateTime: frameNavigationStateRef.current.lastUpdateTime
    };
  }, []);

  /**
   * Get analysis duration
   */
  const getAnalysisDuration = useCallback(() => {
    if (startTimeRef.current) {
      return (Date.now() - startTimeRef.current) / 1000;
    }
    return 0;
  }, []);

  /**
   * Check if analysis can be retried
   */
  const canRetry = useCallback(() => {
    return retryCount < maxRetries && 
           (analysisState === ANALYSIS_STATES.FAILED || analysisState === ANALYSIS_STATES.CANCELLED);
  }, [retryCount, maxRetries, analysisState]);

  // Cleanup on unmount and analysis completion
  useEffect(() => {
    return () => {
      if (analysisTimeoutRef.current) {
        if (analysisTimeoutRef.current) clearTimeout(analysisTimeoutRef.current);
      }
    };
  }, []);

  // Frame cache cleanup for completed analyses (new in Work Order #18)
  useEffect(() => {
    if (analysisState === ANALYSIS_STATES.COMPLETED || analysisState === ANALYSIS_STATES.FAILED) {
      // Keep caches for completed analyses but clear navigation state
      frameNavigationStateRef.current = {
        ...frameNavigationStateRef.current,
        isNavigating: false,
        lastUpdateTime: Date.now()
      };
    }
  }, [analysisState]);

  return {
    // Existing analysis state and functions (maintaining backward compatibility)
    analysisState,
    analysisProgress,
    analysisResult,
    error,
    retryCount,
    isRetrying,
    startAnalysis,
    retryAnalysis,
    cancelAnalysis,
    handleProgressUpdate,
    handleResultUpdate,
    handleErrorEvent,
    getCurrentStageName,
    getAnalysisDuration,
    canRetry,
    
    // Frame-level state and functions (new in Work Order #18)
    currentFrame,
    totalFrames,
    frameProgress,
    isNavigating,
    nextFrame,
    previousFrame,
    goToFrame,
    getFrameConfidence,
    getFrameSuspiciousRegions,
    getFrameDataComplete,
    getFrameNavigationState
  };
};

/**
 * Hook for analysis status display
 * @param {string} analysisState - Current analysis state
 * @returns {Object} - Status display information
 */
export const useAnalysisStatusDisplay = (analysisState) => {
  const getStatusInfo = useCallback(() => {
    switch (analysisState) {
      case ANALYSIS_STATES.IDLE:
        return {
          text: 'Ready',
          color: '#6b7280',
          icon: '⏸️',
          description: 'Analysis ready to start'
        };
        
      case ANALYSIS_STATES.PROCESSING:
        return {
          text: 'Processing',
          color: '#3b82f6',
          icon: '🔄',
          description: 'Analysis in progress'
        };
        
      case ANALYSIS_STATES.COMPLETED:
        return {
          text: 'Completed',
          color: '#10b981',
          icon: '✅',
          description: 'Analysis completed successfully'
        };
        
      case ANALYSIS_STATES.FAILED:
        return {
          text: 'Failed',
          color: '#ef4444',
          icon: '❌',
          description: 'Analysis failed'
        };
        
      case ANALYSIS_STATES.CANCELLED:
        return {
          text: 'Cancelled',
          color: '#f59e0b',
          icon: '⏹️',
          description: 'Analysis was cancelled'
        };
        
      default:
        return {
          text: 'Unknown',
          color: '#6b7280',
          icon: '❓',
          description: 'Unknown analysis state'
        };
    }
  }, [analysisState]);
  
  return getStatusInfo();
};

export default useDetectionAnalysis;