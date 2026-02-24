/**
 * Upload Validation Utilities
 * Client-side validation functions for file uploads
 */

import {
  SUPPORTED_VIDEO_TYPES,
  FILE_SIZE_CONSTRAINTS,
  PROCESSING_FACTORS,
  VALIDATION_MESSAGES,
  SYSTEM_PERFORMANCE,
  SupportedVideoType,
  ProcessingComplexity,
  ErrorSeverity,
  ValidationState
} from '../constants/uploadConstants';

import {
  ValidationResult,
  ValidationError,
  ProcessingEstimate,
  FileMetadata,
  FileTypeValidation,
  FileSizeValidation,
  ProcessingComplexityAssessment,
  SystemPerformanceMetrics,
  ValidationOptions
} from '../types/upload';

// ============================================================================
// File Type Validation
// ============================================================================

/**
 * Validate file type against supported video formats
 */
export function validateFileType(file: File): FileTypeValidation {
  const extension = getFileExtension(file.name);
  const mimeType = file.type;
  
  // Check MIME type first
  if (mimeType && mimeType in SUPPORTED_VIDEO_TYPES) {
    const typeInfo = SUPPORTED_VIDEO_TYPES[mimeType as SupportedVideoType];
    return {
      isValid: true,
      detectedType: mimeType as SupportedVideoType,
      supportedExtensions: typeInfo.extensions,
      codecSupport: typeInfo.codecs,
      description: typeInfo.description
    };
  }
  
  // Fallback to extension checking
  for (const [mimeType, typeInfo] of Object.entries(SUPPORTED_VIDEO_TYPES)) {
    if (typeInfo.extensions.includes(extension)) {
      return {
        isValid: true,
        detectedType: mimeType as SupportedVideoType,
        supportedExtensions: typeInfo.extensions,
        codecSupport: typeInfo.codecs,
        description: typeInfo.description
      };
    }
  }
  
  // No match found
  return {
    isValid: false,
    detectedType: null,
    supportedExtensions: Object.values(SUPPORTED_VIDEO_TYPES)
      .map(type => type.extensions)
      .flat()
  };
}

/**
 * Get file extension from filename
 */
export function getFileExtension(filename: string): string {
  const parts = filename.split('.');
  return parts.length > 1 ? `.${parts[parts.length - 1].toLowerCase()}` : '';
}

// ============================================================================
// File Size Validation
// ============================================================================

/**
 * Validate file size against constraints
 */
export function validateFileSize(file: File): FileSizeValidation {
  const size = file.size;
  const sizeFormatted = formatFileSize(size);
  
  // Check minimum size
  if (size < FILE_SIZE_CONSTRAINTS.MIN_SIZE) {
    return {
      isValid: false,
      size,
      sizeFormatted,
      constraint: 'min'
    };
  }
  
  // Check maximum size
  if (size > FILE_SIZE_CONSTRAINTS.MAX_SIZE) {
    return {
      isValid: false,
      size,
      sizeFormatted,
      constraint: 'max'
    };
  }
  
  // Check warning threshold
  if (size > FILE_SIZE_CONSTRAINTS.WARNING_THRESHOLD) {
    return {
      isValid: true,
      size,
      sizeFormatted,
      constraint: 'warning',
      percentage: (size / FILE_SIZE_CONSTRAINTS.MAX_SIZE) * 100
    };
  }
  
  // Check recommended size
  if (size > FILE_SIZE_CONSTRAINTS.RECOMMENDED_MAX) {
    return {
      isValid: true,
      size,
      sizeFormatted,
      constraint: 'recommended',
      percentage: (size / FILE_SIZE_CONSTRAINTS.MAX_SIZE) * 100
    };
  }
  
  // File size is optimal
  return {
    isValid: true,
    size,
    sizeFormatted,
    constraint: 'min'
  };
}

/**
 * Format file size in human-readable format
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const k = 1024;
  const decimalPlaces = 1;
  
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const size = parseFloat((bytes / Math.pow(k, i)).toFixed(decimalPlaces));
  
  return `${size} ${units[i]}`;
}

// ============================================================================
// Processing Time Estimation
// ============================================================================

/**
 * Estimate processing time for a file
 */
