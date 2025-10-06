#!/usr/bin/env python3
"""
Redis Cache Utilities for Frame-Level Embedding Retrieval
Standardized cache key formatting and performance optimization utilities
"""

from typing import Final, Optional, Dict, Any, List
import hashlib
import json
from datetime import datetime, timezone, timedelta


# Redis key prefixes for different cache types
EMBED_PREFIX: Final[str] = "embed"
ANALYSIS_PREFIX: Final[str] = "analysis"
RESULT_PREFIX: Final[str] = "result"
SESSION_PREFIX: Final[str] = "session"

# Cache TTL settings (in seconds)
EMBEDDING_CACHE_TTL: Final[int] = 3600  # 1 hour
ANALYSIS_CACHE_TTL: Final[int] = 1800   # 30 minutes
RESULT_CACHE_TTL: Final[int] = 86400    # 24 hours
SESSION_CACHE_TTL: Final[int] = 7200    # 2 hours


def get_frame_embedding_cache_key(video_hash: str, frame_number: int) -> str:
    """
    Return standardized Redis key for frame-level embedding retrieval.
    
    Format: 'embed:{video_hash}:{frame_number}'
    
    This function ensures sub-100ms performance target by using a consistent
    key format that enables efficient Redis lookup and caching.
    
    Args:
        video_hash (str): Hash of the video file for unique identification
        frame_number (int): Frame number within the video (0-indexed)
    
    Returns:
        str: Formatted Redis cache key for the frame embedding
        
    Example:
        >>> get_frame_embedding_cache_key("abc123def456", 42)
        "embed:abc123def456:42"
    """
    if not video_hash or not isinstance(video_hash, str):
        raise ValueError("video_hash must be a non-empty string")
    
    if not isinstance(frame_number, int) or frame_number < 0:
        raise ValueError("frame_number must be a non-negative integer")
    
    return f"{EMBED_PREFIX}:{video_hash}:{frame_number}"


def get_analysis_cache_key(analysis_id: str) -> str:
    """
    Get Redis cache key for analysis results.
    
    Args:
        analysis_id (str): Unique analysis identifier
        
    Returns:
        str: Formatted Redis cache key for analysis results
    """
    if not analysis_id or not isinstance(analysis_id, str):
        raise ValueError("analysis_id must be a non-empty string")
    
    return f"{ANALYSIS_PREFIX}:{analysis_id}"


def get_result_cache_key(result_id: str) -> str:
    """
    Get Redis cache key for detection results.
    
    Args:
        result_id (str): Unique result identifier
        
    Returns:
        str: Formatted Redis cache key for detection results
    """
    if not result_id or not isinstance(result_id, str):
        raise ValueError("result_id must be a non-empty string")
    
    return f"{RESULT_PREFIX}:{result_id}"


def get_session_cache_key(session_id: str) -> str:
    """
    Get Redis cache key for user sessions.
    
    Args:
        session_id (str): Unique session identifier
        
    Returns:
        str: Formatted Redis cache key for user sessions
    """
    if not session_id or not isinstance(session_id, str):
        raise ValueError("session_id must be a non-empty string")
    
    return f"{SESSION_PREFIX}:{session_id}"


def generate_video_hash(file_content: bytes) -> str:
    """
    Generate SHA-256 hash for video file content.
    
    Args:
        file_content (bytes): Raw video file content
        
    Returns:
        str: SHA-256 hash of the video content
    """
    if not isinstance(file_content, bytes):
        raise ValueError("file_content must be bytes")
    
    return hashlib.sha256(file_content).hexdigest()


def get_cache_ttl(cache_type: str) -> int:
    """
    Get TTL (Time To Live) for different cache types.
    
    Args:
        cache_type (str): Type of cache (embed, analysis, result, session)
        
    Returns:
        int: TTL in seconds
    """
    ttl_map = {
        "embed": EMBEDDING_CACHE_TTL,
        "embedding": EMBEDDING_CACHE_TTL,
        "analysis": ANALYSIS_CACHE_TTL,
        "result": RESULT_CACHE_TTL,
        "session": SESSION_CACHE_TTL,
    }
    
    ttl = ttl_map.get(cache_type.lower())
    if ttl is None:
        raise ValueError(f"Unknown cache type: {cache_type}")
    
    return ttl


