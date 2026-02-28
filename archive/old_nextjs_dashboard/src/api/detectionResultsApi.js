/**
 * Detection Results API Client
 * Handles fetching detection results data including frame-level analysis and metadata
 */

// ============================================================================
// API Configuration
// ============================================================================

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
const API_TIMEOUT = 30000; // 30 seconds

/**
 * API Error handling utility
 */
const handleApiError = (error, context) => {
  console.error(`API Error in ${context}:`, error);
  
  if (error.response) {
    // Server responded with error status
    return {
      type: 'api_error',
      status: error.response.status,
      message: error.response.data?.message || error.response.statusText,
      details: error.response.data?.details || null
    };
  } else if (error.request) {
    // Network error
    return {
      type: 'network_error',
      message: 'Network connection failed. Please check your internet connection.',
      details: error.message
    };
  } else {
    // Other error
    return {
      type: 'unknown_error',
      message: error.message || 'An unexpected error occurred',
      details: error.toString()
    };
  }
};

/**
 * Generic API request utility
 */
const apiRequest = async (endpoint, options = {}) => {
  const { method = 'GET', body = null, headers = {}, timeout = API_TIMEOUT } = options;
  
  const config = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers
    },
    signal: AbortSignal.timeout(timeout)
  };

  if (body && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
    config.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw {
        response: {
          status: response.status,
          statusText: response.statusText,
          data: errorData
        }
      };
    }

    return await response.json();
  } catch (error) {
    if (error.name === 'AbortError') {
      throw {
        message: 'Request timeout',
        type: 'timeout'
      };
    }
    throw error;
  }
};

// ============================================================================
// Detection Results API Client
// ============================================================================

/**
 * Main API client for detection results
 */
export class DetectionResultsApiClient {
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Fetch detection result by analysis ID
   * @param {string} analysisId - Analysis identifier
   * @returns {Promise<Object>} Detection result data
   */
  async getDetectionResult(analysisId) {
    try {
      const result = await apiRequest(`/api/results/${analysisId}`);
      
      // Transform result to standard format
      return this.transformDetectionResult(result);
    } catch (error) {
      throw handleApiError(error, 'getDetectionResult');
    }
  }

  /**
   * Fetch frame-level analysis data
   * @param {string} analysisId - Analysis identifier
   * @returns {Promise<Array>} Array of frame analysis data
   */
  async getFrameAnalysisData(analysisId) {
    try {
      const result = await apiRequest(`/api/results/${analysisId}/frames`);
      return result.frames || [];
    } catch (error) {
      throw handleApiError(error, 'getFrameAnalysisData');
    }
  }

  /**
   * Fetch suspicious regions for specific frame
   * @param {string} analysisId - Analysis identifier
   * @param {number} frameNumber - Frame number
   * @returns {Promise<Array>} Array of suspicious regions
   */
  async getFrameSuspiciousRegions(analysisId, frameNumber) {
    try {
      const result = await apiRequest(`/api/results/${analysisId}/frames/${frameNumber}/regions`);
      return result.regions || [];
    } catch (error) {
      throw handleApiError(error, 'getFrameSuspiciousRegions');
    }
  }

  /**
   * Fetch frame thumbnail/image data
   * @param {string} analysisId - Analysis identifier
   * @param {number} frameNumber - Frame number
   * @param {Object} options - Options for thumbnail generation
   * @returns {Promise<string>} Base64 encoded thumbnail data or URL
   */
  async getFrameThumbnail(analysisId, frameNumber, options = {}) {
    try {
      const { quality = 'medium', size = '200x150' } = options;
      const params = new URLSearchParams({ quality, size });
      
      const result = await apiRequest(`/api/results/${analysisId}/frames/${frameNumber}/thumbnail?${params}`);
      
      if (result.thumbnail_url) {
        return result.thumbnail_url;
      } else if (result.thumbnail_data) {
        return `data:image/jpeg;base64,${result.thumbnail_data}`;
      }
      
      // Fallback: generate thumbnail on demand
      return await this.generateFrameThumbnail(analysisId, frameNumber, options);
    } catch (error) {
      throw handleApiError(error, 'getFrameThumbnail');
    }
  }

