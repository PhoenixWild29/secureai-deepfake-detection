/**
 * Centralized Error Handling Utility
 * Provides consistent error management across all custom hooks
 */

import { StandardError } from '../types/hooks';

// ============================================================================
// Error Types and Constants
// ============================================================================

export const ERROR_TYPES = {
  NETWORK_ERROR: 'network_error',
  VALIDATION_ERROR: 'validation_error',
  UPLOAD_ERROR: 'upload_error',
  ANALYSIS_ERROR: 'analysis_error',
  WEBSOCKET_ERROR: 'websocket_error',
  AUTHENTICATION_ERROR: 'authentication_error',
  TIMEOUT_ERROR: 'timeout_error',
  FILE_ERROR: 'file_error',
  API_ERROR: 'api_error',
  UNKNOWN_ERROR: 'unknown_error'
} as const;

export const ERROR_SEVERITY = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical'
} as const;

export const RECOVERY_ACTIONS = {
  RETRY: 'retry',
  RESTART: 'restart',
  SKIP: 'skip',
  CANCEL: 'cancel',
  CONTACT_SUPPORT: 'contact_support',
  REFRESH: 'refresh'
} as const;

// ============================================================================
// Error Message Templates
// ============================================================================

const ERROR_MESSAGES = {
  [ERROR_TYPES.NETWORK_ERROR]: {
    title: 'Network Error',
    message: 'Unable to connect to the server. Please check your internet connection and try again.',
    severity: ERROR_SEVERITY.HIGH,
    recoveryActions: [RECOVERY_ACTIONS.RETRY, RECOVERY_ACTIONS.REFRESH]
  },
  
  [ERROR_TYPES.VALIDATION_ERROR]: {
    title: 'Validation Error',
    message: 'The provided data does not meet the requirements. Please check your input and try again.',
    severity: ERROR_SEVERITY.MEDIUM,
    recoveryActions: [RECOVERY_ACTIONS.RETRY]
  },
  
  [ERROR_TYPES.UPLOAD_ERROR]: {
    title: 'Upload Failed',
    message: 'Failed to upload the file. Please try again or contact support if the problem persists.',
    severity: ERROR_SEVERITY.HIGH,
    recoveryActions: [RECOVERY_ACTIONS.RETRY, RECOVERY_ACTIONS.CONTACT_SUPPORT]
  },
  
  [ERROR_TYPES.ANALYSIS_ERROR]: {
    title: 'Analysis Failed',
    message: 'The analysis encountered an error. Please try again or contact support.',
    severity: ERROR_SEVERITY.HIGH,
    recoveryActions: [RECOVERY_ACTIONS.RETRY, RECOVERY_ACTIONS.CONTACT_SUPPORT]
  },
  
  [ERROR_TYPES.WEBSOCKET_ERROR]: {
    title: 'Connection Error',
    message: 'Lost connection to the server. Attempting to reconnect...',
    severity: ERROR_SEVERITY.MEDIUM,
    recoveryActions: [RECOVERY_ACTIONS.RETRY, RECOVERY_ACTIONS.REFRESH]
  },
  
  [ERROR_TYPES.AUTHENTICATION_ERROR]: {
    title: 'Authentication Required',
    message: 'Please log in to continue.',
    severity: ERROR_SEVERITY.HIGH,
    recoveryActions: [RECOVERY_ACTIONS.RESTART]
  },
  
  [ERROR_TYPES.TIMEOUT_ERROR]: {
    title: 'Request Timeout',
    message: 'The request is taking longer than expected. Please try again.',
    severity: ERROR_SEVERITY.MEDIUM,
    recoveryActions: [RECOVERY_ACTIONS.RETRY, RECOVERY_ACTIONS.CONTACT_SUPPORT]
  },
  
  [ERROR_TYPES.FILE_ERROR]: {
    title: 'File Error',
    message: 'There was a problem with the file. Please check the file and try again.',
    severity: ERROR_SEVERITY.MEDIUM,
    recoveryActions: [RECOVERY_ACTIONS.RETRY]
  },
  
  [ERROR_TYPES.API_ERROR]: {
    title: 'API Error',
    message: 'The server encountered an error. Please try again later.',
    severity: ERROR_SEVERITY.HIGH,
    recoveryActions: [RECOVERY_ACTIONS.RETRY, RECOVERY_ACTIONS.CONTACT_SUPPORT]
  },
  
  [ERROR_TYPES.UNKNOWN_ERROR]: {
    title: 'Unexpected Error',
    message: 'An unexpected error occurred. Please try again or contact support.',
    severity: ERROR_SEVERITY.HIGH,
    recoveryActions: [RECOVERY_ACTIONS.RETRY, RECOVERY_ACTIONS.CONTACT_SUPPORT]
  }
} as const;

