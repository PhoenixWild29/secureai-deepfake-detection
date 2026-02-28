/**
 * useStatusTracking Hook
 * Specialized React hook that extends useDetectionAnalysis with comprehensive status tracking capabilities,
 * providing centralized state management for progress visualization, error recovery, and notification handling.
 */

import { 
  useState, 
  useEffect, 
  useCallback, 
  useRef, 
  useMemo,
  useReducer 
} from 'react';
import { useDetectionAnalysis } from './useDetectionAnalysis';
import { useWebSocketEvents, useAnalysisWebSocketEvents } from './useWebSocketEvents';
import { 
  EVENT_TYPES, 
  ANALYSIS_STAGES,
  WebSocketUtils,
  StatusUpdate,
  ResultUpdate,
  ErrorEvent,
  StageTransitionEvent,
  StatusStreamingEvent
} from '../utils/websocketTypes';

// ============================================================================
// Hook Configuration Types
// ============================================================================

/**
 * Status tracking configuration options
 */
const DEFAULT_STATUS_TRACKING_CONFIG = {
  // WebSocket configuration
  enableRealTimeUpdates: true,
  websocketUrl: 'ws://localhost:8000/ws',
  jwtToken: null,
  
  // Performance optimization
  enableStateBatching: true,
  batchIntervalMs: 100,
  enableMemoization: true,
  
  // Persistence configuration
  persistNotificationPreferences: true,
  persistErrorRecovery: true,
  storageKey: 'secureai_status_tracking',
  
  // Error handling
  maxRetryAttempts: 3,
  retryDelayMs: 2000,
  enableAutoRecovery: true,
  
  // Notification preferences
  defaultNotificationTypes: [
    'status_update',
    'stage_transition', 
    'error_notification',
    'completion_notification'
  ],
  enableDesktopNotifications: false,
  enableSoundNotifications: false
};

// ============================================================================
// State Management - Enhanced Status Tracking State
// ============================================================================

/**
 * Initial state for status tracking
 */
const initialStatusTrackingState = {
  // Processing stage management
  currentStage: ANALYSIS_STAGES.INITIALIZING,
  previousStage: null,
  stageProgress: 0,
  stageTransitions: [],
  stageHistory: [],
  
  // Error state management
  errorDetails: null,
  errorHistory: [],
  recoveryStatus: {
    isRecovering: false,
    retryAttempts: 0,
    maxRetries: 3,
    lastRetryTime: null,
    recoveryStrategies: []
  },
  
  // Notification preferences
  notificationPreferences: {
    enabledTypes: new Set(['status_update', 'stage_transition', 'error_notification']),
    deliveryMethods: {
      websocket: true,
      desktop: false,
      sound: false,
      visual: true
    },
    userPreferences: {
      respectDoNotDisturb: true,
      priorityNotificationsOnly: false,
      batchNotifications: true
    }
  },
  
  // Performance metrics
  performanceMetrics: {
    averageStageDuration: {},
    resourceUtilization: {
      cpu: 0,
      memory: 0,
      efficiency: 0
    },
    lastUpdateTime: null,
    updateFrequency: 0
  },
  
  // Real-time update tracking
  realTimeState: {
    isConnected: false,
    lastHeartbeat: null,
    connectionQuality: 'unknown',
    missedHeartbeats: 0,
    reconnectAttempts: 0
  },
  
  // Optimized state for high-frequency updates
  batchedUpdates: [],
  lastBatchedUpdateTime: null,
  
  // State version and validation
  stateVersion: 1,
  lastValidated: null
};

/**
 * Status tracking state reducer for complex state updates
 */
