/**
 * Error Recovery Types
 * TypeScript interfaces for error recovery interface and manual retry capabilities
 */

export interface ErrorInfo {
  /** Unique error identifier */
  id: string;
  /** Error type/category */
  type: ErrorType;
  /** Error severity level */
  severity: ErrorSeverity;
  /** Error code */
  code: string;
  /** Error message */
  message: string;
  /** Detailed error description */
  description?: string;
  /** Stage where error occurred */
  stage: string;
  /** Timestamp when error occurred */
  timestamp: Date;
  /** Whether error is recoverable */
  recoverable: boolean;
  /** Error context data */
  context?: ErrorContext;
  /** Stack trace if available */
  stackTrace?: string;
  /** Additional error metadata */
  metadata?: Record<string, any>;
}

export interface ErrorContext {
  /** Analysis ID where error occurred */
  analysisId: string;
  /** Frame index if applicable */
  frameIndex?: number;
  /** Worker ID if applicable */
  workerId?: string;
  /** GPU ID if applicable */
  gpuId?: string;
  /** Queue position if applicable */
  queuePosition?: number;
  /** Processing step details */
  processingStep?: string;
  /** Input data information */
  inputData?: {
    fileName?: string;
    fileSize?: number;
    fileType?: string;
    duration?: number;
  };
  /** System state at time of error */
  systemState?: {
    cpuUsage?: number;
    memoryUsage?: number;
    diskSpace?: number;
    networkStatus?: string;
  };
}

export interface RetryAttempt {
  /** Unique retry attempt identifier */
  id: string;
  /** Retry attempt number */
  attemptNumber: number;
  /** Retry scope */
  scope: RetryScope;
  /** Retry timestamp */
  timestamp: Date;
  /** Retry status */
  status: RetryStatus;
  /** Retry result */
  result?: RetryResult;
  /** Error that occurred during retry */
  error?: ErrorInfo;
  /** Retry duration in milliseconds */
  duration?: number;
  /** User who initiated retry */
  initiatedBy?: string;
  /** Retry configuration */
  configuration?: RetryConfiguration;
}

export interface RetryResult {
  /** Whether retry was successful */
  success: boolean;
  /** Result message */
  message: string;
  /** Progress made during retry */
  progress?: number;
  /** New stage reached */
  newStage?: string;
  /** Additional result data */
  data?: Record<string, any>;
}

export interface RetryConfiguration {
  /** Retry scope */
  scope: RetryScope;
  /** Specific stage to retry */
  stage?: string;
  /** Specific frame to retry */
  frameIndex?: number;
  /** Retry options */
  options?: {
    skipCompletedStages?: boolean;
    useCachedResults?: boolean;
    forceRestart?: boolean;
    timeout?: number;
    maxRetries?: number;
  };
}

export interface TroubleshootingStep {
  /** Step identifier */
  id: string;
  /** Step title */
  title: string;
  /** Step description */
  description: string;
  /** Step type */
  type: TroubleshootingType;
  /** Whether step requires user action */
  requiresUserAction: boolean;
  /** Step priority */
  priority: TroubleshootingPriority;
  /** Estimated time to complete */
  estimatedTime?: number;
  /** Prerequisites */
  prerequisites?: string[];
  /** Expected outcome */
  expectedOutcome?: string;
  /** Additional resources */
  resources?: {
    documentation?: string;
    video?: string;
    support?: string;
  };
}

export interface ErrorLogEntry {
  /** Log entry identifier */
  id: string;
  /** Log level */
  level: LogLevel;
  /** Log message */
  message: string;
  /** Log timestamp */
  timestamp: Date;
  /** Log source */
  source: string;
  /** Additional log data */
  data?: Record<string, any>;
  /** Stack trace if applicable */
  stackTrace?: string;
  /** Related error ID */
  errorId?: string;
}

export interface UserRole {
  /** Role identifier */
  id: string;
  /** Role name */
  name: string;
  /** Role permissions */
  permissions: Permission[];
}

export interface Permission {
  /** Permission identifier */
  id: string;
  /** Permission name */
  name: string;
  /** Permission description */
  description: string;
  /** Permission scope */
  scope: PermissionScope;
}

export type ErrorType = 
  | 'upload_error'
  | 'frame_extraction_error'
  | 'feature_extraction_error'
  | 'inference_error'
  | 'result_processing_error'
  | 'blockchain_error'
  | 'system_error'
  | 'network_error'
  | 'timeout_error'
  | 'validation_error'
  | 'permission_error'
  | 'resource_error'
  | 'unknown_error';

