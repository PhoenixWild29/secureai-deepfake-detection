/**
 * Workflow Context
 * React Context for shared workflow state management across all detection workflow components
 */

import React, { createContext, useContext, useReducer, useCallback } from 'react';

// Workflow stages
export const WORKFLOW_STAGES = {
  UPLOAD: 'upload',
  PROCESSING: 'processing',
  RESULTS: 'results',
  ERROR: 'error',
  INITIAL: 'initial'
};

// Workflow actions
export const WORKFLOW_ACTIONS = {
  SET_STAGE: 'SET_STAGE',
  SET_FILE: 'SET_FILE',
  START_ANALYSIS: 'START_ANALYSIS',
  UPDATE_PROGRESS: 'UPDATE_PROGRESS',
  SET_RESULTS: 'SET_RESULTS',
  SET_ERROR: 'SET_ERROR',
  CLEAR_ERROR: 'CLEAR_ERROR',
  RESET_WORKFLOW: 'RESET_WORKFLOW',
  SET_UPLOAD_PROGRESS: 'SET_UPLOAD_PROGRESS',
  SET_ANALYSIS_PROGRESS: 'SET_ANALYSIS_PROGRESS',
  SET_SESSION_DATA: 'SET_SESSION_DATA'
};

// Initial workflow state
const initialState = {
  // Current workflow stage
  currentStage: WORKFLOW_STAGES.INITIAL,
  
  // Upload stage data
  uploadedFile: null,
  fileMetadata: null,
  filePreview: null,
  uploadProgress: null,
  uploadResult: null,
  
  // Processing stage data
  analysisId: null,
  analysisProgress: null,
  processingStatus: null,
  estimatedTimeRemaining: null,
  
  // Results stage data
  analysisResults: null,
  resultMetadata: null,
  blockchainHash: null,
  confidenceScore: null,
  
  // Error handling
  error: null,
  errorStage: null,
  retryCount: 0,
  
  // Session management
  sessionId: null,
  lastActivity: null,
  isRecovered: false,
  
  // Navigation state
  canGoBack: false,
  canGoForward: false,
  navigationHistory: [],
  
  // UI state
  isLoading: false,
  isRetrying: false,
  showConfirmationDialog: false,
  confirmationAction: null
};

/**
 * Workflow reducer for state management
 * @param {Object} state - Current state
 * @param {Object} action - Action to perform
 * @returns {Object} New state
 */
const workflowReducer = (state, action) => {
  switch (action.type) {
    case WORKFLOW_ACTIONS.SET_STAGE:
      return {
        ...state,
        currentStage: action.payload.stage,
        canGoBack: action.payload.stage !== WORKFLOW_STAGES.UPLOAD,
        canGoForward: action.payload.stage !== WORKFLOW_STAGES.RESULTS,
        navigationHistory: [...state.navigationHistory, state.currentStage],
        lastActivity: new Date().toISOString()
      };

    case WORKFLOW_ACTIONS.SET_FILE:
      return {
        ...state,
        uploadedFile: action.payload.file,
        fileMetadata: action.payload.metadata,
        filePreview: action.payload.preview,
        error: null,
        errorStage: null,
        lastActivity: new Date().toISOString()
      };

    case WORKFLOW_ACTIONS.START_ANALYSIS:
      return {
        ...state,
        analysisId: action.payload.analysisId,
        currentStage: WORKFLOW_STAGES.PROCESSING,
        processingStatus: 'starting',
        analysisProgress: 0,
        isLoading: true,
        error: null,
        errorStage: null,
        lastActivity: new Date().toISOString()
      };

    case WORKFLOW_ACTIONS.UPDATE_PROGRESS:
      return {
        ...state,
        analysisProgress: action.payload.progress,
        processingStatus: action.payload.status || state.processingStatus,
        estimatedTimeRemaining: action.payload.estimatedTime,
        lastActivity: new Date().toISOString()
      };

    case WORKFLOW_ACTIONS.SET_RESULTS:
      return {
        ...state,
        currentStage: WORKFLOW_STAGES.RESULTS,
        analysisResults: action.payload.results,
        resultMetadata: action.payload.metadata,
        blockchainHash: action.payload.blockchainHash,
        confidenceScore: action.payload.confidenceScore,
        isLoading: false,
        processingStatus: 'completed',
        lastActivity: new Date().toISOString()
      };

    case WORKFLOW_ACTIONS.SET_ERROR:
      return {
        ...state,
        currentStage: WORKFLOW_STAGES.ERROR,
        error: action.payload.error,
        errorStage: action.payload.stage || state.currentStage,
        isLoading: false,
        isRetrying: false,
        lastActivity: new Date().toISOString()
      };

    case WORKFLOW_ACTIONS.CLEAR_ERROR:
      return {
        ...state,
        error: null,
        errorStage: null,
        retryCount: 0,
        isRetrying: false
      };

    case WORKFLOW_ACTIONS.RESET_WORKFLOW:
      return {
        ...initialState,
        sessionId: state.sessionId,
        isRecovered: false
      };

    case WORKFLOW_ACTIONS.SET_UPLOAD_PROGRESS:
      return {
        ...state,
        uploadProgress: action.payload.progress,
        uploadResult: action.payload.result,
        lastActivity: new Date().toISOString()
      };

    case WORKFLOW_ACTIONS.SET_ANALYSIS_PROGRESS:
      return {
        ...state,
        analysisProgress: action.payload.progress,
        processingStatus: action.payload.status,
        estimatedTimeRemaining: action.payload.estimatedTime,
        lastActivity: new Date().toISOString()
      };

    case WORKFLOW_ACTIONS.SET_SESSION_DATA:
      return {
        ...state,
        ...action.payload,
        isRecovered: true,
        lastActivity: new Date().toISOString()
      };

    default:
      return state;
  }
};