function statusTrackingReducer(state, action) {
  switch (action.type) {
    case 'STAGE_TRANSITION':
      return {
        ...state,
        previousStage: state.currentStage,
        currentStage: action.payload.toStage,
        stageProgress: action.payload.stageProgress || 0,
        stageTransitions: [
          ...state.stageTransitions.slice(-9), // Keep last 10 transitions
          {
            timestamp: action.payload.timestamp,
            fromStage: action.payload.fromStage,
            toStage: action.payload.toStage,
            transitionReason: action.payload.transitionReason,
            duration: action.payload.duration
          }
        ],
        stageHistory: [
          ...state.stageHistory.slice(-49), // Keep last 50 history entries
          {
            stage: action.payload.toStage,
            timestamp: action.payload.timestamp,
            progress: action.payload.stageProgress || 0
          }
        ]
      };
      
    case 'PROGRESS_UPDATE':
      return {
        ...state,
        stageProgress: action.payload.stageProgress,
        performanceMetrics: {
          ...state.performanceMetrics,
          lastUpdateTime: action.payload.timestamp,
          updateFrequency: state.performanceMetrics.updateFrequency + 1,
          resourceUtilization: action.payload.resourceUtilization || state.performanceMetrics.resourceUtilization
        }
      };
      
    case 'ERROR_OCCURRED':
      return {
        ...state,
        errorDetails: {
          ...action.payload,
          timestamp: new Date().toISOString(),
          id: `error_${Date.now()}`
        },
        errorHistory: [
          ...state.errorHistory.slice(-19), // Keep last 20 errors
          {
            ...action.payload,
            timestamp: new Date().toISOString(),
            id: `error_${Date.now()}`
          }
        ]
      };
      
    case 'RECOVERY_ATTEMPT':
      return {
        ...state,
        recoveryStatus: {
          ...state.recoveryStatus,
          isRecovering: true,
          retryAttempts: state.recoveryStatus.retryAttempts + 1,
          lastRetryTime: new Date().toISOString(),
          recoveryStrategies: [
            ...state.recoveryStatus.recoveryStrategies,
            action.payload.strategy
          ]
        }
      };
      
    case 'RECOVERY_SUCCESS':
      return {
        ...state,
        recoveryStatus: {
          ...state.recoveryStatus,
          isRecovering: false,
          lastRecoveryTime: new Date().toISOString()
        },
        errorDetails: null
      };
      
    case 'CONNECTION_STATUS_CHANGE':
      return {
        ...state,
        realTimeState: {
          ...state.realtimeState,
          isConnected: action.payload.isConnected,
          connectionQuality: action.payload.quality,
          reconnectAttempts: action.payload.isConnected ? 0 : state.realtimeState.reconnectAttempts + 1
        }
      };
      
    case 'BATCH_UPDATES':
      return {
        ...state,
        batchedUpdates: action.payload.updates,
        lastBatchedUpdateTime: action.payload.timestamp
      };
      
    case 'UPDATE_NOTIFICATION_PREFERENCES':
      return {
        ...state,
        notificationPreferences: {
          ...state.notificationPreferences,
          ...action.payload
        }
      };
      
    case 'RESET_STATE':
      return {
        ...initialStatusTrackingState,
        notificationPreferences: state.notificationPreferences, // Preserve notification preferences
        stateVersion: state.stateVersion + 1
      };
      
    default:
      return state;
  }
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * State persistence utilities
 */
const StatePersistence = {
  save: (key, data) => {
    try {
      const serialized = JSON.stringify({
        ...data,
        timestamp: new Date().toISOString()
      });
      localStorage.setItem(key, serialized);
    } catch (error) {
      console.warn('Failed to save state to localStorage:', error);
    }
  },
  
  load: (key) => {
    try {
      const stored = localStorage.getItem(key);
      return stored ? JSON.parse(stored) : null;
    } catch (error) {
      console.warn('Failed to load state from localStorage:', error);
      return null;
    }
  },
  
  clear: (key) => {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.warn('Failed to clear state from localStorage:', error);
    }
  }
};

/**
 * Performance optimization utilities
 */
