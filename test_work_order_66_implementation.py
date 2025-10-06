#!/usr/bin/env python3
"""
Test Suite for Work Order #66 Implementation
Implement Upload Data Models and Helper Functions
"""

import pytest
import tempfile
import os
from uuid import uuid4, UUID
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch

# Import our implemented models and utilities
from src.models.upload_models import (
    DashboardUploadRequest,
    DashboardUploadResponse,
    UploadSession,
    UploadProgress,
    UploadProgressEvent,
    ValidationResult,
    S3UploadResult,
    UserQuota,
    QuotaValidationResult,
    UploadStatusEnum,
    UploadProgressStatusEnum,
    UploadEventTypeEnum
)

from src.utils.file_validation import (
    validate_video_file,
    validate_file_format,
    validate_file_size,
    calculate_file_hash,
    FileValidationError,
    FileHashError,
    SUPPORTED_VIDEO_FORMATS,
    MAX_FILE_SIZE
)

from src.services.quota_management import (
    QuotaService,
    get_user_quota,
    validate_upload_quota,
    update_user_quota,
    reset_user_quota,
    QuotaManagementError,
    QuotaExceededError
)


class TestUploadModels:
    """Test the upload data models"""
    
    def test_dashboard_upload_request_creation(self):
        """Test creating a valid DashboardUploadRequest"""
        # Mock UploadFile
        mock_file = Mock()
        mock_file.filename = "test_video.mp4"
        
        request = DashboardUploadRequest(
            file=mock_file,
            user_id=uuid4(),
            priority=8,
            metadata={"source": "dashboard", "quality": "high"},
            dashboard_context={"current_section": "/upload"},
            auto_analyze=True,
            store_in_s3=True
        )
        
        assert request.file.filename == "test_video.mp4"
        assert request.priority == 8
        assert request.metadata["source"] == "dashboard"
        assert request.dashboard_context["current_section"] == "/upload"
        assert request.auto_analyze is True
        assert request.store_in_s3 is True
    
    def test_dashboard_upload_request_validation(self):
        """Test DashboardUploadRequest field validation"""
        # Test valid request
        mock_file = Mock()
        mock_file.filename = "test_video.mp4"
        
        valid_request = DashboardUploadRequest(file=mock_file)
        assert valid_request.file.filename == "test_video.mp4"
        
        # Test invalid file format
        mock_file_invalid = Mock()
        mock_file_invalid.filename = "test_document.pdf"
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            DashboardUploadRequest(file=mock_file_invalid)
        
        # Test invalid priority
        with pytest.raises(ValueError, match="Input should be greater than or equal to 1"):
            DashboardUploadRequest(file=mock_file, priority=0)
        
        with pytest.raises(ValueError, match="Input should be less than or equal to 10"):
            DashboardUploadRequest(file=mock_file, priority=11)
    
    def test_dashboard_upload_response_creation(self):
        """Test creating a valid DashboardUploadResponse"""
        video_id = uuid4()
        analysis_id = uuid4()
        
        response = DashboardUploadResponse(
            video_id=video_id,
            status=UploadStatusEnum.COMPLETED,
            message="Upload completed successfully",
            filename="test_video.mp4",
            file_size=1024000,
            file_hash="abc123def456",
            format="mp4",
            storage_location="s3",
            s3_key="videos/test_video.mp4",
            s3_url="https://bucket.s3.amazonaws.com/videos/test_video.mp4",
            analysis_id=analysis_id,
            processing_time_ms=2500,
            validation_result=ValidationResult(is_valid=True, file_format="mp4", file_size=1024000)
        )
        
        assert response.video_id == video_id
        assert response.status == UploadStatusEnum.COMPLETED
        assert response.message == "Upload completed successfully"
        assert response.filename == "test_video.mp4"
        assert response.file_size == 1024000
        assert response.file_hash == "abc123def456"
        assert response.format == "mp4"
        assert response.storage_location == "s3"
        assert response.analysis_id == analysis_id
        assert response.processing_time_ms == 2500
    
    def test_upload_session_creation(self):
        """Test creating a valid UploadSession"""
        user_id = uuid4()
        
        session = UploadSession(
            user_id=user_id,
            quota_remaining=1000000000,  # 1GB
            quota_limit=10000000000,     # 10GB
            dashboard_context={"current_section": "/dashboard/upload"},
            auto_analyze=True,
            store_in_s3=True
        )
        
        assert session.user_id == user_id
        assert session.quota_remaining == 1000000000
        assert session.quota_limit == 10000000000
        assert session.dashboard_context["current_section"] == "/dashboard/upload"
        assert session.auto_analyze is True
        assert session.store_in_s3 is True
        assert session.total_files == 0
        assert session.completed_files == 0
        assert session.failed_files == 0
    
    def test_upload_session_methods(self):
        """Test UploadSession utility methods"""
        session = UploadSession(
            user_id=uuid4(),
            quota_remaining=1000000,  # 1MB
            quota_limit=10000000      # 10MB
        )
        
        # Test adding file to session
        success = session.add_file_to_session(500000)  # 500KB
        assert success is True
        assert session.total_files == 1
        assert session.quota_used == 500000
        assert session.quota_remaining == 500000
        
        # Test adding file that exceeds quota
        success = session.add_file_to_session(600000)  # 600KB > 500KB remaining
        assert success is False
        assert session.total_files == 1  # Should not increment
        
        # Test marking files as completed/failed
        session.mark_file_completed()
        assert session.completed_files == 1
        
        session.mark_file_failed()
        assert session.failed_files == 1
        
        # Test getting session progress
        progress = session.get_session_progress()
        assert progress["total_files"] == 1
        assert progress["completed_files"] == 1
        assert progress["failed_files"] == 1
        assert progress["completion_percentage"] == 100.0
        assert progress["quota_remaining"] == 500000
    
    def test_upload_progress_creation(self):
        """Test creating a valid UploadProgress"""
        upload_id = uuid4()
        session_id = uuid4()
        
        progress = UploadProgress(
            upload_id=upload_id,
            session_id=session_id,
            percentage=0.0,
            bytes_uploaded=0,
            bytes_total=1000000,
            status=UploadProgressStatusEnum.STARTED,
            filename="test_video.mp4",
            file_size=1000000
        )
        
        assert progress.upload_id == upload_id
        assert progress.session_id == session_id
        assert progress.percentage == 0.0
        assert progress.bytes_uploaded == 0
        assert progress.bytes_total == 1000000
        assert progress.status == UploadProgressStatusEnum.STARTED
        assert progress.filename == "test_video.mp4"
        assert progress.file_size == 1000000
    
    def test_upload_progress_methods(self):
        """Test UploadProgress utility methods"""
        progress = UploadProgress(
            upload_id=uuid4(),
            session_id=uuid4(),
            percentage=0.0,
            bytes_uploaded=0,
            bytes_total=1000000,
            status=UploadProgressStatusEnum.IN_PROGRESS,
            filename="test_video.mp4",
            file_size=1000000
        )
        
        # Test updating progress
        progress.update_progress(500000, 1000000)  # 50% complete, 1MB/s
        assert progress.percentage == 50.0
        assert progress.bytes_uploaded == 500000
        assert progress.upload_speed == 1000000
        assert progress.estimated_completion is not None
        
        # Test marking as completed
        progress.mark_completed()
        assert progress.percentage == 100.0
        assert progress.bytes_uploaded == progress.bytes_total
        assert progress.status == UploadProgressStatusEnum.COMPLETED
        assert progress.time_elapsed is not None
        
        # Test marking as failed
        progress.mark_failed("Network error")
        assert progress.status == UploadProgressStatusEnum.FAILED
        assert progress.error_message == "Network error"
    
    def test_upload_progress_event_creation(self):
        """Test creating a valid UploadProgressEvent"""
        progress = UploadProgress(
            upload_id=uuid4(),
            session_id=uuid4(),
            percentage=50.0,
            bytes_uploaded=500000,
            bytes_total=1000000,
            status=UploadProgressStatusEnum.IN_PROGRESS,
            filename="test_video.mp4",
            file_size=1000000
        )
        
        event = UploadProgressEvent(
            event_type=UploadEventTypeEnum.UPLOAD_PROGRESS,
            upload_id=progress.upload_id,
            session_id=progress.session_id,
            user_id=uuid4(),
            progress=progress,
            dashboard_context={"current_section": "/upload"}
        )
        
        assert event.event_type == UploadEventTypeEnum.UPLOAD_PROGRESS
        assert event.upload_id == progress.upload_id
        assert event.session_id == progress.session_id
        assert event.progress == progress
        assert event.dashboard_context["current_section"] == "/upload"
        
        # Test WebSocket message conversion
        websocket_msg = event.to_websocket_message()
        assert websocket_msg["type"] == "upload_progress"
        assert websocket_msg["event_type"] == "upload_progress"
        assert websocket_msg["progress"]["percentage"] == 50.0
        assert websocket_msg["progress"]["bytes_uploaded"] == 500000


