/**
 * TypeScript Declaration File for Custom React Hooks
 * Defines interfaces and types for useDetectionAnalysis, useVideoUpload, and useWebSocketEvents hooks
 */

// ============================================================================
// Common Types
// ============================================================================

export interface StandardError {
  id: string;
  type: string;
  title: string;
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  stage?: string;
  details?: Record<string, any>;
  timestamp: string;
  recoveryActions: string[];
  retryCount: number;
  maxRetries: number;
}

export interface ProgressInfo {
  loaded: number;
  total: number;
  percentage: number;
  speed: number;
  estimatedTime: number;
}

export interface FileMetadata {
  name: string;
  size: number;
  type: string;
  lastModified: number;
  preview?: string;
}

// ============================================================================
// useDetectionAnalysis Hook Types
// ============================================================================

export type AnalysisState = 'idle' | 'uploading' | 'processing' | 'completed' | 'error';

export interface AnalysisProgress {
  stage: string;
  percentage: number;
  message: string;
  estimatedTimeRemaining?: number;
}

export interface DetectionResult {
  analysisId: string;
  isFake: boolean;
  confidence: number;
  processingTime: number;
  timestamp: string;
  blockchainHash?: string;
  securityAnalysis?: {
    riskLevel: string;
    anomalies: string[];
    recommendations: string[];
  };
  metadata: {
    filename: string;
    fileSize: number;
    duration?: number;
    resolution?: string;
  };
}

export interface AnalysisOptions {
  userId?: string;
  metadata?: Record<string, any>;
  enableSecurityAnalysis?: boolean;
  enableBlockchainVerification?: boolean;
}

export interface UseDetectionAnalysisReturn {
  // State
  state: AnalysisState;
  progress: AnalysisProgress | null;
  result: DetectionResult | null;
  error: StandardError | null;
  isRetrying: boolean;
  
  // Actions
  startAnalysis: (file: File, options?: AnalysisOptions) => Promise<void>;
  retryAnalysis: () => Promise<void>;
  clearError: () => void;
  resetAnalysis: () => void;
  
  // React Query integration
  refetch: () => void;
  isRefetching: boolean;
  lastFetchTime: number | null;
}

// ============================================================================
// useVideoUpload Hook Types
// ============================================================================

export type UploadState = 'idle' | 'validating' | 'uploading' | 'completed' | 'error';

export interface UploadProgress extends ProgressInfo {
  stage: 'preparing' | 'uploading' | 'processing' | 'complete';
  speedFormatted: string;
  timeRemainingFormatted: string;
}

export interface UploadResult {
  success: boolean;
  key: string;
  url: string;
  etag?: string;
  uploadTime: number;
  metadata: {
    bucket: string;
    region: string;
    originalName: string;
    fileSize: number;
  };
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  fileInfo: FileMetadata;
}

export interface UploadOptions {
  key?: string;
  prefix?: string;
  metadata?: Record<string, any>;
  usePresignedUrl?: boolean;
  chunkSize?: number;
  maxRetries?: number;
}

export interface UseVideoUploadReturn {
  // State
  state: UploadState;
  progress: UploadProgress | null;
  result: UploadResult | null;
  error: StandardError | null;
  validation: ValidationResult | null;
  preview: string | null;
  
  // Actions
  selectFile: (file: File) => Promise<ValidationResult>;
  uploadFile: (options?: UploadOptions) => Promise<void>;
  cancelUpload: () => void;
  clearError: () => void;
  resetUpload: () => void;
  generatePreview: (file: File) => Promise<string>;
  
  // File handling
  validateFile: (file: File) => ValidationResult;
  formatFileSize: (bytes: number) => string;
  formatUploadSpeed: (bytesPerSecond: number) => string;
}

// ============================================================================
// useWebSocketEvents Hook Types
// ============================================================================

export type WebSocketState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error';

export interface WebSocketConfig {
  url: string;
  protocols?: string[];
  heartbeatInterval?: number;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  reconnectBackoffMultiplier?: number;
  enableHeartbeat?: boolean;
  enableReconnection?: boolean;
  fallbackPollingInterval?: number;
}

