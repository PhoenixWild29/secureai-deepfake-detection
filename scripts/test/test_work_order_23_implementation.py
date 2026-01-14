#!/usr/bin/env python3
"""
Test Suite for Work Order #23 Implementation
Detection Results Display Data Models and API Integration
"""

import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from typing import Dict, Any, List

# Import our implemented models and services
from src.models.detection_results import (
    VisualizationResultResponse,
    ExportResultRequest,
    BlockchainVerificationResponse,
    DetectionResultSearchRequest,
    ExportFormatEnum,
    BlockchainVerificationStatus
)
from src.services.detection_serialization_service import DetectionSerializationService


class TestDetectionResultsModels:
    """Test the new detection results models"""
    
    def test_visualization_result_response_creation(self):
        """Test creating a valid VisualizationResultResponse"""
        response = VisualizationResultResponse(
            analysis_id=uuid4(),
            overall_confidence=0.75,
            confidence_distribution={
                '0.0-0.2': 10,
                '0.2-0.4': 15,
                '0.4-0.6': 25,
                '0.6-0.8': 30,
                '0.8-1.0': 20
            },
            suspicious_regions_summary=[
                {
                    'frame_number': 0,
                    'region_id': 'region_1',
                    'region_data': {'confidence': 0.8, 'coordinates': {'x': 100, 'y': 100}},
                    'confidence': 0.8,
                    'coordinates': {'x': 100, 'y': 100},
                    'artifacts': ['blur', 'compression']
                }
            ],
            blockchain_verification={
                'status': 'verified',
                'blockchain_hash': 'abc123def456',
                'is_tamper_proof': True
            },
            export_formats=['pdf', 'json', 'csv'],
            heatmap_data={'resolution': '1024x768', 'data': []},
            frame_count=100,
            suspicious_frames_count=25,
            processing_time_ms=5000,
            created_at=datetime.now(timezone.utc)
        )
        
        assert response.overall_confidence == 0.75
        assert response.frame_count == 100
        assert response.suspicious_frames_count == 25
        assert response.get_confidence_percentage() == 75.0
        assert response.get_suspicious_percentage() == 25.0
        assert response.get_processing_time_seconds() == 5.0
    
    def test_visualization_result_response_validation(self):
        """Test validation of VisualizationResultResponse"""
        # Test confidence score validation
        with pytest.raises(ValueError, match="confidence_score must be within"):
            VisualizationResultResponse(
                analysis_id=uuid4(),
                overall_confidence=1.5,  # Invalid: > 1.0
                frame_count=100,
                suspicious_frames_count=25,
                processing_time_ms=5000,
                created_at=datetime.now(timezone.utc)
            )
        
        # Test frame count validation
        with pytest.raises(ValueError, match="suspicious_frames_count cannot exceed frame_count"):
            VisualizationResultResponse(
                analysis_id=uuid4(),
                overall_confidence=0.75,
                frame_count=100,
                suspicious_frames_count=150,  # Invalid: > frame_count
                processing_time_ms=5000,
                created_at=datetime.now(timezone.utc)
            )
    
    def test_export_result_request_creation(self):
        """Test creating a valid ExportResultRequest"""
        request = ExportResultRequest(
            analysis_id=uuid4(),
            format="json",
            include_frames=True,
            include_blockchain=True,
            export_options={
                'page_size': 'A4',
                'include_timestamps': True,
                'compression_level': 6
            }
        )
        
        assert request.format == "json"
        assert request.include_frames is True
        assert request.include_blockchain is True
        assert request.get_export_format_enum() == ExportFormatEnum.JSON
        assert request.should_include_detailed_data() is True
        assert request.should_include_blockchain_data() is True
    
    def test_export_result_request_validation(self):
        """Test validation of ExportResultRequest"""
        # Test format validation
        with pytest.raises(ValueError, match="Unsupported export format"):
            ExportResultRequest(
                analysis_id=uuid4(),
                format="invalid_format"  # Invalid format
            )
        
        # Test export options validation
        with pytest.raises(ValueError, match="page_size must be one of"):
            ExportResultRequest(
                analysis_id=uuid4(),
                format="pdf",
                export_options={'page_size': 'InvalidSize'}  # Invalid page size
            )
    
    def test_blockchain_verification_response_creation(self):
        """Test creating a valid BlockchainVerificationResponse"""
        response = BlockchainVerificationResponse(
            analysis_id=uuid4(),
            blockchain_hash="abc123def456789",
            verification_status=BlockchainVerificationStatus.VERIFIED,
            verification_timestamp=datetime.now(timezone.utc),
            verification_details={'hash_length': 15, 'format': 'hex'},
            is_tamper_proof=True
        )
        
        assert response.verification_status == BlockchainVerificationStatus.VERIFIED
        assert response.is_tamper_proof is True
        assert response.blockchain_hash == "abc123def456789"
    
    def test_detection_result_search_request_creation(self):
        """Test creating a valid DetectionResultSearchRequest"""
        request = DetectionResultSearchRequest(
            min_confidence=0.3,
            max_confidence=0.8,
            min_frames=10,
            max_frames=100,
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc),
            limit=50,
            offset=0,
            sort_by="created_at",
            sort_order="desc"
        )
        
        assert request.min_confidence == 0.3
        assert request.max_confidence == 0.8
        assert request.limit == 50
        assert request.sort_by == "created_at"
        assert request.sort_order == "desc"
    
    def test_detection_result_search_request_validation(self):
        """Test validation of DetectionResultSearchRequest"""
        # Test confidence range validation
        with pytest.raises(ValueError, match="min_confidence cannot be greater than max_confidence"):
            DetectionResultSearchRequest(
                min_confidence=0.8,
                max_confidence=0.3  # Invalid: min > max
            )
        
        # Test sort field validation
        with pytest.raises(ValueError, match="Invalid sort field"):
            DetectionResultSearchRequest(
                sort_by="invalid_field"  # Invalid sort field
            )


