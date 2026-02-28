/**
 * BlockchainVerificationPanel Component
 * Real-time blockchain verification status display with audit trails and compliance documentation
 * 
 * This component provides comprehensive blockchain verification information including:
 * - Real-time verification status with visual indicators
 * - Complete audit trail with timestamps and verification hashes
 * - Compliance documentation links based on verification status
 * - Role-based access control for sensitive information
 * - WebSocket integration for real-time updates
 * - Verification failure details with recommended actions
 * - Local timezone timestamp display
 * - Verification certificate download functionality
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useWebSocketEvents } from '../hooks/useWebSocketEvents';
import { blockchainVerificationService } from '../services/blockchainVerificationService';
import { authUtils } from '../utils/authUtils';
import { dateUtils } from '../utils/dateUtils';
import styles from './BlockchainVerificationPanel.module.css';

// ============================================================================
// Constants and Enums
// ============================================================================

/**
 * Verification status enumeration
 */
export const VERIFICATION_STATUS = {
  PENDING: 'pending',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  FAILED: 'failed',
  EXPIRED: 'expired',
  REVOKED: 'revoked'
};

/**
 * Verification priority levels
 */
export const VERIFICATION_PRIORITY = {
  LOW: 'low',
  NORMAL: 'normal',
  HIGH: 'high',
  CRITICAL: 'critical'
};

/**
 * Compliance document types
 */
export const COMPLIANCE_DOC_TYPES = {
  AUDIT_REPORT: 'audit_report',
  VERIFICATION_CERTIFICATE: 'verification_certificate',
  COMPLIANCE_SUMMARY: 'compliance_summary',
  REGULATORY_DOCUMENT: 'regulatory_document',
  TECHNICAL_SPECIFICATION: 'technical_specification'
};

/**
 * Default configuration
 */
const DEFAULT_CONFIG = {
  // Display settings
  showAuditTrail: true,
  showComplianceDocs: true,
  showTechnicalDetails: false,
  showErrorDetails: true,
  
  // Update settings
  refreshInterval: 5000, // 5 seconds
  maxRetries: 3,
  retryDelay: 1000, // 1 second
  
  // UI settings
  compactMode: false,
  showTimestamps: true,
  timezone: 'local',
  
  // Access control
  requireAuthentication: true,
  hideSensitiveData: true
};

// ============================================================================
// Main Component
// ============================================================================

/**
 * BlockchainVerificationPanel - Real-time blockchain verification status display
 * 
 * @param {Object} props - Component properties
 * @param {string} props.analysisId - Analysis identifier for verification data
 * @param {string} props.blockchainHash - Blockchain transaction hash
 * @param {Object} props.config - Configuration options to override defaults
 * @param {Function} props.onVerificationUpdate - Callback when verification status updates
 * @param {Function} props.onError - Callback for error handling
 * @param {Function} props.onCertificateDownload - Callback for certificate download
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Blockchain verification panel component
 */
