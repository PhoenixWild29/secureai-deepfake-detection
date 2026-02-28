/**
 * Validator Feedback Integration Demo
 * Demonstrates the feedback collection functionality
 */

import React, { useState } from 'react';
import { 
  FeedbackForm, 
  QuickFeedbackButton, 
  ErrorReporter, 
  PerformanceReporter 
} from './FeedbackComponents';
import validatorFeedback from '../services/ValidatorFeedback';

const FeedbackDemo = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [demoError, setDemoError] = useState(null);
  const [performanceMetrics, setPerformanceMetrics] = useState(null);

  const triggerDemoError = () => {
    const error = new Error('This is a demo error for testing the error reporter');
    error.stack = `Error: This is a demo error for testing the error reporter
    at triggerDemoError (FeedbackDemo.jsx:25:15)
    at HTMLButtonElement.onClick (FeedbackDemo.jsx:45:9)`;
    setDemoError(error);
  };

  const simulatePerformanceIssue = () => {
    const metrics = {
      loadTime: 8500, // 8.5 seconds
      domContentLoaded: 3200,
      firstPaint: 2800,
      firstContentfulPaint: 3100,
      largestContentfulPaint: 7200
    };
    setPerformanceMetrics(metrics);
  };

  const testDirectSubmission = async () => {
    try {
      const result = await validatorFeedback.submit({
        description: 'This is a test feedback submission from the demo component',
        type: 'other',
        priority: 'low',
        email: 'test@example.com'
      });
      alert(`Feedback submitted successfully! ID: ${result.feedback_id}`);
    } catch (error) {
      alert(`Failed to submit feedback: ${error.message}`);
    }
  };

  const testBugReport = async () => {
    try {
      const result = await validatorFeedback.submitBugReport(
        'Demo bug report: Button not working properly',
        {
          component: 'FeedbackDemo',
          userAction: 'click_button',
          timestamp: new Date().toISOString()
        }
      );
      alert(`Bug report submitted successfully! ID: ${result.feedback_id}`);
    } catch (error) {
      alert(`Failed to submit bug report: ${error.message}`);
    }
  };

  const testFeatureRequest = async () => {
    try {
      const result = await validatorFeedback.submitFeatureRequest(
        'Demo feature request: Add dark mode toggle',
        'user@example.com'
      );
      alert(`Feature request submitted successfully! ID: ${result.feedback_id}`);
    } catch (error) {
      alert(`Failed to submit feature request: ${error.message}`);
    }
  };

  const testPerformanceIssue = async () => {
    try {
      const result = await validatorFeedback.submitPerformanceIssue(
        'Demo performance issue: Slow page loading',
        {
          loadTime: 12000,
          renderTime: 8500,
          networkTime: 3500
        }
      );
      alert(`Performance issue submitted successfully! ID: ${result.feedback_id}`);
    } catch (error) {
      alert(`Failed to submit performance issue: ${error.message}`);
    }
  };

  const getStats = () => {
    const stats = validatorFeedback.getStats();
    alert(`Submission Stats:
- Submissions this session: ${stats.submissionsThisSession}
- Max submissions per session: ${stats.maxSubmissionsPerSession}
- Initialized: ${stats.isInitialized}`);
  };

  return (
    <div className="feedback-demo">
      <div className="feedback-demo-container">
        <h2>Validator Feedback Integration Demo</h2>
        <p>Test the feedback collection functionality with various scenarios.</p>

        <div className="demo-section">
          <h3>Feedback Form Components</h3>
          <div className="demo-buttons">
            <button 
              className="demo-btn"
              onClick={() => setIsModalOpen(true)}
            >
              Open Feedback Modal
            </button>
            
            <QuickFeedbackButton 
              type="bug"
              description="Quick bug report from demo"
              className="demo-btn"
            >
              Quick Bug Report
            </QuickFeedbackButton>
            
            <QuickFeedbackButton 
              type="feature_request"
              description="Quick feature request from demo"
              className="demo-btn"
            >
              Quick Feature Request
            </QuickFeedbackButton>
          </div>
        </div>

        <div className="demo-section">
          <h3>Direct API Testing</h3>
          <div className="demo-buttons">
            <button className="demo-btn" onClick={testDirectSubmission}>
              Test Direct Submission
            </button>
            <button className="demo-btn" onClick={testBugReport}>
              Test Bug Report
            </button>
            <button className="demo-btn" onClick={testFeatureRequest}>
              Test Feature Request
            </button>
            <button className="demo-btn" onClick={testPerformanceIssue}>
              Test Performance Issue
            </button>
          </div>
        </div>

        <div className="demo-section">
          <h3>Error Reporting</h3>
          <div className="demo-buttons">
            <button className="demo-btn" onClick={triggerDemoError}>
              Trigger Demo Error
            </button>
          </div>
          {demoError && (
            <ErrorReporter 
              error={demoError}
              onReport={() => {
                setDemoError(null);
                alert('Demo error reported successfully!');
              }}
            />
          )}
        </div>

        <div className="demo-section">
          <h3>Performance Reporting</h3>
          <div className="demo-buttons">
            <button className="demo-btn" onClick={simulatePerformanceIssue}>
              Simulate Performance Issue
            </button>
          </div>
          {performanceMetrics && (
            <PerformanceReporter 
              metrics={performanceMetrics}
              className="demo-performance-reporter"
            />
          )}
        </div>

        <div className="demo-section">
          <h3>Statistics & Info</h3>
          <div className="demo-buttons">
            <button className="demo-btn" onClick={getStats}>
              Get Submission Stats
            </button>
            <button 
              className="demo-btn"
              onClick={() => validatorFeedback.resetSubmissionCounter()}
            >
              Reset Counter (Testing)
            </button>
          </div>
        </div>

        <div className="demo-section">
          <h3>Automatic Context Information</h3>
          <div className="context-info">
            <p><strong>Current Page:</strong> {validatorFeedback.getPageName()}</p>
            <p><strong>Session ID:</strong> {validatorFeedback.getSessionId()}</p>
            <p><strong>User ID:</strong> {validatorFeedback.getUserId() || 'Not available'}</p>
            <p><strong>User Agent:</strong> {navigator.userAgent}</p>
            <p><strong>Screen Resolution:</strong> {screen.width}x{screen.height}</p>
            <p><strong>Viewport:</strong> {window.innerWidth}x{window.innerHeight}</p>
            <p><strong>Language:</strong> {navigator.language}</p>
            <p><strong>Platform:</strong> {navigator.platform}</p>
          </div>
        </div>
      </div>

      {/* Feedback Modal */}
      <FeedbackForm
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        initialType="other"
        initialDescription="Demo feedback submission"
      />
    </div>
  );
};

export default FeedbackDemo;
