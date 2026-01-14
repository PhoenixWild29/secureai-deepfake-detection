#!/usr/bin/env python3
"""
Work Order #22 Implementation Test Suite
Comprehensive tests for WebSocket real-time analysis updates
"""

import os
import sys
import pytest
import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
import websockets
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.analysis_events import (
    StatusUpdate, ResultUpdate, ErrorEvent, HeartbeatEvent,
    EventType, AnalysisStage, SuspiciousRegion,
    create_status_update, create_result_update, create_error_event
)
from app.core.redis_manager import RedisManager, redis_manager
from app.dependencies.auth import JWTWebSocketAuth, create_mock_token
from app.api.websockets import connection_manager, send_status_update, send_result_update


class TestAnalysisEventModels:
    """Test analysis event Pydantic models."""
    
    def test_status_update_creation(self):
        """Test StatusUpdate model creation."""
        status_update = StatusUpdate(
            task_id="test-task-123",
            analysis_id=str(uuid.uuid4()),
            progress=0.5,
            current_stage=AnalysisStage.MODEL_INFERENCE,
            message="Processing frames"
        )
        
        assert status_update.task_id == "test-task-123"
        assert status_update.progress == 0.5
        assert status_update.current_stage == AnalysisStage.MODEL_INFERENCE
        assert status_update.event_type == EventType.STATUS_UPDATE
    
    def test_status_update_validation(self):
        """Test StatusUpdate model validation."""
        # Valid status update
        status_update = StatusUpdate(
            task_id="test-task-123",
            analysis_id=str(uuid.uuid4()),
            progress=0.75,
            current_stage=AnalysisStage.POST_PROCESSING,
            message="Almost done"
        )
        assert status_update.progress == 0.75
        
        # Invalid progress (should raise validation error)
        with pytest.raises(ValueError):
            StatusUpdate(
                task_id="test-task-123",
                analysis_id=str(uuid.uuid4()),
                progress=1.5,  # Invalid: > 1.0
                current_stage=AnalysisStage.MODEL_INFERENCE,
                message="Invalid progress"
            )
    
    def test_result_update_creation(self):
        """Test ResultUpdate model creation."""
        suspicious_regions = [
            SuspiciousRegion(
                frame_number=10,
                x=0.1, y=0.2, width=0.3, height=0.4,
                confidence=0.85,
                region_type="face_manipulation"
            )
        ]
        
        result_update = ResultUpdate(
            analysis_id=str(uuid.uuid4()),
            confidence_score=0.92,
            frames_processed=100,
            total_frames=120,
            suspicious_regions=suspicious_regions,
            blockchain_hash="abc123def456",
            processing_time_ms=5000,
            is_fake=True
        )
        
        assert result_update.confidence_score == 0.92
        assert result_update.frames_processed == 100
        assert result_update.total_frames == 120
        assert len(result_update.suspicious_regions) == 1
        assert result_update.is_fake is True
    
    def test_error_event_creation(self):
        """Test ErrorEvent model creation."""
        error_event = ErrorEvent(
            analysis_id=str(uuid.uuid4()),
            error_code="PROCESSING_FAILED",
            error_message="Video processing failed",
            error_details={"error_type": "timeout", "retry_count": 3}
        )
        
        assert error_event.error_code == "PROCESSING_FAILED"
        assert error_event.error_message == "Video processing failed"
        assert error_event.error_details["retry_count"] == 3
    
    def test_heartbeat_event_creation(self):
        """Test HeartbeatEvent model creation."""
        heartbeat = HeartbeatEvent(message="ping")
        
        assert heartbeat.message == "ping"
        assert heartbeat.event_type == EventType.HEARTBEAT


