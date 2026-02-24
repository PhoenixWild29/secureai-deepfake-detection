/**
 * InteractiveHeatmap Component
 * Click-to-zoom interactive heatmap visualization with region highlighting
 */

import React, { useState, useCallback, useRef } from 'react';
import styles from './InteractiveHeatmap.module.css';

const InteractiveHeatmap = ({
  heatmapData,
  frameData,
  frameNumber,
  gridSize = 'medium',
  confidenceThreshold = 0.7,
  zoomLevel = 1,
  panPosition = { x: 0, y: 0 },
  onRegionClick,
  selectedRegions = [],
  viewerSettings = {},
  className = ''
}) => {
  
  const [hoverCell, setHoverCell] = useState(null);
  const canvasRef = useRef(null);

  const handleCellClick = useCallback((row, col) => {
    // Find region in heatmap data
    const region = heatmapData?.suspicious_regions?.find(r => 
      Math.floor(r.coordinates.x / (1920 / 10)) === col && 
      Math.floor(r.coordinates.y / (1080 / 10)) === row
    );
    
    if (region && onRegionClick) {
      onRegionClick(region);
    }
  }, [heatmapData, onRegionClick]);

  const renderHeatmapGrid = () => {
    if (!heatmapData?.spatial_confidence?.confidence_grid) {
      return <div className={styles.noData}>No heatmap data available</div>;
    }

    const grid = heatmapData.spatial_confidence.confidence_grid;
    const cellSize = 40 + (gridSize === 'high' ? 20 : 0);

    return (
      <div className={styles.heatmapGrid} style={{ transform: `scale(${zoomLevel})` }}>
        {grid.map((row, rowIndex) => 
          row.map((confidence, colIndex) => (
            <div
              key={`${rowIndex}-${colIndex}`}
              className={`${styles.heatmapCell} ${
                confidence >= confidenceThreshold ? styles.highConfidence : styles.lowConfidence
              } ${hoverCell?.row === rowIndex && hoverCell?.col === colIndex ? styles.hovered : ''}`}
              style={{
                width: cellSize,
                height: cellSize,
                backgroundColor: `rgba(239, 68, 68, ${confidence})`
              }}
              onClick={() => handleCellClick(rowIndex, colIndex)}
              onMouseEnter={() => setHoverCell({ row: rowIndex, col: colIndex })}
              onMouseLeave={() => setHoverCell(null)}
            >
              <div className={styles.confidenceTooltip}>
                {(confidence * 100).toFixed(1)}%
              </div>
            </div>
          ))
        )}
      </div>
    );
  };

  return (
    <div className={`${styles.interactiveHeatmap} ${className}`}>
      <div className={styles.heatmapHeader}>
        <h3>Interactive Heatmap - Frame {frameNumber}</h3>
        <div className={styles.heatmapControls}>
          <span>Zoom: {zoomLevel.toFixed(1)}x</span>
          <span>Threshold: {(confidenceThreshold * 100).toFixed(0)}%</span>
        </div>
      </div>
      
      <div className={styles.heatmapContainer}>
        {renderHeatmapGrid()}
      </div>
      
      {selectedRegions.length > 0 && (
        <div className={styles.selectedRegions}>
          <h4>Selected Regions ({selectedRegions.length})</h4>
          {selectedRegions.slice(0, 3).map((region, index) => (
            <div key={region.region_id || index} className={styles.selectedRegion}>
              {region.region_id}: {(region.confidence || 0).toFixed(1)}% confident
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export { InteractiveHeatmap };
export default InteractiveHeatmap;
