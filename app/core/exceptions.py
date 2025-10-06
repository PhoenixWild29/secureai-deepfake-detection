#!/usr/bin/env python3
"""
Detection API Exception Classes
Custom exception classes for detection API specific error scenarios
"""

from typing import Optional, Dict, Any
from uuid import UUID


class DetectionAPIError(Exception):
    """
    Base exception class for detection API errors.
    Extends the existing APIError pattern for detection-specific scenarios.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: int = 500,
        analysis_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.status_code = status_code
        self.analysis_id = analysis_id
        self.details = details or {}


class AnalysisNotFoundError(DetectionAPIError):
    """
    Exception for when an analysis ID is not found.
    """
    
    def __init__(
        self,
        analysis_id: UUID,
        message: Optional[str] = None
    ):
        if message is None:
            message = f"Analysis with ID {analysis_id} not found"
        
        super().__init__(
            message=message,
            error_code="ANALYSIS_NOT_FOUND",
            status_code=404,
            analysis_id=analysis_id,
            details={'analysis_id': str(analysis_id)}
        )


class AnalysisProcessingError(DetectionAPIError):
    """
    Exception for errors during analysis processing.
    """
    
    def __init__(
        self,
        analysis_id: UUID,
        stage: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Processing error in stage '{stage}': {message}",
            error_code="ANALYSIS_PROCESSING_ERROR",
            status_code=500,
            analysis_id=analysis_id,
            details={
                'stage': stage,
                'analysis_id': str(analysis_id),
                **(details or {})
            }
        )


class AnalysisTimeoutError(DetectionAPIError):
    """
    Exception for analysis processing timeout.
    """
    
    def __init__(
        self,
        analysis_id: UUID,
        timeout_minutes: int,
        message: Optional[str] = None
    ):
        if message is None:
            message = f"Analysis processing timed out after {timeout_minutes} minutes"
        
        super().__init__(
            message=message,
            error_code="ANALYSIS_TIMEOUT",
            status_code=408,
            analysis_id=analysis_id,
            details={
                'timeout_minutes': timeout_minutes,
                'analysis_id': str(analysis_id)
            }
        )


class AnalysisCancelledError(DetectionAPIError):
    """
    Exception for cancelled analysis.
    """
    
    def __init__(
        self,
        analysis_id: UUID,
        reason: Optional[str] = None
    ):
        message = f"Analysis {analysis_id} was cancelled"
        if reason:
            message += f": {reason}"
        
        super().__init__(
            message=message,
            error_code="ANALYSIS_CANCELLED",
            status_code=410,
            analysis_id=analysis_id,
            details={
                'reason': reason,
                'analysis_id': str(analysis_id)
            }
        )


class VideoValidationError(DetectionAPIError):
    """
    Exception for video file validation errors.
    """
    
    def __init__(
        self,
        message: str,
        filename: Optional[str] = None,
        file_size: Optional[int] = None,
        content_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="VIDEO_VALIDATION_ERROR",
            status_code=400,
            details={
                'filename': filename,
                'file_size': file_size,
                'content_type': content_type,
                **(details or {})
            }
        )


class UnsupportedVideoFormatError(VideoValidationError):
    """
    Exception for unsupported video formats.
    """
    
    def __init__(
        self,
        content_type: str,
        filename: Optional[str] = None,
        allowed_formats: Optional[list] = None
    ):
        if allowed_formats is None:
            allowed_formats = ['mp4', 'avi', 'mov']
        
        message = f"Unsupported video format '{content_type}'"
        if filename:
            message += f" for file '{filename}'"
        message += f". Supported formats: {', '.join(allowed_formats)}"
        
        super().__init__(
            message=message,
            filename=filename,
            content_type=content_type,
            details={
                'allowed_formats': allowed_formats,
                'received_format': content_type
            }
        )


class VideoSizeExceededError(VideoValidationError):
    """
    Exception for video file size exceeded.
    """
    
    def __init__(
        self,
        file_size: int,
        max_size: int,
        filename: Optional[str] = None
    ):
        file_size_mb = file_size / (1024 * 1024)
        max_size_mb = max_size / (1024 * 1024)
        
        message = f"Video file size ({file_size_mb:.1f}MB) exceeds maximum allowed size ({max_size_mb:.1f}MB)"
        if filename:
            message += f" for file '{filename}'"
        
        super().__init__(
            message=message,
            filename=filename,
            file_size=file_size,
            details={
                'max_size': max_size,
                'received_size': file_size,
                'max_size_mb': max_size_mb,
                'received_size_mb': file_size_mb
            }
        )


class VideoQualityError(VideoValidationError):
    """
    Exception for video quality issues.
    """
    
    def __init__(
        self,
        message: str,
        filename: Optional[str] = None,
        quality_metrics: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            filename=filename,
            details={
                'quality_metrics': quality_metrics or {},
                **(details or {})
            }
        )


class DetectionMethodError(DetectionAPIError):
    """
    Exception for detection method errors.
    """
    
    def __init__(
        self,
        method: str,
        message: str,
        analysis_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Detection method '{method}' error: {message}",
            error_code="DETECTION_METHOD_ERROR",
            status_code=500,
            analysis_id=analysis_id,
            details={
                'method': method,
                'analysis_id': str(analysis_id) if analysis_id else None,
                **(details or {})
            }
        )


class ModelLoadingError(DetectionAPIError):
    """
    Exception for model loading errors.
    """
    
    def __init__(
        self,
        model_name: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Failed to load model '{model_name}': {message}",
            error_code="MODEL_LOADING_ERROR",
            status_code=500,
            details={
                'model_name': model_name,
                **(details or {})
            }
        )


class FrameProcessingError(DetectionAPIError):
    """
    Exception for frame processing errors.
    """
    
    def __init__(
        self,
        frame_number: int,
        message: str,
        analysis_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Frame {frame_number} processing error: {message}",
            error_code="FRAME_PROCESSING_ERROR",
            status_code=500,
            analysis_id=analysis_id,
            details={
                'frame_number': frame_number,
                'analysis_id': str(analysis_id) if analysis_id else None,
                **(details or {})
            }
        )


class BlockchainVerificationError(DetectionAPIError):
    """
    Exception for blockchain verification errors.
    """
    
    def __init__(
        self,
        analysis_id: UUID,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Blockchain verification failed: {message}",
            error_code="BLOCKCHAIN_VERIFICATION_ERROR",
            status_code=502,
            analysis_id=analysis_id,
            details={
                'analysis_id': str(analysis_id),
                **(details or {})
            }
        )


class ConcurrentAnalysisLimitError(DetectionAPIError):
    """
    Exception for exceeding concurrent analysis limit.
    """
    
    def __init__(
        self,
        current_count: int,
        max_count: int,
        message: Optional[str] = None
    ):
        if message is None:
            message = f"Concurrent analysis limit exceeded. Current: {current_count}, Max: {max_count}"
        
        super().__init__(
            message=message,
            error_code="CONCURRENT_LIMIT_EXCEEDED",
            status_code=429,
            details={
                'current_count': current_count,
                'max_count': max_count
            }
        )


class AnalysisQueueError(DetectionAPIError):
    """
    Exception for analysis queue errors.
    """
    
    def __init__(
        self,
        message: str,
        queue_status: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Analysis queue error: {message}",
            error_code="ANALYSIS_QUEUE_ERROR",
            status_code=503,
            details={
                'queue_status': queue_status,
                **(details or {})
            }
        )


class ResultGenerationError(DetectionAPIError):
    """
    Exception for result generation errors.
    """
    
    def __init__(
        self,
        analysis_id: UUID,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Result generation failed: {message}",
            error_code="RESULT_GENERATION_ERROR",
            status_code=500,
            analysis_id=analysis_id,
            details={
                'analysis_id': str(analysis_id),
                **(details or {})
            }
        )


# Utility functions for creating specific errors
def create_analysis_not_found_error(analysis_id: UUID) -> AnalysisNotFoundError:
    """
    Create an analysis not found error.
    
    Args:
        analysis_id: Analysis ID that was not found
        
    Returns:
        AnalysisNotFoundError instance
    """
    return AnalysisNotFoundError(analysis_id)


def create_video_validation_error(
    message: str,
    filename: Optional[str] = None,
    file_size: Optional[int] = None,
    content_type: Optional[str] = None
) -> VideoValidationError:
    """
    Create a video validation error.
    
    Args:
        message: Error message
        filename: Filename that failed validation
        file_size: File size
        content_type: Content type
        
    Returns:
        VideoValidationError instance
    """
    return VideoValidationError(
        message=message,
        filename=filename,
        file_size=file_size,
        content_type=content_type
    )


def create_processing_error(
    analysis_id: UUID,
    stage: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> AnalysisProcessingError:
    """
    Create an analysis processing error.
    
    Args:
        analysis_id: Analysis ID
        stage: Processing stage where error occurred
        message: Error message
        details: Additional error details
        
    Returns:
        AnalysisProcessingError instance
    """
    return AnalysisProcessingError(
        analysis_id=analysis_id,
        stage=stage,
        message=message,
        details=details
    )


def create_timeout_error(
    analysis_id: UUID,
    timeout_minutes: int
) -> AnalysisTimeoutError:
    """
    Create an analysis timeout error.
    
    Args:
        analysis_id: Analysis ID
        timeout_minutes: Timeout duration in minutes
        
    Returns:
        AnalysisTimeoutError instance
    """
    return AnalysisTimeoutError(
        analysis_id=analysis_id,
        timeout_minutes=timeout_minutes
    )


# Error mapping for HTTP status codes specific to detection
DETECTION_ERROR_STATUS_MAPPING = {
    400: VideoValidationError,
    404: AnalysisNotFoundError,
    408: AnalysisTimeoutError,
    410: AnalysisCancelledError,
    429: ConcurrentAnalysisLimitError,
    500: AnalysisProcessingError,
    502: BlockchainVerificationError,
    503: AnalysisQueueError
}


def create_detection_error_from_status_code(
    status_code: int,
    message: Optional[str] = None,
    analysis_id: Optional[UUID] = None,
    details: Optional[Dict[str, Any]] = None
) -> DetectionAPIError:
    """
    Create an appropriate detection error instance based on HTTP status code.
    
    Args:
        status_code: HTTP status code
        message: Error message
        analysis_id: Optional analysis ID
        details: Additional error details
        
    Returns:
        DetectionAPIError instance
    """
    error_class = DETECTION_ERROR_STATUS_MAPPING.get(status_code, DetectionAPIError)
    
    if message is None:
        message = f"Detection API error {status_code}"
    
    return error_class(
        message=message,
        analysis_id=analysis_id,
        details=details
    )


# Export all error classes and utility functions
__all__ = [
    'DetectionAPIError',
    'AnalysisNotFoundError',
    'AnalysisProcessingError',
    'AnalysisTimeoutError',
    'AnalysisCancelledError',
    'VideoValidationError',
    'UnsupportedVideoFormatError',
    'VideoSizeExceededError',
    'VideoQualityError',
    'DetectionMethodError',
    'ModelLoadingError',
    'FrameProcessingError',
    'BlockchainVerificationError',
    'ConcurrentAnalysisLimitError',
    'AnalysisQueueError',
    'ResultGenerationError',
    'create_analysis_not_found_error',
    'create_video_validation_error',
    'create_processing_error',
    'create_timeout_error',
    'create_detection_error_from_status_code'
]