export type ErrorSeverity = 'low' | 'medium' | 'high' | 'critical';

export type RetryScope = 'full_analysis' | 'stage' | 'frame' | 'worker' | 'gpu';

export type RetryStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';

export type TroubleshootingType = 
  | 'check_system'
  | 'verify_input'
  | 'restart_service'
  | 'clear_cache'
  | 'update_configuration'
  | 'contact_support'
  | 'manual_intervention';

export type TroubleshootingPriority = 'low' | 'medium' | 'high' | 'urgent';

export type LogLevel = 'debug' | 'info' | 'warning' | 'error' | 'critical';

export type PermissionScope = 'analysis' | 'retry' | 'error_details' | 'system' | 'admin';

export interface ErrorRecoveryInterfaceProps {
  /** Error information to display */
  error: ErrorInfo;
  /** Analysis ID */
  analysisId: string;
  /** Current user role */
  userRole?: UserRole;
  /** Retry history */
  retryHistory?: RetryAttempt[];
  /** Error logs */
  errorLogs?: ErrorLogEntry[];
  /** Whether to show detailed error information */
  showDetails?: boolean;
  /** Whether to show retry options */
  showRetryOptions?: boolean;
  /** Whether to show troubleshooting guide */
  showTroubleshooting?: boolean;
  /** Whether to show retry history */
  showRetryHistory?: boolean;
  /** Callback when retry is initiated */
  onRetry?: (config: RetryConfiguration) => Promise<void>;
  /** Callback when error is dismissed */
  onDismiss?: () => void;
  /** Callback when troubleshooting step is completed */
  onTroubleshootingComplete?: (stepId: string) => void;
  /** Additional CSS classes */
  className?: string;
}

export interface ErrorDetailsProps {
  /** Error information */
  error: ErrorInfo;
  /** Whether to show detailed information */
  showDetails?: boolean;
  /** Additional CSS classes */
  className?: string;
}

export interface RetryOptionsProps {
  /** Error information */
  error: ErrorInfo;
  /** Analysis ID */
  analysisId: string;
  /** User role */
  userRole?: UserRole;
  /** Retry history */
  retryHistory?: RetryAttempt[];
  /** Callback when retry is initiated */
  onRetry?: (config: RetryConfiguration) => Promise<void>;
  /** Additional CSS classes */
  className?: string;
}

export interface ErrorLogViewerProps {
  /** Error logs to display */
  errorLogs: ErrorLogEntry[];
  /** Whether to show stack traces */
  showStackTraces?: boolean;
  /** Whether to show detailed log data */
  showDetailedData?: boolean;
  /** Additional CSS classes */
  className?: string;
}

export interface TroubleshootingGuideProps {
  /** Error information */
  error: ErrorInfo;
  /** Troubleshooting steps */
  steps: TroubleshootingStep[];
  /** Callback when step is completed */
  onStepComplete?: (stepId: string) => void;
  /** Additional CSS classes */
  className?: string;
}

