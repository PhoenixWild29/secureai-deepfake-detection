/**
 * FrameThumbnail Component
 * Individual frame thumbnail with confidence indicators and loading states
 */

import React, { useState, useEffect, useRef, useMemo, forwardRef } from 'react';
import { parseConfidenceScore, generateConfidenceStyles } from '../../utils/frameUtils';
import styles from './FrameThumbnail.module.css';

// ============================================================================
// Component
// ============================================================================

/**
 * FrameThumbnail - Individual frame thumbnail component with interactive features
 * @param {Object} props - Component properties
 * @param {Object} props.frameData - Frame data object
 * @param {boolean} props.isSelected - Whether frame is currently selected
 * @param {boolean} props.isLoading - Whether frame is currently loading
 * @param {Function} props.onClick - Callback when thumbnail is clicked
 * @param {Function} props.onLoad - Callback when image loads successfully  
 * @param {Function} props.onError - Callback when image fails to load
 * @param {Function} props.onRegionClick - Callback when suspicious region is clicked
 * @param {number} props.thumbnailSize - Size of thumbnail in pixels
 * @param {boolean} props.showConfidenceScore - Whether to display confidence score
 * @param {boolean} props.showFrameNumber - Whether to display frame number
 * @param {boolean} props.enableHoverEffects - Whether to enable hover interactions
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} Frame thumbnail component
 */
