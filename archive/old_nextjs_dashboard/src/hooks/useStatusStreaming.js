/**
 * useStatusStreaming Hook
 * React hook for managing WebSocket status streaming connections with automatic reconnection
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useWebSocket } from './useWebSocket';
import { 
  EVENT_TYPES, 
  ANALYSIS_STAGES, 
  StageTransitionEvent, 
  StatusStreamingEvent,
  WebSocketMessageParser 
} from '../utils/websocketTypes';

/**
 * Custom hook for status streaming with enhanced features
 * @param {Object} config - Configuration object
 * @param {string} config.analysisId - Analysis ID to stream status for
 * @param {string} config.jwtToken - JWT authentication token
 * @param {boolean} config.autoConnect - Whether to connect automatically (default: true)
 * @param {number} config.reconnectInterval - Reconnection interval in ms (default: 3000)
 * @param {number} config.maxReconnectAttempts - Maximum reconnection attempts (default: 5)
 * @param {Function} config.onStageTransition - Callback for stage transition events
 * @param {Function} config.onStatusStreaming - Callback for status streaming events
 * @param {Function} config.onError - Callback for error events
 * @param {Function} config.onConnectionChange - Callback for connection state changes
 * @returns {Object} Status streaming state and controls
 */
export const useStatusStreaming = ({
  analysisId,
  jwtToken,
  autoConnect = true,
  reconnectInterval = 3000,
  maxReconnectAttempts = 5,
  onStageTransition,
  onStatusStreaming,
  onError,
  onConnectionChange
}) => {
  // State management
  const [currentStage, setCurrentStage] = useState(ANALYSIS_STAGES.INITIALIZING);
  const [overallProgress, setOverallProgress] = useState(0);
  const [stageProgress, setStageProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('Initializing...');
  const [estimatedCompletion, setEstimatedCompletion] = useState(null);
  const [framesProcessed, setFramesProcessed] = useState(0);
  const [totalFrames, setTotalFrames] = useState(0);
  const [processingRate, setProcessingRate] = useState(null);
  const [systemResources, setSystemResources] = useState({
    cpu: 'Unknown',
    memory: 'Unknown',
    efficiency: 'Unknown'
  });
  const [errorRecoveryStatus, setErrorRecoveryStatus] = useState(null);
  const [progressHistory, setProgressHistory] = useState([]);
  const [isCompleted, setIsCompleted] = useState(false);
  const [isFailed, setIsFailed] = useState(false);
  
  // Connection state
  const [connectionState, setConnectionState] = useState('disconnected');
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [lastEventTimestamp, setLastEventTimestamp] = useState(null);
  
  // Refs for cleanup and tracking
  const reconnectTimeoutRef = useRef(null);
  const messageParser = useRef(new WebSocketMessageParser());
  const lastHeartbeatRef = useRef(null);
  
  // WebSocket URL construction
  const getWebSocketUrl = useCallback(() => {
    if (!analysisId || !jwtToken) return null;
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const baseUrl = `${protocol}//${host}/ws/status/${analysisId}`;
    
    return `${baseUrl}?token=${encodeURIComponent(jwtToken)}`;
  }, [analysisId, jwtToken]);
  
  // Enhanced WebSocket connection with status streaming features
  const {
    connectionState: wsConnectionState,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
    isConnected
  } = useWebSocket({
    url: getWebSocketUrl(),
    autoConnect: false, // We'll handle connection manually
    reconnectInterval,
    maxReconnectAttempts,
    onConnectionChange: (state) => {
      setConnectionState(state);
      onConnectionChange?.(state);
    }
  });
  
  // Handle incoming WebSocket messages
  useEffect(() => {
    if (!lastMessage) return;
    
    try {
      const parsedMessage = messageParser.current.parseMessage(lastMessage);
      if (!parsedMessage) return;
      
      setLastEventTimestamp(new Date().toISOString());
      
      switch (parsedMessage.event_type) {
        case EVENT_TYPES.STAGE_TRANSITION:
          handleStageTransition(parsedMessage);
          break;
          
        case EVENT_TYPES.STATUS_STREAMING:
          handleStatusStreaming(parsedMessage);
          break;
          
        case EVENT_TYPES.ERROR:
          handleError(parsedMessage);
          break;
          
        case EVENT_TYPES.HEARTBEAT:
          handleHeartbeat(parsedMessage);
          break;
          
        case EVENT_TYPES.CONNECTION_ESTABLISHED:
          handleConnectionEstablished(parsedMessage);
          break;
          
        default:
          console.warn('Unknown event type:', parsedMessage.event_type);
      }
      
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
      onError?.(error);
    }
  }, [lastMessage]);
  
  // Handle stage transition events
  const handleStageTransition = useCallback((event) => {
    if (!StageTransitionEvent.validate(event)) {
      console.error('Invalid stage transition event:', event);
      return;
    }
    
    const stageEvent = new StageTransitionEvent(event);
    
    setCurrentStage(stageEvent.to_stage);
    setStageProgress(stageEvent.stage_progress);
    setEstimatedCompletion(stageEvent.estimated_stage_completion);
    
    // Update progress history
    setProgressHistory(prev => [
      ...prev.slice(-9), // Keep last 10 entries
      {
        timestamp: stageEvent.timestamp,
        fromStage: stageEvent.from_stage,
        toStage: stageEvent.to_stage,
        stageProgress: stageEvent.stage_progress,
        transitionReason: stageEvent.transition_reason
      }
    ]);
    
    // Reset reconnect attempts on successful stage transition
    setReconnectAttempts(0);
    
    onStageTransition?.(stageEvent);
  }, [onStageTransition]);
  
  // Handle status streaming events
  const handleStatusStreaming = useCallback((event) => {
    if (!StatusStreamingEvent.validate(event)) {
      console.error('Invalid status streaming event:', event);
      return;
    }
    
    const statusEvent = new StatusStreamingEvent(event);
    
    // Update all status fields
    setCurrentStage(statusEvent.current_stage);
    setOverallProgress(statusEvent.overall_progress);
    setStageProgress(statusEvent.stage_progress);
    setStatusMessage(statusEvent.message);
    setEstimatedCompletion(statusEvent.estimated_completion);
    setFramesProcessed(statusEvent.frames_processed);
    setTotalFrames(statusEvent.total_frames);
    setProcessingRate(statusEvent.processing_rate_fps);
    setSystemResources(statusEvent.getSystemResourceStatus());
    setErrorRecoveryStatus(statusEvent.error_recovery_status);
    setProgressHistory(statusEvent.progress_history || []);
    
    // Update completion status
    setIsCompleted(statusEvent.isCompleted());
    setIsFailed(statusEvent.isFailed());
    
    // Reset reconnect attempts on successful status update
    setReconnectAttempts(0);
    
    onStatusStreaming?.(statusEvent);
  }, [onStatusStreaming]);
  
  // Handle error events
  const handleError = useCallback((event) => {
    console.error('Status streaming error:', event);
    setIsFailed(true);
    onError?.(event);
  }, [onError]);
  
  // Handle heartbeat events
  const handleHeartbeat = useCallback((event) => {
    lastHeartbeatRef.current = new Date();
    // Reset reconnect attempts on heartbeat
    setReconnectAttempts(0);
  }, []);
  
  // Handle connection established events
  const handleConnectionEstablished = useCallback((event) => {
    console.log('Status streaming connection established:', event.message);
    setReconnectAttempts(0);
    
    // Request current status
    sendMessage(JSON.stringify({
      type: 'get_current_status',
      timestamp: new Date().toISOString()
    }));
  }, [sendMessage]);
  
  // Enhanced connection management
  const connectWithRetry = useCallback(async () => {
    if (reconnectAttempts >= maxReconnectAttempts) {
      console.error('Maximum reconnection attempts reached');
      setConnectionState('error');
      return false;
    }
    
    try {
      setConnectionState('connecting');
      const success = await connect();
      
      if (success) {
        setReconnectAttempts(0);
        setConnectionState('connected');
        return true;
      } else {
        throw new Error('Connection failed');
      }
      
    } catch (error) {
      console.error('Connection attempt failed:', error);
      setReconnectAttempts(prev => prev + 1);
      setConnectionState('reconnecting');
      
      // Schedule retry
      if (reconnectAttempts < maxReconnectAttempts) {
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWithRetry();
        }, reconnectInterval);
      } else {
        setConnectionState('error');
      }
      
      return false;
    }
  }, [connect, reconnectAttempts, maxReconnectAttempts, reconnectInterval]);
  
  // Auto-connect effect
  useEffect(() => {
    if (autoConnect && analysisId && jwtToken) {
      connectWithRetry();
    }
    
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [autoConnect, analysisId, jwtToken, connectWithRetry]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      disconnect();
    };
  }, [disconnect]);
  
  // Manual connection controls
  const manualConnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    setReconnectAttempts(0);
    return connectWithRetry();
  }, [connectWithRetry]);
  
  const manualDisconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    disconnect();
    setConnectionState('disconnected');
  }, [disconnect]);
  
  // Utility functions
  const requestCurrentStatus = useCallback(() => {
    if (isConnected) {
      sendMessage(JSON.stringify({
        type: 'get_current_status',
        timestamp: new Date().toISOString()
      }));
    }
  }, [isConnected, sendMessage]);
  
  const ping = useCallback(() => {
    if (isConnected) {
      sendMessage(JSON.stringify({
        type: 'ping',
        timestamp: new Date().toISOString()
      }));
    }
  }, [isConnected, sendMessage]);
  
  // Connection health check
  const isConnectionHealthy = useCallback(() => {
    if (!isConnected) return false;
    
    const now = new Date();
    const lastHeartbeat = lastHeartbeatRef.current;
    
    if (!lastHeartbeat) return true; // No heartbeat yet, assume healthy
    
    // Consider connection unhealthy if no heartbeat for 30 seconds
    return (now - lastHeartbeat) < 30000;
  }, [isConnected]);
  
  // Return hook interface
  return {
    // Connection state
    connectionState,
    isConnected,
    isConnectionHealthy: isConnectionHealthy(),
    reconnectAttempts,
    maxReconnectAttempts,
    
    // Analysis status
    currentStage,
    overallProgress,
    stageProgress,
    statusMessage,
    estimatedCompletion,
    framesProcessed,
    totalFrames,
    processingRate,
    systemResources,
    errorRecoveryStatus,
    progressHistory,
    isCompleted,
    isFailed,
    
    // Event timestamps
    lastEventTimestamp,
    lastHeartbeat: lastHeartbeatRef.current,
    
    // Control functions
    connect: manualConnect,
    disconnect: manualDisconnect,
    requestCurrentStatus,
    ping,
    
    // Utility functions
    getOverallProgressPercentage: () => Math.round(overallProgress * 100),
    getStageProgressPercentage: () => Math.round(stageProgress * 100),
    getProcessingRateFormatted: () => processingRate ? `${processingRate.toFixed(1)} fps` : 'Calculating...',
    getEstimatedCompletionDate: () => estimatedCompletion ? new Date(estimatedCompletion) : null,
    getErrorRecoveryStatusText: () => {
      if (!errorRecoveryStatus) return 'No errors';
      const { has_errors, error_count, retry_attempts, max_retries, is_recovering } = errorRecoveryStatus;
      if (!has_errors) return 'No errors';
      if (is_recovering) return `Recovering (${retry_attempts}/${max_retries} attempts)`;
      if (retry_attempts >= max_retries) return `Failed after ${max_retries} attempts`;
      return `${error_count} error(s), ${retry_attempts}/${max_retries} retries`;
    }
  };
};

export default useStatusStreaming;
