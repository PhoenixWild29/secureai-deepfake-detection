#!/usr/bin/env python3
"""
Test Script for Work Order #9: Enhanced Video Upload Endpoint
Tests the enhanced video upload functionality with multipart support
"""

import os
import sys
import json
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all new modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        # Test core modules
        from src.utils.hash_generator import HashGenerator, generate_content_hash
        from src.utils.file_validation import EnhancedFileValidator, validate_video_file_content
        from src.config.settings import get_upload_settings, get_validation_settings
        from src.models.video import EnhancedVideoDetectionRequest, VideoUploadResponse
        from src.schemas.websocket_events import WebSocketEventType, UploadStartedEvent
        from src.database.models.upload_session import UploadSession, UploadSessionManager
        from src.core.celery_tasks import process_video_async, celery_app
        
        print("✅ All imports successful")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_hash_generation():
    """Test hash generation utilities."""
    print("\n🧪 Testing hash generation...")
    
    try:
        from src.utils.hash_generator import HashGenerator
        
        # Test content hash generation
        test_content = b"This is a test video file content"
        hash_gen = HashGenerator()
        
        # Test synchronous hash generation
        quick_hash = hash_gen.generate_quick_hash(test_content)
        assert len(quick_hash) == 64  # SHA-256 hex length
        print(f"✅ Quick hash generated: {quick_hash[:8]}...")
        
        # Test deduplication hash
        dedup_hash = hash_gen.generate_hash_for_deduplication(test_content)
        assert len(dedup_hash) == 64
        print(f"✅ Deduplication hash generated: {dedup_hash[:8]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Hash generation test failed: {e}")
        return False


def test_file_validation():
    """Test enhanced file validation."""
    print("\n🧪 Testing file validation...")
    
    try:
        from src.utils.file_validation import EnhancedFileValidator, validate_video_file_content
        
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            # Write some fake MP4 header content
            temp_file.write(b'\x00\x00\x00\x20ftypisom')  # MP4 magic bytes
            temp_file.write(b'fake video content' * 100)
            temp_file_path = temp_file.name
        
        try:
            # Read the file content
            with open(temp_file_path, 'rb') as f:
                content = f.read()
            
            # Test validation
            validator = EnhancedFileValidator()
            result = asyncio.run(validator.validate_video_file_content(
                filename='test.mp4',
                content_type='video/mp4',
                file_size=len(content),
                content=content
            ))
            
            assert result['is_valid'] == True
            print(f"✅ File validation successful: {result['filename']}")
            
            # Test invalid file
            invalid_result = asyncio.run(validator.validate_video_file_content(
                filename='test.exe',
                content_type='application/x-executable',
                file_size=1024,
                content=b'exe content'
            ))
            
            assert invalid_result['is_valid'] == False
            print("✅ Invalid file correctly rejected")
            
            return True
            
        finally:
            # Clean up
            os.unlink(temp_file_path)
            
    except Exception as e:
        print(f"❌ File validation test failed: {e}")
        return False


def test_settings_configuration():
    """Test configuration settings."""
    print("\n🧪 Testing configuration settings...")
    
    try:
        from src.config.settings import get_upload_settings, get_validation_settings, get_processing_settings
        
        # Test upload settings
        upload_settings = get_upload_settings()
        assert upload_settings.max_file_size > 0
        assert upload_settings.max_chunk_size > 0
        assert len(upload_settings.supported_video_formats) > 0
        print(f"✅ Upload settings loaded: max_size={upload_settings.max_file_size}")
        
        # Test validation settings
        validation_settings = get_validation_settings()
        assert len(validation_settings.allowed_extensions) > 0
        assert len(validation_settings.blocked_extensions) > 0
        print(f"✅ Validation settings loaded: {len(validation_settings.allowed_extensions)} allowed extensions")
        
        # Test processing settings
        processing_settings = get_processing_settings()
        assert processing_settings.max_concurrent_jobs > 0
        assert len(processing_settings.available_models) > 0
        print(f"✅ Processing settings loaded: {len(processing_settings.available_models)} models")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration settings test failed: {e}")
        return False


def test_video_models():
    """Test enhanced video models."""
    print("\n🧪 Testing video models...")
    
    try:
        from src.models.video import EnhancedVideoDetectionRequest, UploadType, ProcessingPriority
        from pydantic import ValidationError
        
        # Test valid request
        valid_request = EnhancedVideoDetectionRequest(
            file=None,  # Mock file object
            upload_type=UploadType.SINGLE,
            priority=5,
            priority_label=ProcessingPriority.NORMAL,
            validate_content=True,
            enable_deduplication=True,
            metadata={"test": "value"},
            tags=["test", "video"]
        )
        
        assert valid_request.get_effective_priority() == 5
        assert valid_request.upload_type == UploadType.SINGLE
        print("✅ Valid video request model created")
        
        # Test invalid request
        try:
            invalid_request = EnhancedVideoDetectionRequest(
                file=None,
                upload_type=UploadType.CHUNKED,
                # Missing required chunk_index and total_chunks
                priority=15  # Invalid priority
            )
            print("❌ Invalid request should have been rejected")
            return False
        except ValidationError:
            print("✅ Invalid request correctly rejected")
        
        return True
        
    except Exception as e:
        print(f"❌ Video models test failed: {e}")
        return False