class TestRedisManager:
    """Test Redis manager functionality."""
    
    @pytest.fixture
    def redis_manager_instance(self):
        """Create Redis manager instance for testing."""
        return RedisManager(
            host="localhost",
            port=6379,
            db=1  # Use different DB for testing
        )
    
    @pytest.mark.asyncio
    async def test_redis_manager_initialization(self, redis_manager_instance):
        """Test Redis manager initialization."""
        assert redis_manager_instance.host == "localhost"
        assert redis_manager_instance.port == 6379
        assert redis_manager_instance.db == 1
        assert redis_manager_instance.decode_responses is True
    
    @pytest.mark.asyncio
    async def test_redis_connection(self, redis_manager_instance):
        """Test Redis connection establishment."""
        # Mock Redis connection
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_redis.return_value = mock_client
            
            connected = await redis_manager_instance.connect()
            
            # Should return True for successful connection
            assert connected is True
            assert redis_manager_instance._pub_client is not None
            assert redis_manager_instance._sub_client is not None
    
    @pytest.mark.asyncio
    async def test_redis_disconnect(self, redis_manager_instance):
        """Test Redis disconnection."""
        # Mock clients
        mock_pub_client = AsyncMock()
        mock_sub_client = AsyncMock()
        mock_pub_pool = AsyncMock()
        mock_sub_pool = AsyncMock()
        
        redis_manager_instance._pub_client = mock_pub_client
        redis_manager_instance._sub_client = mock_sub_client
        redis_manager_instance._pub_pool = mock_pub_pool
        redis_manager_instance._sub_pool = mock_sub_pool
        
        await redis_manager_instance.disconnect()
        
        # Verify cleanup calls
        mock_pub_client.close.assert_called_once()
        mock_sub_client.close.assert_called_once()
        mock_pub_pool.disconnect.assert_called_once()
        mock_sub_pool.disconnect.assert_called_once()
    
    def test_channel_name_generation(self, redis_manager_instance):
        """Test Redis channel name generation."""
        analysis_id = str(uuid.uuid4())
        
        analysis_channel = redis_manager_instance.get_analysis_channel(analysis_id)
        assert analysis_channel == f"analysis:{analysis_id}"
        
        user_channel = redis_manager_instance.get_user_channel("user123")
        assert user_channel == "user:user123"
        
        system_channel = redis_manager_instance.get_system_channel()
        assert system_channel == "system:updates"


class TestJWTWebSocketAuth:
    """Test JWT WebSocket authentication."""
    
    @pytest.fixture
    def jwt_auth(self):
        """Create JWT auth instance for testing."""
        return JWTWebSocketAuth(
            secret_key="test-secret-key",
            algorithm="HS256"
        )
    
    def test_jwt_auth_initialization(self, jwt_auth):
        """Test JWT auth initialization."""
        assert jwt_auth.secret_key == "test-secret-key"
        assert jwt_auth.algorithm == "HS256"
        assert jwt_auth.token_prefix == "Bearer"
        assert jwt_auth.token_param == "token"
    
    def test_token_extraction_from_query(self, jwt_auth):
        """Test token extraction from query parameters."""
        mock_websocket = Mock()
        mock_websocket.query_params = {"token": "test-token-123"}
        mock_websocket.headers = {}
        mock_websocket.cookies = {}
        
        token = jwt_auth.extract_token_from_websocket(mock_websocket)
        assert token == "test-token-123"
    
    def test_token_extraction_from_header(self, jwt_auth):
        """Test token extraction from Authorization header."""
        mock_websocket = Mock()
        mock_websocket.query_params = {}
        mock_websocket.headers = {"authorization": "Bearer test-token-456"}
        mock_websocket.cookies = {}
        
        token = jwt_auth.extract_token_from_websocket(mock_websocket)
        assert token == "test-token-456"
    
    def test_token_extraction_from_cookie(self, jwt_auth):
        """Test token extraction from cookies."""
        mock_websocket = Mock()
        mock_websocket.query_params = {}
        mock_websocket.headers = {}
        mock_websocket.cookies = {"access_token": "test-token-789"}
        
        token = jwt_auth.extract_token_from_websocket(mock_websocket)
        assert token == "test-token-789"
    
    def test_token_validation(self, jwt_auth):
        """Test JWT token validation."""
        # Create valid token
        token = create_mock_token("user123", expires_in_hours=1)
        
        # Validate token
        payload = jwt_auth.validate_token(token)
        
        assert payload['user_id'] == "user123"
        assert payload['sub'] == "user123"
        assert 'validated_at' in payload
    
    def test_token_validation_expired(self, jwt_auth):
        """Test validation of expired token."""
        # Create expired token
        token = create_mock_token("user123", expires_in_hours=-1)
        
        with pytest.raises(Exception):  # Should raise WebSocketAuthError
            jwt_auth.validate_token(token)
    
    def test_mock_token_creation(self):
        """Test mock token creation for testing."""
        token = create_mock_token("test-user", expires_in_hours=24)
        
        assert token is not None
        assert len(token) > 0
        
        # Validate token structure
        assert validate_token_structure(token) is True


