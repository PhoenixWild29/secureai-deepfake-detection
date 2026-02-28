/**
 * ExportProgressIndicator Component
 * Work Order #39 - Multi-Format Export Capabilities
 * 
 * Real-time progress tracking component for export operations with
 * estimated completion time and status updates.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { exportService } from '../../services/exportService';
import styles from './ExportProgressIndicator.module.css';

// ============================================================================
// Constants
// ============================================================================

const EXPORT_STATUSES = {
  INITIATING: 'initiating',
  PROCESSING: 'processing',
  GENERATING: 'generating',
  COMPLETING: 'completing',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
};

const STATUS_MESSAGES = {
  [EXPORT_STATUSES.INITIATING]: 'Initializing export...',
  [EXPORT_STATUSES.PROCESSING]: 'Processing data...',
  [EXPORT_STATUSES.GENERATING]: 'Generating export file...',
  [EXPORT_STATUSES.COMPLETING]: 'Finalizing export...',
  [EXPORT_STATUSES.COMPLETED]: 'Export completed successfully!',
  [EXPORT_STATUSES.FAILED]: 'Export failed',
  [EXPORT_STATUSES.CANCELLED]: 'Export cancelled'
};

const STATUS_ICONS = {
  [EXPORT_STATUSES.INITIATING]: '🔄',
  [EXPORT_STATUSES.PROCESSING]: '⚙️',
  [EXPORT_STATUSES.GENERATING]: '📄',
  [EXPORT_STATUSES.COMPLETING]: '✅',
  [EXPORT_STATUSES.COMPLETED]: '🎉',
  [EXPORT_STATUSES.FAILED]: '❌',
  [EXPORT_STATUSES.CANCELLED]: '⏹️'
};

// ============================================================================
// Main Component
// ============================================================================

/**
 * ExportProgressIndicator - Real-time export progress tracking
 * 
 * @param {Object} props - Component properties
 * @param {Object} props.progress - Progress data object
 * @param {string} props.progress.status - Current export status
 * @param {number} props.progress.progress - Progress percentage (0-100)
 * @param {string} props.progress.message - Status message
 * @param {string} props.progress.exportId - Export job ID
 * @param {string} props.progress.estimatedCompletion - Estimated completion time
 * @param {string} props.progress.errorMessage - Error message if failed
 * @param {Function} props.onComplete - Callback when export completes
 * @param {Function} props.onError - Callback when export fails
 * @param {Function} props.onCancel - Callback when export is cancelled
 * @returns {JSX.Element} ExportProgressIndicator component
 */
