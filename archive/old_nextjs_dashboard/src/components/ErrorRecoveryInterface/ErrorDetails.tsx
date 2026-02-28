import React, { useState } from 'react';
import { 
  ExclamationTriangleIcon,
  ClockIcon,
  InformationCircleIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  DocumentTextIcon,
  CodeBracketIcon
} from '@heroicons/react/24/outline';
import { ErrorInfo, ErrorDetailsProps, ERROR_TYPE_CONFIGS } from '@/types/errorRecovery';
import styles from './ErrorRecoveryInterface.module.css';

/**
 * ErrorDetails component
 * Displays comprehensive error details including error type, stage, timestamp, and context
 */
export const ErrorDetails: React.FC<ErrorDetailsProps> = ({
  error,
  showDetails = true,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showStackTrace, setShowStackTrace] = useState(false);

  const errorConfig = ERROR_TYPE_CONFIGS[error.type] || ERROR_TYPE_CONFIGS.unknown_error;

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return styles.severityCritical;
      case 'high':
        return styles.severityHigh;
      case 'medium':
        return styles.severityMedium;
      case 'low':
        return styles.severityLow;
      default:
        return styles.severityMedium;
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <ExclamationTriangleIcon className={styles.severityIconCritical} />;
      case 'high':
        return <ExclamationTriangleIcon className={styles.severityIconHigh} />;
      case 'medium':
        return <ExclamationTriangleIcon className={styles.severityIconMedium} />;
      case 'low':
        return <InformationCircleIcon className={styles.severityIconLow} />;
      default:
        return <ExclamationTriangleIcon className={styles.severityIconMedium} />;
    }
  };

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const formatDuration = (timestamp: Date) => {
    const now = new Date();
    const diff = now.getTime() - timestamp.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) {
      return `${days} day${days > 1 ? 's' : ''} ago`;
    } else if (hours > 0) {
      return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else if (minutes > 0) {
      return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    } else {
      return 'Just now';
    }
  };

  return (
    <div className={`${styles.errorDetails} ${className}`}>
      {/* Error Header */}
      <div className={styles.errorHeader}>
        <div className={styles.errorIconContainer}>
          {getSeverityIcon(error.severity)}
        </div>
        
        <div className={styles.errorInfo}>
          <div className={styles.errorTitle}>
            <h3 className={styles.errorName}>{errorConfig.name}</h3>
            <span className={`${styles.severityBadge} ${getSeverityColor(error.severity)}`}>
              {error.severity.toUpperCase()}
            </span>
          </div>
          
          <p className={styles.errorMessage}>{error.message}</p>
          
          <div className={styles.errorMetadata}>
            <div className={styles.errorMetaItem}>
              <ClockIcon className={styles.metaIcon} />
              <span className={styles.metaLabel}>Occurred:</span>
              <span className={styles.metaValue}>{formatTimestamp(error.timestamp)}</span>
              <span className={styles.metaSubtext}>({formatDuration(error.timestamp)})</span>
            </div>
            
            <div className={styles.errorMetaItem}>
              <DocumentTextIcon className={styles.metaIcon} />
              <span className={styles.metaLabel}>Stage:</span>
              <span className={styles.metaValue}>{error.stage.replace(/_/g, ' ').toUpperCase()}</span>
            </div>
            
            <div className={styles.errorMetaItem}>
              <CodeBracketIcon className={styles.metaIcon} />
              <span className={styles.metaLabel}>Code:</span>
              <span className={styles.metaValue}>{error.code}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Error Description */}
      {error.description && (
        <div className={styles.errorDescription}>
          <p>{error.description}</p>
        </div>
      )}

      {/* Error Type Information */}
      <div className={styles.errorTypeInfo}>
        <h4 className={styles.errorTypeTitle}>Error Type Information</h4>
        <p className={styles.errorTypeDescription}>{errorConfig.description}</p>
        
        {errorConfig.commonCauses.length > 0 && (
          <div className={styles.commonCauses}>
            <h5 className={styles.commonCausesTitle}>Common Causes:</h5>
            <ul className={styles.commonCausesList}>
              {errorConfig.commonCauses.map((cause, index) => (
                <li key={index} className={styles.commonCausesItem}>
                  {cause}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Expandable Details */}
      {showDetails && (
        <div className={styles.errorDetailsSection}>
          <button
            className={styles.expandButton}
            onClick={() => setIsExpanded(!isExpanded)}
            aria-expanded={isExpanded}
            aria-controls="error-details-content"
          >
            <span className={styles.expandButtonText}>
              {isExpanded ? 'Hide' : 'Show'} Detailed Information
            </span>
            {isExpanded ? (
              <ChevronDownIcon className={styles.expandIcon} />
            ) : (
              <ChevronRightIcon className={styles.expandIcon} />
            )}
          </button>

          {isExpanded && (
            <div id="error-details-content" className={styles.errorDetailsContent}>
              {/* Error Context */}
              {error.context && (
                <div className={styles.errorContext}>
                  <h5 className={styles.contextTitle}>Error Context</h5>
                  
                  {error.context.analysisId && (
                    <div className={styles.contextItem}>
                      <span className={styles.contextLabel}>Analysis ID:</span>
                      <span className={styles.contextValue}>{error.context.analysisId}</span>
                    </div>
                  )}
                  
                  {error.context.frameIndex !== undefined && (
                    <div className={styles.contextItem}>
                      <span className={styles.contextLabel}>Frame Index:</span>
                      <span className={styles.contextValue}>{error.context.frameIndex}</span>
                    </div>
                  )}
                  
                  {error.context.workerId && (
                    <div className={styles.contextItem}>
                      <span className={styles.contextLabel}>Worker ID:</span>
                      <span className={styles.contextValue}>{error.context.workerId}</span>
                    </div>
                  )}
                  
                  {error.context.gpuId && (
                    <div className={styles.contextItem}>
                      <span className={styles.contextLabel}>GPU ID:</span>
                      <span className={styles.contextValue}>{error.context.gpuId}</span>
                    </div>
                  )}
                  
                  {error.context.processingStep && (
                    <div className={styles.contextItem}>
                      <span className={styles.contextLabel}>Processing Step:</span>
                      <span className={styles.contextValue}>{error.context.processingStep}</span>
                    </div>
                  )}

                  {/* Input Data */}
                  {error.context.inputData && (
                    <div className={styles.contextGroup}>
                      <h6 className={styles.contextGroupTitle}>Input Data</h6>
                      {error.context.inputData.fileName && (
                        <div className={styles.contextItem}>
                          <span className={styles.contextLabel}>File Name:</span>
                          <span className={styles.contextValue}>{error.context.inputData.fileName}</span>
                        </div>
                      )}
                      {error.context.inputData.fileSize && (
                        <div className={styles.contextItem}>
                          <span className={styles.contextLabel}>File Size:</span>
                          <span className={styles.contextValue}>
                            {(error.context.inputData.fileSize / (1024 * 1024)).toFixed(2)} MB
                          </span>
                        </div>
                      )}
                      {error.context.inputData.fileType && (
                        <div className={styles.contextItem}>
                          <span className={styles.contextLabel}>File Type:</span>
                          <span className={styles.contextValue}>{error.context.inputData.fileType}</span>
                        </div>
                      )}
                      {error.context.inputData.duration && (
                        <div className={styles.contextItem}>
                          <span className={styles.contextLabel}>Duration:</span>
                          <span className={styles.contextValue}>
                            {Math.floor(error.context.inputData.duration / 60)}:
                            {(error.context.inputData.duration % 60).toString().padStart(2, '0')}
                          </span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* System State */}
                  {error.context.systemState && (
                    <div className={styles.contextGroup}>
                      <h6 className={styles.contextGroupTitle}>System State</h6>
                      {error.context.systemState.cpuUsage !== undefined && (
                        <div className={styles.contextItem}>
                          <span className={styles.contextLabel}>CPU Usage:</span>
                          <span className={styles.contextValue}>{error.context.systemState.cpuUsage}%</span>
                        </div>
                      )}
                      {error.context.systemState.memoryUsage !== undefined && (
                        <div className={styles.contextItem}>
                          <span className={styles.contextLabel}>Memory Usage:</span>
                          <span className={styles.contextValue}>{error.context.systemState.memoryUsage}%</span>
                        </div>
                      )}
                      {error.context.systemState.diskSpace !== undefined && (
                        <div className={styles.contextItem}>
                          <span className={styles.contextLabel}>Disk Space:</span>
                          <span className={styles.contextValue}>{error.context.systemState.diskSpace}%</span>
                        </div>
                      )}
                      {error.context.systemState.networkStatus && (
                        <div className={styles.contextItem}>
                          <span className={styles.contextLabel}>Network Status:</span>
                          <span className={styles.contextValue}>{error.context.systemState.networkStatus}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Error Metadata */}
              {error.metadata && Object.keys(error.metadata).length > 0 && (
                <div className={styles.errorMetadata}>
                  <h5 className={styles.metadataTitle}>Additional Metadata</h5>
                  <div className={styles.metadataContent}>
                    <pre className={styles.metadataPre}>
                      {JSON.stringify(error.metadata, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {/* Stack Trace */}
              {error.stackTrace && (
                <div className={styles.stackTraceSection}>
                  <div className={styles.stackTraceHeader}>
                    <h5 className={styles.stackTraceTitle}>Stack Trace</h5>
                    <button
                      className={styles.stackTraceToggle}
                      onClick={() => setShowStackTrace(!showStackTrace)}
                      aria-expanded={showStackTrace}
                    >
                      {showStackTrace ? 'Hide' : 'Show'} Stack Trace
                    </button>
                  </div>
                  
                  {showStackTrace && (
                    <div className={styles.stackTraceContent}>
                      <pre className={styles.stackTracePre}>
                        {error.stackTrace}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Recovery Status */}
      <div className={styles.recoveryStatus}>
        <div className={styles.recoveryStatusItem}>
          <span className={styles.recoveryStatusLabel}>Recoverable:</span>
          <span className={`${styles.recoveryStatusValue} ${
            error.recoverable ? styles.recoverableYes : styles.recoverableNo
          }`}>
            {error.recoverable ? 'Yes' : 'No'}
          </span>
        </div>
        
        <div className={styles.recoveryStatusItem}>
          <span className={styles.recoveryStatusLabel}>Error ID:</span>
          <span className={styles.recoveryStatusValue}>{error.id}</span>
        </div>
      </div>
    </div>
  );
};

export default ErrorDetails;
