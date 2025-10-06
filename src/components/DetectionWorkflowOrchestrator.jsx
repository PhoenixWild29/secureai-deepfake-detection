/**
 * Detection Workflow Orchestrator Component
 * Main component managing the complete detection workflow from upload through result visualization
 */

import React, { useEffect, useState, useCallback } from 'react';
import { useWorkflow, useWorkflowStage } from '../context/WorkflowContext';
import { useWorkflowPersistence, useWorkflowRecovery } from '../hooks/useWorkflowState';
import {
  handleUploadError,
  handleAnalysisError,
  handleResultsError,
  getRecoveryStrategy,
  formatErrorForDisplay,
  logError,
  createRetryConfig
} from '../utils/workflowErrorHandling';
import VideoUploadComponent from './VideoUpload/VideoUploadComponent';
import AnalysisProgressTracker from './AnalysisProgressTracker/AnalysisProgressTracker';
import FrameProgressVisualization from './FrameProgressVisualization';
import DetectionResultsViewer from './DetectionResultsViewer/DetectionResultsViewer';
import './workflow.css';

/**
 * Detection Workflow Orchestrator Component
 * @returns {JSX.Element} Workflow orchestrator component
 */
const DetectionWorkflowOrchestrator = () => {
  // Workflow context
  const workflow = useWorkflow();
  const stage = useWorkflowStage();
  
  // Local state
  const [isNavigating, setIsNavigating] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);

  // Workflow persistence
  const persistence = useWorkflowPersistence(workflow, {
    enableAutoSave: true,
    saveDelay: 1000,
    onSave: (savedState) => {
      console.log('Workflow state saved:', savedState);
    },
    onError: (error) => {
      console.error('Persistence error:', error);
    }
  });

  // Workflow recovery
  const recovery = useWorkflowRecovery(workflow.restoreSession, {
    enableRecovery: true,
    onRecovery: (recoveredState) => {
      console.log('Workflow state recovered:', recoveredState);
    },
    onRecoveryError: (error) => {
      console.error('Recovery error:', error);
    }
  });

  /**
   * Handle file upload completion
   * @param {Object} uploadResult - Upload result
   * @param {Object} fileData - File data
   */
  const handleUploadComplete = useCallback((uploadResult, fileData) => {
    try {
      // Set file data in workflow state
      workflow.setFile({
        file: fileData.file,
        metadata: fileData.metadata,
        preview: fileData.preview
      });

      // Set upload result
      workflow.setUploadProgress({
        progress: uploadResult,
        result: uploadResult
      });

      // Start analysis
      const analysisId = uploadResult.video_id || `analysis_${Date.now()}`;
      workflow.startAnalysis(analysisId);

    } catch (error) {
      const handledError = handleUploadError(error, { fileData });
      workflow.setError({
        error: handledError,
        stage: WORKFLOW_STAGES.UPLOAD
      });
      logError(handledError);
    }
  }, [workflow]);

  /**
   * Handle upload error
   * @param {string} errorMessage - Error message
   */
  const handleUploadErrorCallback = useCallback((errorMessage) => {
    const error = new Error(errorMessage);
    const handledError = handleUploadError(error);
    workflow.setError({
      error: handledError,
      stage: WORKFLOW_STAGES.UPLOAD
    });
    logError(handledError);
  }, [workflow]);

  /**
   * Handle file selection
   * @param {File} file - Selected file
   * @param {Object} fileData - File data
   */
  const handleFileSelect = useCallback((file, fileData) => {
    // File selection doesn't change workflow stage
    // Just store the file data for later use
    console.log('File selected:', file, fileData);
  }, []);

  /**
   * Handle analysis progress update
   * @param {Object} progressData - Progress data
   */
  const handleAnalysisProgress = useCallback((progressData) => {
    workflow.setAnalysisProgress(progressData);
  }, [workflow]);

  /**
   * Handle analysis completion
   * @param {Object} results - Analysis results
   */
  const handleAnalysisComplete = useCallback((results) => {
    try {
      workflow.setResults({
        results: results.results || results,
        metadata: {
          analysisId: results.analysisId,
          completedAt: new Date().toISOString()
        },
        blockchainHash: results.blockchainHash || `hash_${Date.now()}`,
        confidenceScore: results.confidenceScore || 0.85
      });
    } catch (error) {
      const handledError = handleAnalysisError(error, { results });
      workflow.setError({
        error: handledError,
        stage: WORKFLOW_STAGES.PROCESSING
      });
      logError(handledError);
    }
  }, [workflow]);

  /**
   * Handle analysis error
   * @param {Error} error - Analysis error
   */
  const handleAnalysisErrorCallback = useCallback((error) => {
    const handledError = handleAnalysisError(error);
    workflow.setError({
      error: handledError,
      stage: WORKFLOW_STAGES.PROCESSING
    });
    logError(handledError);
  }, [workflow]);

  /**
   * Handle new analysis request
   */
  const handleNewAnalysis = useCallback(() => {
    setPendingAction(() => workflow.resetWorkflow);
    setShowConfirmation(true);
  }, [workflow]);

  /**
   * Handle download request
   */
  const handleDownload = useCallback(() => {
    // Mock download functionality
    console.log('Downloading analysis report...');
    // In real implementation, this would download the results
  }, []);

  /**
   * Handle navigation
   * @param {string} targetStage - Target workflow stage
   */
  const handleNavigation = useCallback((targetStage) => {
    if (isNavigating) return;

    setIsNavigating(true);
    
    try {
      // Check if navigation requires confirmation
      if (workflow.uploadedFile && targetStage === WORKFLOW_STAGES.UPLOAD) {
        setPendingAction(() => () => {
          workflow.setStage(targetStage);
          setIsNavigating(false);
        });
        setShowConfirmation(true);
        return;
      }

      workflow.setStage(targetStage);
    } catch (error) {
      console.error('Navigation error:', error);
    } finally {
      setIsNavigating(false);
    }
  }, [workflow, isNavigating]);

  /**
   * Handle retry action
   */
  const handleRetry = useCallback(() => {
    if (workflow.error) {
      const retryConfig = createRetryConfig(workflow.error);
      
      if (retryConfig.canRetry) {
        // Clear current error
        workflow.clearError();
        
        // Retry based on current stage
        if (stage.isUpload) {
          // Retry upload - this would trigger re-upload
          console.log('Retrying upload...');
        } else if (stage.isProcessing) {
          // Retry analysis
          workflow.startAnalysis(workflow.analysisId);
        } else if (stage.isResults) {
          // Retry loading results
          console.log('Retrying results load...');
        }
      }
    }
  }, [workflow, stage]);

  /**
   * Handle confirmation dialog actions
   */
  const handleConfirmation = useCallback((confirmed) => {
    if (confirmed && pendingAction) {
      pendingAction();
    }
    
    setShowConfirmation(false);
    setPendingAction(null);
  }, [pendingAction]);

  /**
   * Handle frame update from FrameProgressVisualization
   * @param {Object} frameData - Frame analysis data
   */
  const handleFrameUpdate = useCallback((frameData) => {
    // Update workflow state with latest frame information
    workflow.setAnalysisProgress({
      ...workflow.analysisProgress,
      current_frame: frameData.frame_number,
      frame_data: frameData
    });
  }, [workflow]);

  /**
   * Render processing stage with enhanced visualization
   */
  const renderProcessingStage = useCallback(() => {
    return (
      <div className="processing-stage-enhanced">
        {/* Original AnalysisProgressTracker */}
        <AnalysisProgressTracker
          analysisId={workflow.analysisId}
          uploadId={workflow.uploadId}
          filename={workflow.uploadedFile?.name || 'Unknown'}
          onAnalysisComplete={handleAnalysisComplete}
          onAnalysisError={handleAnalysisErrorCallback}
          onRetry={handleRetry}
          options={{
            websocketUrl: 'ws://localhost:8000/ws',
            maxRetries: 3,
            enableBlockchain: true,
            modelType: 'ensemble'
          }}
        />
        
        {/* New FrameProgressVisualization */}
        {workflow.analysisId && (
          <FrameProgressVisualization
            analysisId={workflow.analysisId}
            websocketUrl="ws://localhost:8000/ws"
            onFrameUpdate={handleFrameUpdate}
            options={{
              maxThumbnails: 20,
              enableHeatmaps: true,
              enableConfidenceOverlays: true,
              enableSmoothAnimations: true
            }}
          />
        )}
      </div>
    );
  }, [workflow, handleAnalysisComplete, handleAnalysisErrorCallback, handleRetry, handleFrameUpdate]);

  /**
   * Render current workflow stage component
   */
  const renderCurrentStage = () => {
    switch (workflow.currentStage) {
      case WORKFLOW_STAGES.UPLOAD:
        return (
          <VideoUploadComponent
            onUploadComplete={handleUploadComplete}
            onUploadError={handleUploadErrorCallback}
            onFileSelect={handleFileSelect}
            options={{
              userId: 'current_user', // This would come from auth context
              metadata: {
                source: 'workflow_orchestrator'
              }
            }}
          />
        );

      case WORKFLOW_STAGES.PROCESSING:
        return renderProcessingStage();

      case WORKFLOW_STAGES.RESULTS:
        return (
          <DetectionResultsViewer
            analysisId={workflow.analysisId}
            onExport={() => handleDownload()}
            onError={(error) => console.error('DetectionResultsViewer error:', error)}
            options={{
              showExportButton: true,
              showBlockchainVerification: true,
              enableFrameViewer: true,
              viewerMode: 'summary'
            }}
          />
        );

      case WORKFLOW_STAGES.ERROR:
        return renderErrorStage();

      case WORKFLOW_STAGES.INITIAL:
      default:
        return (
          <div className="workflow-initial">
            <h2>Welcome to SecureAI DeepFake Detection</h2>
            <p>Upload a video to begin analysis</p>
            <button 
              className="btn-primary"
              onClick={() => workflow.setStage(WORKFLOW_STAGES.UPLOAD)}
            >
              Start Analysis
            </button>
          </div>
        );
    }
  };

  /**
   * Render error stage
   */
  const renderErrorStage = () => {
    if (!workflow.error) {
      return null;
    }

    const errorDisplay = formatErrorForDisplay(workflow.error);
    const recoveryStrategy = getRecoveryStrategy(workflow.error, workflow);

    return (
      <div className="workflow-error">
        <div className="error-container">
          <h2 className="error-title">{errorDisplay.title}</h2>
          <p className="error-message">{errorDisplay.message}</p>
          <p className="error-recovery">{errorDisplay.recoveryMessage}</p>
          
          <div className="error-actions">
            {recoveryStrategy.canRetry && (
              <button 
                className="btn-primary"
                onClick={handleRetry}
                disabled={workflow.isRetrying}
              >
                {workflow.isRetrying ? 'Retrying...' : 'Try Again'}
              </button>
            )}
            
            <button 
              className="btn-secondary"
              onClick={() => workflow.setStage(recoveryStrategy.fallbackStage)}
            >
              {recoveryStrategy.fallbackStage === WORKFLOW_STAGES.UPLOAD ? 'Upload New Video' : 'Start Over'}
            </button>
            
            <button 
              className="btn-secondary"
              onClick={() => workflow.clearError()}
            >
              Dismiss
            </button>
          </div>
        </div>
      </div>
    );
  };

  /**
   * Render workflow navigation
   */
  const renderNavigation = () => {
    if (workflow.currentStage === WORKFLOW_STAGES.INITIAL) {
      return null;
    }

    return (
      <div className="workflow-navigation">
        <div className="nav-progress">
          <div className="progress-steps">
            <div className={`step ${stage.isUpload ? 'active' : stage.isProcessing || stage.isResults ? 'completed' : ''}`}>
              <span className="step-number">1</span>
              <span className="step-label">Upload</span>
            </div>
            <div className={`step ${stage.isProcessing ? 'active' : stage.isResults ? 'completed' : ''}`}>
              <span className="step-number">2</span>
              <span className="step-label">Analysis</span>
            </div>
            <div className={`step ${stage.isResults ? 'active' : ''}`}>
              <span className="step-number">3</span>
              <span className="step-label">Results</span>
            </div>
          </div>
        </div>
        
        <div className="nav-controls">
          {workflow.canGoBack && (
            <button 
              className="btn-secondary"
              onClick={() => handleNavigation(WORKFLOW_STAGES.UPLOAD)}
              disabled={isNavigating}
            >
              ← Back
            </button>
          )}
          
          {workflow.currentStage === WORKFLOW_STAGES.RESULTS && (
            <button 
              className="btn-primary"
              onClick={handleNewAnalysis}
            >
              New Analysis →
            </button>
          )}
        </div>
      </div>
    );
  };

  /**
   * Render confirmation dialog
   */
  const renderConfirmationDialog = () => {
    if (!showConfirmation) return null;

    return (
      <div className="confirmation-overlay">
        <div className="confirmation-dialog">
          <h3>Confirm Action</h3>
          <p>This action will discard your current progress. Are you sure you want to continue?</p>
          <div className="confirmation-actions">
            <button 
              className="btn-secondary"
              onClick={() => handleConfirmation(false)}
            >
              Cancel
            </button>
            <button 
              className="btn-primary"
              onClick={() => handleConfirmation(true)}
            >
              Continue
            </button>
          </div>
        </div>
      </div>
    );
  };

  // Show loading state during recovery
  if (recovery.isRecovering) {
    return (
      <div className="workflow-orchestrator">
        <div className="workflow-loading">
          <div className="loading-spinner"></div>
          <p>Restoring your session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="workflow-orchestrator">
      {renderNavigation()}
      
      <div className="workflow-content">
        {renderCurrentStage()}
      </div>
      
      {renderConfirmationDialog()}
    </div>
  );
};

export default DetectionWorkflowOrchestrator;
