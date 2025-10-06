/**
 * Workflow Error Handling Utilities
 * Centralized error handling functions and messages for detection workflow stages
 */

import { WORKFLOW_STAGES } from '../context/WorkflowContext';

// Error types
export const ERROR_TYPES = {
  NETWORK_ERROR: 'network_error',
  VALIDATION_ERROR: 'validation_error',
  UPLOAD_ERROR: 'upload_error',
  ANALYSIS_ERROR: 'analysis_error',
  RESULTS_ERROR: 'results_error',
  AUTHENTICATION_ERROR: 'authentication_error',
  TIMEOUT_ERROR: 'timeout_error',
  UNKNOWN_ERROR: 'unknown_error'
};

// Error severity levels
export const ERROR_SEVERITY = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical'
};

// Error recovery actions
export const RECOVERY_ACTIONS = {
  RETRY: 'retry',
  RESTART: 'restart',
  SKIP: 'skip',
  CANCEL: 'cancel',
  CONTACT_SUPPORT: 'contact_support'
};

/**
 * Error message templates
 */
const ERROR_MESSAGES = {
  [ERROR_TYPES.NETWORK_ERROR]: {
    title: 'Network Error',
    message: 'Unable to connect to the server. Please check your internet connection and try again.',
    severity: ERROR_SEVERITY.HIGH,
    recoveryActions: [RECOVERY_ACTIONS.RETRY, RECOVERY_ACTIONS.CONTACT_SUPPORT]
  },
  
  [ERROR_TYPES.VALIDATION_ERROR]: {
    title: 'Validation Error',
    message: 'The uploaded file does not meet the requirements. Please check the file format and size.',
    severity: ERROR_SEVERITY.MEDIUM,
    recoveryActions: [RECOVERY_ACTIONS.RESTART]
  },
  
  [ERROR_TYPES.UPLOAD_ERROR]: {
    title: 'Upload Failed',
    message: 'Failed to upload the video file. Please try again or contact support if the problem persists.',
    severity: ERROR_SEVERITY.HIGH,
    recoveryActions: [RECOVERY_ACTIONS.RETRY, RECOVERY_ACTIONS.CONTACT_SUPPORT]
  },
  
  [ERROR_TYPES.ANALYSIS_ERROR]: {
    title: 'Analysis Failed',
    message: 'The video analysis encountered an error. Please try again or contact support.',
    severity: ERROR_SEVERITY.HIGH,
    recoveryActions: [RECOVERY_ACTIONS.RETRY, RECOVERY_ACTIONS.CONTACT_SUPPORT]
  },
  
  [ERROR_TYPES.RESULTS_ERROR]: {
    title: 'Results Error',
    message: 'Unable to load analysis results. Please refresh the page or contact support.',
    severity: ERROR_SEVERITY.MEDIUM,
    recoveryActions: [RECOVERY_ACTIONS.RETRY, RECOVERY_ACTIONS.CONTACT_SUPPORT]
  },
  
  [ERROR_TYPES.AUTHENTICATION_ERROR]: {
    title: 'Authentication Required',
    message: 'Please log in to continue with the analysis.',
    severity: ERROR_SEVERITY.HIGH,
    recoveryActions: [RECOVERY_ACTIONS.RESTART]
  },
  
  [ERROR_TYPES.TIMEOUT_ERROR]: {
    title: 'Request Timeout',
    message: 'The request is taking longer than expected. Please try again.',
    severity: ERROR_SEVERITY.MEDIUM,
    recoveryActions: [RECOVERY_ACTIONS.RETRY, RECOVERY_ACTIONS.CONTACT_SUPPORT]
  },
  
  [ERROR_TYPES.UNKNOWN_ERROR]: {
    title: 'Unexpected Error',
    message: 'An unexpected error occurred. Please try again or contact support.',
    severity: ERROR_SEVERITY.HIGH,
    recoveryActions: [RECOVERY_ACTIONS.RETRY, RECOVERY_ACTIONS.CONTACT_SUPPORT]
  }
};

/**
 * Stage-specific error configurations
 */
const STAGE_ERROR_CONFIGS = {
  [WORKFLOW_STAGES.UPLOAD]: {
    primaryErrorTypes: [ERROR_TYPES.VALIDATION_ERROR, ERROR_TYPES.UPLOAD_ERROR, ERROR_TYPES.NETWORK_ERROR],
    fallbackStage: WORKFLOW_STAGES.INITIAL,
    maxRetries: 3
  },
  
  [WORKFLOW_STAGES.PROCESSING]: {
    primaryErrorTypes: [ERROR_TYPES.ANALYSIS_ERROR, ERROR_TYPES.NETWORK_ERROR, ERROR_TYPES.TIMEOUT_ERROR],
    fallbackStage: WORKFLOW_STAGES.UPLOAD,
    maxRetries: 2
  },
  
  [WORKFLOW_STAGES.RESULTS]: {
    primaryErrorTypes: [ERROR_TYPES.RESULTS_ERROR, ERROR_TYPES.NETWORK_ERROR],
    fallbackStage: WORKFLOW_STAGES.PROCESSING,
    maxRetries: 2
  },
  
  [WORKFLOW_STAGES.ERROR]: {
    primaryErrorTypes: [ERROR_TYPES.UNKNOWN_ERROR],
    fallbackStage: WORKFLOW_STAGES.INITIAL,
    maxRetries: 1
  }
};

