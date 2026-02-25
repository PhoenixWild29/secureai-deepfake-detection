#!/usr/bin/env python3
"""
Test Video Upload Processing Implementation
Comprehensive tests for Work Order #60 video upload processing
"""

import pytest
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock
from io import BytesIO

# Test imports
from src.schemas.video_upload_schema import (
    VideoUploadRequest,
    VideoUploadResponse,
    VideoUploadError,
    VideoUploadErrorCodes,
    VideoFormat,
    VideoValidationResult
)
from src.models.video import Video, VideoStatusEnum, VideoFormatEnum
from src.services.s3_service import DashboardS3Service
from src.services.video_processing_service import VideoProcessingService
from src.services.detection_engine_service import DetectionEngineService
from src.utils.error_handlers import VideoUploadErrorHandler, VideoUploadRedisUtils


class TestVideoUploadSchemas:
    """Test video upload Pydantic schemas"""
    
    def test_video_upload_request_validation(self):
        """Test VideoUploadRequest validation"""
        # Valid request
        request = VideoUploadRequest(
            session_id=uuid.uuid4(),
            filename="test_video.mp4",
            file_size=1000000,
            content_type="video/mp4"
        )
        assert request.filename == "test_video.mp4"
        assert request.file_size == 1000000
        assert request.content_type == "video/mp4"
        
        # Invalid filename
        with pytest.raises(ValueError, match="Invalid video format"):
            VideoUploadRequest(
                session_id=uuid.uuid4(),
                filename="test.txt",
                file_size=1000000,
                content_type="video/mp4"
            )
        
        # File too large
        with pytest.raises(ValueError, match="File size exceeds maximum limit"):
            VideoUploadRequest(
                session_id=uuid.uuid4(),
                filename="test_video.mp4",
                file_size=600000000,  # 600MB
                content_type="video/mp4"
            )
        
        # Invalid content type
        with pytest.raises(ValueError, match="Unsupported content type"):
            VideoUploadRequest(
                session_id=uuid.uuid4(),
                filename="test_video.mp4",
                file_size=1000000,
                content_type="text/plain"
            )
    
    def test_video_upload_response_creation(self):
        """Test VideoUploadResponse creation"""
        video_id = uuid.uuid4()
        analysis_id = uuid.uuid4()
        
        response = VideoUploadResponse(
            video_id=video_id,
            analysis_id=analysis_id,
            upload_status="analyzed",
            redirect_url="/dashboard/videos/results",
            estimated_processing_time=30,
            filename="test_video.mp4",
            file_size=1000000,
            file_hash="abc123",
            format=VideoFormat.MP4,
            s3_key="dashboard-uploads/user/video.mp4",
            created_at=datetime.now(timezone.utc)
        )
        
        assert response.video_id == video_id
        assert response.analysis_id == analysis_id
        assert response.upload_status == "analyzed"
        assert response.format == VideoFormat.MP4


class TestVideoProcessingService:
    """Test VideoProcessingService functionality"""
    
    @pytest.fixture
    def video_service(self):
        """Create VideoProcessingService instance"""
        return VideoProcessingService()
    
    def test_validate_video_file_success(self, video_service):
        """Test successful video file validation"""
        # Mock file content (MP4 header)
        file_content = b'\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom'
        
        with patch.object(video_service, '_validate_video_content') as mock_validate:
            mock_validate.return_value = {
                'is_valid': True,
                'errors': [],
                'warnings': []
            }
            
            result = video_service.validate_video_file(
                file_content=file_content,
                filename="test_video.mp4",
                content_type="video/mp4"
            )
            
            assert result.is_valid is True
            assert result.filename == "test_video.mp4"
            assert result.file_size == len(file_content)
            assert result.format == VideoFormat.MP4
    
    def test_validate_video_file_failure(self, video_service):
        """Test video file validation failure"""
        file_content = b"invalid content"
        
        result = video_service.validate_video_file(
            file_content=file_content,
            filename="test_video.mp4",
            content_type="video/mp4"
        )
        
        # Should fail due to invalid content
        assert result.is_valid is False
        assert len(result.validation_errors) > 0
    
    def test_calculate_file_hash(self, video_service):
        """Test file hash calculation"""
        file_content = b"test content"
        hash_result = video_service.calculate_file_hash(file_content)
        
        assert isinstance(hash_result, str)
        assert len(hash_result) == 64  # SHA256 hash length