const PerformanceOptimizer = {
  // Debounce function for high-frequency updates
  debounce: (func, delay) => {
    let timeoutId;
    return (...args) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func.apply(null, args), delay);
    };
  },
  
  // Throttle function for rate limiting
  throttle: (func, limit) => {
    let inThrottle;
    return (...args) => {
      if (!inThrottle) {
        func.apply(null, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  },
  
  // Memoize expensive calculations
  memoize: (func, keyGenerator) => {
    const cache = new Map();
    return (...args) => {
      const key = keyGenerator ? keyGenerator(...args) : JSON.stringify(args);
      if (cache.has(key)) {
        return cache.get(key);
      }
      const result = func(...args);
      cache.set(key, result);
      return result;
    };
  }
};

// ============================================================================
// Main Hook Implementation
// ============================================================================

/**
 * Enhanced status tracking hook that extends useDetectionAnalysis
 * @param {string} analysisId - Analysis identifier
 * @param {Object} config - Status tracking configuration
 * @returns {Object} Status tracking state and controls
 */
export const useStatusTracking = (analysisId, config = {}) => {
  // Merge configuration with defaults
  const options = { ...DEFAULT_STATUS_TRACKING_CONFIG, ...config };
  
  // Initialize state reducer for complex state management
  const [statusTrackingState, dispatch] = useReducer(
    statusTrackingReducer,
    initialStatusTrackingState
  );
  
  // Initialize existing detection analysis hook
  const detectionAnalysis = useDetectionAnalysis(analysisId, {
    websocketUrl: options.websocketUrl,
    maxRetries: options.maxRetryAttempts,
    timeout: config.timeout || 300,
    enableBlockchain: config.enableBlockchain !== false,
    modelType: config.modelType || 'ensemble',
    customParams: config.customParams || {}
  });
  
  // WebSocket integration for real-time updates
  const webSocketEvents = useAnalysisWebSocketEvents(
    analysisId,
    options.jwtToken,
    {
      baseUrl: options.websocketUrl.replace(/^ws/, 'ws').replace(/\/[^/]*$/, ''),
      enableReconnection: true,
      heartbeatInterval: 30000,
      maxReconnectAttempts: 5
    }
  );
  
  // Refs for cleanup and performance optimization
  const batchUpdateTimeoutRef = useRef(null);
  const performanceMetricsRef = useRef({
    lastUpdateTime: null,
    updateCount: 0
  });
  
  // Create debounced update handler for performance optimization
  const debouncedBatchUpdate = useCallback(
    PerformanceOptimizer.debounce((updates) => {
      dispatch({
        type: 'BATCH_UPDATES',
        payload: {
          updates,
          timestamp: new Date().toISOString()
        }
      });
    }, options.batchIntervalMs),
    [options.batchIntervalMs]
  );
  
  // ============================================================================
  // State Persistence Management
  // ============================================================================
  
  // Load persisted notification preferences
  useEffect(() => {
    if (options.persistNotificationPreferences) {
      const storageKey = `${options.storageKey}_notifications`;
      const persisted = StatePersistence.load(storageKey);
      if (persisted) {
        dispatch({
          type: 'UPDATE_NOTIFICATION_PREFERENCES',
          payload: persisted
        });
      }
    }
  }, [options.storageKey, options.persistNotificationPreferences]);
  
  // Save notification preferences when they change
  useEffect(() => {
    if (options.persistNotificationPreferences) {
      const storageKey = `${options.storageKey}_notifications`;
      StatePersistence.save(storageKey, statusTrackingState.notificationPreferences);
    }
  }, [statusTrackingState.notificationPreferences, options.storageKey, options.persistNotificationPreferences]);
  
  // ============================================================================
  // WebSocket Event Handlers
  // ============================================================================
  
  // Handle stage transition events
  const handleStageTransition = useCallback((event) => {
    if (event.analysis_id === analysisId) {
      dispatch({
        type: 'STAGE_TRANSITION',
        payload: {
          timestamp: event.timestamp,
          fromStage: event.from_stage || statusTrackingState.currentStage,
          toStage: event.to_stage,
          stageProgress: event.stage_progress || 0,
          transitionReason: event.transition_reason || 'automatic',
          duration: event.stage_duration || 0
        }
      });
      
      // Trigger batched update for performance
      if (options.enableStateBatching) {
        debouncedBatchUpdate([{
          type: 'stage_transition',
          data: event,
          timestamp: new Date().toISOString()
        }]);
      }
    }
  }, [analysisId, statusTrackingState.currentStage, debouncedBatchUpdate, options.enableStateBatching]);
  
  // Handle status streaming events
  const handleStatusStreaming = useCallback((event) => {
    if (event.analysis_id === analysisId) {
      dispatch({
        type: 'PROGRESS_UPDATE',
        payload: {
          timestamp: event.timestamp,
          stageProgress: event.stage_progress || 0,
          resourceUtilization: {
            cpu: event.cpu_usage_percent || 0,
            memory: event.memory_usage_mb || 0,
            efficiency: event.processing_efficiency || 0
          }
        }
      });
      
      // Update detection analysis progress
      detectionAnalysis.handleProgressUpdate({
        analysis_id: analysisId,
        current_stage: event.current_stage,
        progress: event.overall_progress || 0,
        message: event.message || '',
        estimated_completion: event.estimated_completion,
        error: null
      });
    }
  }, [analysisId, statusTrackingState, detectionAnalysis]);
  
  // Handle error events
  const handleErrorEvent = useCallback((event) => {
    if (event.analysis_id === analysisId) {
      dispatch({
        type: 'ERROR_OCCURRED',
        payload: {
          error_code: event.error_code,
          error_message: event.error_message,
          error_details: event.error_details,
          stage: statusTrackingState.currentStage,
          severity: event.error_severity || 'error',
          recoverable: event.recoverable !== false
        }
      });
      
      // Trigger recovery attempt if enabled
      if (options.enableAutoRecovery && event.recoverable !== false) {
        dispatch({
          type: 'RECOVERY_ATTEMPT',
          payload: {
            strategy: event.recovery_strategy || 'retry',
            timestamp: new Date().toISOString()
          }
        });
      }
    }
  }, [analysisId, statusTrackingState.currentStage, options.enableAutoRecovery]);
  
  // Handle connection status changes
  const handleConnectionStatusChange = useCallback((isConnected, quality = 'unknown') => {
    dispatch({
      type: 'CONNECTION_STATUS_CHANGE',
      payload: {
        isConnected,
        quality,
        timestamp: new Date().toISOString()
      }
    });
  }, []);
  
  // ============================================================================
  // WebSocket Event Subscriptions
  // ============================================================================
  
  // Subscribe to WebSocket events when connection is established
  useEffect(() => {
    if (webSocketEvents.isConnected && analysisId) {
      // Subscribe to stage transition events
      webSocketEvents.subscribe(EVENT_TYPES.STAGE_TRANSITION, handleStageTransition);
      
      // Subscribe to status streaming events
      webSocketEvents.subscribe(EVENT_TYPES.STATUS_STREAMING, handleStatusStreaming);
      
      // Subscribe to error events
      webSocketEvents.subscribe(EVENT_TYPES.ERROR, handleErrorEvent);
      
      // Handle connection status changes
      webSocketEvents.subscribe(EVENT_TYPES.CONNECTION_ESTABLISHED, () => 
        handleConnectionStatusChange(true, 'good')
      );
      
      // Cleanup subscriptions on unmount
      return () => {
        webSocketEvents.unsubscribe(EVENT_TYPES.STAGE_TRANSITION, handleStageTransition);
        webSocketEvents.unsubscribe(EVENT_TYPES.STATUS_STREAMING, handleStatusStreaming);
        webSocketEffects.unsubscribe(EVENT_TYPES.ERROR, handleErrorEvent);
      };
    }
  }, [
    webSocketEvents.isConnected,
    analysisId,
    handleStageTransition,
    handleStatusStreaming,
    handleErrorEvent,
    handleConnectionStatusChange
  ]);
  
  // ============================================================================
  // State Selectors (Memoized for Performance)
  // ============================================================================
  
  // Progress tracking selectors
  const progressSelectors = useMemo(() => ({
    getOverallProgress: () => detectionAnalysis.analysisProgress,
    getStageProgress: () => statusTrackingState.stageProgress,
    getCurrentStage: () => statusTrackingState.currentStage,
    getStageHistory: () => statusTrackingState.stageHistory.slice(-10), // Last 10 stages
    getTransitions: () => statusTrackingState.stageTransitions.slice(-5), // Last 5 transitions
    getFormattedProgress: () => `${Math.round(statusTrackingState.stageProgress * 100)}%`,
    getStageDisplayName: () => WebSocketUtils.getStageDisplayName(statusTrackingState.currentStage),
    getTimeRemaining: () => {
      if (detectionAnalysis.analysisResult?.estimated_completion) {
        return WebSocketUtils.formatTimeRemaining(detectionAnalysis.analysisResult.estimated_completion);
      }
      return 'Calculating...';
    }
  }), [
    detectionAnalysis.analysisProgress,
    statusTrackingState.stageProgress,
    statusTrackingState.currentStage,
    statusTrackingState.stageHistory,
    statusTrackingState.stageTransitions,
    detectionAnalysis.analysisResult
  ]);
  
  // Error recovery selectors
  const errorRecoverySelectors = useMemo(() => ({
    hasErrors: () => statusTrackingState.errorDetails !== null,
    getCurrentError: () => statusTrackingState.errorDetails,
    getErrorHistory: () => statusTrackingState.errorHistory.slice(-10), // Last 10 errors
    getRecoveryStatus: () => statusTrackingState.recoveryStatus,
    isRecovering: () => statusTrackingState.recoveryStatus.isRecovering,
    getRetryAttempts: () => statusTrackingState.recoveryStatus.retryAttempts,
    getRecoveryStrategies: () => statusTrackingState.recoveryStatus.recoveryStrategies,
    canRetry: () => statusTrackingState.recoveryStatus.retryAttempts < statusTrackingState.recoveryStatus.maxRetries,
    getNextRetryTime: () => {
      const lastRetry = statusTrackingState.recoveryStatus.lastRetryTime;
      if (!lastRetry) return null;
      const nextRetryTime = new Date(lastRetry).getTime() + options.retryDelayMs;
      return new Date(nextRetryTime);
    }
  }), [statusTrackingState.errorDetails, statusTrackingState.recoveryStatus, options.retryDelayMs]);
  
  // Notification management selectors
  const notificationSelectors = useMemo(() => ({
    isNotificationTypeEnabled: (type) => statusTrackingState.notificationPreferences.enabledTypes.has(type),
    getEnabledNotificationTypes: () => Array.from(statusTrackingState.notificationPreferences.enabledTypes),
    getDeliveryMethods: () => statusTrackingState.notificationPreferences.deliveryMethods,
    getUserPreferences: () => statusTrackingState.notificationPreferences.userPreferences,
    canReceiveNotifications: () => {
      const methods = statusTrackingState.realtimePreferences.deliveryMethods;
      return methods.websocket || methods.desktop || methods.visual;
    },
    shouldShowNotification: (type) => {
      return statusTrackingState.notificationPreferences.enabledTypes.has(type) &&
             statusTrackingState.realtimeState.isConnected;
    }
  }), [statusTrackingState.notificationPreferences, statusTrackingState.realtimeState.isConnected]);
  
  // ============================================================================
  // Control Functions
  // ============================================================================
  
  // Enhanced error recovery controls
  const errorRecoveryControls = useCallback({
    attemptRecovery: async (strategy = 'retry') => {
      dispatch({
        type: 'RECOVERY_ATTEMPT',
        payload: {
          strategy,
          timestamp: new Date().toISOString()
        }
      });
      
      try {
        // Trigger retry from detection analysis
        await detectionAnalysis.retryAnalysis();
        
        dispatch({
          type: 'RECOVERY_SUCCESS',
          payload: {
            strategy,
            timestamp: new Date().toISOString()
          }
        });
        
        return true;
      } catch (error) {
        console.error('Recovery attempt failed:', error);
        return false;
      }
    },
    
    clearErrors: () => {
      dispatch({
        type: 'ERROR_OCCURRED',
        payload: null
      });
    },
    
    updateRecoverySettings: (settings) => {
      dispatch({
        type: 'RECOVERY_ATTEMPT',
        payload: {
          strategy: 'settings_update',
          ...settings
        }
      });
    }
  }, [detectionAnalysis]);
  
  // Notification preference controls
  const notificationControls = useCallback({
    enableNotificationType: (type) => {
      const newTypes = new Set([...statusTrackingState.notificationPreferredTypes.enabledTypes, type]);
      dispatch({
        type: 'UPDATE_NOTIFICATION_PREFERENCES',
        payload: {
          enabledTypes: newTypes
        }
      });
    },
    
    disableNotificationType: (type) => {
      const newTypes = new Set([...statusTrackingState.realtimePreferences.enabledTypes]);
      newTypes.delete(type);
      dispatch({
        type: 'UPDATE_NOTIFICATION_PREFERENCES',
        payload: {
          enabledTypes: newTypes
        }
      });
    },
    
    updateDeliveryMethod: (method, enabled) => {
      dispatch({
        type: 'UPDATE_NOTIFICATION_PREFERENCES',
        payload: {
          deliveryMethods: {
            ...statusTrackingState.notificationPreferences.deliveryMethods,
            [method]: enabled
          }
        }
      });
    },
    
    updateUserPreferences: (preferences) => {
      dispatch({
        type: 'UPDATE_NOTIFICATION_PREFERENCES',
        payload: {
          userPreferences: {
            ...statusTrackingState.notificationPreferences.userPreferences,
            ...preferences
          }
        }
      });
    }
  }, [statusTrackingState.notificationPreferences]);
  
  // Performance optimization controls
  const performanceControls = useCallback({
    resetPerformanceMetrics: () => {
      dispatch({
        type: 'PROGRESS_UPDATE',
        payload: {
          timestamp: new Date().toISOString(),
          resetMetrics: true
        }
      });
    },
    
    optimizeBatchInterval: (intervalMs) => {
      // Update batch interval for real-time optimization
      if (intervalMs !== options.batchIntervalMs) {
        // Recreate debounced function with new interval
        debouncedBatchUpdate = PerformanceOptimizer.debounce((updates) => {
          dispatch({
            type: 'BATCH_UPDATES',
            payload: {
              updates,
              timestamp: new Date().toISOString()
            }
          });
        }, intervalMs);
      }
    }
  }, [options.batchIntervalMs]);
  
  // ============================================================================
  // Cleanup and Effect Management
  // ============================================================================
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (batchUpdateTimeoutRef.current) {
        clearTimeout(batchUpdateTimeoutRef.current);
      }
    };
  }, []);
  
  // Performance monitoring effect
  useEffect(() => {
    const now = Date.now();
    const metrics = performanceMetricsRef.current;
    
    if (metrics.lastUpdateTime) {
      const updateInterval = now - metrics.lastUpdateTime;
      metrics.updateCount++;
      
      // Reset metrics every 10 seconds
      if (updateInterval > 10000) {
        metrics.updateCount = 0;
        metrics.lastUpdateTime = now;
      }
    } else {
      metrics.lastUpdateTime = now;
    }
    
    performanceMetricsRef.current = metrics;
  }, [statusTrackingState.currentStage]);
  
  // ============================================================================
  // Return Hook Interface
  // ============================================================================
  
  return useMemo(() => ({
    // Extended from useDetectionAnalysis
    ...detectionAnalysis,
    
    // Enhanced status tracking state
    statusTracking: {
      currentStage: statusTrackingState.currentStage,
      previousStage: statusTrackingState.previousStage,
      stageProgress: statusTrackingState.stageProgress,
      stageTransitions: statusTrackingState.stageTransitions,
      stageHistory: statusTrackingState.stageHistory,
      errorDetails: statusTrackingState.errorDetails,
      errorHistory: statusTrackingState.errorHistory,
      recoveryStatus: statusTrackingState.recoveryStatus,
      notificationPreferences: statusTrackingState.notificationPreferences,
      performanceMetrics: statusTrackingState.performanceMetrics,
      realTimeState: statusTrackingState.realtimeState
    },
    
    // State selectors for efficient access
    selectors: {
      progress: progressSelectors,
      errorRecovery: errorRecoverySelectors,
      notifications: notificationSelectors
    },
    
    // Control functions
    controls: {
      errorRecovery: errorRecoveryControls,
      notifications: notificationControls,
      performance: performanceControls,
      // Inherited controls from detectionAnalysis
      startAnalysis: detectionAnalysis.startAnalysis,
      retryAnalysis: detectionAnalysis.retryAnalysis,
      cancelAnalysis: detectionAnalysis.cancelAnalysis
    },
    
    // WebSocket integration
    webSocket: {
      isConnected: webSocketEvents.isConnected,
      connectionState: webSocketEvents.connectionState,
      lastMessage: webSocketEvents.lastMessage,
      error: webSocketEvents.error,
      stats: webSocketEvents.stats,
      sendMessage: webSocketEvents.sendMessage
    },
    
    // Performance and state information
    performance: {
      updateFrequency: statusTrackingState.performanceMetrics.updateFrequency,
      resourceUtilization: statusTrackingState.performanceMetrics.resourceUtilization,
      batchedUpdates: statusTrackingState.batchedUpdates,
      stateVersion: statusTrackingState.stateVersion
    },
    
    // Utility functions
    utils: {
      getStageDisplayName: progressSelectors.getStageDisplayName,
      getFormattedProgress: progressSelectors.getFormattedProgress,
      getTimeRemaining: progressSelectors.getTimeRemaining,
      canRetry: errorRecoverySelectors.canRetry,
      isRecovering: errorRecoverySelectors.isRecovering,
      isNotificationTypeEnabled: notificationSelectors.isNotificationTypeEnabled,
      shouldShowNotification: notificationSelectors.shouldShowNotification
    }
  }), [
    detectionAnalysis,
    statusTrackingState,
    progressSelectors,
    errorRecoverySelectors,
    notificationSelectors,
    errorRecoveryControls,
    notificationControls,
    performanceControls,
    webSocketEvents
  ]);
};

