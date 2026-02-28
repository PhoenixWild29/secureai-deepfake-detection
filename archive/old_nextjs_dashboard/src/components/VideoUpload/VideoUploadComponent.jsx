/**
 * Video Upload Component
 * React component for video uploads with drag-and-drop functionality, preview generation, and progress tracking
 */

import React, { useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { useAuth } from '../../hooks/useAuth';
import { uploadViaAPI } from '../../services/s3UploadService';
import {
  validateVideoFile,
  generateVideoThumbnail,
  extractVideoMetadata,
  formatFileSize,
  formatDuration,
  formatTimeRemaining,
  isSupportedVideoFormat
} from '../../utils/videoProcessing';
import styles from './VideoUploadComponent.module.css';

/**
 * VideoUploadComponent - Main component for video uploads
 * @param {Object} props - Component props
 * @param {Function} props.onUploadComplete - Callback when upload completes
 * @param {Function} props.onUploadError - Callback when upload fails
 * @param {Function} props.onFileSelect - Callback when file is selected
 * @param {Object} props.options - Upload options
 * @returns {JSX.Element} Video upload component
 */
const VideoUploadComponent = ({
  onUploadComplete,
  onUploadError,
  onFileSelect,
  options = {}
}) => {
  // Authentication hook
  const { isAuthenticated, getToken, authenticatedRequest } = useAuth();

  // Component state
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [validation, setValidation] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [error, setError] = useState(null);

  // Refs
  const fileInputRef = useRef(null);
  const uploadStartTimeRef = useRef(null);

  /**
   * Handle file selection and validation
   * @param {File} file - Selected file
   */
  const handleFileSelect = useCallback(async (file) => {
    try {
      setError(null);
      setUploadResult(null);

      // Validate file
      const validationResult = validateVideoFile(file);
      setValidation(validationResult);

      if (!validationResult.isValid) {
        setError(validationResult.error);
        onUploadError?.(validationResult.error);
        return;
      }

      // Generate preview thumbnail
      let thumbnail = null;
      try {
        thumbnail = await generateVideoThumbnail(file, 1);
      } catch (thumbError) {
        console.warn('Failed to generate thumbnail:', thumbError);
        // Continue without thumbnail
      }

      // Extract metadata
      let fileMetadata = null;
      try {
        fileMetadata = await extractVideoMetadata(file);
      } catch (metaError) {
        console.warn('Failed to extract metadata:', metaError);
        // Use basic metadata
        fileMetadata = {
          name: file.name,
          size: file.size,
          format: file.type,
          duration: 0
        };
      }

      setSelectedFile(file);
      setPreview(thumbnail);
      setMetadata(fileMetadata);

      // Notify parent component
      onFileSelect?.(file, {
        validation: validationResult,
        preview: thumbnail,
        metadata: fileMetadata
      });

    } catch (error) {
      console.error('File selection error:', error);
      const errorMessage = 'Failed to process selected file';
      setError(errorMessage);
      onUploadError?.(errorMessage);
    }
  }, [onFileSelect, onUploadError]);

  /**
   * Handle file drop from drag-and-drop
   * @param {Array} acceptedFiles - Accepted files
   * @param {Array} rejectedFiles - Rejected files
   */
  const onDrop = useCallback((acceptedFiles, rejectedFiles) => {
    // Handle rejected files
    if (rejectedFiles.length > 0) {
      const rejection = rejectedFiles[0];
      let errorMessage = 'File was rejected';

      if (rejection.errors.length > 0) {
        const error = rejection.errors[0];
        if (error.code === 'file-too-large') {
          errorMessage = 'File is too large. Maximum size is 500MB.';
        } else if (error.code === 'file-invalid-type') {
          errorMessage = 'Unsupported file format. Please upload MP4, AVI, or MOV files.';
        } else {
          errorMessage = error.message;
        }
      }

      setError(errorMessage);
      onUploadError?.(errorMessage);
      return;
    }

    // Handle accepted files
    if (acceptedFiles.length > 0) {
      handleFileSelect(acceptedFiles[0]);
    }
  }, [handleFileSelect, onUploadError]);

  /**
   * Configure dropzone options
   */
  const dropzoneOptions = {
    onDrop,
    accept: {
      'video/mp4': ['.mp4'],
      'video/x-msvideo': ['.avi'],
      'video/quicktime': ['.mov']
    },
    maxSize: 500 * 1024 * 1024, // 500MB
    multiple: false,
    disabled: isUploading
  };

  // Initialize dropzone
  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone(dropzoneOptions);

  /**
   * Handle file input change
   * @param {Event} event - Input change event
   */
  const handleFileInputChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  /**
   * Remove selected file
   */
  const removeFile = () => {
    setSelectedFile(null);
    setPreview(null);
    setMetadata(null);
    setValidation(null);
    setUploadProgress(null);
    setUploadResult(null);
    setError(null);

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  /**
   * Start file upload
   */
  const startUpload = async () => {
    if (!selectedFile || !isAuthenticated) {
      setError('Please select a file and ensure you are authenticated');
      return;
    }

    try {
      setIsUploading(true);
      setUploadProgress(null);
      setUploadResult(null);
      setError(null);
      uploadStartTimeRef.current = Date.now();

      // Prepare upload options
      const uploadOptions = {
        userId: options.userId,
        metadata: {
          ...options.metadata,
          originalName: selectedFile.name,
          fileSize: selectedFile.size,
          uploadDate: new Date().toISOString()
        }
      };

      // Progress callback
      const onProgress = (progress) => {
        setUploadProgress(progress);
      };

      // Upload file
      const result = await uploadViaAPI(selectedFile, onProgress, uploadOptions);

      if (result.success) {
        setUploadResult(result);
        onUploadComplete?.(result, {
          file: selectedFile,
          preview,
          metadata,
          validation
        });
      } else {
        throw new Error(result.error || 'Upload failed');
      }

    } catch (error) {
      console.error('Upload error:', error);
      const errorMessage = error.message || 'Upload failed. Please try again.';
      setError(errorMessage);
      onUploadError?.(errorMessage);
    } finally {
      setIsUploading(false);
    }
  };

  /**
   * Cancel upload
   */
  const cancelUpload = () => {
    // Note: XMLHttpRequest abort would need to be implemented in the service
    setIsUploading(false);
    setUploadProgress(null);
    setError('Upload cancelled');
  };

  return (
    <div className={styles.videoUploadContainer}>
      {/* Upload Zone */}
      <div
        {...getRootProps()}
        className={`${styles.uploadZone} ${
          isDragActive ? styles.dragActive : ''
        } ${isDragReject ? styles.dragReject : ''}`}
      >
        <input
          {...getInputProps()}
          ref={fileInputRef}
          onChange={handleFileInputChange}
          className={styles.fileInput}
        />
        <div className={styles.uploadContent}>
          <div className={styles.uploadIcon}>
            {isDragActive ? '📁' : isDragReject ? '❌' : '📹'}
          </div>
          <h3 className={styles.uploadText}>
            {isDragActive
              ? 'Drop your video here'
              : isDragReject
              ? 'File type not supported'
              : 'Drag & drop your video here'}
          </h3>
          <p className={styles.uploadSubtext}>
            {isDragReject
              ? 'Please upload MP4, AVI, or MOV files only'
              : 'or click to browse files (max 500MB)'}
          </p>
        </div>
      </div>

      {/* File Preview */}
      {selectedFile && (
        <div className={styles.previewContainer}>
          <div className={styles.previewHeader}>
            <h4 className={styles.previewTitle}>Selected File</h4>
            <button
              type="button"
              className={styles.removeButton}
              onClick={removeFile}
              disabled={isUploading}
            >
              Remove
            </button>
          </div>

          <div className={styles.videoPreview}>
            {preview && (
              <img
                src={preview}
                alt="Video thumbnail"
                className={styles.thumbnail}
              />
            )}
            <div className={styles.videoInfo}>
              <h5 className={styles.videoName}>{metadata?.name || selectedFile.name}</h5>
              <div className={styles.videoMetadata}>
                <div className={styles.metadataItem}>
                  <span>📁</span>
                  <span>{formatFileSize(metadata?.size || selectedFile.size)}</span>
                </div>
                {metadata?.duration && (
                  <div className={styles.metadataItem}>
                    <span>⏱️</span>
                    <span>{formatDuration(metadata.duration)}</span>
                  </div>
                )}
                <div className={styles.metadataItem}>
                  <span>🎬</span>
                  <span>{metadata?.format || selectedFile.type}</span>
                </div>
                {metadata?.width && metadata?.height && (
                  <div className={styles.metadataItem}>
                    <span>📐</span>
                    <span>{metadata.width}×{metadata.height}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Upload Progress */}
          {uploadProgress && (
            <div className={styles.progressContainer}>
              <div className={styles.progressHeader}>
                <span className={styles.progressLabel}>Upload Progress</span>
                <span className={styles.progressPercentage}>
                  {uploadProgress.percentage}%
                </span>
              </div>
              <div className={styles.progressBar}>
                <div
                  className={styles.progressFill}
                  style={{ width: `${uploadProgress.percentage}%` }}
                />
              </div>
              <div className={styles.progressDetails}>
                <div className={styles.progressSpeed}>
                  <span>⚡</span>
                  <span>{formatFileSize(uploadProgress.speed || 0)}/s</span>
                </div>
                <div className={styles.progressTime}>
                  <span>⏱️</span>
                  <span>{formatTimeRemaining(uploadProgress.estimatedTime || 0)} remaining</span>
                </div>
              </div>
            </div>
          )}

          {/* Upload Buttons */}
          <div className={styles.buttonGroup}>
            <button
              type="button"
              className={styles.uploadButton}
              onClick={startUpload}
              disabled={isUploading || !validation?.isValid}
            >
              {isUploading ? (
                <>
                  <div className={styles.loadingSpinner} />
                  Uploading...
                </>
              ) : (
                'Upload Video'
              )}
            </button>
            {isUploading && (
              <button
                type="button"
                className={styles.cancelButton}
                onClick={cancelUpload}
              >
                Cancel Upload
              </button>
            )}
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className={styles.errorContainer}>
          <h5 className={styles.errorTitle}>Upload Error</h5>
          <p className={styles.errorMessage}>{error}</p>
        </div>
      )}

      {/* Success Display */}
      {uploadResult && (
        <div className={styles.successContainer}>
          <h5 className={styles.successTitle}>Upload Successful!</h5>
          <p className={styles.successMessage}>
            Your video has been uploaded successfully. Video ID: {uploadResult.video_id}
          </p>
        </div>
      )}

      {/* Authentication Warning */}
      {!isAuthenticated && (
        <div className={styles.errorContainer}>
          <h5 className={styles.errorTitle}>Authentication Required</h5>
          <p className={styles.errorMessage}>
            Please log in to upload videos.
          </p>
        </div>
      )}
    </div>
  );
};

export default VideoUploadComponent;
