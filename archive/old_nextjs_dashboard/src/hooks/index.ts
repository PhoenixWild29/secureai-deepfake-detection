/**
 * Custom React Hooks Index
 * Exports all custom hooks for state management and API integration
 */

// ============================================================================
// Main Hooks
// ============================================================================

export { default as useDetectionAnalysis } from './useDetectionAnalysis';
export { default as useVideoUpload } from './useVideoUpload';
export { default as useWebSocketEvents } from './useWebSocketEvents';

// ============================================================================
// Existing Hooks (re-export for convenience)
// ============================================================================

export { useAuth, withAuth, useAuthCheck, getStoredToken, storeToken, removeStoredToken } from './useAuth';
export { default as useWorkflowState } from './useWorkflowState';

// ============================================================================
// Types
// ============================================================================

export type {
  // Common types
  StandardError,
  ProgressInfo,
  FileMetadata,
  
  // Detection Analysis types
  AnalysisState,
  AnalysisProgress,
  DetectionResult,
  AnalysisOptions,
  UseDetectionAnalysisReturn,
  
  // Video Upload types
  UploadState,
  UploadProgress,
  UploadResult,
  ValidationResult,
  UploadOptions,
  UseVideoUploadReturn,
  FileValidationRules,
  
  // WebSocket Events types
  WebSocketState,
  WebSocketConfig,
  WebSocketEvent,
  StatusUpdateEvent,
  ResultUpdateEvent,
  HeartbeatEvent,
  ReconnectionInfo,
  UseWebSocketEventsReturn,
  
  // API Integration types
  ApiResponse,
  DetectionApiResponse,
  UploadApiResponse,
  StatusApiResponse,
  
  // React Query Integration types
  QueryOptions,
  MutationOptions,
  
  // Utility types
  RetryConfig,
  WebSocketMessageHandler,
  ProgressCallback,
  ErrorCallback,
  
  // Hook Configuration types
  DetectionAnalysisConfig,
  VideoUploadConfig
} from '../types/hooks';

// ============================================================================
// Error Handling Utilities
// ============================================================================

export {
  createStandardError,
  createErrorFromNative,
  createErrorFromApiResponse,
  determineErrorType,
  determineErrorTypeFromStatus,
  getDefaultMaxRetries,
  canRetryError,
  calculateRetryDelay,
  incrementRetryCount,
  formatErrorForDisplay,
  getUserFriendlyMessage,
  logError,
  isCriticalError,
  shouldStopWorkflow,
  mergeErrorDetails,
  createDetectionError,
  createUploadError,
  createWebSocketError,
  ERROR_TYPES,
  ERROR_SEVERITY,
  RECOVERY_ACTIONS
} from '../utils/errorHandling';

// ============================================================================
// Hook Usage Examples and Documentation
// ============================================================================

/**
 * EXAMPLE USAGE:
 * 
 * // Detection Analysis Hook
 * import { useDetectionAnalysis } from './hooks';
 * 
 * function DetectionComponent() {
 *   const {
 *     state,
 *     progress,
 *     result,
 *     error,
 *     startAnalysis,
 *     retryAnalysis,
 *     clearError
 *   } = useDetectionAnalysis();
 * 
 *   const handleFileUpload = async (file: File) => {
 *     await startAnalysis(file, { userId: 'user123' });
 *   };
 * 
 *   return (
 *     <div>
 *       {state === 'idle' && <FileUpload onUpload={handleFileUpload} />}
 *       {state === 'processing' && <ProgressBar progress={progress} />}
 *       {state === 'completed' && <Results result={result} />}
 *       {state === 'error' && <ErrorMessage error={error} onRetry={retryAnalysis} />}
 *     </div>
 *   );
 * } 
 * 
 * // Video Upload Hook
 * import { useVideoUpload } from './hooks';
 * 
 * function VideoUploadComponent() {
 *   const {
 *     state,
 *     progress,
 *     result,
 *     error,
 *     validation,
 *     preview,
 *     selectFile,
 *     uploadFile,
 *     cancelUpload
 *   } = useVideoUpload();
 * 
 *   const handleFileSelect = async (file: File) => {
 *     const validation = await selectFile(file);
 *     if (validation.isValid) {
 *       await uploadFile();
 *     }
 *   };
 * 
 *   return (
 *     <div>
 *       {preview && <img src={preview} alt="Preview" />}
 *       {progress && <UploadProgress progress={progress} />}
 *       {error && <ErrorMessage error={error} />}
 *     </div>
 *   );
 * }
 * 
 * // WebSocket Events Hook
 * import { useWebSocketEvents } from './hooks';
 * 
 * function RealTimeComponent() {
 *   const {
 *     state,
 *     isConnected,
 *     lastError,
 *     connect,
 *     disconnect,
 *     sendMessage,
 *     onStatusUpdate,
 *     onResultUpdate
 *   } = useWebSocketEvents({
 *     url: 'ws://localhost:8000/ws',
 *     enableHeartbeat: true
 *   });
 * 
 *   useEffect(() => {
 *     connect();
 *     
 *     onStatusUpdate((event) => {
 *       console.log('Status update:', event.data);
 *     });
 *     
 *     onResultUpdate((event) => {
 *       console.log('Result update:', event.data);
 *     });
 *     
 *     return () => disconnect();
 *   }, []);
 * 
 *   return (
 *     <div>
 *       <p>Status: {state}</p>
 *       <p>Connected: {isConnected ? 'Yes' : 'No'}</p>
 *       {lastError && <ErrorMessage error={lastError} />}
 *     </div>
 *   );
 * }
 */