export interface RetryHistoryProps {
  /** Retry attempts history */
  retryHistory: RetryAttempt[];
  /** Whether to show detailed retry information */
  showDetails?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Error type configurations for troubleshooting guidance
 */
export const ERROR_TYPE_CONFIGS: Record<ErrorType, {
  name: string;
  description: string;
  commonCauses: string[];
  troubleshootingSteps: TroubleshootingStep[];
}> = {
  upload_error: {
    name: 'Upload Error',
    description: 'Error occurred during file upload process',
    commonCauses: [
      'File size exceeds limits',
      'Unsupported file format',
      'Network connectivity issues',
      'Server storage full'
    ],
    troubleshootingSteps: [
      {
        id: 'check_file_size',
        title: 'Check File Size',
        description: 'Verify that the file size is within the allowed limits',
        type: 'verify_input',
        requiresUserAction: true,
        priority: 'high',
        estimatedTime: 2
      },
      {
        id: 'check_file_format',
        title: 'Check File Format',
        description: 'Ensure the file format is supported',
        type: 'verify_input',
        requiresUserAction: true,
        priority: 'high',
        estimatedTime: 1
      }
    ]
  },
  frame_extraction_error: {
    name: 'Frame Extraction Error',
    description: 'Error occurred while extracting frames from video',
    commonCauses: [
      'Corrupted video file',
      'Unsupported video codec',
      'Insufficient memory',
      'Video processing library error'
    ],
    troubleshootingSteps: [
      {
        id: 'verify_video_integrity',
        title: 'Verify Video Integrity',
        description: 'Check if the video file is corrupted or damaged',
        type: 'verify_input',
        requiresUserAction: true,
        priority: 'high',
        estimatedTime: 5
      },
      {
        id: 'check_memory_usage',
        title: 'Check Memory Usage',
        description: 'Ensure sufficient system memory is available',
        type: 'check_system',
        requiresUserAction: false,
        priority: 'medium',
        estimatedTime: 1
      }
    ]
  },
  feature_extraction_error: {
    name: 'Feature Extraction Error',
    description: 'Error occurred during AI feature extraction',
    commonCauses: [
      'GPU memory insufficient',
      'Model loading failure',
      'Input data validation error',
      'Processing timeout'
    ],
    troubleshootingSteps: [
      {
        id: 'check_gpu_memory',
        title: 'Check GPU Memory',
        description: 'Verify GPU memory availability',
        type: 'check_system',
        requiresUserAction: false,
        priority: 'high',
        estimatedTime: 2
      },
      {
        id: 'restart_gpu_service',
        title: 'Restart GPU Service',
        description: 'Restart GPU processing service',
        type: 'restart_service',
        requiresUserAction: true,
        priority: 'medium',
        estimatedTime: 30
      }
    ]
  },
  inference_error: {
    name: 'AI Inference Error',
    description: 'Error occurred during AI model inference',
    commonCauses: [
      'Model loading failure',
      'GPU driver issues',
      'CUDA runtime error',
      'Memory allocation failure'
    ],
    troubleshootingSteps: [
      {
        id: 'check_gpu_drivers',
        title: 'Check GPU Drivers',
        description: 'Verify GPU drivers are up to date',
        type: 'check_system',
        requiresUserAction: false,
        priority: 'high',
        estimatedTime: 5
      },
      {
        id: 'restart_ai_service',
        title: 'Restart AI Service',
        description: 'Restart AI inference service',
        type: 'restart_service',
        requiresUserAction: true,
        priority: 'medium',
        estimatedTime: 60
      }
    ]
  },
  result_processing_error: {
    name: 'Result Processing Error',
    description: 'Error occurred while processing analysis results',
    commonCauses: [
      'Data serialization error',
      'Result validation failure',
      'Storage write error',
      'Format conversion error'
    ],
    troubleshootingSteps: [
      {
        id: 'check_storage_space',
        title: 'Check Storage Space',
        description: 'Verify sufficient storage space is available',
        type: 'check_system',
        requiresUserAction: false,
        priority: 'high',
        estimatedTime: 1
      },
      {
        id: 'clear_temp_files',
        title: 'Clear Temporary Files',
        description: 'Clear temporary processing files',
        type: 'clear_cache',
        requiresUserAction: true,
        priority: 'medium',
        estimatedTime: 5
      }
    ]
  },
  blockchain_error: {
    name: 'Blockchain Verification Error',
    description: 'Error occurred during blockchain verification',
    commonCauses: [
      'Blockchain network issues',
      'Transaction timeout',
      'Gas price too low',
      'Smart contract error'
    ],
    troubleshootingSteps: [
      {
        id: 'check_blockchain_status',
        title: 'Check Blockchain Status',
        description: 'Verify blockchain network status',
        type: 'check_system',
        requiresUserAction: false,
        priority: 'high',
        estimatedTime: 3
      },
      {
        id: 'retry_with_higher_gas',
        title: 'Retry with Higher Gas',
        description: 'Retry transaction with higher gas price',
        type: 'manual_intervention',
        requiresUserAction: true,
        priority: 'medium',
        estimatedTime: 10
      }
    ]
  },
  system_error: {
    name: 'System Error',
    description: 'General system error occurred',
    commonCauses: [
      'System resource exhaustion',
      'Service unavailability',
      'Configuration error',
      'Hardware failure'
    ],
    troubleshootingSteps: [
      {
        id: 'check_system_resources',
        title: 'Check System Resources',
        description: 'Verify system resources are available',
        type: 'check_system',
        requiresUserAction: false,
        priority: 'high',
        estimatedTime: 2
      },
      {
        id: 'restart_services',
        title: 'Restart Services',
        description: 'Restart affected services',
        type: 'restart_service',
        requiresUserAction: true,
        priority: 'medium',
        estimatedTime: 120
      }
    ]
  },
  network_error: {
    name: 'Network Error',
    description: 'Network connectivity error occurred',
    commonCauses: [
      'Internet connection lost',
      'DNS resolution failure',
      'Firewall blocking connection',
      'Server unreachable'
    ],
    troubleshootingSteps: [
      {
        id: 'check_internet_connection',
        title: 'Check Internet Connection',
        description: 'Verify internet connectivity',
        type: 'check_system',
        requiresUserAction: true,
        priority: 'high',
        estimatedTime: 2
      },
      {
        id: 'check_firewall_settings',
        title: 'Check Firewall Settings',
        description: 'Verify firewall is not blocking connections',
        type: 'check_system',
        requiresUserAction: true,
        priority: 'medium',
        estimatedTime: 5
      }
    ]
  },
  timeout_error: {
    name: 'Timeout Error',
    description: 'Operation timed out',
    commonCauses: [
      'Processing taking too long',
      'Network latency',
      'Resource contention',
      'System overload'
    ],
    troubleshootingSteps: [
      {
        id: 'increase_timeout',
        title: 'Increase Timeout',
        description: 'Increase operation timeout',
        type: 'update_configuration',
        requiresUserAction: true,
        priority: 'medium',
        estimatedTime: 5
      },
      {
        id: 'check_system_load',
        title: 'Check System Load',
        description: 'Verify system is not overloaded',
        type: 'check_system',
        requiresUserAction: false,
        priority: 'high',
        estimatedTime: 1
      }
    ]
  },
  validation_error: {
    name: 'Validation Error',
    description: 'Input validation error occurred',
    commonCauses: [
      'Invalid input format',
      'Missing required fields',
      'Value out of range',
      'Constraint violation'
    ],
    troubleshootingSteps: [
      {
        id: 'verify_input_format',
        title: 'Verify Input Format',
        description: 'Check input data format and structure',
        type: 'verify_input',
        requiresUserAction: true,
        priority: 'high',
        estimatedTime: 3
      },
      {
        id: 'check_required_fields',
        title: 'Check Required Fields',
        description: 'Ensure all required fields are provided',
        type: 'verify_input',
        requiresUserAction: true,
        priority: 'high',
        estimatedTime: 2
      }
    ]
  },
  permission_error: {
    name: 'Permission Error',
    description: 'Insufficient permissions error',
    commonCauses: [
      'User lacks required permissions',
      'Role assignment issue',
      'Resource access denied',
      'Authentication failure'
    ],
    troubleshootingSteps: [
      {
        id: 'check_user_permissions',
        title: 'Check User Permissions',
        description: 'Verify user has required permissions',
        type: 'check_system',
        requiresUserAction: false,
        priority: 'high',
        estimatedTime: 2
      },
      {
        id: 'contact_administrator',
        title: 'Contact Administrator',
        description: 'Contact system administrator for permission issues',
        type: 'contact_support',
        requiresUserAction: true,
        priority: 'medium',
        estimatedTime: 60
      }
    ]
  },
  resource_error: {
    name: 'Resource Error',
    description: 'System resource error occurred',
    commonCauses: [
      'Memory allocation failure',
      'Disk space insufficient',
      'CPU overload',
      'GPU memory exhausted'
    ],
    troubleshootingSteps: [
      {
        id: 'check_resource_usage',
        title: 'Check Resource Usage',
        description: 'Monitor system resource usage',
        type: 'check_system',
        requiresUserAction: false,
        priority: 'high',
        estimatedTime: 2
      },
      {
        id: 'free_up_resources',
        title: 'Free Up Resources',
        description: 'Free up system resources',
        type: 'clear_cache',
        requiresUserAction: true,
        priority: 'medium',
        estimatedTime: 10
      }
    ]
  },
  unknown_error: {
    name: 'Unknown Error',
    description: 'An unknown error occurred',
    commonCauses: [
      'Unexpected system behavior',
      'Unhandled exception',
      'Third-party library error',
      'Hardware malfunction'
    ],
    troubleshootingSteps: [
      {
        id: 'collect_error_logs',
        title: 'Collect Error Logs',
        description: 'Gather detailed error logs for analysis',
        type: 'check_system',
        requiresUserAction: false,
        priority: 'high',
        estimatedTime: 5
      },
      {
        id: 'contact_support',
        title: 'Contact Support',
        description: 'Contact technical support with error details',
        type: 'contact_support',
        requiresUserAction: true,
        priority: 'medium',
        estimatedTime: 30
      }
    ]
  }
};

export default ErrorInfo;
