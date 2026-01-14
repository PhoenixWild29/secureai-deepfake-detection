#!/usr/bin/env python3
"""
Comprehensive Test Suite for Frame Analysis API Models and Validation Extensions
Tests all implemented functionality according to Work Order #12 specifications
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone
from typing import List, Dict, Any

# Import our implemented models and utilities
from app.models.frame_analysis import FrameAnalysisResult, FrameAnalysisSequence
from app.models.detection import DetectionResponse
from app.core.redis_utils import (
    get_frame_embedding_cache_key,
    get_analysis_cache_key,
    get_result_cache_key,
    get_session_cache_key,
    generate_video_hash,
    get_cache_ttl,
    create_cache_metadata,
    format_frame_batch_cache_key,
    parse_cache_key,
    get_cache_performance_metrics
)


class TestFrameAnalysisResult:
    """Test FrameAnalysisResult model validation and functionality"""
    
    def test_valid_frame_analysis_result(self):
        """Test creating a valid FrameAnalysisResult"""
        frame = FrameAnalysisResult(
            frame_number=0,
            confidence_score=0.75,
            suspicious_regions=[{"x": 100, "y": 100, "width": 50, "height": 50}],
            artifacts={"blur_score": 0.8, "compression_artifacts": True},
            processing_time_ms=150,
            embedding_cached=True
        )
        
        assert frame.frame_number == 0
        assert frame.confidence_score == 0.75
        assert len(frame.suspicious_regions) == 1
        assert frame.artifacts["blur_score"] == 0.8
        assert frame.processing_time_ms == 150
        assert frame.embedding_cached is True
    
    def test_confidence_score_validation(self):
        """Test confidence score validation (0.0-1.0 range)"""
        # Valid confidence scores
        valid_scores = [0.0, 0.5, 1.0, 0.123, 0.999]
        for score in valid_scores:
            frame = FrameAnalysisResult(
                frame_number=0,
                confidence_score=score,
                processing_time_ms=100
            )
            assert frame.confidence_score == score
        
        # Invalid confidence scores
        invalid_scores = [-0.1, 1.1, -1.0, 2.0]
        for score in invalid_scores:
            with pytest.raises(ValueError, match="confidence_score must be within"):
                FrameAnalysisResult(
                    frame_number=0,
                    confidence_score=score,
                    processing_time_ms=100
                )
    
    def test_frame_number_validation(self):
        """Test frame number validation (non-negative)"""
        # Valid frame numbers
        valid_numbers = [0, 1, 100, 1000]
        for frame_num in valid_numbers:
            frame = FrameAnalysisResult(
                frame_number=frame_num,
                confidence_score=0.5,
                processing_time_ms=100
            )
            assert frame.frame_number == frame_num
        
        # Invalid frame numbers
        invalid_numbers = [-1, -100]
        for frame_num in invalid_numbers:
            with pytest.raises(ValueError, match="frame_number must be non-negative"):
                FrameAnalysisResult(
                    frame_number=frame_num,
                    confidence_score=0.5,
                    processing_time_ms=100
                )
    
    def test_processing_time_validation(self):
        """Test processing time validation (non-negative)"""
        # Valid processing times
        valid_times = [0, 50, 100, 1000]
        for time_ms in valid_times:
            frame = FrameAnalysisResult(
                frame_number=0,
                confidence_score=0.5,
                processing_time_ms=time_ms
            )
            assert frame.processing_time_ms == time_ms
        
        # Invalid processing times
        invalid_times = [-1, -100]
        for time_ms in invalid_times:
            with pytest.raises(ValueError, match="processing_time_ms must be non-negative"):
                FrameAnalysisResult(
                    frame_number=0,
                    confidence_score=0.5,
                    processing_time_ms=time_ms
                )


class TestFrameAnalysisSequence:
    """Test FrameAnalysisSequence model validation and functionality"""
    
    def test_valid_sequential_frames(self):
        """Test valid sequential frame sequence"""
        frames = [
            FrameAnalysisResult(
                frame_number=0,
                confidence_score=0.5,
                processing_time_ms=100
            ),
            FrameAnalysisResult(
                frame_number=1,
                confidence_score=0.6,
                processing_time_ms=120
            ),
            FrameAnalysisResult(
                frame_number=2,
                confidence_score=0.7,
                processing_time_ms=140
            )
        ]
        
        sequence = FrameAnalysisSequence(frames=frames)
        assert sequence.total_frames == 3
        assert sequence.average_confidence == (0.5 + 0.6 + 0.7) / 3
        assert sequence.suspicious_frames_count == 2  # frames with score > 0.5
    
    def test_non_sequential_frames_validation(self):
        """Test validation of non-sequential frame numbers"""
        frames = [
            FrameAnalysisResult(
                frame_number=0,
                confidence_score=0.5,
                processing_time_ms=100
            ),
            FrameAnalysisResult(
                frame_number=2,  # Missing frame 1
                confidence_score=0.6,
                processing_time_ms=120
            )
        ]
        
        with pytest.raises(ValueError, match="Frame sequence must be sequential"):
            FrameAnalysisSequence(frames=frames)
    
    def test_non_chronological_processing_times(self):
        """Test validation of non-chronological processing timestamps"""
        frames = [
            FrameAnalysisResult(
                frame_number=0,
                confidence_score=0.5,
                processing_time_ms=100
            ),
            FrameAnalysisResult(
                frame_number=1,
                confidence_score=0.6,
                processing_time_ms=80  # Earlier than previous frame
            )
        ]
        
        with pytest.raises(ValueError, match="Processing timestamps must be non-decreasing"):
            FrameAnalysisSequence(frames=frames)


class TestDetectionResponse:
    """Test DetectionResponse model with frame analysis integration"""
    
    def test_valid_detection_response_with_frames(self):
        """Test creating a valid DetectionResponse with frame analysis"""
        frames = [
            FrameAnalysisResult(
                frame_number=0,
                confidence_score=0.5,
                processing_time_ms=100,
                embedding_cached=True
            ),
            FrameAnalysisResult(
                frame_number=1,
                confidence_score=0.7,
                processing_time_ms=120,
                embedding_cached=False
            )
        ]
        
        response = DetectionResponse(
            analysis_id=uuid4(),
            status="completed",
            overall_confidence=0.6,
            blockchain_hash="0x1234567890abcdef",
            processing_time_ms=220,
            frame_analysis=frames
        )
        
        assert response.total_frames == 2
        assert response.suspicious_frames_count == 1  # frame with score > 0.5
        assert response.cached_embeddings_count == 1
        assert response.cache_hit_rate == 0.5
        assert response.average_processing_time_per_frame == 110.0
    
    def test_overall_confidence_calculation(self):
        """Test automatic overall confidence calculation"""
        frames = [
            FrameAnalysisResult(
                frame_number=0,
                confidence_score=0.3,
                processing_time_ms=100
            ),
            FrameAnalysisResult(
                frame_number=1,
                confidence_score=0.7,
                processing_time_ms=120
            )
        ]
        
        response = DetectionResponse(
            analysis_id=uuid4(),
            status="completed",
            processing_time_ms=220,
            frame_analysis=frames
            # overall_confidence not provided - should be calculated
        )
        
        assert response.overall_confidence == 0.5  # (0.3 + 0.7) / 2
    
    def test_frame_analysis_consistency_validation(self):
        """Test frame analysis consistency validation"""
        frames = [
            FrameAnalysisResult(
                frame_number=0,
                confidence_score=0.5,
                processing_time_ms=100
            ),
            FrameAnalysisResult(
                frame_number=2,  # Non-sequential
                confidence_score=0.6,
                processing_time_ms=120
            )
        ]
        
        with pytest.raises(ValueError, match="Frame analysis must be sequential"):
            DetectionResponse(
                analysis_id=uuid4(),
                status="completed",
                processing_time_ms=220,
                frame_analysis=frames
            )


class TestRedisUtils:
    """Test Redis cache utilities functionality"""
    
    def test_frame_embedding_cache_key(self):
        """Test frame embedding cache key generation"""
        video_hash = "abc123def456"
        frame_number = 42
        
        cache_key = get_frame_embedding_cache_key(video_hash, frame_number)
        assert cache_key == "embed:abc123def456:42"
    
    def test_frame_embedding_cache_key_validation(self):
        """Test frame embedding cache key validation"""
        # Valid inputs
        get_frame_embedding_cache_key("valid_hash", 0)
        get_frame_embedding_cache_key("another_hash", 1000)
        
        # Invalid inputs
        with pytest.raises(ValueError):
            get_frame_embedding_cache_key("", 0)
        
        with pytest.raises(ValueError):
            get_frame_embedding_cache_key("valid_hash", -1)
        
        with pytest.raises(ValueError):
            get_frame_embedding_cache_key(None, 0)
    
    def test_other_cache_keys(self):
        """Test other cache key generation functions"""
        analysis_id = "analysis_123"
        result_id = "result_456"
        session_id = "session_789"
        
        assert get_analysis_cache_key(analysis_id) == f"analysis:{analysis_id}"
        assert get_result_cache_key(result_id) == f"result:{result_id}"
        assert get_session_cache_key(session_id) == f"session:{session_id}"
    
    def test_cache_ttl(self):
        """Test cache TTL retrieval"""
        assert get_cache_ttl("embed") == 3600
        assert get_cache_ttl("analysis") == 1800
        assert get_cache_ttl("result") == 86400
        assert get_cache_ttl("session") == 7200
        
        with pytest.raises(ValueError):
            get_cache_ttl("invalid_type")
    
    def test_video_hash_generation(self):
        """Test video hash generation"""
        content = b"test video content"
        video_hash = generate_video_hash(content)
        
        assert isinstance(video_hash, str)
        assert len(video_hash) == 64  # SHA-256 hex length
        
        # Same content should produce same hash
        assert generate_video_hash(content) == video_hash
        
        # Different content should produce different hash
        different_content = b"different video content"
        assert generate_video_hash(different_content) != video_hash
    
    def test_cache_metadata_creation(self):
        """Test cache metadata creation"""
        metadata = create_cache_metadata(
            video_hash="abc123",
            frame_number=5,
            model_version="v1.2.3",
            processing_time_ms=150,
            confidence_score=0.8
        )
        
        assert metadata["video_hash"] == "abc123"
        assert metadata["frame_number"] == 5
        assert metadata["model_version"] == "v1.2.3"
        assert metadata["processing_time_ms"] == 150
        assert metadata["confidence_score"] == 0.8
        assert "cached_at" in metadata
        assert metadata["cache_ttl"] == 3600
    
    def test_frame_batch_cache_key(self):
        """Test frame batch cache key generation"""
        video_hash = "abc123"
        frame_start = 10
        frame_end = 20
        
        batch_key = format_frame_batch_cache_key(video_hash, frame_start, frame_end)
        assert batch_key == "embed:abc123:batch:10:20"
    
    def test_cache_key_parsing(self):
        """Test cache key parsing"""
        # Test frame embedding key
        parsed = parse_cache_key("embed:abc123:42")
        assert parsed["type"] == "frame_embedding"
        assert parsed["video_hash"] == "abc123"
        assert parsed["frame_number"] == 42
        
        # Test analysis key
        parsed = parse_cache_key("analysis:analysis_123")
        assert parsed["type"] == "analysis"
        assert parsed["analysis_id"] == "analysis_123"
        
        # Test batch key
        parsed = parse_cache_key("embed:abc123:batch:10:20")
        assert parsed["type"] == "frame_batch"
        assert parsed["video_hash"] == "abc123"
        assert parsed["frame_start"] == 10
        assert parsed["frame_end"] == 20
    
    def test_cache_performance_metrics(self):
        """Test cache performance metrics"""
        metrics = get_cache_performance_metrics()
        
        assert "cache_types" in metrics
        assert "embedding" in metrics["cache_types"]
        assert metrics["cache_types"]["embedding"]["performance_target_ms"] == 100
        assert metrics["total_cache_types"] == 4
        assert metrics["default_embedding_ttl"] == 3600


class TestIntegration:
    """Integration tests combining multiple components"""
    
    def test_complete_frame_analysis_workflow(self):
        """Test complete frame analysis workflow from cache to response"""
        # 1. Generate video hash
        video_content = b"fake video content for testing"
        video_hash = generate_video_hash(video_content)
        
        # 2. Create frame analysis results
        frames = []
        for i in range(3):
            cache_key = get_frame_embedding_cache_key(video_hash, i)
            frame = FrameAnalysisResult(
                frame_number=i,
                confidence_score=0.3 + (i * 0.2),  # 0.3, 0.5, 0.7
                processing_time_ms=100 + (i * 20),  # 100, 120, 140
                embedding_cached=(i % 2 == 0)  # True for even frames
            )
            frames.append(frame)
        
        # 3. Create detection response
        response = DetectionResponse(
            analysis_id=uuid4(),
            status="completed",
            processing_time_ms=360,
            frame_analysis=frames
        )
        
        # 4. Validate results
        assert response.total_frames == 3
        assert response.suspicious_frames_count == 2  # frames with score > 0.5
        assert response.cached_embeddings_count == 2  # frames 0 and 2
        assert response.cache_hit_rate == 2/3
        assert response.average_processing_time_per_frame == 120.0
        assert response.overall_confidence == 0.5  # (0.3 + 0.5 + 0.7) / 3
        
        # 5. Test summary statistics
        stats = response.get_summary_statistics()
        assert stats["total_frames"] == 3
        assert stats["suspicious_frames_count"] == 2
        assert stats["cache_hit_rate"] == 2/3
        
        # 6. Test frame confidence timeline
        timeline = response.get_frame_confidence_timeline()
        assert len(timeline) == 3
        assert timeline[0]["frame_number"] == 0
        assert timeline[0]["confidence_score"] == 0.3
        assert timeline[0]["embedding_cached"] is True


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