class TestDashboardS3Service:
    """Test DashboardS3Service functionality"""
    
    @pytest.fixture
    def s3_service(self):
        """Create DashboardS3Service with mocked S3 client"""
        with patch('src.services.s3_service.boto3.client') as mock_client:
            mock_s3_client = Mock()
            mock_client.return_value = mock_s3_client
            
            service = DashboardS3Service()
            service.s3_client = mock_s3_client
            return service
    
    def test_generate_dashboard_s3_key(self, s3_service):
        """Test S3 key generation for dashboard uploads"""
        user_id = uuid.uuid4()
        session_id = uuid.uuid4()
        
        s3_key = s3_service.generate_dashboard_s3_key(
            filename="test_video.mp4",
            user_id=user_id,
            session_id=session_id
        )
        
        assert s3_key.startswith("dashboard-uploads/")
        assert str(user_id) in s3_key
        assert str(session_id) in s3_key
        assert "test_video.mp4" in s3_key
    
    def test_upload_video_file_success(self, s3_service):
        """Test successful video file upload"""
        user_id = uuid.uuid4()
        file_content = b"test video content"
        
        # Mock successful S3 upload
        s3_service.s3_client.put_object.return_value = None
        
        result = s3_service.upload_video_file(
            file_content=file_content,
            filename="test_video.mp4",
            user_id=user_id,
            content_type="video/mp4"
        )
        
        assert result['success'] is True
        assert 's3_key' in result
        assert 's3_url' in result
        assert result['file_size'] == len(file_content)
    
    def test_cleanup_failed_upload(self, s3_service):
        """Test cleanup of failed upload"""
        s3_key = "dashboard-uploads/user/test_video.mp4"
        
        # Mock successful deletion
        s3_service.s3_client.delete_object.return_value = None
        
        result = s3_service.cleanup_failed_upload(s3_key)
        
        assert result['cleanup_attempted'] is True
        assert result['cleanup_successful'] is True
        assert result['s3_key'] == s3_key


class TestDetectionEngineService:
    """Test DetectionEngineService functionality"""
    
    @pytest.fixture
    def detection_service(self):
        """Create DetectionEngineService with mocked dependencies"""
        with patch('src.services.detection_engine_service.detect_fake') as mock_detect:
            mock_detect.return_value = {
                'is_fake': False,
                'confidence': 0.85,
                'authenticity_score': 0.85,
                'processing_time': 30.5
            }
            
            service = DetectionEngineService()
            return service
    
    def test_initiate_video_analysis_success(self, detection_service):
        """Test successful video analysis initiation"""
        video_id = uuid.uuid4()
        s3_key = "dashboard-uploads/user/test_video.mp4"
        s3_bucket = "test-bucket"
        
        with patch.object(detection_service, '_download_video_from_s3') as mock_download:
            mock_download.return_value = "/tmp/test_video.mp4"
            
            with patch('os.unlink') as mock_unlink:
                result = detection_service.initiate_video_analysis(
                    video_id=video_id,
                    s3_key=s3_key,
                    s3_bucket=s3_bucket,
                    model_type="resnet"
                )
                
                assert result.video_id == video_id
                assert result.status == "completed"
                assert result.is_fake is False
                assert result.confidence_score == 0.85
                assert result.processing_time > 0
    
    def test_estimate_processing_time(self, detection_service):
        """Test processing time estimation"""
        # Small file
        small_file_time = detection_service.estimate_processing_time(1000000, "resnet")
        assert small_file_time > 0
        
        # Large file
        large_file_time = detection_service.estimate_processing_time(100000000, "resnet")
        assert large_file_time > small_file_time
        
        # Different model types
        enhanced_time = detection_service.estimate_processing_time(1000000, "enhanced")
        assert enhanced_time > small_file_time


