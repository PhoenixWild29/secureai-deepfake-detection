/**
 * BlockchainVerificationDisplay Component
 * Shows blockchain verification status with transaction details
 */

import React, { useState, useCallback } from 'react';
import { blockchainService, VERIFICATION_STATUS } from '../../services/blockchainService';
import { formatBlockchainTimestamp, createVerificationBadge } from '../../services/blockchainService';
import styles from './BlockchainVerificationDisplay.module.css';

// ============================================================================
  // Component
  // ============================================================================

/**
 * BlockchainVerificationDisplay - Displays blockchain verification status
 * @param {Object} props - Component properties
 * @param {Object} props.verificationData - Blockchain verification data
 * @param {boolean} props.loading - Loading state
 * @param {Function} props.onRetryVerification - Callback for retry action (optional)
 * @param {string} props.className - Additional CSS classes (optional)
 * @returns {JSX.Element} Blockchain verification display component
 */
const BlockchainVerificationDisplay = ({
  verificationData,
  loading = false,
  onRetryVerification,
  className = ''
}) => {
  // ============================================================================
  // State Management
  // ============================================================================

  const [showDetails, setShowDetails] = useState(false);
  const [retryingVerification, setRetryingVerification] = useState(false);

  // ============================================================================
  // Data Processing
  // ============================================================================
  
  const processedData = verificationData || {
    status: VERIFICATION_STATUS.NOT_SUBMITTED,
    verified: false,
    verificationTimestamp: null,
    transactionHash: null,
    blockHeight: null,
    explorerUrl: null,
    errorMessage: null
  };

  const formattedData = formatBlockchainTimestamp(processedData.verificationTimestamp) || {};
  const badgeData = createVerificationBadge(processedData);

  // ============================================================================
  // Event Handlers
  // ============================================================================

  /**
   * Handle retry verification
   */
  const handleRetryVerification = useCallback(async () => {
    if (!onRetryVerification) return;

    setRetryingVerification(true);
    try {
      await onRetryVerification();
    } catch (error) {
      console.error('Retry verification failed:', error);
    } finally {
      setRetryingVerification(false);
    }
  }, [onRetryVerification]);

  /**
   * Toggle details visibility
   */
  const toggleDetails = useCallback(() => {
    setShowDetails(prev => !prev);
  }, []);

  /**
   * Handle explorer link click
   */
  const handleExplorerClick = useCallback(() => {
    if (processedData.explorerUrl) {
      window.open(processedData.explorerUrl, '_blank', 'noopener,noreferrer');
    }
  }, [processedData.explorerUrl]);

  // ============================================================================
  // Render Helpers
  // ============================================================================

  /**
   * Render verification status
   */
  const renderVerificationStatus = () => {
    return (
      <div className={styles.statusContainer}>
        <div 
          className={`${styles.statusIcon} ${styles[processedData.status]}`}
          style={{ color: badgeData.color }}
        >
          {badgeData.icon}
        </div>
        
        <div className={styles.statusContent}>
          <h4 className={styles.statusTitle} style={{ color: badgeData.color }}>
            {badgeData.statusText}
          </h4>
          
          <p className={styles.statusDescription}>
            {processedData.verified 
              ? 'This result has been verified and recorded on the blockchain'
              : 'This result has not been verified on the blockchain yet'
            }
          </p>
        </div>
      </div>
    );
  };

  /**
   * Render verification details
   */
  const renderVerificationDetails = () => {
    if (!showDetails) return null;

    return (
      <div className={styles.detailsContainer}>
        {processedData.transactionHash && (
          <div className={styles.detailItem}>
            <label>Transaction Hash:</label>
            <div className={styles.transactionHash}>
              <code>{processedData.transactionHash}</code>
              {processedData.explorerUrl && (
                <button 
                  className={styles.explorerButton}
                  onClick={handleExplorerClick}
                  title="View on blockchain explorer"
                >
                  🔗
                </button>
              )}
            </div>
          </div>
        )}

        {processedData.blockHeight && (
          <div className={styles.detailItem}>
            <label>Block Height:</label>
            <span>{processedData.blockHeight.toLocaleString()}</span>
          </div>
        )}

        {processedData.verificationTimestamp && (
          <div className={styles.detailItem}>
            <label>Verified:</label>
            <span>
              {formattedData.formatted} ({formattedData.localDateTime})
            </span>
          </div>
        )}

        {processedData.confirmationCount !== undefined && (
          <div className={styles.detailItem}>
            <label>Confirmations:</label>
            <span>{processedData.confirmationCount}</span>
          </div>
        )}

        {processedData.errorMessage && (
          <div className={styles.detailItem}>
            <label>Error:</label>
            <span className={styles.errorText}>{processedData.errorMessage}</span>
          </div>
        )}
      </div>
    );
  };

  /**
   * Render action buttons
   */
  const renderActionButtons = () => {
    const actions = [];

    // Retry button for failed verifications
    if (processedData.status === VERIFICATION_STATUS.FAILED && badgeData.details?.canRetry) {
      actions.push(
        <button
          key="retry"
          className={styles.actionButton}
          onClick={handleRetryVerification}
          disabled={retryingVerification}
        >
          {retryingVerification ? 'Retrying...' : '🔁 Retry Verification'}
        </button>
      );
    }

    // Request verification button for unverified results
    if (processedData.status === VERIFICATION_STATUS.NOT_SUBMITTED && badgeData.details?.canSubmit) {
      actions.push(
        <button
          key="request"
          className={styles.actionButton}
          onClick={handleRetryVerification}
          disabled={retryingVerification}
        >
          {retryingVerification ? 'Submitting...' : '🔗 Request Verification'}
        </button>
      );
    }

    return actions;
  };

  /**
   * Render loading state
   */
  const renderLoadingState = () => (
    <div className={`${styles.blockchainVerificationDisplay} ${className}`}>
      <div className={styles.loading}>
        <div className={styles.loadingSpinner} />
        <span>Checking verification status...</span>
      </div>
    </div>
  );

  // ============================================================================
  // Main Render
  // ============================================================================

  if (loading) {
    return renderLoadingState();
  }

  return (
    <div className={`${styles.blockchainVerificationDisplay} ${className}`}>
      {/* Header */}
      <div className={styles.header}>
        <h3>Blockchain Verification</h3>
        <button 
          className={`${styles.toggleButton} ${showDetails ? styles.expanded : ''}`}
          onClick={toggleDetails}
          disabled={processedData.status === VERIFICATION_STATUS.NOT_SUBMITTED}
        >
          {showDetails ? '🔼' : '🔽'} {showDetails ? 'Hide' : 'Show'} Details
        </button>
      </div>

      {/* Main Content */}
      <div className={styles.content}>
        
        {/* Verification Status */}
        {renderVerificationStatus()}

        {/* Verification Details */}
        {renderVerificationDetails()}

        {/* Action Buttons */}
        {(processedData.status === VERIFICATION_STATUS.FAILED || 
          processedData.status === VERIFICATION_STATUS.NOT_SUBMITTED) && (
          <div className={styles.actionButtons}>
            {renderActionButtons()}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className={styles.footer}>
        <div className={styles.footerInfo}>
          {processedData.verified ? (
            <span className={styles.verifiedIndicator}>
              ✅ Immutable & Tamper-Proof
            </span>
          ) : (
            <span className={styles.unverifiedIndicator}>
              ⚠️ Not Yet Verified
            </span>
          )}
        </div>
        
        {processedData.status !== VERIFICATION_STATUS.NOT_SUBMITTED && (
          <div className={styles.networkInfo}>
            <span>Network: Solana Mainnet</span>
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// Export
// ============================================================================

export default BlockchainVerificationDisplay;
