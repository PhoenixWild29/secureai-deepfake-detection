/**
 * FrameThumbnailGrid Component
 * Displays a grid of frame thumbnails with virtualized rendering and lazy loading
 */

import React, { useState, useEffect, useCallback, useRef, forwardRef } from 'react';
import { parseConfidenceScore } from '../../api/detectionResultsApi';
import styles from './FrameThumbnailGrid.module.css';

// ============================================================================
// Constants
// ============================================================================

const THUMBNAIL_SIZE = 120; // Height of each thumbnail in pixels
const GRID_PADDING = 8; // Padding between thumbnails
const VIRTUALIZATION_BUFFER = 5; // Extra items to render outside viewport

// ============================================================================
// Component
// ============================================================================

/**
 * FrameThumbnailGrid - Displays grid of frame thumbnails with virtualization
 * @param {Object} props - Component properties
 * @param {Array} props.thumbnails - Array of thumbnail data
 * @param {number} props.selectedFrameIndex - Currently selected frame index
 * @param {Function} props.onFrameSelect - Frame selection callback
 * @param {boolean} props.loading - Loading state
 * @param {Object} props.filters - Filter configuration
 * @param {Function} props.onFilterChange - Filter change callback
 * @param {number} props.maxThumbnails - Maximum thumbnails to display
 * @param {boolean} props.enableVirtualization - Enable virtual scrolling
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Frame thumbnail grid component
 */
