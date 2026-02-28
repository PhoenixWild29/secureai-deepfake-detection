/**
 * Blockchain Verification Service
 * Handles communication with the existing blockchain service for verification status
 */

// ============================================================================
// Service Configuration
// ============================================================================

const BLOCKCHAIN_API_BASE_URL = process.env.REACT_APP_BLOCKCHAIN_SERVICE_URL || 'http://localhost:8000';
const DEFAULT_TIMEOUT = 30000; // 30 seconds
const DEFAULT_RETRY_ATTEMPTS = 3;
const DEFAULT_RETRY_DELAY = 1000; // 1 second

// ============================================================================
// Blockchain Network Types
// ============================================================================

export const BLOCKCHAIN_NETWORKS = {
  SOLANA_MAINNET: {
    name: 'Solana Mainnet',
    endpoint: 'https://api.mainnet-beta.solana.com',
    explorerBaseUrl: 'https://explorer.solana.com'
  },
  SOLANA_DEVNET: {
    name: 'Solana Devnet', 
    endpoint: 'https://api.devnet.solana.com',
    explorerBaseUrl: 'https://explorer.solana.com/?cluster=devnet'
  },
  SOLANA_TESTNET: {
    name: 'Solana Testnet',
    endpoint: 'https://api.testnet.solana.com', 
    explorerBaseUrl: 'https://explorer.solana.com/?cluster=testnet'
  }
};

// ============================================================================
// Verification Status Types
// ============================================================================

export const VERIFICATION_STATUS = {
  VERIFIED: 'verified',
  PENDING: 'pending',
  FAILED: 'failed',
  NOT_SUBMITTED: 'not_submitted',
  UNKNOWN: 'unknown'
};

// ============================================================================
// Blockchain Verification Service
// ============================================================================

/**
 * Service for blockchain verification operations
 */
export class BlockchainVerificationService {
  constructor(baseUrl = BLOCKCHAIN_API_BASE_URL) {
    this.baseUrl = baseUrl;
    this.network = BLOCKCHAIN_NETWORKS.SOLANA_MAINNET; // Default network
  }

  /**
   * Set blockchain network
   * @param {Object} network - Blockchain network configuration
   */
  setNetwork(network) {
    this.network = network;
  }

  /**
   * Verify detection result on blockchain
   * @param {Object} params - Verification parameters
   * @param {string} params.analysisId - Analysis identifier
   * @param {string} params.resultHash - Result hash to verify
   * @param {Object} params.analysisData - Analysis data to store
   * @returns {Promise<Object>} Verification response
   */
  async verifyDetectionResult(params) {
    const { analysisId, resultHash, analysisData } = params;
    
    try {
      const response = await fetch(`${this.baseUrl}/api/blockchain/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          analysis_id: analysisId,
          result_hash: resultHash,
          analysis_data: {
            is_fake: analysisData.isFake,
            confidence_score: analysisData.confidenceScore,
            processing_time: analysisData.processingTime,
            model_used: analysisData.modelUsed,
            timestamp: analysisData.timestamp
          },
          network: this.network.name.toLowerCase()
        }),
        signal: AbortSignal.timeout(DEFAULT_TIMEOUT)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(`Blockchain verification failed: ${errorData?.message || response.statusText}`);
      }

      const result = await response.json();
      
      return {
        success: true,
        transactionHash: result.transaction_hash || result.tx_hash,
        blockHeight: result.block_height,
        slot: result.slot,
        verificationId: result.verification_id,
        explorerUrl: this.createExplorerUrl(result.transaction_hash || result.tx_hash),
        timestamp: result.timestamp,
        gasUsed: result.gas_used,
        status: VERIFICATION_STATUS.VERIFIED
      };
    } catch (error) {
      console.error('Blockchain verification error:', error);
      throw new Error(`Failed to verify on blockchain: ${error.message}`);
    }
  }

  /**
   * Get verification status for analysis
   * @param {string} analysisId - Analysis identifier
   * @returns {Promise<Object>} Verification status
   */
  async getVerificationStatus(analysisId) {
    try {
      const response = await fetch(`${this.baseUrl}/api/blockchain/${analysisId}/status`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        },
        signal: AbortSignal.timeout(DEFAULT_TIMEOUT)
      });

      if (!response.ok) {
        // Check if verification hasn't been submitted yet
        if (response.status === 404) {
          return {
            status: VERIFICATION_STATUS.NOT_SUBMITTED,
            verified: false,
            message: 'Verification not submitted to blockchain'
          };
        }
        throw new Error(`Status check failed: ${response.statusText}`);
      }

      const result = await response.json();
      
      return {
        status: this.parseVerificationStatus(result.status),
        verified: result.verified || false,
        transactionHash: result.transaction_hash,
        blockHeight: result.block_height,
        verificationTimestamp: result.verification_timestamp,
        confirmationCount: result.confirmation_count || 0,
        explorerUrl: result.transaction_hash ? this.createExplorerUrl(result.transaction_hash) : null,
        gasUsed: result.gas_used,
        network: result.network || this.network.name,
        errorMessage: result.error_message
      };
    } catch (error) {
      console.error('Verification status check error:', error);
      throw new Error(`Failed to check verification status: ${error.message}`);
    }
  }

  /**
   * Retrieve verification details from blockchain
   * @param {string} transactionHash - Blockchain transaction hash
   * @returns {Promise<Object>} Verification details
   */
  async getVerificationDetails(transactionHash) {
    try {
      const response = await fetch(`${this.baseUrl}/api/blockchain/transaction/${transactionHash}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        },
        signal: AbortSignal.timeout(DEFAULT_TIMEOUT)
      });

