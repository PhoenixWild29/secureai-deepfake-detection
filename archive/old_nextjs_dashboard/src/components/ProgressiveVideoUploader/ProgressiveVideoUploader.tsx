/**
 * ProgressiveVideoUploader Component (TypeScript)
 * Enhanced video upload component with drag-and-drop support, chunked uploads, and real-time progress tracking
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { useVideoUpload } from '../../hooks/useVideoUpload';
import { EmbeddingCache } from '../../utils/EmbeddingCache';
import { formatFileSize, formatTimeRemaining, formatUploadSpeed } from '../../utils/videoProcessing';
import UploadValidationFeedback from '../UploadValidationFeedback/UploadValidationFeedback';
import styles from './ProgressiveVideoUploader.module.css';

// Type definitions
interface ProgressiveVideoUploaderProps {
  onUploadComplete?: (result: any) => void;
  onAnalysisStart?: (result: any) => void;
  onDuplicateDetected?: (result: any) => void;
  onError?: (error: Error) => void;
  options?: {
    chunkSize?: number;
    maxFileSize?: number;
    maxRetries?: number;
    allowedTypes?: string[];
    [key: string]: any;
  };
  autoTransition?: boolean;
  className?: string;
  showValidationFeedback?: boolean;
}

interface FileMetadata {
  name: string;
  size: number;
  type: string;
  lastModified: number;
  sizeFormatted: string;
  estimatedUploadTime: number;
}

interface DuplicateCheckResult {
  isDuplicate: boolean;
  hash: string | null;
  cachedResult: any;
  originalAnalysisId?: string;
  error?: Error;
}

/**
 * ProgressiveVideoUploader - Main component for progressive video uploads
 */