// Create workflow context
const WorkflowContext = createContext(null);

/**
 * Workflow Provider Component
 * Provides workflow context to all child components
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Child components
 * @returns {JSX.Element} Workflow provider
 */
export const WorkflowProvider = ({ children }) => {
  const [state, dispatch] = useReducer(workflowReducer, initialState);

  // Generate session ID if not present
  React.useEffect(() => {
    if (!state.sessionId) {
      const sessionId = `workflow_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      dispatch({
        type: WORKFLOW_ACTIONS.SET_SESSION_DATA,
        payload: { sessionId }
      });
    }
  }, [state.sessionId]);

  // Workflow action creators
  const actions = {
    /**
     * Set current workflow stage
     * @param {string} stage - Target workflow stage
     */
    setStage: useCallback((stage) => {
      dispatch({
        type: WORKFLOW_ACTIONS.SET_STAGE,
        payload: { stage }
      });
    }, []),

    /**
     * Set uploaded file and metadata
     * @param {Object} payload - File data
     */
    setFile: useCallback((payload) => {
      dispatch({
        type: WORKFLOW_ACTIONS.SET_FILE,
        payload
      });
    }, []),

    /**
     * Start analysis process
     * @param {string} analysisId - Analysis ID
     */
    startAnalysis: useCallback((analysisId) => {
      dispatch({
        type: WORKFLOW_ACTIONS.START_ANALYSIS,
        payload: { analysisId }
      });
    }, []),

    /**
     * Update analysis progress
     * @param {Object} payload - Progress data
     */
    updateProgress: useCallback((payload) => {
      dispatch({
        type: WORKFLOW_ACTIONS.UPDATE_PROGRESS,
        payload
      });
    }, []),

    /**
     * Set analysis results
     * @param {Object} payload - Results data
     */
    setResults: useCallback((payload) => {
      dispatch({
        type: WORKFLOW_ACTIONS.SET_RESULTS,
        payload
      });
    }, []),

    /**
     * Set workflow error
     * @param {Object} payload - Error data
     */
    setError: useCallback((payload) => {
      dispatch({
        type: WORKFLOW_ACTIONS.SET_ERROR,
        payload
      });
    }, []),

    /**
     * Clear current error
     */
    clearError: useCallback(() => {
      dispatch({
        type: WORKFLOW_ACTIONS.CLEAR_ERROR
      });
    }, []),

    /**
     * Reset entire workflow
     */
    resetWorkflow: useCallback(() => {
      dispatch({
        type: WORKFLOW_ACTIONS.RESET_WORKFLOW
      });
    }, []),

    /**
     * Set upload progress
     * @param {Object} payload - Upload progress data
     */
    setUploadProgress: useCallback((payload) => {
      dispatch({
        type: WORKFLOW_ACTIONS.SET_UPLOAD_PROGRESS,
        payload
      });
    }, []),

    /**
     * Set analysis progress
     * @param {Object} payload - Analysis progress data
     */
    setAnalysisProgress: useCallback((payload) => {
      dispatch({
        type: WORKFLOW_ACTIONS.SET_ANALYSIS_PROGRESS,
        payload
      });
    }, []),

    /**
     * Restore session data
     * @param {Object} payload - Session data to restore
     */
    restoreSession: useCallback((payload) => {
      dispatch({
        type: WORKFLOW_ACTIONS.SET_SESSION_DATA,
        payload
      });
    }, [])
  };

  // Context value
  const contextValue = {
    ...state,
    ...actions
  };

  return (
    <WorkflowContext.Provider value={contextValue}>
      {children}
    </WorkflowContext.Provider>
  );
};

/**
 * Hook to use workflow context
 * @returns {Object} Workflow context value
 */
export const useWorkflow = () => {
  const context = useContext(WorkflowContext);
  
  if (!context) {
    throw new Error('useWorkflow must be used within a WorkflowProvider');
  }
  
  return context;
};

/**
 * Hook to get workflow state only (read-only)
 * @returns {Object} Workflow state
 */
export const useWorkflowState = () => {
  const context = useWorkflow();
  const { currentStage, uploadedFile, analysisResults, error, isLoading } = context;
  
  return {
    currentStage,
    uploadedFile,
    analysisResults,
    error,
    isLoading
  };
};

/**
 * Hook to get workflow actions only
 * @returns {Object} Workflow actions
 */
export const useWorkflowActions = () => {
  const context = useWorkflow();
  const {
    setStage,
    setFile,
    startAnalysis,
    updateProgress,
    setResults,
    setError,
    clearError,
    resetWorkflow,
    setUploadProgress,
    setAnalysisProgress,
    restoreSession
  } = context;
  
  return {
    setStage,
    setFile,
    startAnalysis,
    updateProgress,
    setResults,
    setError,
    clearError,
    resetWorkflow,
    setUploadProgress,
    setAnalysisProgress,
    restoreSession
  };
};

/**
 * Hook to get workflow stage information
 * @returns {Object} Stage information
 */
export const useWorkflowStage = () => {
  const context = useWorkflow();
  const { currentStage, canGoBack, canGoForward, navigationHistory } = context;
  
  return {
    currentStage,
    canGoBack,
    canGoForward,
    navigationHistory,
    isUpload: currentStage === WORKFLOW_STAGES.UPLOAD,
    isProcessing: currentStage === WORKFLOW_STAGES.PROCESSING,
    isResults: currentStage === WORKFLOW_STAGES.RESULTS,
    isError: currentStage === WORKFLOW_STAGES.ERROR,
    isInitial: currentStage === WORKFLOW_STAGES.INITIAL
  };
};

export default WorkflowContext;