// ============================================================================
// Error Creation Functions
// ============================================================================

/**
 * Create a standardized error object
 */
export function createStandardError(
  type: keyof typeof ERROR_TYPES,
  message?: string,
  details: Record<string, any> = {},
  stage?: string
): StandardError {
  const errorConfig = ERROR_MESSAGES[type];
  
  return {
    id: generateErrorId(),
    type: ERROR_TYPES[type],
    title: errorConfig.title,
    message: message || errorConfig.message,
    severity: errorConfig.severity,
    stage,
    details,
    timestamp: new Date().toISOString(),
    recoveryActions: errorConfig.recoveryActions,
    retryCount: 0,
    maxRetries: getDefaultMaxRetries(type)
  };
}

/**
 * Create error from a native JavaScript Error
 */
export function createErrorFromNative(
  error: Error,
  type?: keyof typeof ERROR_TYPES,
  context: Record<string, any> = {}
): StandardError {
  const errorType = type || determineErrorType(error);
  
  return createStandardError(
    errorType as keyof typeof ERROR_TYPES,
    error.message,
    {
      originalError: error,
      stack: error.stack,
      ...context
    }
  );
}

/**
 * Create error from API response
 */
export function createErrorFromApiResponse(
  response: Response,
  context: Record<string, any> = {}
): StandardError {
  const status = response.status;
  let type: keyof typeof ERROR_TYPES;
  let message: string;

  if (status === 401 || status === 403) {
    type = 'AUTHENTICATION_ERROR';
    message = 'Authentication required';
  } else if (status === 408 || status >= 500) {
    type = 'TIMEOUT_ERROR';
    message = 'Server error or timeout';
  } else if (status >= 400) {
    type = 'API_ERROR';
    message = `API error: ${status}`;
  } else {
    type = 'UNKNOWN_ERROR';
    message = 'Unknown API error';
  }

  return createStandardError(type, message, {
    status,
    statusText: response.statusText,
    url: response.url,
    ...context
  });
}

// ============================================================================
// Error Type Detection
// ============================================================================

/**
 * Determine error type from native Error
 */
export function determineErrorType(error: Error): keyof typeof ERROR_TYPES {
  const message = error.message.toLowerCase();
  const name = error.name.toLowerCase();

  if (name === 'networkerror' || message.includes('network') || message.includes('fetch')) {
    return 'NETWORK_ERROR';
  }
  
  if (message.includes('timeout')) {
    return 'TIMEOUT_ERROR';
  }
  
  if (message.includes('validation') || message.includes('invalid')) {
    return 'VALIDATION_ERROR';
  }
  
  if (message.includes('upload') || message.includes('file')) {
    return 'UPLOAD_ERROR';
  }
  
  if (message.includes('websocket') || message.includes('connection')) {
    return 'WEBSOCKET_ERROR';
  }
  
  if (message.includes('auth') || message.includes('unauthorized')) {
    return 'AUTHENTICATION_ERROR';
  }

  return 'UNKNOWN_ERROR';
}

/**
 * Determine error type from HTTP status code
 */
export function determineErrorTypeFromStatus(status: number): keyof typeof ERROR_TYPES {
  if (status === 401 || status === 403) {
    return 'AUTHENTICATION_ERROR';
  }
  
  if (status === 408) {
    return 'TIMEOUT_ERROR';
  }
  
  if (status >= 400 && status < 500) {
    return 'VALIDATION_ERROR';
  }
  
  if (status >= 500) {
    return 'API_ERROR';
  }

  return 'UNKNOWN_ERROR';
}

// ============================================================================
// Error Recovery and Retry Logic
// ============================================================================

/**
 * Get default max retries for error type
 */
export function getDefaultMaxRetries(type: keyof typeof ERROR_TYPES): number {
  const retryConfig = {
    [ERROR_TYPES.NETWORK_ERROR]: 3,
    [ERROR_TYPES.VALIDATION_ERROR]: 1,
    [ERROR_TYPES.UPLOAD_ERROR]: 2,
    [ERROR_TYPES.ANALYSIS_ERROR]: 2,
    [ERROR_TYPES.WEBSOCKET_ERROR]: 5,
    [ERROR_TYPES.AUTHENTICATION_ERROR]: 0,
    [ERROR_TYPES.TIMEOUT_ERROR]: 2,
    [ERROR_TYPES.FILE_ERROR]: 1,
    [ERROR_TYPES.API_ERROR]: 2,
    [ERROR_TYPES.UNKNOWN_ERROR]: 1
  };

  return retryConfig[type] || 1;
}

