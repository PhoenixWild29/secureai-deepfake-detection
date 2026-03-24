/**
 * Validator Feedback UI Components
 * React components for collecting user feedback, bug reports, and feature requests
 */

import React, { useState, useEffect } from 'react';
import validatorFeedback from '../services/ValidatorFeedback.js';
import './FeedbackComponents.css';

/**
 * Main Feedback Form Component
 */
export const FeedbackForm = ({ 
  isOpen, 
  onClose, 
  initialType = 'bug',
  initialDescription = '',
  className = '' 
}) => {
  const [formData, setFormData] = useState({
    description: initialDescription,
    type: initialType,
    priority: 'medium',
    email: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState(null);
  const [errors, setErrors] = useState({});

  // Reset form when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setFormData({
        description: initialDescription,
        type: initialType,
        priority: 'medium',
        email: ''
      });
      setSubmitStatus(null);
      setErrors({});
    }
  }, [isOpen, initialType, initialDescription]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: null
      }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.description.trim()) {
      newErrors.description = 'Description is required';
    } else if (formData.description.trim().length < 10) {
      newErrors.description = 'Description must be at least 10 characters';
    }
    
    if (formData.email && !isValidEmail(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const isValidEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    setSubmitStatus(null);

    try {
      const result = await validatorFeedback.submit({
        description: formData.description,
        type: formData.type,
        priority: formData.priority,
        email: formData.email || null
      });

      setSubmitStatus({
        type: 'success',
        message: 'Thank you for your feedback! We\'ll review it and get back to you if needed.',
        feedbackId: result.feedback_id
      });

      // Reset form after successful submission
      setTimeout(() => {
        setFormData({
          description: '',
          type: 'bug',
          priority: 'medium',
          email: ''
        });
      }, 1000);

    } catch (error) {
      setSubmitStatus({
        type: 'error',
        message: error.message || 'Failed to submit feedback. Please try again.'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className={`feedback-modal-overlay ${className}`} onClick={handleClose}>
      <div className="feedback-modal" onClick={(e) => e.stopPropagation()}>
        <div className="feedback-modal-header">
          <h3>Submit Feedback</h3>
          <button 
            className="feedback-close-btn" 
            onClick={handleClose}
            disabled={isSubmitting}
            aria-label="Close feedback form"
          >
            <i className="fas fa-times"></i>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="feedback-form">
          <div className="feedback-form-group">
            <label htmlFor="feedback-type">Type of Feedback</label>
            <select
              id="feedback-type"
              name="type"
              value={formData.type}
              onChange={handleInputChange}
              className="feedback-select"
              disabled={isSubmitting}
            >
              <option value="bug">🐛 Bug Report</option>
              <option value="feature_request">💡 Feature Request</option>
              <option value="performance">⚡ Performance Issue</option>
              <option value="other">📝 Other</option>
            </select>
          </div>

          <div className="feedback-form-group">
            <label htmlFor="feedback-priority">Priority</label>
            <select
              id="feedback-priority"
              name="priority"
              value={formData.priority}
              onChange={handleInputChange}
              className="feedback-select"
              disabled={isSubmitting}
            >
              <option value="low">🟢 Low Priority</option>
              <option value="medium">🟡 Medium Priority</option>
              <option value="high">🔴 High Priority</option>
            </select>
          </div>

          <div className="feedback-form-group">
            <label htmlFor="feedback-description">
              Description <span className="required">*</span>
            </label>
            <textarea
              id="feedback-description"
              name="description"
              value={formData.description}
              onChange={handleInputChange}
              placeholder="Please describe the issue, feature request, or feedback in detail..."
              className={`feedback-textarea ${errors.description ? 'error' : ''}`}
              rows={6}
              disabled={isSubmitting}
              required
            />
            {errors.description && (
              <div className="feedback-error">{errors.description}</div>
            )}
            <div className="feedback-char-count">
              {formData.description.length} characters
            </div>
          </div>

          <div className="feedback-form-group">
            <label htmlFor="feedback-email">Email (Optional)</label>
            <input
              type="email"
              id="feedback-email"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
              placeholder="your.email@example.com"
              className={`feedback-input ${errors.email ? 'error' : ''}`}
              disabled={isSubmitting}
            />
            {errors.email && (
              <div className="feedback-error">{errors.email}</div>
            )}
            <div className="feedback-help-text">
              Provide your email if you'd like us to follow up with you
            </div>
          </div>

          {submitStatus && (
            <div className={`feedback-status ${submitStatus.type}`}>
              <div className="feedback-status-icon">
                {submitStatus.type === 'success' ? '✅' : '❌'}
              </div>
              <div className="feedback-status-message">
                {submitStatus.message}
                {submitStatus.feedbackId && (
                  <div className="feedback-id">
                    Reference ID: {submitStatus.feedbackId}
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="feedback-form-actions">
            <button
              type="button"
              onClick={handleClose}
              className="feedback-btn feedback-btn-secondary"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="feedback-btn feedback-btn-primary"
              disabled={isSubmitting || !formData.description.trim()}
            >
              {isSubmitting ? (
                <>
                  <i className="fas fa-spinner fa-spin"></i>
                  Submitting...
                </>
              ) : (
                <>
                  <i className="fas fa-paper-plane"></i>
                  Submit Feedback
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

/**
 * Quick Feedback Button Component
 */
export const QuickFeedbackButton = ({ 
  type = 'bug',
  description = '',
  className = '',
  children = 'Report Issue'
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <>
      <button
        className={`quick-feedback-btn ${className}`}
        onClick={() => setIsModalOpen(true)}
        title="Report an issue or suggest an improvement"
      >
        {children}
      </button>
      
      <FeedbackForm
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        initialType={type}
        initialDescription={description}
      />
    </>
  );
};

/**
 * Feedback Widget Component (Floating)
 */
export const FeedbackWidget = ({ className = '' }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);

  const toggleWidget = () => {
    if (isOpen) {
      setIsMinimized(!isMinimized);
    } else {
      setIsOpen(true);
      setIsMinimized(false);
    }
  };

  const closeWidget = () => {
    setIsOpen(false);
    setIsMinimized(false);
  };

  return (
    <div className={`feedback-widget ${className}`}>
      {isOpen && (
        <div className={`feedback-widget-panel ${isMinimized ? 'minimized' : ''}`}>
          <div className="feedback-widget-header">
            <h4>Feedback</h4>
            <div className="feedback-widget-controls">
              <button
                className="feedback-widget-minimize"
                onClick={() => setIsMinimized(!isMinimized)}
                title={isMinimized ? 'Expand' : 'Minimize'}
              >
                <i className={`fas fa-${isMinimized ? 'expand' : 'minus'}`}></i>
              </button>
              <button
                className="feedback-widget-close"
                onClick={closeWidget}
                title="Close"
              >
                <i className="fas fa-times"></i>
              </button>
            </div>
          </div>
          
          {!isMinimized && (
            <div className="feedback-widget-content">
              <FeedbackForm
                isOpen={true}
                onClose={closeWidget}
                className="feedback-widget-form"
              />
            </div>
          )}
        </div>
      )}
      
      <button
        className="feedback-widget-toggle"
        onClick={toggleWidget}
        title="Open feedback widget"
      >
        <i className="fas fa-comment-dots"></i>
      </button>
    </div>
  );
};

/**
 * Error Reporting Component
 */
export const ErrorReporter = ({ error, onReport, className = '' }) => {
  const [isReporting, setIsReporting] = useState(false);
  const [hasReported, setHasReported] = useState(false);

  const handleReport = async () => {
    setIsReporting(true);
    
    try {
      await validatorFeedback.submitBugReport(
        `Application Error: ${error.message}`,
        {
          errorType: 'application',
          errorMessage: error.message,
          errorStack: error.stack,
          errorName: error.name,
          userAction: 'manual_report'
        }
      );
      
      setHasReported(true);
      if (onReport) {
        onReport();
      }
    } catch (reportError) {
      console.error('Failed to report error:', reportError);
    } finally {
      setIsReporting(false);
    }
  };

  if (hasReported) {
    return (
      <div className={`error-reporter reported ${className}`}>
        <div className="error-reporter-icon">✅</div>
        <div className="error-reporter-message">
          Error reported successfully. Thank you!
        </div>
      </div>
    );
  }

  return (
    <div className={`error-reporter ${className}`}>
      <div className="error-reporter-content">
        <div className="error-reporter-icon">⚠️</div>
        <div className="error-reporter-details">
          <div className="error-reporter-title">Something went wrong</div>
          <div className="error-reporter-message">{error.message}</div>
        </div>
      </div>
      <button
        className="error-reporter-btn"
        onClick={handleReport}
        disabled={isReporting}
      >
        {isReporting ? (
          <>
            <i className="fas fa-spinner fa-spin"></i>
            Reporting...
          </>
        ) : (
          <>
            <i className="fas fa-bug"></i>
            Report Issue
          </>
        )}
      </button>
    </div>
  );
};

/**
 * Performance Issue Reporter
 */
export const PerformanceReporter = ({ metrics, className = '' }) => {
  const [isReporting, setIsReporting] = useState(false);

  const handleReport = async () => {
    setIsReporting(true);
    
    try {
      await validatorFeedback.submitPerformanceIssue(
        `Performance issue detected: Slow loading times`,
        metrics
      );
    } catch (error) {
      console.error('Failed to report performance issue:', error);
    } finally {
      setIsReporting(false);
    }
  };

  return (
    <div className={`performance-reporter ${className}`}>
      <div className="performance-reporter-content">
        <div className="performance-reporter-icon">⚡</div>
        <div className="performance-reporter-details">
          <div className="performance-reporter-title">Performance Issue</div>
          <div className="performance-reporter-message">
            Page load time: {metrics.loadTime}ms
          </div>
        </div>
      </div>
      <button
        className="performance-reporter-btn"
        onClick={handleReport}
        disabled={isReporting}
      >
        {isReporting ? (
          <>
            <i className="fas fa-spinner fa-spin"></i>
            Reporting...
          </>
        ) : (
          <>
            <i className="fas fa-chart-line"></i>
            Report Performance Issue
          </>
        )}
      </button>
    </div>
  );
};

export default {
  FeedbackForm,
  QuickFeedbackButton,
  FeedbackWidget,
  ErrorReporter,
  PerformanceReporter
};
