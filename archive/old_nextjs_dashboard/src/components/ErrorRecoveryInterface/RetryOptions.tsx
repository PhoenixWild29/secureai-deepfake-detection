import React, { useState } from 'react';
import { 
  ArrowPathIcon,
  PlayIcon,
  StopIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  CpuChipIcon,
  FilmIcon,
  CogIcon
} from '@heroicons/react/24/outline';
import { 
  ErrorInfo, 
  RetryOptionsProps, 
  RetryConfiguration, 
  RetryScope,
  UserRole,
  RetryAttempt 
} from '@/types/errorRecovery';
import styles from './ErrorRecoveryInterface.module.css';

/**
 * RetryOptions component
 * Provides manual retry mechanisms at different granularities
 */
export const RetryOptions: React.FC<RetryOptionsProps> = ({
  error,
  analysisId,
  userRole,
  retryHistory = [],
  onRetry,
  className = '',
}) => {
  const [isRetrying, setIsRetrying] = useState(false);
  const [selectedScope, setSelectedScope] = useState<RetryScope>('stage');
  const [retryOptions, setRetryOptions] = useState({
    skipCompletedStages: true,
    useCachedResults: true,
    forceRestart: false,
    timeout: 300000, // 5 minutes
  });

  // Check if user has permission to retry
  const canRetry = userRole?.permissions.some(p => 
    p.scope === 'retry' || p.scope === 'analysis'
  ) ?? true;

  // Check if there are active retries
  const activeRetries = retryHistory.filter(attempt => 
    attempt.status === 'pending' || attempt.status === 'in_progress'
  );

  // Get retry scope options based on error context
  const getAvailableScopes = (): RetryScope[] => {
    const scopes: RetryScope[] = ['full_analysis'];
    
    if (error.context?.stage) {
      scopes.push('stage');
    }
    
    if (error.context?.frameIndex !== undefined) {
      scopes.push('frame');
    }
    
    if (error.context?.workerId) {
      scopes.push('worker');
    }
    
    if (error.context?.gpuId) {
      scopes.push('gpu');
    }
    
    return scopes;
  };

  const availableScopes = getAvailableScopes();

  const handleRetry = async (scope: RetryScope) => {
    if (!onRetry || isRetrying) return;

    setIsRetrying(true);
    
    try {
      const config: RetryConfiguration = {
        scope,
        stage: scope === 'stage' ? error.stage : undefined,
        frameIndex: scope === 'frame' ? error.context?.frameIndex : undefined,
        options: retryOptions,
      };

      await onRetry(config);
    } catch (error) {
      console.error('Retry failed:', error);
    } finally {
      setIsRetrying(false);
    }
  };

  const getScopeIcon = (scope: RetryScope) => {
    switch (scope) {
      case 'full_analysis':
        return <ArrowPathIcon className={styles.scopeIcon} />;
      case 'stage':
        return <CogIcon className={styles.scopeIcon} />;
      case 'frame':
        return <FilmIcon className={styles.scopeIcon} />;
      case 'worker':
        return <CpuChipIcon className={styles.scopeIcon} />;
      case 'gpu':
        return <CpuChipIcon className={styles.scopeIcon} />;
      default:
        return <PlayIcon className={styles.scopeIcon} />;
    }
  };

  const getScopeDescription = (scope: RetryScope) => {
    switch (scope) {
      case 'full_analysis':
        return 'Restart the entire analysis from the beginning';
      case 'stage':
        return `Retry only the ${error.stage.replace(/_/g, ' ')} stage`;
      case 'frame':
        return `Retry processing for frame ${error.context?.frameIndex}`;
      case 'worker':
        return `Restart worker ${error.context?.workerId}`;
      case 'gpu':
        return `Restart GPU ${error.context?.gpuId}`;
      default:
        return 'Retry the failed operation';
    }
  };

  const getScopeEstimatedTime = (scope: RetryScope) => {
    switch (scope) {
      case 'full_analysis':
        return '5-10 minutes';
      case 'stage':
        return '1-3 minutes';
      case 'frame':
        return '30 seconds - 1 minute';
      case 'worker':
        return '1-2 minutes';
      case 'gpu':
        return '1-2 minutes';
      default:
        return 'Unknown';
    }
  };

  if (!canRetry) {
    return (
      <div className={`${styles.retryOptions} ${className}`}>
        <div className={styles.retryOptionsHeader}>
          <h3 className={styles.retryOptionsTitle}>Retry Options</h3>
        </div>
        <div className={styles.noPermissionMessage}>
          <ExclamationTriangleIcon className={styles.noPermissionIcon} />
          <p>You don't have permission to retry this analysis.</p>
        </div>
      </div>
    );
  }

  if (activeRetries.length > 0) {
    return (
      <div className={`${styles.retryOptions} ${className}`}>
        <div className={styles.retryOptionsHeader}>
          <h3 className={styles.retryOptionsTitle}>Retry Options</h3>
        </div>
        <div className={styles.activeRetryMessage}>
          <ClockIcon className={styles.activeRetryIcon} />
          <div>
            <p className={styles.activeRetryTitle}>Retry in Progress</p>
            <p className={styles.activeRetryDescription}>
              {activeRetries.length} retry attempt{activeRetries.length > 1 ? 's' : ''} currently in progress.
              Please wait for completion before initiating new retries.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.retryOptions} ${className}`}>
      <div className={styles.retryOptionsHeader}>
        <h3 className={styles.retryOptionsTitle}>Retry Options</h3>
        <p className={styles.retryOptionsDescription}>
          Choose how you want to retry the failed operation
        </p>
      </div>

      {/* Retry Scope Selection */}
      <div className={styles.retryScopeSection}>
        <h4 className={styles.retryScopeTitle}>Retry Scope</h4>
        <div className={styles.retryScopeGrid}>
          {availableScopes.map((scope) => (
            <div
              key={scope}
              className={`${styles.retryScopeCard} ${
                selectedScope === scope ? styles.retryScopeCardSelected : ''
              }`}
              onClick={() => setSelectedScope(scope)}
              role="button"
              tabIndex={0}
              aria-pressed={selectedScope === scope}
            >
              <div className={styles.retryScopeCardHeader}>
                {getScopeIcon(scope)}
                <h5 className={styles.retryScopeCardTitle}>
                  {scope.replace(/_/g, ' ').toUpperCase()}
                </h5>
              </div>
              
              <p className={styles.retryScopeCardDescription}>
                {getScopeDescription(scope)}
              </p>
              
              <div className={styles.retryScopeCardMeta}>
                <div className={styles.retryScopeCardMetaItem}>
                  <ClockIcon className={styles.retryScopeCardMetaIcon} />
                  <span className={styles.retryScopeCardMetaText}>
                    Est. {getScopeEstimatedTime(scope)}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Retry Options Configuration */}
      <div className={styles.retryOptionsConfig}>
        <h4 className={styles.retryOptionsConfigTitle}>Retry Configuration</h4>
        
        <div className={styles.retryOptionsConfigGrid}>
          <label className={styles.retryOptionsConfigItem}>
            <input
              type="checkbox"
              checked={retryOptions.skipCompletedStages}
              onChange={(e) => setRetryOptions(prev => ({
                ...prev,
                skipCompletedStages: e.target.checked
              }))}
              className={styles.retryOptionsConfigCheckbox}
            />
            <span className={styles.retryOptionsConfigLabel}>
              Skip completed stages
            </span>
            <span className={styles.retryOptionsConfigDescription}>
              Don't re-run stages that have already completed successfully
            </span>
          </label>

          <label className={styles.retryOptionsConfigItem}>
            <input
              type="checkbox"
              checked={retryOptions.useCachedResults}
              onChange={(e) => setRetryOptions(prev => ({
                ...prev,
                useCachedResults: e.target.checked
              }))}
              className={styles.retryOptionsConfigCheckbox}
            />
            <span className={styles.retryOptionsConfigLabel}>
              Use cached results
            </span>
            <span className={styles.retryOptionsConfigDescription}>
              Use previously computed results when available
            </span>
          </label>

          <label className={styles.retryOptionsConfigItem}>
            <input
              type="checkbox"
              checked={retryOptions.forceRestart}
              onChange={(e) => setRetryOptions(prev => ({
                ...prev,
                forceRestart: e.target.checked
              }))}
              className={styles.retryOptionsConfigCheckbox}
            />
            <span className={styles.retryOptionsConfigLabel}>
              Force restart
            </span>
            <span className={styles.retryOptionsConfigDescription}>
              Force restart even if resources are busy
            </span>
          </label>
        </div>

        <div className={styles.retryOptionsConfigItem}>
          <label className={styles.retryOptionsConfigLabel}>
            Timeout (seconds)
          </label>
          <input
            type="number"
            min="60"
            max="3600"
            step="60"
            value={retryOptions.timeout / 1000}
            onChange={(e) => setRetryOptions(prev => ({
              ...prev,
              timeout: parseInt(e.target.value) * 1000
            }))}
            className={styles.retryOptionsConfigInput}
          />
          <span className={styles.retryOptionsConfigDescription}>
            Maximum time to wait for retry completion
          </span>
        </div>
      </div>

      {/* Retry Actions */}
      <div className={styles.retryActions}>
        <button
          className={`${styles.retryButton} ${styles.retryButtonPrimary}`}
          onClick={() => handleRetry(selectedScope)}
          disabled={isRetrying || !error.recoverable}
          aria-label={`Retry ${selectedScope.replace(/_/g, ' ')}`}
        >
          {isRetrying ? (
            <>
              <div className={styles.retryButtonSpinner} />
              Retrying...
            </>
          ) : (
            <>
              <PlayIcon className={styles.retryButtonIcon} />
              Retry {selectedScope.replace(/_/g, ' ').toUpperCase()}
            </>
          )}
        </button>

        {!error.recoverable && (
          <div className={styles.unrecoverableMessage}>
            <ExclamationTriangleIcon className={styles.unrecoverableIcon} />
            <span>This error cannot be automatically recovered</span>
          </div>
        )}
      </div>

      {/* Retry History Summary */}
      {retryHistory.length > 0 && (
        <div className={styles.retryHistorySummary}>
          <h4 className={styles.retryHistorySummaryTitle}>Previous Retry Attempts</h4>
          <div className={styles.retryHistorySummaryStats}>
            <div className={styles.retryHistorySummaryStat}>
              <span className={styles.retryHistorySummaryStatValue}>
                {retryHistory.length}
              </span>
              <span className={styles.retryHistorySummaryStatLabel}>
                Total Attempts
              </span>
            </div>
            <div className={styles.retryHistorySummaryStat}>
              <span className={styles.retryHistorySummaryStatValue}>
                {retryHistory.filter(a => a.status === 'completed' && a.result?.success).length}
              </span>
              <span className={styles.retryHistorySummaryStatLabel}>
                Successful
              </span>
            </div>
            <div className={styles.retryHistorySummaryStat}>
              <span className={styles.retryHistorySummaryStatValue}>
                {retryHistory.filter(a => a.status === 'failed').length}
              </span>
              <span className={styles.retryHistorySummaryStatLabel}>
                Failed
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RetryOptions;
