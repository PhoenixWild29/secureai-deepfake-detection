import React, { useState, useEffect, useCallback } from 'react';
import { 
  ExclamationTriangleIcon,
  XMarkIcon,
  ArrowPathIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline';
import { 
  ErrorRecoveryInterfaceProps, 
  RetryConfiguration, 
  TroubleshootingStep,
  ErrorLogEntry,
  RetryAttempt
} from '@/types/errorRecovery';
import { errorRecoveryService } from '@/services/errorRecoveryService';
import ErrorDetails from './ErrorDetails';
import RetryOptions from './RetryOptions';
import ErrorLogViewer from './ErrorLogViewer';
import TroubleshootingGuide from './TroubleshootingGuide';
import RetryHistory from './RetryHistory';
import styles from './ErrorRecoveryInterface.module.css';

/**
 * ErrorRecoveryInterface component
 * Main component for error recovery interface with manual retry capabilities
 */
export const ErrorRecoveryInterface: React.FC<ErrorRecoveryInterfaceProps> = ({
  error,
  analysisId,
  userRole,
  retryHistory: initialRetryHistory = [],
  errorLogs: initialErrorLogs = [],
  showDetails = true,
  showRetryOptions = true,
  showTroubleshooting = true,
  showRetryHistory = true,
  onRetry,
  onDismiss,
  onTroubleshootingComplete,
  className = '',
}) => {
  const [retryHistory, setRetryHistory] = useState<RetryAttempt[]>(initialRetryHistory);
  const [errorLogs, setErrorLogs] = useState<ErrorLogEntry[]>(initialErrorLogs);
  const [troubleshootingSteps, setTroubleshootingSteps] = useState<TroubleshootingStep[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorState, setErrorState] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'details' | 'retry' | 'logs' | 'troubleshooting' | 'history'>('details');

  // Load troubleshooting steps for the error type
  useEffect(() => {
    const loadTroubleshootingSteps = async () => {
      try {
        const steps = await errorRecoveryService.getTroubleshootingSteps(error.type);
        setTroubleshootingSteps(steps);
      } catch (err) {
        console.error('Failed to load troubleshooting steps:', err);
        setErrorState('Failed to load troubleshooting steps');
      }
    };

    if (showTroubleshooting) {
      loadTroubleshootingSteps();
    }
  }, [error.type, showTroubleshooting]);

  // Load retry history if not provided
  useEffect(() => {
    const loadRetryHistory = async () => {
      if (initialRetryHistory.length === 0 && showRetryHistory) {
        try {
          setIsLoading(true);
          const history = await errorRecoveryService.getRetryHistory(analysisId);
          setRetryHistory(history);
        } catch (err) {
          console.error('Failed to load retry history:', err);
          setErrorState('Failed to load retry history');
        } finally {
          setIsLoading(false);
        }
      }
    };

    loadRetryHistory();
  }, [analysisId, initialRetryHistory.length, showRetryHistory]);

  // Load error logs if not provided
  useEffect(() => {
    const loadErrorLogs = async () => {
      if (initialErrorLogs.length === 0) {
        try {
          setIsLoading(true);
          const logs = await errorRecoveryService.getErrorLogs(analysisId, error.id);
          setErrorLogs(logs);
        } catch (err) {
          console.error('Failed to load error logs:', err);
          setErrorState('Failed to load error logs');
        } finally {
          setIsLoading(false);
        }
      }
    };

    loadErrorLogs();
  }, [analysisId, error.id, initialErrorLogs.length]);

  // Handle retry initiation
  const handleRetry = useCallback(async (config: RetryConfiguration) => {
    if (!onRetry) {
      try {
        setIsLoading(true);
        setErrorState(null);

        const response = await errorRecoveryService.initiateRetry({
          analysisId,
          configuration: config,
          userId: userRole?.id,
        });

        // Add the new retry attempt to history
        const newAttempt: RetryAttempt = {
          id: response.retryId,
          attemptNumber: retryHistory.length + 1,
          scope: config.scope,
          timestamp: new Date(),
          status: 'pending',
          initiatedBy: userRole?.id,
          configuration: config,
        };

        setRetryHistory(prev => [newAttempt, ...prev]);

        // Switch to retry history tab to show the new attempt
        setActiveTab('history');

      } catch (err) {
        console.error('Retry failed:', err);
        setErrorState(err instanceof Error ? err.message : 'Failed to initiate retry');
      } finally {
        setIsLoading(false);
      }
    } else {
      // Use custom retry handler
      try {
        await onRetry(config);
      } catch (err) {
        console.error('Custom retry failed:', err);
        setErrorState(err instanceof Error ? err.message : 'Retry failed');
      }
    }
  }, [analysisId, userRole?.id, retryHistory.length, onRetry]);

  // Handle troubleshooting step completion
  const handleTroubleshootingComplete = useCallback(async (stepId: string) => {
    try {
      await errorRecoveryService.completeTroubleshootingStep(stepId, analysisId, userRole?.id);
      
      if (onTroubleshootingComplete) {
        onTroubleshootingComplete(stepId);
      }
    } catch (err) {
      console.error('Failed to complete troubleshooting step:', err);
      setErrorState('Failed to mark troubleshooting step as completed');
    }
  }, [analysisId, userRole?.id, onTroubleshootingComplete]);

  // Handle error dismissal
  const handleDismiss = useCallback(async () => {
    try {
      await errorRecoveryService.dismissError(error.id, userRole?.id);
      
      if (onDismiss) {
        onDismiss();
      }
    } catch (err) {
      console.error('Failed to dismiss error:', err);
      setErrorState('Failed to dismiss error');
    }
  }, [error.id, userRole?.id, onDismiss]);

  // Get tab configuration
  const tabs = [
    { id: 'details', label: 'Error Details', icon: InformationCircleIcon, show: showDetails },
    { id: 'retry', label: 'Retry Options', icon: ArrowPathIcon, show: showRetryOptions },
    { id: 'logs', label: 'Error Logs', icon: ExclamationTriangleIcon, show: errorLogs.length > 0 },
    { id: 'troubleshooting', label: 'Troubleshooting', icon: InformationCircleIcon, show: showTroubleshooting && troubleshootingSteps.length > 0 },
    { id: 'history', label: 'Retry History', icon: ArrowPathIcon, show: showRetryHistory },
  ].filter(tab => tab.show);

  const activeTabConfig = tabs.find(tab => tab.id === activeTab) || tabs[0];

  return (
    <div className={`${styles.errorRecoveryInterface} ${className}`}>
      {/* Header */}
      <div className={styles.errorRecoveryInterfaceHeader}>
        <div className={styles.errorRecoveryInterfaceTitle}>
          <ExclamationTriangleIcon className={styles.errorRecoveryInterfaceIcon} />
          <h2 className={styles.errorRecoveryInterfaceTitleText}>Error Recovery</h2>
        </div>

        <div className={styles.errorRecoveryInterfaceActions}>
          {onDismiss && (
            <button
              className={styles.errorRecoveryInterfaceDismissButton}
              onClick={handleDismiss}
              aria-label="Dismiss error"
            >
              <XMarkIcon className={styles.errorRecoveryInterfaceDismissIcon} />
              Dismiss
            </button>
          )}
        </div>
      </div>

      {/* Error State */}
      {errorState && (
        <div className={styles.errorRecoveryInterfaceError}>
          <ExclamationTriangleIcon className={styles.errorRecoveryInterfaceErrorIcon} />
          <p className={styles.errorRecoveryInterfaceErrorMessage}>{errorState}</p>
          <button
            className={styles.errorRecoveryInterfaceErrorDismiss}
            onClick={() => setErrorState(null)}
            aria-label="Dismiss error message"
          >
            <XMarkIcon className={styles.errorRecoveryInterfaceErrorDismissIcon} />
          </button>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className={styles.errorRecoveryInterfaceLoading}>
          <div className={styles.errorRecoveryInterfaceLoadingSpinner} />
          <p className={styles.errorRecoveryInterfaceLoadingText}>Loading...</p>
        </div>
      )}

      {/* Tabs */}
      {tabs.length > 1 && (
        <div className={styles.errorRecoveryInterfaceTabs}>
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                className={`${styles.errorRecoveryInterfaceTab} ${
                  activeTab === tab.id ? styles.errorRecoveryInterfaceTabActive : ''
                }`}
                onClick={() => setActiveTab(tab.id as any)}
                aria-pressed={activeTab === tab.id}
              >
                <Icon className={styles.errorRecoveryInterfaceTabIcon} />
                <span className={styles.errorRecoveryInterfaceTabLabel}>{tab.label}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Tab Content */}
      <div className={styles.errorRecoveryInterfaceContent}>
        {activeTab === 'details' && (
          <ErrorDetails
            error={error}
            showDetails={showDetails}
            className={styles.errorRecoveryInterfaceTabContent}
          />
        )}

        {activeTab === 'retry' && (
          <RetryOptions
            error={error}
            analysisId={analysisId}
            userRole={userRole}
            retryHistory={retryHistory}
            onRetry={handleRetry}
            className={styles.errorRecoveryInterfaceTabContent}
          />
        )}

        {activeTab === 'logs' && (
          <ErrorLogViewer
            errorLogs={errorLogs}
            showStackTraces={true}
            showDetailedData={true}
            className={styles.errorRecoveryInterfaceTabContent}
          />
        )}

        {activeTab === 'troubleshooting' && (
          <TroubleshootingGuide
            error={error}
            steps={troubleshootingSteps}
            onStepComplete={handleTroubleshootingComplete}
            className={styles.errorRecoveryInterfaceTabContent}
          />
        )}

        {activeTab === 'history' && (
          <RetryHistory
            retryHistory={retryHistory}
            showDetails={true}
            className={styles.errorRecoveryInterfaceTabContent}
          />
        )}
      </div>

      {/* Footer */}
      <div className={styles.errorRecoveryInterfaceFooter}>
        <div className={styles.errorRecoveryInterfaceFooterInfo}>
          <span className={styles.errorRecoveryInterfaceFooterLabel}>Analysis ID:</span>
          <span className={styles.errorRecoveryInterfaceFooterValue}>{analysisId}</span>
        </div>
        
        <div className={styles.errorRecoveryInterfaceFooterInfo}>
          <span className={styles.errorRecoveryInterfaceFooterLabel}>Error ID:</span>
          <span className={styles.errorRecoveryInterfaceFooterValue}>{error.id}</span>
        </div>

        {userRole && (
          <div className={styles.errorRecoveryInterfaceFooterInfo}>
            <span className={styles.errorRecoveryInterfaceFooterLabel}>User Role:</span>
            <span className={styles.errorRecoveryInterfaceFooterValue}>{userRole.name}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default ErrorRecoveryInterface;
