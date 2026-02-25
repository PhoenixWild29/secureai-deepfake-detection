#!/usr/bin/env python3
"""
Test Core Video Detection API Implementation
Comprehensive tests for Work Order #1 core video detection API endpoints
"""

import pytest
import uuid
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import UploadFile
from io import BytesIO

# Test imports
from app.schemas.detection import (
    DetectionStatus,
    ProcessingStage,
    DetectionConfig,
    DetectionResponse,
    DetectionStatusResponse,
    DetectionResultsResponse,
    validate_video_file,
    validate_file_size
)
from app.core.exceptions import (
    AnalysisNotFoundError,
    VideoValidationError,
    UnsupportedVideoFormatError,
    VideoSizeExceededError,
    ConcurrentAnalysisLimitError
)
from app.core.config import DetectionConfig as ConfigClass, detection_settings
from app.services.video_processing import VideoProcessingService, AnalysisTracker
from app.api.v1.endpoints.detect import router
from app.main import app


class TestDetectionSchemas:
    """Test detection Pydantic models and validation"""
    
    def test_detection_config_creation(self):
        """Test DetectionConfig model creation and validation"""
        config = DetectionConfig(
            detection_methods=["resnet50", "clip"],
            confidence_threshold=0.7,
            frame_sampling_rate=2,
            enable_blockchain_verification=True
        )
        
        assert config.detection_methods == ["resnet50", "clip"]
        assert config.confidence_threshold == 0.7
        assert config.frame_sampling_rate == 2
        assert config.enable_blockchain_verification is True
    
    def test_detection_response_creation(self):
        """Test DetectionResponse model creation"""
        analysis_id = uuid.uuid4()
        
        response = DetectionResponse(
            analysis_id=analysis_id,
            status=DetectionStatus.PENDING,
            message="Analysis submitted successfully"
        )
        
        assert response.analysis_id == analysis_id
        assert response.status == DetectionStatus.PENDING
        assert response.message == "Analysis submitted successfully"
    
    def test_status_response_creation(self):
        """Test DetectionStatusResponse model creation"""
        analysis_id = uuid.uuid4()
        
        response = DetectionStatusResponse(
            analysis_id=analysis_id,
            status=DetectionStatus.PROCESSING,
            progress_percentage=45.5,
            current_stage=ProcessingStage.DETECTION_ANALYSIS,
            frames_processed=100,
            total_frames=220
        )
        
        assert response.analysis_id == analysis_id
        assert response.status == DetectionStatus.PROCESSING
        assert response.progress_percentage == 45.5
        assert response.current_stage == ProcessingStage.DETECTION_ANALYSIS
    
    def test_results_response_creation(self):
        """Test DetectionResultsResponse model creation"""
        analysis_id = uuid.uuid4()
        
        response = DetectionResultsResponse(
            analysis_id=analysis_id,
            status=DetectionStatus.COMPLETED,
            overall_confidence=0.85,
            detection_summary={"total_frames": 220, "suspicious_frames": 15},
            frame_analysis=[],
            suspicious_regions=[],
            total_frames=220,
            processing_time_seconds=45.2,
            detection_methods_used=["resnet50", "clip"],
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc)
        )
        
        assert response.analysis_id == analysis_id
        assert response.status == DetectionStatus.COMPLETED
        assert response.overall_confidence == 0.85
        assert response.total_frames == 220
    
    def test_video_file_validation(self):
        """Test video file validation function"""
        # Test valid file
        mock_file = Mock()
        mock_file.filename = "test_video.mp4"
        assert validate_video_file(mock_file) is True
        
        # Test invalid file
        mock_file.filename = "test_video.txt"
        with pytest.raises(ValueError, match="Unsupported file format"):
            validate_video_file(mock_file)
    
    def test_file_size_validation(self):
        """Test file size validation function"""
        # Test valid size
        assert validate_file_size(1000000, 2000000) is True
        
        # Test invalid size
        with pytest.raises(ValueError, match="File size.*exceeds maximum"):
            validate_file_size(3000000, 2000000)