def test_websocket_events():
    """Test WebSocket event schemas."""
    print("\n🧪 Testing WebSocket events...")
    
    try:
        from src.schemas.websocket_events import (
            UploadStartedEvent,
            ProcessingInitiatedEvent,
            create_upload_started_event
        )
        from uuid import uuid4
        
        # Test upload started event
        upload_id = uuid4()
        event = create_upload_started_event(
            upload_id=upload_id,
            filename='test.mp4',
            file_size=1024000,
            content_type='video/mp4'
        )
        
        assert event.upload_id == upload_id
        assert event.filename == 'test.mp4'
        assert event.file_size == 1024000
        print("✅ Upload started event created")
        
        # Test processing initiated event
        processing_event = ProcessingInitiatedEvent(
            upload_id=upload_id,
            analysis_id=uuid4(),
            processing_job_id='job_123',
            filename='test.mp4',
            file_hash='abc123',
            model_type='resnet50',
            priority=5
        )
        
        assert processing_event.model_type == 'resnet50'
        assert processing_event.priority == 5
        print("✅ Processing initiated event created")
        
        return True
        
    except Exception as e:
        print(f"❌ WebSocket events test failed: {e}")
        return False


def test_database_models():
    """Test database models."""
    print("\n🧪 Testing database models...")
    
    try:
        from src.database.models.upload_session import (
            UploadSession,
            UploadSessionStatus,
            UploadSessionManager
        )
        from datetime import datetime, timezone, timedelta
        
        # Test session creation
        session = UploadSessionManager.create_session(
            session_id='test_session_123',
            filename='test.mp4',
            content_type='video/mp4',
            total_chunks=10,
            chunk_size=1048576,  # 1MB
            file_size=10485760,  # 10MB
            user_id='user123',
            username='testuser'
        )
        
        assert session.session_id == 'test_session_123'
        assert session.total_chunks == 10
        assert session.status == UploadSessionStatus.ACTIVE
        print("✅ Upload session created")
        
        # Test session progress update
        updated_session = UploadSessionManager.update_session_progress(
            session, chunks_received=5, bytes_uploaded=5242880
        )
        
        assert updated_session.chunks_received == 5
        assert updated_session.progress_percentage == 50.0
        print("✅ Session progress updated")
        
        # Test session expiration check
        is_expired = UploadSessionManager.is_session_expired(session)
        assert is_expired == False
        print("✅ Session expiration check")
        
        return True
        
    except Exception as e:
        print(f"❌ Database models test failed: {e}")
        return False


def test_celery_tasks():
    """Test Celery task configuration."""
    print("\n🧪 Testing Celery tasks...")
    
    try:
        from src.core.celery_tasks import celery_app, process_video_async
        
        # Test Celery app configuration
        assert celery_app is not None
        assert celery_app.conf['task_serializer'] == 'json'
        print("✅ Celery app configured")
        
        # Test task registration
        registered_tasks = celery_app.tasks.keys()
        assert 'src.core.celery_tasks.process_video_async' in registered_tasks
        assert 'src.core.celery_tasks.process_video_batch' in registered_tasks
        assert 'src.core.celery_tasks.cleanup_expired_sessions' in registered_tasks
        print("✅ Celery tasks registered")
        
        return True
        
    except Exception as e:
        print(f"❌ Celery tasks test failed: {e}")
        return False


def test_endpoint_structure():
    """Test endpoint structure and imports."""
    print("\n🧪 Testing endpoint structure...")
    
    try:
        from src.api.v1.endpoints.video_upload import router
        
        # Test router configuration
        assert router is not None
        assert router.prefix == "/v1/upload"
        print("✅ Video upload router configured")
        
        # Test route registration
        routes = [route.path for route in router.routes]
        assert "/video" in routes
        assert "/video/session/{session_id}" in routes
        print("✅ Upload routes registered")
        
        return True
        
    except Exception as e:
        print(f"❌ Endpoint structure test failed: {e}")
        return False


def run_comprehensive_test():
    """Run all tests and provide summary."""
    print("🚀 Starting Work Order #9 Implementation Tests")
    print("=" * 60)
    
    tests = [
        ("Import Tests", test_imports),
        ("Hash Generation", test_hash_generation),
        ("File Validation", test_file_validation),
        ("Settings Configuration", test_settings_configuration),
        ("Video Models", test_video_models),
        ("WebSocket Events", test_websocket_events),
        ("Database Models", test_database_models),
        ("Celery Tasks", test_celery_tasks),
        ("Endpoint Structure", test_endpoint_structure),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📈 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Work Order #9 implementation is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
