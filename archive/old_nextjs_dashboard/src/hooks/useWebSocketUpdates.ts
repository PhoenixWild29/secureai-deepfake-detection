/**
 * Custom hook for WebSocket real-time updates
 * Handles WebSocket connections for analysis status updates and real-time notifications
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { authUtils } from '@/lib/auth';

// WebSocket message types
export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

export interface AnalysisStatusUpdate {
  analysis_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message?: string;
  result?: any;
  error?: string;
}

export interface NotificationUpdate {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

export interface SystemStatusUpdate {
  component: string;
  status: 'healthy' | 'warning' | 'error';
  message?: string;
  timestamp: string;
}

export interface UseWebSocketUpdatesOptions {
  autoConnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onAnalysisUpdate?: (update: AnalysisStatusUpdate) => void;
  onNotification?: (notification: NotificationUpdate) => void;
  onSystemUpdate?: (update: SystemStatusUpdate) => void;
  onError?: (error: string) => void;
}

export interface UseWebSocketUpdatesReturn {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  connectionStatus: 'disconnected' | 'connecting' | 'connected' | 'error';
  connect: () => void;
  disconnect: () => void;
  sendMessage: (message: any) => void;
  lastMessage: WebSocketMessage | null;
}

/**
 * Hook for WebSocket real-time updates
 */
export function useWebSocketUpdates(options: UseWebSocketUpdatesOptions = {}): UseWebSocketUpdatesReturn {
  const {
    autoConnect = true,
    reconnectInterval = 5000,
    maxReconnectAttempts = 5,
    onAnalysisUpdate,
    onNotification,
    onSystemUpdate,
    onError,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const shouldReconnectRef = useRef(true);

  // WebSocket URL - adjust based on your WebSocket server configuration
  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.NEXT_PUBLIC_WS_HOST || window.location.host;
    const token = authUtils.getCurrentUser()?.id || 'anonymous';
    
    return `${protocol}//${host}/ws/updates?token=${token}`;
  }, []);

  // Handle WebSocket messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      setLastMessage(message);

      switch (message.type) {
        case 'analysis_update':
          if (onAnalysisUpdate && message.data) {
            onAnalysisUpdate(message.data as AnalysisStatusUpdate);
          }
          break;
        
        case 'notification':
          if (onNotification && message.data) {
            onNotification(message.data as NotificationUpdate);
          }
          break;
        
        case 'system_status':
          if (onSystemUpdate && message.data) {
            onSystemUpdate(message.data as SystemStatusUpdate);
          }
          break;
        
        case 'error':
          const errorMessage = message.data?.message || 'WebSocket error occurred';
          setError(errorMessage);
          if (onError) {
            onError(errorMessage);
          }
          break;
        
        default:
          console.log('Unknown WebSocket message type:', message.type);
      }
    } catch (err) {
      const errorMessage = 'Failed to parse WebSocket message';
      setError(errorMessage);
      if (onError) {
        onError(errorMessage);
      }
    }
  }, [onAnalysisUpdate, onNotification, onSystemUpdate, onError]);

  // Handle WebSocket connection
  const handleOpen = useCallback(() => {
    setIsConnected(true);
    setIsConnecting(false);
    setConnectionStatus('connected');
    setError(null);
    reconnectAttemptsRef.current = 0;
    console.log('WebSocket connected');
  }, []);

  // Handle WebSocket disconnection
  const handleClose = useCallback((event: CloseEvent) => {
    setIsConnected(false);
    setIsConnecting(false);
    setConnectionStatus('disconnected');
    
    // Attempt to reconnect if not manually closed
    if (shouldReconnectRef.current && reconnectAttemptsRef.current < maxReconnectAttempts) {
      const delay = Math.min(reconnectInterval * Math.pow(2, reconnectAttemptsRef.current), 30000);
      reconnectTimeoutRef.current = setTimeout(() => {
        reconnectAttemptsRef.current++;
        connect();
      }, delay);
    } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
      setConnectionStatus('error');
      setError('Failed to reconnect after maximum attempts');
    }
    
    console.log('WebSocket disconnected:', event.code, event.reason);
  }, [reconnectInterval, maxReconnectAttempts]);

  // Handle WebSocket errors
  const handleError = useCallback((event: Event) => {
    setIsConnecting(false);
    setConnectionStatus('error');
    const errorMessage = 'WebSocket connection error';
    setError(errorMessage);
    if (onError) {
      onError(errorMessage);
    }
    console.error('WebSocket error:', event);
  }, [onError]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || isConnecting) {
      return;
    }

    setIsConnecting(true);
    setConnectionStatus('connecting');
    setError(null);

    try {
      const wsUrl = getWebSocketUrl();
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = handleOpen;
      ws.onclose = handleClose;
      ws.onerror = handleError;
      ws.onmessage = handleMessage;
      
      wsRef.current = ws;
    } catch (err) {
      setIsConnecting(false);
      setConnectionStatus('error');
      const errorMessage = err instanceof Error ? err.message : 'Failed to create WebSocket connection';
      setError(errorMessage);
      if (onError) {
        onError(errorMessage);
      }
    }
  }, [isConnecting, getWebSocketUrl, handleOpen, handleClose, handleError, handleMessage, onError]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
    }
    
    setIsConnected(false);
    setIsConnecting(false);
    setConnectionStatus('disconnected');
    setError(null);
  }, []);

  // Send message through WebSocket
  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected. Cannot send message:', message);
    }
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    isConnected,
    isConnecting,
    error,
    connectionStatus,
    connect,
    disconnect,
    sendMessage,
    lastMessage,
  };
}