const ProgressiveVideoUploader: React.FC<ProgressiveVideoUploaderProps> = ({
  onUploadComplete,
  onAnalysisStart,
  onDuplicateDetected,
  onError,
  options = {},
  autoTransition = true,
  className = '',
  showValidationFeedback = true
}) => {
  // Upload state management
  const {
    uploadState,
    uploadProgress,
    uploadResult,
    error,
    retryCount,
    isRetrying,
    uploadFile,
    retryUpload,
    resetUpload,
    cancelUpload
  } = useVideoUpload(options);

  // Component state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileMetadata, setFileMetadata] = useState<FileMetadata | null>(null);
  const [duplicateCheck, setDuplicateCheck] = useState<DuplicateCheckResult | null>(null);
  const [uploadSession, setUploadSession] = useState<any>(null);
  const [dragActive, setDragActive] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  // Refs
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadStartTimeRef = useRef<number | null>(null);
  const progressIntervalRef = useRef<number | null>(null);

  // EmbeddingCache instance
  const embeddingCache = useRef(new EmbeddingCache());

  // ============================================================================
  // File Selection and Validation
  // ============================================================================

  /**
   * Handle file selection from dropzone or file input
   */
  const handleFileSelect = useCallback(async (acceptedFiles: File[], rejectedFiles: any[]) => {
    if (rejectedFiles && rejectedFiles.length > 0) {
      const rejection = rejectedFiles[0];
      const errorMessage = rejection.errors.map((e: any) => e.message).join(', ');
      onError?.(new Error(`File rejected: ${errorMessage}`));
      return;
    }

    if (acceptedFiles && acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      await processSelectedFile(file);
    }
  }, [onError]);

  /**
   * Process selected file - validation, metadata extraction, and duplicate check
   */
  const processSelectedFile = useCallback(async (file: File) => {
    try {
      setSelectedFile(file);
      
      // Extract file metadata
      const metadata = await extractFileMetadata(file);
      setFileMetadata(metadata);

      // Check for duplicates using EmbeddingCache
      const duplicateResult = await checkForDuplicate(file);
      setDuplicateCheck(duplicateResult);

      if (duplicateResult.isDuplicate) {
        onDuplicateDetected?.(duplicateResult);
        return;
      }

      // Show preview
      setShowPreview(true);
      
    } catch (error) {
      console.error('Error processing selected file:', error);
      onError?.(error as Error);
    }
  }, [onDuplicateDetected, onError]);

  /**
   * Extract file metadata
   */
  const extractFileMetadata = useCallback(async (file: File): Promise<FileMetadata> => {
    return {
      name: file.name,
      size: file.size,
      type: file.type,
      lastModified: file.lastModified,
      sizeFormatted: formatFileSize(file.size),
      estimatedUploadTime: estimateUploadTime(file.size)
    };
  }, []);

  /**
   * Check for duplicate using EmbeddingCache
   */
  const checkForDuplicate = useCallback(async (file: File): Promise<DuplicateCheckResult> => {
    try {
      const fileHash = await embeddingCache.current.generateFileHash(file);
      const duplicateResult = await embeddingCache.current.checkDuplicate(fileHash);
      
      return {
        isDuplicate: duplicateResult.found,
        hash: fileHash,
        cachedResult: duplicateResult.result,
        originalAnalysisId: duplicateResult.analysisId
      };
    } catch (error) {
      console.warn('Duplicate check failed:', error);
      return { isDuplicate: false, hash: null, error: error as Error };
    }
  }, []);

  /**
   * Estimate upload time based on file size
   */
  const estimateUploadTime = useCallback((fileSize: number): number => {
    // Assume average upload speed of 10 Mbps
    const avgSpeedMbps = 10;
    const avgSpeedBytesPerSecond = (avgSpeedMbps * 1024 * 1024) / 8;
    const estimatedSeconds = fileSize / avgSpeedBytesPerSecond;
    return Math.max(estimatedSeconds, 5); // Minimum 5 seconds
  }, []);

  // ============================================================================
  // Upload Management
  // ============================================================================

  /**
   * Start upload process
   */
  const startUpload = useCallback(async () => {
    if (!selectedFile) return;

    try {
      uploadStartTimeRef.current = Date.now();
      
      // Start progress tracking
      startProgressTracking();

      // Initiate upload
      const result = await uploadFile(selectedFile, {
        ...options,
        chunkSize: options.chunkSize || 10 * 1024 * 1024, // 10MB chunks
        enableProgress: true,
        onProgress: handleUploadProgress
      });

      if (result.success) {
        handleUploadComplete(result);
      }
      
    } catch (error) {
      console.error('Upload failed:', error);
      onError?.(error as Error);
    }
  }, [selectedFile, options, uploadFile, onError]);

  /**
   * Handle upload progress updates
   */
  const handleUploadProgress = useCallback((progress: any) => {
    const elapsed = Date.now() - (uploadStartTimeRef.current || 0);
    const uploadSpeed = progress.bytesUploaded / (elapsed / 1000);
    const remainingBytes = progress.totalBytes - progress.bytesUploaded;
    const estimatedTimeRemaining = remainingBytes / uploadSpeed;

    const enhancedProgress = {
      ...progress,
      uploadSpeed: uploadSpeed,
      uploadSpeedFormatted: formatUploadSpeed(uploadSpeed),
      estimatedTimeRemaining: estimatedTimeRemaining,
      estimatedTimeRemainingFormatted: formatTimeRemaining(estimatedTimeRemaining),
      elapsedTime: elapsed / 1000,
      elapsedTimeFormatted: formatTimeRemaining(elapsed / 1000)
    };

    // Update upload session if available
    if (uploadSession) {
      setUploadSession((prev: any) => ({
        ...prev,
        progress: enhancedProgress
      }));
    }
  }, [uploadSession]);

  /**
   * Handle upload completion
   */
  const handleUploadComplete = useCallback((result: any) => {
    setUploadResult(result);
    onUploadComplete?.(result);

    if (autoTransition && result.analysisId) {
      // Auto-transition to analysis tracker
      onAnalysisStart?.(result);
    }
  }, [onUploadComplete, onAnalysisStart, autoTransition]);

  /**
   * Start progress tracking interval
   */
  const startProgressTracking = useCallback(() => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
    }

    progressIntervalRef.current = window.setInterval(() => {
      // Update progress display
      if (uploadProgress && uploadStartTimeRef.current) {
        const elapsed = Date.now() - uploadStartTimeRef.current;
        const speed = uploadProgress.bytesUploaded / (elapsed / 1000);
        
        // Update speed and time estimates
        handleUploadProgress({
          ...uploadProgress,
          uploadSpeed: speed
        });
      }
    }, 1000);
  }, [uploadProgress, handleUploadProgress]);

  /**
   * Stop progress tracking
   */
  const stopProgressTracking = useCallback(() => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
  }, []);

  // ============================================================================
  // Dropzone Configuration
  // ============================================================================

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop: handleFileSelect,
    onDragEnter: () => setDragActive(true),
    onDragLeave: () => setDragActive(false),
    accept: {
      'video/*': ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.ogg']
    },
    maxFiles: 1,
    maxSize: options.maxFileSize || 500 * 1024 * 1024, // 500MB
    disabled: uploadState === 'uploading' || uploadState === 'processing'
  });

  // ============================================================================
  // Event Handlers
  // ============================================================================

  /**
   * Handle retry upload
   */
  const handleRetry = useCallback(() => {
    retryUpload();
  }, [retryUpload]);

  /**
   * Handle cancel upload
   */
  const handleCancel = useCallback(() => {
    cancelUpload();
    stopProgressTracking();
    resetUpload();
    setSelectedFile(null);
    setFileMetadata(null);
    setShowPreview(false);
  }, [cancelUpload, resetUpload, stopProgressTracking]);

  /**
   * Handle reset component
   */
  const handleReset = useCallback(() => {
    resetUpload();
    setSelectedFile(null);
    setFileMetadata(null);
    setDuplicateCheck(null);
    setUploadSession(null);
    setShowPreview(false);
    stopProgressTracking();
  }, [resetUpload, stopProgressTracking]);

  // ============================================================================
  // Effects
  // ============================================================================

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopProgressTracking();
    };
  }, [stopProgressTracking]);

  // Update drag state
  useEffect(() => {
    setDragActive(isDragActive);
  }, [isDragActive]);

  // ============================================================================
  // Render Helpers
  // ============================================================================

  /**
   * Render drag and drop area
   */
  const renderDropZone = () => (
    <div
      {...getRootProps()}
      className={`${styles.dropZone} ${
        dragActive ? styles.dropZoneActive : ''
      } ${
        isDragReject ? styles.dropZoneReject : ''
      } ${
        uploadState === 'uploading' ? styles.dropZoneDisabled : ''
      }`}
    >
      <input {...getInputProps()} ref={fileInputRef} />
      
      <div className={styles.dropZoneContent}>
        <div className={styles.dropZoneIcon}>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7,10 12,15 17,10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
        </div>
        
        <div className={styles.dropZoneText}>
          <h3>Drop your video here</h3>
          <p>or click to browse files</p>
          <p className={styles.dropZoneSubtext}>
            Supports MP4, AVI, MOV, MKV, WebM, OGG (max 500MB)
          </p>
        </div>
      </div>
    </div>
  );

  /**
   * Render file preview
   */
  const renderFilePreview = () => {
    if (!selectedFile || !fileMetadata) return null;

    return (
      <div className={styles.filePreview}>
        <div className={styles.fileInfo}>
          <h4>{fileMetadata.name}</h4>
          <p>{fileMetadata.sizeFormatted}</p>
          <p>Estimated upload time: {formatTimeRemaining(fileMetadata.estimatedUploadTime)}</p>
        </div>
        
        <div className={styles.fileActions}>
          <button 
            className={styles.uploadButton}
            onClick={startUpload}
            disabled={uploadState === 'uploading'}
          >
            Start Upload
          </button>
          <button 
            className={styles.cancelButton}
            onClick={handleReset}
            disabled={uploadState === 'uploading'}
          >
            Cancel
          </button>
        </div>
      </div>
    );
  };

  /**
   * Render upload progress
   */
  const renderUploadProgress = () => {
    if (!uploadProgress || uploadState !== 'uploading') return null;

    return (
      <div className={styles.uploadProgress}>
        <div className={styles.progressHeader}>
          <h4>Uploading {fileMetadata?.name}</h4>
          <span className={styles.progressPercentage}>
            {Math.round(uploadProgress.percentage)}%
          </span>
        </div>
        
        <div className={styles.progressBar}>
          <div 
            className={styles.progressFill}
            style={{ width: `${uploadProgress.percentage}%` }}
          />
        </div>
        
        <div className={styles.progressDetails}>
          <span>{uploadProgress.bytesUploadedFormatted} / {uploadProgress.totalBytesFormatted}</span>
          <span>{uploadProgress.uploadSpeedFormatted}</span>
          <span>{uploadProgress.estimatedTimeRemainingFormatted} remaining</span>
        </div>
        
        <button 
          className={styles.cancelButton}
          onClick={handleCancel}
        >
          Cancel Upload
        </button>
      </div>
    );
  };

  /**
   * Render duplicate detection result
   */
  const renderDuplicateResult = () => {
    if (!duplicateCheck?.isDuplicate) return null;

    return (
      <div className={styles.duplicateResult}>
        <div className={styles.duplicateIcon}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="20,6 9,17 4,12" />
          </svg>
        </div>
        <div className={styles.duplicateContent}>
          <h4>Analysis Complete</h4>
          <p>This video has already been analyzed.</p>
          <button 
            className={styles.viewResultsButton}
            onClick={() => onDuplicateDetected?.(duplicateCheck)}
          >
            View Results
          </button>
        </div>
      </div>
    );
  };

  /**
   * Render error state
   */
  const renderError = () => {
    if (!error) return null;

    return (
      <div className={styles.errorContainer}>
        <div className={styles.errorIcon}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="15" y1="9" x2="9" y2="15" />
            <line x1="9" y1="9" x2="15" y2="15" />
          </svg>
        </div>
        <div className={styles.errorContent}>
          <h4>Upload Failed</h4>
          <p>{error.message}</p>
          {retryCount < (options.maxRetries || 3) && (
            <button 
              className={styles.retryButton}
              onClick={handleRetry}
              disabled={isRetrying}
            >
              {isRetrying ? 'Retrying...' : 'Retry Upload'}
            </button>
          )}
        </div>
      </div>
    );
  };

  // ============================================================================
  // Main Render
  // ============================================================================

  return (
    <div className={`${styles.progressiveUploader} ${className}`}>
      {/* Validation Feedback Component */}
      {showValidationFeedback && (
        <UploadValidationFeedback
          file={selectedFile}
          isDragActive={dragActive}
          isUploading={uploadState === 'uploading'}
          onValidationComplete={(result) => {
            // Handle validation completion if needed
            console.log('Validation completed:', result);
          }}
          onError={(validationError) => {
            // Handle validation errors
            onError?.(new Error(validationError.message));
          }}
          showConstraints={!selectedFile}
          showProcessingEstimate={true}
          options={{
            maxFileSize: options.maxFileSize,
            allowedTypes: options.allowedTypes,
            strictMode: true
          }}
        />
      )}

      {!selectedFile && renderDropZone()}
      
      {selectedFile && !duplicateCheck?.isDuplicate && !showPreview && (
        <div className={styles.processing}>
          <div className={styles.spinner} />
          <p>Processing file...</p>
        </div>
      )}
      
      {duplicateCheck?.isDuplicate && renderDuplicateResult()}
      
      {showPreview && !duplicateCheck?.isDuplicate && renderFilePreview()}
      
      {uploadState === 'uploading' && renderUploadProgress()}
      
      {error && renderError()}
      
      {uploadResult && uploadState === 'completed' && (
        <div className={styles.uploadComplete}>
          <div className={styles.successIcon}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="20,6 9,17 4,12" />
            </svg>
          </div>
          <h4>Upload Complete!</h4>
          <p>Analysis has started. You will be notified when complete.</p>
        </div>
      )}
    </div>
  );
};

export default ProgressiveVideoUploader;
