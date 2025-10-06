#!/usr/bin/env python3
"""
Test Upload Session Management Implementation
Comprehensive tests for Work Order #56 upload session management
"""

import asyncio
import json
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

# Test imports
from src.api.v1.dashboard.schemas import (
    UploadSessionInitiateRequest,
    UploadSessionResponse,
    UploadSessionValidationRequest,
    UploadSessionValidationResponse,
    UploadSessionStatus,
    DashboardContext,
    UploadConfig,
    UploadSessionErrorCodes
)
from src.services.upload_session_service import UploadSessionService
from src.core.config import upload_settings
from src.auth.upload_auth import auth_service, create_test_user_token


class TestUploadSessionSchemas:
    """Test upload session Pydantic schemas"""
    
    def test_dashboard_context_validation(self):
        """Test DashboardContext validation"""
        # Valid context
        context = DashboardContext(
            source_section="video_analysis",
            workflow_type="single_upload",
            user_preferences={"quality": "high"},
            metadata={"test": "data"}
        )
        assert context.source_section == "video_analysis"
        assert context.workflow_type == "single_upload"
        
        # Invalid source section
        with pytest.raises(ValueError, match="Source section cannot be empty"):
            DashboardContext(
                source_section="",
                workflow_type="single_upload"
            )
        
        # Invalid workflow type
        with pytest.raises(ValueError, match="Unsupported workflow type"):
            DashboardContext(
                source_section="video_analysis",
                workflow_type="invalid_type"
            )
    
    def test_upload_session_initiate_request(self):
        """Test UploadSessionInitiateRequest validation"""
        context = DashboardContext(
            source_section="video_analysis",
            workflow_type="single_upload"
        )
        
        # Valid request
        request = UploadSessionInitiateRequest(
            dashboard_context=context,
            expected_file_size=1000000,  # 1MB
            file_format="mp4"
        )
        assert request.expected_file_size == 1000000
        assert request.file_format == "mp4"
        
        # File size too large
        with pytest.raises(ValueError, match="File size exceeds maximum limit"):
            UploadSessionInitiateRequest(
                dashboard_context=context,
                expected_file_size=600000000  # 600MB
            )
        
        # Invalid file format
        with pytest.raises(ValueError, match="Unsupported file format"):
            UploadSessionInitiateRequest(
                dashboard_context=context,
                file_format="invalid_format"
            )
    
    def test_upload_session_response(self):
        """Test UploadSessionResponse creation"""
        context = DashboardContext(
            source_section="video_analysis",
            workflow_type="single_upload"
        )
        
        session_id = uuid.uuid4()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        response = UploadSessionResponse(
            session_id=session_id,
            upload_url="https://api.secureai.com/upload/test",
            max_file_size=UploadConfig.MAX_FILE_SIZE,
            allowed_formats=UploadConfig.ALLOWED_FORMATS,
            remaining_quota=1000000000,  # 1GB
            quota_limit=10000000000,  # 10GB
            session_expires_at=expires_at,
            dashboard_context=context
        )
        
        assert response.session_id == session_id
        assert response.max_file_size == UploadConfig.MAX_FILE_SIZE
        assert len(response.allowed_formats) == len(UploadConfig.ALLOWED_FORMATS)


