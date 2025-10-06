/**
 * ResultExportInterface Component
 * Work Order #39 - Multi-Format Export Capabilities
 * 
 * Comprehensive export functionality that allows users to generate and download
 * detection results in multiple formats for stakeholder sharing, compliance
 * documentation, and external analysis.
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { ExportProgressIndicator } from '../ExportProgressIndicator/ExportProgressIndicator';
import { ExportFormatPreview } from '../ExportFormatPreview/ExportFormatPreview';
import { exportService } from '../../services/exportService';
import { useAuth } from '../../hooks/useAuth';
import { useWebSocket } from '../../hooks/useWebSocket';
import styles from './ResultExportInterface.module.css';

// ============================================================================
// Constants and Configuration
// ============================================================================

/**
 * Supported export formats with their configurations
 */
export const EXPORT_FORMATS = {
  PDF: {
    id: 'pdf',
    name: 'PDF Report',
    description: 'Professional report with formatted detection results and blockchain verification',
    icon: '📄',
    mimeType: 'application/pdf',
    extension: '.pdf',
    supportsBatch: true,
    requiresPreview: true
  },
  JSON: {
    id: 'json',
    name: 'JSON Data',
    description: 'Complete detection result data structure with all metadata',
    icon: '📋',
    mimeType: 'application/json',
    extension: '.json',
    supportsBatch: true,
    requiresPreview: false
  },
  CSV: {
    id: 'csv',
    name: 'CSV Summary',
    description: 'Tabular data suitable for spreadsheet analysis and database import',
    icon: '📊',
    mimeType: 'text/csv',
    extension: '.csv',
    supportsBatch: true,
    requiresPreview: false
  }
};

/**
 * Export configuration options
 */
const EXPORT_OPTIONS = {
  includeFrameAnalysis: {
    label: 'Include Frame Analysis Data',
    description: 'Add detailed frame-by-frame analysis results',
    default: true
  },
  includeBlockchainVerification: {
    label: 'Include Blockchain Verification',
    description: 'Add blockchain verification certificates and audit trail',
    default: true
  },
  includeProcessingMetrics: {
    label: 'Include Processing Metrics',
    description: 'Add performance metrics and processing statistics',
    default: false
  },
  includeSuspiciousRegions: {
    label: 'Include Suspicious Regions',
    description: 'Add detected suspicious region coordinates and details',
    default: false
  }
};

/**
 * Permission levels for export access
 */
const PERMISSION_LEVELS = {
  BASIC: 'basic',
  STANDARD: 'standard',
  PREMIUM: 'premium',
  ADMIN: 'admin'
};

// ============================================================================
// Main Component
// ============================================================================

/**
 * ResultExportInterface - Main export interface component
 * 
 * @param {Object} props - Component properties
 * @param {string|Array} props.analysisIds - Single analysis ID or array of IDs for batch export
 * @param {Object} props.detectionData - Detection result data (for single analysis)
 * @param {Array} props.detectionDataArray - Array of detection results (for batch export)
 * @param {boolean} props.showBatchOptions - Whether to show batch export options
 * @param {Function} props.onExportComplete - Callback when export is completed
 * @param {Function} props.onExportError - Callback when export fails
 * @returns {JSX.Element} ResultExportInterface component
 */
