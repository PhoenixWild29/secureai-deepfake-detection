/**
 * Report Generation Service
 * Handles communication with the existing report generation service for exporting PDF reports
 */

// ============================================================================
// Service Configuration
// ============================================================================

const REPORT_API_BASE_URL = process.env.REACT_APP_REPORT_SERVICE_URL || 'http://localhost:8000';
const DEFAULT_TIMEOUT = 60000; // 60 seconds for report generation

// ============================================================================
// Report Generation Service
// ============================================================================

/**
 * Service for generating and managing detection reports
 */
export class ReportGenerationService {
  constructor(baseUrl = REPORT_API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Generate comprehensive PDF report for detection results
   * @param {Object} params - Report generation parameters
   * @param {string} params.analysisId - Analysis identifier
   * @param {Object} params.options - Report options
   * @param {boolean} params.options.includeFrameDetails - Include frame-by-frame analysis
   * @param {boolean} params.options.includeSuspiciousRegions - Include suspicious region details
   * @param {boolean} params.options.includeThumbnails - Include frame thumbnails
   * @param {string} params.options.format - Report format ('standard', 'detailed', 'summary')
   * @param {string} params.options.theme - PDF theme ('light', 'dark', 'professional')
   * @returns {Promise<Object>} Report generation response
   */
  async generateDetectionReport(params) {
    const { analysisId, options = {} } = params;
    
    try {
      const response = await fetch(`${this.baseUrl}/api/reports/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          analysis_id: analysisId,
          report_type: 'detection_analysis',
          options: {
            include_frame_details: options.includeFrameDetails || false,
            include_suspicious_regions: options.includeSuspiciousRegions || true,
            include_thumbnails: options.includeThumbnails || true,
            include_blockchain_verification: options.includeBlockchainVerification || true,
            include_technical_details: options.includeTechnicalDetails || false,
            format: options.format || 'standard',
            theme: options.theme || 'professional',
            language: options.language || 'en',
            max_frames_displayed: options.maxFramesDisplayed || 50
          }
        }),
        signal: AbortSignal.timeout(DEFAULT_TIMEOUT)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(`Report generation failed: ${errorData?.message || response.statusText}`);
      }

      const result = await response.json();
      
      return {
        success: true,
        reportId: result.report_id,
        downloadUrl: result.download_url,
        expiresAt: result.expires_at,
        estimatedSize: result.estimated_size_mb,
        generationTime: result.generation_time_ms,
        status: result.status
      };
    } catch (error) {
      console.error('Report generation error:', error);
      throw new Error(`Failed to generate report: ${error.message}`);
    }
  }

  /**
   * Download generated report
   * @param {string} reportId - Report identifier
   * @param {string} downloadUrl - Download URL from generation response
   * @returns {Promise<Blob>} Report file blob
   */
  async downloadReport(reportId, downloadUrl) {
    try {
      const response = await fetch(downloadUrl, {
        method: 'GET',
        signal: AbortSignal.timeout(DEFAULT_TIMEOUT)
      });

      if (!response.ok) {
        throw new Error(`Download failed: ${response.statusText}`);
      }

      return await response.blob();
    } catch (error) {
      console.error('Report download error:', error);
      throw new Error(`Failed to download report: ${error.message}`);
    }
  }

  /**
   * Get report generation status
   * @param {string} reportId - Report identifier
   * @returns {Promise<Object>} Report status
   */
  async getReportStatus(reportId) {
    try {
      const response = await fetch(`${this.baseUrl}/api/reports/${reportId}/status`);
      
      if (!response.ok) {
        throw new Error(`Status check failed: ${response.statusText}`);
      }

      const result = await response.json();
      
      return {
        status: result.status, // 'pending', 'generating', 'completed', 'failed'
        progress: result.progress || 0,
        downloadUrl: result.download_url,
        errorMessage: result.error_message,
        generatedAt: result.generated_at
      };
    } catch (error) {
      console.error('Report status check error:', error);
      throw new Error(`Failed to check report status: ${error.message}`);
    }
  }

  /**
   * Generate customized report template
   * @param {string} templateType - Template type ('standard', 'detailed', 'executive')
   * @param {Object} customization - Customization options
   * @returns {Promise<Object>} Customized template configuration
   */
  async customizeTemplate(templateType, customization) {
    try {
      const response = await fetch(`${this.baseUrl}/api/reports/templates/customize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          template_type: templateType,
          customization
        })
      });

