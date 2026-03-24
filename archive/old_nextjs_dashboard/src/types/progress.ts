/**
 * Progress Tracking Types
 * TypeScript interfaces for StatusUpdate and ResultUpdate event schemas
 */

export interface StatusUpdate {
  /** Unique identifier for the analysis session */
  sessionId: string;
  /** Current processing stage */
  stage: ProcessingStage;
  /** Overall progress percentage (0-100) */
  progress: number;
  /** Current stage progress percentage (0-100) */
  stageProgress: number;
  /** Timestamp of the status update */
  timestamp: string;
  /** Additional metadata for the current stage */
  metadata?: Record<string, any>;
  /** Error information if any */
  error?: ErrorInfo;
}

export interface ResultUpdate {
  /** Unique identifier for the analysis session */
  sessionId: string;
  /** Analysis result data */
  result: AnalysisResult;
  /** Processing completion timestamp */
  completedAt: string;
  /** Total processing time in milliseconds */
  processingTime: number;
  /** Frame-level results */
  frameResults?: FrameResult[];
  /** Blockchain verification status */
  blockchainStatus?: BlockchainStatus;
}

export interface ErrorInfo {
  /** Error code */
  code: string;
  /** Error message */
  message: string;
  /** Error severity level */
  severity: 'low' | 'medium' | 'high' | 'critical';
  /** Whether the error is recoverable */
  recoverable: boolean;
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

export interface AnalysisResult {
  /** Overall confidence score (0-1) */
  confidence: number;
  /** Detection result */
  isDeepfake: boolean;
  /** Detailed analysis data */
  analysis: {
    /** Frame analysis results */
    frames: FrameAnalysis[];
    /** Ensemble model scores */
    ensembleScores: ModelScore[];
    /** Processing statistics */
    statistics: ProcessingStats;
  };
  /** Blockchain hash for verification */
  blockchainHash?: string;
}

export interface FrameResult {
  /** Frame index */
  frameIndex: number;
  /** Frame processing status */
  status: 'pending' | 'processing' | 'completed' | 'error';
  /** Frame analysis result */
  result?: FrameAnalysis;
  /** Processing time for this frame */
  processingTime?: number;
  /** Error information if any */
  error?: ErrorInfo;
}

export interface FrameAnalysis {
  /** Frame index */
  frameIndex: number;
  /** Frame timestamp in video */
  timestamp: number;
  /** Individual model scores */
  modelScores: ModelScore[];
  /** Overall frame confidence */
  confidence: number;
  /** Frame-level detection result */
  isDeepfake: boolean;
  /** Processing metadata */
  metadata: {
    /** Frame dimensions */
    dimensions: { width: number; height: number };
    /** Frame quality metrics */
    quality: QualityMetrics;
    /** Feature extraction time */
    extractionTime: number;
  };
}

export interface ModelScore {
  /** Model identifier */
  modelId: string;
  /** Model name */
  modelName: string;
  /** Confidence score (0-1) */
  score: number;
  /** Model-specific metadata */
  metadata?: Record<string, any>;
}

export interface QualityMetrics {
  /** Image sharpness score */
  sharpness: number;
  /** Image brightness score */
  brightness: number;
  /** Image contrast score */
  contrast: number;
  /** Compression artifacts score */
  compressionArtifacts: number;
}

export interface ProcessingStats {
  /** Total frames processed */
  totalFrames: number;
  /** Frames processed successfully */
  successfulFrames: number;
  /** Frames with errors */
  errorFrames: number;
  /** Average processing time per frame */
  averageFrameTime: number;
  /** Total processing time */
  totalProcessingTime: number;
  /** Memory usage statistics */
  memoryUsage: {
    peak: number;
    average: number;
    current: number;
  };
}

export interface BlockchainStatus {
  /** Transaction hash */
  transactionHash: string;
  /** Block number */
  blockNumber: number;
  /** Verification status */
  verified: boolean;
  /** Verification timestamp */
  verifiedAt: string;
  /** Gas used for transaction */
  gasUsed: number;
}

export type ProcessingStage = 
  | 'upload'
  | 'frame_extraction'
  | 'feature_extraction'
  | 'ensemble_inference'
  | 'result_aggregation'
  | 'blockchain_verification'
  | 'completed'
  | 'error';

export interface ProgressState {
  /** Current session ID */
  sessionId: string | null;
  /** Current processing stage */
  currentStage: ProcessingStage;
  /** Overall progress percentage */
  overallProgress: number;
  /** Current stage progress percentage */
  stageProgress: number;
  /** Processing start time */
  startTime: Date | null;
  /** Last update time */
  lastUpdate: Date | null;
  /** Estimated completion time */
  estimatedCompletion: Date | null;
  /** Frame-level progress data */
  frameProgress: FrameProgressData[];
  /** Error information */
  error: ErrorInfo | null;
  /** Whether processing is active */
  isActive: boolean;
  /** Processing statistics */
  statistics: ProcessingStats | null;
  /** Analysis result */
  result: AnalysisResult | null;
}

export interface FrameProgressData {
  /** Frame index */
  frameIndex: number;
  /** Processing status */
  status: 'pending' | 'processing' | 'completed' | 'error';
  /** Progress percentage for this frame */
  progress: number;
  /** Processing start time */
  startTime?: Date;
  /** Processing end time */
  endTime?: Date;
  /** Error information if any */
  error?: ErrorInfo;
}

export interface WebSocketMessage {
  /** Message type */
  type: 'status_update' | 'result_update' | 'error' | 'connection_status';
  /** Message payload */
  payload: StatusUpdate | ResultUpdate | ErrorInfo | ConnectionStatus;
  /** Message timestamp */
  timestamp: string;
}

export interface ConnectionStatus {
  /** Connection status */
  status: 'connected' | 'disconnected' | 'connecting' | 'error';
  /** Connection error if any */
  error?: string;
  /** Reconnection attempt count */
  reconnectAttempts: number;
  /** Next reconnection attempt time */
  nextReconnectAt?: string;
}

export interface ProgressTrackerConfig {
  /** WebSocket server URL */
  websocketUrl: string;
  /** Reconnection interval in milliseconds */
  reconnectInterval: number;
  /** Maximum reconnection attempts */
  maxReconnectAttempts: number;
  /** Update debounce delay in milliseconds */
  debounceDelay: number;
  /** Whether to show frame-level progress */
  showFrameProgress: boolean;
  /** Whether to show detailed statistics */
  showStatistics: boolean;
  /** Animation duration in milliseconds */
  animationDuration: number;
}

export interface StageConfig {
  /** Stage identifier */
  id: ProcessingStage;
  /** Stage display name */
  name: string;
  /** Stage description */
  description: string;
  /** Stage icon */
  icon: string;
  /** Estimated duration in milliseconds */
  estimatedDuration: number;
  /** Whether this stage can be skipped */
  skippable: boolean;
  /** Dependencies on other stages */
  dependencies: ProcessingStage[];
}

export const STAGE_CONFIGS: Record<ProcessingStage, StageConfig> = {
  upload: {
    id: 'upload',
    name: 'Upload',
    description: 'Uploading video file to server',
    icon: 'cloud-arrow-up',
    estimatedDuration: 5000,
    skippable: false,
    dependencies: [],
  },
  frame_extraction: {
    id: 'frame_extraction',
    name: 'Frame Extraction',
    description: 'Extracting frames from video',
    icon: 'film',
    estimatedDuration: 10000,
    skippable: false,
    dependencies: ['upload'],
  },
  feature_extraction: {
    id: 'feature_extraction',
    name: 'Feature Extraction',
    description: 'Extracting features from frames',
    icon: 'eye',
    estimatedDuration: 15000,
    skippable: false,
    dependencies: ['frame_extraction'],
  },
  ensemble_inference: {
    id: 'ensemble_inference',
    name: 'AI Analysis',
    description: 'Running ensemble deepfake detection',
    icon: 'cpu-chip',
    estimatedDuration: 30000,
    skippable: false,
    dependencies: ['feature_extraction'],
  },
  result_aggregation: {
    id: 'result_aggregation',
    name: 'Result Processing',
    description: 'Aggregating analysis results',
    icon: 'chart-bar',
    estimatedDuration: 5000,
    skippable: false,
    dependencies: ['ensemble_inference'],
  },
  blockchain_verification: {
    id: 'blockchain_verification',
    name: 'Blockchain Verification',
    description: 'Verifying results on blockchain',
    icon: 'link',
    estimatedDuration: 15000,
    skippable: true,
    dependencies: ['result_aggregation'],
  },
  completed: {
    id: 'completed',
    name: 'Completed',
    description: 'Analysis completed successfully',
    icon: 'check-circle',
    estimatedDuration: 0,
    skippable: false,
    dependencies: ['blockchain_verification'],
  },
  error: {
    id: 'error',
    name: 'Error',
    description: 'An error occurred during processing',
    icon: 'exclamation-triangle',
    estimatedDuration: 0,
    skippable: false,
    dependencies: [],
  },
};

export default ProgressState;
