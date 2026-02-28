/**
 * Upload Type Definitions
 * TypeScript interfaces and types for file upload validation
 */

import { 
  SupportedVideoType, 
  ProcessingComplexity, 
  ErrorSeverity, 
  ValidationState,
  SystemPerformanceLevel 
} from '../constants/uploadConstants';

// File metadata interface
export interface FileMetadata {
  name: string;
  size: number;
  type: string;
  lastModified: number;
  extension: string;
  sizeFormatted: string;
}

// Validation result interface
export interface ValidationResult {
  isValid: boolean;
  state: ValidationState;
  errors: ValidationError[];
  warnings: ValidationError[];
  metadata?: FileMetadata;
  processingEstimate?: ProcessingEstimate;
}

// Validation error interface
export interface ValidationError {
  code: string;
  message: string;
  severity: ErrorSeverity;
  field?: string;
  suggestion?: string;
}

// Processing time estimate interface
export interface ProcessingEstimate {
  estimatedTimeSeconds: number;
  estimatedTimeFormatted: string;
  complexity: ProcessingComplexity;
  factors: {
    fileSize: number;
    complexity: number;
    systemPerformance: number;
    resolution?: number;
  };
  confidence: 'low' | 'medium' | 'high';
}

// File constraint interface
export interface FileConstraint {
  type: 'size' | 'format' | 'duration' | 'resolution';
  value: string | number;
  unit?: string;
  description: string;
  isRequired: boolean;
}

// Upload validation feedback props
export interface UploadValidationFeedbackProps {
  file: File | null;
  isDragActive?: boolean;
  isUploading?: boolean;
  onValidationComplete?: (result: ValidationResult) => void;
  onError?: (error: ValidationError) => void;
  showConstraints?: boolean;
  showProcessingEstimate?: boolean;
  className?: string;
  options?: ValidationOptions;
}

// Validation options interface
export interface ValidationOptions {
  strictMode?: boolean;
  showWarnings?: boolean;
  maxFileSize?: number;
  allowedTypes?: SupportedVideoType[];
  systemPerformance?: SystemPerformanceLevel;
  customProcessingFactors?: Partial<ProcessingEstimate['factors']>;
}

// File type validation result
export interface FileTypeValidation {
  isValid: boolean;
  detectedType: SupportedVideoType | null;
  supportedExtensions: string[];
  codecSupport?: string[];
  description?: string;
}

// File size validation result
export interface FileSizeValidation {
  isValid: boolean;
  size: number;
  sizeFormatted: string;
  constraint: 'min' | 'max' | 'recommended' | 'warning';
  percentage?: number;
}

// Processing complexity assessment
export interface ProcessingComplexityAssessment {
  complexity: ProcessingComplexity;
  factors: {
    fileSize: number;
    codecComplexity: number;
    resolutionComplexity: number;
    containerComplexity: number;
  };
  score: number; // 0-100 scale
}

// System performance metrics
export interface SystemPerformanceMetrics {
  level: SystemPerformanceLevel;
  cpuCores: number;
  memoryGB: number;
  userAgent: string;
  estimatedCapability: number; // 0-100 scale
}

// Validation feedback state
export interface ValidationFeedbackState {
  result: ValidationResult | null;
  isProcessing: boolean;
  lastValidatedFile: File | null;
  constraints: FileConstraint[];
  systemPerformance: SystemPerformanceMetrics;
}

// Upload validation event types
export interface UploadValidationEvents {
  onFileSelected: (file: File) => void;
  onFileDropped: (file: File) => void;
  onValidationStart: (file: File) => void;
  onValidationComplete: (result: ValidationResult) => void;
  onValidationError: (error: Error) => void;
  onConstraintsUpdate: (constraints: FileConstraint[]) => void;
}

// Component ref interface for imperative access
export interface UploadValidationFeedbackRef {
  validateFile: (file: File) => Promise<ValidationResult>;
  clearValidation: () => void;
  getLastResult: () => ValidationResult | null;
  updateConstraints: (constraints: FileConstraint[]) => void;
}

// Utility type for validation callback
export type ValidationCallback = (result: ValidationResult) => void;

// Utility type for error callback
export type ValidationErrorCallback = (error: ValidationError) => void;

// Utility type for file constraint callback
export type FileConstraintCallback = (constraints: FileConstraint[]) => void;