/**
 * Hook specifically for analysis status updates
 */
export function useAnalysisStatusUpdates(analysisId?: string): {
  status: string | null;
  progress: number;
  result: any | null;
  error: string | null;
  isConnected: boolean;
} {
  const [status, setStatus] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalysisUpdate = useCallback((update: AnalysisStatusUpdate) => {
    if (!analysisId || update.analysis_id === analysisId) {
      setStatus(update.status);
      setProgress(update.progress);
      if (update.result) {
        setResult(update.result);
      }
      if (update.error) {
        setError(update.error);
      }
    }
  }, [analysisId]);

  const { isConnected } = useWebSocketUpdates({
    onAnalysisUpdate: handleAnalysisUpdate,
  });

  return {
    status,
    progress,
    result,
    error,
    isConnected,
  };
}

/**
 * Hook for real-time notifications
 */
export function useRealtimeNotifications(): {
  notifications: NotificationUpdate[];
  unreadCount: number;
  addNotification: (notification: NotificationUpdate) => void;
  markAsRead: (notificationId: string) => void;
  clearAll: () => void;
  isConnected: boolean;
} {
  const [notifications, setNotifications] = useState<NotificationUpdate[]>([]);

  const handleNotification = useCallback((notification: NotificationUpdate) => {
    setNotifications(prev => [notification, ...prev.slice(0, 49)]); // Keep last 50 notifications
  }, []);

  const addNotification = useCallback((notification: NotificationUpdate) => {
    setNotifications(prev => [notification, ...prev]);
  }, []);

  const markAsRead = useCallback((notificationId: string) => {
    setNotifications(prev => 
      prev.map(notification => 
        notification.id === notificationId 
          ? { ...notification, read: true }
          : notification
      )
    );
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  const { isConnected } = useWebSocketUpdates({
    onNotification: handleNotification,
  });

  const unreadCount = notifications.filter(n => !n.read).length;

  return {
    notifications,
    unreadCount,
    addNotification,
    markAsRead,
    clearAll,
    isConnected,
  };
}

/**
 * Hook for system status monitoring
 */
export function useSystemStatusMonitoring(): {
  systemStatus: Record<string, SystemStatusUpdate>;
  overallStatus: 'healthy' | 'warning' | 'error';
  isConnected: boolean;
} {
  const [systemStatus, setSystemStatus] = useState<Record<string, SystemStatusUpdate>>({});

  const handleSystemUpdate = useCallback((update: SystemStatusUpdate) => {
    setSystemStatus(prev => ({
      ...prev,
      [update.component]: update,
    }));
  }, []);

  const { isConnected } = useWebSocketUpdates({
    onSystemUpdate: handleSystemUpdate,
  });

  // Calculate overall system status
  const overallStatus = useCallback((): 'healthy' | 'warning' | 'error' => {
    const statuses = Object.values(systemStatus);
    if (statuses.length === 0) return 'healthy';
    
    if (statuses.some(s => s.status === 'error')) return 'error';
    if (statuses.some(s => s.status === 'warning')) return 'warning';
    return 'healthy';
  }, [systemStatus]);

  return {
    systemStatus,
    overallStatus: overallStatus(),
    isConnected,
  };
}
