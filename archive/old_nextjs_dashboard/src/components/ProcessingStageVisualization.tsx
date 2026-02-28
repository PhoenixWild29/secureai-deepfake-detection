import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  CpuChipIcon,
  ServerIcon,
  ChartBarIcon,
  QueueListIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';
import { 
  AnalysisStatus, 
  ProcessingStageInfo, 
  WorkerInfo, 
  GPUInfo, 
  QueueInfo,
  ResourceMetrics,
  PROCESSING_STAGE_CONFIGS 
} from '@/types/processingStage';
import { analysisService } from '@/services/analysisService';
import styles from './ProcessingStageVisualization.module.css';

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

/**
 * ProcessingStageVisualization component
 * Displays detailed analysis processing stages and system resource utilization
 */
export const ProcessingStageVisualization: React.FC<ProcessingStageVisualizationProps> = ({
  analysisId,
  updateInterval = 2000,
  showResourceDetails = true,
  showWorkerAllocation = true,
  showGPUUtilization = true,
  showQueueStatus = true,
  className = '',
  onStatusChange,
  onError,
}) => {
  // State management
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  // Refs
  const stopPollingRef = useRef<(() => void) | null>(null);
  const isMountedRef = useRef(true);

  // Initialize polling
  useEffect(() => {
    if (!analysisId) return;

    setIsLoading(true);
    setError(null);

    // Start polling for analysis status
    stopPollingRef.current = analysisService.startPolling(
      analysisId,
      (status) => {
        if (isMountedRef.current) {
          setAnalysisStatus(status);
          setLastUpdate(new Date());
          setIsLoading(false);
          
          if (onStatusChange) {
            onStatusChange(status);
          }
        }
      },
      {
        interval: updateInterval,
        autoStart: true,
        stopOnError: false,
      }
    );

    return () => {
      if (stopPollingRef.current) {
        stopPollingRef.current();
      }
    };
  }, [analysisId, updateInterval, onStatusChange]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      if (stopPollingRef.current) {
        stopPollingRef.current();
      }
    };
  }, []);

  // Handle errors
  const handleError = useCallback((error: Error) => {
    setError(error);
    setIsLoading(false);
    
    if (onError) {
      onError(error);
    }
  }, [onError]);

  // Retry function
  const handleRetry = useCallback(() => {
    setError(null);
    setIsLoading(true);
    
    // Restart polling
    if (stopPollingRef.current) {
      stopPollingRef.current();
    }
    
    stopPollingRef.current = analysisService.startPolling(
      analysisId,
      (status) => {
        if (isMountedRef.current) {
          setAnalysisStatus(status);
          setLastUpdate(new Date());
          setIsLoading(false);
          
          if (onStatusChange) {
            onStatusChange(status);
          }
        }
      },
      {
        interval: updateInterval,
        autoStart: true,
        stopOnError: false,
      }
    );
  }, [analysisId, updateInterval, onStatusChange]);

  // Get status indicator display
  const getStatusIndicator = () => {
    if (!analysisStatus) return null;

    const statusClasses = {
      processing: styles.statusIndicatorProcessing,
      completed: styles.statusIndicatorCompleted,
      failed: styles.statusIndicatorFailed,
      pending: styles.statusIndicatorPending,
      cancelled: styles.statusIndicatorCancelled,
    };

    const dotClasses = {
      processing: styles.statusDotProcessing,
      completed: styles.statusDotCompleted,
      failed: styles.statusDotFailed,
      pending: styles.statusDotPending,
      cancelled: styles.statusDotCancelled,
    };

    return (
      <div className={`${styles.statusIndicator} ${statusClasses[analysisStatus.status]}`}>
        <div className={`${styles.statusDot} ${dotClasses[analysisStatus.status]}`} />
        <span className="capitalize">{analysisStatus.status}</span>
      </div>
    );
  };

  // Get stage icon
  const getStageIcon = (stageId: string) => {
    const config = PROCESSING_STAGE_CONFIGS[stageId];
    if (!config) return '?';

    // Return first letter of stage name as icon
    return config.name.charAt(0).toUpperCase();
  };

  // Get stage color class
  const getStageColorClass = (stageId: string) => {
    const config = PROCESSING_STAGE_CONFIGS[stageId];
    if (!config) return styles.stageIconGray;

    const colorClasses = {
      blue: styles.stageIconBlue,
      green: styles.stageIconGreen,
      purple: styles.stageIconPurple,
      orange: styles.stageIconOrange,
      indigo: styles.stageIconIndigo,
      teal: styles.stageIconTeal,
      red: styles.stageIconRed,
      gray: styles.stageIconGray,
    };

    return colorClasses[config.color as keyof typeof colorClasses] || styles.stageIconGray;
  };

  // Get stage progress fill class
  const getStageProgressFillClass = (stageId: string) => {
    const config = PROCESSING_STAGE_CONFIGS[stageId];
    if (!config) return styles.stageProgressFillGray;

    const fillClasses = {
      blue: styles.stageProgressFillBlue,
      green: styles.stageProgressFillGreen,
      purple: styles.stageProgressFillPurple,
      orange: styles.stageProgressFillOrange,
      indigo: styles.stageProgressFillIndigo,
      teal: styles.stageProgressFillTeal,
      red: styles.stageProgressFillRed,
    };

    return fillClasses[config.color as keyof typeof fillClasses] || styles.stageProgressFillBlue;
  };

  // Get stage card class
  const getStageCardClass = (stage: ProcessingStageInfo) => {
    if (stage.hasError) return styles.stageCardError;
    if (stage.isCompleted) return styles.stageCardCompleted;
    if (stage.isActive) return styles.stageCardActive;
    if (stage.isSkipped) return styles.stageCardSkipped;
    return styles.stageCardPending;
  };

  // Get stage status dot class
  const getStageStatusDotClass = (stage: ProcessingStageInfo) => {
    if (stage.hasError) return styles.stageStatusDotError;
    if (stage.isCompleted) return styles.stageStatusDotCompleted;
    if (stage.isActive) return styles.stageStatusDotActive;
    if (stage.isSkipped) return styles.stageStatusDotSkipped;
    return styles.stageStatusDotPending;
  };

  // Get worker card class
  const getWorkerCardClass = (worker: WorkerInfo) => {
    const cardClasses = {
      active: styles.workerCardActive,
      idle: styles.workerCardIdle,
      busy: styles.workerCardBusy,
      offline: styles.workerCardOffline,
      error: styles.workerCardError,
    };
    return cardClasses[worker.status] || styles.workerCardOffline;
  };

  // Get worker icon class
  const getWorkerIconClass = (worker: WorkerInfo) => {
    const iconClasses = {
      active: styles.workerIconActive,
      idle: styles.workerIconIdle,
      busy: styles.workerIconBusy,
      offline: styles.workerIconOffline,
      error: styles.workerIconError,
    };
    return iconClasses[worker.status] || styles.workerIconOffline;
  };

  // Get GPU card class
  const getGPUCardClass = (gpu: GPUInfo) => {
    const cardClasses = {
      active: styles.gpuCardActive,
      idle: styles.gpuCardIdle,
      busy: styles.gpuCardBusy,
      offline: styles.gpuCardOffline,
      error: styles.gpuCardError,
    };
    return cardClasses[gpu.status] || styles.gpuCardOffline;
  };

  // Get GPU icon class
  const getGPUIconClass = (gpu: GPUInfo) => {
    const iconClasses = {
      active: styles.gpuIconActive,
      idle: styles.gpuIconIdle,
      busy: styles.gpuIconBusy,
      offline: styles.gpuIconOffline,
      error: styles.gpuIconError,
    };
    return iconClasses[gpu.status] || styles.gpuIconOffline;
  };

  // Get queue card class
  const getQueueCardClass = (queue: QueueInfo) => {
    const cardClasses = {
      active: styles.queueCardActive,
      paused: styles.queueCardPaused,
      stopped: styles.queueCardStopped,
      error: styles.queueCardError,
    };
    return cardClasses[queue.status] || styles.queueCardActive;
  };

  // Format duration
  const formatDuration = (ms: number) => {
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

  // Format memory
  const formatMemory = (bytes: number) => {
    const mb = bytes / (1024 * 1024);
    if (mb > 1024) {
      return `${(mb / 1024).toFixed(1)} GB`;
    }
    return `${mb.toFixed(1)} MB`;
  };

  // Render loading state
  if (isLoading) {
    return (
      <div className={`${styles.processingStageViz} ${className}`}>
        <div className={styles.loadingState}>
          <div className={styles.loadingSpinner} />
          <p className={styles.loadingText}>Loading analysis status...</p>
        </div>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className={`${styles.processingStageViz} ${className}`}>
        <div className={styles.errorState}>
          <ExclamationTriangleIcon className={styles.errorIcon} />
          <h3 className={styles.errorTitle}>Error Loading Analysis Status</h3>
          <p className={styles.errorMessage}>
            {error.message}
          </p>
          <div className={styles.errorActions}>
            <button
              className={`${styles.errorButton} ${styles.errorButtonPrimary}`}
              onClick={handleRetry}
            >
              <ArrowPathIcon className="w-4 h-4 mr-2" />
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Render main component
  return (
    <div className={`${styles.processingStageViz} ${className}`}>
      {/* Header */}
      <div className={styles.processingStageVizHeader}>
        <div>
          <h2 className={styles.processingStageVizTitle}>
            Processing Stage Visualization
          </h2>
          <p className={styles.processingStageVizSubtitle}>
            Analysis ID: {analysisId}
          </p>
        </div>
        {getStatusIndicator()}
      </div>

      {/* Overall Progress */}
      <div className={styles.overallProgress}>
        <div className={styles.overallProgressHeader}>
          <h3 className={styles.overallProgressTitle}>
            Overall Progress
          </h3>
          <span className={styles.overallProgressPercentage}>
            {analysisStatus ? Math.round(analysisStatus.overallProgress) : 0}%
          </span>
        </div>
        <div className={styles.overallProgressBar}>
          <div 
            className={styles.overallProgressFill}
            style={{ width: `${analysisStatus?.overallProgress || 0}%` }}
            aria-valuenow={analysisStatus?.overallProgress || 0}
            aria-valuemin={0}
            aria-valuemax={100}
            role="progressbar"
            aria-label={`Overall progress: ${Math.round(analysisStatus?.overallProgress || 0)}%`}
          />
        </div>
      </div>

      {/* Processing Stages */}
      {analysisStatus && (
        <div className={styles.processingStages}>
          <div className={styles.stagesHeader}>
            <h3 className={styles.stagesTitle}>Processing Stages</h3>
          </div>
          
          <div className={styles.stagesGrid}>
            {analysisStatus.stages.map((stage) => (
              <div key={stage.id} className={`${styles.stageCard} ${getStageCardClass(stage)}`}>
                <div className={styles.stageHeader}>
                  <div className={`${styles.stageIcon} ${getStageColorClass(stage.id)}`}>
                    {getStageIcon(stage.id)}
                  </div>
                  <div className={styles.stageInfo}>
                    <div className={styles.stageName}>{stage.name}</div>
                    <div className={styles.stageProgress}>{Math.round(stage.progress)}%</div>
                  </div>
                </div>
                
                <div className={styles.stageProgressBar}>
                  <div 
                    className={`${styles.stageProgressFill} ${getStageProgressFillClass(stage.id)}`}
                    style={{ width: `${stage.progress}%` }}
                  />
                </div>
                
                <div className={styles.stageDescription}>
                  {stage.description}
                </div>
                
                <div className={styles.stageStatus}>
                  <div className={`${styles.stageStatusDot} ${getStageStatusDotClass(stage)}`} />
                  <span className={styles.stageStatusText}>
                    {stage.hasError ? 'Error' : 
                     stage.isCompleted ? 'Completed' : 
                     stage.isActive ? 'Active' : 
                     stage.isSkipped ? 'Skipped' : 'Pending'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Resource Monitoring */}
      {showResourceDetails && analysisStatus && (
        <div className={styles.resourceMonitoring}>
          <div className={styles.resourceHeader}>
            <h3 className={styles.resourceTitle}>System Resources</h3>
          </div>
          
          <div className={styles.resourceGrid}>
            <div className={styles.resourceCard}>
              <div className={styles.resourceCardHeader}>
                <CpuChipIcon className={styles.resourceCardIcon} />
                <span className={styles.resourceCardTitle}>CPU Usage</span>
              </div>
              <div className={styles.resourceCardValue}>
                {Math.round(analysisStatus.resourceMetrics.systemCpuUsage)}%
              </div>
              <div className={styles.resourceCardLabel}>System CPU</div>
              <div className={styles.resourceCardProgress}>
                <div 
                  className={`${styles.resourceCardProgressFill} ${styles.resourceCardProgressFillBlue}`}
                  style={{ width: `${analysisStatus.resourceMetrics.systemCpuUsage}%` }}
                />
              </div>
            </div>
            
            <div className={styles.resourceCard}>
              <div className={styles.resourceCardHeader}>
                <ServerIcon className={styles.resourceCardIcon} />
                <span className={styles.resourceCardTitle}>Memory Usage</span>
              </div>
              <div className={styles.resourceCardValue}>
                {Math.round(analysisStatus.resourceMetrics.systemMemoryUsagePercentage)}%
              </div>
              <div className={styles.resourceCardLabel}>
                {formatMemory(analysisStatus.resourceMetrics.systemMemoryUsed)} / {formatMemory(analysisStatus.resourceMetrics.systemMemoryTotal)}
              </div>
              <div className={styles.resourceCardProgress}>
                <div 
                  className={`${styles.resourceCardProgressFill} ${styles.resourceCardProgressFillGreen}`}
                  style={{ width: `${analysisStatus.resourceMetrics.systemMemoryUsagePercentage}%` }}
                />
              </div>
            </div>
            
            <div className={styles.resourceCard}>
              <div className={styles.resourceCardHeader}>
                <ChartBarIcon className={styles.resourceCardIcon} />
                <span className={styles.resourceCardTitle}>Disk Usage</span>
              </div>
              <div className={styles.resourceCardValue}>
                {Math.round(analysisStatus.resourceMetrics.diskUsagePercentage)}%
              </div>
              <div className={styles.resourceCardLabel}>Storage</div>
              <div className={styles.resourceCardProgress}>
                <div 
                  className={`${styles.resourceCardProgressFill} ${styles.resourceCardProgressFillOrange}`}
                  style={{ width: `${analysisStatus.resourceMetrics.diskUsagePercentage}%` }}
                />
              </div>
            </div>
            
            <div className={styles.resourceCard}>
              <div className={styles.resourceCardHeader}>
                <QueueListIcon className={styles.resourceCardIcon} />
                <span className={styles.resourceCardTitle}>Network I/O</span>
              </div>
              <div className={styles.resourceCardValue}>
                {analysisStatus.resourceMetrics.networkIO.toFixed(1)}
              </div>
              <div className={styles.resourceCardLabel}>MB/s</div>
            </div>
          </div>
        </div>
      )}

      {/* Worker Allocation */}
      {showWorkerAllocation && analysisStatus && analysisStatus.workers.length > 0 && (
        <div className={styles.workerAllocation}>
          <div className={styles.workerHeader}>
            <h3 className={styles.workerTitle}>Worker Allocation</h3>
          </div>
          
          <div className={styles.workerGrid}>
            {analysisStatus.workers.map((worker) => (
              <div key={worker.id} className={`${styles.workerCard} ${getWorkerCardClass(worker)}`}>
                <div className={styles.workerHeader}>
                  <div className={`${styles.workerIcon} ${getWorkerIconClass(worker)}`}>
                    {worker.name.charAt(0).toUpperCase()}
                  </div>
                  <div className={styles.workerInfo}>
                    <div className={styles.workerName}>{worker.name}</div>
                    <div className={styles.workerStatus}>{worker.status}</div>
                    {worker.currentTask && (
                      <div className={styles.workerCurrentTask}>
                        Task: {worker.currentTask}
                      </div>
                    )}
                  </div>
                </div>
                
                <div className={styles.workerMetrics}>
                  <div className={styles.workerMetric}>
                    <div className={styles.workerMetricValue}>{Math.round(worker.cpuUsage)}%</div>
                    <div className={styles.workerMetricLabel}>CPU</div>
                  </div>
                  <div className={styles.workerMetric}>
                    <div className={styles.workerMetricValue}>{formatMemory(worker.memoryUsage)}</div>
                    <div className={styles.workerMetricLabel}>Memory</div>
                  </div>
                  <div className={styles.workerMetric}>
                    <div className={styles.workerMetricValue}>{worker.tasksCompleted}</div>
                    <div className={styles.workerMetricLabel}>Tasks</div>
                  </div>
                  <div className={styles.workerMetric}>
                    <div className={styles.workerMetricValue}>{formatDuration(worker.uptime * 1000)}</div>
                    <div className={styles.workerMetricLabel}>Uptime</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* GPU Utilization */}
      {showGPUUtilization && analysisStatus && analysisStatus.gpus.length > 0 && (
        <div className={styles.gpuUtilization}>
          <div className={styles.gpuHeader}>
            <h3 className={styles.gpuTitle}>GPU Utilization</h3>
          </div>
          
          <div className={styles.gpuGrid}>
            {analysisStatus.gpus.map((gpu) => (
              <div key={gpu.id} className={`${styles.gpuCard} ${getGPUCardClass(gpu)}`}>
                <div className={styles.gpuHeader}>
                  <div className={`${styles.gpuIcon} ${getGPUIconClass(gpu)}`}>
                    {gpu.name.charAt(0).toUpperCase()}
                  </div>
                  <div className={styles.gpuInfo}>
                    <div className={styles.gpuName}>{gpu.name}</div>
                    <div className={styles.gpuStatus}>{gpu.status}</div>
                    {gpu.currentTask && (
                      <div className={styles.gpuCurrentTask}>
                        Task: {gpu.currentTask}
                      </div>
                    )}
                  </div>
                </div>
                
                <div className={styles.gpuMetrics}>
                  <div className={styles.gpuMetric}>
                    <div className={styles.gpuMetricValue}>{Math.round(gpu.utilization)}%</div>
                    <div className={styles.gpuMetricLabel}>Utilization</div>
                  </div>
                  <div className={styles.gpuMetric}>
                    <div className={styles.gpuMetricValue}>{Math.round(gpu.memoryUsagePercentage)}%</div>
                    <div className={styles.gpuMetricLabel}>Memory</div>
                  </div>
                  <div className={styles.gpuMetric}>
                    <div className={styles.gpuMetricValue}>{gpu.temperature}°C</div>
                    <div className={styles.gpuMetricLabel}>Temperature</div>
                  </div>
                  <div className={styles.gpuMetric}>
                    <div className={styles.gpuMetricValue}>{gpu.powerUsage}W</div>
                    <div className={styles.gpuMetricLabel}>Power</div>
                  </div>
                </div>
                
                <div className={styles.gpuUtilizationBar}>
                  <div 
                    className={styles.gpuUtilizationFill}
                    style={{ width: `${gpu.utilization}%` }}
                  />
                </div>
                
                <div className={styles.gpuMemoryBar}>
                  <div 
                    className={styles.gpuMemoryFill}
                    style={{ width: `${gpu.memoryUsagePercentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Queue Status */}
      {showQueueStatus && analysisStatus && (
        <div className={styles.queueStatus}>
          <div className={styles.queueHeader}>
            <h3 className={styles.queueTitle}>Queue Status</h3>
          </div>
          
          <div className={`${styles.queueCard} ${getQueueCardClass(analysisStatus.queue)}`}>
            <div className={styles.queueInfo}>
              <div className={styles.queueInfoItem}>
                <div className={styles.queueInfoValue}>{analysisStatus.queue.position}</div>
                <div className={styles.queueInfoLabel}>Position</div>
              </div>
              <div className={styles.queueInfoItem}>
                <div className={styles.queueInfoValue}>{analysisStatus.queue.totalItems}</div>
                <div className={styles.queueInfoLabel}>Total Items</div>
              </div>
              <div className={styles.queueInfoItem}>
                <div className={styles.queueInfoValue}>{formatDuration(analysisStatus.queue.estimatedWaitTime * 1000)}</div>
                <div className={styles.queueInfoLabel}>Est. Wait Time</div>
              </div>
              <div className={styles.queueInfoItem}>
                <div className={styles.queueInfoValue}>{analysisStatus.queue.priority}</div>
                <div className={styles.queueInfoLabel}>Priority</div>
              </div>
            </div>
            
            <div className={styles.queueProgress}>
              <div 
                className={styles.queueProgressFill}
                style={{ width: `${(analysisStatus.queue.position / analysisStatus.queue.totalItems) * 100}%` }}
              />
            </div>
            
            <div className={styles.queueDetails}>
              <div className={styles.queueDetail}>
                <div className={styles.queueDetailValue}>{analysisStatus.queue.processingRate}</div>
                <div className={styles.queueDetailLabel}>Items/min</div>
              </div>
              <div className={styles.queueDetail}>
                <div className={styles.queueDetailValue}>{formatDuration(analysisStatus.queue.averageProcessingTime * 1000)}</div>
                <div className={styles.queueDetailLabel}>Avg. Processing Time</div>
              </div>
              <div className={styles.queueDetail}>
                <div className={styles.queueDetailValue}>{analysisStatus.queue.status}</div>
                <div className={styles.queueDetailLabel}>Queue Status</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Last Update */}
      {lastUpdate && (
        <div className="mt-4 text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Last updated: {lastUpdate.toLocaleTimeString()}
          </p>
        </div>
      )}
    </div>
  );
};

export default ProcessingStageVisualization;
