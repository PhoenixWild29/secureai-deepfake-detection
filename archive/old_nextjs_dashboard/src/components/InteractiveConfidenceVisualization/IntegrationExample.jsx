/**
 * InteractiveConfidenceVisualization Integration Example
 * Shows how to integrate the component with existing detection results
 */

import React, { useState, useEffect, useCallback } from 'react';
import InteractiveConfidenceVisualization from './InteractiveConfidenceVisualization';
import { frameAnalysisGridIntegration } from './integrations/frameAnalysisGridIntegration';
import { resultExportInterfaceIntegration } from './integrations/resultExportInterfaceIntegration';

// ============================================================================
// Integration Example Component
// ============================================================================

const InteractiveConfidenceVisualizationIntegrationExample = () => {
  const [analysisId, setAnalysisId] = useState(null);
  const [frameData, setFrameData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // ============================================================================
  // Data Loading
  // ============================================================================

  /**
   * Load analysis data from API
   */
  const loadAnalysisData = useCallback(async (analysisId) => {
    setLoading(true);
    setError(null);

    try {
      // Simulate API call to get detection results
      const response = await fetch(`/api/v1/results/${analysisId}`);
      if (!response.ok) {
        throw new Error(`Failed to load analysis: ${response.statusText}`);
      }

      const result = await response.json();
      
      // Transform API response to frame data format
      const transformedFrameData = transformApiResponseToFrameData(result);
      setFrameData(transformedFrameData);
      
    } catch (err) {
      console.error('Error loading analysis data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Transform API response to frame data format
   */
  const transformApiResponseToFrameData = (apiResult) => {
    const frameData = [];
    
    // Extract confidence per frame from API response
    const confidencePerFrame = apiResult.details?.confidence_per_frame || [];
    const frameArtifacts = apiResult.details?.frame_artifacts || [];
    const suspiciousRegions = apiResult.details?.suspicious_regions || [];
    
    confidencePerFrame.forEach((confidence, index) => {
      frameData.push({
        frameNumber: index,
        confidence: confidence,
        timestamp: index / 30, // Assuming 30 FPS
        algorithm: 'ensemble',
        suspiciousRegions: suspiciousRegions.filter(region => 
          region.frame_number === index
        ).map(region => ({
          regionId: `region_${index}_${region.id}`,
          coordinates: region.coordinates,
          confidence: region.confidence,
          description: region.description,
          artifactType: region.artifact_type,
          severity: region.severity
        })),
        artifacts: frameArtifacts[index] || {},
        processingTime: apiResult.processing_time_ms / confidencePerFrame.length
      });
    });

    return frameData;
  };

  // ============================================================================
  // Event Handlers
  // ============================================================================

  /**
   * Handle frame selection from chart
   */
  const handleFrameSelect = useCallback((frameInfo) => {
    console.log('Frame selected from chart:', frameInfo);
    
    // Navigate to frame in FrameAnalysisGrid
    frameAnalysisGridIntegration.navigateToFrame(frameInfo.frameNumber, {
      highlight: true,
      scrollIntoView: true,
      callback: (frameNumber, element) => {
        console.log(`Navigated to frame ${frameNumber}`, element);
      }
    });
  }, []);

  /**
   * Handle data export
   */
  const handleDataExport = useCallback(async (data, format) => {
    console.log('Exporting chart data:', format);
    
    try {
      const exportResult = await resultExportInterfaceIntegration.exportChartData(data, format);
      
      // Create download link
      const blob = new Blob([exportResult.data], { type: exportResult.mimeType });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `confidence_chart_${analysisId}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      console.log('Export completed:', exportResult);
    } catch (error) {
      console.error('Export failed:', error);
    }
  }, [analysisId]);

  /**
   * Handle errors
   */
  const handleError = useCallback((errorType, errorMessage) => {
    console.error('Chart error:', errorType, errorMessage);
    setError(`${errorType}: ${errorMessage}`);
  }, []);

  // ============================================================================
  // Effects
  // ============================================================================

  // Load data when analysisId changes
  useEffect(() => {
    if (analysisId) {
      loadAnalysisData(analysisId);
    }
  }, [analysisId, loadAnalysisData]);

  // Initialize integrations
  useEffect(() => {
    // Initialize frame analysis grid integration
    // In a real app, you would get the grid instance from context or props
    frameAnalysisGridIntegration.initialize(null); // Placeholder
    
    return () => {
      // Cleanup
      frameAnalysisGridIntegration.destroy();
    };
  }, []);

  // ============================================================================
  // Render Functions
  // ============================================================================

  const renderAnalysisSelector = () => (
    <div style={{ 
      padding: '20px', 
      background: '#f8fafc', 
      borderBottom: '1px solid #e2e8f0' 
    }}>
      <h3>Select Analysis to Visualize</h3>
      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
        <input
          type="text"
          placeholder="Enter Analysis ID"
          value={analysisId || ''}
          onChange={(e) => setAnalysisId(e.target.value)}
          style={{
            padding: '8px 12px',
            border: '1px solid #d1d5db',
            borderRadius: '6px',
            fontSize: '14px'
          }}
        />
        <button
          onClick={() => analysisId && loadAnalysisData(analysisId)}
          disabled={!analysisId || loading}
          style={{
            padding: '8px 16px',
            background: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.6 : 1
          }}
        >
          {loading ? 'Loading...' : 'Load Analysis'}
        </button>
      </div>
    </div>
  );

  const renderError = () => (
    <div style={{ 
      padding: '20px', 
      background: '#fef2f2', 
      border: '1px solid #fecaca',
      borderRadius: '8px',
      margin: '20px'
    }}>
      <h3 style={{ color: '#dc2626', margin: '0 0 8px 0' }}>Error</h3>
      <p style={{ color: '#7f1d1d', margin: 0 }}>{error}</p>
      <button
        onClick={() => setError(null)}
        style={{
          marginTop: '12px',
          padding: '6px 12px',
          background: '#dc2626',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        Dismiss
      </button>
    </div>
  );

  const renderVisualization = () => {
    if (!analysisId) {
      return (
        <div style={{ 
          padding: '40px', 
          textAlign: 'center', 
          color: '#6b7280' 
        }}>
          <h3>No Analysis Selected</h3>
          <p>Enter an analysis ID above to load confidence visualization</p>
        </div>
      );
    }

    if (loading) {
      return (
        <div style={{ 
          padding: '40px', 
          textAlign: 'center' 
        }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '4px solid #e2e8f0',
            borderTop: '4px solid #3b82f6',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 16px'
          }} />
          <p>Loading analysis data...</p>
        </div>
      );
    }

    if (frameData.length === 0) {
      return (
        <div style={{ 
          padding: '40px', 
          textAlign: 'center', 
          color: '#6b7280' 
        }}>
          <h3>No Frame Data Available</h3>
          <p>This analysis doesn't contain frame-level confidence data</p>
        </div>
      );
    }

    return (
      <InteractiveConfidenceVisualization
        analysisId={analysisId}
        frameData={frameData}
        config={{
          defaultMode: 'line_chart',
          enableZoom: true,
          enablePan: true,
          enableTooltips: true,
          frameRate: 30,
          movingAveragePeriod: 10,
          confidenceThresholds: {
            low: 0.0,
            medium: 0.4,
            high: 0.7,
            critical: 0.9
          },
          exportFormats: ['json', 'csv', 'png']
        }}
        onFrameSelect={handleFrameSelect}
        onDataExport={handleDataExport}
        onError={handleError}
      />
    );
  };

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
      {/* Analysis Selector */}
      {renderAnalysisSelector()}
      
      {/* Error Display */}
      {error && renderError()}
      
      {/* Main Visualization */}
      <div style={{ flex: 1, minHeight: 0 }}>
        {renderVisualization()}
      </div>
      
      {/* Integration Status */}
      <div style={{ 
        padding: '12px 20px', 
        background: '#f3f4f6', 
        borderTop: '1px solid #d1d5db',
        fontSize: '12px',
        color: '#6b7280'
      }}>
        <strong>Integration Status:</strong> FrameAnalysisGrid: {frameAnalysisGridIntegration.getStatus().initialized ? 'Connected' : 'Disconnected'} | 
        Export Interface: {resultExportInterfaceIntegration.getStatus().activeExports} active exports
      </div>
    </div>
  );
};

export default InteractiveConfidenceVisualizationIntegrationExample;
