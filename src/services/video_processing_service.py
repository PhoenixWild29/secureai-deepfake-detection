#!/usr/bin/env python3
"""
Video Processing Service
Service for video file validation, metadata extraction, and content analysis
"""

import os
import hashlib
import logging
import subprocess
import tempfile
from typing import Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timezone

from src.schemas.video_upload_schema import (
    VideoValidationResult,
    VideoFormat,
    VideoUploadConfig,
    VideoUploadErrorCodes
)

logger = logging.getLogger(__name__)


class VideoProcessingService:
    """
    Service for video file processing, validation, and metadata extraction.
    Handles file validation, content analysis, and metadata extraction.
    """
    
    def __init__(self):
        """Initialize video processing service"""
        self.max_file_size = VideoUploadConfig.MAX_FILE_SIZE
        self.allowed_formats = VideoUploadConfig.ALLOWED_FORMATS
        self.allowed_content_types = VideoUploadConfig.ALLOWED_CONTENT_TYPES
    
    def validate_video_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str
    ) -> VideoValidationResult:
        """
        Validate video file for format, size, and content validity.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            content_type: MIME content type
            
        Returns:
            VideoValidationResult with validation details
        """
        start_time = datetime.now(timezone.utc)
        validation_errors = []
        warnings = []
        
        try:
            # Basic file validation
            if not self._validate_file_size(file_content):
                validation_errors.append(f"File size exceeds maximum limit of {self.max_file_size // (1024*1024)}MB")
            
            if not self._validate_filename(filename):
                validation_errors.append(f"Invalid filename format. Allowed formats: {', '.join(self.allowed_formats)}")
            
            if not self._validate_content_type(content_type):
                validation_errors.append(f"Unsupported content type. Allowed types: {', '.join(self.allowed_content_types)}")
            
            # Extract video format from filename
            video_format = self._extract_format_from_filename(filename)
            
            # If basic validation passes, do content validation
            if not validation_errors:
                content_validation = self._validate_video_content(file_content, filename)
                if not content_validation['is_valid']:
                    validation_errors.extend(content_validation['errors'])
                else:
                    warnings.extend(content_validation.get('warnings', []))
            
            # Calculate validation time
            validation_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Create result
            result = VideoValidationResult(
                is_valid=len(validation_errors) == 0,
                validation_errors=validation_errors,
                warnings=warnings,
                filename=filename,
                file_size=len(file_content),
                format=video_format,
                validation_time=validation_time,
                validation_method="ffprobe"
            )
            
            # If validation passed, extract metadata
            if result.is_valid:
                metadata = self._extract_video_metadata(file_content, filename)
                result.duration = metadata.get('duration')
                result.resolution = metadata.get('resolution')
                result.fps = metadata.get('fps')
                result.bitrate = metadata.get('bitrate')
                result.codec = metadata.get('codec')
            
            return result
            
        except Exception as e:
            logger.error(f"Video validation failed: {str(e)}")
            validation_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return VideoValidationResult(
                is_valid=False,
                validation_errors=[f"Validation failed: {str(e)}"],
                warnings=[],
                filename=filename,
                file_size=len(file_content),
                format=self._extract_format_from_filename(filename),
                validation_time=validation_time,
                validation_method="error"
            )
    
    def calculate_file_hash(self, file_content: bytes) -> str:
        """
        Calculate SHA256 hash of file content.
        
        Args:
            file_content: File content as bytes
            
        Returns:
            SHA256 hash as hexadecimal string
        """
        return hashlib.sha256(file_content).hexdigest()
    
    def extract_video_metadata(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Extract video metadata using ffprobe.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            
        Returns:
            Dictionary with video metadata
        """
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=f".{self._extract_format_from_filename(filename)}", delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            try:
                # Use ffprobe to extract metadata
                metadata = self._extract_metadata_with_ffprobe(temp_file_path)
                return metadata
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except Exception as e:
            logger.error(f"Failed to extract video metadata: {str(e)}")
            return {}
    
    def _validate_file_size(self, file_content: bytes) -> bool:
        """Validate file size against maximum limit"""
        return len(file_content) <= self.max_file_size
    
    def _validate_filename(self, filename: str) -> bool:
        """Validate filename format"""
        if not filename or not filename.strip():
            return False
        
        return VideoUploadConfig.is_allowed_format(filename)
    
    def _validate_content_type(self, content_type: str) -> bool:
        """Validate content type"""
        return VideoUploadConfig.is_allowed_content_type(content_type)
    
    def _extract_format_from_filename(self, filename: str) -> VideoFormat:
        """Extract video format from filename"""
        filename_lower = filename.lower()
        for format_enum in VideoFormat:
            if filename_lower.endswith(f'.{format_enum.value}'):
                return format_enum
        return VideoFormat.MP4  # Default fallback
    
    def _validate_video_content(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Validate video content using ffprobe.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=f".{self._extract_format_from_filename(filename)}", delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            try:
                # Use ffprobe to validate video
                result = self._validate_with_ffprobe(temp_file_path)
                return result
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except Exception as e:
            logger.error(f"Video content validation failed: {str(e)}")
            return {
                'is_valid': False,
                'errors': [f"Content validation failed: {str(e)}"],
                'warnings': []
            }
    
    def _extract_metadata_with_ffprobe(self, file_path: str) -> Dict[str, Any]:
        """
        Extract video metadata using ffprobe.
        
        Args:
            file_path: Path to video file
            
        Returns:
            Dictionary with video metadata
        """
        try:
            # Run ffprobe command
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.warning(f"ffprobe failed: {result.stderr}")
                return {}
            
            import json
            data = json.loads(result.stdout)
            
            # Extract relevant metadata
            metadata = {}
            
            # Get format information
            if 'format' in data:
                format_info = data['format']
                metadata['duration'] = float(format_info.get('duration', 0))
                metadata['bitrate'] = int(format_info.get('bit_rate', 0))
                metadata['size'] = int(format_info.get('size', 0))
            
            # Get video stream information
            if 'streams' in data:
                for stream in data['streams']:
                    if stream.get('codec_type') == 'video':
                        metadata['width'] = int(stream.get('width', 0))
                        metadata['height'] = int(stream.get('height', 0))
                        metadata['fps'] = self._parse_fps(stream.get('r_frame_rate', '0/1'))
                        metadata['codec'] = stream.get('codec_name', 'unknown')
                        
                        # Create resolution string
                        if metadata['width'] and metadata['height']:
                            metadata['resolution'] = f"{metadata['width']}x{metadata['height']}"
                        
                        break
            
            return metadata
            
        except subprocess.TimeoutExpired:
            logger.error("ffprobe command timed out")
            return {}
        except Exception as e:
            logger.error(f"Failed to extract metadata with ffprobe: {str(e)}")
            return {}
    
    def _validate_with_ffprobe(self, file_path: str) -> Dict[str, Any]:
        """
        Validate video file using ffprobe.
        
        Args:
            file_path: Path to video file
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Run ffprobe command to check if file is valid
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return {
                    'is_valid': False,
                    'errors': [f"Invalid video file: {result.stderr}"],
                    'warnings': []
                }
            
            import json
            data = json.loads(result.stdout)
            
            errors = []
            warnings = []
            
            # Check if video stream exists
            has_video_stream = False
            if 'streams' in data:
                for stream in data['streams']:
                    if stream.get('codec_type') == 'video':
                        has_video_stream = True
                        
                        # Check video properties
                        width = stream.get('width', 0)
                        height = stream.get('height', 0)
                        
                        if width < 64 or height < 64:
                            warnings.append("Video resolution is very low")
                        
                        if width > 4096 or height > 4096:
                            warnings.append("Video resolution is very high")
                        
                        break
            
            if not has_video_stream:
                errors.append("No video stream found in file")
            
            return {
                'is_valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings
            }
            
        except subprocess.TimeoutExpired:
            return {
                'is_valid': False,
                'errors': ["Video validation timed out"],
                'warnings': []
            }
        except Exception as e:
            return {
                'is_valid': False,
                'errors': [f"Validation failed: {str(e)}"],
                'warnings': []
            }
    
    def _parse_fps(self, fps_string: str) -> float:
        """
        Parse FPS string from ffprobe output.
        
        Args:
            fps_string: FPS string in format "num/den"
            
        Returns:
            FPS as float
        """
        try:
            if '/' in fps_string:
                num, den = fps_string.split('/')
                return float(num) / float(den) if float(den) != 0 else 0.0
            else:
                return float(fps_string)
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    def _extract_video_metadata(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Extract video metadata (wrapper method).
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            
        Returns:
            Dictionary with video metadata
        """
        return self.extract_video_metadata(file_content, filename)


# Global service instance
_video_processing_service: Optional[VideoProcessingService] = None


def get_video_processing_service() -> VideoProcessingService:
    """
    Get or create the global video processing service instance.
    
    Returns:
        VideoProcessingService instance
    """
    global _video_processing_service
    
    if _video_processing_service is None:
        _video_processing_service = VideoProcessingService()
    
    return _video_processing_service


def validate_video_file(
    file_content: bytes,
    filename: str,
    content_type: str
) -> VideoValidationResult:
    """
    Convenience function to validate video file.
    
    Args:
        file_content: File content as bytes
        filename: Original filename
        content_type: MIME content type
        
    Returns:
        VideoValidationResult with validation details
    """
    service = get_video_processing_service()
    return service.validate_video_file(file_content, filename, content_type)


def calculate_file_hash(file_content: bytes) -> str:
    """
    Convenience function to calculate file hash.
    
    Args:
        file_content: File content as bytes
        
    Returns:
        SHA256 hash as hexadecimal string
    """
    service = get_video_processing_service()
    return service.calculate_file_hash(file_content)


# Export main service class and convenience functions
__all__ = [
    'VideoProcessingService',
    'get_video_processing_service',
    'validate_video_file',
    'calculate_file_hash'
]
