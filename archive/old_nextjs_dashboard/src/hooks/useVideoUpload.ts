/**
 * useVideoUpload Hook
 * Custom React hook for handling video file selection, validation, preview generation, and S3 upload
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { S3UploadService } from '../services/s3UploadService';
import { 
  UploadState, 
  UploadProgress, 
  UploadResult, 
  ValidationResult, 
  UploadOptions,
  UseVideoUploadReturn,
  FileMetadata,
  FileValidationRules
} from '../types/hooks';
import { 
  createUploadError, 
  canRetryError, 
  incrementRetryCount,
  calculateRetryDelay,
  logError
} from '../utils/errorHandling';
import { StandardError } from '../types/hooks';

// ============================================================================
// Configuration
// ============================================================================

const DEFAULT_VALIDATION_RULES: FileValidationRules = {
  maxSize: 500 * 1024 * 1024, // 500MB
  minSize: 1024, // 1KB
  allowedTypes: ['video/mp4', 'video/avi', 'video/mov', 'video/mkv', 'video/webm'],
  allowedExtensions: ['mp4', 'avi', 'mov', 'mkv', 'webm']
};

const DEFAULT_UPLOAD_CONFIG = {
  s3Config: {
    bucket: 'secureai-deepfake-videos',
    region: 'us-east-1',
    usePresignedUrls: true
  },
  validationRules: DEFAULT_VALIDATION_RULES,
  retryConfig: {
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 30000,
    backoffMultiplier: 2
  }
};

// ============================================================================
// File Validation
// ============================================================================

/**
 * Validate file against rules
 */
function validateFile(file: File, rules: FileValidationRules): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  
  // Check file size
  if (file.size > rules.maxSize) {
    errors.push(`File size (${formatFileSize(file.size)}) exceeds maximum allowed size (${formatFileSize(rules.maxSize)})`);
  }
  
  if (rules.minSize && file.size < rules.minSize) {
    errors.push(`File size (${formatFileSize(file.size)}) is below minimum required size (${formatFileSize(rules.minSize)})`);
  }
  
  // Check file type
  if (!rules.allowedTypes.includes(file.type)) {
    errors.push(`File type '${file.type}' is not supported. Allowed types: ${rules.allowedTypes.join(', ')}`);
  }
  
  // Check file extension
  const extension = file.name.split('.').pop()?.toLowerCase();
  if (extension && !rules.allowedExtensions.includes(extension)) {
    errors.push(`File extension '.${extension}' is not supported. Allowed extensions: ${rules.allowedExtensions.join(', ')}`);
  }
  
  // Check file name
  if (!file.name || file.name.trim() === '') {
    errors.push('File name is required');
  }
  
  // Check for suspicious file names
  if (file.name.includes('..') || file.name.includes('/') || file.name.includes('\\')) {
    warnings.push('File name contains potentially unsafe characters');
  }
  
  // Check for very large files (warning)
  if (file.size > 100 * 1024 * 1024) { // 100MB
    warnings.push('Large file detected. Upload may take longer than usual.');
  }

  const fileInfo: FileMetadata = {
    name: file.name,
    size: file.size,
    type: file.type,
    lastModified: file.lastModified
  };

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    fileInfo
  };
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Format file size for display
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Format upload speed for display
 */