const ExportProgressIndicator = ({
  progress,
  onComplete,
  onError,
  onCancel
}) => {
  
  // ============================================================================
  // State Management
  // ============================================================================
  
  const [currentProgress, setCurrentProgress] = useState(progress);
  const [timeRemaining, setTimeRemaining] = useState(null);
  const [startTime, setStartTime] = useState(Date.now());
  const [isExpanded, setIsExpanded] = useState(false);
  const [logs, setLogs] = useState([]);
  
  const { subscribe, unsubscribe } = useWebSocket();
  
  // ============================================================================
  // Effects
  // ============================================================================
  
  useEffect(() => {
    setCurrentProgress(progress);
    
    if (progress.status === EXPORT_STATUSES.INITIATING) {
      setStartTime(Date.now());
      setLogs([{ timestamp: Date.now(), message: 'Export initiated', level: 'info' }]);
    }
  }, [progress]);
  
  useEffect(() => {
    // Subscribe to export progress updates
    const handleProgressUpdate = (data) => {
      if (data.type === 'export_progress' && data.exportId === currentProgress.exportId) {
        setCurrentProgress(data.progress);
        
        // Add to logs
        setLogs(prev => [...prev, {
          timestamp: Date.now(),
          message: data.progress.message,
          level: data.progress.status === EXPORT_STATUSES.FAILED ? 'error' : 'info'
        }]);
        
        // Handle completion
        if (data.progress.status === EXPORT_STATUSES.COMPLETED) {
          onComplete?.(data.progress);
        } else if (data.progress.status === EXPORT_STATUSES.FAILED) {
          onError?.(data.progress);
        }
      }
    };
    
    subscribe('export_progress', handleProgressUpdate);
    
    return () => {
      unsubscribe('export_progress', handleProgressUpdate);
    };
  }, [currentProgress.exportId, subscribe, unsubscribe, onComplete, onError]);
  
  useEffect(() => {
    // Calculate time remaining
    if (currentProgress.progress > 0 && currentProgress.progress < 100) {
      const elapsed = Date.now() - startTime;
      const estimatedTotal = (elapsed / currentProgress.progress) * 100;
      const remaining = estimatedTotal - elapsed;
      
      if (remaining > 0) {
        setTimeRemaining(Math.ceil(remaining / 1000)); // Convert to seconds
      }
    }
  }, [currentProgress.progress, startTime]);
  
  // ============================================================================
  // Event Handlers
  // ============================================================================
  
  const handleCancel = useCallback(async () => {
    try {
      await exportService.cancelExport(currentProgress.exportId);
      setCurrentProgress(prev => ({ ...prev, status: EXPORT_STATUSES.CANCELLED }));
      onCancel?.(currentProgress);
    } catch (err) {
      console.error('Failed to cancel export:', err);
    }
  }, [currentProgress.exportId, currentProgress, onCancel]);
  
  const handleDownload = useCallback(async () => {
    try {
      await exportService.downloadExport(currentProgress.exportId);
    } catch (err) {
      console.error('Failed to download export:', err);
    }
  }, [currentProgress.exportId]);
  
  const handleRetry = useCallback(async () => {
    try {
      const retryProgress = await exportService.retryExport(currentProgress.exportId);
      setCurrentProgress(retryProgress);
      setStartTime(Date.now());
      setLogs(prev => [...prev, {
        timestamp: Date.now(),
        message: 'Export retry initiated',
        level: 'info'
      }]);
    } catch (err) {
      console.error('Failed to retry export:', err);
    }
  }, [currentProgress.exportId]);
  
  // ============================================================================
  // Helper Functions
  // ============================================================================
  
  const formatTime = (seconds) => {
    if (seconds < 60) {
      return `${seconds}s`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      return `${minutes}m ${remainingSeconds}s`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return `${hours}h ${minutes}m`;
    }
  };
  
  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString();
  };
  
  const getProgressColor = (status) => {
    switch (status) {
      case EXPORT_STATUSES.COMPLETED:
        return '#48bb78';
      case EXPORT_STATUSES.FAILED:
        return '#f56565';
      case EXPORT_STATUSES.CANCELLED:
        return '#a0aec0';
      default:
        return '#667eea';
    }
  };
  
  const canCancel = () => {
    return [
      EXPORT_STATUSES.INITIATING,
      EXPORT_STATUSES.PROCESSING,
      EXPORT_STATUSES.GENERATING
    ].includes(currentProgress.status);
  };
  
  const canDownload = () => {
    return currentProgress.status === EXPORT_STATUSES.COMPLETED;
  };
  
  const canRetry = () => {
    return currentProgress.status === EXPORT_STATUSES.FAILED;
  };
  
  // ============================================================================
  // Render Functions
  // ============================================================================
  
  const renderProgressBar = () => (
    <div className={styles.progressBarContainer}>
      <div className={styles.progressBar}>
        <div
          className={styles.progressFill}
          style={{
            width: `${currentProgress.progress}%`,
            backgroundColor: getProgressColor(currentProgress.status)
          }}
        />
      </div>
      <div className={styles.progressText}>
        {currentProgress.progress}%
      </div>
    </div>
  );
  
  const renderStatusInfo = () => (
    <div className={styles.statusInfo}>
      <div className={styles.statusIcon}>
        {STATUS_ICONS[currentProgress.status]}
      </div>
      <div className={styles.statusContent}>
        <div className={styles.statusMessage}>
          {currentProgress.message || STATUS_MESSAGES[currentProgress.status]}
        </div>
        {timeRemaining && currentProgress.status !== EXPORT_STATUSES.COMPLETED && (
          <div className={styles.timeRemaining}>
            Estimated time remaining: {formatTime(timeRemaining)}
          </div>
        )}
      </div>
    </div>
  );
  
  const renderActionButtons = () => {
    const buttons = [];
    
    if (canCancel()) {
      buttons.push(
        <button
          key="cancel"
          onClick={handleCancel}
          className={styles.cancelButton}
        >
          Cancel Export
        </button>
      );
    }
    
    if (canDownload()) {
      buttons.push(
        <button
          key="download"
          onClick={handleDownload}
          className={styles.downloadButton}
        >
          Download Export
        </button>
      );
    }
    
    if (canRetry()) {
      buttons.push(
        <button
          key="retry"
          onClick={handleRetry}
          className={styles.retryButton}
        >
          Retry Export
        </button>
      );
    }
    
    if (buttons.length > 0) {
      return (
        <div className={styles.actionButtons}>
          {buttons}
        </div>
      );
    }
    
    return null;
  };
  
  const renderLogs = () => {
    if (!isExpanded || logs.length === 0) return null;
    
    return (
      <div className={styles.logsContainer}>
        <div className={styles.logsHeader}>
          <h4>Export Logs</h4>
        </div>
        <div className={styles.logsList}>
          {logs.map((log, index) => (
            <div key={index} className={`${styles.logEntry} ${styles[log.level]}`}>
              <span className={styles.logTimestamp}>
                {formatTimestamp(log.timestamp)}
              </span>
              <span className={styles.logMessage}>{log.message}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };
  
  const renderErrorDetails = () => {
    if (currentProgress.status !== EXPORT_STATUSES.FAILED || !currentProgress.errorMessage) {
      return null;
    }
    
    return (
      <div className={styles.errorDetails}>
        <div className={styles.errorIcon}>⚠️</div>
        <div className={styles.errorContent}>
          <h4>Export Failed</h4>
          <p>{currentProgress.errorMessage}</p>
        </div>
      </div>
    );
  };
  
  // ============================================================================
  // Main Render
  // ============================================================================
  
  return (
    <div className={styles.exportProgressIndicator}>
      <div className={styles.progressHeader}>
        <h3>Export Progress</h3>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={styles.expandButton}
        >
          {isExpanded ? '▼' : '▶'}
        </button>
      </div>
      
      <div className={styles.progressContent}>
        {renderProgressBar()}
        {renderStatusInfo()}
        {renderActionButtons()}
        {renderErrorDetails()}
        {renderLogs()}
      </div>
      
      {currentProgress.exportId && (
        <div className={styles.exportId}>
          Export ID: {currentProgress.exportId}
        </div>
      )}
    </div>
  );
};

export { ExportProgressIndicator };
export default ExportProgressIndicator;