      if (!response.ok) {
        throw new Error(`Template customization failed: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Template customization error:', error);
      throw new Error(`Failed to customize template: ${error.message}`);
    }
  }

  /**
   * Get available report formats and templates
   * @returns {Promise<Array>} Available formats and templates
   */
  async getAvailableFormats() {
    try {
      const response = await fetch(`${this.baseUrl}/api/reports/formats`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch formats: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Format fetch error:', error);
      throw new Error(`Failed to fetch available formats: ${error.message}`);
    }
  }
}

// ============================================================================
// Report Content Builders
// ============================================================================

/**
 * Build report content structure
 * @param {Object} detectionData - Detection result data
 * @param {Object} options - Report options
 * @returns {Object} Structured report content
 */
export export const buildReportContent = (detectionData, options = {}) => {
  const content = {
    metadata: {
      title: 'SecureAI DeepFake Detection Analysis Report',
      subtitle: `Analysis ID: ${detectionData.analysisId}`,
      generatedAt: new Date().toISOString(),
      version: '1.0'
    },
    
    summary: {
      filename: detectionData.videoInfo?.filename || 'Unknown Video',
      analysisResult: detectionData.isFake ? 'Deepfake Detected' : 'Authentic Video',
      confidenceScore: Math.round(detectionData.confidenceScore * 100),
      riskLevel: parseRiskLevel(detectionData.confidenceScore),
      processingTime: `${detectionData.processingTime.toFixed(2)}s`,
      totalFrames: detectionData.totalFrames,
      modelUsed: detectionData.modelUsed
    },
    
    technicalDetails: {
      confidenceScores: {
        overall: detectionData.confidenceScore,
        accuracy: detectionData.accuracyScore,
        perFrame: detectionData.confidencePerFrame || []
      },
      suspiciousRegions: detectionData.suspiciousRegions || [],
      frameArtifacts: detectionData.frameArtifacts || [],
      processingInfo: {
        framesProcessed: detectionData.framesProcessed,
        totalFrames: detectionData.totalFrames,
        processingTime: detectionData.processingTime,
        modelType: detectionData.modelUsed
      }
    },
    
    blockchainVerification: {
      hash: detectionData.blockchainHash,
      verified: detectionData.blockchainHash ? true : false,
      verificationStatus: detectionData.blockchainHash ? 'verified' : 'not_available'
    },
    
    recommendations: generateRecommendations(detectionData)
  };

  // Include detailed frame analysis if requested
  if (options.includeFrameDetails && detectionData.confidencePerFrame) {
    content.frameAnalysis = {
      frameSamples: buildFrameSamples(detectionData, options.maxFramesDisplayed || 20),
      confidenceDistribution: analyzeConfidenceDistribution(detectionData.confidencePerFrame),
      temporalAnalysis: analyzeTemporalPatterns(detenceData.confidencePerFrame)
    };
  }

  return content;
};

/**
 * Parse risk level from confidence score
 * @param {number} confidence - Confidence score (0.0-1.0)
 * @returns {string} Risk level
 */
const parseRiskLevel = (confidence) => {
  if (confidence <= 0.3) return 'Low Risk';
  if (confidence <= 0.7) return 'Medium Risk';
  return 'High Risk';
};

/**
 * Generate recommendations based on analysis
 * @param {Object} detectionData - Detection result data
 * @returns {Array} Array of recommendations
 */
const generateRecommendations = (detectionData) => {
  const recommendations = [];

  if (detectionData.isFake) {
    recommendations.push({
      type: 'warning',
      title: 'Deepfake Content Detected',
      description: 'This video appears to contain manipulated content. Proceed with caution.',
      priority: 'high'
    });

    if (detectionData.confidenceScore > 0.8) {
      recommendations.push({
        type: 'critical',
        title: 'High Confidence Detection',
        description: 'The analysis shows very strong evidence of content manipulation.',
        priority: 'critical'
      });
    }
  } else {
    recommendations.push({
      type: 'info',
      title: 'Authentic Content',
      description: 'No significant signs of manipulation detected in this video.',
      priority: 'low'
    });
  }

  if (detectionData.confidenceScore > 0.5 && detectionData.confidenceScore <= 0.7) {
    recommendations.push({
      type: 'caution',
      title: 'Uncertain Analysis',
      description: 'The analysis results show moderate confidence. Manual review recommended.',
      priority: 'medium'
    });
  }

  return recommendations;
};

/**
 * Build frame samples for detailed report
 * @param {Object} detectionData - Detection result data
 * @param {number} maxSamples - Maximum frames to include
 * @returns {Array} Frame sample data
 */
const buildFrameSamples = (detectionData, maxSamples = 20) => {
  const frameCount = detectionData.confidencePerFrame?.length || 0;
  const samples = [];
  
  if (frameCount === 0) return samples;

  // Select representative frames
  const step = Math.max(1, Math.floor(frameCount / maxSamples));
  
  for (let i = 0; i < frameCount; i += step) {
    samples.push({
      frameNumber: i,
      confidence: detectionData.confidencePerFrame[i],
      riskLevel: parseRiskLevel(detectionData.confidencePerFrame[i]),
      artifacts: detectionData.frameArtifacts?.[i] || []
    });
  }

  return samples.slice(0, maxSamples);
};

/**
 * Analyze confidence score distribution
 * @param {Array} confidenceScores - Array of confidence scores per frame
 * @returns {Object} Distribution analysis
 */
const analyzeConfidenceDistribution = (confidenceScores) => {
  if (!confidenceScores.length) return null;

  const sorted = [...confidenceScores].sort((a, b) => a - b);
  const mean = confidenceScores.reduce((sum, score) => sum + score, 0) / confidenceScores.length;
  const median = sorted[Math.floor(sorted.length / 2)];
  
  const quartiles = {
    q25: sorted[Math.floor(sorted.length * 0.25)],
    q50: median,
    q75: sorted[Math.floor(sorted.length * 0.75)]
  };

  return {
    mean: mean,
    median: median,
    quartiles,
    range: {
      min: sorted[0],
      max: sorted[sorted.length - 1]
    },
    standardDeviation: calculateStandardDeviation(confidenceScores, mean)
  };
};

/**
 * Analyze temporal patterns in confidence scores
 * @param {Array} confidenceScores - Array of confidence scores per frame
 * @returns {Object} Temporal analysis
 */
const analyzeTemporalPatterns = (confidenceScores) => {
  if (confidenceScores.length < 2) return null;

  const trends = detectTrends(confidenceScores);
  const clusters = detectClusters(confidenceScores);
  
  return {
    trend: trends,
    clusteredRegions: clusters,
    stability: calculateStability(confidenceScores)
  };
};

/**
 * Calculate standard deviation
 * @param {Array} values - Array of values
 * @param {number} mean - Mean value
 * @returns {number} Standard deviation
 */
const calculateStandardDeviation = (values, mean) => {
  const variance = values.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / values.length;
  return Math.sqrt(variance);
};

/**
 * Detect trends in confidence scores
 * @param {Array} scores - Confidence scores
 * @returns {string} Trend direction
 */
const detectTrends = (scores) => {
  if (scores.length < 3) return 'insufficient_data';
  
  let increasing = 0;
  let decreasing = 0;
  
  for (let i = 1; i < scores.length; i++) {
    const diff = scores[i] - scores[i - 1];
    if (diff > 0) increasing++;
    else if (diff < 0) decreasing++;
  }
  
  const ratio = Math.abs(increasing - decreasing) / scores.length;
  
  if (ratio < 0.1) return 'stable';
  return increasing > decreasing ? 'increasing' : 'decreasing';
};

/**
 * Detect clustered regions of high confidence
 * @param {Array} scores - Confidence scores
 * @param {number} threshold - High confidence threshold
 * @returns {Array} Clustered regions
 */
const detectClusters = (scores, threshold = 0.7) => {
  const clusters = [];
  let clusterStart = null;
  
  for (let i = 0; i < scores.length; i++) {
    if (scores[i] > threshold) {
      if (clusterStart === null) {
        clusterStart = i;
      }
    } else if (clusterStart !== null) {
      clusters.push({
        start: clusterStart,
        end: i - 1,
        length: i - clusterStart,
        averageConfidence: scores.slice(clusterStart, i).reduce((sum, score) => sum + score, 0) / (i - clusterStart)
      });
      clusterStart = null;
    }
  }
  
  // Handle cluster at the end
  if (clusterStart !== null) {
    clusters.push({
      start: clusterStart,
      end: scores.length - 1,
      length: scores.length - clusterStart,
      averageConfidence: scores.slice(clusterStart).reduce((sum, score) => sum + score, 0) / (scores.length - clusterStart)
    });
  }
  
  return clusters;
};

/**
 * Calculate stability of confidence scores
 * @param {Array} scores - Confidence scores
 * @returns {number} Stability score (0-1)
 */
const calculateStability = (scores) => {
  if (scores.length < 2) return 1;
  
  const mean = scores.reduce((sum, score) => sum + score, 0) / scores.length;
  const variance = scores.reduce((sum, score) => sum + Math.pow(score - mean, 2), 0) / scores.length;
  const coefficientOfVariation = Math.sqrt(variance) / mean;
  
  // Convert to stability score (lower variation = higher stability)
  return Math.max(0, Math.min(1, 1 - coefficientOfVariation));
};

// ============================================================================
// Utility Functions for Report Export
// ============================================================================

/**
 * Trigger browser download for generated report
 * @param {Blob} reportBlob - Report file blob
 * @param {string} filename - Download filename
 */
export const downloadReportFile = (reportBlob, filename = 'detection_report.pdf') => {
  try {
    const url = URL.createObjectURL(reportBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.display = 'none';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Clean up the URL object
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {
    console.error('Download error:', error);
    throw new Error(`Failed to download report: ${error.message}`);
  }
};

// ============================================================================
// Default Instance
// ============================================================================

export const reportGenerationService = new ReportGenerationService();
export default reportGenerationService;
