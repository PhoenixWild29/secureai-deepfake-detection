/**
 * Processing Stage Visualization Types
 * TypeScript interfaces for analysis processing stages and resource monitoring
 */

export interface ProcessingStageInfo {
  /** Stage identifier */
  id: string;
  /** Stage display name */
  name: string;
  /** Stage description */
  description: string;
  /** Current progress percentage (0-100) */
  progress: number;
  /** Whether this stage is currently active */
  isActive: boolean;
  /** Whether this stage is completed */
  isCompleted: boolean;
  /** Whether this stage has an error */
  hasError: boolean;
  /** Whether this stage is skipped */
  isSkipped: boolean;
  /** Stage start time */
  startTime?: Date;
  /** Stage end time */
  endTime?: Date;
  /** Estimated duration for this stage */
  estimatedDuration?: number;
  /** Actual duration for this stage */
  actualDuration?: number;
  /** Error information if any */
  error?: StageError;
  /** Stage-specific metadata */
  metadata?: Record<string, any>;
}

export interface StageError {
  /** Error code */
  code: string;
  /** Error message */
  message: string;
  /** Error severity */
  severity: 'low' | 'medium' | 'high' | 'critical';
  /** Whether the error is recoverable */
  recoverable: boolean;
  /** Error timestamp */
  timestamp: Date;
  /** Suggested recovery actions */
  recoveryActions?: RecoveryAction[];
}

export interface RecoveryAction {
  /** Action identifier */
  id: string;
  /** Action description */
  description: string;
  /** Action type */
  type: 'retry' | 'skip' | 'abort' | 'manual';
  /** Whether action requires user confirmation */
  requiresConfirmation: boolean;
}

export interface WorkerInfo {
  /** Worker identifier */
  id: string;
  /** Worker name */
  name: string;
  /** Worker status */
  status: 'active' | 'idle' | 'busy' | 'offline' | 'error';
  /** Current task being processed */
  currentTask?: string;
  /** Task start time */
  taskStartTime?: Date;
  /** CPU usage percentage */
  cpuUsage: number;
  /** Memory usage in MB */
  memoryUsage: number;
  /** Worker uptime in seconds */
  uptime: number;
  /** Number of tasks completed */
  tasksCompleted: number;
  /** Worker metadata */
  metadata?: Record<string, any>;
}

export interface GPUInfo {
  /** GPU identifier */
  id: string;
  /** GPU name */
  name: string;
  /** GPU status */
  status: 'active' | 'idle' | 'busy' | 'offline' | 'error';
  /** GPU utilization percentage */
  utilization: number;
  /** Memory usage in MB */
  memoryUsed: number;
  /** Total memory in MB */
  memoryTotal: number;
  /** Memory usage percentage */
  memoryUsagePercentage: number;
  /** Temperature in Celsius */
  temperature: number;
  /** Power usage in Watts */
  powerUsage: number;
  /** Current task being processed */
  currentTask?: string;
  /** Task start time */
  taskStartTime?: Date;
  /** GPU metadata */
  metadata?: Record<string, any>;
}

export interface QueueInfo {
  /** Queue identifier */
  id: string;
  /** Queue name */
  name: string;
  /** Current position in queue */
  position: number;
  /** Total items in queue */
  totalItems: number;
  /** Estimated wait time in seconds */
  estimatedWaitTime: number;
  /** Queue priority */
  priority: 'low' | 'normal' | 'high' | 'urgent';
  /** Queue status */
  status: 'active' | 'paused' | 'stopped' | 'error';
  /** Items processed per minute */
  processingRate: number;
  /** Average processing time per item */
  averageProcessingTime: number;
  /** Queue metadata */
  metadata?: Record<string, any>;
}

export interface ResourceMetrics {
  /** System CPU usage percentage */
  systemCpuUsage: number;
  /** System memory usage in MB */
  systemMemoryUsed: number;
  /** Total system memory in MB */
  systemMemoryTotal: number;
  /** System memory usage percentage */
  systemMemoryUsagePercentage: number;
  /** Disk usage percentage */
  diskUsagePercentage: number;
  /** Network I/O in MB/s */
  networkIO: number;
  /** Timestamp of metrics collection */
  timestamp: Date;
}