export function estimateProcessingTime(
  file: File,
  fileTypeValidation: FileTypeValidation,
  options: ValidationOptions = {}
): ProcessingEstimate {
  const sizeMB = file.size / (1024 * 1024);
  const systemPerformance = options.systemPerformance || SYSTEM_PERFORMANCE.getPerformanceLevel();
  
  // Get complexity factor
  const complexity = fileTypeValidation.detectedType 
    ? SUPPORTED_VIDEO_TYPES[fileTypeValidation.detectedType].processingComplexity
    : 'medium';
  
  const complexityFactor = PROCESSING_FACTORS.complexity[complexity];
  const systemFactor = PROCESSING_FACTORS.system[systemPerformance];
  
  // Calculate base processing time
  let baseTimeSeconds = sizeMB * complexityFactor * systemFactor;
  
  // Apply custom factors if provided
  if (options.customProcessingFactors) {
    const customFactors = options.customProcessingFactors;
    if (customFactors.complexity) baseTimeSeconds *= customFactors.complexity;
    if (customFactors.systemPerformance) baseTimeSeconds *= customFactors.systemPerformance;
  }
  
  // Add minimum processing time
  baseTimeSeconds = Math.max(baseTimeSeconds, 5); // Minimum 5 seconds
  
  // Calculate confidence based on available information
  let confidence: 'low' | 'medium' | 'high' = 'low';
  if (fileTypeValidation.detectedType && fileTypeValidation.isValid) {
    confidence = 'medium';
  }
  if (fileTypeValidation.codecSupport && fileTypeValidation.codecSupport.length > 0) {
    confidence = 'high';
  }
  
  return {
    estimatedTimeSeconds: Math.round(baseTimeSeconds),
    estimatedTimeFormatted: formatTimeRemaining(baseTimeSeconds),
    complexity,
    factors: {
      fileSize: sizeMB,
      complexity: complexityFactor,
      systemPerformance: systemFactor,
      resolution: 1.0 // Default, could be enhanced with actual resolution detection
    },
    confidence
  };
}

/**
 * Format time remaining in human-readable format
 */