  /**
   * Generate frame thumbnail on demand
   * @param {string} analysisId - Analysis identifier
   * @param {number} frameNumber - Frame number
   * @param {Object} options - Thumbnail generation options
   * @returns {Promise<string>} Generated thumbnail data
   */
  async generateFrameThumbnail(analysisId, frameNumber, options = {}) {
    try {
      const result = await apiRequest(`/api/results/${analysisId}/frames/${frameNumber}/generate-thumbnail`, {
        method: 'POST',
        body: options
      });
      
      return result.thumbnail_data 
        ? `data:image/jpeg;base64,${result.thumbnail_data}`
        : result.thumbnail_url;
    } catch (error) {
      throw handleApiError(error, 'generateFrameThumbnail');
    }
  }

  /**
   * Fetch blockchain verification status
   * @param {string} analysisId - Analysis identifier
   * @returns {Promise<Object>} Blockchain verification data
   */
  async getBlockchainVerification(analysisId) {
    try {
      const result = await apiRequest(`/api/results/${analysisId}/blockchain`);
      return {
        verified: result.verified || false,
        transactionHash: result.transaction_hash || result.blockchain_hash,
        blockHeight: result.block_height,
        verificationTimestamp: result.verification_timestamp,
        verificationMethod: result.verification_method || 'solana',
        status: result.status || 'unknown'
      };
    } catch (error) {
      throw handleApiError(error, 'getBlockchainVerification');
    }
  }

  /**
   * Fetch analysis summary and metadata
   * @param {string} analysisId - Analysis identifier
   * @returns {Promise<Object>} Analysis summary data
   */
  async getAnalysisSummary(analysisId) {
    try {
      const result = await apiRequest(`/api/results/${analysisId}/summary`);
      
      return {
        analysisId: result.analysis_id || analysisId,
        filename: result.filename || 'Unknown',
        timestamp: result.timestamp || result.created_at,
        processingTime: result.processing_time_seconds || result.processing_time_ms / 1000,
        modelUsed: result.model_used || result.model_type || 'ensemble',
        totalFrames: result.total_frames || 0,
        framesProcessed: result.frames_processed || 0,
        videoDuration: result.video_duration || 0,
        videoSize: result.file_size || 0,
        videoFormat: result.video_format || 'unknown',
        analysisVersion: result.analysis_version || '1.0'
      };
    } catch (error) {
      throw handleApiError(error, 'getAnalysisSummary');
    }
  }
  
  /**
   * Transform detection result to standard format
   * @param {Object} rawResult - Raw API result
   * @returns {Object} Standardized detection result
   */
  transformDetectionResult(rawResult) {
    // Handle multiple potential response formats
    const isFake = rawResult.is_fake || rawResult.prediction === 1 || rawResult.score > 0.5;
    const confidence = rawResult.confidence_score || rawResult.confidence || rawResult.score || 0;
    
    return {
      analysisId: rawResult.analysis_id || rawResult.detection_id || rawResult.id,
      isFake,
      confidenceScore: confidence,
      accuracyScore: 1 - confidence, // Often provided as inverse confidence
      overallConfidence: Math.max(confidence, rawResult.overall_confidence || confidence),
      
      // Frame-level data
      totalFrames: rawResult.total_frames || rawResult.frames_processd || 0,
      framesProcessed: rawResult.frames_processed || 0,
      confidencePerFrame: rawResult.details?.confidence_per_frame || rawResult.frame_confidences || [],
      frameArtifacts: rawResult.details?.frame_artifacts || rawResult.frame_details || [],
      
      // Suspicious regions
      suspiciousRegions: rawResult.suspicious_regions || rawResult.details?.suspicious_regions || [],
      
      // Processing metadata
      processingTime: rawResult.processing_time_seconds || (rawResult.processing_time_ms / 1000),
      modelUsed: rawResult.model_type || rawResult.details?.model_used || rawResult.model_used,
      timestamp: rawResult.timestamp || rawResult.created_at,
      
      // Blockchain verification
      blockchainHash: rawResult.blockchain_hash,
      
      // Video metadata
      videoInfo: {
        filename: rawResult.filename,
        duration: rawResult.video_duration || rawResult.duration,
        size: rawResult.file_size,
        format: rawResult.video_format,
        resolution: rawResult.resolution,
        fps: rawResult.fps
      },
      
      // Additional analysis details
      analysisDetails: rawResult.details || {},
      
      // Raw result for debugging
      rawResult
    };
  }