def create_cache_metadata(
    video_hash: str,
    frame_number: int,
    model_version: str,
    processing_time_ms: Optional[int] = None,
    confidence_score: Optional[float] = None
) -> Dict[str, Any]:
    """
    Create metadata for cached frame embedding.
    
    Args:
        video_hash (str): Hash of the video file
        frame_number (int): Frame number
        model_version (str): Model version used for embedding
        processing_time_ms (Optional[int]): Processing time in milliseconds
        confidence_score (Optional[float]): Confidence score for the frame
        
    Returns:
        Dict[str, Any]: Metadata dictionary for caching
    """
    return {
        "video_hash": video_hash,
        "frame_number": frame_number,
        "model_version": model_version,
        "processing_time_ms": processing_time_ms,
        "confidence_score": confidence_score,
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "cache_ttl": EMBEDDING_CACHE_TTL
    }


def format_frame_batch_cache_key(video_hash: str, frame_start: int, frame_end: int) -> str:
    """
    Generate cache key for a batch of frame embeddings.
    
    Args:
        video_hash (str): Hash of the video file
        frame_start (int): Starting frame number
        frame_end (int): Ending frame number
        
    Returns:
        str: Formatted Redis cache key for frame batch
    """
    if not video_hash or not isinstance(video_hash, str):
        raise ValueError("video_hash must be a non-empty string")
    
    if not isinstance(frame_start, int) or frame_start < 0:
        raise ValueError("frame_start must be a non-negative integer")
    
    if not isinstance(frame_end, int) or frame_end < frame_start:
        raise ValueError("frame_end must be an integer >= frame_start")
    
    return f"{EMBED_PREFIX}:{video_hash}:batch:{frame_start}:{frame_end}"


def parse_cache_key(cache_key: str) -> Dict[str, Any]:
    """
    Parse Redis cache key to extract components.
    
    Args:
        cache_key (str): Redis cache key
        
    Returns:
        Dict[str, Any]: Parsed components of the cache key
    """
    if not cache_key or not isinstance(cache_key, str):
        raise ValueError("cache_key must be a non-empty string")
    
    parts = cache_key.split(":")
    
    if len(parts) < 2:
        raise ValueError("Invalid cache key format")
    
    prefix = parts[0]
    
    if prefix == EMBED_PREFIX:
        if len(parts) == 3:
            return {
                "type": "frame_embedding",
                "video_hash": parts[1],
                "frame_number": int(parts[2])
            }
        elif len(parts) == 5 and parts[2] == "batch":
            return {
                "type": "frame_batch",
                "video_hash": parts[1],
                "frame_start": int(parts[3]),
                "frame_end": int(parts[4])
            }
    elif prefix == ANALYSIS_PREFIX:
        return {
            "type": "analysis",
            "analysis_id": parts[1]
        }
    elif prefix == RESULT_PREFIX:
        return {
            "type": "result",
            "result_id": parts[1]
        }
    elif prefix == SESSION_PREFIX:
        return {
            "type": "session",
            "session_id": parts[1]
        }
    
    raise ValueError(f"Unknown cache key format: {cache_key}")


def get_cache_performance_metrics() -> Dict[str, Any]:
    """
    Get cache performance metrics and configuration.
    
    Returns:
        Dict[str, Any]: Cache performance metrics
    """
    return {
        "cache_types": {
            "embedding": {
                "prefix": EMBED_PREFIX,
                "ttl_seconds": EMBEDDING_CACHE_TTL,
                "performance_target_ms": 100,
                "description": "Frame-level embedding cache for sub-100ms retrieval"
            },
            "analysis": {
                "prefix": ANALYSIS_PREFIX,
                "ttl_seconds": ANALYSIS_CACHE_TTL,
                "performance_target_ms": 200,
                "description": "Analysis results cache"
            },
            "result": {
                "prefix": RESULT_PREFIX,
                "ttl_seconds": RESULT_CACHE_TTL,
                "performance_target_ms": 150,
                "description": "Detection results cache"
            },
            "session": {
                "prefix": SESSION_PREFIX,
                "ttl_seconds": SESSION_CACHE_TTL,
                "performance_target_ms": 50,
                "description": "User session cache"
            }
        },
        "total_cache_types": 4,
        "default_embedding_ttl": EMBEDDING_CACHE_TTL,
        "max_key_length": 128  # Redis recommended max key length
    }
