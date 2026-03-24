#!/usr/bin/env python3
"""
API v1 endpoints package.
"""

from .video_upload import router as video_upload_router
from .heatmap import router as heatmap_router

__all__ = [
    'video_upload_router',
    'heatmap_router'
]