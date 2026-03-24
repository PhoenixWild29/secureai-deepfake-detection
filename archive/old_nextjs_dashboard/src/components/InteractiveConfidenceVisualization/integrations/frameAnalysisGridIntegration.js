/**
 * FrameAnalysisGrid Integration
 * Utility for coordinating navigation between confidence charts and frame analysis grid
 */

// ============================================================================
// Integration Configuration
// ============================================================================

const INTEGRATION_CONFIG = {
  // Navigation settings
  scrollIntoView: true,
  highlightDuration: 2000,
  smoothScrolling: true,
  
  // Visual feedback settings
  highlightColor: '#3b82f6',
  highlightOpacity: 0.3,
  borderColor: '#1d4ed8',
  borderWidth: 2,
  
  // Animation settings
  animationDuration: 300,
  easingFunction: 'ease-in-out'
};

// ============================================================================
// FrameAnalysisGrid Integration Class
// ============================================================================

class FrameAnalysisGridIntegration {
  constructor() {
    this.gridInstance = null;
    this.eventListeners = new Map();
    this.highlightTimeouts = new Map();
  }

  /**
   * Initialize integration with FrameAnalysisGrid
   * @param {Object} gridInstance - FrameAnalysisGrid component instance
   */
  initialize(gridInstance) {
    this.gridInstance = gridInstance;
    this.setupEventListeners();
    console.log('FrameAnalysisGrid integration initialized');
  }

  /**
   * Navigate to specific frame in the grid
   * @param {number} frameNumber - Target frame number
   * @param {Object} options - Navigation options
   */
  navigateToFrame(frameNumber, options = {}) {
    if (!this.gridInstance) {
      console.warn('FrameAnalysisGrid not initialized');
      return false;
    }

    const {
      highlight = true,
      scrollIntoView = INTEGRATION_CONFIG.scrollIntoView,
      smoothScrolling = INTEGRATION_CONFIG.smoothScrolling,
      callback
    } = options;

    try {
      // Find frame element in grid
      const frameElement = this.findFrameElement(frameNumber);
      if (!frameElement) {
        console.warn(`Frame ${frameNumber} not found in grid`);
        return false;
      }

      // Scroll to frame if requested
      if (scrollIntoView) {
        this.scrollToFrame(frameElement, smoothScrolling);
      }

      // Highlight frame if requested
      if (highlight) {
        this.highlightFrame(frameElement, frameNumber);
      }

      // Trigger frame selection in grid
      this.selectFrameInGrid(frameNumber);

      // Execute callback if provided
      if (callback && typeof callback === 'function') {
        callback(frameNumber, frameElement);
      }

      console.log(`Navigated to frame ${frameNumber}`);
      return true;
    } catch (error) {
      console.error('Error navigating to frame:', error);
      return false;
    }
  }

  /**
   * Find frame element in the grid
   * @param {number} frameNumber - Frame number to find
   * @returns {HTMLElement|null} Frame element or null if not found
   */
  findFrameElement(frameNumber) {
    if (!this.gridInstance) return null;

    // Try multiple selectors for frame elements
    const selectors = [
      `[data-frame-number="${frameNumber}"]`,
      `[data-frame="${frameNumber}"]`,
      `.frame-item[data-index="${frameNumber}"]`,
      `.frame-thumbnail[data-frame-number="${frameNumber}"]`
    ];

    for (const selector of selectors) {
      const element = document.querySelector(selector);
      if (element) return element;
    }

    // Fallback: search within grid container
    const gridContainer = this.getGridContainer();
    if (gridContainer) {
      for (const selector of selectors) {
        const element = gridContainer.querySelector(selector);
        if (element) return element;
      }
    }

    return null;
  }

  /**
   * Get grid container element
   * @returns {HTMLElement|null} Grid container element
   */
  getGridContainer() {
    if (!this.gridInstance) return null;

    // Try to get container from grid instance
    if (this.gridInstance.containerRef?.current) {
      return this.gridInstance.containerRef.current;
    }

    // Fallback: search for common grid container selectors
    const containerSelectors = [
      '.frame-analysis-grid',
      '.frame-grid-container',
      '.detection-results-grid',
      '[data-testid="frame-grid"]'
    ];

    for (const selector of containerSelectors) {
      const container = document.querySelector(selector);
      if (container) return container;
    }

    return null;
  }

  /**
   * Scroll to frame element
   * @param {HTMLElement} frameElement - Frame element to scroll to
   * @param {boolean} smooth - Whether to use smooth scrolling
   */
  scrollToFrame(frameElement, smooth = true) {
    if (!frameElement) return;

    const scrollOptions = {
      behavior: smooth ? 'smooth' : 'auto',
      block: 'center',
      inline: 'center'
    };

    frameElement.scrollIntoView(scrollOptions);
  }