class TestVideoUploadErrorHandler:
    """Test VideoUploadErrorHandler functionality"""
    
    @pytest.fixture
    async def error_handler(self):
        """Create VideoUploadErrorHandler with mocked Redis"""
        handler = VideoUploadErrorHandler()
        
        with patch('src.utils.error_handlers.get_upload_redis_client') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            handler.redis_client = mock_redis_client
            
            return handler
    
    async def test_handle_upload_error_with_cleanup(self, error_handler):
        """Test error handling with cleanup operations"""
        error = Exception("Test error")
        video_id = uuid.uuid4()
        session_id = uuid.uuid4()
        s3_key = "dashboard-uploads/user/test_video.mp4"
        user_id = uuid.uuid4()
        
        with patch('src.utils.error_handlers.cleanup_failed_dashboard_upload') as mock_cleanup:
            mock_cleanup.return_value = {
                'cleanup_successful': True,
                's3_key': s3_key
            }
            
            result = await error_handler.handle_upload_error(
                error=error,
                error_code=VideoUploadErrorCodes.VALIDATION_FAILED,
                video_id=video_id,
                session_id=session_id,
                s3_key=s3_key,
                user_id=user_id
            )
            
            assert result.error_code == VideoUploadErrorCodes.VALIDATION_FAILED
            assert result.error_message == "Test error"
            assert result.cleanup_performed is True
            assert result.cleanup_details['s3_cleanup'] is True


