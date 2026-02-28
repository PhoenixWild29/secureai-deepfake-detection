/**
 * InteractiveConfidenceVisualization Test Component
 * Test component to verify the InteractiveConfidenceVisualization functionality
 */

import React, { useState, useCallback } from 'react';
import InteractiveConfidenceVisualization, { CHART_MODES, TREND_TYPES } from './InteractiveConfidenceVisualization';
import './InteractiveConfidenceVisualization.module.css';

// ============================================================================
// Test Data Generator
// ============================================================================

/**
 * Generate mock confidence data for testing
 */
const generateMockConfidenceData = (frameCount = 100, frameRate = 30) => {
  const data = [];
  const algorithms = ['ensemble', 'quality_agnostic', 'clip_based', 'dm_aware'];
  
  for (let i = 0; i < frameCount; i++) {
    const timestamp = i / frameRate;
    
    // Generate realistic confidence patterns
    let confidence;
    if (i < 10) {
      // Low confidence at start
      confidence = 0.1 + Math.random() * 0.2;
    } else if (i > 80) {
      // High confidence at end (potential fake)
      confidence = 0.7 + Math.random() * 0.3;
    } else {
      // Variable confidence in middle
      confidence = 0.2 + Math.random() * 0.6;
    }
    
    // Add some noise
    confidence += (Math.random() - 0.5) * 0.1;
    confidence = Math.max(0, Math.min(1, confidence));
    
    data.push({
      frameNumber: i,
      confidence: confidence,
      timestamp: timestamp,
      algorithm: algorithms[i % algorithms.length],
      suspiciousRegions: confidence > 0.7 ? [
        {
          regionId: `region_${i}_1`,
          coordinates: { x: 100, y: 100, width: 50, height: 50 },
          confidence: confidence * 100,
          description: 'Potential face manipulation',
          artifactType: 'face_synthesis',
          severity: confidence > 0.9 ? 'critical' : 'high'
        }
      ] : [],
      artifacts: {
        compression: Math.random() * 0.5,
        temporal: Math.random() * 0.3,
        spatial: Math.random() * 0.4
      },
      processingTime: 10 + Math.random() * 20
    });
  }
  
  return data;
};

// ============================================================================
// Test Component
// ============================================================================