      if (!response.ok) {
        throw new Error(`Transaction lookup failed: ${response.statusText}`);
      }

      const result = await response.json();
      
      return {
        transactionHash: result.transaction_hash,
        blockHeight: result.block_height,
        slot: result.slot,
        timestamp: result.timestamp,
        confirmed: result.confirmed || false,
        confirmationCount: result.confirmation_count || 0,
        gasUsed: result.gas_used,
        error: result.error,
        logMessages: result.log_messages || [],
        programData: result.program_data || null,
        explorerUrl: this.createExplorerUrl(result.transaction_hash)
      };
    } catch (error) {
      console.error('Transaction details lookup error:', error);
      throw new Error(`Failed to retrieve transaction details: ${error.message}`);
    }
  }

  /**
   * Check if result hash exists on blockchain
   * @param {string} resultHash - Result hash to check
   * @param {number} maxAttempts - Maximum retry attempts
   * @returns {Promise<boolean>} Whether hash exists on blockchain
   */
  async checkHashExists(resultHash, maxAttempts = DEFAULT_RETRY_ATTEMPTS) {
    let attempt = 0;
    
    while (attempt < maxAttempts) {
      try {
        const response = await fetch(`${this.baseUrl}/api/blockchain/hash/${resultHash}/exists`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          },
          signal: AbortSignal.timeout(DEFAULT_TIMEOUT)
        });

        if (response.ok) {
          const result = await response.json();
          return result.exists || false;
        }
        
        // If not found, wait before retry
        if (response.status === 404) {
          await new Promise(resolve => setTimeout(resolve, DEFAULT_RETRY_DELAY));
          attempt++;
          continue;
        }
        
        throw new Error(`Hash check failed: ${response.statusText}`);
      } catch (error) {
        console.warn(`Hash check attempt ${attempt + 1} failed:`, error.message);
        
        if (attempt >= maxAttempts - 1) {
          throw new Error(`Hash existence check failed after ${maxAttempts} attempts: ${error.message}`);
        }
        
        await new Promise(resolve => setTimeout(resolve, DEFAULT_RETRY_DELAY * (attempt + 1)));
        attempt++;
      }
    }
    
    return false;
  }

  /**
   * Get network status and health
   * @returns {Promise<Object>} Network status
   */
  async getNetworkStatus() {
    try {
      const response = await fetch(`${this.baseUrl}/api/blockchain/network/status`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        },
        signal: AbortSignal.timeout(DEFAULT_TIMEOUT)
      });

      if (!response.ok) {
        throw new Error(`Network status check failed: ${response.statusText}`);
      }

      const result = await response.json();
      
      return {
        networkName: result.network_name,
        isConnected: result.is_connected,
        blockHeight: result.current_block_height,
        slot: result.current_slot,
        averageConfirmationTime: result.average_confirmation_time_ms,
        networkHashrate: result.network_hashrate,
        status: result.status,
        lastUpdate: result.last_updated
      };
    } catch (error) {
      console.error('Network status check error:', error);
      throw new Error(`Failed to check network status: ${error.message}`);
    }
  }

  /**
   * Retry failed verification
   * @param {string} analysisId - Analysis identifier
   * @returns {Promise<Object>} Retry verification response
   */
  async retryVerification(analysisId) {
    try {
      const response = await fetch(`${this.baseUrl}/api/blockchain/${analysisId}/retry`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        signal: AbortSignal.timeout(DEFAULT_TIMEOUT)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(`Verification retry failed: ${errorData?.message || response.statusText}`);
      }

      const result = await response.json();
      
      return {
        success: true,
        transactionHash: result.transaction_hash,
        blockHeight: result.block_height,
        verificationId: result.verification_id,
        explorerUrl: this.createExplorerUrl(result.transaction_hash),
        timestamp: result.timestamp
      };
    } catch (error) {
      console.error('Verification retry error:', error);
      throw new Error(`Failed to retry verification: ${error.message}`);
    }
  }

  /**
   * Parse verification status string to enum
   * @param {string} statusString - Status string from API
   * @returns {string} Verification status enum
   */
  parseVerificationStatus(statusString) {
    const status = statusString?.toLowerCase();
    
    switch (status) {
      case 'verified':
      case 'confirmed':
        return VERIFICATION_STATUS.VERIFIED;
      case 'pending':
      case 'verifying':
        return VERIFICATION_STATUS.PENDING;
      case 'failed':
      case 'error':
        return VERIFICATION_STATUS.FAILED;
      case 'not_submitted':
      case 'not_verified':
        return VERIFICATION_STATUS.NOT_SUBMITTED;
      default:
        return VERIFICATION_STATUS.UNKNOWN;
    }
  }

  /**
   * Create blockchain explorer URL for transaction
   * @param {string} transactionHash - Transaction hash
   * @returns {string} Explorer URL
   */
  createExplorerUrl(transactionHash) {
    if (!transactionHash || !this.network.explorerBaseUrl) {
      return null;
    }
    
    return `${this.network.explorerBaseUrl}/tx/${transactionHash}`;
  }

  /**
   * Validate blockchain transaction
   * @param {Object} verificationData - Verification data to validate
   * @returns {Object} Validation result
   */
  validateVerificationData(verificationData) {
    const errors = [];
    
    if (!verificationData.transactionHash) {
      errors.push('Transaction hash is required');
    }
    
    if (!verificationData.blockHeight || verificationData.blockHeight < 0) {
      errors.push('Valid block height is required');
    }
    
    if (!verificationData.timestamp) {
      errors.push('Verification timestamp is required');
    }
    
    if (verificationData.gasUsed !== undefined && verificationData.gasUsed < 0) {
      errors.push('Gas used cannot be negative');
    }
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }

  /**
   * Format verification status for display
   * @param {Object} verificationInfo - Verification information
   * @returns {Object} Formatted status for UI
   */
  formatVerificationStatus(verificationInfo) {
    const { status, verified, transactionHash, blockHeight, explorerUrl, errorMessage } = verificationInfo;
    
    let statusText, statusColor, icon;
    
    switch (status) {
      case VERIFICATION_STATUS.VERIFIED:
        statusText = 'Verified';
        statusColor = '#10b981'; // Green
        icon = '🔐';
        break;
      case VERIFICATION_STATUS.PENDING:
        statusText = 'Verifying...';
        statusColor = '#f59e0b'; // Yellow
        icon = '⏳';
        break;
      case VERIFICATION_STATUS.FAILED:
        statusText = 'Verification Failed';
        statusColor = '#ef4444'; // Red
        icon = '❌';
        break;
      case VERIFICATION_STATUS.NOT_SUBMITTED:
        statusText = 'Not Submitted';
        statusColor = '#6b7280'; // Gray
        icon = '⚪';
        break;
      default:
        statusText = 'Unknown Status';
        statusColor = '#6b7280'; // Gray
        icon = '❓';
    }
    
    return {
      statusText,
      statusColor,
      icon,
      verified,
      transactionHash,
      blockHeight,
      explorerUrl,
      errorMessage,
      details: {
        networkName: this.network.name,
        canRetry: status === VERIFICATION_STATUS.FAILED,
        canSubmit: status === VERIFICATION_STATUS.NOT_SUBMITTED
      }
    };
  }
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Calculate verification confirmations needed
 * @param {number} currentConfirmations - Current confirmation count
 * @param {number} requiredConfirmations - Required confirmation count
 * @returns {Object} Confirmation status
 */
