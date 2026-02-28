/**
 * SummaryDashboardView Component
 * Dashboard visualization mode showing overall detection metrics and confidence distributions
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { ConfidenceScoreDashboard } from '../visualization/ConfidenceScoreDashboard';
import styles from './SummaryDashboardView.module.css';

// ============================================================================
// Main Component
// ============================================================================

/**
 * SummaryDashboardView - Comprehensive overview of detection analysis results
 * 
 * @param {Object} props - Component properties
 * @param {string} props.analysisId - Analysis identifier
 * @param {Object} props.detectionData - Main detection results data
 * @param {Array} props.frameAnalysisData - Frame-level analysis data
 * @param {Object} props.blockchainStatus - Blockchain verification status
 * @param {Object} props.loadingState - Loading states for different data types
 * @param {Object} props.config - Configuration options
 * @param {Function} props.onExport - Export callback
 * @param {Function} props.onError - Error callback
 * @param {Component} props.ConfidenceScoreDashboard - Confidence dashboard component
 * @returns {JSX.Element} Summary dashboard view component
 */
const SummaryDashboardView = ({
  analysisId,
  detectionData,
  frameAnalysisData,
  blockchainStatus,
  loadingState,
  config,
  onExport,
  onError,
  ConfidenceScoreDashboard
}) => {
  
  // ============================================================================
  // State Management
  // ============================================================================
  
  const [selectedMetric, setSelectedMetric] = useState('overall');
  const [timeRangeFilter, setTimeRangeFilter] = useState('all');
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.7);
  const [chartAnimation, setChartAnimation] = useState(false);

  // ============================================================================
  // Computed Data
  // ============================================================================

  /**
   * Calculate comprehensive detection metrics
   */
  const detectionMetrics = useMemo(() => {
    if (!detectionData || !frameAnalysisData) {
      return {
        overall: { confidence: 0, riskLevel: 'unknown', authenticated: false, synthetic: false },
        byFrame: [],
        distribution: { low: 0, medium: 0, high: 0, critical: 0 },
        timeline: [],
        regions: []
      };
    }

    // Overall metrics
    const overallConfidence = detectionData.confidence_score || detectionData.score || 0;
    const riskLevel = overallConfidence >= 0.9 ? 'critical' : 
                    overallConfidence >= 0.7 ? 'high' : 
                    overallConfidence >= 0.4 ? 'medium' : 'low';
    
    // Frame-level analysis
    const frameMetrics = frameAnalysisData.map(frame => ({
      frameNumber: frame.frame_number || 0,
      confidence: frame.confidence_score || 0,
      timestamp: (frame.frame_number || 0) / 30, // Assuming 30 FPS
      suspiciousRegions: frame.suspicious_regions || [],
      artifacts: frame.artifacts || {}
    }));

    // Confidence distribution
    const distribution = frameMetrics.reduce((acc, frame) => {
      const conf = frame.confidence;
      if (conf >= 0.9) acc.critical++;
      else if (conf >= 0.7) acc.high++;
      else if (conf >= 0.4) acc.medium++;
      else acc.low++;
      return acc;
    }, { low: 0, medium: 0, high: 0, critical: 0 });

    // Timeline data for charts
    const timeline = frameMetrics.map(frame => ({
      time: frame.timestamp,
      confidence: frame.confidence,
      riskLevel: frame.confidence >= 0.7 ? 'high' : frame.confidence >= 0.4 ? 'medium' : 'low'
    }));

    // Suspicious regions aggregation
    const regions = frameMetrics
      .flatMap(frame => frame.suspiciousRegions.map(region => ({
        ...region,
        frameNumber: frame.frameNumber,
        timestamp: frame.timestamp
      })))
      .reduce((acc, region) => {
        const key = `${region.x}_${region.y}_${region.width}_${region.height}`;
        if (!acc[key]) {
          acc[key] = { ...region, frequency: 0 };
        }
        acc[key].frequency++;
        return acc;
      }, {});

    return {
      overall: {
        confidence: overallConfidence,
        riskLevel,
        authenticated: detectionData.blockchain_hash ? true : false,
        synthetic: detectionData.is_fake || detectionData.decision === 'deepfake',
        totalFrames: frameAnalysisData.length,
        processingTime: detectionData.processing_time_ms || 0
      },
      byFrame: frameMetrics,
      distribution,
      timeline,
      regions: Object.values(regions)
    };
  }, [detectionData, frameAnalysisData]);

  /**
   * Calculate blockchain verification metrics
   */
  const blockchainMetrics = useMemo(() => {
    if (!blockchainStatus) {
      return {
        status: 'unknown',
        progress: 0,
        hashValue: null,
        verificationTime: null,
        network: 'unknown',
        cost: { gas: 0, token: 0 },
        reliability: 0
      };
    }

    return {
      status: blockchainStatus.status || 'unknown',
      progress: blockchainStatus.progress || 0,
      hashValue: blockchainStatus.hash_value || blockchainStatus.transaction_hash,
      verificationTime: blockchainStatus.verification_time_ms,
      network: blockchainStatus.network || 'ethereum',
      cost: {
        gas: blockchainStatus.gas_used || 0,
        token: blockchainStatus.token_cost || 0
      },
      reliability: blockchainStatus.node_agreement_percentage || 0
    };
  }, [blockchainStatus]);

  /**
   * Filter data based on selected criteria
   */
  const filteredData = useMemo(() => {
    let filtered = { ...detectionMetrics };
    
    // Apply confidence threshold filter
    if (confidenceThreshold > 0) {
      filtered.byFrame = filtered.byFrame.filter(frame => 
        frame.confidence >= confidenceThreshold
      );
      filtered.timeline = filtered.timeline.filter(frame => 
        frame.confidence >= confidenceThreshold
      );
    }
    
    // Apply time range filter
    if (timeRangeFilter !== 'all') {
      const maxTime = filtered.byFrame.length > 0 ? Math.max(...filtered.byFrame.map(f => f.timestamp)) : 0;
      const timeRanges = {
        'first_quarter': maxTime * 0.25,
        'second_quarter': maxTime * 0.5,
        'third_quarter': maxTime * 0.75,
        'last_quarter': maxTime
      };
      
      const cutoff = timeRanges[timeRangeFilter] || maxTime;
      filtered.byFrame = filtered.byFrame.filter(frame => frame.timestamp <= cutoff);
      filtered.timeline = filtered.timeline.filter(frame => frame.timestamp <= cutoff);
    }
    
    return filtered;
  }, [detectionMetrics, confidenceThreshold, timeRangeFilter]);

  // ============================================================================
  // Effects
  // ============================================================================

  /**
   * Trigger chart animations
   */
  useEffect(() => {
    if (detectionMetrics.overall.confidence > 0) {
      setChartAnimation(false);
      setTimeout(() => setChartAnimation(true), 100);
    }
  }, [detectionMetrics]);

  // ============================================================================
  // Render Functions
  // ============================================================================

  /**
   * Render overall metrics summary cards
   */
  const renderSummarycards = () => {
    const metrics = filteredData.overall;
    
    const metricsCards = [
      {
        title: 'Overall Confidence',
        value: `${(metrics.confidence * 100).toFixed(1)}%`,
        status: metrics.riskLevel,
        icon: '🎯',
        description: `Detected as ${metrics.synthetic ? 'deepfake' : 'authentic'} content`
      },
      {
        title: 'Risk Assessment',
        value: metrics.riskLevel.toUpperCase(),
        status: metrics.riskLevel,
        icon: metrics.riskLevel === 'critical' ? '🚨' : metrics.riskLevel === 'high' ? '⚠️' : metrics.riskLevel === 'medium' ? '📊' : '✅',
        description: `${filteredData.distribution[metrics.riskLevel] || 0} frames at ${metrics.riskLevel} risk level`
      },
      {
        title: 'Blockchain Status',
        value: blockchainMetrics.status,
        status: blockchainMetrics.status,
        icon: blockchainMetrics.status === 'verified' ? '✔️' : blockchainMetrics.status === 'pending' ? '⏳' : '❌',
        description: blockchainMetrics.hashValue ? `Hash: ${blockchainMetrics.hashValue.slice(0, 8)}...` : 'No hash recorded'
      },
      {
        title: 'Analysis Scope',
        value: `${metrics.totalFrames} frames`,
        status: 'info',
        icon: '🎬',
        description: `Processed in ${(metrics.processingTime / 1000).toFixed(1)}s`
      }
    ];

    return (
      <div className={styles.summarycards}>
        {metricsCards.map((card, index) => (
          <div 
            key={index} 
            className={`${styles.metriccard} ${styles[card.status]}`}
            style={{ animationDelay: `${index * 100}ms` }}
          >
            <div className={styles.cardHeader}>
              <span className={styles.cardIcon}>{card.icon}</span>
              <h3 className={styles.cardTitle}>{card.title}</h3>
            </div>
            <div className={styles.cardValue}>{card.value}</div>
            <div className={styles.cardDescription}>{card.description}</div>
          </div>
        ))}
      </div>
    );
  };

  /**
   * Render confidence distribution chart
   */
  const renderConfidenceDistribution = () => (
    <div className={styles.distributionChart}>
      <h3>Confidence Distribution</h3>
      <ConfidenceScoreDashboard
        frameData={filteredData.byFrame}
        distribution={filteredData.distribution}
        overallConfidence={filteredData.overall.confidence}
        animation={chartAnimation}
        showDetailed={true}
        height={200}
      />
    </div>
  );

  /**
   * Render blockchain verification details
   */
  const renderBlockchainDetails = () => (
    <div className={styles.blockchainDetails}>
      <h3>Blockchain Verification</h3>
      <div className={styles.blockchainStatus}>
        <div className={`${styles.statusIndicator} ${styles[blockchainMetrics.status]}`}>
          <div className={styles.statusProgress}>
            <div 
              className={styles.progressBar} 
              style={{ width: `${blockchainMetrics.progress}%` }}
            />
          </div>
          <span className={styles.statusText}>
            {blockchainMetrics.status.toUpperCase()} ({blockchainMetrics.progress}%)
          </span>
        </div>
        
        {blockchainMetrics.hashValue && (
          <div className={styles.blockchainInfo}>
            <div className={styles.infoItem}>
              <label>Hash:</label>
              <code>{blockchainMetrics.hashValue.slice(0, 16)}...{blockchainMetrics.hashValue.slice(-8)}</code>
            </div>
            <div className={styles.infoItem}>
              <label>Network:</label>
              <span>{blockchainMetrics.network}</span>
            </div>
            <div className={styles.infoItem}>
              <label>Reliability:</label>
              <span>{blockchainMetrics.reliability}% agreement</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  /**
   * Render suspicious regions summary
   */
  const renderSuspiciousRegionSummary = () => {
    const topRegions = filteredData.regions
      .sort((a, b) => b.frequency - a.frequency)
      .slice(0, 5);

    return (
      <div className={styles.suspiciousRegionSummary}>
        <h3>Top Suspicious Regions</h3>
        <div className={styles.regionsList}>
          {topRegions.length > 0 ? (
            topRegions.map((region, index) => (
              <div key={index} className={styles.regionItem}>
                <div className={styles.regionCoordinate}>
                  ({region.x}, {region.y}) - {region.width}x{region.height}
                </div>
                <div className={styles.regionFrequency}>
                  {region.frequency} frame{region.frequency !== 1 ? 's' : ''}
                </div>
                <div className={styles.regionConfidence}>
                  {(region.confidence * 100).toFixed(1)}% confident
                </div>
              </div>
            ))
          ) : (
            <div className={styles.noRegions}>
              No suspicious regions detected above threshold
            </div>
          )}
        </div>
      </div>
    );
  };

  /**
   * Render filter controls
   */
  const renderFilterControls = () => (
    <div className={styles.filterControls}>
      <div className={styles.filterGroup}>
        <label>Confidence Threshold:</label>
        <input
          type="range"
          min="0"
          max="1"
          step="0.1"
          value={confidenceThreshold}
          onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
          className={styles.thresholdSlider}
        />
        <span className={styles.thresholdValue}>{(confidenceThreshold * 100).toFixed(0)}%</span>
      </div>
      
      <div className={styles.filterGroup}>
        <label>Time Range:</label>
        <select 
          value={timeRangeFilter} 
          onChange={(e) => setTimeRangeFilter(e.target.value)}
          className={styles.timeRangeSelect}
        >
          <option value="all">All Time</option>
          <option value="first_quarter">First 25%</option>
          <option value="second_quarter">First 50%</option>
          <option value="third_quarter">First 75%</option>
          <option value="last_quarter">Complete Analysis</option>
        </select>
      </div>
      
      <div className={styles.filterGroup}>
        <label>Metric Focus:</label>
        <select 
          value={selectedMetric} 
          onChange={(e) => setSelectedMetric(e.target.value)}
          className={styles.metricSelect}
        >
          <option value="overall">Overall Analysis</option>
          <option value="frames">Frame-level Details</option>
          <option value="regions">Suspicious Regions</option>
          <option value="timeline">Timeline Analysis</option>
        </select>
      </div>
    </div>
  );

  // ============================================================================
  // Main Render
  // ============================================================================

  if (loadingState.detection) {
    return (
      <div className={styles.loadingState}>
        <div className={styles.loadingSpinner} />
        <p>Loading detection results for summarization...</p>
      </div>
    );
  }

  if (!detectionData) {
    return (
      <div className={styles.errorState}>
        <div className={styles.errorIcon}>📊</div>
        <h3>No Detection Data Available</h3>
        <p>Unable to load detection results for analysis summary.</p>
      </div>
    );
  }

  return (
    <div className={styles.summaryDashboard}>
      {/* Header */}
      <div className={styles.dashboardHeader}>
        <h2>Detection Analysis Summary</h2>
        <p>Comprehensive overview of deepfake detection results and confidence metrics</p>
      </div>

      {/* Filter Controls */}
      {renderFilterControls()}

      {/* Summary Cards */}
      {renderSummarycards()}

      {/* Main Content Areas */}
      <div className={styles.dashboardContent}>
        <div className={styles.leftColumn}>
          {/* Confidence Distribution */}
          {config.showConfidenceDashboard && renderConfidenceDistribution()}
          
          {/* Blockchain Details */}
          {config.showBlockchainStatus && blockchainMetrics.status !== 'unknown' && renderBlockchainDetails()}
        </div>
        
        <div className={styles.rightColumn}>
          {/* Suspicious Regions Summary */}
          {renderSuspiciousRegionSummary()}
          
          {/* Analysis Metadata */}
          <div className={styles.analysisMetadata}>
            <h3>Analysis Details</h3>
            <div className={styles.metadataGrid}>
              <div className={styles.metadataItem}>
                <label>Analysis ID:</label>
                <code>{analysisId}</code>
              </div>
              <div className={styles.metadataItem}>
                <label>Total Frames:</label>
                <span>{detectionMetrics.overall.totalFrames}</span>
              </div>
              <div className={styles.metadataItem}>
                <label>Processing Time:</label>
                <span>{(detectionMetrics.overall.processingTime / 1000).toFixed(2)}s</span>
              </div>
              <div className={styles.metadataItem}>
                <label>Generated:</label>
                <span>{new Date(detectionData.created_at || Date.now()).toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// Exports
// ============================================================================

export { SummaryDashboardView };
export default SummaryDashboardView;