class TestConnectionManager:
    """Test WebSocket connection manager."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket for testing."""
        websocket = Mock()
        websocket.client_state = WebSocketState.CONNECTED
        websocket.accept = AsyncMock()
        websocket.close = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.receive_text = AsyncMock()
        return websocket
    
    @pytest.mark.asyncio
    async def test_connection_manager_initialization(self):
        """Test connection manager initialization."""
        manager = connection_manager
        
        assert isinstance(manager.active_connections, dict)
        assert isinstance(manager.connection_info, dict)
        assert isinstance(manager.heartbeat_timeouts, dict)
    
    @pytest.mark.asyncio
    async def test_websocket_connect(self, mock_websocket):
        """Test WebSocket connection."""
        analysis_id = str(uuid.uuid4())
        user_id = "test-user"
        
        # Mock Redis subscription
        with patch('app.core.redis_manager.subscribe_to_analysis_updates') as mock_subscribe:
            mock_subscribe.return_value = True
            
            await connection_manager.connect(mock_websocket, analysis_id, user_id)
            
            # Verify connection setup
            assert analysis_id in connection_manager.active_connections
            assert mock_websocket in connection_manager.active_connections[analysis_id]
            assert mock_websocket in connection_manager.connection_info
            
            # Verify WebSocket accept call
            mock_websocket.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_disconnect(self, mock_websocket):
        """Test WebSocket disconnection."""
        analysis_id = str(uuid.uuid4())
        
        # Setup connection
        connection_manager.active_connections[analysis_id] = {mock_websocket}
        connection_manager.connection_info[mock_websocket] = {
            'analysis_id': analysis_id,
            'user_id': 'test-user'
        }
        
        # Mock Redis unsubscription
        with patch('app.core.redis_manager.redis_manager.unsubscribe_from_channel') as mock_unsubscribe:
            await connection_manager.disconnect(mock_websocket)
            
            # Verify cleanup
            assert analysis_id not in connection_manager.active_connections
            assert mock_websocket not in connection_manager.connection_info
            
            # Verify WebSocket close call
            mock_websocket.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message(self, mock_websocket):
        """Test sending message to WebSocket."""
        message = {"event_type": "test", "data": "test message"}
        
        await connection_manager.send_message(mock_websocket, message)
        
        # Verify message was sent
        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        sent_data = json.loads(call_args)
        assert sent_data["event_type"] == "test"
    
    @pytest.mark.asyncio
    async def test_broadcast_to_analysis(self, mock_websocket):
        """Test broadcasting message to analysis connections."""
        analysis_id = str(uuid.uuid4())
        message = {"event_type": "broadcast", "data": "broadcast message"}
        
        # Setup connection
        connection_manager.active_connections[analysis_id] = {mock_websocket}
        
        await connection_manager.broadcast_to_analysis(analysis_id, message)
        
        # Verify message was sent
        mock_websocket.send_text.assert_called_once()


