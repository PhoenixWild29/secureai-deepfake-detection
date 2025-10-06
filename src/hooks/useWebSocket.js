/**
 * WebSocket Hook
 * Custom React hook for WebSocket connection management with authentication, reconnection, and heartbeat
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { 
  CONNECTION_STATES, 
  WebSocketMessageParser, 
  WebSocketUtils 
} from '../utils/websocketTypes';

/**
 * WebSocket connection configuration
 * @typedef {Object} WebSocketConfig
 * @property {string} url - WebSocket URL
 * @property {string} token - JWT authentication token
 * @property {number} maxReconnectAttempts - Maximum reconnection attempts (default: 5)
 * @property {number} reconnectInterval - Base reconnection interval in ms (default: 1000)
 * @property {number} maxReconnectInterval - Maximum reconnection interval in ms (default: 30000)
 * @property {number} heartbeatInterval - Heartbeat interval in ms (default: 30000)
 * @property {number} pollingInterval - Polling interval in ms when WebSocket fails (default: 5000)
 * @property {boolean} enablePolling - Enable polling fallback (default: true)
 */

/**
 * WebSocket hook return value
 * @typedef {Object} WebSocketHookReturn
 * @property {string} connectionState - Current connection state
 * @property {Object|null} lastMessage - Last received message
 * @property {string|null} error - Last error message
 * @property {boolean} isConnected - Whether WebSocket is connected
 * @property {Function} sendMessage - Function to send messages
 * @property {Function} reconnect - Function to manually reconnect
 * @property {Function} disconnect - Function to disconnect
 * @property {Object} stats - Connection statistics
 */

/**
 * Custom hook for WebSocket connection management
 * @param {WebSocketConfig} config - WebSocket configuration
 * @returns {WebSocketHookReturn} - WebSocket hook return value
 */
