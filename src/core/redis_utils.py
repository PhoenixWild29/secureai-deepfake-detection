#!/usr/bin/env python3
"""
Redis utilities for caching conventions
"""

from typing import Final


EMBED_PREFIX: Final[str] = "embed"


def get_frame_embedding_cache_key(video_hash: str, frame_number: int) -> str:
	"""Return standardized Redis key for frame-level embeddings.
	Format: 'embed:{video_hash}:{frame_number}'
	"""
	return f"{EMBED_PREFIX}:{video_hash}:{frame_number}"