class TestWebSocketIntegration:
    """Test WebSocket endpoint integration."""
    
    @pytest.mark.asyncio
    async def test_send_status_update(self):
        """Test sending status update."""
        analysis_id = str(uuid.uuid4())
        
        # Mock connection manager
        with patch('app.api.websockets.connection_manager.broadcast_to_analysis') as mock_broadcast, \
             patch('app.api.websockets.redis_manager.publish_message') as mock_publish:
            
            await send_status_update(
                analysis_id=analysis_id,
                task_id="test-task-123",
                progress=0.5,
                current_stage=AnalysisStage.MODEL_INFERENCE,
                message="Processing frames"
            )
            
            # Verify broadcast was called
            mock_broadcast.assert_called_once()
            broadcast_args = mock_broadcast.call_args[0]
            assert broadcast_args[0] == analysis_id
            
            # Verify Redis publish was called
            mock_publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_result_update(self):
        """Test sending result update."""
        analysis_id = str(uuid.uuid4())
        
        # Mock connection manager
        with patch('app.api.websockets.connection_manager.broadcast_to_analysis') as mock_broadcast, \
             patch('app.api.websockets.redis_manager.publish_message') as mock_publish:
            
            await send_result_update(
                analysis_id=analysis_id,
                confidence_score=0.92,
                frames_processed=100,
                total_frames=120,
                is_fake=True
            )
            
            # Verify broadcast was called
            mock_broadcast.assert_called_once()
            broadcast_args = mock_broadcast.call_args[0]
            assert broadcast_args[0] == analysis_id
            
            # Verify Redis publish was called
            mock_publish.assert_called_once()


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_status_update_function(self):
        """Test create_status_update utility function."""
        status_update = create_status_update(
            task_id="test-task",
            analysis_id=str(uuid.uuid4()),
            progress=0.75,
            current_stage=AnalysisStage.POST_PROCESSING,
            message="Almost done"
        )
        
        assert isinstance(status_update, StatusUpdate)
        assert status_update.task_id == "test-task"
        assert status_update.progress == 0.75
    
    def test_create_result_update_function(self):
        """Test create_result_update utility function."""
        result_update = create_result_update(
            analysis_id=str(uuid.uuid4()),
            confidence_score=0.88,
            frames_processed=50,
            total_frames=60,
            is_fake=False
        )
        
        assert isinstance(result_update, ResultUpdate)
        assert result_update.confidence_score == 0.88
        assert result_update.frames_processed == 50
        assert result_update.is_fake is False
    
    def test_create_error_event_function(self):
        """Test create_error_event utility function."""
        error_event = create_error_event(
            analysis_id=str(uuid.uuid4()),
            error_code="TIMEOUT",
            error_message="Processing timeout"
        )
        
        assert isinstance(error_event, ErrorEvent)
        assert error_event.error_code == "TIMEOUT"
        assert error_event.error_message == "Processing timeout"


class TestEventValidation:
    """Test event validation and serialization."""
    
    def test_event_json_serialization(self):
        """Test event JSON serialization."""
        status_update = StatusUpdate(
            task_id="test-task",
            analysis_id=str(uuid.uuid4()),
            progress=0.5,
            current_stage=AnalysisStage.MODEL_INFERENCE,
            message="Processing"
        )
        
        # Convert to dict
        event_dict = status_update.dict()
        
        # Verify all required fields are present
        assert "event_type" in event_dict
        assert "task_id" in event_dict
        assert "analysis_id" in event_dict
        assert "progress" in event_dict
        assert "current_stage" in event_dict
        assert "message" in event_dict
        assert "timestamp" in event_dict
    
    def test_event_json_deserialization(self):
        """Test event JSON deserialization."""
        event_data = {
            "event_type": "status_update",
            "task_id": "test-task",
            "analysis_id": str(uuid.uuid4()),
            "progress": 0.5,
            "current_stage": "model_inference",
            "message": "Processing",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Create event from dict
        status_update = StatusUpdate(**event_data)
        
        assert status_update.task_id == "test-task"
        assert status_update.progress == 0.5
        assert status_update.current_stage == AnalysisStage.MODEL_INFERENCE


# Test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
