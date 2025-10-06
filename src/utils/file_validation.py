#!/usr/bin/env python3
"""
Enhanced File Validation Utilities
Comprehensive file validation including content validation, format detection, and integrity checks
"""

import os
import re
import mimetypes
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..errors.api_errors import FileValidationError, InvalidFileTypeError, FileSizeExceededError


class EnhancedFileValidator:
    """
    Enhanced file validator with comprehensive validation capabilities.
    """
    
    # Supported video formats with MIME types and extensions
    SUPPORTED_VIDEO_FORMATS = {
        'video/mp4': {
            'extensions': ['.mp4'],
            'magic_bytes': [b'\x00\x00\x00\x20ftypisom', b'\x00\x00\x00\x18ftypmp42'],
            'description': 'MP4 Video'
        },
        'video/avi': {
            'extensions': ['.avi'],
            'magic_bytes': [b'RIFF'],
            'description': 'AVI Video'
        },
        'video/quicktime': {
            'extensions': ['.mov'],
            'magic_bytes': [b'\x00\x00\x00\x14ftypqt'],
            'description': 'QuickTime Video'
        },
        'video/x-msvideo': {
            'extensions': ['.avi'],
            'magic_bytes': [b'RIFF'],
            'description': 'AVI Video (Alternative MIME)'
        },
        'video/mkv': {
            'extensions': ['.mkv'],
            'magic_bytes': [b'\x1a\x45\xdf\xa3'],
            'description': 'Matroska Video'
        },
        'video/x-matroska': {
            'extensions': ['.mkv'],
            'magic_bytes': [b'\x1a\x45\xdf\xa3'],
            'description': 'Matroska Video (Alternative MIME)'
        },
        'video/webm': {
            'extensions': ['.webm'],
            'magic_bytes': [b'\x1a\x45\xdf\xa3'],
            'description': 'WebM Video'
        },
        'video/ogg': {
            'extensions': ['.ogv'],
            'magic_bytes': [b'OggS'],
            'description': 'Ogg Video'
        }
    }
    
    # File size limits
    DEFAULT_MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    DEFAULT_MIN_FILE_SIZE = 1024  # 1KB
    
    # Security patterns
    DANGEROUS_EXTENSIONS = [
        '.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.vbs', '.js',
        '.jar', '.php', '.asp', '.aspx', '.jsp', '.py', '.rb', '.pl',
        '.sh', '.ps1', '.psm1', '.psd1', '.ps1xml', '.psc1', '.pssc'
    ]
    
    DANGEROUS_FILENAME_PATTERNS = [
        r'\.\.',  # Path traversal
        r'/',     # Directory separator
        r'\\',    # Windows directory separator
        r':',     # Windows drive separator
        r'<',     # HTML/XML injection
        r'>',     # HTML/XML injection
        r'"',     # Command injection
        r"'",     # Command injection
        r'\|',    # Command injection
        r'&',     # Command injection
        r';',     # Command injection
        r'\*',    # Wildcard
        r'\?',    # Wildcard
        r'\[',    # Character class
        r'\]'     # Character class
    ]
    
    def __init__(
        self,
        max_file_size: Optional[int] = None,
        min_file_size: Optional[int] = None,
        strict_content_validation: bool = True
    ):
        """
        Initialize enhanced file validator.
    
    Args:
            max_file_size: Maximum file size in bytes
            min_file_size: Minimum file size in bytes
            strict_content_validation: Whether to perform strict content validation
        """
        self.max_file_size = max_file_size or self.DEFAULT_MAX_FILE_SIZE
        self.min_file_size = min_file_size or self.DEFAULT_MIN_FILE_SIZE
        self.strict_content_validation = strict_content_validation
        
        # Compile regex patterns for performance
        self.dangerous_patterns = [
            re.compile(pattern) for pattern in self.DANGEROUS_FILENAME_PATTERNS
        ]
    
    async def validate_video_file_content(
        self,
        filename: str,
        content_type: str,
        file_size: int,
        content: bytes,
        validate_integrity: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive validation of video file content.
    
    Args:
            filename: Original filename
            content_type: MIME content type
            file_size: File size in bytes
            content: File content bytes
            validate_integrity: Whether to validate file integrity
        
    Returns:
            Dictionary with validation results
        """
        validation_results = {
            'is_valid': True,
            'filename': filename,
            'content_type': content_type,
            'file_size': file_size,
            'errors': [],
            'warnings': [],
            'validation_details': {}
        }
        
        try:
            # Basic filename validation
            self._validate_filename(filename, validation_results)
            
            # File size validation
            self._validate_file_size(file_size, validation_results)
            
            # Content type validation
            self._validate_content_type(content_type, filename, validation_results)
            
            # File extension validation
            self._validate_file_extension(filename, validation_results)
            
            # Content-based validation
            if self.strict_content_validation:
                await self._validate_file_content(content, content_type, validation_results)
            
            # Integrity validation
            if validate_integrity:
                await self._validate_file_integrity(content, content_type, validation_results)
            
            # Security checks
            self._validate_security(filename, validation_results)
            
            # Determine overall validity
            validation_results['is_valid'] = len(validation_results['errors']) == 0
            
            return validation_results
            
        except Exception as e:
            validation_results['is_valid'] = False
            validation_results['errors'].append(f"Validation error: {str(e)}")
            return validation_results
    
    def _validate_filename(self, filename: str, results: Dict[str, Any]) -> None:
        """Validate filename for basic requirements."""
        if not filename:
            results['errors'].append("Filename is required")
            return
        
        if not filename.strip():
            results['errors'].append("Filename cannot be empty or whitespace only")
            return
        
        # Check filename length
        if len(filename) > 255:
            results['errors'].append(f"Filename too long (max 255 characters, got {len(filename)})")
            return
        
        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if pattern.search(filename):
                results['errors'].append(f"Filename contains potentially unsafe characters: {filename}")
                return
        
        results['validation_details']['filename_valid'] = True
    
    def _validate_file_size(self, file_size: int, results: Dict[str, Any]) -> None:
        """Validate file size against limits."""
        if file_size <= 0:
            results['errors'].append("File size must be greater than 0")
            return
        
        if file_size < self.min_file_size:
            results['errors'].append(
                f"File too small (min {self._format_size(self.min_file_size)}, "
                f"got {self._format_size(file_size)})"
            )
            return
        
        if file_size > self.max_file_size:
            results['errors'].append(
                f"File too large (max {self._format_size(self.max_file_size)}, "
                f"got {self._format_size(file_size)})"
            )
            return
        
        # Warning for large files
        if file_size > 100 * 1024 * 1024:  # 100MB
            results['warnings'].append("Large file detected, upload may take longer than usual")
        
        results['validation_details']['file_size_valid'] = True
    
    def _validate_content_type(self, content_type: str, filename: str, results: Dict[str, Any]) -> None:
        """Validate MIME content type."""
        if not content_type:
            results['errors'].append("Content type is required")
            return
        
        # Normalize content type
        content_type = content_type.lower().strip()
        
        # Check against supported types
        if content_type not in [ct.lower() for ct in self.SUPPORTED_VIDEO_FORMATS.keys()]:
            # Try to guess content type from filename
            guessed_type, _ = mimetypes.guess_type(filename)
            if guessed_type and guessed_type.lower() in [ct.lower() for ct in self.SUPPORTED_VIDEO_FORMATS.keys()]:
                results['warnings'].append(
                    f"Content type '{content_type}' not recognized, "
                    f"but filename suggests '{guessed_type}' which is allowed"
                )
                results['validation_details']['content_type_guessed'] = guessed_type
            else:
                results['errors'].append(
                    f"Invalid content type '{content_type}'. "
                    f"Allowed types: {', '.join(self.SUPPORTED_VIDEO_FORMATS.keys())}"
                )
                return
        
        # Check for suspicious content types
        if self._is_suspicious_content_type(content_type):
            results['errors'].append(f"Suspicious content type detected: {content_type}")
            return
        
        results['validation_details']['content_type_valid'] = True
    
    def _validate_file_extension(self, filename: str, results: Dict[str, Any]) -> None:
        """Validate file extension."""
        if not filename:
            return
        
        # Extract extension
        _, ext = os.path.splitext(filename.lower())
        
        if not ext:
            results['errors'].append("File must have an extension")
            return
        
        # Get all supported extensions
        all_supported_extensions = []
        for format_info in self.SUPPORTED_VIDEO_FORMATS.values():
            all_supported_extensions.extend(format_info['extensions'])
        
        # Check if extension is supported
        if ext not in all_supported_extensions:
            results['errors'].append(
                f"File extension '{ext}' not allowed. "
                f"Allowed extensions: {', '.join(all_supported_extensions)}"
            )
            return
        
        # Check for dangerous extensions
        if ext in self.DANGEROUS_EXTENSIONS:
            results['errors'].append(f"Dangerous file extension detected: {ext}")
            return
        
        results['validation_details']['extension_valid'] = True
    
    async def _validate_file_content(self, content: bytes, content_type: str, results: Dict[str, Any]) -> None:
        """Validate file content based on magic bytes."""
        try:
            # Get expected magic bytes for the content type
            format_info = self.SUPPORTED_VIDEO_FORMATS.get(content_type.lower())
            if not format_info:
                return
            
            magic_bytes = format_info.get('magic_bytes', [])
            if not magic_bytes:
                return
            
            # Check if content starts with any expected magic bytes
            content_valid = False
            for magic in magic_bytes:
                if content.startswith(magic):
                    content_valid = True
                    break
            
            if not content_valid:
                # Try checking first few bytes more flexibly
                for magic in magic_bytes:
                    if magic in content[:100]:  # Check first 100 bytes
                        content_valid = True
                        break
            
            if not content_valid:
                results['warnings'].append(
                    f"File content doesn't match expected format for {content_type}. "
                    "File may be corrupted or mislabeled."
                )
                results['validation_details']['content_magic_bytes_mismatch'] = True
            else:
                results['validation_details']['content_magic_bytes_valid'] = True
        
    except Exception as e:
            results['warnings'].append(f"Content validation failed: {str(e)}")
    
    async def _validate_file_integrity(self, content: bytes, content_type: str, results: Dict[str, Any]) -> None:
        """Validate file integrity and basic structure."""
        try:
            # Basic integrity checks
            if len(content) == 0:
                results['errors'].append("File is empty")
                return
            
            # Check for common corruption patterns
            if content.count(b'\x00') > len(content) * 0.5:  # More than 50% null bytes
                results['warnings'].append("File contains excessive null bytes, may be corrupted")
                results['validation_details']['excessive_null_bytes'] = True
            
            # Check for truncated files (basic check)
            if content_type.lower() in ['video/mp4', 'video/quicktime']:
                # MP4/MOV files should end with proper container structure
                if not content.endswith((b'mdat', b'moov', b'free')):
                    results['warnings'].append("File may be truncated or corrupted")
                    results['validation_details']['possible_truncation'] = True
            
            results['validation_details']['integrity_valid'] = True
            
        except Exception as e:
            results['warnings'].append(f"Integrity validation failed: {str(e)}")
    
    def _validate_security(self, filename: str, results: Dict[str, Any]) -> None:
        """Perform security validation checks."""
        # Check for executable patterns
        if any(filename.lower().endswith(ext) for ext in self.DANGEROUS_EXTENSIONS):
            results['errors'].append("Executable file type not allowed")
            return
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'\.(php|asp|aspx|jsp|cgi)',  # Server-side scripts
            r'\.(bat|cmd|sh|ps1)',        # Scripts
            r'\.(exe|dll|so)',            # Executables
            r'\.(sql|db|sqlite)',         # Database files
            r'\.(env|config|ini)',        # Configuration files
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, filename.lower()):
                results['errors'].append(f"Suspicious file pattern detected: {pattern}")
                return
        
        results['validation_details']['security_valid'] = True
    
    def _is_suspicious_content_type(self, content_type: str) -> bool:
        """Check if content type is suspicious."""
        suspicious_types = [
            'application/x-executable',
            'application/x-msdownload',
            'application/x-shockwave-flash',
            'text/html',
            'application/javascript',
            'application/x-php',
            'application/x-asp',
            'application/x-jsp'
        ]
        
        return content_type.lower() in suspicious_types
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 Bytes"
        
        size_names = ["Bytes", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"


# Convenience functions
async def validate_video_file_content(
    filename: str,
    content_type: str,
    file_size: int,
    content: bytes,
    max_size: Optional[int] = None,
    validate_integrity: bool = True
) -> Dict[str, Any]:
    """
    Validate video file content comprehensively.
    
    Args:
        filename: Original filename
        content_type: MIME content type
        file_size: File size in bytes
        content: File content bytes
        max_size: Optional maximum file size override
        validate_integrity: Whether to validate file integrity
        
    Returns:
        Dictionary with validation results
    """
    validator = EnhancedFileValidator(max_file_size=max_size)
    return await validator.validate_video_file_content(
        filename=filename,
        content_type=content_type,
        file_size=file_size,
        content=content,
        validate_integrity=validate_integrity
    )


def is_valid_video_file(
    filename: str,
    content_type: str,
    file_size: int
) -> bool:
    """
    Quick check if a file is a valid video file.
    
    Args:
        filename: Original filename
        content_type: MIME content type
        file_size: File size in bytes
        
    Returns:
        True if valid, False otherwise
    """
    try:
        validator = EnhancedFileValidator()
        
        # Basic validation without content
        if not filename or not content_type:
            return False
        
        # Check extension
        _, ext = os.path.splitext(filename.lower())
        all_supported_extensions = []
        for format_info in validator.SUPPORTED_VIDEO_FORMATS.values():
            all_supported_extensions.extend(format_info['extensions'])
        
        if ext not in all_supported_extensions:
            return False
        
        # Check content type
        if content_type.lower() not in [ct.lower() for ct in validator.SUPPORTED_VIDEO_FORMATS.keys()]:
            return False
        
        # Check file size
        if file_size <= 0 or file_size > validator.max_file_size:
        return False
        
        return True
        
    except Exception:
        return False


def get_supported_video_formats() -> Dict[str, Dict[str, Any]]:
    """
    Get information about supported video formats.
        
    Returns:
        Dictionary with format information
    """
    return EnhancedFileValidator.SUPPORTED_VIDEO_FORMATS.copy()


# Export main components
__all__ = [
    'EnhancedFileValidator',
    'validate_video_file_content',
    'is_valid_video_file',
    'get_supported_video_formats'
]