/**
 * useResultVisualization Hook
 * Work Order #48 - Extended State Management for Result Visualization
 * 
 * Specialized React hook that extends the Core Detection Engine's useDetectionAnalysis hook
 * to manage visualization state, export progress, and real-time updates specific to
 * results display components.
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useDetectionAnalysis } from './useDetectionAnalysis';
import { useWebSocket } from './useWebSocket';
import { useAuth } from './useAuth';
import { exportService } from '../services/exportService';

// Import visualization types
import {
  VISUALIZATION_MODES,
  EXPORT_FORMATS,
  EXPORT_STATUS,
  BLOCKCHAIN_STATUS,
  HEATMAP_STATUS,
  VISUALIZATION_ERROR_TYPES,
  DEFAULT_VISUALIZATION_OPTIONS,
  DEFAULT_VISUALIZATION_STATE,
  validateVisualizationOptions,
  isValidVisualizationMode,
  isValidExportFormat,
  isValidBlockchainStatus
} from '../types/visualization';

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * useResultVisualization - Extended visualization state management hook
 * 
 * @param {string} analysisId - Analysis ID for detection results
 * @param {Object} options - Visualization options configuration
 * @param {boolean} options.enableConfidenceCaching - Enable confidence score caching
 * @param {boolean} options.enableHeatmapProcessing - Enable heatmap data processing
 * @param {boolean} options.enableExportTracking - Enable export state tracking
 * @param {boolean} options.enableBlockchainMonitoring - Enable blockchain verification monitoring
 * @param {boolean} options.enableModificationTracking - Enable result modification tracking
 * @param {number} options.cacheSize - Maximum cache size for confidence scores
 * @param {number} options.heatmapOptimizationThreshold - Threshold for heatmap optimization
 * @param {number} options.debounceDelay - Debounce delay for real-time updates
 * @param {boolean} options.enablePerformanceOptimization - Enable performance optimizations
 * @returns {Object} Visualization state and actions
 */