function formatUploadSpeed(bytesPerSecond: number): string {
  if (bytesPerSecond === 0) return '0 B/s';
  
  const k = 1024;
  const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
  const i = Math.floor(Math.log(bytesPerSecond) / Math.log(k));
  
  return parseFloat((bytesPerSecond / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Generate file preview (video thumbnail)
 */
async function generateVideoPreview(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    if (!ctx) {
      reject(new Error('Canvas context not available'));
      return;
    }
    
    video.addEventListener('loadedmetadata', () => {
      // Set canvas size to video dimensions
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      // Seek to 1 second or 10% of duration, whichever is smaller
      const seekTime = Math.min(1, video.duration * 0.1);
      video.currentTime = seekTime;
    });
    
    video.addEventListener('seeked', () => {
      try {
        // Draw video frame to canvas
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Convert to data URL
        const dataURL = canvas.toDataURL('image/jpeg', 0.8);
        resolve(dataURL);
      } catch (error) {
        reject(error);
      }
    });
    
    video.addEventListener('error', (event) => {
      reject(new Error('Failed to load video for preview generation'));
    });
    
    // Load the video
    video.src = URL.createObjectURL(file);
    video.load();
  });
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useVideoUpload(config = DEFAULT_UPLOAD_CONFIG): UseVideoUploadReturn {
  // ============================================================================
  // State Management
  // ============================================================================
  
  const [state, setState] = useState<UploadState>('idle');
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<StandardError | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  
  // Refs for managing upload operations
  const currentFile = useRef<File | null>(null);
  const uploadAbortController = useRef<AbortController | null>(null);
  const s3Service = useRef<S3UploadService | null>(null);
  const retryTimeoutRef = useRef<number | null>(null);
  
  // ============================================================================
  // S3 Service Initialization
  // ============================================================================
  
  useEffect(() => {
    s3Service.current = new S3UploadService(config.s3Config);
  }, [config.s3Config]);
  
  // ============================================================================
  // File Selection and Validation
  // ============================================================================
  
  const selectFile = useCallback(async (file: File): Promise<ValidationResult> => {
    try {
      setState('validating');
      setError(null);
      setValidation(null);
      setPreview(null);
      
      // Validate file
      const validationResult = validateFile(file, config.validationRules);
      setValidation(validationResult);
      
      if (validationResult.isValid) {
        currentFile.current = file;
        setState('idle');
        
        // Generate preview
        try {
          const previewDataURL = await generateVideoPreview(file);
          setPreview(previewDataURL);
        } catch (previewError) {
          console.warn('Failed to generate preview:', previewError);
          // Don't fail the file selection if preview generation fails
        }
      } else {
        setState('error');
        setError(createUploadError(
          new Error(`File validation failed: ${validationResult.errors.join(', ')}`),
          { fileInfo: validationResult.fileInfo, validationErrors: validationResult.errors }
        ));
      }
      
      return validationResult;
    } catch (error) {
      const uploadError = createUploadError(error as Error, { 
        operation: 'selectFile',
        fileName: file.name 
      });
      setError(uploadError);
      setState('error');
      logError(uploadError, { operation: 'selectFile' });
      throw uploadError;
    }
  }, [config.validationRules]);
  
  // ============================================================================
  // File Upload
  // ============================================================================
  
  const uploadFile = useCallback(async (options: UploadOptions = {}) => {
    if (!currentFile.current || !s3Service.current) {
      throw new Error('No file selected or S3 service not initialized');
    }
    
    try {
      setState('uploading');
      setError(null);
      setProgress(null);
      setResult(null);
      
      // Create abort controller for cancellation
      uploadAbortController.current = new AbortController();
      
      const file = currentFile.current;
      const uploadOptions = {
        ...options,
        metadata: {
          originalName: file.name,
          uploadDate: new Date().toISOString(),
          fileSize: file.size.toString(),
          ...options.metadata
        }
      };
      
      // Generate unique key if not provided
      const key = options.key || s3Service.current.generateUniqueKey(file, options.prefix);
      
      // Progress callback
      const onProgress = (progressInfo: any) => {
        setProgress({
          loaded: progressInfo.loaded,
          total: progressInfo.total,
          percentage: progressInfo.percentage,
          speed: progressInfo.speed,
          estimatedTime: progressInfo.estimatedTime,
          stage: progressInfo.percentage === 100 ? 'complete' : 'uploading',
          speedFormatted: formatUploadSpeed(progressInfo.speed),
          timeRemainingFormatted: s3Service.current?.formatTimeRemaining(progressInfo.estimatedTime) || 'Calculating...'
        });
      };
      
      // Upload file
      const uploadResult = await s3Service.current.upload(file, key, onProgress, uploadOptions);
      
      if (uploadResult.success) {
        const result: UploadResult = {
          success: true,
          key,
          url: `https://${config.s3Config.bucket}.s3.${config.s3Config.region}.amazonaws.com/${key}`,
          etag: uploadResult.etag,
          uploadTime: uploadResult.uploadTime || 0,
          metadata: {
            bucket: config.s3Config.bucket,
            region: config.s3Config.region,
            originalName: file.name,
            fileSize: file.size
          }
        };
        
        setResult(result);
        setState('completed');
        setProgress({
          loaded: file.size,
          total: file.size,
          percentage: 100,
          speed: 0,
          estimatedTime: 0,
          stage: 'complete',
          speedFormatted: '0 B/s',
          timeRemainingFormatted: 'Complete'
        });
      } else {
        throw new Error(uploadResult.error || 'Upload failed');
      }
      
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        // Upload was cancelled
        setState('idle');
        setProgress(null);
        return;
      }
      
      const uploadError = createUploadError(error as Error, { 
        operation: 'uploadFile',
        fileName: currentFile.current?.name,
        uploadOptions: options 
      });
      setError(uploadError);
      setState('error');
      logError(uploadError, { operation: 'uploadFile' });
      throw uploadError;
    }
  }, [config.s3Config]);
  
  // ============================================================================
  // Upload Management
  // ============================================================================
  
  const cancelUpload = useCallback(() => {
    if (uploadAbortController.current) {
      uploadAbortController.current.abort();
      uploadAbortController.current = null;
    }
    
    setState('idle');
    setProgress(null);
  }, []);
  
  const retryUpload = useCallback(async () => {
    if (!error || !canRetryError(error) || !currentFile.current) return;
    
    try {
      const retryDelay = calculateRetryDelay(
        error.retryCount,
        config.retryConfig.baseDelay,
        config.retryConfig.maxDelay,
        config.retryConfig.backoffMultiplier
      );
      
      // Wait before retry
      await new Promise(resolve => {
        retryTimeoutRef.current = setTimeout(resolve, retryDelay);
      });
      
      // Increment retry count
      const updatedError = incrementRetryCount(error);
      setError(updatedError);
      
      // Retry upload
      await uploadFile();
      
    } catch (error) {
      setError(error as StandardError);
      logError(error as StandardError, { operation: 'retryUpload' });
    }
  }, [error, uploadFile, config.retryConfig]);
  
  // ============================================================================
  // Utility Actions
  // ============================================================================
  
  const clearError = useCallback(() => {
    setError(null);
  }, []);
  
  const resetUpload = useCallback(() => {
    setState('idle');
    setProgress(null);
    setResult(null);
    setError(null);
    setValidation(null);
    setPreview(null);
    currentFile.current = null;
    
    // Cancel any ongoing upload
    if (uploadAbortController.current) {
      uploadAbortController.current.abort();
      uploadAbortController.current = null;
    }
  }, []);
  
  const generatePreview = useCallback(async (file: File): Promise<string> => {
    try {
      const previewDataURL = await generateVideoPreview(file);
      setPreview(previewDataURL);
      return previewDataURL;
    } catch (error) {
      console.error('Preview generation failed:', error);
      throw error;
    }
  }, []);
  
  // ============================================================================
  // Cleanup
  // ============================================================================
  
  useEffect(() => {
    return () => {
      if (uploadAbortController.current) {
        uploadAbortController.current.abort();
      }
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
      // Clean up preview URL
      if (preview && preview.startsWith('blob:')) {
        URL.revokeObjectURL(preview);
      }
    };
  }, [preview]);
  
  // ============================================================================
  // Return Hook Interface
  // ============================================================================
  
  return {
    // State
    state,
    progress,
    result,
    error,
    validation,
    preview,
    
    // Actions
    selectFile,
    uploadFile,
    cancelUpload,
    clearError,
    resetUpload,
    generatePreview,
    
    // Utility functions
    validateFile: (file: File) => validateFile(file, config.validationRules),
    formatFileSize,
    formatUploadSpeed
  };
}

// ============================================================================
// Hook Variants and Utilities
// ============================================================================

/**
 * Hook with custom configuration
 */
export function useVideoUploadWithConfig(
  customConfig: Partial<typeof DEFAULT_UPLOAD_CONFIG>
) {
  const config = { ...DEFAULT_UPLOAD_CONFIG, ...customConfig };
  return useVideoUpload(config);
}

/**
 * Hook with custom validation rules
 */
export function useVideoUploadWithValidation(
  validationRules: FileValidationRules,
  s3Config = DEFAULT_UPLOAD_CONFIG.s3Config
) {
  const config = {
    ...DEFAULT_UPLOAD_CONFIG,
    validationRules,
    s3Config
  };
  return useVideoUpload(config);
}

/**
 * Hook for drag and drop functionality
 */
export function useVideoUploadWithDragDrop(config = DEFAULT_UPLOAD_CONFIG) {
  const uploadHook = useVideoUpload(config);
  const [isDragOver, setIsDragOver] = useState(false);
  
  const handleDragOver = useCallback((event: DragEvent) => {
    event.preventDefault();
    setIsDragOver(true);
  }, []);
  
  const handleDragLeave = useCallback((event: DragEvent) => {
    event.preventDefault();
    setIsDragOver(false);
  }, []);
  
  const handleDrop = useCallback(async (event: DragEvent) => {
    event.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(event.dataTransfer?.files || []);
    if (files.length > 0) {
      const file = files[0];
      try {
        await uploadHook.selectFile(file);
      } catch (error) {
        console.error('Drag and drop upload failed:', error);
      }
    }
  }, [uploadHook]);
  
  return {
    ...uploadHook,
    isDragOver,
    handleDragOver,
    handleDragLeave,
    handleDrop
  };
}

export default useVideoUpload;