export const useWebSocket = (config) => {
  const {
    url,
    token,
    maxReconnectAttempts = 5,
    reconnectInterval = 1000,
    maxReconnectInterval = 30000,
    heartbeatInterval = 30000,
    pollingInterval = 5000,
    enablePolling = true
  } = config;

  // State management
  const [connectionState, setConnectionState] = useState(CONNECTION_STATES.DISCONNECTED);
  const [lastMessage, setLastMessage] = useState(null);
  const [error, setError] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  // Refs for persistent data
  const wsRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  const heartbeatTimeoutRef = useRef(null);
  const pollingTimeoutRef = useRef(null);
  const isManualDisconnectRef = useRef(false);
  const lastHeartbeatRef = useRef(Date.now());
  const statsRef = useRef({
    messagesReceived: 0,
    messagesSent: 0,
    reconnections: 0,
    errors: 0,
    connectedAt: null,
    lastActivity: null
  });

  /**
   * Calculate reconnection delay with exponential backoff and jitter
   * @param {number} attempt - Current attempt number
   * @returns {number} - Delay in milliseconds
   */
  const calculateReconnectDelay = useCallback((attempt) => {
    const baseDelay = Math.min(reconnectInterval * Math.pow(2, attempt), maxReconnectInterval);
    const jitter = Math.random() * 0.1 * baseDelay; // 10% jitter
    return baseDelay + jitter;
  }, [reconnectInterval, maxReconnectInterval]);

  /**
   * Start heartbeat mechanism
   */
  const startHeartbeat = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
    }

    heartbeatTimeoutRef.current = setTimeout(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        const heartbeatMessage = WebSocketMessageParser.createHeartbeatMessage('ping');
        wsRef.current.send(heartbeatMessage);
        statsRef.current.messagesSent++;
        statsRef.current.lastActivity = new Date();
        
        // Set timeout for pong response
        setTimeout(() => {
          const timeSinceLastHeartbeat = Date.now() - lastHeartbeatRef.current;
          if (timeSinceLastHeartbeat > heartbeatInterval + 5000) { // 5 second tolerance
            console.warn('Heartbeat timeout - no pong received');
            handleConnectionError('Heartbeat timeout');
          }
        }, 5000);
      }
      
      startHeartbeat(); // Schedule next heartbeat
    }, heartbeatInterval);
  }, [heartbeatInterval]);

  /**
   * Stop heartbeat mechanism
   */
  const stopHeartbeat = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }
  }, []);

  /**
   * Start polling fallback
   */
  const startPolling = useCallback(() => {
    if (!enablePolling || pollingTimeoutRef.current) {
      return;
    }

    console.log('Starting polling fallback');
    setConnectionState(CONNECTION_STATES.RECONNECTING);

    const poll = async () => {
      try {
        // Simulate polling by attempting WebSocket reconnection
        await attemptReconnection();
      } catch (error) {
        console.warn('Polling attempt failed:', error);
      }

      pollingTimeoutRef.current = setTimeout(poll, pollingInterval);
    };

    poll();
  }, [enablePolling, pollingInterval]);

  /**
   * Stop polling fallback
   */
  const stopPolling = useCallback(() => {
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = null;
    }
  }, []);

  /**
   * Handle WebSocket connection error
   * @param {string} errorMessage - Error message
   */
  const handleConnectionError = useCallback((errorMessage) => {
    console.error('WebSocket error:', errorMessage);
    setError(errorMessage);
    statsRef.current.errors++;
    statsRef.current.lastActivity = new Date();
    
    if (wsRef.current) {
      wsRef.current.close();
    }
    
    setIsConnected(false);
    setConnectionState(CONNECTION_STATES.ERROR);
    stopHeartbeat();
    
    // Attempt reconnection if not manually disconnected
    if (!isManualDisconnectRef.current && reconnectAttemptsRef.current < maxReconnectAttempts) {
      attemptReconnection();
    } else if (reconnectAttemptsRef.current >= maxReconnectAttempts && enablePolling) {
      startPolling();
    }
  }, [maxReconnectAttempts, enablePolling, startPolling, stopHeartbeat]);

  /**
   * Attempt WebSocket reconnection
   */
  const attemptReconnection = useCallback(async () => {
    if (isManualDisconnectRef.current) {
      return;
    }

    reconnectAttemptsRef.current++;
    statsRef.current.reconnections++;
    
    const delay = calculateReconnectDelay(reconnectAttemptsRef.current - 1);
    
    console.log(`Attempting reconnection ${reconnectAttemptsRef.current}/${maxReconnectAttempts} in ${delay}ms`);
    
    setConnectionState(CONNECTION_STATES.RECONNECTING);
    
    reconnectTimeoutRef.current = setTimeout(() => {
      connect();
    }, delay);
  }, [maxReconnectAttempts, calculateReconnectDelay]);

  /**
   * Connect to WebSocket
   */
  const connect = useCallback(() => {
    if (!url || !token) {
      setError('Missing URL or token');
      return;
    }

    try {
      // Build WebSocket URL with token
      const wsUrl = new URL(url);
      wsUrl.searchParams.set('token', token);
      
      console.log('Connecting to WebSocket:', wsUrl.toString());
      setConnectionState(CONNECTION_STATES.CONNECTING);
      setError(null);
      
      // Create WebSocket connection
      const ws = new WebSocket(wsUrl.toString());
      wsRef.current = ws;
      
      // Connection opened
      ws.onopen = () => {
        console.log('WebSocket connected');
        setConnectionState(CONNECTION_STATES.CONNECTED);
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        statsRef.current.connectedAt = new Date();
        statsRef.current.lastActivity = new Date();
        
        stopPolling();
        startHeartbeat();
      };
      
      // Message received
      ws.onmessage = (event) => {
        try {
          const parsedMessage = WebSocketMessageParser.parseMessage(event.data);
          
          if (parsedMessage) {
            setLastMessage(parsedMessage);
            statsRef.current.messagesReceived++;
            statsRef.current.lastActivity = new Date();
            
            // Handle heartbeat responses
            if (parsedMessage.event_type === 'heartbeat' && parsedMessage.message === 'pong') {
              lastHeartbeatRef.current = Date.now();
            }
          } else {
            console.warn('Invalid WebSocket message:', event.data);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      // Connection closed
      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setIsConnected(false);
        stopHeartbeat();
        
        if (event.code === 4001) {
          // Authentication error
          setError('Authentication failed');
          setConnectionState(CONNECTION_STATES.ERROR);
          return;
        }
        
        if (!isManualDisconnectRef.current) {
          setConnectionState(CONNECTION_STATES.DISCONNECTED);
          handleConnectionError('Connection closed unexpectedly');
        }
      };
      
      // Connection error
      ws.onerror = (error) => {
        console.error('WebSocket error event:', error);
        handleConnectionError('WebSocket connection error');
      };
      
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      handleConnectionError('Failed to create WebSocket connection');
    }
  }, [url, token, startHeartbeat, stopHeartbeat, stopPolling, handleConnectionError]);

  /**
   * Send message through WebSocket
   * @param {string|Object} message - Message to send
   */
  const sendMessage = useCallback((message) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected, cannot send message');
      return false;
    }
    
    try {
      const messageString = typeof message === 'string' ? message : JSON.stringify(message);
      wsRef.current.send(messageString);
      statsRef.current.messagesSent++;
      statsRef.current.lastActivity = new Date();
      return true;
    } catch (error) {
      console.error('Failed to send WebSocket message:', error);
      return false;
    }
  }, []);

  /**
   * Manually reconnect WebSocket
   */
  const reconnect = useCallback(() => {
    console.log('Manual reconnection requested');
    isManualDisconnectRef.current = false;
    reconnectAttemptsRef.current = 0;
    
    // Clear any existing timeouts
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
    }
    
    stopPolling();
    connect();
  }, [connect, stopPolling]);

  /**
   * Disconnect WebSocket
   */
  const disconnect = useCallback(() => {
    console.log('Manual disconnection requested');
    isManualDisconnectRef.current = true;
    
    // Clear all timeouts
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
    }
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
    }
    
    // Close WebSocket connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setConnectionState(CONNECTION_STATES.DISCONNECTED);
    setIsConnected(false);
    stopHeartbeat();
    stopPolling();
  }, [stopHeartbeat, stopPolling]);

  // Effect for initial connection
  useEffect(() => {
    if (url && token) {
      connect();
    }
    
    // Cleanup on unmount
    return () => {
      disconnect();
    };
  }, [url, token, connect, disconnect]);

  // Effect for cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // Return hook interface
  return {
    connectionState,
    lastMessage,
    error,
    isConnected,
    sendMessage,
    reconnect,
    disconnect,
    stats: {
      ...statsRef.current,
      reconnectAttempts: reconnectAttemptsRef.current,
      isPolling: pollingTimeoutRef.current !== null
    }
  };
};

