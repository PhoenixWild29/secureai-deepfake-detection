/**
 * WebSocket Service for Real-time Progress Updates
 * Manages WebSocket connections and handles StatusUpdate and ResultUpdate events
 */

import { 
  WebSocketMessage, 
  StatusUpdate, 
  ResultUpdate, 
  ConnectionStatus,
  ProgressTrackerConfig 
} from '@/types/progress';

export type WebSocketEventHandler<T = any> = (data: T) => void;
export type ConnectionEventHandler = (status: ConnectionStatus) => void;

export interface WebSocketServiceConfig {
  /** WebSocket server URL */
  url: string;
  /** Reconnection interval in milliseconds */
  reconnectInterval?: number;
  /** Maximum reconnection attempts */
  maxReconnectAttempts?: number;
  /** Connection timeout in milliseconds */
  connectionTimeout?: number;
  /** Heartbeat interval in milliseconds */
  heartbeatInterval?: number;
}

export class WebSocketService {
  private ws: WebSocket | null = null;
  private config: Required<WebSocketServiceConfig>;
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private connectionTimeoutTimer: NodeJS.Timeout | null = null;
  private isConnecting = false;
  private isDestroyed = false;

  // Event handlers
  private statusUpdateHandlers: WebSocketEventHandler<StatusUpdate>[] = [];
  private resultUpdateHandlers: WebSocketEventHandler<ResultUpdate>[] = [];
  private errorHandlers: WebSocketEventHandler<Error>[] = [];
  private connectionHandlers: ConnectionEventHandler[] = [];

  constructor(config: WebSocketServiceConfig) {
    this.config = {
      url: config.url,
      reconnectInterval: config.reconnectInterval || 3000,
      maxReconnectAttempts: config.maxReconnectAttempts || 5,
      connectionTimeout: config.connectionTimeout || 10000,
      heartbeatInterval: config.heartbeatInterval || 30000,
    };
  }

  /**
   * Connect to WebSocket server
   */
  public async connect(): Promise<void> {
    if (this.isDestroyed || this.isConnecting || this.isConnected()) {
      return;
    }

    this.isConnecting = true;
    this.notifyConnectionStatus({
      status: 'connecting',
      reconnectAttempts: this.reconnectAttempts,
    });

    try {
      this.ws = new WebSocket(this.config.url);
      
      // Set connection timeout
      this.connectionTimeoutTimer = setTimeout(() => {
        if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
          this.ws.close();
          this.handleConnectionError(new Error('Connection timeout'));
        }
      }, this.config.connectionTimeout);

      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
      this.ws.onerror = this.handleError.bind(this);

    } catch (error) {
      this.handleConnectionError(error as Error);
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  public disconnect(): void {
    this.isDestroyed = true;
    this.clearTimers();
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }

    this.notifyConnectionStatus({
      status: 'disconnected',
      reconnectAttempts: this.reconnectAttempts,
    });
  }

  /**
   * Check if WebSocket is connected
   */
  public isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Send message to WebSocket server
   */
  public send(message: any): boolean {
    if (!this.isConnected()) {
      console.warn('WebSocket not connected, cannot send message');
      return false;
    }

    try {
      this.ws!.send(JSON.stringify(message));
      return true;
    } catch (error) {
      console.error('Failed to send WebSocket message:', error);
      return false;
    }
  }

  /**
   * Subscribe to status update events
   */
  public onStatusUpdate(handler: WebSocketEventHandler<StatusUpdate>): () => void {
    this.statusUpdateHandlers.push(handler);
    return () => {
      const index = this.statusUpdateHandlers.indexOf(handler);
      if (index > -1) {
        this.statusUpdateHandlers.splice(index, 1);
      }
    };
  }

  /**
   * Subscribe to result update events
   */
  public onResultUpdate(handler: WebSocketEventHandler<ResultUpdate>): () => void {
    this.resultUpdateHandlers.push(handler);
    return () => {
      const index = this.resultUpdateHandlers.indexOf(handler);
      if (index > -1) {
        this.resultUpdateHandlers.splice(index, 1);
      }
    };
  }

  /**
   * Subscribe to error events
   */
  public onError(handler: WebSocketEventHandler<Error>): () => void {
    this.errorHandlers.push(handler);
    return () => {
      const index = this.errorHandlers.indexOf(handler);
      if (index > -1) {
        this.errorHandlers.splice(index, 1);
      }
    };
  }

  /**
   * Subscribe to connection status events
   */
  public onConnectionStatus(handler: ConnectionEventHandler): () => void {
    this.connectionHandlers.push(handler);
    return () => {
      const index = this.connectionHandlers.indexOf(handler);
      if (index > -1) {
        this.connectionHandlers.splice(index, 1);
      }
    };
  }

