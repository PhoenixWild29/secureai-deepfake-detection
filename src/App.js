/**
 * Main Application Component
 * Integrates the Detection Workflow Orchestrator with the existing application structure
 */

import React, { Component, Suspense, ErrorBoundary } from 'react';
import { WorkflowProvider } from './context/WorkflowContext';
import DetectionWorkflowOrchestrator from './components/DetectionWorkflowOrchestrator';
import BreadcrumbNavigation from './components/BreadcrumbNavigation';
import { useNavigation } from './hooks/useNavigation';
import { handleReactError, ERROR_SEVERITY } from './utils/workflowErrorHandling';
import { FeedbackWidget, ErrorReporter } from './components/FeedbackComponents';
import './App.css';

/**
 * Error Boundary Component for catching React errors
 */
class WorkflowErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log the error
    const handledError = handleReactError(error, errorInfo);
    this.setState({
      error: handledError,
      errorInfo: errorInfo
    });

    // Log to console for development
    console.error('Workflow Error Boundary caught an error:', error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      const error = this.state.error;
      
      return (
        <div className="error-boundary">
          <div className="error-boundary-container">
            <h2 className="error-boundary-title">
              {error?.title || 'Something went wrong'}
            </h2>
            <p className="error-boundary-message">
              {error?.message || 'An unexpected error occurred in the workflow.'}
            </p>
            
            {/* Error Reporter Component */}
            <ErrorReporter 
              error={this.state.error || { message: error?.message || 'Unknown error' }}
              onReport={() => console.log('Error reported successfully')}
            />
            
            <div className="error-boundary-actions">
              <button 
                className="btn-primary"
                onClick={this.handleRetry}
              >
                Try Again
              </button>
              <button 
                className="btn-secondary"
                onClick={() => window.location.reload()}
              >
                Reload Page
              </button>
            </div>
            {process.env.NODE_ENV === 'development' && (
              <details className="error-boundary-details">
                <summary>Error Details (Development)</summary>
                <pre className="error-boundary-stack">
                  {this.state.errorInfo?.componentStack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Loading Component for Suspense fallback
 */
const LoadingFallback = () => (
  <div className="app-loading">
    <div className="loading-spinner"></div>
    <p>Loading SecureAI DeepFake Detection...</p>
  </div>
);

/**
 * App Content Component with Navigation Hook
 */
const AppContent = () => {
  const navigation = useNavigation({
    enableDataPrefetching: true,
    enableHistoryTracking: true,
    enablePerformanceTracking: true
  });

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="header-brand">
            <i className="fas fa-shield-alt"></i>
            <h1>SecureAI</h1>
            <span className="header-subtitle">DeepFake Detection</span>
          </div>
          <div className="header-actions">
            <button 
              className="btn-secondary btn-sm"
              onClick={() => navigation.handleNavigate('/login')}
              title="Login"
            >
              <i className="fas fa-sign-in-alt"></i>
              Login
            </button>
            <button 
              className="btn-secondary btn-sm"
              onClick={() => window.open('/docs', '_blank')}
              title="Documentation"
            >
              <i className="fas fa-book"></i>
              Docs
            </button>
          </div>
        </div>
        
        {/* Breadcrumb Navigation */}
        <div className="header-breadcrumbs">
          <BreadcrumbNavigation 
            useNavigationHook={true}
            className="app-breadcrumbs"
            maxItems={4}
          />
        </div>
      </header>

      {/* Main Content */}
      <main className="app-main">
        <DetectionWorkflowOrchestrator />
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <div className="footer-content">
          <div className="footer-info">
            <p>&copy; 2025 SecureAI. All rights reserved.</p>
            <p>Enterprise-grade deepfake detection with blockchain verification.</p>
          </div>
          <div className="footer-links">
            <a href="/privacy" className="footer-link">Privacy Policy</a>
            <a href="/terms" className="footer-link">Terms of Service</a>
            <a href="/support" className="footer-link">Support</a>
          </div>
        </div>
      </footer>

      {/* Feedback Widget */}
      <FeedbackWidget />
    </div>
  );
};

/**
 * Main App Component
 */
const App = () => {
  return (
    <div className="app">
      <ErrorBoundary FallbackComponent={WorkflowErrorBoundary}>
        <Suspense fallback={<LoadingFallback />}>
          <WorkflowProvider>
            <AppContent />
          </WorkflowProvider>
        </Suspense>
      </ErrorBoundary>
    </div>
  );
};

export default App;