/**
 * Hook for WebSocket connection with automatic retry
 * @param {string} analysisId - Analysis ID for WebSocket connection
 * @param {string} token - JWT authentication token
 * @param {Object} options - Additional options
 * @returns {WebSocketHookReturn} - WebSocket hook return value
 */
export const useAnalysisWebSocket = (analysisId, token, options = {}) => {
  const baseUrl = options.baseUrl || 'ws://localhost:8000';
  const wsUrl = `${baseUrl}/ws/analysis/${analysisId}`;
  
  return useWebSocket({
    url: wsUrl,
    token,
    ...options
  });
};

/**
 * Hook for WebSocket connection status display
 * @param {string} connectionState - Current connection state
 * @returns {Object} - Status display information
 */
export const useConnectionStatus = (connectionState) => {
  const getStatusInfo = useCallback(() => {
    switch (connectionState) {
      case CONNECTION_STATES.CONNECTING:
        return {
          text: 'Connecting...',
          color: '#f59e0b', // amber
          icon: '🔄',
          description: 'Establishing connection to server'
        };
        
      case CONNECTION_STATES.CONNECTED:
        return {
          text: 'Connected',
          color: '#10b981', // emerald
          icon: '🟢',
          description: 'Real-time updates active'
        };
        
      case CONNECTION_STATES.DISCONNECTED:
        return {
          text: 'Disconnected',
          color: '#6b7280', // gray
          icon: '⚫',
          description: 'Connection lost'
        };
        
      case CONNECTION_STATES.RECONNECTING:
        return {
          text: 'Reconnecting...',
          color: '#f59e0b', // amber
          icon: '🔄',
          description: 'Attempting to reconnect'
        };
        
      case CONNECTION_STATES.ERROR:
        return {
          text: 'Connection Error',
          color: '#ef4444', // red
          icon: '🔴',
          description: 'Connection failed'
        };
        
      default:
        return {
          text: 'Unknown',
          color: '#6b7280', // gray
          icon: '❓',
          description: 'Unknown connection state'
        };
    }
  }, [connectionState]);
  
  return getStatusInfo();
};

export default useWebSocket;