const FrameThumbnailGrid = forwardRef(({
  thumbnails = [],
  selectedFrameIndex,
  onFrameSelect,
  loading = false,
  filters = {},
  onFilterChange,
  maxThumbnails = 100,
  enableVirtualization = true,
  className = ''
}, ref) => {
  // ============================================================================
  // State Management
  // ============================================================================

  const [viewportHeight, setViewportHeight] = useState(400);
  const [scrollTop, setScrollTop] = useState(0);
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: Math.min(10, thumbnails.length) });

  // Refs
  const containerRef = useRef(null);
  const gridRef = useRef(null);
  const lastScrollTimeRef = useRef(0);

  // ============================================================================
  // Viewport Management
  // ============================================================================

  useEffect(() => {
    const updateViewportHeight = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setViewportHeight(rect.height);
      }
    };

    updateViewportHeight();
    window.addEventListener('resize', updateViewportHeight);
    
    return () => window.removeEventListener('resize', updateViewportHeight);
  }, []);

  // ============================================================================
  // Virtualization Logic
  // ============================================================================

  // Calculate visible range for virtualization
  useEffect(() => {
    if (!enableVirtualization || thumbnails.length === 0) {
      setVisibleRange({ start: 0, end: thumbnails.length });
      return;
    }

    const thumbnailsPerRow = Math.floor((viewportHeight) / (THUMBNAIL_SIZE + GRID_PADDING));
    const startRow = Math.floor(scrollTop / (THUMBNAIL_SIZE + GRID_PADDING));
    const endRow = Math.ceil((scrollTop + viewportHeight) / (THUMBNAIL_SIZE + GRID_PADDING));
    
    const start = Math.max(0, startRow - VIRTUALIZATION_BUFFER);
    const end = Math.min(thumbnails.length, endRow + VIRTUALIZATION_BUFFER);

    setVisibleRange({ start, end });
  }, [scrollTop, viewportHeight, thumbnails.length, enableVirtualization]);

  // ============================================================================
  // Event Handlers
  // ============================================================================

  /**
   * Handle scroll events with throttling
   */
  const handleScroll = useCallback((event) => {
    const now = Date.now();
    if (now - lastScrollTimeRef.current < 16) { // 60fps throttling
      return;
    }
    
    lastScrollTimeRef.current = now;
    setScrollTop(event.target.scrollTop);
  }, []);

  /**
   * Handle frame thumbnail click
   */
  const handleFrameClick = useCallback((frameNumber) => {
    onFrameSelect?.(frameNumber);
  }, [onFrameSelect]);

  /**
   * Handle filter changes
   */
  const handleFilterChange = useCallback((filterKey, value) => {
    onFilterChange?.({ [filterKey]: value });
  }, [onFilterChange]);

  // ============================================================================
  // Render Helpers
  // ============================================================================

  /**
   * Render filter controls
   */
  const renderFilters = () => (
    <div className={styles.filterControls}>
      <div className={styles.filterGroup}>
        <label>Risk Level:</label>
        <select 
          value={filters.riskLevelFilter || 'all'}
          onChange={(e) => handleFilterChange('riskLevelFilter', e.target.value)}
          className={styles.filterSelect}
        >
          <option value="all">All Risk Levels</option>
          <option value="low">Low Risk (&le;30%)</option>
          <option value="medium">Medium Risk (30-70%)</option>
          <option value="high">High Risk (&gt;70%)</option>
        </select>
      </div>

      <div className={styles.filterGroup}>
        <label>
          <input 
            type="checkbox"
            checked={filters.showHighConfidenceOnly || false}
            onChange={(e) => handleFilterChange('showHighConfidenceOnly', e.target.checked)}
            className={styles.filterCheckbox}
          />
          High Confidence Only (&gt;50%)
        </label>
      </div>

      <div className={styles.frameCountInfo}>
        Showing {thumbnails.length} frames
        {thumbnails.length === maxThumbnails && ` (max ${maxThumbnails})`}
      </div>
    </div>
  );

  /**
   * Render individual thumbnail
   */
  const renderThumbnail = useCallback((thumbnail, index) => {
    if (!thumbnail) return null;

    const confidenceInfo = parseConfidenceScore(thumbnail.confidence || 0);
    const isSelected = thumbnail.frameNumber === selectedFrameIndex;
    
    return (
      <div
        key={thumbnail.frameNumber}
        className={`${styles.thumbnailWrapper} ${isSelected ? styles.selected : ''}`}
        style={{
          ['--confidence-color']: confidenceInfo.color
        }}
        onClick={() => handleFrameClick(thumbnail.frameNumber)}
      >
        <div className={styles.thumbnailContainer}>
          {thumbnail.thumbnailUrl ? (
            <img 
              src={thumbnail.thumbnailUrl}
              alt={`Frame ${thumbnail.frameNumber}`}
              className={styles.thumbnailImage}
              loading="lazy"
              onError={(e) => {
                console.warn(`Failed to load thumbnail for frame ${thumbnail.frameNumber}`);
                e.target.style.display = 'none';
              }}
            />
          ) : (
            <div className={styles.thumbnailPlaceholder}>
              <span>Frame {thumbnail.frameNumber}</span>
            </div>
          )}
          
          {/* Confidence overlay */}
          <div className={styles.confidenceOverlay}>
            <div 
              className={styles.confidenceBar}
              style={{ 
                width: `${confidenceInfo.percentage}%`,
                backgroundColor: confidenceInfo.color
              }}
            />
          </div>
          
          {/* Frame number */}
          <div className={styles.frameNumber}>
            {thumbnail.frameNumber}
          </div>
          
          {/* Risk indicator */}
          <div 
            className={`${styles.riskIndicator} ${styles[confidenceInfo.riskLevel]}`}
            title={confidenceInfo.category}
          />
        </div>
      </div>
    );
  }, [selectedFrameIndex, handleFrameClick]);

  /**
   * Render loading placeholders
   */
  const renderLoadingPlaceholders = (count = 6) => (
    <div className={styles.loadingContainer}>
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className={styles.loadingPlaceholder}>
          <div className={styles.loadingSkeleton} />
        </div>
      ))}
    </div>
  );

  /**
   * Render empty state
   */
  const renderEmptyState = () => (
    <div className={styles.emptyState}>
      <div className={styles.emptyIcon}>🖼️</div>
      <h3>No frames available</h3>
      <p>
        {filters.riskLevelFilter !== 'all' || filters.showHighConfidenceOnly
          ? 'No frames match the current filter settings'
          : 'No frame thumbnails have been generated yet'
        }
      </p>
      
      {(filters.riskLevelFilter !== 'all' || filters.showHighConfidenceOnly) && (
        <button
          className={styles.clearFiltersButton}
          onClick={() => onFilterChange?.({ 
            riskLevelFilter: 'all', 
            showHighConfidenceOnly: false 
          })}
        >
          Clear Filters
        </button>
      )}
    </div>
  );

  // ============================================================================
  // Virtualization Calculations
  // ============================================================================

  const totalHeight = enableVirtualization ? 
    Math.ceil(thumbnails.length / Math.floor((viewportHeight) / (THUMBNAIL_SIZE + GRID_PADDING))) * 
    (THUMBNAIL_SIZE + GRID_PADDING) : 
    'auto';

  const visibleThumbnails = enableVirtualization ? 
    thumbnails.slice(visibleRange.start, visibleRange.end) :
    thumbnails;

  // ============================================================================
  // Main Render
  // ============================================================================

  return (
    <div 
      ref={containerRef} 
      className={`${styles.frameThumbnailGrid} ${className}`}
    >
      {/* Header */}
      <div className={styles.header}>
        <h3>Frame Analysis Grid</h3>
        
        {/* Filter controls */}
        {thumbnails.length > 0 && (
          <div className={styles.headerRight}>
            {renderFilters()}
          </div>
        )}
      </div>

      {/* Grid Container */}
      <div 
        ref={gridRef}
        className={styles.gridContainer}
        onScroll={handleScroll}
        style={{
          height: viewportHeight
        }}
      >
        {loading ? (
          renderLoadingPlaceholders()
        ) : thumbnails.length === 0 ? (
          renderEmptyState()
        ) : enableVirtualization ? (
          <div 
            className={styles.virtualGrid}
            style={{ height: totalHeight }}
          >
            {/* Spacer for items before visible range */}
            {visibleRange.start > 0 && (
              <div 
                className={styles.gridSpacer}
                style={{ height: visibleRange.start * (THUMBNAIL_SIZE + GRID_PADDING) }}
              />
            )}
            
            {/* Visible thumbnails */}
            <div className={styles.thumbnailsRow}>
              {visibleThumbnails.map((thumbnail, index) => 
                renderThumbnail(thumbnail, visibleRange.start + index)
              )}
            </div>
            
            {/* Spacer for items after visible range */}
            {visibleRange.end < thumbnails.length && (
              <div 
                className={styles.gridSpacer}
                style={{ height: (thumbnails.length - visibleRange.end) * (THUMBNAIL_SIZE + GRID_PADDING) }}
              />
            )}
          </div>
        ) : (
          <div className={styles.thumbnailsRow}>
            {thumbnails.map(renderThumbnail)}
          </div>
        )}
      </div>

      {/* Footer Info */}
      {thumbnails.length > 0 && (
        <div className={styles.footer}>
          <div className={styles.footerInfo}>
            <span>Showing {thumbnails.length} frames</span>
            {enableVirtualization && (
              <span>Virtualized rendering active</span>
            )}
          </div>
          
          <div className={styles.footerStats}>
            <span>
              Selected: Frame {selectedFrameIndex}
            </span>
          </div>
        </div>
      )}
    </div>
  );
});

// ============================================================================
// Display Name
// ============================================================================

FrameThumbnailGrid.displayName = 'FrameThumbnailGrid';

// ============================================================================
// Export
// ============================================================================

export default FrameThumbnailGrid;
