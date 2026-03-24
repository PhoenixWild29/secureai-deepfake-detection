/**
 * Validator Feedback SDK Integration
 * Captures user feedback, bug reports, and feature requests from production applications
 * 
 * Project: SecureAI Deepfake Video Detection Model
 * App Key: sf-int-fhJkPlxWrhKWX2848Pf3I3B6ZzGy0ovy
 * Endpoint: https://api.factory.8090.dev/v1/integration/validator/feedback
 */

class ValidatorFeedback {
  constructor() {
    this.appKey = 'sf-int-fhJkPlxWrhKWX2848Pf3I3B6ZzGy0ovy';
    this.endpoint = 'https://api.factory.8090.dev/v1/integration/validator/feedback';
    this.isInitialized = false;
    this.submissionCount = 0;
    this.maxSubmissionsPerSession = 10; // Prevent spam
  }

  /**
   * Initialize the Validator Feedback system
   */
  initialize() {
    if (this.isInitialized) {
      return;
    }

    // Set up automatic error tracking
    this.setupErrorTracking();
    
    // Set up performance monitoring
    this.setupPerformanceTracking();
    
    this.isInitialized = true;
    console.log('Validator Feedback SDK initialized');
  }

  /**
   * Submit feedback to the Validator API
   * @param {Object} feedback - Feedback data
   * @param {string} feedback.description - Required description
   * @param {string} feedback.type - Feedback type (bug, feature_request, performance, other)
   * @param {string} feedback.priority - Priority level (low, medium, high)
   * @param {string} feedback.email - Optional user email
   * @param {Object} feedback.context - Optional additional context
   * @returns {Promise<Object>} API response
   */
  async submit(feedback) {
    // Validate required fields
    if (!feedback.description || feedback.description.trim().length === 0) {
      throw new Error('Feedback description is required');
    }

    // Check submission limits
    if (this.submissionCount >= this.maxSubmissionsPerSession) {
      throw new Error('Maximum feedback submissions reached for this session');
    }

    // Prepare payload with automatic context
    const payload = {
      description: this.formatDescription(feedback.description),
      feedback_type: feedback.type || 'bug',
      priority: feedback.priority || 'medium',
      user_email: feedback.email || null,
      context: {
        ...this.getAutomaticContext(),
        ...feedback.context
      }
    };

    try {
      const response = await fetch(this.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-App-Key': this.appKey
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        if (response.status === 429) {
          throw new Error('Rate limit exceeded. Please try again later.');
        }
        throw new Error(`Failed to submit feedback: ${response.statusText}`);
      }

      const result = await response.json();
      this.submissionCount++;
      
      console.log('Feedback submitted successfully:', result);
      return result;
    } catch (error) {
      console.error('Validator Feedback Error:', error);
      throw error;
    }
  }

  /**
   * Format feedback description with context
   * @param {string} description - Original description
   * @returns {string} Formatted description
   */
  formatDescription(description) {
    const context = this.getAutomaticContext();
    const timestamp = new Date().toISOString();
    
    return `${description}

--- Context ---
Page: ${context.page}
Timestamp: ${timestamp}
User Agent: ${context.userAgent}
Screen Resolution: ${context.screenResolution}
Viewport: ${context.viewport}
URL Path: ${context.urlPath}`;
  }

  /**
   * Get automatic context information
   * @returns {Object} Context data
   */
  getAutomaticContext() {
    const now = new Date();
    const url = new URL(window.location.href);
    
    return {
      page: this.getPageName(),
      urlPath: url.pathname,
      timestamp: now.toISOString(),
      userAgent: navigator.userAgent,
      screenResolution: `${screen.width}x${screen.height}`,
      viewport: `${window.innerWidth}x${window.innerHeight}`,
      language: navigator.language,
      platform: navigator.platform,
      referrer: document.referrer || 'direct',
      sessionId: this.getSessionId(),
      userId: this.getUserId()
    };
  }

  /**
   * Get human-readable page name
   * @returns {string} Page name
   */
  getPageName() {
    const path = window.location.pathname;
    
    // Map routes to friendly names
    const routeMap = {
      '/': 'Home',
      '/dashboard': 'Dashboard',
      '/dashboard/upload': 'Video Upload',
      '/dashboard/results': 'Detection Results',
      '/dashboard/history': 'Analysis History',
      '/dashboard/reports': 'Reports',
      '/dashboard/analytics': 'Analytics',
      '/dashboard/settings': 'Settings',
      '/dashboard/profile': 'Profile',
      '/dashboard/notifications': 'Notifications',
      '/dashboard/system': 'System Status',
      '/dashboard/help': 'Help & Support',
      '/dashboard/docs': 'Documentation',
      '/dashboard/api': 'API Documentation'
    };

    // Check for exact matches first
    if (routeMap[path]) {
      return routeMap[path];
    }

    // Check for dynamic routes
    for (const [route, name] of Object.entries(routeMap)) {
      if (path.startsWith(route) && route !== '/') {
        return `${name} (${path})`;
      }
    }

    return `Unknown Page (${path})`;
  }