// ============================================================================
// Convenience Hooks and Utilities
// ============================================================================

/**
 * Hook for status tracking with simplified interface
 * @param {string} analysisId - Analysis identifier
 * @param {Object} config - Simplified configuration
 */
export const useStatusTrackingSimple = (analysisId, config = {}) => {
  const statusTracking = useStatusTracking(analysisId, config);
  
  return useMemo(() => ({
    // Simplified state
    stage: statusTracking.statusTracking.currentStage,
    stageProgress: statusTracking.statusTracking.stageProgress,
    overallProgress: statusTracking.analysisProgress,
    hasErrors: statusTracking.selectors.errorRecovery.hasErrors(),
    isRecovering: statusTracking.selectors.errorRecovery.isRecovering(),
    isConnected: statusTracking.webSocket.isConnected,
    
    // Simplified controls
    retry: statusTracking.controls.startAnalysis,
    clearError: statusTracking.controls.errorRecovery.clearErrors,
    enableNotifications: statusTracking.controls.notifications.enableNotificationType,
    disableNotifications: statusTracking.controls.notifications.disableNotificationType
  }), [statusTracking]);
};

/**
 * Hook for notification management only
 * @param {Object} config - Notification configuration
 */
export const useNotificationManagement = (config = {}) => {
  const [preferences, setPreferences] = useState(config.defaultPreferences || {
    enabledTypes: new Set(['status_update', 'stage_transition']),
    deliveryMethods: { websocket: true, desktop: false },
    userPreferences: { batchNotifications: true }
  });
  
  const controls = useCallback({
    enableType: (type) => {
      setPreferences(prev => ({
        ...prev,
        enabledTypes: new Set([...prev.enabledTypes, type])
      }));
    },
    
    disableType: (type) => {
      setPreferences(prev => {
        const newTypes = new Set([...prev.enabledTypes]);
        newTypes.delete(type);
        return {
          ...prev,
          enabledTypes: newTypes
        };
      });
    },
    
    updateDeliveryMethod: (method, enabled) => {
      setPreferences(prev => ({
        ...prev,
        deliveryMethods: {
          ...prev.deliveryMethods,
          [method]: enabled
        }
      }));
    }
  }, []);
  
  return {
    preferences,
    ...controls,
    isEnabled: (type) => preferences.enabledTypes.has(type)
  };
};

// Export default hook
export default useStatusTracking;

// Export all utilities and types
export {
  DEFAULT_STATUS_TRACKING_CONFIG as StatusTrackingConfig,
  StatePersistence,
  PerformanceOptimizer,
  statusTrackingReducer as StatusTrackingReducer
};
