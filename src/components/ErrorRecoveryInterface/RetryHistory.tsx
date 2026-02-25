import React, { useState, useMemo } from 'react';
import { 
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  PlayIcon,
  StopIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  UserIcon,
  CogIcon,
  FilmIcon,
  CpuChipIcon
} from '@heroicons/react/24/outline';
import { 
  RetryHistoryProps, 
  RetryAttempt, 
  RetryStatus,
  RetryScope 
} from '@/types/errorRecovery';
import styles from './ErrorRecoveryInterface.module.css';

/**
 * RetryHistory component
 * Displays history of previous retry attempts and their outcomes
 */
export const RetryHistory: React.FC<RetryHistoryProps> = ({
  retryHistory,
  showDetails = true,
  className = '',
}) => {
  const [expandedAttempts, setExpandedAttempts] = useState<Set<string>>(new Set());
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Sort retry attempts by timestamp
  const sortedAttempts = useMemo(() => {
    return [...retryHistory].sort((a, b) => {
      const comparison = a.timestamp.getTime() - b.timestamp.getTime();
      return sortOrder === 'asc' ? comparison : -comparison;
    });
  }, [retryHistory, sortOrder]);

  const getStatusIcon = (status: RetryStatus) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className={styles.retryStatusIconCompleted} />;
      case 'failed':
        return <XCircleIcon className={styles.retryStatusIconFailed} />;
      case 'in_progress':
        return <ArrowPathIcon className={styles.retryStatusIconInProgress} />;
      case 'pending':
        return <ClockIcon className={styles.retryStatusIconPending} />;
      case 'cancelled':
        return <StopIcon className={styles.retryStatusIconCancelled} />;
      default:
        return <ExclamationTriangleIcon className={styles.retryStatusIconUnknown} />;
    }
  };

  const getStatusColor = (status: RetryStatus) => {
    switch (status) {
      case 'completed':
        return styles.retryStatusCompleted;
      case 'failed':
        return styles.retryStatusFailed;
      case 'in_progress':
        return styles.retryStatusInProgress;
      case 'pending':
        return styles.retryStatusPending;
      case 'cancelled':
        return styles.retryStatusCancelled;
      default:
        return styles.retryStatusUnknown;
    }
  };

  const getScopeIcon = (scope: RetryScope) => {
    switch (scope) {
      case 'full_analysis':
        return <ArrowPathIcon className={styles.retryScopeIcon} />;
      case 'stage':
        return <CogIcon className={styles.retryScopeIcon} />;
      case 'frame':
        return <FilmIcon className={styles.retryScopeIcon} />;
      case 'worker':
        return <CpuChipIcon className={styles.retryScopeIcon} />;
      case 'gpu':
        return <CpuChipIcon className={styles.retryScopeIcon} />;
      default:
        return <PlayIcon className={styles.retryScopeIcon} />;
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

  const formatDuration = (duration?: number) => {
    if (!duration) return 'Unknown';
    
    const seconds = Math.floor(duration / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  };

  const formatRelativeTime = (timestamp: Date) => {
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

  const toggleAttemptExpansion = (attemptId: string) => {
    setExpandedAttempts(prev => {
      const newSet = new Set(prev);
      if (newSet.has(attemptId)) {
        newSet.delete(attemptId);
      } else {
        newSet.add(attemptId);
      }
      return newSet;
    });
  };

  const isAttemptExpanded = (attemptId: string) => expandedAttempts.has(attemptId);

  // Calculate statistics
  const stats = useMemo(() => {
    const total = retryHistory.length;
    const completed = retryHistory.filter(a => a.status === 'completed' && a.result?.success).length;
    const failed = retryHistory.filter(a => a.status === 'failed').length;
    const inProgress = retryHistory.filter(a => a.status === 'in_progress').length;
    const cancelled = retryHistory.filter(a => a.status === 'cancelled').length;
    
    const successRate = total > 0 ? (completed / total) * 100 : 0;
    const avgDuration = retryHistory
      .filter(a => a.duration)
      .reduce((sum, a) => sum + (a.duration || 0), 0) / 
      retryHistory.filter(a => a.duration).length || 0;

    return {
      total,
      completed,
      failed,
      inProgress,
      cancelled,
      successRate,
      avgDuration,
    };
  }, [retryHistory]);

  return (
    <div className={`${styles.retryHistory} ${className}`}>
      {/* Header */}
      <div className={styles.retryHistoryHeader}>
        <div className={styles.retryHistoryTitle}>
          <ClockIcon className={styles.retryHistoryIcon} />
          <h3 className={styles.retryHistoryTitleText}>Retry History</h3>
          <span className={styles.retryHistoryCount}>
            {retryHistory.length} attempt{retryHistory.length !== 1 ? 's' : ''}
          </span>
        </div>

        <div className={styles.retryHistorySort}>
          <button
            className={`${styles.retryHistorySortButton} ${
              sortOrder === 'desc' ? styles.retryHistorySortButtonActive : ''
            }`}
            onClick={() => setSortOrder('desc')}
            aria-pressed={sortOrder === 'desc'}
          >
            Newest First
          </button>
          <button
            className={`${styles.retryHistorySortButton} ${
              sortOrder === 'asc' ? styles.retryHistorySortButtonActive : ''
            }`}
            onClick={() => setSortOrder('asc')}
            aria-pressed={sortOrder === 'asc'}
          >
            Oldest First
          </button>
        </div>
      </div>

      {/* Statistics */}
      {retryHistory.length > 0 && (
        <div className={styles.retryHistoryStats}>
          <div className={styles.retryHistoryStatsGrid}>
            <div className={styles.retryHistoryStat}>
              <span className={styles.retryHistoryStatValue}>{stats.total}</span>
              <span className={styles.retryHistoryStatLabel}>Total Attempts</span>
            </div>
            <div className={styles.retryHistoryStat}>
              <span className={`${styles.retryHistoryStatValue} ${styles.retryHistoryStatValueSuccess}`}>
                {stats.completed}
              </span>
              <span className={styles.retryHistoryStatLabel}>Successful</span>
            </div>
            <div className={styles.retryHistoryStat}>
              <span className={`${styles.retryHistoryStatValue} ${styles.retryHistoryStatValueFailed}`}>
                {stats.failed}
              </span>
              <span className={styles.retryHistoryStatLabel}>Failed</span>
            </div>
            <div className={styles.retryHistoryStat}>
              <span className={styles.retryHistoryStatValue}>
                {stats.successRate.toFixed(1)}%
              </span>
              <span className={styles.retryHistoryStatLabel}>Success Rate</span>
            </div>
            <div className={styles.retryHistoryStat}>
              <span className={styles.retryHistoryStatValue}>
                {formatDuration(stats.avgDuration)}
              </span>
              <span className={styles.retryHistoryStatLabel}>Avg Duration</span>
            </div>
          </div>
        </div>
      )}

      {/* Retry Attempts List */}
      <div className={styles.retryHistoryList}>
        {sortedAttempts.length === 0 ? (
          <div className={styles.retryHistoryEmpty}>
            <ClockIcon className={styles.retryHistoryEmptyIcon} />
            <p className={styles.retryHistoryEmptyText}>
              No retry attempts have been made yet
            </p>
          </div>
        ) : (
          sortedAttempts.map((attempt) => {
            const isExpanded = isAttemptExpanded(attempt.id);
            const hasDetails = showDetails && (attempt.result || attempt.error || attempt.configuration);

            return (
              <div key={attempt.id} className={styles.retryAttempt}>
                {/* Attempt Header */}
                <div 
                  className={`${styles.retryAttemptHeader} ${
                    hasDetails ? styles.retryAttemptHeaderExpandable : ''
                  }`}
                  onClick={hasDetails ? () => toggleAttemptExpansion(attempt.id) : undefined}
                  role={hasDetails ? 'button' : undefined}
                  tabIndex={hasDetails ? 0 : undefined}
                  aria-expanded={hasDetails ? isExpanded : undefined}
                >
                  <div className={styles.retryAttemptMain}>
                    <div className={styles.retryAttemptStatus}>
                      {getStatusIcon(attempt.status)}
                      <span className={`${styles.retryAttemptStatusText} ${getStatusColor(attempt.status)}`}>
                        {attempt.status.toUpperCase()}
                      </span>
                    </div>

                    <div className={styles.retryAttemptContent}>
                      <div className={styles.retryAttemptTitle}>
                        <div className={styles.retryAttemptScope}>
                          {getScopeIcon(attempt.scope)}
                          <span className={styles.retryAttemptScopeText}>
                            {attempt.scope.replace(/_/g, ' ').toUpperCase()}
                          </span>
                        </div>
                        <span className={styles.retryAttemptNumber}>
                          Attempt #{attempt.attemptNumber}
                        </span>
                      </div>

                      <div className={styles.retryAttemptMeta}>
                        <div className={styles.retryAttemptMetaItem}>
                          <ClockIcon className={styles.retryAttemptMetaIcon} />
                          <span className={styles.retryAttemptMetaText}>
                            {formatTimestamp(attempt.timestamp)}
                          </span>
                          <span className={styles.retryAttemptMetaSubtext}>
                            ({formatRelativeTime(attempt.timestamp)})
                          </span>
                        </div>

                        {attempt.duration && (
                          <div className={styles.retryAttemptMetaItem}>
                            <span className={styles.retryAttemptMetaLabel}>Duration:</span>
                            <span className={styles.retryAttemptMetaText}>
                              {formatDuration(attempt.duration)}
                            </span>
                          </div>
                        )}

                        {attempt.initiatedBy && (
                          <div className={styles.retryAttemptMetaItem}>
                            <UserIcon className={styles.retryAttemptMetaIcon} />
                            <span className={styles.retryAttemptMetaText}>
                              {attempt.initiatedBy}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {hasDetails && (
                    <div className={styles.retryAttemptExpand}>
                      {isExpanded ? (
                        <ChevronDownIcon className={styles.retryAttemptExpandIcon} />
                      ) : (
                        <ChevronRightIcon className={styles.retryAttemptExpandIcon} />
                      )}
                    </div>
                  )}
                </div>

                {/* Attempt Details */}
                {isExpanded && hasDetails && (
                  <div className={styles.retryAttemptDetails}>
                    {/* Retry Result */}
                    {attempt.result && (
                      <div className={styles.retryAttemptResult}>
                        <h5 className={styles.retryAttemptResultTitle}>Result</h5>
                        <div className={styles.retryAttemptResultContent}>
                          <div className={styles.retryAttemptResultStatus}>
                            <span className={styles.retryAttemptResultStatusLabel}>Success:</span>
                            <span className={`${styles.retryAttemptResultStatusValue} ${
                              attempt.result.success ? styles.retryAttemptResultSuccess : styles.retryAttemptResultFailed
                            }`}>
                              {attempt.result.success ? 'Yes' : 'No'}
                            </span>
                          </div>
                          
                          <div className={styles.retryAttemptResultMessage}>
                            <span className={styles.retryAttemptResultMessageLabel}>Message:</span>
                            <span className={styles.retryAttemptResultMessageValue}>
                              {attempt.result.message}
                            </span>
                          </div>

                          {attempt.result.progress !== undefined && (
                            <div className={styles.retryAttemptResultProgress}>
                              <span className={styles.retryAttemptResultProgressLabel}>Progress:</span>
                              <span className={styles.retryAttemptResultProgressValue}>
                                {attempt.result.progress}%
                              </span>
                            </div>
                          )}

                          {attempt.result.newStage && (
                            <div className={styles.retryAttemptResultStage}>
                              <span className={styles.retryAttemptResultStageLabel}>New Stage:</span>
                              <span className={styles.retryAttemptResultStageValue}>
                                {attempt.result.newStage}
                              </span>
                            </div>
                          )}

                          {attempt.result.data && Object.keys(attempt.result.data).length > 0 && (
                            <div className={styles.retryAttemptResultData}>
                              <span className={styles.retryAttemptResultDataLabel}>Additional Data:</span>
                              <pre className={styles.retryAttemptResultDataPre}>
                                {JSON.stringify(attempt.result.data, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Retry Error */}
                    {attempt.error && (
                      <div className={styles.retryAttemptError}>
                        <h5 className={styles.retryAttemptErrorTitle}>Error Details</h5>
                        <div className={styles.retryAttemptErrorContent}>
                          <div className={styles.retryAttemptErrorType}>
                            <span className={styles.retryAttemptErrorTypeLabel}>Type:</span>
                            <span className={styles.retryAttemptErrorTypeValue}>
                              {attempt.error.type.replace(/_/g, ' ').toUpperCase()}
                            </span>
                          </div>
                          
                          <div className={styles.retryAttemptErrorMessage}>
                            <span className={styles.retryAttemptErrorMessageLabel}>Message:</span>
                            <span className={styles.retryAttemptErrorMessageValue}>
                              {attempt.error.message}
                            </span>
                          </div>

                          {attempt.error.code && (
                            <div className={styles.retryAttemptErrorCode}>
                              <span className={styles.retryAttemptErrorCodeLabel}>Code:</span>
                              <span className={styles.retryAttemptErrorCodeValue}>
                                {attempt.error.code}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Retry Configuration */}
                    {attempt.configuration && (
                      <div className={styles.retryAttemptConfiguration}>
                        <h5 className={styles.retryAttemptConfigurationTitle}>Configuration</h5>
                        <div className={styles.retryAttemptConfigurationContent}>
                          <div className={styles.retryAttemptConfigurationScope}>
                            <span className={styles.retryAttemptConfigurationScopeLabel}>Scope:</span>
                            <span className={styles.retryAttemptConfigurationScopeValue}>
                              {attempt.configuration.scope.replace(/_/g, ' ').toUpperCase()}
                            </span>
                          </div>

                          {attempt.configuration.stage && (
                            <div className={styles.retryAttemptConfigurationStage}>
                              <span className={styles.retryAttemptConfigurationStageLabel}>Stage:</span>
                              <span className={styles.retryAttemptConfigurationStageValue}>
                                {attempt.configuration.stage}
                              </span>
                            </div>
                          )}

                          {attempt.configuration.frameIndex !== undefined && (
                            <div className={styles.retryAttemptConfigurationFrame}>
                              <span className={styles.retryAttemptConfigurationFrameLabel}>Frame Index:</span>
                              <span className={styles.retryAttemptConfigurationFrameValue}>
                                {attempt.configuration.frameIndex}
                              </span>
                            </div>
                          )}

                          {attempt.configuration.options && (
                            <div className={styles.retryAttemptConfigurationOptions}>
                              <span className={styles.retryAttemptConfigurationOptionsLabel}>Options:</span>
                              <pre className={styles.retryAttemptConfigurationOptionsPre}>
                                {JSON.stringify(attempt.configuration.options, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default RetryHistory;
