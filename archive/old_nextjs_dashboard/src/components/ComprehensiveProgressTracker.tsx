import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';
import { 
  ProgressState, 
  StatusUpdate, 
  ResultUpdate, 
  ProcessingStage,
  STAGE_CONFIGS,
  ConnectionStatus 
} from '@/types/progress';
import { WebSocketService, createWebSocketService, defaultWebSocketConfig } from '@/utils/websocketService';
import { createDebouncedProgressUpdater, ProgressCalculator } from '@/utils/progressCalculations';
import { StageIndicator, StageIndicatorGroup } from './StageIndicator';
import FrameProgressDisplay from './FrameProgressDisplay';
import styles from './ComprehensiveProgressTracker.module.css';

export interface ComprehensiveProgressTrackerProps {
  /** Session ID for tracking progress */
  sessionId?: string;
  /** WebSocket configuration */
  websocketConfig?: {
    url?: string;
    reconnectInterval?: number;
    maxReconnectAttempts?: number;
    connectionTimeout?: number;
    heartbeatInterval?: number;
  };
  /** Progress update debounce delay */
  debounceDelay?: number;
  /** Whether to show frame-level progress */
  showFrameProgress?: boolean;
  /** Whether to show detailed statistics */
  showStatistics?: boolean;
  /** Whether to show timeline information */
  showTimeline?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Callback when analysis is completed */
  onComplete?: (result: ResultUpdate) => void;
  /** Callback when an error occurs */
  onError?: (error: Error) => void;
  /** Callback when connection status changes */
  onConnectionChange?: (status: ConnectionStatus) => void;
}

/**
 * ComprehensiveProgressTracker component
 * Main component for displaying real-time analysis progress with WebSocket integration
 */