const FrameThumbnail = forwardRef(({
  frameData,
  isSelected = false,
  isLoading = false,
  onClick,
  onLoad,
  onError,
  onRegionClick,
  thumbnailSize = 160,
  showConfidenceScore = true,
  showFrameNumber = true,
  enableHoverEffects = true,
  className = ''
}, ref) => {
  // ============================================================================
  // State Management
  // ============================================================================

  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [showRegions, setShowRegions] = useState(false);

  // Refs
  const imageRef = useRef(null);
  const thumbnailRef = useRef(null);

  // Combined ref
  React.useImperativeHandle(ref, () => ({
    ...thumbnailRef.current,
    scrollIntoView: () => thumbnailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }),
    focus: () => thumbnailRef.current?.focus()
  }));

  // ============================================================================
  // Computed Values
  // ============================================================================

  const confidenceInfo = useMemo(() => {
    return parseConfidenceScore(frameData?.confidenceScore || 0);
  }, [frameData?.confidenceScore]);

  const confidenceStyles = useMemo(() => {
    return generateConfidenceStyles(frameData?.confidenceScore || 0);
  }, [frameData?.confidenceScore]);

  const thumbnailStyle = useMemo(() => ({
    ...confidenceStyles,
    width: `${thumbnailSize}px`,
    height: `${Math.round(thumbnailSize * 0.75)}px`
  }), [confidenceStyles, thumbnailSize]);

  // ============================================================================
  // Effects
  // ============================================================================

  // Handle loading state changes
  useEffect(() => {
    if (!isLoading && frameData?.imageUrl) {
      setImageError(false);
      setImageLoaded(false);
    }
  }, [isLoading, frameData?.imageUrl]);

  // Auto-focus selected frame for accessibility
  useEffect(() => {
    if (isSelected && thumbnailRef.current) {
      thumbnailRef.current.focus();
    }
  }, [isSelected]);

  // ============================================================================
  // Event Handlers
  // ============================================================================

  /**
   * Handle thumbnail click
   */
  const handleClick = useCallback((event) => {
    event.preventDefault();
    event.stopPropagation();
    onClick?.(frameData, event);
  }, [frameData, onClick]);

  /**
   * Handle image load
   */
  const handleImageLoad = useCallback(() => {
    setImageLoaded(true);
    setImageError(false);
    onLoad?.(frameData);
  }, [frameData, onLoad]);

  /**
   * Handle image error
   */
  const handleImageError = useCallback(() => {
    setImageError(true);
    setImageLoaded(false);
    onError?.(frameData);
  }, [frameData, onError]);

  /**
   * Handle suspicious region click
   */
  const handleRegionClick = useCallback((region, event) => {
    event.stopPropagation();
    onRegionClick?.(region, frameData, event);
  }, [frameData, onRegionClick]);

  /**
   * Handle keyboard interactions
   */
  const handleKeyDown = useCallback((event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleClick(event);
    }
  }, [handleClick]);

  /**
   * Handle mouse enter
   */
  const handleMouseEnter = useCallback(() => {
    setIsHovered(true);
    if (enableHoverEffects && frameData?.suspiciousRegions?.length > 0) {
      setShowRegions(true);
    }
  }, [enableHoverEffects, frameData?.suspiciousRegions]);

  /**
   * Handle mouse leave
   */
  const handleMouseLeave = useCallback(() => {
    setIsHovered(false);
    setShowRegions(false);
  }, []);

  // ============================================================================
  // Render Helpers
  // ============================================================================

  /**
   * Render confidence score indicator
   */
  const renderConfidenceScore = () => {
    if (!showConfidenceScore) return null;

    return (
      <div className={`${styles.confidenceScore} ${styles[confidenceInfo.riskLevel]}`}>
        <span className={styles.scorePercentage}>
          {confidenceInfo.percentage}%
        </span>
        <div 
          className={styles.confidenceBar}
          style={{ 
            width: `${confidenceInfo.percentage}%`,
            backgroundColor: confidenceInfo.color
          }}
        />
        <span className={styles.scoreLabel}>
          {confidenceInfo.riskLevel.toUpperCase()}
        </span>
      </div>
    );
  };

  /**
   * Render frame number indicator
   */
  const renderFrameNumber = () => {
    if (!showFrameNumber) return null;

    return (
      <div className={styles.frameNumber}>
        <span className={styles.frameNumberText}>
          #{frameData?.frameNumber || 0}
        </span>
      </div>
    );
  };

  /**
   * Render suspicious regions overlay
   */
  const renderSuspiciousRegions = () => {
    const regions = frameData?.suspiciousRegions || [];
    if (!regions.length || !showRegions) return null;

    return (
      <div className={styles.suspiciousRegions}>
        {regions.map((region, index) => (
          <div
            key={region.id || index}
            className={styles.suspiciousRegion}
            style={{
              left: `${region.x}px`,
              top: `${region.y}px`,
              width: `${region.width}px`,
              height: `${region.height}px`,
              borderColor: confidenceInfo.color
            }}
            onClick={(e) => handleRegionClick(region, e)}
            title={`Suspicious Region: ${Math.round((region.confidence || 0) * 100)}% confidence`}
          />
        ))}
      </div>
    );
  };

  /**
   * Render loading state
   */
  const renderLoadingState = () => {
    if (!isLoading) return null;

    return (
      <div className={styles.loadingOverlay}>
        <div className={styles.loadingSpinner} />
        <span className={styles.loadingText}>Loading...</span>
      </div>
    );
  };

  /**
   * Render error state
   */
  const renderErrorState = () => {
    if (!imageError) return null;

    return (
      <div className={styles.errorOverlay}>
        <div className={styles.errorIcon}>❌</div>
        <span className={styles.errorText}>Load Failed</span>
      </div>
    );
  };

  /**
   * Render frame image
   */
  const renderFrameImage = () => {
    if (!frameData?.imageUrl) {
      return (
        <div className={styles.placeholderImage}>
          <div className={styles.placeholderIcon}>🎬</div>
          <span className={styles.placeholderText}>No Frame</span>
        </div>
      );
    }

    return (
      <img
        ref={imageRef}
        src={frameData.imageUrl}
        alt={`Frame ${frameData.frameNumber || 0}`}
        className={`${styles.frameImage} ${imageLoaded ? styles.loaded : styles.loading}`}
        onLoad={handleImageLoad}
        onError={handleImageError}
        loading="lazy"
        draggable={false}
      />
    );
  };

  /**
   * Render selection indicator
   */
  const renderSelectionIndicator = () => {
    if (!isSelected) return null;

    return (
      <div className={styles.selectionIndicator}>
        <div className={styles.selectionBorder} />
      </div>
    );
  };

  /**
   * Render frame info tooltip
   */
  const renderFrameInfoTooltip = () => {
    if (!isHovered && !isSelected) return null;

    return (
      <div className={styles.frameTooltip}>
        <div className={styles.tooltipContent}>
          <div className={styles.tooltipRow}>
            <strong>Frame:</strong> {frameData?.frameNumber || 0}
          </div>
          <div className={styles.tooltipRow}>
            <strong>Confidence:</strong> {confidenceInfo.description}
          </div>
          {frameData?.suspiciousRegions?.length > 0 && (
            <div className={styles.tooltipRow}>
              <strong>Regions:</strong> {frameData.suspiciousRegions.length}
            </div>
          )}
          {frameData?.processingTimeMs && (
            <div className={styles.tooltipRow}>
              <strong>Processed:</strong> {frameData.processingTimeMs}ms
            </div>
          )}
        </div>
      </div>
    );
  };

  // ============================================================================
  // Main Render
  // ============================================================================

  return (
    <div
      ref={thumbnailRef}
      className={`
        ${styles.frameThumbnail} 
        ${isSelected ? styles.selected : ''}
        ${isHovered ? styles.hovered : ''}
        ${className}
      `}
      style={thumbnailStyle}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      tabIndex={isSelected ? 0 : -1}
      role="button"
      aria-label={`Frame ${frameData?.frameNumber || 0}, ${confidenceInfo.description}`}
      aria-selected={isSelected}
    >
      {/* Selection Indicator */}
      {renderSelectionIndicator()}

      {/* Frame Image */}
      <div className={styles.imageContainer}>
        {renderFrameImage()}
        
        {/* Loading State */}
        {renderLoadingState()}
        
        {/* Error State */}
        {renderErrorState()}
      </div>

      {/* Confidence Score */}
      {renderConfidenceScore()}

      {/* Frame Number */}
      {renderFrameNumber()}

      {/* Suspicious Regions Overlay */}
      {renderSuspiciousRegions()}

      {/* Frame Information Tooltip */}
      {renderFrameInfoTooltip()}

      {/* Interaction Overlay for extra controls */}
      <div className={styles.interactionOverlay}>
        <div className={styles.interactionButtons}>
          {frameData?.suspiciousRegions?.length > 0 && (
            <button
              className={styles.regionToggle}
              title="Toggle suspicious regions"
              aria-label="Toggle suspicious regions"
            >
              🔍
            </button>
          )}
          <button
            className={styles.expandButton}
            title="View details"
            aria-label="View frame details"
          >
            ⟳
          </button>
        </div>
      </div>
    </div>
  );
});

// ============================================================================
// Display Name
// ============================================================================

FrameThumbnail.displayName = 'FrameThumbnail';

// ============================================================================
// Export
// ============================================================================

export default FrameThumbnail;
