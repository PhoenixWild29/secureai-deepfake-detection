/**
 * Upload Constants
 * Configuration constants for file upload validation and processing
 */

// Supported video file types based on Core Detection Engine data models
export const SUPPORTED_VIDEO_TYPES = {
  'video/mp4': {
    extensions: ['.mp4'],
    codecs: ['avc1', 'avc3', 'hev1', 'hvc1'],
    description: 'MPEG-4 Video',
    maxSize: 500 * 1024 * 1024, // 500MB
    processingComplexity: 'medium'
  },
  'video/x-msvideo': {
    extensions: ['.avi'],
    codecs: ['divx', 'xvid', 'h264'],
    description: 'Audio Video Interleave',
    maxSize: 500 * 1024 * 1024, // 500MB
    processingComplexity: 'medium'
  },
  'video/quicktime': {
    extensions: ['.mov'],
    codecs: ['avc1', 'h264', 'hev1'],
    description: 'QuickTime Movie',
    maxSize: 500 * 1024 * 1024, // 500MB
    processingComplexity: 'medium'
  },
  'video/x-matroska': {
    extensions: ['.mkv'],
    codecs: ['avc1', 'h264', 'hev1'],
    description: 'Matroska Video',
    maxSize: 500 * 1024 * 1024, // 500MB
    processingComplexity: 'medium'
  },
  'video/webm': {
    extensions: ['.webm'],
    codecs: ['vp8', 'vp9', 'av1'],
    description: 'WebM Video',
    maxSize: 500 * 1024 * 1024, // 500MB
    processingComplexity: 'low'
  },
  'video/ogg': {
    extensions: ['.ogv'],
    codecs: ['theora'],
    description: 'Ogg Video',
    maxSize: 500 * 1024 * 1024, // 500MB
    processingComplexity: 'low'
  }
} as const;

// File size constraints
export const FILE_SIZE_CONSTRAINTS = {
  MIN_SIZE: 1024, // 1KB minimum
  MAX_SIZE: 500 * 1024 * 1024, // 500MB maximum
  WARNING_THRESHOLD: 100 * 1024 * 1024, // 100MB warning threshold
  RECOMMENDED_MAX: 200 * 1024 * 1024 // 200MB recommended maximum
} as const;

// Processing time estimation factors (seconds per MB)
export const PROCESSING_FACTORS = {
  // Base processing time per MB based on file complexity
  complexity: {
    low: 0.5,    // WebM, OGG
    medium: 0.8, // MP4, AVI, MOV, MKV
    high: 1.2    // High-resolution or complex codecs
  },
  // Additional factors
  resolution: {
    '480p': 0.5,
    '720p': 1.0,
    '1080p': 1.5,
    '4K': 2.5,
    '8K': 4.0
  },
  // System performance factors
  system: {
    fast: 0.8,    // High-end hardware
    medium: 1.0,  // Standard hardware
    slow: 1.5     // Lower-end hardware
  }
} as const;

// Validation error messages
export const VALIDATION_MESSAGES = {
  FILE_TYPE: {
    INVALID: 'File type not supported. Please select a supported video format.',
    UNKNOWN: 'Unable to determine file type. Please ensure the file has a valid video extension.',
    EMPTY: 'Please select a file to upload.'
  },
  FILE_SIZE: {
    TOO_SMALL: 'File is too small. Minimum size is 1KB.',
    TOO_LARGE: 'File exceeds maximum size limit of 500MB.',
    WARNING_LARGE: 'Large file detected. Upload and processing may take longer than usual.',
    RECOMMENDATION: 'For best performance, consider using files under 200MB.'
  },
  PROCESSING: {
    ESTIMATING: 'Calculating estimated processing time...',
    UNABLE_TO_ESTIMATE: 'Unable to estimate processing time for this file.',
    LONG_PROCESSING: 'This file may take a long time to process due to its size or complexity.'
  },
  GENERAL: {
    VALIDATING: 'Validating file...',
    VALID: 'File is valid and ready for upload.',
    INVALID: 'File validation failed. Please check the requirements and try again.',
    LOADING: 'Loading file information...'
  }
} as const;

// File constraint information for proactive display
export const FILE_CONSTRAINTS = {
  SUPPORTED_FORMATS: Object.values(SUPPORTED_VIDEO_TYPES).map(type => type.extensions).flat(),
  MAX_SIZE_FORMATTED: '500MB',
  MIN_SIZE_FORMATTED: '1KB',
  RECOMMENDED_SIZE_FORMATTED: '200MB',
  PROCESSING_TIME_RANGE: '1-30 minutes depending on file size and complexity'
} as const;

// Error severity levels
export const ERROR_SEVERITY = {
  INFO: 'info',
  WARNING: 'warning',
  ERROR: 'error',
  SUCCESS: 'success'
} as const;

// Validation states
export const VALIDATION_STATES = {
  IDLE: 'idle',
  VALIDATING: 'validating',
  VALID: 'valid',
  INVALID: 'invalid',
  WARNING: 'warning'
} as const;

// System performance detection
export const SYSTEM_PERFORMANCE = {
  // Simple heuristic based on available memory and CPU cores
  getPerformanceLevel: (): 'fast' | 'medium' | 'slow' => {
    if (typeof navigator !== 'undefined' && 'hardwareConcurrency' in navigator) {
      const cores = navigator.hardwareConcurrency || 4;
      const memory = (navigator as any).deviceMemory || 4; // GB
      
      if (cores >= 8 && memory >= 8) return 'fast';
      if (cores >= 4 && memory >= 4) return 'medium';
      return 'slow';
    }
    return 'medium'; // Default to medium if detection fails
  }
} as const;

// Type exports for TypeScript
export type SupportedVideoType = keyof typeof SUPPORTED_VIDEO_TYPES;
export type FileSizeConstraint = keyof typeof FILE_SIZE_CONSTRAINTS;
export type ProcessingComplexity = 'low' | 'medium' | 'high';
export type ErrorSeverity = keyof typeof ERROR_SEVERITY;
export type ValidationState = keyof typeof VALIDATION_STATES;
export type SystemPerformanceLevel = 'fast' | 'medium' | 'slow';
