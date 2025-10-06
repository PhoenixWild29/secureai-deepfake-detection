/**
 * DetectionSummary Component
 * Displays the overall confidence score and summary of detection findings
 */

import React from 'react';
import { formatTimeRemaining, formatFileSize } from '../../utils/videoProcessing';
import { parseConfidenceScore } from '../../api/detectionResultsApi';
import styles from './DetectionSummary.module.css';

// ============================================================================
// Component
// ============================================================================

/**
 * DetectionSummary - Displays overall detection analysis summary
 * @param {Object} props - Component properties
 * @param {Object} props.analysisData - Detection analysis data
 * @param {Object} props.confidenceSummary - Confidence score summary
 * @param {Function} props.onExport - Export callback (optional)
 * @param {string} props.className - Additional CSS classes (optional)
 * @returns {JSX.Element} Detection summary component
 */
const DetectionSummary = ({
  analysisData,
  confidenceSummary,
  onExport,
  className = ''
}) => {
  // ============================================================================
  // Data Processing
  // ============================================================================
  
  if (!analysisData) {
    return (
      <div className={`${styles.detectionSummary} ${className}`}>
        <div className={styles.noData}>
          <p>No analysis data available</p>
        </div>
      </div>
    );
  }

  // Parse confidence score for display
  const confidenceInfo = parseConfidenceScore(analysisData.confidenceScore);
  
  // Video information
  const videoInfo = analysisData.videoInfo || {};
  
  // Processing statistics
  const processingStats = {
    totalFrames: analysisData.totalFrames || 0,
    framesProcessed: analysisData.framesProcessed || 0,
    processingTime: analysisData.processingTime || 0,
    processingSpeed: analysisData.processingTime > 0 ? 
      (analysisData.framesProcessed / analysisData.processingTime).toFixed(2) : 0,
    modelUsed: analysisData.modelUsed || 'Unknown'
  };

  // ============================================================================
  // Render Helpers
  // ============================================================================

  /**
   * Render confidence score visualization
   */
  const renderConfidenceVisualization = () => {
    const percentage = confidenceInfo.percentage;
    const color = confidenceInfo.color;
    
    return (
      <div className={styles.confidenceVisualization}>
        <div className={styles.confidenceCircle}>
          <svg width="120" height="120" className={styles.confidenceSvg}>
 C           <circle 
              cx="60" 
              cy="60" 
              r="50" 
              stroke="#e5e7eb" 
              strokeWidth="8" 
              fill="none"
              className={styles.confidenceBackground}
            />
            <circle 
              cx="60" 
              cy="60" 
              r="50" 
              stroke={color} 
              strokeWidth="8" 
              fill="none"
              strokeDasharray={`${2 * Math.PI * 50}`}
              strokeDashoffset={`${2 * Math.PI * 50 * (1 - percentage / 100)}`}
              strokeLinecap="round"
              className={styles.confidenceProgress}
              style={{
                transform: 'rotate(-90deg)',
                transformOrigin: '60px 60px'
              }}
            />
            <text 
              x="60" 
              y="65" 
              textAnchor="middle" 
              className={styles.confidenceSymbol}
              style={{ fill: color }}
            >
              {percentage}%
            </text>
          </svg>
        </div>
        
        <div className={styles.confidenceDetails}>
          <div 
            className={styles.confidenceLabel}
            style={{ color }}
          >
            {confidenceInfo.category}
          </div>
          <div className={styles.confidenceDescription}>
            {confidenceInfo.description}
          </div>
        </div>
      </div>
    );
  };

  /**
   * Render result indicator
   */
  const renderResultIndicator = () => {
    const isFake = analysisData.isFake;
    
    return (
      <div className={`${styles.resultIndicator} ${isFake ? styles.fakeResult : styles.authenticResult}`}>
        <div className={styles.resultIcon}>
          {isFake ? '🚨' : '✅'}
        </div>
        <div className={styles.resultText}>
          <h3>{isFake ? 'Deepfake Detected' : 'Authentic Video'}</h3>
          <p>{isFake ? 'Content manipulation detected' : 'No signs of manipulation'}</p>
        </div>
      </div>
    );
  };

  /**
   * Render analysis statistics
   */
  const renderAnalysisStats = () => (
    <div className={styles.statsSection}>
      <h4>Analysis Statistics</h4>
      
      <div className={styles.statsGrid}>
        <div className={styles.statItem}>
          <label>Processing Time:</label>
          <span>{formatTimeRemaining(processingStats.processingTime)}</span>
        </div>
        
        <div className={styles.statItem}>
          <label>Speed:</label>
          <span>{processingStats.processingSpeed} fps</span>
        </div>
        
        <div className={styles.statItem}>
          <label>Frames Analyzed:</label>
          <span>{processingStats.framesProcessed} / {processingStats.totalFrames}</span>
        </div>
        
        <div className={styles.statItem}>
          <label>Model:</label>
          <span>{processingStats.modelUsed}</span>
        </div>
      </div>

      {processingStats.totalFrames > 0 && (
        <div className={styles.progressBar}>
          <div 
            className={styles.progressFill}
            style={{ 
              width: `${(processingStats.framesProcessed / processingStats.totalFrames) * 100}%` 
            }}
          />
        </div>
      )}
    </div>
  );

  /**
   * Render video information
   */
  const renderVideoInfo = () => (
    <div className={styles.videoSection}>
      <h4>Video Information</h4>
      
      <div className={styles.videoGrid}>
        {videoInfo.filename && (
          <div className={styles.videoItem}>
            <label>Filename:</label>
            <span>{videoInfo.filename}</span>
          </div>
        )}
        
        {videoInfo.duration && (
          <div className={styles.videoItem}>
            <label>Duration:</label>
            <span>{formatTimeRemaining(videoInfo.duration)}</span>
          </div>
        )}
        
        {videoInfo.size && (
          <div className={styles.videoItem}>
            <label>Size:</label>
            <span>{formatFileSize(videoInfo.size)}</span>
          </div>
        )}
        
        {videoInfo.format && (
          <div className={styles.videoItem}>
            <label>Format:</label>
            <span>{videoInfo.format.toUpperCase()}</span>
          </div>
        )}
        
        {videoInfo.resolution && (
          <div className={styles.videoItem}>
            <label>Resolution:</label>
            <span>{videoInfo.resolution}</span>
          </div>
        )}
        
        {videoInfo.fps && (
          <div className={styles.videoItem}>
            <label>Frame Rate:</label>
            <span>{videoInfo.fps} fps</span>
          </div>
        )}
      </div>
    </div>
  );

  /**
   * Render risk breakdown
   */
  const renderRiskBreakdown = () => {
    if (!confidenceSummary?.distribution) return null;

    const { distribution } = confidenceSummary;
    const total = distribution.lowRisk + distribution.mediumRisk + distribution.highRisk;
    
    if (total === 0) return null;

    const percentages = {
      low: (distribution.lowRisk / total) * 100,
      medium: (distribution.mediumRisk / total) * 100,
      high: (distribution.highRisk / total) * 100
    };

    return (
      <div className={styles.riskSection}>
        <h4>Risk Distribution</h4>
        
        <div className={styles.riskChart}>
          <div 
            className={`${styles.riskSegment} ${styles.lowRisk}`}
            style={{ width: `${percentages.low}%` }}
            title={`${distribution.lowRisk} frames (${percentages.low.toFixed(1)}%)`}
          />
          <div 
            className={`${styles.riskSegment} ${styles.mediumRisk}`}
            style={{ width: `${percentages.medium}%` }}
            title={`${distribution.mediumRisk} frames (${percentages.medium.toFixed(1)}%)`}
          />
          <div 
            className={`${styles.riskSegment} ${styles.highRisk}`}
            style={{ width: `${percentages.high}%` }}
            title={`${distribution.highRisk} frames (${percentages.high.toFixed(1)}%)`}
          />
        </div>
        
        <div className={styles.riskLegend}>
          <div className={styles.riskLegendItem}>
            <div className={`${styles.riskIndicator} ${styles.lowRisk}`} />
            <span>Low Risk ({distribution.lowRisk})</span>
          </div>
          <div className={styles.riskLegendItem}>
            <div className={`${styles.riskIndicator} ${styles.mediumRisk}`} />
            <span>Medium Risk ({distribution.mediumRisk})</span>
          </div>
          <div className={styles.riskLegendItem}>
            <div className={`${styles.riskIndicator} ${styles.highRisk}`} />
            <span>High Risk ({distribution.highRisk})</span>
          </div>
        </div>
      </div>
    );
  };

  // ============================================================================
  // Main Render
  // ============================================================================

  return (
    <div className={`${styles.detectionSummary} ${className}`}>
      {/* Header */}
      <div className={styles.header}>
        <h3>Detection Summary</h3>
        {onExport && (
          <button 
            className={styles.exportButton}
            onClick={onExport}
            title="Export detailed report"
          >
            📋 Export
          </button>
        )}
      </div>

      {/* Main Content */}
      <div className={styles.content}>
        
        {/* Result Indicator */}
        {renderResultIndicator()}

        {/* Confidence Visualization */}
        {renderConfidenceVisualization()}

        {/* Analysis Statistics */}
        {renderAnalysisStats()}

        {/* Risk Breakdown */}
        {renderRiskBreakdown()}

        {/* Video Information */}
        {renderVideoInfo()}

        {/* Additional Technical Details */}
        {analysisData.analysisDetails && Object.keys(analysisData.analysisDetails).length > 0 && (
          <div className={styles.technicalSection}>
            <h4>Technical Details</h4>
            <div className={styles.technicalDetails}>
              {Object.entries(analysisData.analysisDetails).map(([key, value]) => (
                <div key={key} className={styles.detailItem}>
                  <label>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</label>
                  <span>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className={styles.footer}>
        <div className={styles.timestamp}>
          Analysis completed: {new Date(analysisData.timestamp).toLocaleString()}
        </div>
        
        {analysisData.blockchainHash && (
          <div className={styles.blockchainInfo}>
            <span>🔗 Blockchained</span>
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// Export
// ============================================================================

export default DetectionSummary;