class TestDetectionExceptions:
    """Test detection-specific exception classes"""
    
    def test_analysis_not_found_error(self):
        """Test AnalysisNotFoundError creation"""
        analysis_id = uuid.uuid4()
        error = AnalysisNotFoundError(analysis_id)
        
        assert error.analysis_id == analysis_id
        assert error.status_code == 404
        assert error.error_code == "ANALYSIS_NOT_FOUND"
        assert str(analysis_id) in error.message
    
    def test_video_validation_error(self):
        """Test VideoValidationError creation"""
        error = VideoValidationError(
            message="Invalid video format",
            filename="test.txt",
            file_size=1000,
            content_type="text/plain"
        )
        
        assert error.status_code == 400
        assert error.error_code == "VIDEO_VALIDATION_ERROR"
        assert error.details["filename"] == "test.txt"
    
    def test_unsupported_format_error(self):
        """Test UnsupportedVideoFormatError creation"""
        error = UnsupportedVideoFormatError(
            content_type="text/plain",
            filename="test.txt",
            allowed_formats=["mp4", "avi"]
        )
        
        assert error.status_code == 400
        assert "text/plain" in error.message
        assert "mp4" in error.message
    
    def test_size_exceeded_error(self):
        """Test VideoSizeExceededError creation"""
        error = VideoSizeExceededError(
            file_size=1000000,
            max_size=500000,
            filename="large_video.mp4"
        )
        
        assert error.status_code == 400
        assert "1.0MB" in error.message
        assert "0.5MB" in error.message


class TestAnalysisTracker:
    """Test AnalysisTracker functionality"""
    
    @pytest.fixture
    def tracker(self):
        """Create AnalysisTracker instance"""
        return AnalysisTracker()
    
    def test_create_analysis(self, tracker):
        """Test analysis creation"""
        config = DetectionConfig()
        analysis_id = tracker.create_analysis("test.mp4", 1000000, config)
        
        assert isinstance(analysis_id, uuid.UUID)
        assert analysis_id in tracker.analyses
        
        analysis = tracker.analyses[analysis_id]
        assert analysis["filename"] == "test.mp4"
        assert analysis["file_size"] == 1000000
        assert analysis["status"] == DetectionStatus.PENDING
    
    def test_get_analysis(self, tracker):
        """Test analysis retrieval"""
        config = DetectionConfig()
        analysis_id = tracker.create_analysis("test.mp4", 1000000, config)
        
        analysis = tracker.get_analysis(analysis_id)
        assert analysis["filename"] == "test.mp4"
        assert analysis["status"] == DetectionStatus.PENDING
    
    def test_get_nonexistent_analysis(self, tracker):
        """Test retrieval of nonexistent analysis"""
        analysis_id = uuid.uuid4()
        
        with pytest.raises(AnalysisNotFoundError):
            tracker.get_analysis(analysis_id)
    
    def test_update_analysis_status(self, tracker):
        """Test analysis status updates"""
        config = DetectionConfig()
        analysis_id = tracker.create_analysis("test.mp4", 1000000, config)
        
        tracker.update_analysis_status(
            analysis_id,
            DetectionStatus.PROCESSING,
            progress_percentage=50.0,
            current_stage=ProcessingStage.DETECTION_ANALYSIS
        )
        
        analysis = tracker.get_analysis(analysis_id)
        assert analysis["status"] == DetectionStatus.PROCESSING
        assert analysis["progress_percentage"] == 50.0
        assert analysis["current_stage"] == ProcessingStage.DETECTION_ANALYSIS
    
    def test_concurrent_limit(self, tracker):
        """Test concurrent analysis limit"""
        config = DetectionConfig()
        
        # Create analyses up to the limit
        for i in range(tracker.max_concurrent):
            analysis_id = tracker.create_analysis(f"test_{i}.mp4", 1000000, config)
            tracker.start_analysis(analysis_id)
        
        # Try to start one more
        analysis_id = tracker.create_analysis("test_overflow.mp4", 1000000, config)
        
        with pytest.raises(ConcurrentAnalysisLimitError):
            tracker.start_analysis(analysis_id)