export function formatTimeRemaining(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)} seconds`;
  } else if (seconds < 3600) {
    const minutes = Math.round(seconds / 60);
    return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.round((seconds % 3600) / 60);
    return `${hours} hour${hours !== 1 ? 's' : ''}${minutes > 0 ? ` ${minutes} minute${minutes !== 1 ? 's' : ''}` : ''}`;
  }
}

// ============================================================================
// Processing Complexity Assessment
// ============================================================================

/**
 * Assess processing complexity of a file
 */
export function assessProcessingComplexity(
  file: File,
  fileTypeValidation: FileTypeValidation
): ProcessingComplexityAssessment {
  const sizeMB = file.size / (1024 * 1024);
  
  // File size complexity (0-40 points)
  const fileSizeComplexity = Math.min(sizeMB / 5, 40); // 5MB = 1 point, max 40
  
  // Codec complexity (0-30 points)
  let codecComplexity = 15; // Default medium
  if (fileTypeValidation.codecSupport) {
    const codecs = fileTypeValidation.codecSupport;
    if (codecs.includes('h264') || codecs.includes('avc1')) codecComplexity = 10; // Low
    if (codecs.includes('hev1') || codecs.includes('hvc1')) codecComplexity = 25; // High
    if (codecs.includes('vp9') || codecs.includes('av1')) codecComplexity = 30; // Very High
  }
  
  // Resolution complexity (0-20 points) - estimated based on file size
  const estimatedResolutionComplexity = Math.min(sizeMB / 10, 20); // Rough estimate
  
  // Container complexity (0-10 points)
  let containerComplexity = 5; // Default
  if (fileTypeValidation.detectedType) {
    const type = fileTypeValidation.detectedType;
    if (type.includes('webm') || type.includes('ogg')) containerComplexity = 3; // Low
    if (type.includes('mkv') || type.includes('avi')) containerComplexity = 8; // High
  }
  
  const totalScore = fileSizeComplexity + codecComplexity + estimatedResolutionComplexity + containerComplexity;
  
  let complexity: ProcessingComplexity;
  if (totalScore < 30) complexity = 'low';
  else if (totalScore < 70) complexity = 'medium';
  else complexity = 'high';
  
  return {
    complexity,
    factors: {
      fileSize: fileSizeComplexity,
      codecComplexity,
      resolutionComplexity: estimatedResolutionComplexity,
      containerComplexity
    },
    score: Math.min(totalScore, 100)
  };
}

// ============================================================================
// System Performance Detection
// ============================================================================

/**
 * Get system performance metrics
 */
export function getSystemPerformanceMetrics(): SystemPerformanceMetrics {
  const level = SYSTEM_PERFORMANCE.getPerformanceLevel();
  const cpuCores = navigator.hardwareConcurrency || 4;
  const memoryGB = (navigator as any).deviceMemory || 4;
  const userAgent = navigator.userAgent;
  
  // Calculate estimated capability (0-100)
  let estimatedCapability = 50; // Base
  estimatedCapability += Math.min(cpuCores * 5, 30); // CPU contribution
  estimatedCapability += Math.min(memoryGB * 3, 20); // Memory contribution
  
  if (level === 'fast') estimatedCapability += 10;
  else if (level === 'slow') estimatedCapability -= 10;
  
  estimatedCapability = Math.max(0, Math.min(100, estimatedCapability));
  
  return {
    level,
    cpuCores,
    memoryGB,
    userAgent,
    estimatedCapability
  };
}

// ============================================================================
// Main Validation Function
// ============================================================================

/**
 * Perform comprehensive file validation
 */
export async function validateFile(file: File, options: ValidationOptions = {}): Promise<ValidationResult> {
  const errors: ValidationError[] = [];
  const warnings: ValidationError[] = [];
  
  // Extract file metadata
  const metadata: FileMetadata = {
    name: file.name,
    size: file.size,
    type: file.type,
    lastModified: file.lastModified,
    extension: getFileExtension(file.name),
    sizeFormatted: formatFileSize(file.size)
  };
  
  // Validate file type
  const fileTypeValidation = validateFileType(file);
  if (!fileTypeValidation.isValid) {
    errors.push({
      code: 'INVALID_FILE_TYPE',
      message: VALIDATION_MESSAGES.FILE_TYPE.INVALID,
      severity: 'ERROR',
      field: 'type',
      suggestion: `Supported formats: ${fileTypeValidation.supportedExtensions.join(', ')}`
    });
  }
  
  // Validate file size
  const fileSizeValidation = validateFileSize(file);
  if (!fileSizeValidation.isValid) {
    const constraint = fileSizeValidation.constraint;
    if (constraint === 'min') {
      errors.push({
        code: 'FILE_TOO_SMALL',
        message: VALIDATION_MESSAGES.FILE_SIZE.TOO_SMALL,
        severity: 'ERROR',
        field: 'size'
      });
    } else if (constraint === 'max') {
      errors.push({
        code: 'FILE_TOO_LARGE',
        message: VALIDATION_MESSAGES.FILE_SIZE.TOO_LARGE,
        severity: 'ERROR',
        field: 'size',
        suggestion: 'Consider compressing the file or using a different format.'
      });
    }
  } else if (fileSizeValidation.constraint === 'warning') {
    warnings.push({
      code: 'LARGE_FILE_WARNING',
      message: VALIDATION_MESSAGES.FILE_SIZE.WARNING_LARGE,
      severity: 'WARNING',
      field: 'size'
    });
  } else if (fileSizeValidation.constraint === 'recommended') {
    warnings.push({
      code: 'RECOMMENDED_SIZE',
      message: VALIDATION_MESSAGES.FILE_SIZE.RECOMMENDATION,
      severity: 'WARNING',
      field: 'size'
    });
  }
  
  // Estimate processing time if file is valid
  let processingEstimate: ProcessingEstimate | undefined;
  if (fileTypeValidation.isValid && fileSizeValidation.isValid) {
    try {
      processingEstimate = estimateProcessingTime(file, fileTypeValidation, options);
    } catch (error) {
      warnings.push({
        code: 'PROCESSING_ESTIMATE_ERROR',
        message: VALIDATION_MESSAGES.PROCESSING.UNABLE_TO_ESTIMATE,
        severity: 'WARNING',
        field: 'processing'
      });
    }
  }
  
  // Determine overall validation state
  let state: ValidationState;
  if (errors.length > 0) {
    state = 'INVALID';
  } else if (warnings.length > 0) {
    state = 'WARNING';
  } else {
    state = 'VALID';
  }
  
  const isValid = errors.length === 0;
  
  return {
    isValid,
    state,
    errors,
    warnings,
    metadata,
    processingEstimate
  };
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Create a validation error
 */
export function createValidationError(
  code: string,
  message: string,
  severity: ErrorSeverity,
  field?: string,
  suggestion?: string
): ValidationError {
  return {
    code,
    message,
    severity,
    field,
    suggestion
  };
}

/**
 * Check if file has valid video extension
 */
export function hasValidVideoExtension(filename: string): boolean {
  const extension = getFileExtension(filename);
  const validExtensions = Object.values(SUPPORTED_VIDEO_TYPES)
    .map(type => type.extensions)
    .flat();
  
  return validExtensions.includes(extension);
}

/**
 * Get file type information from MIME type or extension
 */
export function getFileTypeInfo(file: File): { type: SupportedVideoType | null; description: string } {
  const validation = validateFileType(file);
  
  if (validation.detectedType) {
    const typeInfo = SUPPORTED_VIDEO_TYPES[validation.detectedType];
    return {
      type: validation.detectedType,
      description: typeInfo.description
    };
  }
  
  return {
    type: null,
    description: 'Unknown file type'
  };
}