export interface AnalysisStatus {
  /** Analysis identifier */
  analysisId: string;
  /** Current processing stage */
  currentStage: string;
  /** Overall progress percentage */
  overallProgress: number;
  /** Analysis start time */
  startTime: Date;
  /** Last update time */
  lastUpdate: Date;
  /** Estimated completion time */
  estimatedCompletion?: Date;
  /** Processing stages information */
  stages: ProcessingStageInfo[];
  /** Worker allocation information */
  workers: WorkerInfo[];
  /** GPU resource information */
  gpus: GPUInfo[];
  /** Queue information */
  queue: QueueInfo;
  /** System resource metrics */
  resourceMetrics: ResourceMetrics;
  /** Analysis status */
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  /** Error information if any */
  error?: StageError;
  /** Analysis metadata */
  metadata?: Record<string, any>;
}

export interface ProcessingStageVisualizationProps {
  /** Analysis ID to monitor */
  analysisId: string;
  /** Update interval in milliseconds */
  updateInterval?: number;
  /** Whether to show detailed resource information */
  showResourceDetails?: boolean;
  /** Whether to show worker allocation */
  showWorkerAllocation?: boolean;
  /** Whether to show GPU utilization */
  showGPUUtilization?: boolean;
  /** Whether to show queue status */
  showQueueStatus?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Callback when analysis status changes */
  onStatusChange?: (status: AnalysisStatus) => void;
  /** Callback when an error occurs */
  onError?: (error: Error) => void;
}

export interface StageVisualizationConfig {
  /** Stage identifier */
  id: string;
  /** Stage display name */
  name: string;
  /** Stage description */
  description: string;
  /** Stage icon */
  icon: string;
  /** Stage color theme */
  color: string;
  /** Estimated duration in milliseconds */
  estimatedDuration: number;
  /** Whether this stage can be skipped */
  skippable: boolean;
  /** Dependencies on other stages */
  dependencies: string[];
}

export const PROCESSING_STAGE_CONFIGS: Record<string, StageVisualizationConfig> = {
  upload: {
    id: 'upload',
    name: 'Upload',
    description: 'Uploading video file to server',
    icon: 'cloud-arrow-up',
    color: 'blue',
    estimatedDuration: 5000,
    skippable: false,
    dependencies: [],
  },
  frame_extraction: {
    id: 'frame_extraction',
    name: 'Frame Extraction',
    description: 'Extracting frames from video',
    icon: 'film',
    color: 'green',
    estimatedDuration: 10000,
    skippable: false,
    dependencies: ['upload'],
  },
  feature_extraction: {
    id: 'feature_extraction',
    name: 'Feature Extraction',
    description: 'Extracting AI features from frames',
    icon: 'eye',
    color: 'purple',
    estimatedDuration: 15000,
    skippable: false,
    dependencies: ['frame_extraction'],
  },
  ensemble_inference: {
    id: 'ensemble_inference',
    name: 'AI Analysis',
    description: 'Running ensemble deepfake detection',
    icon: 'cpu-chip',
    color: 'orange',
    estimatedDuration: 30000,
    skippable: false,
    dependencies: ['feature_extraction'],
  },
  result_aggregation: {
    id: 'result_aggregation',
    name: 'Result Processing',
    description: 'Aggregating analysis results',
    icon: 'chart-bar',
    color: 'indigo',
    estimatedDuration: 5000,
    skippable: false,
    dependencies: ['ensemble_inference'],
  },
  blockchain_verification: {
    id: 'blockchain_verification',
    name: 'Blockchain Verification',
    description: 'Verifying results on blockchain',
    icon: 'link',
    color: 'teal',
    estimatedDuration: 15000,
    skippable: true,
    dependencies: ['result_aggregation'],
  },
  completed: {
    id: 'completed',
    name: 'Completed',
    description: 'Analysis completed successfully',
    icon: 'check-circle',
    color: 'green',
    estimatedDuration: 0,
    skippable: false,
    dependencies: ['blockchain_verification'],
  },
  error: {
    id: 'error',
    name: 'Error',
    description: 'An error occurred during processing',
    icon: 'exclamation-triangle',
    color: 'red',
    estimatedDuration: 0,
    skippable: false,
    dependencies: [],
  },
};

export default AnalysisStatus;
