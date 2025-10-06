#!/usr/bin/env python3
"""
Test Async Video Processing Pipeline Implementation
Comprehensive tests for Work Order #11 async video processing pipeline with Celery
"""

import pytest
import uuid
import json
import asyncio
import tempfile
import os
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import torch
import numpy as np
from pathlib import Path

# Test imports
from celery_app.celeryconfig import create_celery_app, validate_configuration
from celery_app.tasks import detect_video, health_check, cleanup_expired_results, monitor_gpu_usage
from utils.redis_client import RedisClient, redis_client
from utils.db_client import DatabaseClient, db_client
from video_processing.frame_extractor import VideoFrameExtractor, frame_extractor
from video_processing.ml_inference import (
    ResNet50EmbeddingExtractor, CLIPEmbeddingExtractor, 
    EnsembleEmbeddingGenerator, DeepfakeDetector
)
from main import VideoProcessingPipeline


class TestCeleryConfiguration:
    """Test Celery configuration and setup"""
    
    def test_celery_config_creation(self):
        """Test Celery configuration creation"""
        config = validate_configuration()
        
        assert 'redis_connection' in config
        assert 'celery_settings' in config
        assert 'task_settings' in config
        assert 'gpu_settings' in config
        assert 'database_settings' in config
        assert 'cache_settings' in config
        assert 'overall_valid' in config
    
    def test_celery_app_creation(self):
        """Test Celery app creation"""
        app = create_celery_app()
        
        assert app is not None
        assert app.conf.broker_url is not None
        assert app.conf.result_backend is not None
        assert app.conf.task_serializer == 'json'
        assert app.conf.result_serializer == 'json'
    
    def test_task_annotations(self):
        """Test task annotations configuration"""
        from celery_app.celeryconfig import CELERY_TASK_ANNOTATIONS
        
        assert 'celery_app.tasks.detect_video' in CELERY_TASK_ANNOTATIONS
        
        detect_video_config = CELERY_TASK_ANNOTATIONS['celery_app.tasks.detect_video']
        assert detect_video_config['rate_limit'] == '10/m'
        assert detect_video_config['max_retries'] == 3
        assert detect_video_config['default_retry_delay'] == 60


class TestRedisClient:
    """Test Redis client functionality"""
    
    @pytest.fixture
    def redis_client_instance(self):
        """Create Redis client instance for testing"""
        return RedisClient(host='localhost', port=6379, db=1)  # Use test DB
    
    def test_redis_client_initialization(self, redis_client_instance):
        """Test Redis client initialization"""
        assert redis_client_instance.host == 'localhost'
        assert redis_client_instance.port == 6379
        assert redis_client_instance.db == 1
        assert redis_client_instance.EMBEDDING_PREFIX == 'embed'
        assert redis_client_instance.ANALYSIS_PREFIX == 'analysis'
    
    def test_cache_key_generation(self, redis_client_instance):
        """Test cache key generation"""
        video_path = "/path/to/video.mp4"
        cache_key = redis_client_instance.get_embedding_cache_key(video_path)
        
        assert cache_key.startswith('embed:')
        assert len(cache_key) > len('embed:')
    
    def test_video_hash_generation(self, redis_client_instance):
        """Test video hash generation"""
        video_path = "/path/to/video.mp4"
        hash1 = redis_client_instance._generate_video_hash(video_path)
        hash2 = redis_client_instance._generate_video_hash(video_path)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hash length
    
    @patch('redis.Redis')
    def test_cache_embeddings(self, mock_redis, redis_client_instance):
        """Test caching embeddings"""
        mock_client = Mock()
        mock_redis.return_value = mock_client
        
        video_path = "/path/to/video.mp4"
        embeddings = {'resnet50': [1, 2, 3], 'clip': [4, 5, 6]}
        
        result = redis_client_instance.cache_embeddings(video_path, embeddings, ttl=3600)
        
        assert result is True
        mock_client.setex.assert_called_once()
    
    @patch('redis.Redis')
    def test_get_cached_embeddings(self, mock_redis, redis_client_instance):
        """Test retrieving cached embeddings"""
        mock_client = Mock()
        mock_redis.return_value = mock_client
        
        # Mock cached data
        cached_data = {
            'embeddings': {'resnet50': [1, 2, 3], 'clip': [4, 5, 6]},
            'cached_at': datetime.now(timezone.utc).isoformat(),
            'video_path': '/path/to/video.mp4',
            'ttl': 3600
        }
        mock_client.get.return_value = json.dumps(cached_data)
        
        video_path = "/path/to/video.mp4"
        result = redis_client_instance.get_cached_embeddings(video_path)
        
        assert result is not None
        assert 'embeddings' in result
        assert result['embeddings']['resnet50'] == [1, 2, 3]
    
    @patch('redis.Redis')
    def test_publish_progress_update(self, mock_redis, redis_client_instance):
        """Test publishing progress updates"""
        mock_client = Mock()
        mock_redis.return_value = mock_client
        
        analysis_id = str(uuid.uuid4())
        progress_data = {
            'status': 'processing',
            'progress_percentage': 50.0,
            'current_stage': 'detection_analysis'
        }
        
        result = redis_client_instance.publish_progress_update(analysis_id, progress_data)
        
        assert result is True
        mock_client.publish.assert_called_once()