export const ComprehensiveProgressTracker: React.FC<ComprehensiveProgressTrackerProps> = ({
  sessionId,
  websocketConfig = {},
  debounceDelay = 300,
  showFrameProgress = true,
  showStatistics = true,
  showTimeline = true,
  className = '',
  onComplete,
  onError,
  onConnectionChange,
}) => {
  // State management
  const [progressState, setProgressState] = useState<ProgressState>({
    sessionId: sessionId || null,
    currentStage: 'upload',
    overallProgress: 0,
    stageProgress: 0,
    startTime: null,
    lastUpdate: null,
    estimatedCompletion: null,
    frameProgress: [],
    error: null,
    isActive: false,
    statistics: null,
    result: null,
  });

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    status: 'disconnected',
    reconnectAttempts: 0,
  });

  const [isInitialized, setIsInitialized] = useState(false);

  // Refs
  const wsServiceRef = useRef<WebSocketService | null>(null);
  const progressUpdaterRef = useRef<ReturnType<typeof createDebouncedProgressUpdater> | null>(null);
  const calculatorRef = useRef<ProgressCalculator | null>(null);

  // Initialize WebSocket service and progress calculator
  useEffect(() => {
    const config = {
      ...defaultWebSocketConfig,
      ...websocketConfig,
    };

    wsServiceRef.current = createWebSocketService(config);
    calculatorRef.current = new ProgressCalculator();

    // Set up progress updater with debouncing
    progressUpdaterRef.current = createDebouncedProgressUpdater(
      debounceDelay,
      (newState) => {
        setProgressState(newState);
      }
    );

    setIsInitialized(true);

    return () => {
      if (wsServiceRef.current) {
        wsServiceRef.current.disconnect();
      }
      if (progressUpdaterRef.current) {
        progressUpdaterRef.current.cancel();
      }
    };
  }, [websocketConfig, debounceDelay]);

  // Set up WebSocket event handlers
  useEffect(() => {
    if (!wsServiceRef.current || !isInitialized) return;

    const wsService = wsServiceRef.current;

    // Status update handler
    const unsubscribeStatus = wsService.onStatusUpdate((update: StatusUpdate) => {
      if (progressUpdaterRef.current) {
        progressUpdaterRef.current.update(progressState, update);
      }
    });

    // Result update handler
    const unsubscribeResult = wsService.onResultUpdate((result: ResultUpdate) => {
      setProgressState(prev => ({
        ...prev,
        result: result.result,
        currentStage: 'completed',
        overallProgress: 100,
        stageProgress: 100,
        isActive: false,
        lastUpdate: new Date(),
      }));

      if (onComplete) {
        onComplete(result);
      }
    });

    // Error handler
    const unsubscribeError = wsService.onError((error: Error) => {
      setProgressState(prev => ({
        ...prev,
        error: {
          code: 'WEBSOCKET_ERROR',
          message: error.message,
          severity: 'high',
          recoverable: true,
        },
        isActive: false,
      }));

      if (onError) {
        onError(error);
      }
    });

    // Connection status handler
    const unsubscribeConnection = wsService.onConnectionStatus((status: ConnectionStatus) => {
      setConnectionStatus(status);
      if (onConnectionChange) {
        onConnectionChange(status);
      }
    });

    return () => {
      unsubscribeStatus();
      unsubscribeResult();
      unsubscribeError();
      unsubscribeConnection();
    };
  }, [isInitialized, progressState, onComplete, onError, onConnectionChange]);

  // Connect to WebSocket when sessionId is provided
  useEffect(() => {
    if (sessionId && wsServiceRef.current && isInitialized) {
      wsServiceRef.current.connect();
    }
  }, [sessionId, isInitialized]);

  // Handle manual reconnection
  const handleReconnect = useCallback(() => {
    if (wsServiceRef.current) {
      wsServiceRef.current.connect();
    }
  }, []);

  // Handle stage click
  const handleStageClick = useCallback((stage: ProcessingStage) => {
    console.log('Stage clicked:', stage);
    // Could implement stage-specific actions here
  }, []);

  // Handle frame click
  const handleFrameClick = useCallback((frameIndex: number) => {
    console.log('Frame clicked:', frameIndex);
    // Could implement frame-specific actions here
  }, []);

  // Get connection status display
  const getConnectionStatusDisplay = () => {
    const statusClasses = {
      connected: styles.connectionStatusConnected,
      disconnected: styles.connectionStatusDisconnected,
      connecting: styles.connectionStatusConnecting,
      error: styles.connectionStatusError,
    };

    const dotClasses = {
      connected: styles.connectionDotConnected,
      disconnected: styles.connectionDotDisconnected,
      connecting: styles.connectionDotConnecting,
      error: styles.connectionDotError,
    };

    return (
      <div className={`${styles.connectionStatus} ${statusClasses[connectionStatus.status]}`}>
        <div className={`${styles.connectionDot} ${dotClasses[connectionStatus.status]}`} />
        <span className="capitalize">{connectionStatus.status}</span>
        {connectionStatus.error && (
          <span className="ml-2 text-xs">({connectionStatus.error})</span>
        )}
        {connectionStatus.status === 'disconnected' && (
          <button
            onClick={handleReconnect}
            className="ml-2 p-1 rounded hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-white/50"
            aria-label="Reconnect"
          >
            <ArrowPathIcon className="w-4 h-4" />
          </button>
        )}
      </div>
    );
  };

  // Get timeline display
  const getTimelineDisplay = () => {
    if (!showTimeline || !progressState.startTime) return null;

    const now = new Date();
    const elapsed = now.getTime() - progressState.startTime.getTime();
    const remaining = progressState.estimatedCompletion 
      ? progressState.estimatedCompletion.getTime() - now.getTime()
      : 0;

    const formatTime = (ms: number) => {
      const seconds = Math.floor(ms / 1000);
      const minutes = Math.floor(seconds / 60);
      const hours = Math.floor(minutes / 60);

      if (hours > 0) {
        return `${hours}h ${minutes % 60}m`;
      } else if (minutes > 0) {
        return `${minutes}m ${seconds % 60}s`;
      } else {
        return `${seconds}s`;
      }
    };

    return (
      <div className={styles.timelineDisplay}>
        <div className={styles.timelineHeader}>
          <h3 className={styles.timelineTitle}>Processing Timeline</h3>
        </div>
        
        <div className={styles.timelineStats}>
          <div className={styles.timelineStat}>
            <div className={styles.timelineStatValue}>
              {formatTime(elapsed)}
            </div>
            <div className={styles.timelineStatLabel}>
              Elapsed Time
            </div>
          </div>
          
          <div className={styles.timelineStat}>
            <div className={styles.timelineStatValue}>
              {remaining > 0 ? formatTime(remaining) : '--'}
            </div>
            <div className={styles.timelineStatLabel}>
              Estimated Remaining
            </div>
          </div>
          
          <div className={styles.timelineStat}>
            <div className={styles.timelineStatValue}>
              {progressState.estimatedCompletion?.toLocaleTimeString() || '--'}
            </div>
            <div className={styles.timelineStatLabel}>
              Estimated Completion
            </div>
          </div>
          
          <div className={styles.timelineStat}>
            <div className={styles.timelineStatValue}>
              {progressState.frameProgress.length}
            </div>
            <div className={styles.timelineStatLabel}>
              Total Frames
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Get stage data for display
  const getStageData = () => {
    const stages: ProcessingStage[] = [
      'upload',
      'frame_extraction',
      'feature_extraction',
      'ensemble_inference',
      'result_aggregation',
      'blockchain_verification',
      'completed',
    ];

    return stages.map(stage => {
      const isActive = stage === progressState.currentStage && progressState.isActive;
      const isCompleted = progressState.currentStage === 'completed' || 
        (progressState.currentStage !== stage && stages.indexOf(progressState.currentStage) > stages.indexOf(stage));
      const hasError = progressState.error && stage === progressState.currentStage;
      const isSkipped = false; // Could implement skip logic here

      let progress = 0;
      if (isActive) {
        progress = progressState.stageProgress;
      } else if (isCompleted) {
        progress = 100;
      }

      return {
        stage,
        progress,
        isActive,
        isCompleted,
        hasError,
        isSkipped,
        estimatedDuration: STAGE_CONFIGS[stage]?.estimatedDuration,
        actualDuration: undefined, // Could implement actual duration tracking
      };
    });
  };

  // Render error state
  if (progressState.error && progressState.error.severity === 'critical') {
    return (
      <div className={`${styles.progressTracker} ${className}`}>
        <div className={styles.errorState}>
          <ExclamationTriangleIcon className={styles.errorIcon} />
          <h3 className={styles.errorTitle}>Critical Error</h3>
          <p className={styles.errorMessage}>
            {progressState.error.message}
          </p>
          <div className={styles.errorActions}>
            <button
              className={`${styles.errorButton} ${styles.errorButtonPrimary}`}
              onClick={handleReconnect}
            >
              Retry Connection
            </button>
            <button
              className={`${styles.errorButton} ${styles.errorButtonSecondary}`}
              onClick={() => window.location.reload()}
            >
              Refresh Page
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Render loading state
  if (!isInitialized) {
    return (
      <div className={`${styles.progressTracker} ${className}`}>
        <div className={styles.loadingState}>
          <div className={styles.loadingSpinner} />
          <p className={styles.loadingText}>Initializing progress tracker...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.progressTracker} ${className}`}>
      {/* Header */}
      <div className={styles.progressTrackerHeader}>
        <div>
          <h2 className={styles.progressTrackerTitle}>
            Analysis Progress
          </h2>
          <p className={styles.progressTrackerSubtitle}>
            Real-time deepfake detection analysis
          </p>
        </div>
        {getConnectionStatusDisplay()}
      </div>

      {/* Overall Progress */}
      <div className={styles.overallProgress}>
        <div className={styles.overallProgressHeader}>
          <h3 className={styles.overallProgressTitle}>
            Overall Progress
          </h3>
          <span className={styles.overallProgressPercentage}>
            {Math.round(progressState.overallProgress)}%
          </span>
        </div>
        <div className={styles.overallProgressBar}>
          <div 
            className={styles.overallProgressFill}
            style={{ width: `${progressState.overallProgress}%` }}
            aria-valuenow={progressState.overallProgress}
            aria-valuemin={0}
            aria-valuemax={100}
            role="progressbar"
            aria-label={`Overall progress: ${Math.round(progressState.overallProgress)}%`}
          />
        </div>
      </div>

      {/* Timeline Display */}
      {getTimelineDisplay()}

      {/* Stage Indicators */}
      <StageIndicatorGroup
        stages={getStageData()}
        showDetails={showStatistics}
        onStageClick={handleStageClick}
      />

      {/* Frame Progress Display */}
      {showFrameProgress && progressState.frameProgress.length > 0 && (
        <FrameProgressDisplay
          frameProgress={progressState.frameProgress}
          showDetails={showStatistics}
          onFrameClick={handleFrameClick}
        />
      )}

      {/* Error Display */}
      {progressState.error && progressState.error.severity !== 'critical' && (
        <div className={styles.errorState}>
          <ExclamationTriangleIcon className={styles.errorIcon} />
          <h3 className={styles.errorTitle}>Processing Error</h3>
          <p className={styles.errorMessage}>
            {progressState.error.message}
          </p>
          {progressState.error.recoveryActions && progressState.error.recoveryActions.length > 0 && (
            <div className={styles.errorActions}>
              {progressState.error.recoveryActions.map((action, index) => (
                <button
                  key={index}
                  className={`${styles.errorButton} ${styles.errorButtonSecondary}`}
                  onClick={() => {
                    // Implement recovery action
                    console.log('Recovery action:', action);
                  }}
                >
                  {action.description}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Completion State */}
      {progressState.currentStage === 'completed' && progressState.result && (
        <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
          <div className="flex items-center gap-3">
            <CheckCircleIcon className="w-8 h-8 text-green-600 dark:text-green-400" />
            <div>
              <h3 className="text-lg font-semibold text-green-800 dark:text-green-200">
                Analysis Complete
              </h3>
              <p className="text-green-700 dark:text-green-300">
                Deepfake detection analysis has been completed successfully.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ComprehensiveProgressTracker;
