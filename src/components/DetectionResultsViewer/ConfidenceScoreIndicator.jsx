/**
 * ConfidenceScoreIndicator Component
 * Displays the overall confidence score as a circular progress indicator
 */

import React from 'react';
import { parseConfidenceScore } from '../../api/detectionResultsApi';
import styles from './ConfidenceScoreIndicator.module.css';

// ============================================================================
// Component
// ============================================================================

/**
 * ConfidenceScoreIndicator - Displays overall confidence score with visual indicator
 * @param {Object} props - Component properties
 * @param {number} props.confidenceScore - Overall confidence score (0.0-1.0)
 * @param {Object} props.confidenceSummary - Confidence summary data (optional)
 * @param {string} props.className - Additional CSS classes (optional)
 * @returns {JSX.Element} Confidence score indicator component
 */
const ConfidenceScoreIndicator = ({
  confidenceScore,
  confidenceSummary,
  className = ''
}) => {
  // ============================================================================
  // Data Processing
  // ============================================================================
  
  if (typeof confidenceScore !== 'number' || confidenceScore < 0 || confidenceScore > 1) {
    return (
      <div className={`${styles.confidenceScoreIndicator} ${className}`}>
        <div className={styles.noData}>
          <span>Invalid confidence score</span>
        </div>
      </div>
    );
  }

  const confidenceInfo = parseConfidenceScore(confidenceScore);
  const percentage = confidenceInfo.percentage;

  // ============================================================================
  // Render Helpers
  // ============================================================================

  /**
   * Render confidence circle SVG
   */
  const renderConfidenceCircle = () => {
    const radius = 70;
    const circumference = 2 * Math.PI * radius;
    const strokeDasharray = circumference;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    return (
      <div className={styles.confidenceCircle}>
        <svg width="150" height="150" className={styles.confidenceSvg}>
          {/* Background circle */}
          <circle
            cx="75"
            cy="75"
            r={radius}
            stroke="#e5e7eb"
            strokeWidth="12"
            fill="none"
            className={styles.background}
          />
          
          {/* Progress circle */}
          <circle
            cx="75"
            cy="75"
            r={radius}
            stroke={confidenceInfo.color}
            strokeWidth="12"
            fill="none"
            strokeDasharray={strokeDasharray}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className={styles.progress}
            style={{
              transform: 'rotate(-90deg)',
              transformOrigin: 'center',
              transition: 'stroke-dashoffset 0.8s ease-in-out'
            }}
          />
          
          {/* Percentage text */}
          <text
            x="75"
            y="75"
            textAnchor="middle"
            dominantBaseline="central"
            className={styles.percentageText}
            style={{ fill: confidenceInfo.color }}
          >
            {percentage}%
          </text>
          
          {/* Risk level text */}
          <text
            x="75"
            y="95"
            textAnchor="middle"
            dominantBaseline="central"
            className={styles.riskLevelText}
            style={{ color: confidenceInfo.color }}
          >
            {confidenceInfo.category}
          </text>
        </svg>
      </div>
    );
  };

  /**
   * Render summary statistics
   */
  const renderSummaryStats = () => {
    if (!confidenceSummary) return null;

    return (
      <div className={styles.summaryStats}>
        <div className={styles.statItem}>
          <label>Mean Confidence:</label>
          <span>{Math.round(confidenceSummary.mean * 100)}%</span>
        </div>
        
        <div className={styles.statItem}>
          <label>Maximum:</label>
          <span>{Math.round(confidenceSummary.max * 100)}%</span>
        </div>
        
        <div className={styles.statItem}>
          <label>Minimum:</label>
          <span>{Math.round(confidenceSummary.min * 100)}%</span>
        </div>
      </div>
    );
  };

  /**
   * Render confidence level indicator
   */
  const renderConfidenceLevel = () => {
    const riskLevelClass = styles[confidenceInfo.riskLevel];
    
    return (
      <div className={styles.confidenceLevel}>
        <div className={`${styles.levelIndicator} ${riskLevelClass}`} />
        <div className={styles.levelContent}>
          <h4 className={styles.levelTitle}>
            {confidenceInfo.category}
          </h4>
          <p className={styles.levelDescription}>
            {confidenceInfo.description}
          </p>
        </div>
      </div>
    );
  };

  /**
   * Render trend information
   */
  const renderTrend = () => {
    if (!confidenceSummary?.distribution) return null;

    const { distribution } = confidenceSummary;
    const total = distribution.lowRisk + distribution.mediumRisk + distribution.highRisk;
    
    if (total === 0) return null;

    const highRiskPercentage = (distribution.highRisk / total) * 100;
    const mediumRiskPercentage = (distribution.mediumRisk / total) * 100;
    const lowRiskPercentage = (distribution.lowRisk / total) * 100;

    return (
      <div className={styles.trendSection}>
        <h4>Risk Distribution</h4>
        <div className={styles.trendChart}>
          <div className={styles.trendBar}>
            <div 
              className={`${styles.trendSegment} ${styles.lowRisk}`}
              style={{ width: `${lowRiskPercentage}%` }}
              title={`Low Risk: ${distribution.lowRisk} frames (${lowRiskPercentage.toFixed(1)}%)`}
            />
            <div 
              className={`${styles.trendSegment} ${styles.mediumRisk}`}
              style={{ width: `${mediumRiskPercentage}%` }}
              title={`Medium Risk: ${distribution.mediumRisk} frames (${mediumRiskPercentage.toFixed(1)}%)`}
            />
            <div 
              className={`${styles.trendSegment} ${styles.highRisk}`}
              style={{ width: `${highRiskPercentage}%` }}
              title={`High Risk: ${distribution.highRisk} frames (${highRiskPercentage.toFixed(1)}%)`}
            />
          </div>
        </div>
      </div>
    );
  };

  // ============================================================================
  // Main Render
  // ============================================================================

  return (
    <div className={`${styles.confidenceScoreIndicator} ${className}`}>
      {/* Header */}
      <div className={styles.header}>
        <h3>Confidence Analysis</h3>
        <div className={styles.scoreBadge}>
          <span className={styles.scoreValue} style={{ color: confidenceInfo.color }}>
            {percentage}%
          </span>
          <span className={styles.scoreLabel}>Overall</span>
        </div>
      </div>

      {/* Main Content */}
      <div className={styles.content}>
        
        {/* Confidence Circle */}
        {renderConfidenceCircle()}

        {/* Confidence Level */}
        {renderConfidenceLevel()}

        {/* Summary Stats */}
        {renderSummaryStats()}

        {/* Trend */}
        {renderTrend()}
      </div>

      {/* Footer */}
      <div className={styles.footer}>
        <div className={styles.footerInfo}>
          <span className={styles.scoreInterpretation}>
            {percentage >= 70 ? 'High confidence detection' : 
             percentage >= 30 ? 'Moderate confidence detection' : 
             'Low confidence detection'}
          </span>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// Export
// ============================================================================

export default ConfidenceScoreIndicator;