class TestDatabaseClient:
    """Test database client functionality"""
    
    @pytest.fixture
    def db_client_instance(self):
        """Create database client instance for testing"""
        return DatabaseClient(
            database_url='postgresql://test:test@localhost:5432/test_db',
            pool_size=5
        )
    
    def test_db_client_initialization(self, db_client_instance):
        """Test database client initialization"""
        assert db_client_instance.database_url is not None
        assert db_client_instance.pool_size == 5
        assert db_client_instance.ANALYSES_TABLE == 'analyses'
        assert db_client_instance.DETECTION_RESULTS_TABLE == 'detection_results'
    
    @patch('psycopg2.pool.ThreadedConnectionPool')
    def test_create_analysis_record(self, mock_pool, db_client_instance):
        """Test creating analysis record"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool.return_value.getconn.return_value = mock_conn
        
        analysis_id = str(uuid.uuid4())
        result = db_client_instance.create_analysis_record(
            analysis_id=analysis_id,
            video_path="/path/to/video.mp4",
            filename="test_video.mp4",
            file_size=1000000,
            status="pending"
        )
        
        assert result is True
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
    
    @patch('psycopg2.pool.ThreadedConnectionPool')
    def test_update_analysis_status(self, mock_pool, db_client_instance):
        """Test updating analysis status"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool.return_value.getconn.return_value = mock_conn
        
        analysis_id = str(uuid.uuid4())
        result = db_client_instance.update_analysis_status(
            analysis_id=analysis_id,
            status="processing",
            progress_percentage=50.0
        )
        
        assert result is True
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
    
    @patch('psycopg2.pool.ThreadedConnectionPool')
    def test_store_detection_result(self, mock_pool, db_client_instance):
        """Test storing detection result"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool.return_value.getconn.return_value = mock_conn
        
        analysis_id = str(uuid.uuid4())
        result = db_client_instance.store_detection_result(
            analysis_id=analysis_id,
            overall_confidence=0.85,
            detection_summary={"total_frames": 100, "suspicious_frames": 10},
            processing_time_seconds=45.2,
            detection_methods_used=["resnet50", "clip"]
        )
        
        assert result is True
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()


class TestVideoFrameExtractor:
    """Test video frame extractor functionality"""
    
    @pytest.fixture
    def frame_extractor_instance(self):
        """Create frame extractor instance for testing"""
        return VideoFrameExtractor(
            target_size=(224, 224),
            sampling_rate=1,
            max_frames=100,
            enable_gpu=False  # Disable GPU for testing
        )
    
    def test_frame_extractor_initialization(self, frame_extractor_instance):
        """Test frame extractor initialization"""
        assert frame_extractor_instance.target_size == (224, 224)
        assert frame_extractor_instance.sampling_rate == 1
        assert frame_extractor_instance.max_frames == 100
        assert frame_extractor_instance.device.type == 'cpu'
    
    def test_supported_formats(self, frame_extractor_instance):
        """Test supported video formats"""
        supported_formats = frame_extractor_instance.supported_formats
        assert '.mp4' in supported_formats
        assert '.avi' in supported_formats
        assert '.mov' in supported_formats
        assert '.mkv' in supported_formats
    
    def test_validate_video_file_nonexistent(self, frame_extractor_instance):
        """Test video file validation with nonexistent file"""
        result = frame_extractor_instance.validate_video_file("/nonexistent/video.mp4")
        assert result is False
    
    def test_validate_video_file_unsupported_format(self, frame_extractor_instance):
        """Test video file validation with unsupported format"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(b"fake content")
            tmp_path = tmp_file.name
        
        try:
            result = frame_extractor_instance.validate_video_file(tmp_path)
            assert result is False
        finally:
            os.unlink(tmp_path)
    
    def test_get_extraction_metrics(self, frame_extractor_instance):
        """Test getting extraction metrics"""
        metrics = frame_extractor_instance.get_extraction_metrics()
        
        assert 'total_frames_extracted' in metrics
        assert 'total_processing_time' in metrics
        assert 'average_frame_time' in metrics
        assert 'device' in metrics
        assert 'target_size' in metrics
    
    def test_resize_frame(self, frame_extractor_instance):
        """Test frame resizing"""
        # Create a dummy frame
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        resized_frame = frame_extractor_instance.resize_frame(frame, (224, 224))
        
        assert resized_frame.shape == (224, 224, 3)
        assert resized_frame.dtype == np.uint8


class TestMLInference:
    """Test ML inference functionality"""
    
    @pytest.fixture
    def resnet50_extractor(self):
        """Create ResNet50 extractor for testing"""
        return ResNet50EmbeddingExtractor(device=torch.device('cpu'))
    
    @pytest.fixture
    def clip_extractor(self):
        """Create CLIP extractor for testing"""
        return CLIPEmbeddingExtractor(device=torch.device('cpu'))
    
    @pytest.fixture
    def ensemble_generator_instance(self):
        """Create ensemble generator for testing"""
        return EnsembleEmbeddingGenerator(device=torch.device('cpu'))
    
    def test_resnet50_extractor_initialization(self, resnet50_extractor):
        """Test ResNet50 extractor initialization"""
        assert resnet50_extractor.device.type == 'cpu'
        assert resnet50_extractor.model is not None
        assert resnet50_extractor.get_embedding_dimension() == 2048
    
    def test_clip_extractor_initialization(self, clip_extractor):
        """Test CLIP extractor initialization"""
        assert clip_extractor.device.type == 'cpu'
        assert clip_extractor.model is not None
        assert clip_extractor.get_embedding_dimension() == 512
    
    def test_ensemble_generator_initialization(self, ensemble_generator_instance):
        """Test ensemble generator initialization"""
        assert ensemble_generator_instance.device.type == 'cpu'
        assert ensemble_generator_instance.resnet50_extractor is not None
        assert ensemble_generator_instance.clip_extractor is not None
        assert 'resnet50' in ensemble_generator_instance.ensemble_weights
        assert 'clip' in ensemble_generator_instance.ensemble_weights
    
    def test_generate_embeddings(self, ensemble_generator_instance):
        """Test generating embeddings"""
        # Create dummy frames tensor
        frames = torch.randn(2, 3, 224, 224)  # 2 frames, 3 channels, 224x224
        
        result = ensemble_generator_instance.generate_embeddings(frames)
        
        assert 'ensemble_embeddings' in result
        assert 'resnet50_embeddings' in result
        assert 'clip_embeddings' in result
        assert 'metadata' in result
        
        assert len(result['ensemble_embeddings']) == 2
        assert len(result['resnet50_embeddings']) == 2
        assert len(result['clip_embeddings']) == 2
    
    def test_get_inference_metrics(self, ensemble_generator_instance):
        """Test getting inference metrics"""
        metrics = ensemble_generator_instance.get_inference_metrics()
        
        assert 'total_frames_processed' in metrics
        assert 'total_inference_time' in metrics
        assert 'average_inference_time' in metrics
        assert 'device' in metrics
        assert 'ensemble_weights' in metrics