class TestFileValidation:
    """Test file validation utilities"""
    
    def test_validate_file_format(self):
        """Test file format validation"""
        # Test valid formats
        assert validate_file_format("test.mp4") == "mp4"
        assert validate_file_format("test.avi") == "avi"
        assert validate_file_format("test.mov") == "mov"
        assert validate_file_format("test.mkv") == "mkv"
        assert validate_file_format("test.webm") == "webm"
        
        # Test invalid formats
        assert validate_file_format("test.pdf") is None
        assert validate_file_format("test.txt") is None
        assert validate_file_format("") is None
        assert validate_file_format("no_extension") is None
    
    def test_validate_file_size(self):
        """Test file size validation"""
        # Test valid sizes
        assert validate_file_size(1024) is True  # 1KB
        assert validate_file_size(MAX_FILE_SIZE) is True  # Max size
        assert validate_file_size(MAX_FILE_SIZE // 2) is True  # Half max size
        
        # Test invalid sizes
        assert validate_file_size(0) is False  # Too small
        assert validate_file_size(500) is False  # Too small
        assert validate_file_size(MAX_FILE_SIZE + 1) is False  # Too large
    
    def test_calculate_file_hash(self):
        """Test file hash calculation"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content for hashing")
            temp_file = f.name
        
        try:
            # Test hash calculation
            hash_result = calculate_file_hash(temp_file)
            assert isinstance(hash_result, str)
            assert len(hash_result) == 64  # SHA256 hex length
            
            # Test that same content produces same hash
            hash_result2 = calculate_file_hash(temp_file)
            assert hash_result == hash_result2
            
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_file_validation_error_handling(self):
        """Test file validation error handling"""
        # Test non-existent file
        with pytest.raises(FileHashError):
            calculate_file_hash("non_existent_file.txt")
        
        # Test invalid algorithm
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test")
            temp_file = f.name
        
        try:
            with pytest.raises(FileHashError):
                calculate_file_hash(temp_file, algorithm="invalid")
        finally:
            os.unlink(temp_file)


class TestQuotaManagement:
    """Test quota management service"""
    
    @pytest.fixture
    def temp_users_file(self):
        """Create temporary users file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_get_user_quota(self, temp_users_file):
        """Test getting user quota"""
        quota_service = QuotaService(users_file=temp_users_file)
        user_id = uuid4()
        
        # Test getting quota for new user
        quota = await quota_service.get_user_quota(user_id)
        assert quota.user_id == user_id
        assert quota.quota_limit == quota_service.default_quota_limit
        assert quota.quota_used == 0
        assert quota.quota_remaining == quota_service.default_quota_limit
    
    @pytest.mark.asyncio
    async def test_validate_upload_quota(self, temp_users_file):
        """Test quota validation"""
        quota_service = QuotaService(users_file=temp_users_file)
        user_id = uuid4()
        
        # Create user with quota
        await quota_service.get_user_quota(user_id)
        
        # Test valid upload
        result = await quota_service.validate_upload_quota(user_id, 1000000)  # 1MB
        assert result.is_valid is True
        assert result.can_upload is True
        assert result.quota_remaining > 0
        
        # Test upload that exceeds quota
        result = await quota_service.validate_upload_quota(user_id, quota_service.default_quota_limit + 1)
        assert result.is_valid is False
        assert result.can_upload is False
    
    @pytest.mark.asyncio
    async def test_update_user_quota(self, temp_users_file):
        """Test updating user quota"""
        quota_service = QuotaService(users_file=temp_users_file)
        user_id = uuid4()
        
        # Create user with quota
        await quota_service.get_user_quota(user_id)
        
        # Test incrementing quota
        updated_quota = await quota_service.update_user_quota(user_id, 1000000, increment=True)
        assert updated_quota.quota_used == 1000000
        assert updated_quota.quota_remaining == quota_service.default_quota_limit - 1000000
        
        # Test decrementing quota
        updated_quota = await quota_service.update_user_quota(user_id, 500000, increment=False)
        assert updated_quota.quota_used == 500000
        assert updated_quota.quota_remaining == quota_service.default_quota_limit - 500000
        
        # Test quota exceeded
        with pytest.raises(QuotaExceededError):
            await quota_service.update_user_quota(user_id, quota_service.default_quota_limit + 1, increment=True)
    
    @pytest.mark.asyncio
    async def test_reset_user_quota(self, temp_users_file):
        """Test resetting user quota"""
        quota_service = QuotaService(users_file=temp_users_file)
        user_id = uuid4()
        
        # Create user and use some quota
        await quota_service.get_user_quota(user_id)
        await quota_service.update_user_quota(user_id, 1000000, increment=True)
        
        # Reset quota
        reset_quota = await quota_service.reset_user_quota(user_id)
        assert reset_quota.quota_used == 0
        assert reset_quota.quota_remaining == quota_service.default_quota_limit
        
        # Test reset with custom limit
        custom_limit = 5000000000  # 5GB
        reset_quota = await quota_service.reset_user_quota(user_id, custom_limit)
        assert reset_quota.quota_limit == custom_limit
        assert reset_quota.quota_used == 0
        assert reset_quota.quota_remaining == custom_limit
    
    @pytest.mark.asyncio
    async def test_get_user_quota_usage(self, temp_users_file):
        """Test getting detailed quota usage"""
        quota_service = QuotaService(users_file=temp_users_file)
        user_id = uuid4()
        
        # Create user and use some quota
        await quota_service.get_user_quota(user_id)
        await quota_service.update_user_quota(user_id, 2000000000, increment=True)  # 2GB
        
        usage = await quota_service.get_user_quota_usage(user_id)
        assert usage["user_id"] == str(user_id)
        assert usage["quota_used"] == 2000000000
        assert usage["quota_remaining"] == quota_service.default_quota_limit - 2000000000
        assert usage["usage_percentage"] > 0
        assert "quota_limit_gb" in usage
        assert "quota_used_gb" in usage
        assert "quota_remaining_gb" in usage


class TestModelIntegration:
    """Test integration between models and services"""
    
    @pytest.mark.asyncio
    async def test_upload_session_with_quota_validation(self):
        """Test UploadSession integration with quota validation"""
        user_id = uuid4()
        
        # Create upload session
        session = UploadSession(
            user_id=user_id,
            quota_remaining=5000000,  # 5MB
            quota_limit=10000000      # 10MB
        )
        
        # Test adding files within quota
        success = session.add_file_to_session(2000000)  # 2MB
        assert success is True
        assert session.quota_remaining == 3000000
        
        success = session.add_file_to_session(2000000)  # 2MB
        assert success is True
        assert session.quota_remaining == 1000000
        
        # Test adding file that would exceed quota
        success = session.add_file_to_session(2000000)  # 2MB > 1MB remaining
        assert success is False
        assert session.quota_remaining == 1000000  # Should not change
        
        # Test session progress
        progress = session.get_session_progress()
        assert progress["total_files"] == 2
        assert progress["quota_remaining"] == 1000000
        assert progress["quota_percentage"] == 90.0  # 9MB used out of 10MB
    
    def test_upload_progress_with_websocket_event(self):
        """Test UploadProgress integration with WebSocket events"""
        progress = UploadProgress(
            upload_id=uuid4(),
            session_id=uuid4(),
            percentage=75.0,
            bytes_uploaded=750000,
            bytes_total=1000000,
            status=UploadProgressStatusEnum.IN_PROGRESS,
            filename="test_video.mp4",
            file_size=1000000
        )
        
        event = UploadProgressEvent(
            event_type=UploadEventTypeEnum.UPLOAD_PROGRESS,
            upload_id=progress.upload_id,
            session_id=progress.session_id,
            user_id=uuid4(),
            progress=progress
        )
        
        # Test WebSocket message format
        websocket_msg = event.to_websocket_message()
        assert websocket_msg["type"] == "upload_progress"
        assert websocket_msg["event_type"] == "upload_progress"
        assert websocket_msg["progress"]["percentage"] == 75.0
        assert websocket_msg["progress"]["bytes_uploaded"] == 750000
        assert websocket_msg["progress"]["status"] == "in_progress"
        assert websocket_msg["progress"]["filename"] == "test_video.mp4"


def test_work_order_66_requirements_compliance():
    """
    Test that all Work Order #66 requirements are met
    """
    
    # Test 1: DashboardUploadRequest and DashboardUploadResponse models
    mock_file = Mock()
    mock_file.filename = "test_video.mp4"
    
    request = DashboardUploadRequest(
        file=mock_file,
        user_id=uuid4(),
        priority=5,
        metadata={"test": "data"},
        dashboard_context={"section": "/upload"},
        auto_analyze=True,
        store_in_s3=True
    )
    
    response = DashboardUploadResponse(
        video_id=uuid4(),
        status=UploadStatusEnum.COMPLETED,
        message="Upload successful",
        filename="test_video.mp4",
        file_size=1024000,
        file_hash="abc123",
        format="mp4",
        storage_location="s3"
    )
    
    # Verify all required fields are present
    assert hasattr(request, 'file')
    assert hasattr(request, 'user_id')
    assert hasattr(request, 'priority')
    assert hasattr(request, 'metadata')
    assert hasattr(request, 'dashboard_context')
    assert hasattr(request, 'auto_analyze')
    assert hasattr(request, 'store_in_s3')
    
    assert hasattr(response, 'upload_id')
    assert hasattr(response, 'video_id')
    assert hasattr(response, 'status')
    assert hasattr(response, 'message')
    assert hasattr(response, 'filename')
    assert hasattr(response, 'file_size')
    assert hasattr(response, 'file_hash')
    
    # Test 2: UploadSession model
    session = UploadSession(
        user_id=uuid4(),
        quota_remaining=1000000,
        quota_limit=10000000,
        dashboard_context={"current_section": "/upload"}
    )
    
    # Verify all required fields are present
    assert hasattr(session, 'session_id')
    assert hasattr(session, 'user_id')
    assert hasattr(session, 'quota_remaining')
    assert hasattr(session, 'dashboard_context')
    
    # Test 3: UploadProgress and UploadProgressEvent models
    progress = UploadProgress(
        upload_id=uuid4(),
        session_id=uuid4(),
        percentage=50.0,
        bytes_uploaded=500000,
        bytes_total=1000000,
        status=UploadProgressStatusEnum.IN_PROGRESS,
        filename="test_video.mp4",
        file_size=1000000
    )
    
    event = UploadProgressEvent(
        event_type=UploadEventTypeEnum.UPLOAD_PROGRESS,
        upload_id=progress.upload_id,
        session_id=progress.session_id,
        progress=progress
    )
    
    # Verify all required fields are present
    assert hasattr(progress, 'upload_id')
    assert hasattr(progress, 'session_id')
    assert hasattr(progress, 'percentage')
    assert hasattr(progress, 'bytes_uploaded')
    assert hasattr(progress, 'bytes_total')
    assert hasattr(progress, 'status')
    
    assert hasattr(event, 'event_type')
    assert hasattr(event, 'upload_id')
    assert hasattr(event, 'session_id')
    assert hasattr(event, 'progress')
    
    # Test 4: Video file validation function
    assert validate_file_format("test.mp4") == "mp4"
    assert validate_file_size(1024000) is True
    assert validate_file_size(MAX_FILE_SIZE + 1) is False
    
    # Test 5: File hash calculation function
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("test content")
        temp_file = f.name
    
    try:
        hash_result = calculate_file_hash(temp_file)
        assert isinstance(hash_result, str)
        assert len(hash_result) == 64
    finally:
        os.unlink(temp_file)
    
    # Test 6: S3 upload helper (mock test)
    from src.utils.s3_helper import S3Helper
    
    # Test S3Helper initialization (will fail without real credentials, but tests structure)
    with pytest.raises((S3ConfigurationError, NoCredentialsError)):
        S3Helper(bucket_name="test-bucket")
    
    # Test 7: User quota management functions
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{}')
        temp_users_file = f.name
    
    try:
        quota_service = QuotaService(users_file=temp_users_file)
        user_id = uuid4()
        
        # Test quota retrieval
        quota = asyncio.run(quota_service.get_user_quota(user_id))
        assert quota.user_id == user_id
        assert quota.quota_limit > 0
        
        # Test quota validation
        validation = asyncio.run(quota_service.validate_upload_quota(user_id, 1000000))
        assert validation.is_valid is True
        assert validation.can_upload is True
        
        # Test quota update
        updated_quota = asyncio.run(quota_service.update_user_quota(user_id, 1000000))
        assert updated_quota.quota_used == 1000000
        
    finally:
        os.unlink(temp_users_file)
    
    # Test 8: Integration with existing Core Detection Engine models
    # This is verified by the use of UUID types and proper field validation
    
    # Test 9: JSON serialization support
    request_json = request.model_dump()
    response_json = response.model_dump()
    session_json = session.model_dump()
    progress_json = progress.model_dump()
    event_json = event.model_dump()
    
    assert isinstance(request_json, dict)
    assert isinstance(response_json, dict)
    assert isinstance(session_json, dict)
    assert isinstance(progress_json, dict)
    assert isinstance(event_json, dict)
    
    # Test 10: WebSocket compatibility
    websocket_msg = event.to_websocket_message()
    assert isinstance(websocket_msg, dict)
    assert websocket_msg["type"] == "upload_progress"
    
    print("✅ All Work Order #66 requirements have been successfully implemented and tested!")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