  /**
   * Get or create session ID
   * @returns {string} Session ID
   */
  getSessionId() {
    let sessionId = sessionStorage.getItem('validator_session_id');
    if (!sessionId) {
      sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      sessionStorage.setItem('validator_session_id', sessionId);
    }
    return sessionId;
  }

  /**
   * Get user ID if available
   * @returns {string|null} User ID
   */
  getUserId() {
    // Try to get user ID from various sources
    if (window.user && window.user.id) {
      return window.user.id;
    }
    
    if (window.auth && window.auth.user && window.auth.user.id) {
      return window.auth.user.id;
    }
    
    // Check localStorage for user data
    const userData = localStorage.getItem('user_data');
    if (userData) {
      try {
        const user = JSON.parse(userData);
        return user.id || user.userId || null;
      } catch (e) {
        // Ignore parsing errors
      }
    }
    
    return null;
  }

  /**
   * Set up automatic error tracking
   */
  setupErrorTracking() {
    // JavaScript errors
    window.addEventListener('error', (event) => {
      this.submit({
        description: `JavaScript Error: ${event.message}`,
        type: 'bug',
        priority: 'high',
        context: {
          errorType: 'javascript',
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
          stack: event.error ? event.error.stack : null
        }
      }).catch(console.error);
    });

    // Unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.submit({
        description: `Unhandled Promise Rejection: ${event.reason}`,
        type: 'bug',
        priority: 'high',
        context: {
          errorType: 'promise_rejection',
          reason: event.reason,
          stack: event.reason && event.reason.stack ? event.reason.stack : null
        }
      }).catch(console.error);
    });

    // Network errors (if fetch fails)
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
      try {
        return await originalFetch(...args);
      } catch (error) {
        // Only track network errors for our API endpoints
        if (args[0] && args[0].includes('api.factory.8090.dev')) {
          this.submit({
            description: `Network Error: ${error.message}`,
            type: 'bug',
            priority: 'medium',
            context: {
              errorType: 'network',
              url: args[0],
              method: args[1]?.method || 'GET'
            }
          }).catch(console.error);
        }
        throw error;
      }
    };
  }

  /**
   * Set up performance tracking
   */
  setupPerformanceTracking() {
    // Track page load performance
    window.addEventListener('load', () => {
      setTimeout(() => {
        const perfData = performance.getEntriesByType('navigation')[0];
        if (perfData && perfData.loadEventEnd - perfData.loadEventStart > 5000) {
          this.submit({
            description: `Slow page load detected: ${Math.round(perfData.loadEventEnd - perfData.loadEventStart)}ms`,
            type: 'performance',
            priority: 'medium',
            context: {
              performanceType: 'page_load',
              loadTime: perfData.loadEventEnd - perfData.loadEventStart,
              domContentLoaded: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart,
              firstPaint: this.getFirstPaintTime()
            }
          }).catch(console.error);
        }
      }, 1000);
    });
  }

  /**
   * Get first paint time
   * @returns {number|null} First paint time in milliseconds
   */
  getFirstPaintTime() {
    const paintEntries = performance.getEntriesByType('paint');
    const firstPaint = paintEntries.find(entry => entry.name === 'first-paint');
    return firstPaint ? firstPaint.startTime : null;
  }

  /**
   * Submit bug report with automatic context
   * @param {string} description - Bug description
   * @param {Object} additionalContext - Additional context
   */
  async submitBugReport(description, additionalContext = {}) {
    return this.submit({
      description,
      type: 'bug',
      priority: 'high',
      context: additionalContext
    });
  }

  /**
   * Submit feature request
   * @param {string} description - Feature description
   * @param {string} email - User email for follow-up
   */
  async submitFeatureRequest(description, email = null) {
    return this.submit({
      description,
      type: 'feature_request',
      priority: 'medium',
      email
    });
  }

  /**
   * Submit performance issue
   * @param {string} description - Performance issue description
   * @param {Object} metrics - Performance metrics
   */
  async submitPerformanceIssue(description, metrics = {}) {
    return this.submit({
      description,
      type: 'performance',
      priority: 'medium',
      context: {
        performanceMetrics: metrics
      }
    });
  }

  /**
   * Get submission statistics
   * @returns {Object} Statistics
   */
  getStats() {
    return {
      submissionsThisSession: this.submissionCount,
      maxSubmissionsPerSession: this.maxSubmissionsPerSession,
      isInitialized: this.isInitialized
    };
  }

  /**
   * Reset submission counter (for testing)
   */
  resetSubmissionCounter() {
    this.submissionCount = 0;
  }
}

// Create singleton instance
const validatorFeedback = new ValidatorFeedback();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    validatorFeedback.initialize();
  });
} else {
  validatorFeedback.initialize();
}

// Export for use in modules
export default validatorFeedback;

// Also make available globally for easy access
window.ValidatorFeedback = validatorFeedback;