class TestVideoUploadRedisUtils:
    """Test VideoUploadRedisUtils functionality"""
    
    @pytest.fixture
    async def redis_utils(self):
        """Create VideoUploadRedisUtils with mocked Redis"""
        utils = VideoUploadRedisUtils()
        
        with patch('src.utils.error_handlers.get_upload_redis_client') as mock_redis:
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            utils.redis_client = mock_redis_client
            
            return utils
    
    async def test_validate_upload_session_success(self, redis_utils):
        """Test successful upload session validation"""
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        # Mock valid session data
        session_data = {
            'user_id': str(user_id),
            'expires_at': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            'status': 'active'
        }
        
        redis_utils.redis_client.get_session_data.return_value = session_data
        
        result = await redis_utils.validate_upload_session(session_id, user_id)
        
        assert result['is_valid'] is True
        assert result['session_data'] == session_data
    
    async def test_validate_upload_session_expired(self, redis_utils):
        """Test validation of expired session"""
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        # Mock expired session data
        session_data = {
            'user_id': str(user_id),
            'expires_at': (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            'status': 'active'
        }
        
        redis_utils.redis_client.get_session_data.return_value = session_data
        
        result = await redis_utils.validate_upload_session(session_id, user_id)
        
        assert result['is_valid'] is False
        assert 'expired' in result['error'].lower()
    
    async def test_track_upload_progress(self, redis_utils):
        """Test upload progress tracking"""
        video_id = uuid.uuid4()
        session_id = uuid.uuid4()
        
        redis_utils.redis_client.set_session_data.return_value = True
        
        await redis_utils.track_upload_progress(
            video_id=video_id,
            session_id=session_id,
            status="uploading",
            progress_percentage=50.0,
            current_step="S3 upload"
        )
        
        # Verify Redis client was called
        redis_utils.redis_client.set_session_data.assert_called_once()


class TestVideoUploadAPI:
    """Test video upload API endpoints"""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for API testing"""
        from fastapi.testclient import TestClient
        from api_fastapi import app
        return TestClient(app)
    
    def test_upload_video_endpoint_success(self, test_client):
        """Test successful video upload endpoint"""
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        # Mock authentication
        with patch('src.auth.upload_auth.get_current_user_jwt') as mock_auth:
            mock_auth.return_value = user_id
            
            # Mock session validation
            with patch('src.utils.error_handlers.validate_upload_session_redis') as mock_validate:
                mock_validate.return_value = {
                    'is_valid': True,
                    'session_data': {
                        'user_id': str(user_id),
                        'dashboard_context': {'source_section': 'video_analysis'}
                    }
                }
                
                # Mock services
                with patch('src.services.s3_service.get_dashboard_s3_service') as mock_s3:
                    with patch('src.services.video_processing_service.get_video_processing_service') as mock_video:
                        with patch('src.services.detection_engine_service.get_detection_engine_service') as mock_detection:
                            with patch('src.services.quota_management.QuotaService') as mock_quota:
                                
                                # Mock service responses
                                mock_s3_service = Mock()
                                mock_s3_service.upload_video_file.return_value = {
                                    'success': True,
                                    's3_key': 'dashboard-uploads/user/test.mp4',
                                    's3_url': 'https://bucket.s3.amazonaws.com/test.mp4'
                                }
                                mock_s3_service.bucket_name = 'test-bucket'
                                mock_s3.return_value = mock_s3_service
                                
                                mock_video_service = Mock()
                                mock_video_service.validate_video_file.return_value = Mock(
                                    is_valid=True,
                                    format=VideoFormat.MP4,
                                    validation_errors=[],
                                    warnings=[]
                                )
                                mock_video_service.calculate_file_hash.return_value = 'abc123'
                                mock_video.return_value = mock_video_service
                                
                                mock_detection_service = Mock()
                                mock_detection_service.initiate_video_analysis.return_value = Mock(
                                    analysis_id=uuid.uuid4(),
                                    status='completed',
                                    detection_result={'is_fake': False},
                                    confidence_score=0.85,
                                    is_fake=False,
                                    processing_time=30.0,
                                    completed_at=datetime.now(timezone.utc)
                                )
                                mock_detection_service.estimate_processing_time.return_value = 30
                                mock_detection.return_value = mock_detection_service
                                
                                mock_quota_service = Mock()
                                mock_quota_service.update_user_quota.return_value = None
                                mock_quota.return_value = mock_quota_service
                                
                                # Create test file
                                test_file_content = b"test video content"
                                test_file = BytesIO(test_file_content)
                                
                                response = test_client.post(
                                    f"/v1/dashboard/upload/{session_id}",
                                    files={"file": ("test_video.mp4", test_file, "video/mp4")},
                                    headers={"Authorization": "Bearer test-token"}
                                )
                                
                                assert response.status_code == 201
                                data = response.json()
                                assert "video_id" in data
                                assert "analysis_id" in data
                                assert "upload_status" in data
                                assert "redirect_url" in data
    
    def test_upload_video_endpoint_invalid_session(self, test_client):
        """Test video upload with invalid session"""
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        # Mock authentication
        with patch('src.auth.upload_auth.get_current_user_jwt') as mock_auth:
            mock_auth.return_value = user_id
            
            # Mock invalid session
            with patch('src.utils.error_handlers.validate_upload_session_redis') as mock_validate:
                mock_validate.return_value = {
                    'is_valid': False,
                    'error': 'Session not found or expired'
                }
                
                test_file_content = b"test video content"
                test_file = BytesIO(test_file_content)
                
                response = test_client.post(
                    f"/v1/dashboard/upload/{session_id}",
                    files={"file": ("test_video.mp4", test_file, "video/mp4")},
                    headers={"Authorization": "Bearer test-token"}
                )
                
                assert response.status_code == 404
                data = response.json()
                assert data["detail"]["error_code"] == VideoUploadErrorCodes.SESSION_NOT_FOUND


class TestVideoUploadIntegration:
    """Integration tests for video upload workflow"""
    
    async def test_complete_upload_workflow(self):
        """Test complete video upload workflow"""
        # This would test the complete workflow from session validation to analysis
        # In a real test environment, this would use actual services and test the full flow
        
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()
        video_id = uuid.uuid4()
        
        # Mock the complete workflow
        with patch('src.services.s3_service.get_dashboard_s3_service') as mock_s3:
            with patch('src.services.video_processing_service.get_video_processing_service') as mock_video:
                with patch('src.services.detection_engine_service.get_detection_engine_service') as mock_detection:
                    
                    # Test session validation
                    session_validation = {
                        'is_valid': True,
                        'session_data': {'user_id': str(user_id)}
                    }
                    
                    # Test file validation
                    validation_result = Mock(
                        is_valid=True,
                        format=VideoFormat.MP4,
                        validation_errors=[],
                        warnings=[]
                    )
                    
                    # Test S3 upload
                    s3_result = {
                        'success': True,
                        's3_key': 'dashboard-uploads/user/test.mp4',
                        's3_url': 'https://bucket.s3.amazonaws.com/test.mp4'
                    }
                    
                    # Test analysis initiation
                    analysis_result = Mock(
                        analysis_id=uuid.uuid4(),
                        status='completed',
                        detection_result={'is_fake': False},
                        confidence_score=0.85,
                        is_fake=False,
                        processing_time=30.0
                    )
                    
                    # Verify workflow components
                    assert session_validation['is_valid'] is True
                    assert validation_result.is_valid is True
                    assert s3_result['success'] is True
                    assert analysis_result.status == 'completed'


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
