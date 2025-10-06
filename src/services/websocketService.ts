/**
 * WebSocket Service
 * Manages WebSocket connections, message parsing, and event dispatching for real-time dashboard updates
 */

import { 
  WebSocketConfig, 
  WebSocketMessage, 
  RealTimeEvent, 
  RealTimeEventType,
  DEFAULT_WEB_SOCKET_CONFIG 
} from '@/types/dashboard';

// WebSocket connection states
export enum WebSocketState {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  RECONNECTING = 'reconnecting',
  ERROR = 'error',
}

// Event listener types
export type WebSocketEventListener = (event: RealTimeEvent) => void;
export type ConnectionStateListener = (state: WebSocketState) => void;
export type ErrorListener = (error: Error) => void;

// WebSocket service class
export class WebSocketService {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private state: WebSocketState = WebSocketState.DISCONNECTED;
  private reconnectAttempts = 0;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private heartbeatTimeout: ReturnType<typeof setTimeout> | null = null;
  private messageQueue: WebSocketMessage[] = [];
  private eventListeners = new Map<RealTimeEventType, Set<WebSocketEventListener>>();
  private connectionStateListeners = new Set<ConnectionStateListener>();
  private errorListeners = new Set<ErrorListener>();
  private isDestroyed = false;

  constructor(config: Partial<WebSocketConfig> = {}) {
    this.config = { ...DEFAULT_WEB_SOCKET_CONFIG, ...config };
    this.setupEventListeners();
  }

