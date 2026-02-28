/**
 * WebSocket Events Hook
 * Custom React hook for handling WebSocket events with type-safe validation
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useWebSocket } from './useWebSocket';
import { 
  EVENT_TYPES, 
  WebSocketMessageParser, 
  StatusUpdate, 
  ResultUpdate, 
  ErrorEvent 
} from '../utils/websocketTypes';

/**
 * WebSocket events configuration
 * @typedef {Object} WebSocketEventsConfig
 * @property {string} url - WebSocket URL
 * @property {string} token - JWT authentication token
 * @property {boolean} enableReconnection - Enable automatic reconnection (default: true)
 * @property {number} heartbeatInterval - Heartbeat interval in ms (default: 30000)
 * @property {number} maxReconnectAttempts - Maximum reconnection attempts (default: 5)
 * @property {number} reconnectInterval - Base reconnection interval in ms (default: 1000)
 * @property {number} pollingInterval - Polling interval in ms when WebSocket fails (default: 5000)
 */

/**
 * WebSocket events hook return value
 * @typedef {Object} WebSocketEventsReturn
 * @property {boolean} isConnected - Whether WebSocket is connected
 * @property {string} connectionState - Current connection state
 * @property {Function} subscribe - Subscribe to specific event types
 * @property {Function} unsubscribe - Unsubscribe from specific event types
 * @property {Function} sendMessage - Send message through WebSocket
 * @property {Object} lastMessage - Last received message
 * @property {string|null} error - Last error message
 * @property {Object} stats - Connection statistics
 */

/**
 * Custom hook for WebSocket events handling
 * @param {WebSocketEventsConfig} config - WebSocket configuration
 * @returns {WebSocketEventsReturn} - WebSocket events hook return value
 */
export const useWebSocketEvents = (config) => {
  const {
    url,
    token,
    enableReconnection = true,
    heartbeatInterval = 30000,
    maxReconnectAttempts = 5,
    reconnectInterval = 1000,
    pollingInterval = 5000
  } = config;

  // Event handlers registry
  const eventHandlersRef = useRef(new Map());
  const [lastMessage, setLastMessage] = useState(null);
  const [error, setError] = useState(null);

  // Use the base WebSocket hook
  const {
    connectionState,
    isConnected,
    sendMessage,
    reconnect,
    disconnect,
    stats
  } = useWebSocket({
    url,
    token,
    maxReconnectAttempts,
    reconnectInterval,
    heartbeatInterval,
    pollingInterval,
    enablePolling: enableReconnection
  });

  /**
   * Handle incoming WebSocket messages
   */
  const handleMessage = useCallback((message) => {
    try {
      const parsedMessage = WebSocketMessageParser.parseMessage(message);
      
      if (parsedMessage) {
        setLastMessage(parsedMessage);
        setError(null);
        
        // Call registered event handlers
        const eventType = parsedMessage.event_type;
        const handlers = eventHandlersRef.current.get(eventType) || [];
        
        handlers.forEach(handler => {
          try {
            handler(parsedMessage);
          } catch (error) {
            console.error(`Error in event handler for ${eventType}:`, error);
          }
        });
      } else {
        console.warn('Invalid WebSocket message:', message);
        setError('Invalid message format');
      }
    } catch (error) {
      console.error('Error handling WebSocket message:', error);
      setError('Message handling error');
    }
  }, []);

  /**
   * Subscribe to specific event types
   * @param {string} eventType - Event type to subscribe to
   * @param {Function} handler - Event handler function
   */
  const subscribe = useCallback((eventType, handler) => {
    if (!eventHandlersRef.current.has(eventType)) {
      eventHandlersRef.current.set(eventType, []);
    }
    
    const handlers = eventHandlersRef.current.get(eventType);
    handlers.push(handler);
    
    console.log(`Subscribed to ${eventType} events`);
  }, []);

  /**
   * Unsubscribe from specific event types
   * @param {string} eventType - Event type to unsubscribe from
   * @param {Function} handler - Event handler function to remove
   */
  const unsubscribe = useCallback((eventType, handler) => {
    const handlers = eventHandlersRef.current.get(eventType);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
        console.log(`Unsubscribed from ${eventType} events`);
      }
    }
  }, []);

  /**
   * Send a message through WebSocket
   * @param {string|Object} message - Message to send
   * @returns {boolean} - True if sent successfully
   */
  const sendWebSocketMessage = useCallback((message) => {
    return sendMessage(message);
  }, [sendMessage]);

  // Effect to handle incoming messages
  useEffect(() => {
    if (lastMessage) {
      handleMessage(lastMessage);
    }
  }, [lastMessage, handleMessage]);

  // Effect to handle connection errors
  useEffect(() => {
    if (stats.error) {
      setError(stats.error);
    }
  }, [stats.error]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      eventHandlersRef.current.clear();
    };
  }, []);

  return {
    isConnected,
    connectionState,
    subscribe,
    unsubscribe,
    sendMessage: sendWebSocketMessage,
    lastMessage,
    error,
    stats
  };
};