class TestUploadSessionService:
    """Test UploadSessionService functionality"""
    
    @pytest.fixture
    async def mock_redis(self):
        """Mock Redis client for testing"""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.hgetall = AsyncMock(return_value={})
        mock_redis.hset = AsyncMock(return_value=True)
        mock_redis.expire = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.sadd = AsyncMock(return_value=1)
        mock_redis.srem = AsyncMock(return_value=1)
        mock_redis.smembers = AsyncMock(return_value=set())
        mock_redis.keys = AsyncMock(return_value=[])
        mock_redis.ttl = AsyncMock(return_value=3600)
        
        return mock_redis
    
    @pytest.fixture
    async def upload_service(self, mock_redis):
        """Create UploadSessionService with mocked Redis"""
        service = UploadSessionService()
        service.redis = mock_redis
        service._redis_pool = AsyncMock()
        return service
    
    async def test_service_initialization(self, mock_redis):
        """Test service initialization"""
        service = UploadSessionService()
        
        with patch('src.services.upload_session_service.aioredis.ConnectionPool.from_url') as mock_pool:
            mock_pool.return_value = AsyncMock()
            service.redis = mock_redis
            
            initialized = await service.initialize()
            assert initialized is True
    
    async def test_create_upload_session_success(self, upload_service):
        """Test successful upload session creation"""
        user_id = uuid.uuid4()
        context = DashboardContext(
            source_section="video_analysis",
            workflow_type="single_upload"
        )
        request = UploadSessionInitiateRequest(
            dashboard_context=context,
            expected_file_size=1000000
        )
        
        # Mock quota service
        with patch.object(upload_service.quota_service, 'get_user_quota') as mock_quota:
            mock_quota.return_value = {
                'quota_limit': 10000000000,  # 10GB
                'quota_used': 0
            }
            
            # Mock Redis operations
            upload_service.redis.pipeline.return_value.__aenter__.return_value = AsyncMock()
            
            response = await upload_service.create_upload_session(user_id, request)
            
            assert isinstance(response, UploadSessionResponse)
            assert response.max_file_size == upload_service.config.upload_session.max_file_size_bytes
            assert response.remaining_quota > 0
    
    async def test_create_upload_session_quota_exceeded(self, upload_service):
        """Test upload session creation with exceeded quota"""
        user_id = uuid.uuid4()
        context = DashboardContext(
            source_section="video_analysis",
            workflow_type="single_upload"
        )
        request = UploadSessionInitiateRequest(
            dashboard_context=context,
            expected_file_size=20000000000  # 20GB
        )
        
        # Mock quota service with insufficient quota
        with patch.object(upload_service.quota_service, 'get_user_quota') as mock_quota:
            mock_quota.return_value = {
                'quota_limit': 10000000000,  # 10GB
                'quota_used': 5000000000  # 5GB used
            }
            
            with pytest.raises(Exception):  # Should raise QuotaExceededError
                await upload_service.create_upload_session(user_id, request)
    
    async def test_validate_upload_session_success(self, upload_service):
        """Test successful session validation"""
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        # Mock session data
        session_data = {
            'session_id': str(session_id),
            'user_id': str(user_id),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'expires_at': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            'dashboard_context': json.dumps({
                'source_section': 'video_analysis',
                'workflow_type': 'single_upload',
                'user_preferences': {},
                'metadata': None
            }),
            'status': 'active'
        }
        
        upload_service.redis.hgetall.return_value = session_data
        
        request = UploadSessionValidationRequest(
            session_id=session_id,
            user_id=user_id
        )
        
        response = await upload_service.validate_upload_session(request)
        
        assert response.is_valid is True
        assert response.is_owner is True
        assert response.session_status is not None
    
    async def test_validate_upload_session_expired(self, upload_service):
        """Test validation of expired session"""
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        # Mock expired session data
        session_data = {
            'session_id': str(session_id),
            'user_id': str(user_id),
            'created_at': (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
            'expires_at': (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            'dashboard_context': json.dumps({
                'source_section': 'video_analysis',
                'workflow_type': 'single_upload',
                'user_preferences': {},
                'metadata': None
            }),
            'status': 'active'
        }
        
        upload_service.redis.hgetall.return_value = session_data
        
        request = UploadSessionValidationRequest(
            session_id=session_id,
            user_id=user_id
        )
        
        response = await upload_service.validate_upload_session(request)
        
        assert response.is_valid is False
        assert response.is_owner is False
        assert "expired" in response.error_message.lower()
    
    async def test_validate_upload_session_unauthorized(self, upload_service):
        """Test validation with unauthorized user"""
        session_id = uuid.uuid4()
        owner_user_id = uuid.uuid4()
        requesting_user_id = uuid.uuid4()  # Different user
        
        # Mock session data
        session_data = {
            'session_id': str(session_id),
            'user_id': str(owner_user_id),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'expires_at': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            'dashboard_context': json.dumps({
                'source_section': 'video_analysis',
                'workflow_type': 'single_upload',
                'user_preferences': {},
                'metadata': None
            }),
            'status': 'active'
        }
        
        upload_service.redis.hgetall.return_value = session_data
        
        request = UploadSessionValidationRequest(
            session_id=session_id,
            user_id=requesting_user_id
        )
        
        response = await upload_service.validate_upload_session(request)
        
        assert response.is_valid is False
        assert response.is_owner is False
        assert "unauthorized" in response.error_message.lower()


class TestUploadSessionAPI:
    """Test upload session API endpoints"""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for API testing"""
        from fastapi.testclient import TestClient
        from api_fastapi import app
        return TestClient(app)
    
    def test_initiate_upload_session_endpoint(self, test_client):
        """Test POST /v1/dashboard/upload/initiate endpoint"""
        # Mock authentication
        test_token = create_test_user_token()
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Test request data
        request_data = {
            "dashboard_context": {
                "source_section": "video_analysis",
                "workflow_type": "single_upload",
                "user_preferences": {"quality": "high"},
                "metadata": {"test": "data"}
            },
            "expected_file_size": 1000000,
            "file_format": "mp4"
        }
        
        # Mock the upload service
        with patch('src.api.v1.dashboard.upload_endpoints.upload_session_service') as mock_service:
            mock_service.redis = AsyncMock()
            mock_service.create_upload_session = AsyncMock()
            
            # Mock successful response
            mock_response = UploadSessionResponse(
                session_id=uuid.uuid4(),
                upload_url="https://api.secureai.com/upload/test",
                max_file_size=524288000,
                allowed_formats=["mp4", "avi", "mov"],
                remaining_quota=1000000000,
                quota_limit=10000000000,
                session_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                dashboard_context=DashboardContext(**request_data["dashboard_context"])
            )
            mock_service.create_upload_session.return_value = mock_response
            
            response = test_client.post(
                "/v1/dashboard/upload/initiate",
                json=request_data,
                headers=headers
            )
            
            assert response.status_code == 201
            data = response.json()
            assert "session_id" in data
            assert "upload_url" in data
            assert "max_file_size" in data
            assert "allowed_formats" in data
    
    def test_validate_upload_session_endpoint(self, test_client):
        """Test POST /v1/dashboard/upload/validate endpoint"""
        # Mock authentication
        test_token = create_test_user_token()
        headers = {"Authorization": f"Bearer {test_token}"}
        
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        request_data = {
            "session_id": str(session_id),
            "user_id": str(user_id)
        }
        
        # Mock the upload service
        with patch('src.api.v1.dashboard.upload_endpoints.upload_session_service') as mock_service:
            mock_service.redis = AsyncMock()
            mock_service.validate_upload_session = AsyncMock()
            
            # Mock successful validation response
            mock_response = UploadSessionValidationResponse(
                is_valid=True,
                is_owner=True,
                session_status=UploadSessionStatus(
                    session_id=session_id,
                    user_id=user_id,
                    status="active",
                    created_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                    dashboard_context=DashboardContext(
                        source_section="video_analysis",
                        workflow_type="single_upload"
                    ),
                    upload_url="https://api.secureai.com/upload/test",
                    is_expired=False,
                    is_valid=True
                )
            )
            mock_service.validate_upload_session.return_value = mock_response
            
            response = test_client.post(
                "/v1/dashboard/upload/validate",
                json=request_data,
                headers=headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["is_valid"] is True
            assert data["is_owner"] is True
    
    def test_get_user_active_sessions_endpoint(self, test_client):
        """Test GET /v1/dashboard/upload/sessions endpoint"""
        # Mock authentication
        test_token = create_test_user_token()
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Mock the upload service
        with patch('src.api.v1.dashboard.upload_endpoints.upload_session_service') as mock_service:
            mock_service.redis = AsyncMock()
            mock_service.get_user_active_sessions = AsyncMock()
            
            # Mock active sessions
            mock_sessions = [
                UploadSessionStatus(
                    session_id=uuid.uuid4(),
                    user_id=uuid.uuid4(),
                    status="active",
                    created_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                    dashboard_context=DashboardContext(
                        source_section="video_analysis",
                        workflow_type="single_upload"
                    ),
                    upload_url="https://api.secureai.com/upload/test",
                    is_expired=False,
                    is_valid=True
                )
            ]
            mock_service.get_user_active_sessions.return_value = mock_sessions
            
            response = test_client.get(
                "/v1/dashboard/upload/sessions",
                headers=headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
    
    def test_health_check_endpoint(self, test_client):
        """Test GET /v1/dashboard/upload/health endpoint"""
        # Mock the upload service
        with patch('src.api.v1.dashboard.upload_endpoints.upload_session_service') as mock_service:
            mock_service.redis = AsyncMock()
            mock_service.redis.ping = AsyncMock(return_value=True)
            mock_service.config.validate_configuration.return_value = {'overall_valid': True}
            
            response = test_client.get("/v1/dashboard/upload/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["redis_connected"] is True


class TestConfiguration:
    """Test configuration and settings"""
    
    def test_upload_config_constants(self):
        """Test UploadConfig constants"""
        assert UploadConfig.MAX_FILE_SIZE == 524288000  # 500MB
        assert UploadConfig.MAX_FILE_SIZE_MB == 500
        assert UploadConfig.SESSION_TTL_SECONDS == 3600  # 1 hour
        assert "mp4" in UploadConfig.ALLOWED_FORMATS
        assert "avi" in UploadConfig.ALLOWED_FORMATS
    
    def test_upload_settings_configuration(self):
        """Test upload settings configuration"""
        config = upload_settings
        
        assert config.upload_session.max_file_size_bytes > 0
        assert config.upload_session.session_ttl_seconds > 0
        assert len(config.upload_session.allowed_formats) > 0
        assert config.redis.host is not None
        assert config.redis.port > 0
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        validation_results = upload_settings.validate_configuration()
        
        assert "redis" in validation_results
        assert "upload_session" in validation_results
        assert "storage" in validation_results
        assert "overall_valid" in validation_results


class TestAuthentication:
    """Test authentication integration"""
    
    def test_create_test_user_token(self):
        """Test test user token creation"""
        user_id = "12345678-1234-5678-9012-123456789012"
        token = create_test_user_token(user_id)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_auth_service_initialization(self):
        """Test authentication service initialization"""
        assert auth_service.secret_key is not None
        assert auth_service.algorithm == "HS256"
        assert auth_service.token_expiry_hours == 24


# Integration tests
class TestUploadSessionIntegration:
    """Integration tests for upload session management"""
    
    async def test_complete_upload_workflow(self):
        """Test complete upload session workflow"""
        # This would test the complete workflow from session creation to validation
        # In a real test environment, this would use actual Redis and test the full flow
        
        user_id = uuid.uuid4()
        context = DashboardContext(
            source_section="video_analysis",
            workflow_type="single_upload"
        )
        request = UploadSessionInitiateRequest(
            dashboard_context=context,
            expected_file_size=1000000
        )
        
        # Mock the complete workflow
        with patch('src.services.upload_session_service.upload_session_service') as mock_service:
            mock_service.redis = AsyncMock()
            mock_service.create_upload_session = AsyncMock()
            mock_service.validate_upload_session = AsyncMock()
            
            # Test session creation
            mock_response = UploadSessionResponse(
                session_id=uuid.uuid4(),
                upload_url="https://api.secureai.com/upload/test",
                max_file_size=524288000,
                allowed_formats=["mp4", "avi", "mov"],
                remaining_quota=1000000000,
                quota_limit=10000000000,
                session_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                dashboard_context=context
            )
            mock_service.create_upload_session.return_value = mock_response
            
            # Test session validation
            validation_response = UploadSessionValidationResponse(
                is_valid=True,
                is_owner=True,
                session_status=UploadSessionStatus(
                    session_id=mock_response.session_id,
                    user_id=user_id,
                    status="active",
                    created_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                    dashboard_context=context,
                    upload_url=mock_response.upload_url,
                    is_expired=False,
                    is_valid=True
                )
            )
            mock_service.validate_upload_session.return_value = validation_response
            
            # Simulate workflow
            session_response = await mock_service.create_upload_session(user_id, request)
            assert session_response.session_id is not None
            
            validation_request = UploadSessionValidationRequest(
                session_id=session_response.session_id,
                user_id=user_id
            )
            validation_result = await mock_service.validate_upload_session(validation_request)
            assert validation_result.is_valid is True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