class TestVideoProcessingService:
    """Test VideoProcessingService functionality"""
    
    @pytest.fixture
    def service(self):
        """Create VideoProcessingService instance"""
        return VideoProcessingService()
    
    @pytest.fixture
    def config(self):
        """Create DetectionConfig instance"""
        return DetectionConfig()
    
    async def test_initiate_analysis(self, service, config):
        """Test video analysis initiation"""
        analysis_id = await service.initiate_video_analysis(
            file_path="test_video.mp4",
            filename="test_video.mp4",
            file_size=1000000,
            config=config
        )
        
        assert isinstance(analysis_id, uuid.UUID)
        
        # Check that analysis was created
        status = await service.get_analysis_status(analysis_id)
        assert status["filename"] == "test_video.mp4"
        assert status["status"] == DetectionStatus.PROCESSING
    
    async def test_get_analysis_status(self, service, config):
        """Test analysis status retrieval"""
        analysis_id = await service.initiate_video_analysis(
            file_path="test_video.mp4",
            filename="test_video.mp4",
            file_size=1000000,
            config=config
        )
        
        status = await service.get_analysis_status(analysis_id)
        assert status["analysis_id"] == analysis_id
        assert "status" in status
        assert "progress_percentage" in status
    
    async def test_get_nonexistent_status(self, service):
        """Test status retrieval for nonexistent analysis"""
        analysis_id = uuid.uuid4()
        
        with pytest.raises(AnalysisNotFoundError):
            await service.get_analysis_status(analysis_id)
    
    async def test_cancel_analysis(self, service, config):
        """Test analysis cancellation"""
        analysis_id = await service.initiate_video_analysis(
            file_path="test_video.mp4",
            filename="test_video.mp4",
            file_size=1000000,
            config=config
        )
        
        success = await service.cancel_analysis(analysis_id)
        assert success is True
        
        status = await service.get_analysis_status(analysis_id)
        assert status["status"] == DetectionStatus.CANCELLED
    
    def test_service_stats(self, service):
        """Test service statistics"""
        stats = service.get_service_stats()
        
        assert "total_analyses" in stats
        assert "active_analyses" in stats
        assert "completed_analyses" in stats
        assert "max_concurrent" in stats