class TestCeleryTasks:
    """Test Celery tasks functionality"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies"""
        with patch('celery_app.tasks.redis_client') as mock_redis, \
             patch('celery_app.tasks.db_client') as mock_db, \
             patch('celery_app.tasks.frame_extractor') as mock_frame_extractor, \
             patch('celery_app.tasks.ensemble_generator') as mock_ensemble_generator, \
             patch('celery_app.tasks.detect_deepfake') as mock_detect_deepfake:
            
            # Configure mocks
            mock_redis.get_cached_embeddings.return_value = None  # Cache miss
            mock_redis.cache_embeddings.return_value = True
            mock_redis.publish_progress_update.return_value = True
            mock_redis.publish_completion_update.return_value = True
            
            mock_db.create_analysis_record.return_value = True
            mock_db.update_analysis_status.return_value = True
            mock_db.store_detection_result.return_value = True
            mock_db.store_frame_analysis.return_value = True
            mock_db.store_suspicious_regions.return_value = True
            mock_db.store_performance_metrics.return_value = True
            
            mock_frame_extractor.validate_video_file.return_value = True
            mock_frame_extractor.extract_and_preprocess_frames.return_value = [
                torch.randn(32, 3, 224, 224)  # Mock frame batch
            ]
            
            mock_ensemble_generator.generate_embeddings_batch.return_value = {
                'ensemble_embeddings': [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
                'resnet50_embeddings': [[0.1, 0.2], [0.3, 0.4]],
                'clip_embeddings': [[0.5, 0.6], [0.7, 0.8]],
                'metadata': {
                    'total_frames': 2,
                    'total_inference_time': 1.5,
                    'average_time_per_frame': 0.75
                }
            }
            
            mock_detect_deepfake.return_value = {
                'is_deepfake': False,
                'confidence_score': 0.3,
                'threshold': 0.5
            }
            
            yield {
                'redis': mock_redis,
                'db': mock_db,
                'frame_extractor': mock_frame_extractor,
                'ensemble_generator': mock_ensemble_generator,
                'detect_deepfake': mock_detect_deepfake
            }
    
    def test_detect_video_task_success(self, mock_dependencies):
        """Test successful video detection task"""
        analysis_id = str(uuid.uuid4())
        video_path = "/path/to/test_video.mp4"
        filename = "test_video.mp4"
        file_size = 1000000
        
        # Mock video info
        mock_dependencies['frame_extractor'].get_video_info.return_value = {
            'duration_seconds': 10.0,
            'frame_count': 300,
            'file_size_mb': 1.0
        }
        
        # Create mock task context
        mock_task = Mock()
        mock_task.request.id = str(uuid.uuid4())
        mock_task.request.retries = 0
        mock_task.max_retries = 3
        
        # Call the task function directly
        result = detect_video(
            mock_task,
            analysis_id=analysis_id,
            video_path=video_path,
            filename=filename,
            file_size=file_size
        )
        
        assert result['analysis_id'] == analysis_id
        assert result['status'] == 'completed'
        assert 'detection_result' in result
        assert 'performance_metrics' in result
    
    def test_detect_video_task_cache_hit(self, mock_dependencies):
        """Test video detection task with cache hit"""
        analysis_id = str(uuid.uuid4())
        video_path = "/path/to/test_video.mp4"
        filename = "test_video.mp4"
        file_size = 1000000
        
        # Mock cache hit
        mock_dependencies['redis'].get_cached_embeddings.return_value = {
            'embeddings': {
                'ensemble_embeddings': [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
                'resnet50_embeddings': [[0.1, 0.2], [0.3, 0.4]],
                'clip_embeddings': [[0.5, 0.6], [0.7, 0.8]]
            }
        }
        
        # Mock video info
        mock_dependencies['frame_extractor'].get_video_info.return_value = {
            'duration_seconds': 10.0,
            'frame_count': 300,
            'file_size_mb': 1.0
        }
        
        # Create mock task context
        mock_task = Mock()
        mock_task.request.id = str(uuid.uuid4())
        mock_task.request.retries = 0
        mock_task.max_retries = 3
        
        # Call the task function directly
        result = detect_video(
            mock_task,
            analysis_id=analysis_id,
            video_path=video_path,
            filename=filename,
            file_size=file_size
        )
        
        assert result['analysis_id'] == analysis_id
        assert result['status'] == 'completed'
        # Should not call frame extraction or ML inference for cache hit
        mock_dependencies['frame_extractor'].extract_and_preprocess_frames.assert_not_called()
        mock_dependencies['ensemble_generator'].generate_embeddings_batch.assert_not_called()
    
    def test_detect_video_task_validation_error(self, mock_dependencies):
        """Test video detection task with validation error"""
        analysis_id = str(uuid.uuid4())
        video_path = "/path/to/invalid_video.mp4"
        filename = "invalid_video.mp4"
        file_size = 1000000
        
        # Mock validation failure
        mock_dependencies['frame_extractor'].validate_video_file.return_value = False
        
        # Create mock task context
        mock_task = Mock()
        mock_task.request.id = str(uuid.uuid4())
        mock_task.request.retries = 0
        mock_task.max_retries = 3
        
        # Call the task function and expect exception
        with pytest.raises(Exception, match="Invalid video file"):
            detect_video(
                mock_task,
                analysis_id=analysis_id,
                video_path=video_path,
                filename=filename,
                file_size=file_size
            )
    
    def test_health_check_task(self):
        """Test health check task"""
        with patch('celery_app.tasks.redis_client') as mock_redis, \
             patch('celery_app.tasks.db_client') as mock_db, \
             patch('celery_app.tasks.ensemble_generator') as mock_ensemble_generator:
            
            # Configure mocks
            mock_redis.health_check.return_value = {'status': 'healthy'}
            mock_db.health_check.return_value = {'status': 'healthy'}
            mock_ensemble_generator.get_inference_metrics.return_value = {
                'total_frames_processed': 100,
                'device': 'cpu'
            }
            
            result = health_check()
            
            assert 'overall_status' in result
            assert 'redis' in result
            assert 'database' in result
            assert 'ml_inference' in result
            assert 'timestamp' in result
    
    def test_cleanup_expired_results_task(self):
        """Test cleanup expired results task"""
        with patch('celery_app.tasks.redis_client') as mock_redis, \
             patch('celery_app.tasks.db_client') as mock_db:
            
            # Configure mocks
            mock_redis.cleanup_expired_keys.return_value = 5
            mock_db.cleanup_old_records.return_value = 3
            
            result = cleanup_expired_results()
            
            assert 'cleaned_cache_keys' in result
            assert 'cleaned_db_records' in result
            assert result['cleaned_cache_keys'] == 5
            assert result['cleaned_db_records'] == 3


class TestVideoProcessingPipeline:
    """Test main video processing pipeline"""
    
    @pytest.fixture
    def pipeline(self):
        """Create video processing pipeline instance"""
        return VideoProcessingPipeline()
    
    def test_pipeline_initialization(self, pipeline):
        """Test pipeline initialization"""
        assert pipeline.celery_app is not None
        assert pipeline.startup_time is not None
    
    def test_validate_system(self, pipeline):
        """Test system validation"""
        with patch('main.validate_configuration') as mock_config, \
             patch('main.redis_client') as mock_redis, \
             patch('main.db_client') as mock_db, \
             patch('main.frame_extractor') as mock_frame_extractor, \
             patch('main.ensemble_generator') as mock_ensemble_generator:
            
            # Configure mocks
            mock_config.return_value = {'overall_valid': {'valid': True}}
            mock_redis.health_check.return_value = {'status': 'healthy'}
            mock_db.health_check.return_value = {'status': 'healthy'}
            mock_frame_extractor.get_extraction_metrics.return_value = {'total_frames_extracted': 0}
            mock_ensemble_generator.get_inference_metrics.return_value = {'total_frames_processed': 0}
            
            result = pipeline.validate_system()
            
            assert 'overall_valid' in result
            assert 'celery_config' in result
            assert 'redis_health' in result
            assert 'database_health' in result
    
    def test_start_video_analysis(self, pipeline):
        """Test starting video analysis"""
        with patch('main.frame_extractor') as mock_frame_extractor, \
             patch('main.create_analysis_record') as mock_create_record, \
             patch('main.detect_video') as mock_detect_video:
            
            # Configure mocks
            mock_frame_extractor.validate_video_file.return_value = True
            mock_create_record.return_value = True
            mock_task_result = Mock()
            mock_task_result.id = str(uuid.uuid4())
            mock_detect_video.delay.return_value = mock_task_result
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
                tmp_file.write(b"fake video content")
                video_path = tmp_file.name
            
            try:
                result = pipeline.start_video_analysis(video_path)
                
                assert 'analysis_id' in result
                assert 'task_id' in result
                assert 'status' in result
                assert result['status'] == 'started'
            finally:
                os.unlink(video_path)
    
    def test_get_system_health(self, pipeline):
        """Test getting system health"""
        with patch('main.health_check') as mock_health_check:
            mock_health_check.delay.return_value.get.return_value = {
                'overall_status': 'healthy',
                'redis': {'status': 'healthy'},
                'database': {'status': 'healthy'},
                'ml_inference': {'status': 'healthy'}
            }
            
            result = pipeline.get_system_health()
            
            assert 'overall_status' in result
            assert 'system_info' in result
            assert 'uptime' in result['system_info']


class TestIntegration:
    """Integration tests for complete workflow"""
    
    def test_complete_workflow_simulation(self):
        """Test complete workflow simulation"""
        # This would test the complete workflow in a real test environment
        # For now, we'll test that all components can be imported and initialized
        
        # Test imports
        from celery_app.tasks import detect_video
        from utils.redis_client import redis_client
        from utils.db_client import db_client
        from video_processing.frame_extractor import frame_extractor
        from video_processing.ml_inference import ensemble_generator
        
        # Test initialization
        assert redis_client is not None
        assert db_client is not None
        assert frame_extractor is not None
        assert ensemble_generator is not None
        
        # Test configuration
        config = validate_configuration()
        assert config is not None
    
    def test_error_handling(self):
        """Test error handling across components"""
        # Test Redis client error handling
        redis_client = RedisClient(host='invalid_host', port=9999)
        health = redis_client.health_check()
        assert health['status'] == 'unhealthy'
        
        # Test database client error handling
        db_client = DatabaseClient(database_url='postgresql://invalid:invalid@localhost:9999/invalid')
        health = db_client.health_check()
        assert health['status'] == 'unhealthy'


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