class TestDetectionSerializationService:
    """Test the serialization service"""
    
    def test_json_serialization(self):
        """Test JSON serialization"""
        service = DetectionSerializationService()
        
        result_data = {
            "analysis_id": uuid4(),
            "overall_confidence": 0.75,
            "frame_count": 100,
            "suspicious_frames": 25,
            "processing_time_ms": 5000,
            "created_at": datetime.now(timezone.utc),
            "blockchain_hash": "abc123def456"
        }
        
        json_data = service.serialize_to_json(result_data, include_frames=True, include_blockchain=True)
        
        assert json_data["overall_confidence"] == 0.75
        assert json_data["frame_count"] == 100
        assert json_data["export_format"] == "json"
        assert "audit_trail" in json_data
        assert "blockchain_hash" in json_data
    
    def test_csv_data_preparation(self):
        """Test CSV data preparation"""
        service = DetectionSerializationService()
        
        result_data = {
            "analysis_id": uuid4(),
            "overall_confidence": 0.75,
            "frame_count": 100,
            "suspicious_frames": 25,
            "processing_time_ms": 5000,
            "created_at": datetime.now(timezone.utc),
            "blockchain_hash": "abc123def456"
        }
        
        # Mock frame data
        from decimal import Decimal
        frame_data = [
            type('FrameAnalysis', (), {
                'frame_number': 0,
                'confidence_score': Decimal('0.8'),
                'processing_time_ms': 100,
                'suspicious_regions': {'region1': {'x': 100, 'y': 100}},
                'artifacts': {'blur': 0.9}
            })()
        ]
        
        csv_data = service.prepare_csv_data(result_data, frame_data)
        
        assert len(csv_data) == 2  # Header row + 1 frame row
        assert csv_data[0]["frame_number"] == "SUMMARY"
        assert csv_data[1]["frame_number"] == 0
        assert csv_data[1]["frame_confidence"] == 0.8
    
    def test_pdf_data_preparation(self):
        """Test PDF data preparation"""
        service = DetectionSerializationService()
        
        result_data = {
            "analysis_id": uuid4(),
            "overall_confidence": 0.75,
            "frame_count": 100,
            "suspicious_frames": 25,
            "processing_time_ms": 5000,
            "created_at": datetime.now(timezone.utc),
            "blockchain_hash": "abc123def456"
        }
        
        # Mock frame data
        from decimal import Decimal
        frame_data = [
            type('FrameAnalysis', (), {
                'frame_number': 0,
                'confidence_score': Decimal('0.8'),
                'processing_time_ms': 100,
                'suspicious_regions': {'region1': {'x': 100, 'y': 100}},
                'artifacts': {'blur': 0.9}
            })()
        ]
        
        pdf_data = service.prepare_pdf_data(result_data, frame_data)
        
        assert "document_info" in pdf_data
        assert "executive_summary" in pdf_data
        assert "technical_details" in pdf_data
        assert "frame_analysis_summary" in pdf_data
        assert "frame_details" in pdf_data
        assert pdf_data["executive_summary"]["overall_confidence"] == 0.75
        assert pdf_data["executive_summary"]["confidence_percentage"] == 75.0
    
    def test_audit_trail_creation(self):
        """Test audit trail creation"""
        service = DetectionSerializationService()
        
        data = {
            "analysis_id": uuid4(),
            "overall_confidence": 0.75,
            "created_at": datetime.now(timezone.utc),
            "blockchain_hash": "abc123def456",
            "frame_analysis": [{"frame": 0}],
            "suspicious_regions_summary": [{"region": 1}],
            "confidence_distribution": {"0.0-0.2": 10}
        }
        
        audit_trail = service.create_audit_trail(data)
        
        assert "export_timestamp" in audit_trail
        assert "data_version" in audit_trail
        assert "original_analysis_id" in audit_trail
        assert "data_integrity_checks" in audit_trail
        assert "serialization_metadata" in audit_trail
        assert audit_trail["data_integrity_checks"]["confidence_range_valid"] is True
        assert audit_trail["serialization_metadata"]["frames_included"] is True
    
    def test_frame_statistics_aggregation(self):
        """Test frame statistics aggregation"""
        service = DetectionSerializationService()
        
        # Mock frame data
        from decimal import Decimal
        frames = [
            type('FrameAnalysis', (), {
                'confidence_score': Decimal('0.3'),
                'processing_time_ms': 100,
                'suspicious_regions': {'region1': {}},
                'artifacts': {'blur': 0.9}
            })(),
            type('FrameAnalysis', (), {
                'confidence_score': Decimal('0.7'),
                'processing_time_ms': 150,
                'suspicious_regions': None,
                'artifacts': None
            })(),
            type('FrameAnalysis', (), {
                'confidence_score': Decimal('0.9'),
                'processing_time_ms': 120,
                'suspicious_regions': {'region2': {}},
                'artifacts': {'compression': 0.8}
            })()
        ]
        
        stats = service.aggregate_frame_statistics(frames)
        
        assert stats["total_frames"] == 3
        assert stats["average_confidence"] == (0.3 + 0.7 + 0.9) / 3
        assert stats["min_confidence"] == 0.3
        assert stats["max_confidence"] == 0.9
        assert stats["suspicious_frames"] == 2  # frames with confidence > 0.5
        assert stats["suspicious_percentage"] == (2 / 3) * 100
        assert stats["average_processing_time_ms"] == (100 + 150 + 120) / 3


