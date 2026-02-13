/**
 * WebSocket Service for Real-time Analysis Progress
 * Handles WebSocket connections for live progress updates during video analysis
 */

import { io, type Socket } from 'socket.io-client';

// IMPORTANT:
// Flask-SocketIO speaks the Socket.IO protocol (Engine.IO), NOT raw WebSocket frames.
// Use socket.io-client and connect via the /socket.io path (proxied by Nginx in prod).
const SOCKET_IO_URL = import.meta.env.DEV
  ? (import.meta.env.VITE_WS_URL || (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host)
  : ((window.location.protocol === 'https:' ? 'https:' : 'http:') + '//' + window.location.host);

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
 * Legacy helper retained for compatibility; use ReconnectingWebSocket below.
 */
export function connectAnalysisWebSocket(
  analysisId: string,
  onProgress: ProgressCallback,
  onComplete: CompleteCallback,
  onError: ErrorCallback
): WebSocket {
  // eslint-disable-next-line no-console
  console.warn('connectAnalysisWebSocket is deprecated; use ReconnectingWebSocket (Socket.IO).');
  // Dummy WebSocket to keep callers from crashing; real-time progress is handled by ReconnectingWebSocket.
  // @ts-expect-error - Intentional stub
  return {};
}

/**
 * Check if WebSocket is supported
 */
export function isWebSocketSupported(): boolean {
  // Socket.IO uses WebSocket/polling under the hood.
  return true;
}

/**
 * Socket.IO connection with automatic reconnection and room subscription.
 */
export class ReconnectingWebSocket {
  public socket: Socket | null = null;
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
    this.connect();
  }
  
  public updateAnalysisId(newAnalysisId: string): void {
    const prev = this.currentAnalysisId;
    this.currentAnalysisId = newAnalysisId;
    if (this.socket && this.socket.connected) {
      if (prev) {
        this.socket.emit('unsubscribe', { analysis_id: prev });
      }
      this.socket.emit('subscribe', { analysis_id: newAnalysisId });
    }
  }

  private connect() {
    try {
      this.socket = io(SOCKET_IO_URL, {
        path: '/socket.io',
        // Prefer polling first (more reliable behind some HTTPS proxies),
        // but allow websocket upgrade if available.
        transports: ['polling', 'websocket'],
        withCredentials: true,
        timeout: 120000, // 2 min so server under load (model load) can still respond
        reconnection: true,
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: this.reconnectDelay,
      });

      this.socket.on('connect', () => {
        console.log('Socket.IO connected:', this.socket?.id);
        this.reconnectAttempts = 0;
        // subscribe to current room
        this.socket?.emit('subscribe', { analysis_id: this.currentAnalysisId || this.analysisId });
      });

      this.socket.on('connect_error', (err: any) => {
        console.error('Socket.IO connect_error:', err);
      });

      this.socket.on('progress', (payload: any) => {
        // Payload already includes status/message/progress
        const data = payload as ProgressMessage & { status?: string; message?: string; progress?: number };
        if (data.progress !== undefined && data.status && data.message) {
          this.onProgress(data.progress, data.status, data.message);
        }
      });

      this.socket.on('complete', (payload: any) => {
        const data = payload as any;
        // Backend sends { result: response }
        const result = data?.result || data;
        if (result) {
          this.onComplete(result);
          this.close();
        }
      });

      this.socket.on('error', (payload: any) => {
        const msg = typeof payload === 'string' ? payload : (payload?.error || 'Socket.IO error');
        this.onError(msg);
      });

      this.socket.on('disconnect', (reason: any) => {
        console.warn('Socket.IO disconnected:', reason);
      });
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      this.onError('WebSocket not supported or connection failed');
    }
  }

  public close() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  public send(data: any) {
    if (!this.socket || !this.socket.connected) return;
    // Map previous message shapes to Socket.IO events
    if (data?.type === 'subscribe') {
      this.socket.emit('subscribe', { analysis_id: data.analysis_id });
    } else if (data?.type === 'update_analysis_id') {
      this.updateAnalysisId(data.analysis_id);
    } else {
      // Generic fallback
      this.socket.emit('message', data);
    }
  }

  public isConnected(): boolean {
    return !!this.socket?.connected;
  }
}

