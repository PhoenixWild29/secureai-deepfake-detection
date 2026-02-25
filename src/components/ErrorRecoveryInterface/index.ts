/**
 * Error Recovery Interface Components
 * Export all error recovery interface components and utilities
 */

// Main Components
export { default as ErrorRecoveryInterface } from './ErrorRecoveryInterface';
export { default as ErrorDetails } from './ErrorDetails';
export { default as RetryOptions } from './RetryOptions';
export { default as ErrorLogViewer } from './ErrorLogViewer';
export { default as TroubleshootingGuide } from './TroubleshootingGuide';
export { default as RetryHistory } from './RetryHistory';

// Re-export types for convenience
export type {
  ErrorInfo,
  ErrorContext,
  RetryAttempt,
  RetryResult,
  RetryConfiguration,
  TroubleshootingStep,
  ErrorLogEntry,
  UserRole,
  Permission,
  ErrorType,
  ErrorSeverity,
  RetryScope,
  RetryStatus,
  TroubleshootingType,
  TroubleshootingPriority,
  LogLevel,
  PermissionScope,
  ErrorRecoveryInterfaceProps,
  ErrorDetailsProps,
  RetryOptionsProps,
  ErrorLogViewerProps,
  TroubleshootingGuideProps,
  RetryHistoryProps,
} from '@/types/errorRecovery';

// Re-export service for convenience
export { 
  errorRecoveryService,
  createErrorRecoveryService,
  ErrorRecoveryService 
} from '@/services/errorRecoveryService';

// Re-export error type configurations
export { ERROR_TYPE_CONFIGS } from '@/types/errorRecovery';

// Default export
export { default } from './ErrorRecoveryInterface';
