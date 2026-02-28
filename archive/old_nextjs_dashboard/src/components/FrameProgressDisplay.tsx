import React, { useState, useMemo } from 'react';
import { 
  ChevronDownIcon, 
  ChevronRightIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  PlayIcon
} from '@heroicons/react/24/outline';
import { FrameProgressData, ErrorInfo } from '@/types/progress';
import styles from './ComprehensiveProgressTracker.module.css';

export interface FrameProgressDisplayProps {
  /** Frame progress data */
  frameProgress: FrameProgressData[];
  /** Whether to show detailed frame information */
  showDetails?: boolean;
  /** Maximum number of frames to display before collapsing */
  maxVisibleFrames?: number;
  /** Whether the display is collapsed by default */
  collapsed?: boolean;
  /** Callback when frame is clicked */
  onFrameClick?: (frameIndex: number) => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * FrameProgressDisplay component for showing frame-level processing progress
 */
export const FrameProgressDisplay: React.FC<FrameProgressDisplayProps> = ({
  frameProgress,
  showDetails = false,
  maxVisibleFrames = 10,
  collapsed: initialCollapsed = true,
  onFrameClick,
  className = '',
}) => {
  const [collapsed, setCollapsed] = useState(initialCollapsed);
  const [expandedFrames, setExpandedFrames] = useState<Set<number>>(new Set());

  // Calculate frame statistics
  const frameStats = useMemo(() => {
    const total = frameProgress.length;
    const completed = frameProgress.filter(f => f.status === 'completed').length;
    const processing = frameProgress.filter(f => f.status === 'processing').length;
    const pending = frameProgress.filter(f => f.status === 'pending').length;
    const error = frameProgress.filter(f => f.status === 'error').length;

    return {
      total,
      completed,
      processing,
      pending,
      error,
      completionRate: total > 0 ? (completed / total) * 100 : 0,
    };
  }, [frameProgress]);

  // Get frames to display
  const visibleFrames = useMemo(() => {
    if (collapsed && frameProgress.length > maxVisibleFrames) {
      // Show first few frames, last few frames, and any frames with errors
      const firstFrames = frameProgress.slice(0, Math.floor(maxVisibleFrames / 2));
      const lastFrames = frameProgress.slice(-Math.floor(maxVisibleFrames / 2));
      const errorFrames = frameProgress.filter(f => f.status === 'error');
      
      const visible = [...firstFrames, ...lastFrames, ...errorFrames];
      return Array.from(new Set(visible.map(f => f.frameIndex)))
        .map(index => frameProgress.find(f => f.frameIndex === index)!)
        .sort((a, b) => a.frameIndex - b.frameIndex);
    }
    
    return frameProgress;
  }, [frameProgress, collapsed, maxVisibleFrames]);

  const toggleCollapsed = () => {
    setCollapsed(!collapsed);
  };

  const toggleFrameExpansion = (frameIndex: number) => {
    setExpandedFrames(prev => {
      const newSet = new Set(prev);
      if (newSet.has(frameIndex)) {
        newSet.delete(frameIndex);
      } else {
        newSet.add(frameIndex);
      }
      return newSet;
    });
  };

  const getFrameIcon = (status: FrameProgressData['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className={styles.frameIcon} />;
      case 'processing':
        return <PlayIcon className={styles.frameIcon} />;
      case 'error':
        return <ExclamationTriangleIcon className={styles.frameIcon} />;
      default:
        return <ClockIcon className={styles.frameIcon} />;
    }
  };

  const getFrameStatusClass = (status: FrameProgressData['status']) => {
    return styles[`frame-${status}`];
  };

  const formatDuration = (startTime?: Date, endTime?: Date) => {
    if (!startTime) return 'N/A';
    
    const end = endTime || new Date();
    const duration = end.getTime() - startTime.getTime();
    const seconds = Math.floor(duration / 1000);
    
    if (seconds < 60) {
      return `${seconds}s`;
    }
    
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m ${seconds % 60}s`;
  };

  const renderFrameError = (error?: ErrorInfo) => {
    if (!error) return null;

    return (
      <div className={styles.frameError}>
        <div className={styles.errorHeader}>
          <ExclamationTriangleIcon className={styles.errorIcon} />
          <span className={styles.errorCode}>{error.code}</span>
        </div>
        <p className={styles.errorMessage}>{error.message}</p>
        {error.recoveryActions && error.recoveryActions.length > 0 && (
          <div className={styles.recoveryActions}>
            <span className={styles.recoveryLabel}>Recovery options:</span>
            <ul className={styles.recoveryList}>
              {error.recoveryActions.map((action, index) => (
                <li key={index} className={styles.recoveryItem}>
                  {action.description}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  const renderFrameDetails = (frame: FrameProgressData) => {
    if (!showDetails) return null;

    return (
      <div className={styles.frameDetails}>
        <div className={styles.frameMetadata}>
          <div className={styles.metadataItem}>
            <span className={styles.metadataLabel}>Progress:</span>
            <span className={styles.metadataValue}>{Math.round(frame.progress)}%</span>
          </div>
          
          {frame.startTime && (
            <div className={styles.metadataItem}>
              <span className={styles.metadataLabel}>Duration:</span>
              <span className={styles.metadataValue}>
                {formatDuration(frame.startTime, frame.endTime)}
              </span>
            </div>
          )}
          
          {frame.endTime && (
            <div className={styles.metadataItem}>
              <span className={styles.metadataLabel}>Completed:</span>
              <span className={styles.metadataValue}>
                {frame.endTime.toLocaleTimeString()}
              </span>
            </div>
          )}
        </div>
        
        {frame.error && renderFrameError(frame.error)}
      </div>
    );
  };

  if (frameProgress.length === 0) {
    return (
      <div className={`${styles.frameProgressDisplay} ${className}`}>
        <div className={styles.frameStats}>
          <span className={styles.statsLabel}>No frames to process</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.frameProgressDisplay} ${className}`}>
      {/* Frame Statistics Header */}
      <div className={styles.frameStats}>
        <div className={styles.statsHeader}>
          <h4 className={styles.statsTitle}>Frame Progress</h4>
          <button
            className={styles.collapseButton}
            onClick={toggleCollapsed}
            aria-expanded={!collapsed}
            aria-label={collapsed ? 'Expand frame details' : 'Collapse frame details'}
          >
            {collapsed ? (
              <ChevronRightIcon className={styles.collapseIcon} />
            ) : (
              <ChevronDownIcon className={styles.collapseIcon} />
            )}
          </button>
        </div>
        
        <div className={styles.statsGrid}>
          <div className={styles.statItem}>
            <span className={styles.statValue}>{frameStats.total}</span>
            <span className={styles.statLabel}>Total</span>
          </div>
          <div className={styles.statItem}>
            <span className={styles.statValue}>{frameStats.completed}</span>
            <span className={styles.statLabel}>Completed</span>
          </div>
          <div className={styles.statItem}>
            <span className={styles.statValue}>{frameStats.processing}</span>
            <span className={styles.statLabel}>Processing</span>
          </div>
          <div className={styles.statItem}>
            <span className={styles.statValue}>{frameStats.pending}</span>
            <span className={styles.statLabel}>Pending</span>
          </div>
          {frameStats.error > 0 && (
            <div className={styles.statItem}>
              <span className={styles.statValue}>{frameStats.error}</span>
              <span className={styles.statLabel}>Errors</span>
            </div>
          )}
        </div>
        
        {/* Overall Progress Bar */}
        <div className={styles.frameProgressBar}>
          <div 
            className={styles.frameProgressFill}
            style={{ width: `${frameStats.completionRate}%` }}
            aria-valuenow={frameStats.completionRate}
            aria-valuemin={0}
            aria-valuemax={100}
            role="progressbar"
            aria-label={`Frame processing progress: ${Math.round(frameStats.completionRate)}%`}
          />
        </div>
      </div>

      {/* Frame List */}
      {!collapsed && (
        <div className={styles.frameList}>
          {visibleFrames.map((frame) => (
            <div
              key={frame.frameIndex}
              className={`${styles.frameItem} ${getFrameStatusClass(frame.status)}`}
              onClick={() => onFrameClick?.(frame.frameIndex)}
              role={onFrameClick ? 'button' : undefined}
              tabIndex={onFrameClick ? 0 : undefined}
              aria-label={`Frame ${frame.frameIndex} - ${frame.status}`}
            >
              <div className={styles.frameHeader}>
                <div className={styles.frameIconContainer}>
                  {getFrameIcon(frame.status)}
                </div>
                
                <div className={styles.frameInfo}>
                  <span className={styles.frameIndex}>Frame {frame.frameIndex}</span>
                  <span className={styles.frameStatus}>{frame.status}</span>
                </div>
                
                <div className={styles.frameProgress}>
                  <span className={styles.frameProgressText}>
                    {Math.round(frame.progress)}%
                  </span>
                </div>
                
                {showDetails && (
                  <button
                    className={styles.expandButton}
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleFrameExpansion(frame.frameIndex);
                    }}
                    aria-expanded={expandedFrames.has(frame.frameIndex)}
                    aria-label={`${expandedFrames.has(frame.frameIndex) ? 'Collapse' : 'Expand'} frame ${frame.frameIndex} details`}
                  >
                    {expandedFrames.has(frame.frameIndex) ? (
                      <ChevronDownIcon className={styles.expandIcon} />
                    ) : (
                      <ChevronRightIcon className={styles.expandIcon} />
                    )}
                  </button>
                )}
              </div>
              
              {/* Frame Progress Bar */}
              <div className={styles.frameItemProgressBar}>
                <div 
                  className={styles.frameItemProgressFill}
                  style={{ width: `${frame.progress}%` }}
                />
              </div>
              
              {/* Expanded Details */}
              {expandedFrames.has(frame.frameIndex) && renderFrameDetails(frame)}
            </div>
          ))}
          
          {/* Show More Indicator */}
          {collapsed && frameProgress.length > maxVisibleFrames && (
            <div className={styles.showMoreIndicator}>
              <span className={styles.showMoreText}>
                ... and {frameProgress.length - maxVisibleFrames} more frames
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FrameProgressDisplay;