class TestDetectionAPIEndpoints:
    """Test detection API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_upload_video_success(self, client):
        """Test successful video upload"""
        # Create mock video file
        video_content = b"fake video content"
        files = {"file": ("test_video.mp4", BytesIO(video_content), "video/mp4")}
        data = {"options": "{}", "priority": "5"}
        
        with patch('app.api.v1.endpoints.detect.get_video_processing_service') as mock_service:
            mock_processing_service = AsyncMock()
            mock_service.return_value = mock_processing_service
            
            # Mock successful analysis initiation
            analysis_id = uuid.uuid4()
            mock_processing_service.initiate_video_analysis.return_value = analysis_id
            
            response = client.post("/v1/detect/video", files=files, data=data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["analysis_id"] == str(analysis_id)
            assert data["status"] == "pending"
            assert data["message"] == "Video uploaded successfully and analysis initiated"
    
    def test_upload_video_invalid_format(self, client):
        """Test video upload with invalid format"""
        # Create mock file with invalid format
        files = {"file": ("test_video.txt", BytesIO(b"fake content"), "text/plain")}
        data = {"options": "{}"}
        
        response = client.post("/v1/detect/video", files=files, data=data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "UNSUPPORTED_FORMAT"
    
    def test_upload_video_large_file(self, client):
        """Test video upload with file size exceeded"""
        # Create mock large file
        large_content = b"x" * (600 * 1024 * 1024)  # 600MB
        files = {"file": ("large_video.mp4", BytesIO(large_content), "video/mp4")}
        data = {"options": "{}"}
        
        response = client.post("/v1/detect/video", files=files, data=data)
        
        assert response.status_code == 413
        data = response.json()
        assert data["error"]["code"] == "FILE_SIZE_EXCEEDED"
    
    def test_get_status_success(self, client):
        """Test successful status retrieval"""
        analysis_id = uuid.uuid4()
        
        with patch('app.api.v1.endpoints.detect.get_video_processing_service') as mock_service:
            mock_processing_service = AsyncMock()
            mock_service.return_value = mock_processing_service
            
            # Mock status data
            status_data = {
                "analysis_id": analysis_id,
                "status": DetectionStatus.PROCESSING,
                "progress_percentage": 45.5,
                "current_stage": ProcessingStage.DETECTION_ANALYSIS,
                "frames_processed": 100,
                "total_frames": 220,
                "last_updated": datetime.now(timezone.utc)
            }
            mock_processing_service.get_analysis_status.return_value = status_data
            
            response = client.get(f"/v1/detect/status/{analysis_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["analysis_id"] == str(analysis_id)
            assert data["status"] == "processing"
            assert data["progress_percentage"] == 45.5
    
    def test_get_status_not_found(self, client):
        """Test status retrieval for nonexistent analysis"""
        analysis_id = uuid.uuid4()
        
        with patch('app.api.v1.endpoints.detect.get_video_processing_service') as mock_service:
            mock_processing_service = AsyncMock()
            mock_service.return_value = mock_processing_service
            
            # Mock analysis not found
            mock_processing_service.get_analysis_status.side_effect = AnalysisNotFoundError(analysis_id)
            
            response = client.get(f"/v1/detect/status/{analysis_id}")
            
            assert response.status_code == 404
            data = response.json()
            assert data["error"]["code"] == "ANALYSIS_NOT_FOUND"
    
    def test_get_results_success(self, client):
        """Test successful results retrieval"""
        analysis_id = uuid.uuid4()
        
        with patch('app.api.v1.endpoints.detect.get_video_processing_service') as mock_service:
            mock_processing_service = AsyncMock()
            mock_service.return_value = mock_processing_service
            
            # Mock results data
            results_data = {
                "analysis_id": analysis_id,
                "status": DetectionStatus.COMPLETED,
                "overall_confidence": 0.85,
                "detection_summary": {"total_frames": 220, "suspicious_frames": 15},
                "frame_analysis": [],
                "suspicious_regions": [],
                "total_frames": 220,
                "processing_time_seconds": 45.2,
                "detection_methods_used": ["resnet50", "clip"],
                "blockchain_hash": "abc123",
                "verification_status": "verified",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat()
            }
            mock_processing_service.get_analysis_results.return_value = results_data
            
            response = client.get(f"/v1/detect/results/{analysis_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["analysis_id"] == str(analysis_id)
            assert data["status"] == "completed"
            assert data["overall_confidence"] == 0.85
    
    def test_get_results_not_found(self, client):
        """Test results retrieval for nonexistent analysis"""
        analysis_id = uuid.uuid4()
        
        with patch('app.api.v1.endpoints.detect.get_video_processing_service') as mock_service:
            mock_processing_service = AsyncMock()
            mock_service.return_value = mock_processing_service
            
            # Mock analysis not found
            mock_processing_service.get_analysis_results.side_effect = AnalysisNotFoundError(analysis_id)
            
            response = client.get(f"/v1/detect/results/{analysis_id}")
            
            assert response.status_code == 404
            data = response.json()
            assert data["error"]["code"] == "ANALYSIS_NOT_FOUND"
    
    def test_cancel_analysis_success(self, client):
        """Test successful analysis cancellation"""
        analysis_id = uuid.uuid4()
        
        with patch('app.api.v1.endpoints.detect.get_video_processing_service') as mock_service:
            mock_processing_service = AsyncMock()
            mock_service.return_value = mock_processing_service
            
            # Mock successful cancellation
            mock_processing_service.cancel_analysis.return_value = True
            
            response = client.delete(f"/v1/detect/analysis/{analysis_id}")
            
            assert response.status_code == 204
    
    def test_get_service_stats(self, client):
        """Test service statistics endpoint"""
        with patch('app.api.v1.endpoints.detect.get_video_processing_service') as mock_service:
            mock_processing_service = AsyncMock()
            mock_service.return_value = mock_processing_service
            
            # Mock service stats
            stats = {
                "total_analyses": 10,
                "active_analyses": 2,
                "completed_analyses": 8,
                "failed_analyses": 0
            }
            mock_processing_service.get_service_stats.return_value = stats
            
            response = client.get("/v1/detect/stats")
            
            assert response.status_code == 200
            data = response.json()
            assert "service_stats" in data
            assert "configuration" in data
            assert "timestamp" in data


class TestConfiguration:
    """Test configuration settings"""
    
    def test_detection_config_creation(self):
        """Test DetectionConfig creation and validation"""
        config = ConfigClass()
        
        assert config.max_file_size_bytes == 524288000  # 500MB
        assert "mp4" in config.allowed_video_formats
        assert config.max_processing_time_minutes == 30
        assert config.max_concurrent_analyses == 10
    
    def test_config_validation(self):
        """Test configuration validation"""
        validation_results = detection_settings.validate_configuration()
        
        assert "detection" in validation_results
        assert "processing" in validation_results
        assert "api" in validation_results
        assert "overall_valid" in validation_results
    
    def test_config_summary(self):
        """Test configuration summary generation"""
        summary = detection_settings.get_complete_config_summary()
        
        assert "detection" in summary
        assert "processing" in summary
        assert "api" in summary
        assert "validation" in summary


class TestIntegration:
    """Integration tests for complete workflow"""
    
    async def test_complete_detection_workflow(self):
        """Test complete detection workflow from upload to results"""
        # This would test the complete workflow in a real test environment
        # For now, we'll test the individual components work together
        
        service = VideoProcessingService()
        config = DetectionConfig()
        
        # Initiate analysis
        analysis_id = await service.initiate_video_analysis(
            file_path="test_video.mp4",
            filename="test_video.mp4",
            file_size=1000000,
            config=config
        )
        
        # Check status
        status = await service.get_analysis_status(analysis_id)
        assert status["status"] == DetectionStatus.PROCESSING
        
        # Cancel analysis
        success = await service.cancel_analysis(analysis_id)
        assert success is True
        
        # Check final status
        final_status = await service.get_analysis_status(analysis_id)
        assert final_status["status"] == DetectionStatus.CANCELLED


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