  /**
   * Batch fetch multiple frames for grid view
   * @param {string} analysisId - Analysis identifier
   * @param {number} startFrame - Starting frame number
   * @param {number} endFrame - Ending frame number
   * @returns {Promise<Array>} Array of frame data with thumbnails
   */
  async batchGetFrameThumbnails(analysisId, startFrame, endFrame) {
    try {
      const params = new URLSearchParams({
        start: startFrame.toString(),
        end: endFrame.toString(),
        batch: 'true'
      });
      
      const result = await apiRequest(`/api/results/${analysisId}/thumbnails?${params}`);
      return result.thumbnails || [];
    } catch (error) {
      throw handleApiError(error, 'batchGetFrameThumbnails');
    }
  }
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Create thumbnail URL for frame
 * @param {string} analysisId - Analysis ID
 * @param {number} frameNumber - Frame number
 * @param {string} size - Thumbnail size (e.g., '200x150')
 * @returns {string} Thumbnail URL
 */
export const createThumbnailUrl = (analysisId, frameNumber, size = '200x150') => {
  return `${API_BASE_URL}/api/results/${analysisId}/frames/${frameNumber}/thumbnail?size=${size}&format=jpeg`;
};

/**
 * Create frame viewer URL
 * @param {string} analysisId - Analysis ID
 * @param {number} frameNumber - Frame number
 * @param {string} quality - Image quality ('low', 'medium', 'high', 'original')
 * @returns {string} Frame viewer URL
 */
export const createFrameViewerUrl = (analysisId, frameNumber, quality = 'high') => {
  return `${API_BASE_URL}/api/results/${analysisId}/frames/${frameNumber}/view?quality=${quality}&overlays=true`;
};

/**
 * Parse confidence score to risk level
 * @param {number} confidence - Confidence score (0.0-1.0)
 * @returns {Object} Risk level information
 */
export const parseConfidenceScore = (confidence) => {
  const percentage = Math.round(confidence * 100);
  
  let riskLevel, color, category;
  
  if (confidence <= 0.3) {
    riskLevel = 'low';
    color = '#10b981'; // Green
    category = 'Likely Authentic';
  } else if (confidence <= 0.7) {
    riskLevel = 'medium';
    color = '#f59e0b'; // Yellow
    category = 'Uncertain';
  } else {
    riskLevel = 'high';
    color = '#ef4444'; // Red
    category = 'Likely Deepfake';
  }
  
  return {
    percentage,
    riskLevel,
    color,
    category,
    description: `Confidence score indicates ${category.toLowerCase()}`
  };
};

/**
 * Format suspicious region data for display
 * @param {Object} region - Suspicious region data
 * @returns {Object} Formatted region data
 */
export const formatSuspiciousRegion = (region) => {
  return {
    id: region.id || `${region.frame_number}_${region.x}_${region.y}`,
    frameNumber: region.frame_number || 0,
    x: region.x || 0,
    y: region.y || 0,
    width: region.width || 0,
    height: region.height || 0,
    confidence: region.confidence || 0,
    regionType: region.region_type || 'unknown',
    boundingBox: {
      left: region.x,
      top: region.y,
      right: region.x + region.width,
      bottom: region.y + region.height
    }
  };
};

// ============================================================================
// Default Instance
// ============================================================================

export const detectionResultsApi = new DetectionResultsApiClient();
export default detectionResultsApi;