  /**
   * Connect to WebSocket server
   */
  public async connect(): Promise<void> {
    if (this.isDestroyed) {
      throw new Error('WebSocket service has been destroyed');
    }

    if (this.state === WebSocketState.CONNECTED || this.state === WebSocketState.CONNECTING) {
      return;
    }

    return new Promise((resolve, reject) => {
      try {
        this.setState(WebSocketState.CONNECTING);
        
        // Add authentication token to URL if provided
        const url = this.config.authToken 
          ? `${this.config.url}?token=${this.config.authToken}`
          : this.config.url;

        this.ws = new WebSocket(url);
        
        // Set connection timeout
        const connectionTimeout = setTimeout(() => {
          if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
            this.ws.close();
            reject(new Error('Connection timeout'));
          }
        }, this.config.timeout);

        this.ws.onopen = () => {
          clearTimeout(connectionTimeout);
          this.setState(WebSocketState.CONNECTED);
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          this.processMessageQueue();
          resolve();
        };

        this.ws.onclose = (event) => {
          clearTimeout(connectionTimeout);
          this.stopHeartbeat();
          
          if (!event.wasClean && !this.isDestroyed) {
            this.handleReconnection();
          } else {
            this.setState(WebSocketState.DISCONNECTED);
          }
        };

        this.ws.onerror = (error) => {
          clearTimeout(connectionTimeout);
          this.setState(WebSocketState.ERROR);
          this.notifyErrorListeners(new Error('WebSocket connection error'));
          reject(error);
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };

      } catch (error) {
        this.setState(WebSocketState.ERROR);
        this.notifyErrorListeners(error as Error);
        reject(error);
      }
    });
  }

  /**
   * Disconnect from WebSocket server
   */
  public disconnect(): void {
    this.isDestroyed = true;
    this.stopHeartbeat();
    this.clearReconnectTimeout();
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    
    this.setState(WebSocketState.DISCONNECTED);
  }

  /**
   * Send message to WebSocket server
   */
  public sendMessage(message: Omit<WebSocketMessage, 'id' | 'timestamp'>): void {
    const fullMessage: WebSocketMessage = {
      ...message,
      id: this.generateMessageId(),
      timestamp: new Date(),
    };

    if (this.state === WebSocketState.CONNECTED && this.ws) {
      try {
        this.ws.send(JSON.stringify(fullMessage));
      } catch (error) {
        this.notifyErrorListeners(error as Error);
      }
    } else {
      // Queue message for later sending
      this.messageQueue.push(fullMessage);
    }
  }

  /**
   * Subscribe to specific event type
   */
  public subscribe(eventType: RealTimeEventType): void {
    this.sendMessage({
      type: 'subscribe',
      payload: { eventType },
    });
  }

  /**
   * Unsubscribe from specific event type
   */
  public unsubscribe(eventType: RealTimeEventType): void {
    this.sendMessage({
      type: 'unsubscribe',
      payload: { eventType },
    });
  }

  /**
   * Add event listener for specific event type
   */
  public addEventListener(eventType: RealTimeEventType, listener: WebSocketEventListener): void {
    if (!this.eventListeners.has(eventType)) {
      this.eventListeners.set(eventType, new Set());
    }
    this.eventListeners.get(eventType)!.add(listener);
  }

  /**
   * Remove event listener for specific event type
   */
  public removeEventListener(eventType: RealTimeEventType, listener: WebSocketEventListener): void {
    const listeners = this.eventListeners.get(eventType);
    if (listeners) {
      listeners.delete(listener);
      if (listeners.size === 0) {
        this.eventListeners.delete(eventType);
      }
    }
  }

  /**
   * Add connection state listener
   */
  public addConnectionStateListener(listener: ConnectionStateListener): void {
    this.connectionStateListeners.add(listener);
  }

  /**
   * Remove connection state listener
   */
  public removeConnectionStateListener(listener: ConnectionStateListener): void {
    this.connectionStateListeners.delete(listener);
  }

  /**
   * Add error listener
   */
  public addErrorListener(listener: ErrorListener): void {
    this.errorListeners.add(listener);
  }

  /**
   * Remove error listener
   */
  public removeErrorListener(listener: ErrorListener): void {
    this.errorListeners.delete(listener);
  }

  /**
   * Get current connection state
   */
  public getState(): WebSocketState {
    return this.state;
  }

  /**
   * Get connection statistics
   */
  public getStats() {
    return {
      state: this.state,
      reconnectAttempts: this.reconnectAttempts,
      queuedMessages: this.messageQueue.length,
      activeListeners: Array.from(this.eventListeners.keys()),
    };
  }

  /**
   * Update configuration
   */
  public updateConfig(newConfig: Partial<WebSocketConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  /**
   * Set authentication token
   */
  public setAuthToken(token: string): void {
    this.config.authToken = token;
    
    // Reconnect with new token if currently connected
    if (this.state === WebSocketState.CONNECTED) {
      this.disconnect();
      this.connect();
    }
  }

  // Private methods

  private setState(newState: WebSocketState): void {
    if (this.state !== newState) {
      this.state = newState;
      this.notifyConnectionStateListeners(newState);
    }
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      switch (message.type) {
        case 'pong':
          this.handlePong();
          break;
        case 'event':
          this.handleEvent(message.payload);
          break;
        case 'error':
          this.handleError(message.payload);
          break;
        default:
          console.warn('Unknown message type:', message.type);
      }
    } catch (error) {
      this.notifyErrorListeners(new Error('Failed to parse WebSocket message'));
    }
  }

  private handleEvent(eventData: any): void {
    try {
      const event: RealTimeEvent = {
        id: eventData.id || this.generateMessageId(),
        type: eventData.type,
        data: eventData.data,
        priority: eventData.priority || 'normal',
        source: eventData.source || 'unknown',
        target: eventData.target,
        timestamp: new Date(eventData.timestamp || Date.now()),
        metadata: eventData.metadata,
        createdAt: new Date(),
        updatedAt: new Date(),
        version: 1,
      };

      this.notifyEventListeners(event);
    } catch (error) {
      this.notifyErrorListeners(new Error('Failed to process event data'));
    }
  }

  private handleError(errorData: any): void {
    const error = new Error(errorData.message || 'WebSocket server error');
    this.notifyErrorListeners(error);
  }

  private handlePong(): void {
    // Clear heartbeat timeout on pong
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  private handleReconnection(): void {
    if (this.isDestroyed || !this.config.reconnect.enabled) {
      return;
    }

    if (this.reconnectAttempts >= this.config.reconnect.maxAttempts) {
      this.setState(WebSocketState.ERROR);
      this.notifyErrorListeners(new Error('Max reconnection attempts reached'));
      return;
    }

    this.setState(WebSocketState.RECONNECTING);
    this.reconnectAttempts++;

    const delay = Math.min(
      this.config.reconnect.initialDelay * Math.pow(this.config.reconnect.backoffMultiplier, this.reconnectAttempts - 1),
      this.config.reconnect.maxDelay
    );

    this.reconnectTimeout = setTimeout(() => {
      this.connect().catch(() => {
        // Reconnection failed, will be handled by handleReconnection
      });
    }, delay);
  }

  private startHeartbeat(): void {
    if (!this.config.heartbeat.enabled) {
      return;
    }

    this.heartbeatInterval = setInterval(() => {
      if (this.state === WebSocketState.CONNECTED) {
        this.sendMessage({
          type: 'ping',
          payload: {},
        });

        // Set timeout for pong response
        this.heartbeatTimeout = setTimeout(() => {
          this.notifyErrorListeners(new Error('Heartbeat timeout'));
          this.handleReconnection();
        }, this.config.heartbeat.timeout);
      }
    }, this.config.heartbeat.interval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  private clearReconnectTimeout(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  private processMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.state === WebSocketState.CONNECTED) {
      const message = this.messageQueue.shift();
      if (message) {
        this.sendMessage(message);
      }
    }
  }

  private notifyEventListeners(event: RealTimeEvent): void {
    const listeners = this.eventListeners.get(event.type);
    if (listeners) {
      listeners.forEach(listener => {
        try {
          listener(event);
        } catch (error) {
          console.error('Error in event listener:', error);
        }
      });
    }
  }

  private notifyConnectionStateListeners(state: WebSocketState): void {
    this.connectionStateListeners.forEach(listener => {
      try {
        listener(state);
      } catch (error) {
        console.error('Error in connection state listener:', error);
        }
    });
  }

  private notifyErrorListeners(error: Error): void {
    this.errorListeners.forEach(listener => {
      try {
        listener(error);
      } catch (listenerError) {
        console.error('Error in error listener:', listenerError);
      }
    });
  }

  private generateMessageId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private setupEventListeners(): void {
    // Handle page visibility changes
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
          this.stopHeartbeat();
        } else if (this.state === WebSocketState.CONNECTED) {
          this.startHeartbeat();
        }
      });
    }

    // Handle online/offline events
    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => {
        if (this.state === WebSocketState.DISCONNECTED) {
          this.connect().catch(() => {
            // Connection will be retried automatically
          });
        }
      });

      window.addEventListener('offline', () => {
        this.setState(WebSocketState.DISCONNECTED);
      });
    }
  }
}

// Singleton instance
let webSocketServiceInstance: WebSocketService | null = null;

/**
 * Get WebSocket service singleton instance
 */
export const getWebSocketService = (config?: Partial<WebSocketConfig>): WebSocketService => {
  if (!webSocketServiceInstance) {
    webSocketServiceInstance = new WebSocketService(config);
  }
  return webSocketServiceInstance;
};

/**
 * Create new WebSocket service instance
 */
export const createWebSocketService = (config?: Partial<WebSocketConfig>): WebSocketService => {
  return new WebSocketService(config);
};

/**
 * Destroy WebSocket service singleton
 */
export const destroyWebSocketService = (): void => {
  if (webSocketServiceInstance) {
    webSocketServiceInstance.disconnect();
    webSocketServiceInstance = null;
  }
};

export default WebSocketService;