export const calculateConfirmationStatus = (currentConfirmations, requiredConfirmations = 1) => {
  const isConfirmed = currentConfirmations >= requiredConfirmations;
  const remainingConfirmations = Math.max(0, requiredConfirmations - currentConfirmations);
  
  return {
    isConfirmed,
    currentConfirmations,
    requiredConfirmations,
    remainingConfirmations,
    confirmationPercentage: Math.min(100, (currentConfirmations / requiredConfirmations) * 100)
  };
};

/**
 * Format blockchain transaction time
 * @param {string} timestamp - Transaction timestamp
 * @returns {Object} Formatted time information
 */
export const formatBlockchainTimestamp = (timestamp) => {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMinutes = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    let timeAgo;
    if (diffMinutes < 1) {
      timeAgo = 'Just now';
    } else if (diffMinutes < 60) {
      timeAgo = `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
    } else if (diffHours < 24) {
      timeAgo = `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    } else {
      timeAgo = `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    }
    
    return {
      formatted: timeAgo,
      isoString: timestamp,
      localDateTime: date.toLocaleString(),
      relativeTime: Math.abs(diffMs),
      isRecent: diffMs < 300000 // Within 5 minutes
    };
  } catch (error) {
    console.error('Timestamp formatting error:', error);
    return {
      formatted: 'Unknown',
      isoString: timestamp,
      localDateTime: 'Invalid date',
      relativeTime: 0,
      isRecent: false
    };
  }
};

/**
 * Create verification badge component data
 * @param {Object} verificationInfo - Verification information
 * @returns {Object} Badge configuration
 */
export const createVerificationBadge = (verificationInfo) => {
  const formatted = new BlockchainVerificationService().formatVerificationStatus(verificationInfo);
  
  return {
    ...formatted,
    tooltip: formatted.errorMessage || `${formatted.statusText} on ${formatted.details.networkName}`,
    badgeVariant: verificationInfo.verified ? 'success' : 'secondary',
    animationClass: verificationInfo.status === VERIFICATION_STATUS.PENDING ? 'pulse' : null
  };
};

// ============================================================================
// Default Instance
// ============================================================================

export const blockchainService = new BlockchainVerificationService();
export default blockchainService;
