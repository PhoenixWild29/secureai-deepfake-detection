import React from 'react';
import { 
  CheckCircleIcon, 
  ClockIcon, 
  ExclamationTriangleIcon,
  PlayIcon,
  PauseIcon
} from '@heroicons/react/24/outline';
import { ProcessingStage, StageConfig, STAGE_CONFIGS } from '@/types/progress';
import styles from './ComprehensiveProgressTracker.module.css';

export interface StageIndicatorProps {
  /** Stage configuration */
  stage: ProcessingStage;
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
  /** Estimated duration for this stage */
  estimatedDuration?: number;
  /** Actual duration for this stage */
  actualDuration?: number;
  /** Additional CSS classes */
  className?: string;
  /** Whether to show detailed information */
  showDetails?: boolean;
  /** Callback when stage is clicked */
  onClick?: (stage: ProcessingStage) => void;
}

/**
 * StageIndicator component for displaying individual processing stages
 */
export const StageIndicator: React.FC<StageIndicatorProps> = ({
  stage,
  progress,
  isActive,
  isCompleted,
  hasError,
  isSkipped,
  estimatedDuration,
  actualDuration,
  className = '',
  showDetails = false,
  onClick,
}) => {
  const stageConfig: StageConfig = STAGE_CONFIGS[stage] || {
    id: stage,
    name: stage.replace(/_/g, ' ').toUpperCase(),
    description: 'Processing stage',
    icon: 'cog',
    estimatedDuration: 0,
    skippable: false,
    dependencies: [],
  };

  const getStageIcon = () => {
    if (hasError) {
      return <ExclamationTriangleIcon className={styles.stageIcon} />;
    }
    
    if (isCompleted) {
      return <CheckCircleIcon className={styles.stageIcon} />;
    }
    
    if (isActive) {
      return <PlayIcon className={styles.stageIcon} />;
    }
    
    if (isSkipped) {
      return <PauseIcon className={styles.stageIcon} />;
    }
    
    return <ClockIcon className={styles.stageIcon} />;
  };

  const getStageStatus = () => {
    if (hasError) return 'error';
    if (isCompleted) return 'completed';
    if (isActive) return 'active';
    if (isSkipped) return 'skipped';
    return 'pending';
  };

  const formatDuration = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    
    if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    }
    return `${seconds}s`;
  };

  const handleClick = () => {
    if (onClick) {
      onClick(stage);
    }
  };

  const stageClasses = [
    styles.stageIndicator,
    styles[`stage-${getStageStatus()}`],
    isActive ? styles.active : '',
    onClick ? styles.clickable : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div 
      className={stageClasses}
      onClick={handleClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-label={`${stageConfig.name} stage - ${getStageStatus()}`}
      aria-current={isActive ? 'step' : undefined}
    >
      {/* Stage Icon */}
      <div className={styles.stageIconContainer}>
        {getStageIcon()}
        {isActive && (
          <div className={styles.activeIndicator}>
            <div className={styles.pulse} />
          </div>
        )}
      </div>

      {/* Stage Content */}
      <div className={styles.stageContent}>
        <div className={styles.stageHeader}>
          <h3 className={styles.stageName}>{stageConfig.name}</h3>
          <span className={styles.stageProgress}>{Math.round(progress)}%</span>
        </div>

        {/* Progress Bar */}
        <div className={styles.progressBarContainer}>
          <div 
            className={styles.progressBar}
            style={{ width: `${progress}%` }}
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            role="progressbar"
            aria-label={`${stageConfig.name} progress: ${Math.round(progress)}%`}
          />
        </div>

        {/* Stage Description */}
        <p className={styles.stageDescription}>
          {stageConfig.description}
        </p>

        {/* Detailed Information */}
        {showDetails && (
          <div className={styles.stageDetails}>
            {estimatedDuration && (
              <div className={styles.durationInfo}>
                <span className={styles.durationLabel}>Estimated:</span>
                <span className={styles.durationValue}>
                  {formatDuration(estimatedDuration)}
                </span>
              </div>
            )}
            
            {actualDuration && (
              <div className={styles.durationInfo}>
                <span className={styles.durationLabel}>Actual:</span>
                <span className={styles.durationValue}>
                  {formatDuration(actualDuration)}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Stage Status Indicator */}
      <div className={styles.stageStatusIndicator}>
        <div className={styles.statusDot} />
      </div>
    </div>
  );
};

/**
 * StageIndicatorGroup component for displaying multiple stages
 */
export interface StageIndicatorGroupProps {
  /** Array of stage data */
  stages: Array<{
    stage: ProcessingStage;
    progress: number;
    isActive: boolean;
    isCompleted: boolean;
    hasError: boolean;
    isSkipped: boolean;
    estimatedDuration?: number;
    actualDuration?: number;
  }>;
  /** Whether to show detailed information */
  showDetails?: boolean;
  /** Callback when stage is clicked */
  onStageClick?: (stage: ProcessingStage) => void;
  /** Additional CSS classes */
  className?: string;
}

export const StageIndicatorGroup: React.FC<StageIndicatorGroupProps> = ({
  stages,
  showDetails = false,
  onStageClick,
  className = '',
}) => {
  return (
    <div className={`${styles.stageGroup} ${className}`}>
      <div className={styles.stageList}>
        {stages.map((stageData, index) => (
          <React.Fragment key={stageData.stage}>
            <StageIndicator
              {...stageData}
              showDetails={showDetails}
              onClick={onStageClick}
            />
            
            {/* Connection Line */}
            {index < stages.length - 1 && (
              <div className={styles.stageConnector}>
                <div className={styles.connectorLine} />
                <div className={styles.connectorDot} />
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

export default StageIndicator;