export const useResultVisualization = (analysisId, options = {}) => {
  
  // ============================================================================
  // Configuration and Initialization
  // ============================================================================
  
  const validatedOptions = useMemo(() => validateVisualizationOptions(options), [options]);
  
  // Core detection analysis hook (extends existing functionality)
  const detectionAnalysis = useDetectionAnalysis(analysisId, {
    enableBlockchain: validatedOptions.enableBlockchainMonitoring,
    websocketUrl: process.env.REACT_APP_WEBSOCKET_URL || 'ws://localhost:8000'
  });
  
  // Authentication hook
  const { user, hasPermission } = useAuth();
  
  // WebSocket hook for real-time updates
  const { subscribe, unsubscribe, isConnected } = useWebSocket();
  
  // ============================================================================
  // State Management
  // ============================================================================
  
  const [visualizationState, setVisualizationState] = useState(() => ({
    ...DEFAULT_VISUALIZATION_STATE,
    currentMode: VISUALIZATION_MODES.SUMMARY
  }));
  
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Performance tracking refs
  const renderStartTime = useRef(Date.now());
  const stateUpdateCount = useRef(0);
  const confidenceCacheRef = useRef(new Map());
  const debounceTimeoutRef = useRef(null);
  const lastWebSocketUpdateRef = useRef(Date.now());
  
  // ============================================================================
  // Memoized Values and Computed Properties
  // ============================================================================
  
  const performanceMetrics = useMemo(() => ({
    renderCount: stateUpdateCount.current,
    stateUpdateCount: stateUpdateCount.current,
    cacheHitRate: calculateCacheHitRate(),
    averageRenderTime: calculateAverageRenderTime(),
    memoryUsage: performance.memory ? performance.memory.usedJSHeapSize : 0,
    renderTimes: visualizationState.performanceMetrics.renderTimes,
    lastOptimization: visualizationState.performanceMetrics.lastOptimization,
    optimizationStats: visualizationState.performanceMetrics.optimizationStats
  }), [visualizationState.performanceMetrics]);
  
  const canExport = useMemo(() => {
    return user && hasPermission('export', 'any') && !visualizationState.exportState.isExporting;
  }, [user, hasPermission, visualizationState.exportState.isExporting]);
  
  const hasUnseenModifications = useMemo(() => {
    return visualizationState.modificationState.hasUnseenModifications;
  }, [visualizationState.modificationState.hasUnseenModifications]);
  
  // ============================================================================
  // Helper Functions
  // ============================================================================
  
  const calculateCacheHitRate = useCallback(() => {
    const cache = confidenceCacheRef.current;
    if (cache.size === 0) return 0;
    
    let hits = 0;
    let total = 0;
    
    for (const [key, value] of cache.entries()) {
      total++;
      if (value.isProcessed) hits++;
    }
    
    return total > 0 ? (hits / total) * 100 : 0;
  }, []);
  
  const calculateAverageRenderTime = useCallback(() => {
    const renderTimes = visualizationState.performanceMetrics.renderTimes;
    if (renderTimes.length === 0) return 0;
    
    const sum = renderTimes.reduce((acc, time) => acc + time, 0);
    return sum / renderTimes.length;
  }, [visualizationState.performanceMetrics.renderTimes]);
  
  const debouncedStateUpdate = useCallback((updateFunction) => {
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }
    
    debounceTimeoutRef.current = setTimeout(() => {
      setVisualizationState(prevState => {
        const newState = updateFunction(prevState);
        stateUpdateCount.current++;
        return {
          ...newState,
          lastStateUpdate: Date.now(),
          performanceMetrics: {
            ...newState.performanceMetrics,
            renderCount: stateUpdateCount.current,
            stateUpdateCount: stateUpdateCount.current
          }
        };
      });
    }, validatedOptions.debounceDelay);
  }, [validatedOptions.debounceDelay]);
  
  const addToErrorHistory = useCallback((errorData) => {
    setVisualizationState(prevState => ({
      ...prevState,
      errorHistory: [
        ...prevState.errorHistory.slice(-9), // Keep last 10 errors
        {
          type: errorData.type || VISUALIZATION_ERROR_TYPES.PERFORMANCE_ERROR,
          message: errorData.message || 'Unknown error',
          originalError: errorData.originalError || null,
          timestamp: Date.now(),
          context: errorData.context || null,
          isRecoverable: errorData.isRecoverable || false,
          recoveryAction: errorData.recoveryAction || null
        }
      ]
    }));
  }, []);
  
  const handleError = useCallback((error, errorType = VISUALIZATION_ERROR_TYPES.PERFORMANCE_ERROR, context = null) => {
    console.error(`[useResultVisualization] ${errorType}:`, error);
    
    setError(error);
    addToErrorHistory({
      type: errorType,
      message: error.message || 'An error occurred',
      originalError: error,
      context,
      isRecoverable: true
    });
  }, [addToErrorHistory]);
  
  // ============================================================================
  // Confidence Score Caching
  // ============================================================================
  
  const updateConfidenceCache = useCallback((frameNumber, confidenceData) => {
    if (!validatedOptions.enableConfidenceCaching) return;
    
    try {
      const cacheEntry = {
        frameNumber,
        confidenceScore: confidenceData.confidenceScore,
        timestamp: Date.now(),
        isProcessed: confidenceData.isProcessed || false,
        suspiciousRegions: confidenceData.suspiciousRegions || []
      };
      
      // Maintain cache size limit
      const cache = confidenceCacheRef.current;
      if (cache.size >= validatedOptions.cacheSize) {
        const firstKey = cache.keys().next().value;
        cache.delete(firstKey);
      }
      
      cache.set(frameNumber, cacheEntry);
      
      // Update visualization state
      debouncedStateUpdate(prevState => ({
        ...prevState,
        confidenceCache: new Map(cache)
      }));
      
    } catch (error) {
      handleError(error, VISUALIZATION_ERROR_TYPES.CACHE_ERROR, { frameNumber, confidenceData });
    }
  }, [validatedOptions.enableConfidenceCaching, validatedOptions.cacheSize, debouncedStateUpdate, handleError]);
  
  const getCachedConfidenceScore = useCallback((frameNumber) => {
    return confidenceCacheRef.current.get(frameNumber) || null;
  }, []);
  
  // ============================================================================
  // Heatmap Data Processing
  // ============================================================================
  
  const processHeatmapData = useCallback(async (heatmapData) => {
    if (!validatedOptions.enableHeatmapProcessing) return;
    
    try {
      debouncedStateUpdate(prevState => ({
        ...prevState,
        heatmapState: {
          ...prevState.heatmapState,
          status: HEATMAP_STATUS.LOADING,
          progress: 0,
          error: null
        }
      }));
      
      // Simulate heatmap processing with progress updates
      const totalSteps = 10;
      for (let step = 1; step <= totalSteps; step++) {
        await new Promise(resolve => setTimeout(resolve, 100));
        
        const progress = (step / totalSteps) * 100;
        debouncedStateUpdate(prevState => ({
          ...prevState,
          heatmapState: {
            ...prevState.heatmapState,
            status: HEATMAP_STATUS.PROCESSING,
            progress
          }
        }));
      }
      
      // Optimize data if threshold exceeded
      const isOptimized = heatmapData.dataPoints.length > validatedOptions.heatmapOptimizationThreshold;
      const optimizedData = isOptimized ? optimizeHeatmapData(heatmapData) : heatmapData;
      
      debouncedStateUpdate(prevState => ({
        ...prevState,
        heatmapState: {
          status: HEATMAP_STATUS.COMPLETED,
          progress: 100,
          data: optimizedData,
          error: null,
          lastUpdate: Date.now(),
          isOptimized
        }
      }));
      
    } catch (error) {
      handleError(error, VISUALIZATION_ERROR_TYPES.HEATMAP_ERROR, { heatmapData });
      
      debouncedStateUpdate(prevState => ({
        ...prevState,
        heatmapState: {
          ...prevState.heatmapState,
          status: HEATMAP_STATUS.FAILED,
          error: error.message
        }
      }));
    }
  }, [validatedOptions.enableHeatmapProcessing, validatedOptions.heatmapOptimizationThreshold, debouncedStateUpdate, handleError]);
  
  const optimizeHeatmapData = useCallback((heatmapData) => {
    // Simple optimization: reduce data points while maintaining important features
    const optimizedPoints = heatmapData.dataPoints
      .filter(point => point.intensity > 0.1) // Filter low intensity points
      .sort((a, b) => b.intensity - a.intensity) // Sort by intensity
      .slice(0, validatedOptions.heatmapOptimizationThreshold); // Limit points
    
    return {
      ...heatmapData,
      dataPoints: optimizedPoints,
      metadata: {
        ...heatmapData.metadata,
        optimized: true,
        originalPointCount: heatmapData.dataPoints.length,
        optimizedPointCount: optimizedPoints.length
      }
    };
  }, [validatedOptions.heatmapOptimizationThreshold]);
  
  // ============================================================================
  // Export State Management
  // ============================================================================
  
  const initiateExport = useCallback(async (format = EXPORT_FORMATS.PDF, exportOptions = {}) => {
    if (!validatedOptions.enableExportTracking || !canExport) return;
    
    try {
      debouncedStateUpdate(prevState => ({
        ...prevState,
        exportState: {
          ...prevState.exportState,
          isExporting: true,
          selectedFormat: format,
          currentExport: {
            exportId: `export_${Date.now()}`,
            status: EXPORT_STATUS.INITIATING,
            progress: 0,
            message: 'Initiating export...',
            estimatedCompletion: new Date(Date.now() + 60000).toISOString(),
            fileSize: 0,
            fileName: ''
          }
        }
      }));
      
      const exportRequest = {
        format,
        analysisIds: [analysisId],
        options: exportOptions,
        userId: user.id,
        permissions: user.permissions
      };
      
      const exportJob = await exportService.initiateExport(exportRequest);
      
      debouncedStateUpdate(prevState => ({
        ...prevState,
        exportState: {
          ...prevState.exportState,
          currentExport: {
            ...prevState.exportState.currentExport,
            exportId: exportJob.exportId,
            status: EXPORT_STATUS.PROCESSING,
            progress: 10,
            message: 'Export initiated successfully'
          }
        }
      }));
      
    } catch (error) {
      handleError(error, VISUALIZATION_ERROR_TYPES.EXPORT_ERROR, { format, exportOptions });
      
      debouncedStateUpdate(prevState => ({
        ...prevState,
        exportState: {
          ...prevState.exportState,
          isExporting: false,
          currentExport: {
            ...prevState.exportState.currentExport,
            status: EXPORT_STATUS.FAILED,
            errorMessage: error.message
          }
        }
      }));
    }
  }, [validatedOptions.enableExportTracking, canExport, analysisId, user, debouncedStateUpdate, handleError]);
  
  const cancelExport = useCallback(async () => {
    if (!visualizationState.exportState.currentExport) return;
    
    try {
      await exportService.cancelExport(visualizationState.exportState.currentExport.exportId);
      
      debouncedStateUpdate(prevState => ({
        ...prevState,
        exportState: {
          ...prevState.exportState,
          isExporting: false,
          currentExport: {
            ...prevState.exportState.currentExport,
            status: EXPORT_STATUS.CANCELLED,
            message: 'Export cancelled by user'
          }
        }
      }));
      
    } catch (error) {
      handleError(error, VISUALIZATION_ERROR_TYPES.EXPORT_ERROR, { action: 'cancel' });
    }
  }, [visualizationState.exportState.currentExport, debouncedStateUpdate, handleError]);
  
  const retryExport = useCallback(async () => {
    if (!visualizationState.exportState.currentExport) return;
    
    try {
      await exportService.retryExport(visualizationState.exportState.currentExport.exportId);
      
      debouncedStateUpdate(prevState => ({
        ...prevState,
        exportState: {
          ...prevState.exportState,
          currentExport: {
            ...prevState.exportState.currentExport,
            status: EXPORT_STATUS.INITIATING,
            progress: 0,
            message: 'Retrying export...',
            errorMessage: null
          }
        }
      }));
      
    } catch (error) {
      handleError(error, VISUALIZATION_ERROR_TYPES.EXPORT_ERROR, { action: 'retry' });
    }
  }, [visualizationState.exportState.currentExport, debouncedStateUpdate, handleError]);
  
  // ============================================================================
  // Blockchain Verification Monitoring
  // ============================================================================
  
  const refreshBlockchainStatus = useCallback(async () => {
    if (!validatedOptions.enableBlockchainMonitoring) return;
    
    try {
      const blockchainData = detectionAnalysis.blockchainVerification;
      
      debouncedStateUpdate(prevState => ({
        ...prevState,
        blockchainState: {
          ...prevState.blockchainState,
          verification: {
            status: blockchainData.verified ? BLOCKCHAIN_STATUS.VERIFIED : BLOCKCHAIN_STATUS.PENDING,
            progress: blockchainData.verified ? 100 : 0,
            transactionHash: blockchainData.transactionHash || null,
            verificationTimestamp: blockchainData.verifiedAt || null,
            blockNumber: blockchainData.blockNumber || null,
            gasUsed: blockchainData.gasUsed || null,
            networkId: blockchainData.networkId || null,
            metadata: blockchainData.metadata || null
          },
          lastUpdate: Date.now()
        }
      }));
      
    } catch (error) {
      handleError(error, VISUALIZATION_ERROR_TYPES.BLOCKCHAIN_ERROR);
    }
  }, [validatedOptions.enableBlockchainMonitoring, detectionAnalysis.blockchainVerification, debouncedStateUpdate, handleError]);
  
  // ============================================================================
  // Result Modification Tracking
  // ============================================================================
  
  const trackModification = useCallback((modificationType, previousValue, newValue, source = 'websocket') => {
    if (!validatedOptions.enableModificationTracking) return;
    
    const modificationEntry = {
      modificationId: `mod_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type: modificationType,
      timestamp: new Date(),
      previousValue,
      newValue,
      source,
      metadata: {
        analysisId,
        userId: user?.id
      }
    };
    
    debouncedStateUpdate(prevState => {
      const newHistory = [
        ...prevState.modificationState.modificationHistory,
        modificationEntry
      ].slice(-prevState.modificationState.maxHistorySize);
      
      return {
        ...prevState,
        modificationState: {
          ...prevState.modificationState,
          modificationHistory: newHistory,
          hasUnseenModifications: true,
          lastModificationTime: new Date()
        }
      };
    });
  }, [validatedOptions.enableModificationTracking, analysisId, user, debouncedStateUpdate]);
  
  const markModificationsSeen = useCallback(() => {
    debouncedStateUpdate(prevState => ({
      ...prevState,
      modificationState: {
        ...prevState.modificationState,
        hasUnseenModifications: false
      }
    }));
  }, [debouncedStateUpdate]);
  
  // ============================================================================
  // Visualization Mode Management
  // ============================================================================
  
  const setVisualizationMode = useCallback((mode) => {
    if (!isValidVisualizationMode(mode)) {
      handleError(new Error(`Invalid visualization mode: ${mode}`), VISUALIZATION_ERROR_TYPES.PERFORMANCE_ERROR);
      return;
    }
    
    debouncedStateUpdate(prevState => ({
      ...prevState,
      currentMode: mode
    }));
  }, [debouncedStateUpdate, handleError]);
  
  // ============================================================================
  // WebSocket Event Handlers
  // ============================================================================
  
  const handleWebSocketUpdate = useCallback((eventData) => {
    const now = Date.now();
    
    // Throttle WebSocket updates to prevent excessive re-renders
    if (now - lastWebSocketUpdateRef.current < 100) {
      return;
    }
    
    lastWebSocketUpdateRef.current = now;
    
    try {
      switch (eventData.type) {
        case 'analysis_progress':
          // Update confidence cache with new frame data
          if (eventData.frameData && validatedOptions.enableConfidenceCaching) {
            updateConfidenceCache(eventData.frameData.frameNumber, eventData.frameData);
          }
          break;
          
        case 'blockchain_update':
          if (validatedOptions.enableBlockchainMonitoring) {
            refreshBlockchainStatus();
          }
          break;
          
        case 'export_progress':
          if (validatedOptions.enableExportTracking && eventData.exportId === visualizationState.exportState.currentExport?.exportId) {
            debouncedStateUpdate(prevState => ({
              ...prevState,
              exportState: {
                ...prevState.exportState,
                currentExport: {
                  ...prevState.exportState.currentExport,
                  ...eventData.progress
                }
              }
            }));
          }
          break;
          
        case 'result_modification':
          if (validatedOptions.enableModificationTracking) {
            trackModification(
              eventData.modificationType,
              eventData.previousValue,
              eventData.newValue,
              'websocket'
            );
          }
          break;
          
        default:
          // Handle other WebSocket events
          break;
      }
    } catch (error) {
      handleError(error, VISUALIZATION_ERROR_TYPES.WEBSOCKET_ERROR, { eventData });
    }
  }, [
    validatedOptions.enableConfidenceCaching,
    validatedOptions.enableBlockchainMonitoring,
    validatedOptions.enableExportTracking,
    validatedOptions.enableModificationTracking,
    updateConfidenceCache,
    refreshBlockchainStatus,
    visualizationState.exportState.currentExport?.exportId,
    trackModification,
    debouncedStateUpdate,
    handleError
  ]);
  
  // ============================================================================
  // Performance Optimization
  // ============================================================================
  
  const optimizePerformance = useCallback(() => {
    if (!validatedOptions.enablePerformanceOptimization) return;
    
    try {
      // Clear old cache entries
      const cache = confidenceCacheRef.current;
      const now = Date.now();
      const maxAge = 5 * 60 * 1000; // 5 minutes
      
      for (const [key, value] of cache.entries()) {
        if (now - value.timestamp > maxAge) {
          cache.delete(key);
        }
      }
      
      // Optimize heatmap data if needed
      if (visualizationState.heatmapState.data && !visualizationState.heatmapState.isOptimized) {
        const optimizedData = optimizeHeatmapData(visualizationState.heatmapState.data);
        debouncedStateUpdate(prevState => ({
          ...prevState,
          heatmapState: {
            ...prevState.heatmapState,
            data: optimizedData,
            isOptimized: true
          },
          performanceMetrics: {
            ...prevState.performanceMetrics,
            lastOptimization: Date.now(),
            optimizationStats: {
              ...prevState.performanceMetrics.optimizationStats,
              heatmapOptimizations: (prevState.performanceMetrics.optimizationStats.heatmapOptimizations || 0) + 1
            }
          }
        }));
      }
      
    } catch (error) {
      handleError(error, VISUALIZATION_ERROR_TYPES.PERFORMANCE_ERROR, { action: 'optimize' });
    }
  }, [validatedOptions.enablePerformanceOptimization, visualizationState.heatmapState, optimizeHeatmapData, debouncedStateUpdate, handleError]);
  
  // ============================================================================
  // Utility Actions
  // ============================================================================
  
  const clearExportHistory = useCallback(() => {
    debouncedStateUpdate(prevState => ({
      ...prevState,
      exportState: {
        ...prevState.exportState,
        exportHistory: []
      }
    }));
  }, [debouncedStateUpdate]);
  
  const clearModificationHistory = useCallback(() => {
    debouncedStateUpdate(prevState => ({
      ...prevState,
      modificationState: {
        ...prevState.modificationState,
        modificationHistory: [],
        hasUnseenModifications: false
      }
    }));
  }, [debouncedStateUpdate]);
  
  const resetVisualizationState = useCallback(() => {
    setVisualizationState({
      ...DEFAULT_VISUALIZATION_STATE,
      currentMode: visualizationState.currentMode // Preserve current mode
    });
    confidenceCacheRef.current.clear();
    stateUpdateCount.current = 0;
    setError(null);
  }, [visualizationState.currentMode]);
  
  const refresh = useCallback(async () => {
    setIsLoading(true);
    
    try {
      // Refresh all visualization data
      await Promise.all([
        refreshBlockchainStatus(),
        // Add other refresh operations as needed
      ]);
      
      setIsLoading(false);
    } catch (error) {
      handleError(error, VISUALIZATION_ERROR_TYPES.PERFORMANCE_ERROR, { action: 'refresh' });
      setIsLoading(false);
    }
  }, [refreshBlockchainStatus, handleError]);
  
  // ============================================================================
  // Effects and Lifecycle Management
  // ============================================================================
  
  // Initialize visualization state
  useEffect(() => {
    if (!analysisId) return;
    
    setIsLoading(true);
    
    const initializeVisualization = async () => {
      try {
        // Initialize state with detection analysis data
        setVisualizationState(prevState => ({
          ...prevState,
          isInitialized: true,
          lastStateUpdate: Date.now()
        }));
        
        // Process initial heatmap data if available
        if (detectionAnalysis.frameAnalysis && validatedOptions.enableHeatmapProcessing) {
          const heatmapData = convertFrameAnalysisToHeatmap(detectionAnalysis.frameAnalysis);
          await processHeatmapData(heatmapData);
        }
        
        setIsLoading(false);
      } catch (error) {
        handleError(error, VISUALIZATION_ERROR_TYPES.PERFORMANCE_ERROR, { action: 'initialize' });
        setIsLoading(false);
      }
    };
    
    initializeVisualization();
  }, [analysisId, detectionAnalysis.frameAnalysis, validatedOptions.enableHeatmapProcessing, processHeatmapData, handleError]);
  
  // WebSocket subscription management
  useEffect(() => {
    if (!isConnected || !analysisId) return;
    
    const eventTypes = ['analysis_progress', 'blockchain_update', 'export_progress', 'result_modification'];
    
    eventTypes.forEach(eventType => {
      subscribe(eventType, handleWebSocketUpdate);
    });
    
    return () => {
      eventTypes.forEach(eventType => {
        unsubscribe(eventType, handleWebSocketUpdate);
      });
    };
  }, [isConnected, analysisId, subscribe, unsubscribe, handleWebSocketUpdate]);
  
  // Performance optimization interval
  useEffect(() => {
    if (!validatedOptions.enablePerformanceOptimization) return;
    
    const interval = setInterval(optimizePerformance, 30000); // Every 30 seconds
    
    return () => clearInterval(interval);
  }, [validatedOptions.enablePerformanceOptimization, optimizePerformance]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
      confidenceCacheRef.current.clear();
    };
  }, []);
  
  // ============================================================================
  // Helper Functions
  // ============================================================================
  
  const convertFrameAnalysisToHeatmap = useCallback((frameAnalysis) => {
    const dataPoints = frameAnalysis.map((frame, index) => ({
      x: Math.random(), // Placeholder - would be calculated from frame data
      y: Math.random(), // Placeholder - would be calculated from frame data
      intensity: frame.confidence || 0,
      confidence: frame.confidence || 0,
      frameNumber: index,
      regionType: 'detection'
    }));
    
    return {
      dataPoints,
      frameCount: frameAnalysis.length,
      maxIntensity: Math.max(...dataPoints.map(p => p.intensity)),
      minIntensity: Math.min(...dataPoints.map(p => p.intensity)),
      metadata: {
        source: 'frame_analysis',
        processedAt: Date.now()
      },
      processingTime: 0
    };
  }, []);
  
  // ============================================================================
  // Return Hook Interface
  // ============================================================================
  
  const actions = useMemo(() => ({
    setVisualizationMode,
    updateConfidenceCache,
    processHeatmapData,
    initiateExport,
    cancelExport,
    retryExport,
    clearExportHistory,
    refreshBlockchainStatus,
    markModificationsSeen,
    clearModificationHistory,
    resetVisualizationState,
    optimizePerformance
  }), [
    setVisualizationMode,
    updateConfidenceCache,
    processHeatmapData,
    initiateExport,
    cancelExport,
    retryExport,
    clearExportHistory,
    refreshBlockchainStatus,
    markModificationsSeen,
    clearModificationHistory,
    resetVisualizationState,
    optimizePerformance
  ]);
  
  const cleanup = useCallback(() => {
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }
    confidenceCacheRef.current.clear();
    stateUpdateCount.current = 0;
  }, []);
  
  return {
    visualizationState,
    actions,
    detectionAnalysis,
    isLoading,
    error,
    performanceMetrics,
    canExport,
    hasUnseenModifications,
    refresh,
    cleanup
  };
};

// ============================================================================
// Export
// ============================================================================

export default useResultVisualization;
