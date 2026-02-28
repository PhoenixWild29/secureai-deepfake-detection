/**
 * UploadValidationFeedback Component
 * Client-side validation feedback component for file uploads
 */

import React, { useState, useEffect, useCallback, useRef, forwardRef, useImperativeHandle } from 'react';
import { validateFile, getSystemPerformanceMetrics } from '../../utils/uploadValidationUtils';
import { FILE_CONSTRAINTS, VALIDATION_MESSAGES, ERROR_SEVERITY } from '../../constants/uploadConstants';
import {
  UploadValidationFeedbackProps,
  UploadValidationFeedbackRef,
  ValidationResult,
  ValidationError,
  FileConstraint,
  SystemPerformanceMetrics
} from '../../types/upload';
import styles from './UploadValidationFeedback.module.css';

/**
 * UploadValidationFeedback - Component for displaying file validation feedback
 */
const UploadValidationFeedback = forwardRef<UploadValidationFeedbackRef, UploadValidationFeedbackProps>(
  ({
    file,
    isDragActive = false,
    isUploading = false,
    onValidationComplete,
    onError,
    showConstraints = true,
    showProcessingEstimate = true,
    className = '',
    options = {}
  }, ref) => {
    // Component state
    const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
    const [isValidating, setIsValidating] = useState(false);
    const [systemPerformance, setSystemPerformance] = useState<SystemPerformanceMetrics | null>(null);
    const [constraints, setConstraints] = useState<FileConstraint[]>([]);
    
    // Refs
    const validationTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const lastValidatedFileRef = useRef<File | null>(null);

    // ============================================================================
    // Imperative API for parent components
    // ============================================================================

    useImperativeHandle(ref, () => ({
      validateFile: async (fileToValidate: File) => {
        return await validateFile(fileToValidate, options);
      },
      clearValidation: () => {
        setValidationResult(null);
        setIsValidating(false);
        lastValidatedFileRef.current = null;
      },
      getLastResult: () => validationResult,
      updateConstraints: (newConstraints: FileConstraint[]) => {
        setConstraints(newConstraints);
      }
    }), [validationResult, options]);

    // ============================================================================
    // Initialize constraints and system performance
    // ============================================================================

    useEffect(() => {
      // Initialize system performance metrics
      const performance = getSystemPerformanceMetrics();
      setSystemPerformance(performance);

      // Initialize file constraints
      const initialConstraints: FileConstraint[] = [
        {
          type: 'format',
          value: FILE_CONSTRAINTS.SUPPORTED_FORMATS.join(', '),
          description: 'Supported video formats',
          isRequired: true
        },
        {
          type: 'size',
          value: FILE_CONSTRAINTS.MAX_SIZE_FORMATTED,
          description: 'Maximum file size',
          isRequired: true
        },
        {
          type: 'size',
          value: FILE_CONSTRAINTS.RECOMMENDED_SIZE_FORMATTED,
          description: 'Recommended file size for optimal performance',
          isRequired: false
        }
      ];
      setConstraints(initialConstraints);
    }, []);

    // ============================================================================
    // File validation effect
    // ============================================================================

    useEffect(() => {
      if (!file) {
        setValidationResult(null);
        setIsValidating(false);
        lastValidatedFileRef.current = null;
        return;
      }

      // Skip validation if it's the same file and we already have a result
      if (lastValidatedFileRef.current === file && validationResult) {
        return;
      }

      // Clear any existing timeout
      if (validationTimeoutRef.current) {
        clearTimeout(validationTimeoutRef.current);
      }

      // Start validation
      setIsValidating(true);
      lastValidatedFileRef.current = file;

      // Debounce validation to avoid excessive calls
      validationTimeoutRef.current = setTimeout(async () => {
        try {
          const result = await validateFile(file, {
            ...options,
            systemPerformance: systemPerformance?.level
          });

          setValidationResult(result);
          setIsValidating(false);

          // Call completion callback
          onValidationComplete?.(result);

          // Call error callback if validation failed
          if (!result.isValid && result.errors.length > 0) {
            onError?.(result.errors[0]);
          }

        } catch (error) {
          console.error('Validation failed:', error);
          setIsValidating(false);
          
          const validationError: ValidationError = {
            code: 'VALIDATION_ERROR',
            message: 'An error occurred during file validation',
            severity: ERROR_SEVERITY.ERROR
          };
          
          onError?.(validationError);
        }
      }, 300); // 300ms debounce

      // Cleanup timeout on unmount or file change
      return () => {
        if (validationTimeoutRef.current) {
          clearTimeout(validationTimeoutRef.current);
        }
      };
    }, [file, options, systemPerformance, onValidationComplete, onError, validationResult]);

    // ============================================================================
    // Render helpers
    // ============================================================================

    /**
     * Render file constraints information
     */
    const renderConstraints = () => {
      if (!showConstraints || constraints.length === 0) return null;

      return (
        <div className={styles.constraintsContainer}>
          <h4 className={styles.constraintsTitle}>File Requirements</h4>
          <div className={styles.constraintsList}>
            {constraints.map((constraint, index) => (
              <div key={index} className={styles.constraintItem}>
                <span className={styles.constraintType}>
                  {constraint.type.toUpperCase()}
                </span>
                <span className={styles.constraintValue}>{constraint.value}</span>
                <span className={styles.constraintDescription}>
                  {constraint.description}
                  {constraint.isRequired && (
                    <span className={styles.required}> *</span>
                  )}
                </span>
              </div>
            ))}
          </div>
          <div className={styles.processingInfo}>
            <span className={styles.processingTime}>
              Estimated processing: {FILE_CONSTRAINTS.PROCESSING_TIME_RANGE}
            </span>
          </div>
        </div>
      );
    };

    /**
     * Render validation status
     */
    const renderValidationStatus = () => {
      if (!file) return null;

      if (isValidating) {
        return (
          <div className={styles.validationStatus}>
            <div className={styles.spinner} />
            <span className={styles.statusText}>Validating file...</span>
          </div>
        );
      }

      if (!validationResult) return null;

      const { isValid, state, errors, warnings, metadata, processingEstimate } = validationResult;

      return (
        <div className={`${styles.validationStatus} ${styles[`status-${state.toLowerCase()}`]}`}>
          <div className={styles.statusIcon}>
            {state === 'VALID' && '✅'}
            {state === 'WARNING' && '⚠️'}
            {state === 'INVALID' && '❌'}
          </div>
          
          <div className={styles.statusContent}>
            <div className={styles.statusHeader}>
              <h4 className={styles.statusTitle}>
                {metadata?.name || 'Unknown file'}
              </h4>
              <span className={styles.fileSize}>
                {metadata?.sizeFormatted}
              </span>
            </div>

            <div className={styles.statusMessage}>
              {isValid ? (
                <span className={styles.successMessage}>
                  {VALIDATION_MESSAGES.GENERAL.VALID}
                </span>
              ) : (
                <span className={styles.errorMessage}>
                  {VALIDATION_MESSAGES.GENERAL.INVALID}
                </span>
              )}
            </div>

            {/* Processing estimate */}
            {showProcessingEstimate && processingEstimate && isValid && (
              <div className={styles.processingEstimate}>
                <span className={styles.estimateLabel}>Estimated processing time:</span>
                <span className={styles.estimateValue}>
                  {processingEstimate.estimatedTimeFormatted}
                </span>
                <span className={styles.estimateConfidence}>
                  (Confidence: {processingEstimate.confidence})
                </span>
              </div>
            )}
          </div>
        </div>
      );
    };

    /**
     * Render validation errors
     */
    const renderValidationErrors = () => {
      if (!validationResult || validationResult.errors.length === 0) return null;

      return (
        <div className={styles.errorsContainer}>
          <h5 className={styles.errorsTitle}>Issues Found</h5>
          {validationResult.errors.map((error, index) => (
            <div key={index} className={styles.errorItem}>
              <div className={styles.errorIcon}>❌</div>
              <div className={styles.errorContent}>
                <div className={styles.errorMessage}>{error.message}</div>
                {error.suggestion && (
                  <div className={styles.errorSuggestion}>
                    💡 {error.suggestion}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      );
    };

    /**
     * Render validation warnings
     */
    const renderValidationWarnings = () => {
      if (!validationResult || validationResult.warnings.length === 0) return null;

      return (
        <div className={styles.warningsContainer}>
          <h5 className={styles.warningsTitle}>Recommendations</h5>
          {validationResult.warnings.map((warning, index) => (
            <div key={index} className={styles.warningItem}>
              <div className={styles.warningIcon}>⚠️</div>
              <div className={styles.warningContent}>
                <div className={styles.warningMessage}>{warning.message}</div>
                {warning.suggestion && (
                  <div className={styles.warningSuggestion}>
                    💡 {warning.suggestion}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      );
    };

    /**
     * Render drag active state
     */
    const renderDragActiveState = () => {
      if (!isDragActive) return null;

      return (
        <div className={styles.dragActiveOverlay}>
          <div className={styles.dragActiveContent}>
            <div className={styles.dragActiveIcon}>📁</div>
            <div className={styles.dragActiveText}>
              Drop your video file here
            </div>
            <div className={styles.dragActiveSubtext}>
              Release to validate and upload
            </div>
          </div>
        </div>
      );
    };

    /**
     * Render system performance info
     */
    const renderSystemPerformance = () => {
      if (!systemPerformance || !validationResult?.processingEstimate) return null;

      return (
        <div className={styles.systemPerformance}>
          <span className={styles.performanceLabel}>System Performance:</span>
          <span className={styles.performanceValue}>
            {systemPerformance.level.toUpperCase()}
          </span>
          <span className={styles.performanceDetails}>
            ({systemPerformance.cpuCores} cores, {systemPerformance.memoryGB}GB RAM)
          </span>
        </div>
      );
    };

    // ============================================================================
    // Main render
    // ============================================================================

    return (
      <div className={`${styles.validationFeedback} ${className}`}>
        {renderDragActiveState()}
        
        <div className={styles.validationContent}>
          {renderConstraints()}
          {renderValidationStatus()}
          {renderValidationErrors()}
          {renderValidationWarnings()}
          {renderSystemPerformance()}
        </div>
      </div>
    );
  }
);

// Set display name for debugging
UploadValidationFeedback.displayName = 'UploadValidationFeedback';

export default UploadValidationFeedback;