/**
 * Create error object with standardized format
 * @param {string} type - Error type
 * @param {string} message - Error message
 * @param {Object} details - Additional error details
 * @param {string} stage - Workflow stage where error occurred
 * @returns {Object} Standardized error object
 */
export const createError = (type, message, details = {}, stage = null) => {
  const errorConfig = ERROR_MESSAGES[type] || ERROR_MESSAGES[ERROR_TYPES.UNKNOWN_ERROR];
  
  return {
    id: `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    type,
    title: errorConfig.title,
    message: message || errorConfig.message,
    severity: errorConfig.severity,
    stage,
    details,
    timestamp: new Date().toISOString(),
    recoveryActions: errorConfig.recoveryActions,
    retryCount: 0,
    maxRetries: STAGE_ERROR_CONFIGS[stage]?.maxRetries || 3
  };
};

/**
 * Handle upload stage errors
 * @param {Error} error - Original error
 * @param {Object} context - Upload context
 * @returns {Object} Handled error
 */
export const handleUploadError = (error, context = {}) => {
  let errorType = ERROR_TYPES.UPLOAD_ERROR;
  let errorMessage = error.message;
  
  // Determine error type based on error details
  if (error.name === 'ValidationError' || error.message.includes('validation')) {
    errorType = ERROR_TYPES.VALIDATION_ERROR;
  } else if (error.name === 'NetworkError' || error.message.includes('network')) {
    errorType = ERROR_TYPES.NETWORK_ERROR;
  } else if (error.message.includes('timeout')) {
    errorType = ERROR_TYPES.TIMEOUT_ERROR;
  } else if (error.message.includes('authentication') || error.message.includes('unauthorized')) {
    errorType = ERROR_TYPES.AUTHENTICATION_ERROR;
  }
  
  const handledError = createError(
    errorType,
    errorMessage,
    {
      originalError: error,
      fileInfo: context.fileInfo,
      uploadProgress: context.uploadProgress
    },
    WORKFLOW_STAGES.UPLOAD
  );
  
  console.error('Upload error:', handledError);
  return handledError;
};

/**
 * Handle analysis stage errors
 * @param {Error} error - Original error
 * @param {Object} context - Analysis context
 * @returns {Object} Handled error
 */
export const handleAnalysisError = (error, context = {}) => {
  let errorType = ERROR_TYPES.ANALYSIS_ERROR;
  let errorMessage = error.message;
  
  // Determine error type based on error details
  if (error.name === 'NetworkError' || error.message.includes('network')) {
    errorType = ERROR_TYPES.NETWORK_ERROR;
  } else if (error.message.includes('timeout')) {
    errorType = ERROR_TYPES.TIMEOUT_ERROR;
  } else if (error.message.includes('authentication')) {
    errorType = ERROR_TYPES.AUTHENTICATION_ERROR;
  }
  
  const handledError = createError(
    errorType,
    errorMessage,
    {
      originalError: error,
      analysisId: context.analysisId,
      analysisProgress: context.analysisProgress,
      processingStatus: context.processingStatus
    },
    WORKFLOW_STAGES.PROCESSING
  );
  
  console.error('Analysis error:', handledError);
  return handledError;
};

/**
 * Handle results stage errors
 * @param {Error} error - Original error
 * @param {Object} context - Results context
 * @returns {Object} Handled error
 */
export const handleResultsError = (error, context = {}) => {
  let errorType = ERROR_TYPES.RESULTS_ERROR;
  let errorMessage = error.message;
  
  // Determine error type based on error details
  if (error.name === 'NetworkError' || error.message.includes('network')) {
    errorType = ERROR_TYPES.NETWORK_ERROR;
  } else if (error.message.includes('timeout')) {
    errorType = ERROR_TYPES.TIMEOUT_ERROR;
  }
  
  const handledError = createError(
    errorType,
    errorMessage,
    {
      originalError: error,
      analysisId: context.analysisId,
      resultsData: context.resultsData
    },
    WORKFLOW_STAGES.RESULTS
  );
  
  console.error('Results error:', handledError);
  return handledError;
};

/**
 * Handle general workflow errors
 * @param {Error} error - Original error
 * @param {Object} context - Error context
 * @returns {Object} Handled error
 */
export const handleWorkflowError = (error, context = {}) => {
  let errorType = ERROR_TYPES.UNKNOWN_ERROR;
  let errorMessage = error.message;
  
  // Determine error type based on error details
  if (error.name === 'NetworkError' || error.message.includes('network')) {
    errorType = ERROR_TYPES.NETWORK_ERROR;
  } else if (error.message.includes('authentication')) {
    errorType = ERROR_TYPES.AUTHENTICATION_ERROR;
  } else if (error.message.includes('timeout')) {
    errorType = ERROR_TYPES.TIMEOUT_ERROR;
  }
  
  const handledError = createError(
    errorType,
    errorMessage,
    {
      originalError: error,
      workflowContext: context
    },
    context.currentStage
  );
  
  console.error('Workflow error:', handledError);
  return handledError;
};

/**
 * Get error recovery strategy
 * @param {Object} error - Error object
 * @param {Object} workflowState - Current workflow state
 * @returns {Object} Recovery strategy
 */
export const getRecoveryStrategy = (error, workflowState) => {
  const stageConfig = STAGE_ERROR_CONFIGS[error.stage];
  const canRetry = error.retryCount < error.maxRetries;
  
  const strategy = {
    canRetry,
    fallbackStage: stageConfig?.fallbackStage || WORKFLOW_STAGES.INITIAL,
    recommendedAction: canRetry ? RECOVERY_ACTIONS.RETRY : RECOVERY_ACTIONS.RESTART,
    recoveryActions: error.recoveryActions,
    userMessage: getRecoveryMessage(error, canRetry)
  };
  
  return strategy;
};

/**
 * Get recovery message for user
 * @param {Object} error - Error object
 * @param {boolean} canRetry - Whether retry is possible
 * @returns {string} Recovery message
 */
export const getRecoveryMessage = (error, canRetry) => {
  if (canRetry) {
    return `You can try again (${error.maxRetries - error.retryCount} attempts remaining).`;
  }
  
  const fallbackStage = STAGE_ERROR_CONFIGS[error.stage]?.fallbackStage;
  
  if (fallbackStage === WORKFLOW_STAGES.INITIAL) {
    return 'Please start over with a new analysis.';
  } else if (fallbackStage === WORKFLOW_STAGES.UPLOAD) {
    return 'Please try uploading the file again.';
  } else if (fallbackStage === WORKFLOW_STAGES.PROCESSING) {
    return 'Please try the analysis again.';
  }
  
  return 'Please contact support for assistance.';
};

/**
 * Format error for display
 * @param {Object} error - Error object
 * @returns {Object} Formatted error for UI
 */
export const formatErrorForDisplay = (error) => {
  return {
    title: error.title,
    message: error.message,
    severity: error.severity,
    stage: error.stage,
    timestamp: error.timestamp,
    canRetry: error.retryCount < error.maxRetries,
    retryCount: error.retryCount,
    maxRetries: error.maxRetries,
    recoveryActions: error.recoveryActions,
    recoveryMessage: getRecoveryMessage(error, error.retryCount < error.maxRetries)
  };
};

/**
 * Log error for analytics/debugging
 * @param {Object} error - Error object
 * @param {Object} context - Additional context
 */
export const logError = (error, context = {}) => {
  const logData = {
    errorId: error.id,
    errorType: error.type,
    errorStage: error.stage,
    errorSeverity: error.severity,
    errorMessage: error.message,
    timestamp: error.timestamp,
    context,
    userAgent: navigator.userAgent,
    url: window.location.href
  };
  
  // Log to console for development
  console.error('Workflow Error Log:', logData);
  
  // In production, this could send to analytics service
  // analyticsService.trackError(logData);
};

/**
 * Create retry configuration
 * @param {Object} error - Error object
 * @param {Object} options - Retry options
 * @returns {Object} Retry configuration
 */
export const createRetryConfig = (error, options = {}) => {
  const {
    maxRetries = error.maxRetries,
    retryDelay = 1000,
    exponentialBackoff = true,
    maxRetryDelay = 30000
  } = options;
  
  const retryCount = error.retryCount || 0;
  const delay = exponentialBackoff 
    ? Math.min(retryDelay * Math.pow(2, retryCount), maxRetryDelay)
    : retryDelay;
  
  return {
    canRetry: retryCount < maxRetries,
    retryCount,
    maxRetries,
    delay,
    nextRetryAt: new Date(Date.now() + delay)
  };
};

/**
 * Error boundary helper for React components
 * @param {Error} error - Error object
 * @param {Object} errorInfo - Error info from React
 * @returns {Object} Formatted error for error boundary
 */
export const handleReactError = (error, errorInfo) => {
  const handledError = createError(
    ERROR_TYPES.UNKNOWN_ERROR,
    error.message,
    {
      originalError: error,
      errorInfo,
      componentStack: errorInfo.componentStack
    }
  );
  
  logError(handledError, { errorInfo });
  return handledError;
};

export default {
  createError,
  handleUploadError,
  handleAnalysisError,
  handleResultsError,
  handleWorkflowError,
  getRecoveryStrategy,
  getRecoveryMessage,
  formatErrorForDisplay,
  logError,
  createRetryConfig,
  handleReactError,
  ERROR_TYPES,
  ERROR_SEVERITY,
  RECOVERY_ACTIONS
};