const InteractiveConfidenceVisualizationTest = () => {
  const [analysisId] = useState('test_analysis_001');
  const [frameData] = useState(() => generateMockConfidenceData(150, 30));
  const [selectedFrames, setSelectedFrames] = useState([]);
  const [exportedData, setExportedData] = useState(null);
  const [errors, setErrors] = useState([]);

  // ============================================================================
  // Event Handlers
  // ============================================================================

  const handleFrameSelect = useCallback((frameInfo) => {
    console.log('Frame selected:', frameInfo);
    setSelectedFrames(prev => {
      const exists = prev.find(f => f.frameNumber === frameInfo.frameNumber);
      if (exists) {
        return prev.filter(f => f.frameNumber !== frameInfo.frameNumber);
      } else {
        return [...prev, frameInfo];
      }
    });
  }, []);

  const handleDataExport = useCallback((data, format) => {
    console.log('Data exported:', { format, dataSize: JSON.stringify(data).length });
    setExportedData({ format, timestamp: new Date().toISOString(), dataSize: JSON.stringify(data).length });
  }, []);

  const handleError = useCallback((errorType, errorMessage) => {
    console.error('Error occurred:', errorType, errorMessage);
    setErrors(prev => [...prev, { type: errorType, message: errorMessage, timestamp: new Date().toISOString() }]);
  }, []);

  // ============================================================================
  // Test Configuration
  // ============================================================================

  const testConfig = {
    defaultMode: CHART_MODES.LINE_CHART,
    enableZoom: true,
    enablePan: true,
    enableTooltips: true,
    enableAnimation: true,
    frameRate: 30,
    movingAveragePeriod: 15,
    confidenceThresholds: {
      low: 0.0,
      medium: 0.4,
      high: 0.7,
      critical: 0.9
    },
    enableVirtualization: true,
    maxDataPoints: 200,
    animationDuration: 300,
    exportFormats: ['json', 'csv', 'png'],
    exportResolution: { width: 1920, height: 1080 }
  };

  // ============================================================================
  // Render Functions
  // ============================================================================

  const renderTestControls = () => (
    <div style={{ 
      padding: '20px', 
      background: '#f8fafc', 
      borderBottom: '1px solid #e2e8f0',
      display: 'flex',
      flexWrap: 'wrap',
      gap: '16px',
      alignItems: 'center'
    }}>
      <div>
        <strong>Test Controls:</strong>
      </div>
      
      <div>
        <label>
          Data Points: {frameData.length}
        </label>
      </div>
      
      <div>
        <label>
          Selected Frames: {selectedFrames.length}
        </label>
      </div>
      
      <div>
        <label>
          Exports: {exportedData ? `${exportedData.format} (${exportedData.dataSize} bytes)` : 'None'}
        </label>
      </div>
      
      <div>
        <label>
          Errors: {errors.length}
        </label>
      </div>
    </div>
  );

  const renderSelectedFrames = () => {
    if (selectedFrames.length === 0) return null;
    
    return (
      <div style={{ 
        padding: '16px', 
        background: '#f0f9ff', 
        borderTop: '1px solid #bae6fd' 
      }}>
        <h4 style={{ margin: '0 0 12px 0', color: '#0369a1' }}>
          Selected Frames ({selectedFrames.length})
        </h4>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {selectedFrames.map((frame, index) => (
            <span
              key={index}
              style={{
                padding: '4px 12px',
                background: '#3b82f6',
                color: '#ffffff',
                borderRadius: '16px',
                fontSize: '12px',
                fontWeight: '500'
              }}
            >
              Frame {frame.frameNumber} ({(frame.confidence * 100).toFixed(1)}%)
            </span>
          ))}
        </div>
      </div>
    );
  };

  const renderErrors = () => {
    if (errors.length === 0) return null;
    
    return (
      <div style={{ 
        padding: '16px', 
        background: '#fef2f2', 
        borderTop: '1px solid #fecaca' 
      }}>
        <h4 style={{ margin: '0 0 12px 0', color: '#dc2626' }}>
          Errors ({errors.length})
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {errors.slice(-5).map((error, index) => (
            <div
              key={index}
              style={{
                padding: '8px 12px',
                background: '#ffffff',
                border: '1px solid #fecaca',
                borderRadius: '6px',
                fontSize: '12px'
              }}
            >
              <strong>{error.type}:</strong> {error.message}
              <br />
              <small style={{ color: '#6b7280' }}>{error.timestamp}</small>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderTestInfo = () => (
    <div style={{ 
      padding: '16px', 
      background: '#f3f4f6', 
      borderTop: '1px solid #d1d5db',
      fontSize: '12px',
      color: '#6b7280',
      fontFamily: 'Monaco, Menlo, Ubuntu Mono, monospace'
    }}>
      <div><strong>Test Information:</strong></div>
      <div>• Interactive confidence visualization with {frameData.length} data points</div>
      <div>• Supports zoom, pan, tooltips, and frame selection</div>
      <div>• Multiple chart modes: {Object.values(CHART_MODES).join(', ')}</div>
      <div>• Trend analysis: {Object.values(TREND_TYPES).join(', ')}</div>
      <div>• Export formats: {testConfig.exportFormats.join(', ')}</div>
      <div>• Click on data points to select frames, hover for tooltips</div>
    </div>
  );

  // ============================================================================
  // Main Render
  // ============================================================================

  return (
    <div style={{ 
      width: '100%', 
      height: '100vh', 
      display: 'flex', 
      flexDirection: 'column',
      fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif'
    }}>
      {/* Test Controls */}
      {renderTestControls()}
      
      {/* Main Visualization */}
      <div style={{ flex: 1, minHeight: 0 }}>
        <InteractiveConfidenceVisualization
          analysisId={analysisId}
          frameData={frameData}
          config={testConfig}
          onFrameSelect={handleFrameSelect}
          onDataExport={handleDataExport}
          onError={handleError}
          className="test-visualization"
        />
      </div>
      
      {/* Selected Frames */}
      {renderSelectedFrames()}
      
      {/* Errors */}
      {renderErrors()}
      
      {/* Test Info */}
      {renderTestInfo()}
    </div>
  );
};

export default InteractiveConfidenceVisualizationTest;