const ResultExportInterface = ({
  analysisIds,
  detectionData,
  detectionDataArray,
  showBatchOptions = false,
  onExportComplete,
  onExportError
}) => {
  
  // ============================================================================
  // State Management
  // ============================================================================
  
  const [selectedFormat, setSelectedFormat] = useState(EXPORT_FORMATS.PDF.id);
  const [exportOptions, setExportOptions] = useState(() => {
    const options = {};
    Object.keys(EXPORT_OPTIONS).forEach(key => {
      options[key] = EXPORT_OPTIONS[key].default;
    });
    return options;
  });
  
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(null);
  const [exportHistory, setExportHistory] = useState([]);
  const [showPreview, setShowPreview] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [permissions, setPermissions] = useState(null);
  const [error, setError] = useState(null);
  
  // Hooks
  const { user, hasPermission } = useAuth();
  const { subscribe, unsubscribe } = useWebSocket();
  
  // ============================================================================
  // Computed Values
  // ============================================================================
  
  const isBatchExport = useMemo(() => {
    return Array.isArray(analysisIds) && analysisIds.length > 1;
  }, [analysisIds]);
  
  const selectedFormatConfig = useMemo(() => {
    return EXPORT_FORMATS[selectedFormat.toUpperCase()];
  }, [selectedFormat]);
  
  const canExport = useMemo(() => {
    if (!user || !permissions) return false;
    if (isBatchExport && !selectedFormatConfig.supportsBatch) return false;
    return hasPermission('export', selectedFormat);
  }, [user, permissions, isBatchExport, selectedFormatConfig, hasPermission]);
  
  const exportData = useMemo(() => {
    if (isBatchExport) {
      return detectionDataArray || [];
    }
    return detectionData ? [detectionData] : [];
  }, [isBatchExport, detectionData, detectionDataArray]);
  
  // ============================================================================
  // Effects
  // ============================================================================
  
  useEffect(() => {
    // Load user permissions and export history
    loadUserPermissions();
    loadExportHistory();
    
    // Subscribe to export progress updates
    const handleExportProgress = (data) => {
      if (data.type === 'export_progress') {
        setExportProgress(data.progress);
      }
    };
    
    subscribe('export_updates', handleExportProgress);
    
    return () => {
      unsubscribe('export_updates', handleExportProgress);
    };
  }, [subscribe, unsubscribe]);
  
  useEffect(() => {
    // Reset preview when format changes
    setShowPreview(false);
    setPreviewData(null);
  }, [selectedFormat]);
  
  // ============================================================================
  // Event Handlers
  // ============================================================================
  
  const handleFormatChange = useCallback((format) => {
    setSelectedFormat(format);
    setError(null);
  }, []);
  
  const handleOptionChange = useCallback((option, value) => {
    setExportOptions(prev => ({
      ...prev,
      [option]: value
    }));
  }, []);
  
  const handlePreviewRequest = useCallback(async () => {
    try {
      setError(null);
      const preview = await exportService.generatePreview({
        format: selectedFormat,
        analysisIds: isBatchExport ? analysisIds : [analysisIds],
        options: exportOptions
      });
      
      setPreviewData(preview);
      setShowPreview(true);
    } catch (err) {
      setError(`Preview generation failed: ${err.message}`);
    }
  }, [selectedFormat, analysisIds, exportOptions, isBatchExport]);
  
  const handleExportInitiate = useCallback(async () => {
    try {
      setIsExporting(true);
      setError(null);
      setExportProgress({
        status: 'initiating',
        progress: 0,
        message: 'Preparing export...'
      });
      
      const exportRequest = {
        format: selectedFormat,
        analysisIds: isBatchExport ? analysisIds : [analysisIds],
        options: exportOptions,
        userId: user.id,
        permissions: permissions
      };
      
      const exportJob = await exportService.initiateExport(exportRequest);
      
      // Track export progress
      setExportProgress({
        status: 'processing',
        progress: 10,
        message: 'Export initiated successfully',
        exportId: exportJob.exportId,
        estimatedCompletion: exportJob.estimatedCompletion
      });
      
      // Add to history
      setExportHistory(prev => [exportJob, ...prev]);
      
    } catch (err) {
      setError(`Export initiation failed: ${err.message}`);
      setIsExporting(false);
      setExportProgress(null);
      onExportError?.(err);
    }
  }, [
    selectedFormat, 
    analysisIds, 
    exportOptions, 
    isBatchExport, 
    user, 
    permissions, 
    onExportError
  ]);
  
  const handleExportComplete = useCallback((exportResult) => {
    setIsExporting(false);
    setExportProgress(null);
    setExportHistory(prev => prev.map(item => 
      item.exportId === exportResult.exportId 
        ? { ...item, ...exportResult, status: 'completed' }
        : item
    ));
    onExportComplete?.(exportResult);
  }, [onExportComplete]);
  
  const handleExportError = useCallback((exportError) => {
    setIsExporting(false);
    setExportProgress(null);
    setError(`Export failed: ${exportError.message}`);
    onExportError?.(exportError);
  }, [onExportError]);
  
  // ============================================================================
  // Helper Functions
  // ============================================================================
  
  const loadUserPermissions = async () => {
    try {
      const userPermissions = await exportService.getUserPermissions(user.id);
      setPermissions(userPermissions);
    } catch (err) {
      console.error('Failed to load user permissions:', err);
    }
  };
  
  const loadExportHistory = async () => {
    try {
      const history = await exportService.getExportHistory(user.id);
      setExportHistory(history);
    } catch (err) {
      console.error('Failed to load export history:', err);
    }
  };
  
  // ============================================================================
  // Render Functions
  // ============================================================================
  
  const renderFormatSelection = () => (
    <div className={styles.formatSelection}>
      <h3>Export Format</h3>
      <div className={styles.formatGrid}>
        {Object.values(EXPORT_FORMATS).map(format => (
          <div
            key={format.id}
            className={`${styles.formatOption} ${
              selectedFormat === format.id ? styles.formatOptionSelected : ''
            }`}
            onClick={() => handleFormatChange(format.id)}
          >
            <div className={styles.formatIcon}>{format.icon}</div>
            <div className={styles.formatInfo}>
              <h4>{format.name}</h4>
              <p>{format.description}</p>
              {isBatchExport && !format.supportsBatch && (
                <span className={styles.unsupportedBadge}>Batch not supported</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
  
  const renderExportOptions = () => (
    <div className={styles.exportOptions}>
      <h3>Export Options</h3>
      <div className={styles.optionsGrid}>
        {Object.entries(EXPORT_OPTIONS).map(([key, option]) => (
          <label key={key} className={styles.optionItem}>
            <input
              type="checkbox"
              checked={exportOptions[key]}
              onChange={(e) => handleOptionChange(key, e.target.checked)}
              className={styles.optionCheckbox}
            />
            <div className={styles.optionContent}>
              <span className={styles.optionLabel}>{option.label}</span>
              <span className={styles.optionDescription}>{option.description}</span>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
  
  const renderBatchInfo = () => {
    if (!isBatchExport) return null;
    
    return (
      <div className={styles.batchInfo}>
        <h3>Batch Export Information</h3>
        <div className={styles.batchStats}>
          <div className={styles.batchStat}>
            <span className={styles.batchStatLabel}>Analyses:</span>
            <span className={styles.batchStatValue}>{analysisIds.length}</span>
          </div>
          <div className={styles.batchStat}>
            <span className={styles.batchStatLabel}>Format:</span>
            <span className={styles.batchStatValue}>{selectedFormatConfig.name}</span>
          </div>
          <div className={styles.batchStat}>
            <span className={styles.batchStatLabel}>Estimated Size:</span>
            <span className={styles.batchStatValue}>~{Math.ceil(analysisIds.length * 2.5)}MB</span>
          </div>
        </div>
      </div>
    );
  };
  
  const renderActionButtons = () => (
    <div className={styles.actionButtons}>
      {selectedFormatConfig.requiresPreview && (
        <button
          onClick={handlePreviewRequest}
          disabled={isExporting}
          className={styles.previewButton}
        >
          Preview {selectedFormatConfig.name}
        </button>
      )}
      
      <button
        onClick={handleExportInitiate}
        disabled={!canExport || isExporting || exportData.length === 0}
        className={styles.exportButton}
      >
        {isExporting ? 'Exporting...' : `Export ${selectedFormatConfig.name}`}
      </button>
    </div>
  );
  
  const renderError = () => {
    if (!error) return null;
    
    return (
      <div className={styles.errorMessage}>
        <div className={styles.errorIcon}>⚠️</div>
        <div className={styles.errorContent}>
          <h4>Export Error</h4>
          <p>{error}</p>
        </div>
      </div>
    );
  };
  
  // ============================================================================
  // Main Render
  // ============================================================================
  
  return (
    <div className={styles.resultExportInterface}>
      <div className={styles.exportHeader}>
        <h2>Export Detection Results</h2>
        <p>Generate and download detection results in multiple formats for sharing and analysis</p>
      </div>
      
      <div className={styles.exportContent}>
        <div className={styles.exportConfiguration}>
          {renderFormatSelection()}
          {renderExportOptions()}
          {renderBatchInfo()}
          {renderActionButtons()}
          {renderError()}
        </div>
        
        <div className={styles.exportSidebar}>
          {isExporting && exportProgress && (
            <ExportProgressIndicator
              progress={exportProgress}
              onComplete={handleExportComplete}
              onError={handleExportError}
            />
          )}
          
          {showPreview && previewData && (
            <ExportFormatPreview
              format={selectedFormat}
              data={previewData}
              onClose={() => setShowPreview(false)}
            />
          )}
          
          {exportHistory.length > 0 && (
            <div className={styles.exportHistory}>
              <h3>Recent Exports</h3>
              <div className={styles.historyList}>
                {exportHistory.slice(0, 5).map(item => (
                  <div key={item.exportId} className={styles.historyItem}>
                    <div className={styles.historyInfo}>
                      <span className={styles.historyFormat}>{item.format.toUpperCase()}</span>
                      <span className={styles.historyDate}>
                        {new Date(item.createdAt).toLocaleDateString()}
                      </span>
                    </div>
                    <div className={`${styles.historyStatus} ${styles[item.status]}`}>
                      {item.status}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export { ResultExportInterface };
export default ResultExportInterface;