const BlockchainVerificationPanel = ({
  analysisId,
  blockchainHash,
  config = {},
  onVerificationUpdate,
  onError,
  onCertificateDownload,
  className = ''
}) => {
  
  // ============================================================================
  // Configuration and State
  // ============================================================================
  
  const mergedConfig = useMemo(() => ({
    ...DEFAULT_CONFIG,
    ...config
  }), [config]);

  // Verification state
  const [verificationData, setVerificationData] = useState(null);
  const [verificationStatus, setVerificationStatus] = useState(VERIFICATION_STATUS.PENDING);
  const [auditTrail, setAuditTrail] = useState([]);
  const [complianceDocs, setComplianceDocs] = useState([]);
  const [errorDetails, setErrorDetails] = useState(null);
  
  // UI state
  const [loading, setLoading] = useState(true);
  const [expandedSections, setExpandedSections] = useState({
    auditTrail: true,
    complianceDocs: false,
    technicalDetails: false,
    errorDetails: false
  });
  
  // User permissions
  const [userPermissions, setUserPermissions] = useState(null);
  const [canViewSensitiveData, setCanViewSensitiveData] = useState(false);
  
  // Refs
  const refreshIntervalRef = useRef(null);
  const retryCountRef = useRef(0);
  const lastUpdateRef = useRef(null);

  // ============================================================================
  // WebSocket Integration
  // ============================================================================

  /**
   * Handle WebSocket events for real-time updates
   */
  const handleWebSocketEvent = useCallback((event) => {
    try {
      const { type, data } = event;
      
      switch (type) {
        case 'blockchain_verification_update':
          handleVerificationUpdate(data);
          break;
        case 'blockchain_verification_completed':
          handleVerificationCompleted(data);
          break;
        case 'blockchain_verification_failed':
          handleVerificationFailed(data);
          break;
        case 'audit_trail_update':
          handleAuditTrailUpdate(data);
          break;
        case 'compliance_docs_update':
          handleComplianceDocsUpdate(data);
          break;
        default:
          console.log('Unhandled WebSocket event:', type);
      }
    } catch (error) {
      console.error('Error handling WebSocket event:', error);
      onError && onError('websocket_event_error', error.message);
    }
  }, [onError]);

  // Subscribe to WebSocket events
  const { isConnected, subscribe, unsubscribe } = useWebSocketEvents({
    onEvent: handleWebSocketEvent,
    analysisId,
    eventTypes: [
      'blockchain_verification_update',
      'blockchain_verification_completed',
      'blockchain_verification_failed',
      'audit_trail_update',
      'compliance_docs_update'
    ]
  });

  // ============================================================================
  // Data Loading and Management
  // ============================================================================

  /**
   * Load initial verification data
   */
  const loadVerificationData = useCallback(async () => {
    if (!analysisId) return;

    setLoading(true);
    retryCountRef.current = 0;

    try {
      // Check user permissions first
      const permissions = await authUtils.getUserPermissions();
      setUserPermissions(permissions);
      setCanViewSensitiveData(permissions?.canViewBlockchainDetails || false);

      // Load verification data
      const data = await blockchainVerificationService.getVerificationData(analysisId, blockchainHash);
      
      if (data) {
        setVerificationData(data);
        setVerificationStatus(data.status);
        setAuditTrail(data.auditTrail || []);
        setComplianceDocs(data.complianceDocs || []);
        setErrorDetails(data.errorDetails || null);
        lastUpdateRef.current = new Date();
        
        // Notify parent component
        onVerificationUpdate && onVerificationUpdate(data);
      }

      setLoading(false);
    } catch (error) {
      console.error('Error loading verification data:', error);
      handleLoadError(error);
    }
  }, [analysisId, blockchainHash, onVerificationUpdate]);

  /**
   * Handle load error with retry logic
   */
  const handleLoadError = useCallback((error) => {
    if (retryCountRef.current < mergedConfig.maxRetries) {
      retryCountRef.current++;
      setTimeout(() => {
        loadVerificationData();
      }, mergedConfig.retryDelay * retryCountRef.current);
    } else {
      setLoading(false);
      onError && onError('verification_load_failed', error.message);
    }
  }, [loadVerificationData, mergedConfig.maxRetries, mergedConfig.retryDelay, onError]);

  /**
   * Refresh verification data
   */
  const refreshVerificationData = useCallback(async () => {
    if (!analysisId || loading) return;

    try {
      const data = await blockchainVerificationService.getVerificationData(analysisId, blockchainHash);
      
      if (data) {
        setVerificationData(prev => ({ ...prev, ...data }));
        setVerificationStatus(data.status);
        setAuditTrail(data.auditTrail || []);
        setComplianceDocs(data.complianceDocs || []);
        setErrorDetails(data.errorDetails || null);
        lastUpdateRef.current = new Date();
        
        onVerificationUpdate && onVerificationUpdate(data);
      }
    } catch (error) {
      console.error('Error refreshing verification data:', error);
      onError && onError('verification_refresh_failed', error.message);
    }
  }, [analysisId, blockchainHash, loading, onVerificationUpdate, onError]);

  // ============================================================================
  // Event Handlers
  // ============================================================================

  /**
   * Handle verification status update
   */
  const handleVerificationUpdate = useCallback((data) => {
    setVerificationData(prev => ({ ...prev, ...data }));
    setVerificationStatus(data.status);
    lastUpdateRef.current = new Date();
    
    onVerificationUpdate && onVerificationUpdate(data);
  }, [onVerificationUpdate]);

  /**
   * Handle verification completion
   */
  const handleVerificationCompleted = useCallback((data) => {
    setVerificationStatus(VERIFICATION_STATUS.COMPLETED);
    setVerificationData(prev => ({ ...prev, ...data, status: VERIFICATION_STATUS.COMPLETED }));
    setErrorDetails(null);
    lastUpdateRef.current = new Date();
    
    onVerificationUpdate && onVerificationUpdate(data);
  }, [onVerificationUpdate]);

  /**
   * Handle verification failure
   */
  const handleVerificationFailed = useCallback((data) => {
    setVerificationStatus(VERIFICATION_STATUS.FAILED);
    setVerificationData(prev => ({ ...prev, ...data, status: VERIFICATION_STATUS.FAILED }));
    setErrorDetails(data.errorDetails);
    lastUpdateRef.current = new Date();
    
    onVerificationUpdate && onVerificationUpdate(data);
    onError && onError('verification_failed', data.errorMessage);
  }, [onVerificationUpdate, onError]);

  /**
   * Handle audit trail update
   */
  const handleAuditTrailUpdate = useCallback((data) => {
    setAuditTrail(prev => [...prev, ...data.newEntries]);
  }, []);

  /**
   * Handle compliance docs update
   */
  const handleComplianceDocsUpdate = useCallback((data) => {
    setComplianceDocs(prev => [...prev, ...data.newDocs]);
  }, []);

  /**
   * Handle section toggle
   */
  const toggleSection = useCallback((section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  }, []);

  /**
   * Handle certificate download
   */
  const handleCertificateDownload = useCallback(async (certificateType) => {
    if (!verificationData || !onCertificateDownload) return;

    try {
      const certificate = await blockchainVerificationService.downloadCertificate(
        analysisId,
        blockchainHash,
        certificateType
      );
      
      onCertificateDownload(certificate, certificateType);
    } catch (error) {
      console.error('Error downloading certificate:', error);
      onError && onError('certificate_download_failed', error.message);
    }
  }, [analysisId, blockchainHash, verificationData, onCertificateDownload, onError]);

  // ============================================================================
  // Effects
  // ============================================================================

  // Load initial data
  useEffect(() => {
    loadVerificationData();
  }, [loadVerificationData]);

  // Set up refresh interval
  useEffect(() => {
    if (verificationStatus === VERIFICATION_STATUS.PENDING || 
        verificationStatus === VERIFICATION_STATUS.IN_PROGRESS) {
      refreshIntervalRef.current = setInterval(refreshVerificationData, mergedConfig.refreshInterval);
    } else {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
        refreshIntervalRef.current = null;
      }
    }

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [verificationStatus, refreshVerificationData, mergedConfig.refreshInterval]);

  // Subscribe to WebSocket events
  useEffect(() => {
    if (isConnected && analysisId) {
      subscribe();
    }

    return () => {
      unsubscribe();
    };
  }, [isConnected, analysisId, subscribe, unsubscribe]);

  // ============================================================================
  // Render Functions
  // ============================================================================

  /**
   * Render verification status indicator
   */
  const renderStatusIndicator = () => {
    const statusConfig = {
      [VERIFICATION_STATUS.PENDING]: { 
        icon: '⏳', 
        color: '#f59e0b', 
        text: 'Pending Verification',
        description: 'Verification is queued and will begin shortly'
      },
      [VERIFICATION_STATUS.IN_PROGRESS]: { 
        icon: '🔄', 
        color: '#3b82f6', 
        text: 'Verifying',
        description: 'Blockchain verification in progress'
      },
      [VERIFICATION_STATUS.COMPLETED]: { 
        icon: '✅', 
        color: '#10b981', 
        text: 'Verified',
        description: 'Blockchain verification completed successfully'
      },
      [VERIFICATION_STATUS.FAILED]: { 
        icon: '❌', 
        color: '#ef4444', 
        text: 'Verification Failed',
        description: 'Blockchain verification encountered an error'
      },
      [VERIFICATION_STATUS.EXPIRED]: { 
        icon: '⏰', 
        color: '#6b7280', 
        text: 'Expired',
        description: 'Verification has expired'
      },
      [VERIFICATION_STATUS.REVOKED]: { 
        icon: '🚫', 
        color: '#dc2626', 
        text: 'Revoked',
        description: 'Verification has been revoked'
      }
    };

    const config = statusConfig[verificationStatus] || statusConfig[VERIFICATION_STATUS.PENDING];

    return (
      <div className={styles.statusIndicator}>
        <div 
          className={styles.statusIcon}
          style={{ color: config.color }}
        >
          {config.icon}
        </div>
        <div className={styles.statusContent}>
          <h3 className={styles.statusText} style={{ color: config.color }}>
            {config.text}
          </h3>
          <p className={styles.statusDescription}>
            {config.description}
          </p>
          {verificationData?.verificationTimestamp && (
            <p className={styles.verificationTimestamp}>
              {dateUtils.formatTimestamp(verificationData.verificationTimestamp, mergedConfig.timezone)}
            </p>
          )}
        </div>
      </div>
    );
  };

  /**
   * Render audit trail
   */
  const renderAuditTrail = () => {
    if (!mergedConfig.showAuditTrail || auditTrail.length === 0) return null;

    return (
      <div className={styles.auditTrailSection}>
        <div 
          className={styles.sectionHeader}
          onClick={() => toggleSection('auditTrail')}
        >
          <h4>Audit Trail</h4>
          <span className={styles.toggleIcon}>
            {expandedSections.auditTrail ? '▼' : '▶'}
          </span>
        </div>
        
        {expandedSections.auditTrail && (
          <div className={styles.auditTrailContent}>
            {auditTrail.map((entry, index) => (
              <div key={index} className={styles.auditEntry}>
                <div className={styles.auditTimestamp}>
                  {dateUtils.formatTimestamp(entry.timestamp, mergedConfig.timezone)}
                </div>
                <div className={styles.auditDetails}>
                  <div className={styles.auditAction}>{entry.action}</div>
                  <div className={styles.auditDescription}>{entry.description}</div>
                  {entry.verificationHash && canViewSensitiveData && (
                    <div className={styles.auditHash}>
                      Hash: <code>{entry.verificationHash}</code>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  /**
   * Render compliance documentation
   */
  const renderComplianceDocs = () => {
    if (!mergedConfig.showComplianceDocs || complianceDocs.length === 0) return null;

    return (
      <div className={styles.complianceDocsSection}>
        <div 
          className={styles.sectionHeader}
          onClick={() => toggleSection('complianceDocs')}
        >
          <h4>Compliance Documentation</h4>
          <span className={styles.toggleIcon}>
            {expandedSections.complianceDocs ? '▼' : '▶'}
          </span>
        </div>
        
        {expandedSections.complianceDocs && (
          <div className={styles.complianceDocsContent}>
            {complianceDocs.map((doc, index) => (
              <div key={index} className={styles.complianceDoc}>
                <div className={styles.docIcon}>
                  {doc.type === COMPLIANCE_DOC_TYPES.VERIFICATION_CERTIFICATE ? '📜' : '📄'}
                </div>
                <div className={styles.docContent}>
                  <div className={styles.docTitle}>{doc.title}</div>
                  <div className={styles.docDescription}>{doc.description}</div>
                  <div className={styles.docActions}>
                    <button
                      className={styles.docButton}
                      onClick={() => window.open(doc.url, '_blank')}
                    >
                      View Document
                    </button>
                    {doc.downloadable && (
                      <button
                        className={styles.docButton}
                        onClick={() => handleCertificateDownload(doc.type)}
                      >
                        Download
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  /**
   * Render error details
   */
  const renderErrorDetails = () => {
    if (!errorDetails || !mergedConfig.showErrorDetails) return null;

    return (
      <div className={styles.errorDetailsSection}>
        <div 
          className={styles.sectionHeader}
          onClick={() => toggleSection('errorDetails')}
        >
          <h4>Error Details</h4>
          <span className={styles.toggleIcon}>
            {expandedSections.errorDetails ? '▼' : '▶'}
          </span>
        </div>
        
        {expandedSections.errorDetails && (
          <div className={styles.errorDetailsContent}>
            <div className={styles.errorMessage}>
              <strong>Error:</strong> {errorDetails.message}
            </div>
            {errorDetails.code && (
              <div className={styles.errorCode}>
                <strong>Code:</strong> {errorDetails.code}
              </div>
            )}
            {errorDetails.recommendedActions && (
              <div className={styles.recommendedActions}>
                <strong>Recommended Actions:</strong>
                <ul>
                  {errorDetails.recommendedActions.map((action, index) => (
                    <li key={index}>{action}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  /**
   * Render loading state
   */
  const renderLoadingState = () => (
    <div className={styles.loadingContainer}>
      <div className={styles.loadingSpinner} />
      <div className={styles.loadingMessage}>
        Loading verification data...
      </div>
    </div>
  );

  /**
   * Render error state
   */
  const renderErrorState = () => (
    <div className={styles.errorContainer}>
      <div className={styles.errorIcon}>⚠️</div>
      <h3>Verification Data Unavailable</h3>
      <p>Unable to load blockchain verification data. Please try again later.</p>
      <button 
        className={styles.retryButton}
        onClick={loadVerificationData}
      >
        Retry
      </button>
    </div>
  );

  // ============================================================================
  // Main Render
  // ============================================================================

  if (loading) {
    return renderLoadingState();
  }

  if (!verificationData) {
    return renderErrorState();
  }

  return (
    <div className={`${styles.blockchainVerificationPanel} ${className}`}>
      {/* Header */}
      <div className={styles.header}>
        <h2>Blockchain Verification</h2>
        <div className={styles.headerInfo}>
          {lastUpdateRef.current && (
            <span className={styles.lastUpdate}>
              Last updated: {dateUtils.formatTimestamp(lastUpdateRef.current, mergedConfig.timezone)}
            </span>
          )}
          <div className={styles.connectionStatus}>
            <span className={`${styles.statusDot} ${isConnected ? styles.connected : styles.disconnected}`} />
            {isConnected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
      </div>

      {/* Status Indicator */}
      {renderStatusIndicator()}

      {/* Audit Trail */}
      {renderAuditTrail()}

      {/* Compliance Documentation */}
      {renderComplianceDocs()}

      {/* Error Details */}
      {renderErrorDetails()}

      {/* Technical Details (if enabled and user has permission) */}
      {mergedConfig.showTechnicalDetails && canViewSensitiveData && verificationData?.technicalDetails && (
        <div className={styles.technicalDetailsSection}>
          <div 
            className={styles.sectionHeader}
            onClick={() => toggleSection('technicalDetails')}
          >
            <h4>Technical Details</h4>
            <span className={styles.toggleIcon}>
              {expandedSections.technicalDetails ? '▼' : '▶'}
            </span>
          </div>
          
          {expandedSections.technicalDetails && (
            <div className={styles.technicalDetailsContent}>
              <pre>{JSON.stringify(verificationData.technicalDetails, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Exports
// ============================================================================

export { VERIFICATION_STATUS, VERIFICATION_PRIORITY, COMPLIANCE_DOC_TYPES };
export default BlockchainVerificationPanel;

