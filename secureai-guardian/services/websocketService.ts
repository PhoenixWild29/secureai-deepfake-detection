/**
 * WebSocket Service for Real-time Analysis Progress
 * Handles WebSocket connections for live progress updates during video analysis
 */

// Use relative WebSocket URL in development to work with Vite proxy
const WS_BASE_URL = import.meta.env.DEV
  ? (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host.replace(':3000', ':5000')
  : (import.meta.env.VITE_WS_URL || 'ws://localhost:5000');

export interface ProgressMessage {
  type: 'progress' | 'status' | 'complete' | 'error';
  progress?: number;
  status?: string;
  message?: string;
  result?: any;
  error?: string;
}

export type ProgressCallback = (progress: number, status: string, message: string) => void;
export type CompleteCallback = (result: any) => void;
export type ErrorCallback = (error: string) => void;

/**
 * Connect to WebSocket for analysis progress updates
 */
export function connectAnalysisWebSocket(
  analysisId: string,
  onProgress: ProgressCallback,
  onComplete: CompleteCallback,
  onError: ErrorCallback
): WebSocket {
  // Flask-SocketIO uses Socket.IO protocol, but we can use standard WebSocket
  // The backend will handle Socket.IO protocol conversion
  const wsUrl = `${WS_BASE_URL}`;
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('WebSocket connected for analysis:', analysisId);
    // Send initial message to subscribe to updates
    ws.send(JSON.stringify({ 
      type: 'subscribe', 
      analysis_id: analysisId 
    }));
  };

  ws.onmessage = (event) => {
    try {
      const data: ProgressMessage = JSON.parse(event.data);

      switch (data.type) {
        case 'progress':
          if (data.progress !== undefined && data.status && data.message) {
            onProgress(data.progress, data.status, data.message);
          }
          break;

        case 'status':
          if (data.status && data.message) {
            onProgress(data.progress || 0, data.status, data.message);
          }
          break;

        case 'complete':
          if (data.result) {
            onComplete(data.result);
            ws.close();
          }
          break;

        case 'error':
          if (data.error) {
            onError(data.error);
            ws.close();
          }
          break;

        default:
          console.warn('Unknown WebSocket message type:', data.type);
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
      onError('Failed to parse progress update');
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    onError('WebSocket connection error');
  };

  ws.onclose = (event) => {
    if (event.code !== 1000) {
      // Not a normal closure
      console.warn('WebSocket closed unexpectedly:', event.code, event.reason);
    }
  };

  return ws;
}

/**
 * Check if WebSocket is supported
 */
export function isWebSocketSupported(): boolean {
  return typeof WebSocket !== 'undefined';
}

/**
 * Create a WebSocket connection with automatic reconnection
 */
export class ReconnectingWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private onProgress: ProgressCallback;
  private onComplete: CompleteCallback;
  private onError: ErrorCallback;
  private analysisId: string;
  public currentAnalysisId: string | null = null;

  constructor(
    analysisId: string,
    onProgress: ProgressCallback,
    onComplete: CompleteCallback,
    onError: ErrorCallback
  ) {
    this.analysisId = analysisId;
    this.currentAnalysisId = analysisId;
    this.onProgress = onProgress;
    this.onComplete = onComplete;
    this.onError = onError;
    this.url = `${WS_BASE_URL}/analysis/${analysisId}`;
    this.connect();
  }
  
  public updateAnalysisId(newAnalysisId: string): void {
    this.currentAnalysisId = newAnalysisId;
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.send({ type: 'update_analysis_id', analysis_id: newAnalysisId });
    }
  }

  private connect() {
    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('WebSocket connected:', this.analysisId);
        this.reconnectAttempts = 0;
        this.ws?.send(JSON.stringify({ type: 'subscribe', analysis_id: this.analysisId }));
      };

      this.ws.onmessage = (event) => {
        try {
          const data: ProgressMessage = JSON.parse(event.data);

          switch (data.type) {
            case 'progress':
            case 'status':
              if (data.progress !== undefined && data.status && data.message) {
                this.onProgress(data.progress, data.status, data.message);
              }
              break;

            case 'complete':
              if (data.result) {
                this.onComplete(data.result);
                this.close();
              }
              break;

            case 'error':
              if (data.error) {
                this.onError(data.error);
                this.close();
              }
              break;
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      this.ws.onclose = (event) => {
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          // Attempt to reconnect
          this.reconnectAttempts++;
          const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
          console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
          setTimeout(() => this.connect(), delay);
        } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          this.onError('Failed to establish WebSocket connection after multiple attempts');
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      this.onError('WebSocket not supported or connection failed');
    }
  }

  public close() {
    if (this.ws) {
      this.ws.close(1000, 'Normal closure');
      this.ws = null;
    }
  }

  public send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }
}