export interface WebSocketEvent {
  type: string;
  data: any;
  timestamp: string;
  id?: string;
}

export interface StatusUpdateEvent extends WebSocketEvent {
  type: 'status_update';
  data: {
    analysisId: string;
    status: string;
    progress: number;
    message: string;
    estimatedTimeRemaining?: number;
  };
}

export interface ResultUpdateEvent extends WebSocketEvent {
  type: 'result_update';
  data: {
    analysisId: string;
    result: DetectionResult;
    completed: boolean;
  };
}

export interface HeartbeatEvent extends WebSocketEvent {
  type: 'heartbeat';
  data: {
    timestamp: string;
    serverTime: string;
  };
}

export interface ReconnectionInfo {
  attempt: number;
  maxAttempts: number;
  nextAttemptAt: number;
  backoffDelay: number;
}

export interface UseWebSocketEventsReturn {
  // State
  state: WebSocketState;
  isConnected: boolean;
  isReconnecting: boolean;
  lastError: StandardError | null;
  reconnectionInfo: ReconnectionInfo | null;
  lastHeartbeat: string | null;
  
  // Actions
  connect: () => void;
  disconnect: () => void;
  reconnect: () => void;
  sendMessage: (message: any) => void;
  clearError: () => void;
  
  // Event handling
  onStatusUpdate: (callback: (event: StatusUpdateEvent) => void) => void;
  onResultUpdate: (callback: (event: ResultUpdateEvent) => void) => void;
  onHeartbeat: (callback: (event: HeartbeatEvent) => void) => void;
  onError: (callback: (error: StandardError) => void) => void;
  onConnect: (callback: () => void) => void;
  onDisconnect: (callback: () => void) => void;
  
  // Event cleanup
  removeEventListener: (eventType: string, callback: Function) => void;
  removeAllEventListeners: (eventType?: string) => void;
}

// ============================================================================
// API Integration Types
// ============================================================================

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface DetectionApiResponse extends ApiResponse {
  data?: DetectionResult;
}

export interface UploadApiResponse extends ApiResponse {
  data?: UploadResult;
}

export interface StatusApiResponse extends ApiResponse {
  data?: {
    status: string;
    progress: number;
    message: string;
    estimatedTimeRemaining?: number;
  };
}

// ============================================================================
// React Query Integration Types
// ============================================================================

export interface QueryOptions {
  enabled?: boolean;
  staleTime?: number;
  cacheTime?: number;
  refetchOnWindowFocus?: boolean;
  refetchOnMount?: boolean;
  retry?: number | boolean;
  retryDelay?: number | ((retryAttempt: number) => number);
}

export interface MutationOptions<T = any> {
  onSuccess?: (data: T) => void;
  onError?: (error: StandardError) => void;
  onSettled?: (data: T | undefined, error: StandardError | null) => void;
}

// ============================================================================
// Utility Types
// ============================================================================

export interface RetryConfig {
  maxRetries: number;
  retryDelay: number;
  exponentialBackoff: boolean;
  maxRetryDelay: number;
}

export interface FileValidationRules {
  maxSize: number;
  allowedTypes: string[];
  allowedExtensions: string[];
  minSize?: number;
}

export interface WebSocketMessageHandler {
  (event: WebSocketEvent): void;
}

export interface ProgressCallback {
  (progress: ProgressInfo): void;
}

export interface ErrorCallback {
  (error: StandardError): void;
}

// ============================================================================
// Hook Configuration Types
// ============================================================================

export interface DetectionAnalysisConfig {
  apiEndpoint: string;
  queryOptions?: QueryOptions;
  retryConfig?: RetryConfig;
  enableOptimisticUpdates?: boolean;
  enableCache?: boolean;
}

export interface VideoUploadConfig {
  s3Config: {
    bucket: string;
    region: string;
    usePresignedUrls: boolean;
  };
  validationRules: FileValidationRules;
  uploadOptions?: UploadOptions;
  retryConfig?: RetryConfig;
}

export interface WebSocketConfig {
  url: string;
  heartbeatInterval?: number;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  reconnectBackoffMultiplier?: number;
  enableHeartbeat?: boolean;
  enableReconnection?: boolean;
  fallbackPollingInterval?: number;
}