  /**
   * Handle WebSocket open event
   */
  private handleOpen(): void {
    this.isConnecting = false;
    this.reconnectAttempts = 0;
    this.clearTimers();
    
    this.notifyConnectionStatus({
      status: 'connected',
      reconnectAttempts: 0,
    });

    // Start heartbeat
    this.startHeartbeat();
    
    console.log('WebSocket connected successfully');
  }

  /**
   * Handle WebSocket message event
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      switch (message.type) {
        case 'status_update':
          this.notifyStatusUpdate(message.payload as StatusUpdate);
          break;
        case 'result_update':
          this.notifyResultUpdate(message.payload as ResultUpdate);
          break;
        case 'error':
          this.notifyError(new Error((message.payload as any).message || 'Unknown error'));
          break;
        case 'connection_status':
          this.notifyConnectionStatus(message.payload as ConnectionStatus);
          break;
        default:
          console.warn('Unknown WebSocket message type:', message.type);
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
      this.notifyError(error as Error);
    }
  }

  /**
   * Handle WebSocket close event
   */
  private handleClose(event: CloseEvent): void {
    this.isConnecting = false;
    this.clearTimers();
    
    if (!this.isDestroyed) {
      this.notifyConnectionStatus({
        status: 'disconnected',
        reconnectAttempts: this.reconnectAttempts,
        error: `Connection closed: ${event.reason || 'Unknown reason'}`,
      });

      // Attempt to reconnect if not a normal closure
      if (event.code !== 1000 && this.reconnectAttempts < this.config.maxReconnectAttempts) {
        this.scheduleReconnect();
      }
    }

    console.log('WebSocket connection closed:', event.code, event.reason);
  }

  /**
   * Handle WebSocket error event
   */
  private handleError(event: Event): void {
    this.handleConnectionError(new Error('WebSocket connection error'));
  }

  /**
   * Handle connection errors
   */
  private handleConnectionError(error: Error): void {
    this.isConnecting = false;
    this.clearTimers();
    
    this.notifyConnectionStatus({
      status: 'error',
      reconnectAttempts: this.reconnectAttempts,
      error: error.message,
    });

    this.notifyError(error);

    // Attempt to reconnect
    if (!this.isDestroyed && this.reconnectAttempts < this.config.maxReconnectAttempts) {
      this.scheduleReconnect();
    }
  }

  /**
   * Schedule reconnection attempt
   */
  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    
    const nextReconnectAt = new Date(Date.now() + this.config.reconnectInterval);
    
    this.notifyConnectionStatus({
      status: 'disconnected',
      reconnectAttempts: this.reconnectAttempts,
      nextReconnectAt: nextReconnectAt.toISOString(),
    });

    this.reconnectTimer = setTimeout(() => {
      if (!this.isDestroyed) {
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.config.maxReconnectAttempts})`);
        this.connect();
      }
    }, this.config.reconnectInterval);
  }

  /**
   * Start heartbeat to keep connection alive
   */
  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected()) {
        this.send({ type: 'ping', timestamp: new Date().toISOString() });
      }
    }, this.config.heartbeatInterval);
  }

  /**
   * Clear all timers
   */
  private clearTimers(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    
    if (this.connectionTimeoutTimer) {
      clearTimeout(this.connectionTimeoutTimer);
      this.connectionTimeoutTimer = null;
    }
  }

  /**
   * Notify status update handlers
   */
  private notifyStatusUpdate(data: StatusUpdate): void {
    this.statusUpdateHandlers.forEach(handler => {
      try {
        handler(data);
      } catch (error) {
        console.error('Error in status update handler:', error);
      }
    });
  }

  /**
   * Notify result update handlers
   */
  private notifyResultUpdate(data: ResultUpdate): void {
    this.resultUpdateHandlers.forEach(handler => {
      try {
        handler(data);
      } catch (error) {
        console.error('Error in result update handler:', error);
      }
    });
  }

  /**
   * Notify error handlers
   */
  private notifyError(error: Error): void {
    this.errorHandlers.forEach(handler => {
      try {
        handler(error);
      } catch (handlerError) {
        console.error('Error in error handler:', handlerError);
      }
    });
  }

  /**
   * Notify connection status handlers
   */
  private notifyConnectionStatus(status: ConnectionStatus): void {
    this.connectionHandlers.forEach(handler => {
      try {
        handler(status);
      } catch (error) {
        console.error('Error in connection status handler:', error);
      }
    });
  }
}

/**
 * Create WebSocket service instance
 */
export const createWebSocketService = (config: WebSocketServiceConfig): WebSocketService => {
  return new WebSocketService(config);
};

/**
 * Default WebSocket service configuration
 */
export const defaultWebSocketConfig: WebSocketServiceConfig = {
  url: process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8000/ws/progress',
  reconnectInterval: 3000,
  maxReconnectAttempts: 5,
  connectionTimeout: 10000,
  heartbeatInterval: 30000,
};

export default WebSocketService;