  /**
   * Highlight frame element
   * @param {HTMLElement} frameElement - Frame element to highlight
   * @param {number} frameNumber - Frame number for timeout management
   */
  highlightFrame(frameElement, frameNumber) {
    if (!frameElement) return;

    // Clear existing highlight timeout for this frame
    if (this.highlightTimeouts.has(frameNumber)) {
      clearTimeout(this.highlightTimeouts.get(frameNumber));
    }

    // Add highlight class
    frameElement.classList.add('confidence-chart-highlighted');
    
    // Add inline styles for immediate visual feedback
    const originalStyle = frameElement.style.cssText;
    frameElement.style.cssText = `
      ${originalStyle}
      box-shadow: 0 0 0 ${INTEGRATION_CONFIG.borderWidth}px ${INTEGRATION_CONFIG.borderColor};
      background-color: ${INTEGRATION_CONFIG.highlightColor}${Math.round(INTEGRATION_CONFIG.highlightOpacity * 255).toString(16).padStart(2, '0')};
      transition: all ${INTEGRATION_CONFIG.animationDuration}ms ${INTEGRATION_CONFIG.easingFunction};
    `;

    // Remove highlight after duration
    const timeout = setTimeout(() => {
      frameElement.classList.remove('confidence-chart-highlighted');
      frameElement.style.cssText = originalStyle;
      this.highlightTimeouts.delete(frameNumber);
    }, INTEGRATION_CONFIG.highlightDuration);

    this.highlightTimeouts.set(frameNumber, timeout);
  }

  /**
   * Select frame in grid component
   * @param {number} frameNumber - Frame number to select
   */
  selectFrameInGrid(frameNumber) {
    if (!this.gridInstance) return;

    // Try to call grid's frame selection method
    if (typeof this.gridInstance.selectFrame === 'function') {
      this.gridInstance.selectFrame(frameNumber);
    } else if (typeof this.gridInstance.setSelectedFrame === 'function') {
      this.gridInstance.setSelectedFrame(frameNumber);
    } else if (typeof this.gridInstance.onFrameSelect === 'function') {
      this.gridInstance.onFrameSelect(frameNumber);
    } else {
      // Fallback: dispatch custom event
      const event = new CustomEvent('frameSelectFromChart', {
        detail: { frameNumber },
        bubbles: true
      });
      document.dispatchEvent(event);
    }
  }

  /**
   * Setup event listeners for grid integration
   */
  setupEventListeners() {
    // Listen for frame selection events from grid
    const handleGridFrameSelect = (event) => {
      const { frameNumber, timestamp, confidence } = event.detail || {};
      
      // Emit event for confidence chart to respond
      const chartEvent = new CustomEvent('frameSelectedInGrid', {
        detail: { frameNumber, timestamp, confidence },
        bubbles: true
      });
      document.dispatchEvent(chartEvent);
    };

    document.addEventListener('frameSelectedInGrid', handleGridFrameSelect);
    this.eventListeners.set('frameSelectedInGrid', handleGridFrameSelect);

    // Listen for grid navigation events
    const handleGridNavigation = (event) => {
      const { direction, currentFrame } = event.detail || {};
      
      // Emit event for confidence chart to update view
      const chartEvent = new CustomEvent('gridNavigation', {
        detail: { direction, currentFrame },
        bubbles: true
      });
      document.dispatchEvent(chartEvent);
    };

    document.addEventListener('gridNavigation', handleGridNavigation);
    this.eventListeners.set('gridNavigation', handleGridNavigation);
  }

  /**
   * Get current frame selection from grid
   * @returns {Object|null} Current frame selection info
   */
  getCurrentFrameSelection() {
    if (!this.gridInstance) return null;

    // Try to get current selection from grid instance
    if (typeof this.gridInstance.getSelectedFrame === 'function') {
      return this.gridInstance.getSelectedFrame();
    } else if (this.gridInstance.selectedFrame !== undefined) {
      return {
        frameNumber: this.gridInstance.selectedFrame,
        timestamp: this.gridInstance.selectedFrame / 30, // Assuming 30 FPS
        confidence: this.gridInstance.selectedFrameConfidence
      };
    }

    return null;
  }

  /**
   * Sync chart view with grid selection
   * @param {Function} chartUpdateCallback - Callback to update chart view
   */
  syncWithGridSelection(chartUpdateCallback) {
    const currentSelection = this.getCurrentFrameSelection();
    if (currentSelection && chartUpdateCallback) {
      chartUpdateCallback(currentSelection);
    }
  }

  /**
   * Enable/disable grid integration
   * @param {boolean} enabled - Whether integration is enabled
   */
  setEnabled(enabled) {
    if (enabled) {
      this.setupEventListeners();
    } else {
      this.removeEventListeners();
    }
  }

  /**
   * Remove event listeners
   */
  removeEventListeners() {
    this.eventListeners.forEach((handler, eventType) => {
      document.removeEventListener(eventType, handler);
    });
    this.eventListeners.clear();
  }

  /**
   * Clear all highlight timeouts
   */
  clearHighlights() {
    this.highlightTimeouts.forEach(timeout => clearTimeout(timeout));
    this.highlightTimeouts.clear();

    // Remove highlight classes from all elements
    const highlightedElements = document.querySelectorAll('.confidence-chart-highlighted');
    highlightedElements.forEach(element => {
      element.classList.remove('confidence-chart-highlighted');
    });
  }

  /**
   * Get integration status
   * @returns {Object} Integration status information
   */
  getStatus() {
    return {
      initialized: !!this.gridInstance,
      activeListeners: this.eventListeners.size,
      activeHighlights: this.highlightTimeouts.size,
      config: INTEGRATION_CONFIG
    };
  }

  /**
   * Destroy integration and cleanup
   */
  destroy() {
    this.removeEventListeners();
    this.clearHighlights();
    this.gridInstance = null;
    console.log('FrameAnalysisGrid integration destroyed');
  }
}

// ============================================================================
// Export Singleton Instance
// ============================================================================

const frameAnalysisGridIntegration = new FrameAnalysisGridIntegration();

export { FrameAnalysisGridIntegration, frameAnalysisGridIntegration };
export default frameAnalysisGridIntegration;
