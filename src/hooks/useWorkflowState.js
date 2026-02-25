/**
 * Workflow State Hook
 * Custom hook for managing workflow state persistence and recovery
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { WORKFLOW_STAGES } from '../context/WorkflowContext';

// Local storage keys
const STORAGE_KEYS = {
  WORKFLOW_STATE: 'secureai_workflow_state',
  SESSION_ID: 'secureai_workflow_session',
  LAST_ACTIVITY: 'secureai_workflow_last_activity'
};

// Session timeout (30 minutes)
const SESSION_TIMEOUT = 30 * 60 * 1000;

/**
 * Custom hook for workflow state persistence
 * @param {Object} options - Hook options
 * @returns {Object} State persistence utilities
 */
export const useWorkflowState = (options = {}) => {
  const {
    enablePersistence = true,
    enableRecovery = true,
    sessionTimeout = SESSION_TIMEOUT,
    onStateChange = null,
    onRecovery = null
  } = options;

  // State
  const [isRecovering, setIsRecovering] = useState(false);
  const [recoveryError, setRecoveryError] = useState(null);
  const [lastSavedState, setLastSavedState] = useState(null);
  
  // Refs
  const saveTimeoutRef = useRef(null);
  const isInitializedRef = useRef(false);

  /**
   * Validate workflow state
   * @param {Object} state - State to validate
   * @returns {boolean} True if state is valid
   */
  const validateState = useCallback((state) => {
    if (!state || typeof state !== 'object') {
      return false;
    }

    // Check required fields
    const requiredFields = ['currentStage', 'sessionId'];
    for (const field of requiredFields) {
      if (!(field in state)) {
        return false;
      }
    }

    // Validate stage
    if (!Object.values(WORKFLOW_STAGES).includes(state.currentStage)) {
      return false;
    }

    // Check session timeout
    if (state.lastActivity) {
      const lastActivity = new Date(state.lastActivity);
      const now = new Date();
      const timeDiff = now.getTime() - lastActivity.getTime();
      
      if (timeDiff > sessionTimeout) {
        return false; // Session expired
      }
    }

    return true;
  }, [sessionTimeout]);

  /**
   * Save workflow state to localStorage
   * @param {Object} state - State to save
   */
  const saveState = useCallback((state) => {
    if (!enablePersistence) {
      return;
    }

    try {
      const stateToSave = {
        ...state,
        lastSaved: new Date().toISOString(),
        version: '1.0.0'
      };

      localStorage.setItem(STORAGE_KEYS.WORKFLOW_STATE, JSON.stringify(stateToSave));
      localStorage.setItem(STORAGE_KEYS.LAST_ACTIVITY, new Date().toISOString());
      
      setLastSavedState(stateToSave);
      
      if (onStateChange) {
        onStateChange(stateToSave);
      }
    } catch (error) {
      console.error('Failed to save workflow state:', error);
    }
  }, [enablePersistence, onStateChange]);

  /**
   * Load workflow state from localStorage
   * @returns {Object|null} Recovered state or null
   */
  const loadState = useCallback(() => {
    if (!enableRecovery) {
      return null;
    }

    try {
      const savedState = localStorage.getItem(STORAGE_KEYS.WORKFLOW_STATE);
      if (!savedState) {
        return null;
      }

      const parsedState = JSON.parse(savedState);
      
      // Validate state
      if (!validateState(parsedState)) {
        console.warn('Invalid or expired workflow state, clearing...');
        clearState();
        return null;
      }

      return parsedState;
    } catch (error) {
      console.error('Failed to load workflow state:', error);
      setRecoveryError(error.message);
      return null;
    }
  }, [enableRecovery, validateState]);

  /**
   * Clear workflow state from localStorage
   */
  const clearState = useCallback(() => {
    try {
      localStorage.removeItem(STORAGE_KEYS.WORKFLOW_STATE);
      localStorage.removeItem(STORAGE_KEYS.SESSION_ID);
      localStorage.removeItem(STORAGE_KEYS.LAST_ACTIVITY);
      setLastSavedState(null);
    } catch (error) {
      console.error('Failed to clear workflow state:', error);
    }
  }, []);

  /**
   * Restore workflow state
   * @param {Function} restoreCallback - Callback to restore state
   */
  const restoreState = useCallback((restoreCallback) => {
    if (!enableRecovery) {
      return;
    }

    setIsRecovering(true);
    setRecoveryError(null);

    try {
      const savedState = loadState();
      
      if (savedState) {
        restoreCallback(savedState);
        
        if (onRecovery) {
          onRecovery(savedState);
        }
      }
    } catch (error) {
      console.error('Failed to restore workflow state:', error);
      setRecoveryError(error.message);
    } finally {
      setIsRecovering(false);
    }
  }, [enableRecovery, loadState, onRecovery]);

  /**
   * Debounced save function
   * @param {Object} state - State to save
   * @param {number} delay - Delay in milliseconds
   */
  const debouncedSave = useCallback((state, delay = 500) => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = setTimeout(() => {
      saveState(state);
    }, delay);
  }, [saveState]);

  /**
   * Get session information
   * @returns {Object} Session info
   */
  const getSessionInfo = useCallback(() => {
    try {
      const sessionId = localStorage.getItem(STORAGE_KEYS.SESSION_ID);
      const lastActivity = localStorage.getItem(STORAGE_KEYS.LAST_ACTIVITY);
      
      return {
        sessionId,
        lastActivity: lastActivity ? new Date(lastActivity) : null,
        isActive: lastActivity ? (new Date() - new Date(lastActivity)) < sessionTimeout : false
      };
    } catch (error) {
      console.error('Failed to get session info:', error);
      return {
        sessionId: null,
        lastActivity: null,
        isActive: false
      };
    }
  }, [sessionTimeout]);

  /**
   * Update session activity
   */
  const updateSessionActivity = useCallback(() => {
    try {
      localStorage.setItem(STORAGE_KEYS.LAST_ACTIVITY, new Date().toISOString());
    } catch (error) {
      console.error('Failed to update session activity:', error);
    }
  }, []);

  /**
   * Initialize session
   */
  const initializeSession = useCallback(() => {
    if (isInitializedRef.current) {
      return;
    }

    try {
      const sessionId = `workflow_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem(STORAGE_KEYS.SESSION_ID, sessionId);
      updateSessionActivity();
      isInitializedRef.current = true;
    } catch (error) {
      console.error('Failed to initialize session:', error);
    }
  }, [updateSessionActivity]);

  /**
   * Clean up expired sessions
   */
  const cleanupExpiredSessions = useCallback(() => {
    try {
      const lastActivity = localStorage.getItem(STORAGE_KEYS.LAST_ACTIVITY);
      
      if (lastActivity) {
        const lastActivityDate = new Date(lastActivity);
        const now = new Date();
        const timeDiff = now.getTime() - lastActivityDate.getTime();
        
        if (timeDiff > sessionTimeout) {
          clearState();
        }
      }
    } catch (error) {
      console.error('Failed to cleanup expired sessions:', error);
    }
  }, [sessionTimeout, clearState]);

  // Initialize session on mount
  useEffect(() => {
    if (enablePersistence) {
      initializeSession();
      cleanupExpiredSessions();
    }

    // Cleanup on unmount
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [enablePersistence, initializeSession, cleanupExpiredSessions]);

  // Update session activity on window focus
  useEffect(() => {
    const handleFocus = () => {
      updateSessionActivity();
    };

    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, [updateSessionActivity]);

  // Update session activity before page unload
  useEffect(() => {
    const handleBeforeUnload = () => {
      updateSessionActivity();
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [updateSessionActivity]);

  return {
    // State
    isRecovering,
    recoveryError,
    lastSavedState,
    
    // Actions
    saveState,
    loadState,
    clearState,
    restoreState,
    debouncedSave,
    
    // Session management
    getSessionInfo,
    updateSessionActivity,
    initializeSession,
    cleanupExpiredSessions,
    
    // Utilities
    validateState
  };
};

/**
 * Hook for workflow state persistence with automatic saving
 * @param {Object} workflowState - Current workflow state
 * @param {Object} options - Hook options
 * @returns {Object} Persistence utilities
 */
export const useWorkflowPersistence = (workflowState, options = {}) => {
  const {
    enableAutoSave = true,
    saveDelay = 1000,
    onSave = null,
    onError = null
  } = options;

  const persistence = useWorkflowState(options);

  // Auto-save when state changes
  useEffect(() => {
    if (enableAutoSave && workflowState) {
      persistence.debouncedSave(workflowState, saveDelay);
    }
  }, [workflowState, enableAutoSave, saveDelay, persistence]);

  // Handle save events
  useEffect(() => {
    if (onSave && persistence.lastSavedState) {
      onSave(persistence.lastSavedState);
    }
  }, [persistence.lastSavedState, onSave]);

  // Handle errors
  useEffect(() => {
    if (onError && persistence.recoveryError) {
      onError(persistence.recoveryError);
    }
  }, [persistence.recoveryError, onError]);

  return persistence;
};

/**
 * Hook for workflow state recovery on mount
 * @param {Function} restoreCallback - Callback to restore state
 * @param {Object} options - Hook options
 * @returns {Object} Recovery utilities
 */
export const useWorkflowRecovery = (restoreCallback, options = {}) => {
  const {
    enableRecovery = true,
    onRecovery = null,
    onRecoveryError = null
  } = options;

  const persistence = useWorkflowState(options);

  // Attempt recovery on mount
  useEffect(() => {
    if (enableRecovery && restoreCallback) {
      persistence.restoreState(restoreCallback);
    }
  }, [enableRecovery, restoreCallback, persistence]);

  // Handle recovery events
  useEffect(() => {
    if (onRecovery && persistence.lastSavedState && !persistence.isRecovering) {
      onRecovery(persistence.lastSavedState);
    }
  }, [persistence.lastSavedState, persistence.isRecovering, onRecovery]);

  // Handle recovery errors
  useEffect(() => {
    if (onRecoveryError && persistence.recoveryError) {
      onRecoveryError(persistence.recoveryError);
    }
  }, [persistence.recoveryError, onRecoveryError]);

  return {
    isRecovering: persistence.isRecovering,
    recoveryError: persistence.recoveryError,
    restoreState: persistence.restoreState,
    clearState: persistence.clearState
  };
};

export default useWorkflowState;
