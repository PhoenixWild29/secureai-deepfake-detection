/**
 * ExportPreviewMode Component
 * Export preview visualization mode showing formatted results ready for export
 */

import React, { useState, useMemo, useCallback } from 'react';
import styles from './ExportPreviewMode.module.css';

/**
 * ExportPreviewMode - Formatted view for export preparation
 * 
 * @param {Object} props - Component properties
 * @param {string} props.analysisId - Analysis identifier
 * @param {Object} props.detectionData - Main detection results data
 * @param {Array} props.frameAnalysisData - Frame-level analysis data
 * @param {Object} props.blockchainStatus - Blockchain verification status
 * @param {Array} props.exportFormats - Available export formats
 * @param {string} props.exportPreviewMode - Preview mode type
 * @param {Function} props.onExport - Export callback
 * @returns {JSX.Element} Export preview mode component
 */
const ExportPreviewMode = ({
  analysisId,
  detectionData,
  frameAnalysisData,
  blockchainStatus,
  exportFormats = ['pdf', 'json', 'csv'],
  exportPreviewMode = 'detailed',
  onExport
}) => {
  
  const [selectedFormat, setSelectedFormat] = useState(exportFormats[0]);
  const [includeFrames, setIncludeFrames] = useState(true);
  const [includeBlockchain, setIncludeBlockchain] = useState(true);

  // Generate formatted export preview
  const exportPreview = useMemo(() => {
    if (!detectionData) return null;

    const preview = {
      analysis_summary: {
        analysis_id: analysisId,
        overall_confidence: detectionData.confidence_score || detectionData.score || 0,
        is_fake: detectionData.is_fake || false,
        total_frames: frameAnalysisData?.length || 0,
        processing_time: detectionData.processing_time_ms || 0
      },
      frame_summary: null,
      blockchain_summary: null,
      export_metadata: {
        generated_at: new Date().toISOString(),
        preview_format: selectedFormat,
        version: '1.0'
      }
    };

    if (includeFrames && frameAnalysisData) {
      preview.frame_summary = {
        frame_count: frameAnalysisData.length,
        confidence_distribution: frameAnalysisData.reduce((acc, frame) => {
          const conf = frame.confidence_score;
          if (conf >= 0.9) acc.critical++;
          else if (conf >= 0.7) acc.high++;
          else if (conf >= 0.4) acc.medium++;
          else acc.low++;
          return acc;
        }, { low: 0, medium: 0, high: 0, critical: 0 }),
        sample_frames: frameAnalysisData.slice(0, 5).map(frame => ({
          frame_number: frame.frame_number,
          confidence: frame.confidence_score,
          suspicious_regions: frame.suspicious_regions?.length || 0
        }))
      };
    }

    if (includeBlockchain && blockchainStatus) {
      preview.blockchain_summary = {
        status: blockchainStatus.status,
        hash: blockchainStatus.hash_value,
        verification_timestamp: blockchainStatus.verification_time_ms,
        network: blockchainStatus.network
      };
    }

    return preview;
  }, [detectionData, frameAnalysisData, blockchainStatus, selectedFormat, includeFrames, includeBlockchain]);

  const handleExport = useCallback(() => {
    if (onExport && exportPreview) {
      onExport({
        format: selectedFormat,
        data: exportPreview,
        analysisId
      });
    }
  }, [onExport, exportPreview, selectedFormat, analysisId]);

  const renderExportOptions = () => (
    <div className={styles.exportOptions}>
      <h3>Export Configuration</h3>
      
      <div className={styles.formatSelection}>
        <label>Export Format:</label>
        <select 
          value={selectedFormat} 
          onChange={(e) => setSelectedFormat(e.target.value)}
          className={styles.formatSelect}
        >
          {exportFormats.map(format => (
            <option key={format} value={format}>
              {format.toUpperCase()}
            </option>
          ))}
        </select>
      </div>
      
      <div className={styles.inclusionOptions}>
        <label className={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={includeFrames}
            onChange={(e) => setIncludeFrames(e.target.checked)}
            className={styles.checkbox}
          />
          Include Frame Analysis Data
        </label>
        
        <label className={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={includeBlockchain}
            onChange={(e) => setIncludeBlockchain(e.target.checked)}
            className={styles.checkbox}
          />
          Include Blockchain Verification
        </label>
      </div>
      
      <button 
        onClick={handleExport}
        className={styles.exportButton}
        type="button"
      >
        Export {selectedFormat.toUpperCase()} Report
      </button>
    </div>
  );

  const renderPreviewContent = () => {
    if (!exportPreview) {
      return (
        <div className={styles.noPreview}>
          <div className={styles.noPreviewIcon}>📄</div>
          <h3>No Export Data Available</h3>
          <p>Unable to generate export preview. Detection data may not be loaded.</p>
        </div>
      );
    }

    return (
      <div className={styles.previewContent}>
        <h3>Export Preview</h3>
        <pre className={styles.previewText}>
          {JSON.stringify(exportPreview, null, 2)}
        </pre>
      </div>
    );
  };

  return (
    <div className={styles.exportPreviewMode}>
      <div className={styles.previewHeader}>
        <h2>Export Preview</h2>
        <p>Configure and preview your detection results export</p>
      </div>
      
      <div className={styles.previewLayout}>
        <div className={styles.optionsColumn}>
          {renderExportOptions()}
        </div>
        
        <div className={styles.previewColumn}>
          {renderPreviewContent()}
        </div>
      </div>
    </div>
  );
};

export { ExportPreviewMode };
export default ExportPreviewMode;