class TestExportFormatEnum:
    """Test the export format enum"""
    
    def test_export_format_enum_values(self):
        """Test export format enum has correct values"""
        assert ExportFormatEnum.PDF == "pdf"
        assert ExportFormatEnum.JSON == "json"
        assert ExportFormatEnum.CSV == "csv"


class TestBlockchainVerificationStatus:
    """Test the blockchain verification status enum"""
    
    def test_blockchain_verification_status_values(self):
        """Test blockchain verification status has correct values"""
        assert BlockchainVerificationStatus.VERIFIED == "verified"
        assert BlockchainVerificationStatus.PENDING == "pending"
        assert BlockchainVerificationStatus.FAILED == "failed"
        assert BlockchainVerificationStatus.NOT_AVAILABLE == "not_available"


def test_work_order_23_requirements_compliance():
    """
    Test that all Work Order #23 requirements are met
    """
    
    # Test 1: VisualizationResultResponse model with all required fields
    visualization_response = VisualizationResultResponse(
        analysis_id=uuid4(),
        overall_confidence=0.75,
        confidence_distribution={'0.0-0.2': 10, '0.2-0.4': 15, '0.4-0.6': 25, '0.6-0.8': 30, '0.8-1.0': 20},
        suspicious_regions_summary=[{'frame_number': 0, 'region_id': 'region_1', 'confidence': 0.8}],
        blockchain_verification={'status': 'verified', 'is_tamper_proof': True},
        export_formats=['pdf', 'json', 'csv'],
        heatmap_data={'resolution': '1024x768'},
        frame_count=100,
        suspicious_frames_count=25,
        processing_time_ms=5000,
        created_at=datetime.now(timezone.utc)
    )
    
    # Verify all required fields are present
    assert hasattr(visualization_response, 'analysis_id')
    assert hasattr(visualization_response, 'overall_confidence')
    assert hasattr(visualization_response, 'confidence_distribution')
    assert hasattr(visualization_response, 'suspicious_regions_summary')
    assert hasattr(visualization_response, 'blockchain_verification')
    assert hasattr(visualization_response, 'export_formats')
    assert hasattr(visualization_response, 'heatmap_data')
    
    # Test 2: ExportResultRequest model with all required fields
    export_request = ExportResultRequest(
        analysis_id=uuid4(),
        format='json',
        include_frames=True,
        include_blockchain=True,
        export_options={'page_size': 'A4', 'compression_level': 6}
    )
    
    # Verify all required fields are present
    assert hasattr(export_request, 'analysis_id')
    assert hasattr(export_request, 'format')
    assert hasattr(export_request, 'include_frames')
    assert hasattr(export_request, 'include_blockchain')
    assert hasattr(export_request, 'export_options')
    
    # Test 3: Export format validation
    supported_formats = ['pdf', 'json', 'csv']
    for format_name in supported_formats:
        request = ExportResultRequest(analysis_id=uuid4(), format=format_name)
        assert request.format == format_name
    
    # Test 4: Serialization service for multiple formats
    service = DetectionSerializationService()
    
    result_data = {
        'analysis_id': uuid4(),
        'overall_confidence': 0.75,
        'frame_count': 100,
        'suspicious_frames': 25,
        'processing_time_ms': 5000,
        'created_at': datetime.now(timezone.utc),
        'blockchain_hash': 'abc123def456'
    }
    
    # Test JSON serialization
    json_data = service.serialize_to_json(result_data)
    assert json_data['export_format'] == 'json'
    assert 'audit_trail' in json_data
    
    # Test 5: Data validation for export formats
    validation_results = []
    for format_name in ['pdf', 'json', 'csv']:
        try:
            request = ExportResultRequest(analysis_id=uuid4(), format=format_name)
            validation_results.append(True)
        except ValueError:
            validation_results.append(False)
    
    assert all(validation_results), "All export formats should be valid"
    
    print("✅ All Work Order #23 requirements have been successfully implemented and tested!")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