/**
 * Hook for analysis-specific WebSocket events
 * @param {string} analysisId - Analysis ID for WebSocket connection
 * @param {string} token - JWT authentication token
 * @param {Object} options - Additional options
 * @returns {WebSocketEventsReturn} - WebSocket events hook return value
 */
export const useAnalysisWebSocketEvents = (analysisId, token, options = {}) => {
  const baseUrl = options.baseUrl || 'ws://localhost:8000';
  const wsUrl = `${baseUrl}/ws/analysis/${analysisId}`;
  
  return useWebSocketEvents({
    url: wsUrl,
    token,
    ...options
  });
};

/**
 * Hook for processing progress events
 * @param {string} analysisId - Analysis ID
 * @param {Function} onProgress - Progress update handler
 * @param {Function} onComplete - Completion handler
 * @param {Function} onError - Error handler
 * @param {Object} options - Additional options
 * @returns {WebSocketEventsReturn} - WebSocket events hook return value
 */
export const useProcessingProgressEvents = (
  analysisId,
  onProgress,
  onComplete,
  onError,
  options = {}
) => {
  const token = options.token || 'demo_token'; // In production, get from auth context
  
  const {
    isConnected,
    connectionState,
    subscribe,
    unsubscribe,
    sendMessage,
    error,
    stats
  } = useAnalysisWebSocketEvents(analysisId, token, options);

  // Subscribe to progress events
  useEffect(() => {
    if (isConnected && analysisId) {
      // Subscribe to status updates
      subscribe(EVENT_TYPES.STATUS_UPDATE, (event) => {
        if (event.analysis_id === analysisId) {
          onProgress?.(event);
        }
      });

      // Subscribe to result updates
      subscribe(EVENT_TYPES.RESULT_UPDATE, (event) => {
        if (event.analysis_id === analysisId) {
          onComplete?.(event);
        }
      });

      // Subscribe to error events
      subscribe(EVENT_TYPES.ERROR, (event) => {
        if (event.analysis_id === analysisId) {
          onError?.(event);
        }
      });

      return () => {
        unsubscribe(EVENT_TYPES.STATUS_UPDATE, onProgress);
        unsubscribe(EVENT_TYPES.RESULT_UPDATE, onComplete);
        unsubscribe(EVENT_TYPES.ERROR, onError);
      };
    }
  }, [isConnected, analysisId, subscribe, unsubscribe, onProgress, onComplete, onError]);

  return {
    isConnected,
    connectionState,
    subscribe,
    unsubscribe,
    sendMessage,
    error,
    stats
  };
};

/**
 * Hook for connection status display
 * @param {string} connectionState - Current connection state
 * @returns {Object} - Status display information
 */
export const useConnectionStatusDisplay = (connectionState) => {
  const getStatusInfo = useCallback(() => {
    switch (connectionState) {
      case 'connecting':
        return {
          text: 'Connecting...',
          color: '#f59e0b',
          icon: '🔄',
          description: 'Establishing connection to server'
        };
        
      case 'connected':
        return {
          text: 'Connected',
          color: '#10b981',
          icon: '🟢',
          description: 'Real-time updates active'
        };
        
      case 'disconnected':
        return {
          text: 'Disconnected',
          color: '#6b7280',
          icon: '⚫',
          description: 'Connection lost'
        };
        
      case 'reconnecting':
        return {
          text: 'Reconnecting...',
          color: '#f59e0b',
          icon: '🔄',
          description: 'Attempting to reconnect'
        };
        
      case 'error':
        return {
          text: 'Connection Error',
          color: '#ef4444',
          icon: '🔴',
          description: 'Connection failed'
        };
        
      default:
        return {
          text: 'Unknown',
          color: '#6b7280',
          icon: '❓',
          description: 'Unknown connection state'
        };
    }
  }, [connectionState]);
  
  return getStatusInfo();
};

export default useWebSocketEvents;