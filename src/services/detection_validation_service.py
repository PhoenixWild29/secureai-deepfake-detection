#!/usr/bin/env python3
"""
Detection Validation Service
Data validation logic for export formats and visualization data consistency
"""

from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import re

# Import existing Core Detection Engine models
from ..core_models.models import DetectionResult, FrameAnalysis, Analysis
from ..models.detection_results import ExportFormatEnum, BlockchainVerificationStatus


class DetectionValidationService:
    """
    Service class for validating detection result data and export parameters.
    Ensures data integrity and adherence to specified formats and consistency rules.
    """
    
    def __init__(self, session: AsyncSession):
        """Initialize with database session"""
        self.session = session
    
    async def validate_export_format(self, format_name: str) -> bool:
        """
        Validate export format is supported.
        Returns True if format is valid, raises ValueError if invalid.
        """
        try:
            ExportFormatEnum(format_name.lower())
            return True
        except ValueError:
            supported_formats = [fmt.value for fmt in ExportFormatEnum]
            raise ValueError(f"Unsupported export format '{format_name}'. Supported formats: {supported_formats}")
    
    async def validate_visualization_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate visualization data consistency.
        Ensures data structure integrity and value ranges.
        """
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'validated_data': data.copy()
        }
        
        # Validate required fields
        required_fields = ['analysis_id', 'overall_confidence', 'frame_count', 'suspicious_frames_count']
        for field in required_fields:
            if field not in data:
                validation_results['errors'].append(f"Missing required field: {field}")
                validation_results['is_valid'] = False
        
        # Validate confidence score range
        if 'overall_confidence' in data:
            confidence = data['overall_confidence']
            if not isinstance(confidence, (int, float)):
                validation_results['errors'].append("overall_confidence must be a number")
                validation_results['is_valid'] = False
            elif not (0.0 <= confidence <= 1.0):
                validation_results['errors'].append("overall_confidence must be between 0.0 and 1.0")
                validation_results['is_valid'] = False
        
        # Validate frame counts
        if 'frame_count' in data and 'suspicious_frames_count' in data:
            frame_count = data['frame_count']
            suspicious_count = data['suspicious_frames_count']
            
            if not isinstance(frame_count, int) or frame_count < 0:
                validation_results['errors'].append("frame_count must be a non-negative integer")
                validation_results['is_valid'] = False
            
            if not isinstance(suspicious_count, int) or suspicious_count < 0:
                validation_results['errors'].append("suspicious_frames_count must be a non-negative integer")
                validation_results['is_valid'] = False
            
            if isinstance(frame_count, int) and isinstance(suspicious_count, int):
                if suspicious_count > frame_count:
                    validation_results['errors'].append("suspicious_frames_count cannot exceed frame_count")
                    validation_results['is_valid'] = False
        
        # Validate confidence distribution
        if 'confidence_distribution' in data:
            distribution = data['confidence_distribution']
            if not isinstance(distribution, dict):
                validation_results['errors'].append("confidence_distribution must be a dictionary")
                validation_results['is_valid'] = False
            else:
                valid_bins = ['0.0-0.2', '0.2-0.4', '0.4-0.6', '0.6-0.8', '0.8-1.0']
                for bin_name, count in distribution.items():
                    if bin_name not in valid_bins:
                        validation_results['warnings'].append(f"Unknown confidence bin: {bin_name}")
                    if not isinstance(count, int) or count < 0:
                        validation_results['errors'].append(f"Invalid count for bin {bin_name}: must be non-negative integer")
                        validation_results['is_valid'] = False
        
        # Validate suspicious regions summary
        if 'suspicious_regions_summary' in data:
            regions = data['suspicious_regions_summary']
            if not isinstance(regions, list):
                validation_results['errors'].append("suspicious_regions_summary must be a list")
                validation_results['is_valid'] = False
            else:
                for i, region in enumerate(regions):
                    if not isinstance(region, dict):
                        validation_results['errors'].append(f"Region {i} must be a dictionary")
                        validation_results['is_valid'] = False
                    elif 'frame_number' not in region:
                        validation_results['errors'].append(f"Region {i} missing frame_number")
                        validation_results['is_valid'] = False
        
        # Validate blockchain verification data
        if 'blockchain_verification' in data:
            blockchain_data = data['blockchain_verification']
            if not isinstance(blockchain_data, dict):
                validation_results['errors'].append("blockchain_verification must be a dictionary")
                validation_results['is_valid'] = False
            else:
                if 'status' in blockchain_data:
                    status = blockchain_data['status']
                    valid_statuses = [s.value for s in BlockchainVerificationStatus]
                    if status not in valid_statuses:
                        validation_results['warnings'].append(f"Unknown blockchain status: {status}")
        
        return validation_results
    
    async def validate_analysis_id(self, analysis_id: UUID) -> bool:
        """
        Validate analysis ID exists and is accessible.
        Returns True if valid, raises ValueError if invalid.
        """
        query = select(DetectionResult).where(DetectionResult.analysis_id == analysis_id)
        result = await self.session.execute(query)
        detection_result = result.scalar_one_or_none()
        
        if not detection_result:
            raise ValueError(f"Analysis ID {analysis_id} not found or not accessible")
        
        return True
    
    async def validate_confidence_ranges(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate confidence score ranges in data.
        Ensures all confidence values are within 0.0-1.0 range.
        """
        validation_results = {
            'is_valid': True,
            'errors': [],
            'confidence_fields_checked': []
        }
        
        # Check overall_confidence
        if 'overall_confidence' in data:
            confidence = data['overall_confidence']
            validation_results['confidence_fields_checked'].append('overall_confidence')
            
            if not isinstance(confidence, (int, float)):
                validation_results['errors'].append("overall_confidence must be a number")
                validation_results['is_valid'] = False
            elif not (0.0 <= confidence <= 1.0):
                validation_results['errors'].append("overall_confidence must be between 0.0 and 1.0")
                validation_results['is_valid'] = False
        
        # Check confidence_distribution
        if 'confidence_distribution' in data:
            distribution = data['confidence_distribution']
            validation_results['confidence_fields_checked'].append('confidence_distribution')
            
            if isinstance(distribution, dict):
                for bin_name, count in distribution.items():
                    if not isinstance(count, int) or count < 0:
                        validation_results['errors'].append(f"Invalid count in confidence_distribution bin {bin_name}")
                        validation_results['is_valid'] = False
        
        # Check suspicious_regions_summary confidence values
        if 'suspicious_regions_summary' in data:
            regions = data['suspicious_regions_summary']
            validation_results['confidence_fields_checked'].append('suspicious_regions_summary')
            
            if isinstance(regions, list):
                for i, region in enumerate(regions):
                    if isinstance(region, dict) and 'confidence' in region:
                        region_confidence = region['confidence']
                        if not isinstance(region_confidence, (int, float)):
                            validation_results['errors'].append(f"Region {i} confidence must be a number")
                            validation_results['is_valid'] = False
                        elif not (0.0 <= region_confidence <= 1.0):
                            validation_results['errors'].append(f"Region {i} confidence must be between 0.0 and 1.0")
                            validation_results['is_valid'] = False
        
        return validation_results
    
    async def validate_blockchain_hash(self, hash_value: Optional[str]) -> Dict[str, Any]:
        """
        Validate blockchain hash format and structure.
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'hash_info': {}
        }
        
        if not hash_value:
            validation_result['warnings'].append("Blockchain hash is empty or None")
            validation_result['hash_info'] = {
                'length': 0,
                'format': 'empty',
                'is_hex': False
            }
            return validation_result
        
        # Check hash length
        hash_length = len(hash_value)
        validation_result['hash_info']['length'] = hash_length
        
        # Validate hash format
        if hash_length == 64:
            # Standard SHA-256 hash length
            is_hex = all(c in '0123456789abcdefABCDEF' for c in hash_value)
            validation_result['hash_info']['is_hex'] = is_hex
            validation_result['hash_info']['format'] = 'sha256_hex' if is_hex else 'unknown_64_char'
            
            if not is_hex:
                validation_result['warnings'].append("Hash appears to be 64 characters but not hexadecimal")
        elif hash_length == 40:
            # Standard SHA-1 hash length
            is_hex = all(c in '0123456789abcdefABCDEF' for c in hash_value)
            validation_result['hash_info']['is_hex'] = is_hex
            validation_result['hash_info']['format'] = 'sha1_hex' if is_hex else 'unknown_40_char'
        elif hash_length == 32:
            # MD5 hash length
            is_hex = all(c in '0123456789abcdefABCDEF' for c in hash_value)
            validation_result['hash_info']['is_hex'] = is_hex
            validation_result['hash_info']['format'] = 'md5_hex' if is_hex else 'unknown_32_char'
        else:
            validation_result['hash_info']['format'] = f'unknown_{hash_length}_char'
            validation_result['warnings'].append(f"Unusual hash length: {hash_length} characters")
        
        # Check for common hash patterns
        if hash_value.startswith('0x'):
            validation_result['hash_info']['format'] += '_with_prefix'
            validation_result['warnings'].append("Hash includes '0x' prefix")
        elif hash_value.startswith('sha256:'):
            validation_result['hash_info']['format'] += '_with_prefix'
            validation_result['warnings'].append("Hash includes 'sha256:' prefix")
        
        return validation_result
    
    async def validate_export_options(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate export options parameters.
        Ensures options are reasonable and supported.
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'validated_options': options.copy()
        }
        
        # Validate page_size for PDF exports
        if 'page_size' in options:
            page_size = options['page_size']
            valid_sizes = ['A4', 'Letter', 'Legal', 'A3', 'A5']
            if page_size not in valid_sizes:
                validation_result['errors'].append(f"Invalid page_size '{page_size}'. Valid sizes: {valid_sizes}")
                validation_result['is_valid'] = False
        
        # Validate include_timestamps
        if 'include_timestamps' in options:
            include_timestamps = options['include_timestamps']
            if not isinstance(include_timestamps, bool):
                validation_result['errors'].append("include_timestamps must be a boolean")
                validation_result['is_valid'] = False
        
        # Validate compression_level
        if 'compression_level' in options:
            compression_level = options['compression_level']
            if not isinstance(compression_level, int):
                validation_result['errors'].append("compression_level must be an integer")
                validation_result['is_valid'] = False
            elif not (0 <= compression_level <= 9):
                validation_result['errors'].append("compression_level must be between 0 and 9")
                validation_result['is_valid'] = False
        
        # Validate include_metadata
        if 'include_metadata' in options:
            include_metadata = options['include_metadata']
            if not isinstance(include_metadata, bool):
                validation_result['errors'].append("include_metadata must be a boolean")
                validation_result['is_valid'] = False
        
        # Validate max_file_size
        if 'max_file_size' in options:
            max_file_size = options['max_file_size']
            if not isinstance(max_file_size, int):
                validation_result['errors'].append("max_file_size must be an integer")
                validation_result['is_valid'] = False
            elif max_file_size <= 0:
                validation_result['errors'].append("max_file_size must be positive")
                validation_result['is_valid'] = False
            elif max_file_size > 100 * 1024 * 1024:  # 100MB limit
                validation_result['warnings'].append("max_file_size exceeds 100MB, may cause performance issues")
        
        # Validate custom_fields
        if 'custom_fields' in options:
            custom_fields = options['custom_fields']
            if not isinstance(custom_fields, list):
                validation_result['errors'].append("custom_fields must be a list")
                validation_result['is_valid'] = False
            else:
                for field in custom_fields:
                    if not isinstance(field, str):
                        validation_result['errors'].append("All custom_fields must be strings")
                        validation_result['is_valid'] = False
                        break
        
        return validation_result
    
    async def validate_search_parameters(
        self, 
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        min_frames: Optional[int] = None,
        max_frames: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Validate search and filter parameters.
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validate confidence ranges
        if min_confidence is not None:
            if not (0.0 <= min_confidence <= 1.0):
                validation_result['errors'].append("min_confidence must be between 0.0 and 1.0")
                validation_result['is_valid'] = False
        
        if max_confidence is not None:
            if not (0.0 <= max_confidence <= 1.0):
                validation_result['errors'].append("max_confidence must be between 0.0 and 1.0")
                validation_result['is_valid'] = False
        
        if min_confidence is not None and max_confidence is not None:
            if min_confidence > max_confidence:
                validation_result['errors'].append("min_confidence cannot be greater than max_confidence")
                validation_result['is_valid'] = False
        
        # Validate frame counts
        if min_frames is not None:
            if min_frames < 0:
                validation_result['errors'].append("min_frames must be non-negative")
                validation_result['is_valid'] = False
        
        if max_frames is not None:
            if max_frames < 0:
                validation_result['errors'].append("max_frames must be non-negative")
                validation_result['is_valid'] = False
        
        if min_frames is not None and max_frames is not None:
            if min_frames > max_frames:
                validation_result['errors'].append("min_frames cannot be greater than max_frames")
                validation_result['is_valid'] = False
        
        # Validate date ranges
        if start_date is not None and end_date is not None:
            if start_date > end_date:
                validation_result['errors'].append("start_date cannot be greater than end_date")
                validation_result['is_valid'] = False
        
        # Validate pagination
        if limit <= 0:
            validation_result['errors'].append("limit must be positive")
            validation_result['is_valid'] = False
        elif limit > 1000:
            validation_result['warnings'].append("Large limit value may cause performance issues")
        
        if offset < 0:
            validation_result['errors'].append("offset must be non-negative")
            validation_result['is_valid'] = False
        
        return validation_result
    
    async def validate_data_consistency(self, detection_result: DetectionResult, frame_analyses: List[FrameAnalysis]) -> Dict[str, Any]:
        """
        Validate consistency between detection result and frame analyses.
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'consistency_checks': {}
        }
        
        # Check frame count consistency
        actual_frame_count = len(frame_analyses)
        expected_frame_count = detection_result.frame_count
        validation_result['consistency_checks']['frame_count'] = {
            'actual': actual_frame_count,
            'expected': expected_frame_count,
            'matches': actual_frame_count == expected_frame_count
        }
        
        if actual_frame_count != expected_frame_count:
            validation_result['warnings'].append(f"Frame count mismatch: expected {expected_frame_count}, found {actual_frame_count}")
        
        # Check suspicious frames consistency
        actual_suspicious_count = len([fa for fa in frame_analyses if fa.confidence_score > 0.5])
        expected_suspicious_count = detection_result.suspicious_frames
        validation_result['consistency_checks']['suspicious_frames'] = {
            'actual': actual_suspicious_count,
            'expected': expected_suspicious_count,
            'matches': actual_suspicious_count == expected_suspicious_count
        }
        
        if actual_suspicious_count != expected_suspicious_count:
            validation_result['warnings'].append(f"Suspicious frames count mismatch: expected {expected_suspicious_count}, found {actual_suspicious_count}")
        
        # Check frame number sequence
        frame_numbers = [fa.frame_number for fa in frame_analyses]
        if frame_numbers:
            expected_sequence = list(range(min(frame_numbers), max(frame_numbers) + 1))
            sequence_valid = frame_numbers == expected_sequence
            validation_result['consistency_checks']['frame_sequence'] = {
                'is_sequential': sequence_valid,
                'frame_range': f"{min(frame_numbers)}-{max(frame_numbers)}"
            }
            
            if not sequence_valid:
                validation_result['warnings'].append("Frame numbers are not sequential")
        
        # Check confidence score consistency
        if frame_analyses:
            frame_confidences = [float(fa.confidence_score) for fa in frame_analyses]
            avg_frame_confidence = sum(frame_confidences) / len(frame_confidences)
            overall_confidence = float(detection_result.overall_confidence)
            
            confidence_diff = abs(avg_frame_confidence - overall_confidence)
            validation_result['consistency_checks']['confidence_consistency'] = {
                'frame_average': avg_frame_confidence,
                'overall_confidence': overall_confidence,
                'difference': confidence_diff,
                'within_tolerance': confidence_diff < 0.1  # 10% tolerance
            }
            
            if confidence_diff >= 0.1:
                validation_result['warnings'].append(f"Confidence score inconsistency: frame average {avg_frame_confidence:.3f}, overall {overall_confidence:.3f}")
        
        return validation_result
