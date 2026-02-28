/**
 * ConfidenceScoreDashboard Component
 * Visual confidence indicators with frame-level data visualization
 */

import React from 'react';
import styles from './ConfidenceScoreDashboard.module.css';

const ConfidenceScoreDashboard = ({
  frameData = [],
  currentFrame = null,
  selectedFrameIndex = 0,
  distribution = { low: 0, medium: 0, high: 0, critical: 0 },
  animation = false,
  showDetailed = true,
  height = 200,
  interactive = false
}) => {
  
  const renderDistributionChart = () => (
    <div className={styles.distributionChart}>
      <div className={styles.chartBar}>
        <div 
          className={`${styles.bar} ${styles.low}`} 
          style={{ height: `${(distribution.low / Object.values(distribution).reduce((a, b) => a + b, 0)) * 100}%` }}
        />
        <div 
          className={`${styles.bar} ${styles.medium}`} 
          style={{ height: `${(distribution.medium / Object.values(distribution).reduce((a, b) => a + b, 0)) * 100}%` }}
        />
        <div 
          className={`${styles.bar} ${styles.high}`} 
          style={{ height: `${(distribution.high / Object.values(distribution).reduce((a, b) => a + b, 0)) * 100}%` }}
        />
        <div 
          className={`${styles.bar} ${styles.critical}`} 
          style={{ height: `${(distribution.critical / Object.values(distribution).reduce((a, b) => a + b, 0)) * 100}%` }}
        />
      </div>
      <div className={styles.labels}>
        <span className={styles.label}>Low</span><span className={styles.label}>Medium</span>
        <span className={styles.label}>High</span><span className={styles.label}>Critical</span>
      </div>
    </div>
  );

  return (
    <div className={styles.confidenceDashboard} style={{ height }}>
      <h3>Confidence Distribution</h3>
      {renderDistributionChart()}
      
      {showDetailed && currentFrame && (
        <div className={styles.frameDetails}>
          <h4>Current Frame: {currentFrame.frame_number}</h4>
          <div className={styles.confidenceScore}>
            {(currentFrame.confidence_score * 100).toFixed(1)}%
          </div>
        </div>
      )}
    </div>
  );
};

export { ConfidenceScoreDashboard };
export default ConfidenceScoreDashboard;