/**
 * Check if error can be retried
 */
export function canRetryError(error: StandardError): boolean {
  return error.retryCount < error.maxRetries;
}

/**
 * Calculate retry delay with exponential backoff
 */
export function calculateRetryDelay(
  retryCount: number,
  baseDelay: number = 1000,
  maxDelay: number = 30000,
  backoffMultiplier: number = 2
): number {
  const delay = baseDelay * Math.pow(backoffMultiplier, retryCount);
  return Math.min(delay, maxDelay);
}

/**
 * Increment retry count for error
 */
export function incrementRetryCount(error: StandardError): StandardError {
  return {
    ...error,
    retryCount: error.retryCount + 1
  };
}

// ============================================================================
// Error Formatting and Display
// ============================================================================

/**
 * Format error for user display
 */
export function formatErrorForDisplay(error: StandardError): {
  title: string;
  message: string;
  severity: string;
  canRetry: boolean;
  retryInfo: string;
  recoveryActions: string[];
} {
  const canRetry = canRetryError(error);
  const retryInfo = canRetry 
    ? `${error.maxRetries - error.retryCount} attempts remaining`
    : 'No more attempts available';

  return {
    title: error.title,
    message: error.message,
    severity: error.severity,
    canRetry,
    retryInfo,
    recoveryActions: error.recoveryActions
  };
}

/**
 * Get user-friendly error message
 */
export function getUserFriendlyMessage(error: StandardError): string {
  const display = formatErrorForDisplay(error);
  
  if (display.canRetry) {
    return `${display.message} (${display.retryInfo})`;
  }
  
  return display.message;
}

// ============================================================================
// Error Logging
// ============================================================================

/**
 * Log error for debugging and analytics
 */
export function logError(error: StandardError, context: Record<string, any> = {}): void {
  const logData = {
    errorId: error.id,
    errorType: error.type,
    errorSeverity: error.severity,
    errorStage: error.stage,
    errorMessage: error.message,
    retryCount: error.retryCount,
    maxRetries: error.maxRetries,
    timestamp: error.timestamp,
    context,
    userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
    url: typeof window !== 'undefined' ? window.location.href : 'unknown'
  };

  // Log to console in development
  if (typeof process !== 'undefined' && process.env?.NODE_ENV === 'development') {
    console.error('Standard Error:', logData);
  }

  // In production, this could send to analytics service
  // analyticsService.trackError(logData);
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Generate unique error ID
 */
function generateErrorId(): string {
  return `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Check if error is critical
 */
export function isCriticalError(error: StandardError): boolean {
  return error.severity === ERROR_SEVERITY.CRITICAL;
}

/**
 * Check if error should stop the workflow
 */
export function shouldStopWorkflow(error: StandardError): boolean {
  return isCriticalError(error) || 
         error.type === ERROR_TYPES.AUTHENTICATION_ERROR ||
         (error.retryCount >= error.maxRetries && error.severity === ERROR_SEVERITY.HIGH);
}

/**
 * Merge error details
 */
export function mergeErrorDetails(
  error: StandardError,
  additionalDetails: Record<string, any>
): StandardError {
  return {
    ...error,
    details: {
      ...error.details,
      ...additionalDetails
    }
  };
}

// ============================================================================
// Hook-specific Error Helpers
// ============================================================================

/**
 * Create detection analysis error
 */
export function createDetectionError(
  error: Error | Response,
  context: Record<string, any> = {}
): StandardError {
  if (error instanceof Response) {
    return createErrorFromApiResponse(error, context);
  }
  
  return createErrorFromNative(error, ERROR_TYPES.ANALYSIS_ERROR, context);
}

/**
 * Create video upload error
 */
export function createUploadError(
  error: Error | Response,
  context: Record<string, any> = {}
): StandardError {
  if (error instanceof Response) {
    return createErrorFromApiResponse(error, context);
  }
  
  return createErrorFromNative(error, 'UPLOAD_ERROR', context);
}

/**
 * Create WebSocket error
 */
export function createWebSocketError(
  error: Error | Event,
  context: Record<string, any> = {}
): StandardError {
  let message = 'WebSocket connection error';
  
  if (error instanceof Error) {
    message = error.message;
  } else if (error instanceof Event) {
    message = `WebSocket ${error.type} event`;
  }
  
  return createStandardError(
    'WEBSOCKET_ERROR',
    message,
    {
      originalError: error,
      ...context
    }
  );
}

// ============================================================================
// Default Export
// ============================================================================

export default {
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
};
