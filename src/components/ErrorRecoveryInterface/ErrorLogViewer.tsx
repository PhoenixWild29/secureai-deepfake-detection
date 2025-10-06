import React, { useState, useMemo } from 'react';
import { 
  DocumentTextIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  CodeBracketIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XCircleIcon
} from '@heroicons/react/24/outline';
import { ErrorLogViewerProps, ErrorLogEntry, LogLevel } from '@/types/errorRecovery';
import styles from './ErrorRecoveryInterface.module.css';

/**
 * ErrorLogViewer component
 * Visualizes error logs with expandable details and stack traces
 */
export const ErrorLogViewer: React.FC<ErrorLogViewerProps> = ({
  errorLogs,
  showStackTraces = true,
  showDetailedData = true,
  className = '',
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLevel, setSelectedLevel] = useState<LogLevel | 'all'>('all');
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Filter and sort logs
  const filteredLogs = useMemo(() => {
    let filtered = errorLogs.filter(log => {
      const matchesSearch = log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           log.source.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesLevel = selectedLevel === 'all' || log.level === selectedLevel;
      return matchesSearch && matchesLevel;
    });

    // Sort by timestamp
    filtered.sort((a, b) => {
      const comparison = a.timestamp.getTime() - b.timestamp.getTime();
      return sortOrder === 'asc' ? comparison : -comparison;
    });

    return filtered;
  }, [errorLogs, searchTerm, selectedLevel, sortOrder]);

  const getLogLevelIcon = (level: LogLevel) => {
    switch (level) {
      case 'critical':
        return <XCircleIcon className={styles.logLevelIconCritical} />;
      case 'error':
        return <ExclamationTriangleIcon className={styles.logLevelIconError} />;
      case 'warning':
        return <ExclamationTriangleIcon className={styles.logLevelIconWarning} />;
      case 'info':
        return <InformationCircleIcon className={styles.logLevelIconInfo} />;
      case 'debug':
        return <CodeBracketIcon className={styles.logLevelIconDebug} />;
      default:
        return <InformationCircleIcon className={styles.logLevelIconInfo} />;
    }
  };

  const getLogLevelColor = (level: LogLevel) => {
    switch (level) {
      case 'critical':
        return styles.logLevelCritical;
      case 'error':
        return styles.logLevelError;
      case 'warning':
        return styles.logLevelWarning;
      case 'info':
        return styles.logLevelInfo;
      case 'debug':
        return styles.logLevelDebug;
      default:
        return styles.logLevelInfo;
    }
  };

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
    });
  };

  const toggleLogExpansion = (logId: string) => {
    setExpandedLogs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(logId)) {
        newSet.delete(logId);
      } else {
        newSet.add(logId);
      }
      return newSet;
    });
  };

  const expandAllLogs = () => {
    setExpandedLogs(new Set(filteredLogs.map(log => log.id)));
  };

  const collapseAllLogs = () => {
    setExpandedLogs(new Set());
  };

  const logLevels: LogLevel[] = ['critical', 'error', 'warning', 'info', 'debug'];

  return (
    <div className={`${styles.errorLogViewer} ${className}`}>
      {/* Header */}
      <div className={styles.errorLogViewerHeader}>
        <div className={styles.errorLogViewerTitle}>
          <DocumentTextIcon className={styles.errorLogViewerIcon} />
          <h3 className={styles.errorLogViewerTitleText}>Error Logs</h3>
          <span className={styles.errorLogViewerCount}>
            {filteredLogs.length} of {errorLogs.length} logs
          </span>
        </div>

        <div className={styles.errorLogViewerActions}>
          <button
            className={styles.errorLogViewerActionButton}
            onClick={expandAllLogs}
            aria-label="Expand all logs"
          >
            Expand All
          </button>
          <button
            className={styles.errorLogViewerActionButton}
            onClick={collapseAllLogs}
            aria-label="Collapse all logs"
          >
            Collapse All
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className={styles.errorLogViewerFilters}>
        {/* Search */}
        <div className={styles.errorLogViewerSearch}>
          <MagnifyingGlassIcon className={styles.errorLogViewerSearchIcon} />
          <input
            type="text"
            placeholder="Search logs..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className={styles.errorLogViewerSearchInput}
          />
        </div>

        {/* Level Filter */}
        <div className={styles.errorLogViewerLevelFilter}>
          <FunnelIcon className={styles.errorLogViewerFilterIcon} />
          <select
            value={selectedLevel}
            onChange={(e) => setSelectedLevel(e.target.value as LogLevel | 'all')}
            className={styles.errorLogViewerLevelSelect}
          >
            <option value="all">All Levels</option>
            {logLevels.map(level => (
              <option key={level} value={level}>
                {level.toUpperCase()}
              </option>
            ))}
          </select>
        </div>

        {/* Sort Order */}
        <div className={styles.errorLogViewerSort}>
          <button
            className={`${styles.errorLogViewerSortButton} ${
              sortOrder === 'desc' ? styles.errorLogViewerSortButtonActive : ''
            }`}
            onClick={() => setSortOrder('desc')}
            aria-pressed={sortOrder === 'desc'}
          >
            Newest First
          </button>
          <button
            className={`${styles.errorLogViewerSortButton} ${
              sortOrder === 'asc' ? styles.errorLogViewerSortButtonActive : ''
            }`}
            onClick={() => setSortOrder('asc')}
            aria-pressed={sortOrder === 'asc'}
          >
            Oldest First
          </button>
        </div>
      </div>

      {/* Logs List */}
      <div className={styles.errorLogViewerList}>
        {filteredLogs.length === 0 ? (
          <div className={styles.errorLogViewerEmpty}>
            <DocumentTextIcon className={styles.errorLogViewerEmptyIcon} />
            <p className={styles.errorLogViewerEmptyText}>
              {searchTerm || selectedLevel !== 'all' 
                ? 'No logs match your filters' 
                : 'No error logs available'
              }
            </p>
          </div>
        ) : (
          filteredLogs.map((log) => {
            const isExpanded = expandedLogs.has(log.id);
            const hasDetails = showDetailedData && (log.data || log.stackTrace);

            return (
              <div key={log.id} className={styles.errorLogEntry}>
                {/* Log Header */}
                <div 
                  className={`${styles.errorLogEntryHeader} ${
                    hasDetails ? styles.errorLogEntryHeaderExpandable : ''
                  }`}
                  onClick={hasDetails ? () => toggleLogExpansion(log.id) : undefined}
                  role={hasDetails ? 'button' : undefined}
                  tabIndex={hasDetails ? 0 : undefined}
                  aria-expanded={hasDetails ? isExpanded : undefined}
                >
                  <div className={styles.errorLogEntryMain}>
                    <div className={styles.errorLogEntryLevel}>
                      {getLogLevelIcon(log.level)}
                      <span className={`${styles.errorLogEntryLevelText} ${getLogLevelColor(log.level)}`}>
                        {log.level.toUpperCase()}
                      </span>
                    </div>

                    <div className={styles.errorLogEntryContent}>
                      <p className={styles.errorLogEntryMessage}>{log.message}</p>
                      <div className={styles.errorLogEntryMeta}>
                        <div className={styles.errorLogEntryMetaItem}>
                          <ClockIcon className={styles.errorLogEntryMetaIcon} />
                          <span className={styles.errorLogEntryMetaText}>
                            {formatTimestamp(log.timestamp)}
                          </span>
                        </div>
                        <div className={styles.errorLogEntryMetaItem}>
                          <span className={styles.errorLogEntryMetaLabel}>Source:</span>
                          <span className={styles.errorLogEntryMetaText}>{log.source}</span>
                        </div>
                        {log.errorId && (
                          <div className={styles.errorLogEntryMetaItem}>
                            <span className={styles.errorLogEntryMetaLabel}>Error ID:</span>
                            <span className={styles.errorLogEntryMetaText}>{log.errorId}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {hasDetails && (
                    <div className={styles.errorLogEntryExpand}>
                      {isExpanded ? (
                        <ChevronDownIcon className={styles.errorLogEntryExpandIcon} />
                      ) : (
                        <ChevronRightIcon className={styles.errorLogEntryExpandIcon} />
                      )}
                    </div>
                  )}
                </div>

                {/* Log Details */}
                {isExpanded && hasDetails && (
                  <div className={styles.errorLogEntryDetails}>
                    {/* Log Data */}
                    {log.data && Object.keys(log.data).length > 0 && (
                      <div className={styles.errorLogEntryData}>
                        <h5 className={styles.errorLogEntryDataTitle}>Additional Data</h5>
                        <div className={styles.errorLogEntryDataContent}>
                          <pre className={styles.errorLogEntryDataPre}>
                            {JSON.stringify(log.data, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}

                    {/* Stack Trace */}
                    {showStackTraces && log.stackTrace && (
                      <div className={styles.errorLogEntryStackTrace}>
                        <h5 className={styles.errorLogEntryStackTraceTitle}>Stack Trace</h5>
                        <div className={styles.errorLogEntryStackTraceContent}>
                          <pre className={styles.errorLogEntryStackTracePre}>
                            {log.stackTrace}
                          </pre>
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

      {/* Log Statistics */}
      {errorLogs.length > 0 && (
        <div className={styles.errorLogViewerStats}>
          <h4 className={styles.errorLogViewerStatsTitle}>Log Statistics</h4>
          <div className={styles.errorLogViewerStatsGrid}>
            {logLevels.map(level => {
              const count = errorLogs.filter(log => log.level === level).length;
              return (
                <div key={level} className={styles.errorLogViewerStat}>
                  <span className={`${styles.errorLogViewerStatValue} ${getLogLevelColor(level)}`}>
                    {count}
                  </span>
                  <span className={styles.errorLogViewerStatLabel}>
                    {level.toUpperCase()}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default ErrorLogViewer;
