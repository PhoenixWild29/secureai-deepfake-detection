#!/usr/bin/env python3
"""
Video Path Management Utility
Provides consistent, reliable path resolution for video files across the application.
This is a long-term solution for video file management.
"""
import os
from pathlib import Path
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

# Standard video storage locations (in order of preference)
VIDEO_STORAGE_LOCATIONS = [
    '/app/uploads',           # Container mount point (primary)
    'uploads',                 # Relative path (fallback)
    './uploads',               # Current directory relative
    os.path.expanduser('~/secureai-deepfake-detection/uploads'),  # User home
]

# Standard test video locations
TEST_VIDEO_LOCATIONS = [
    '/app/uploads',
    'uploads',
    './uploads',
    '/app/test_videos',
    'test_videos',
    './test_videos',
    '.',  # Root directory
]


class VideoPathManager:
    """
    Centralized video path management for long-term reliability.
    Handles path resolution, directory creation, and file discovery.
    """
    
    def __init__(self):
        self.uploads_dir = self._find_uploads_directory()
        self.test_videos_dir = self._find_test_videos_directory()
        logger.info(f"VideoPathManager initialized: uploads={self.uploads_dir}, test_videos={self.test_videos_dir}")
    
    def _find_uploads_directory(self) -> Path:
        """Find or create the uploads directory"""
        for location in VIDEO_STORAGE_LOCATIONS:
            path = Path(location)
            if path.exists() and path.is_dir():
                logger.debug(f"Found uploads directory: {path}")
                return path
        
        # Create uploads directory in first writable location
        for location in VIDEO_STORAGE_LOCATIONS:
            try:
                path = Path(location)
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created uploads directory: {path}")
                return path
            except (PermissionError, OSError) as e:
                logger.debug(f"Cannot create directory at {location}: {e}")
                continue
        
        # Fallback to current directory
        fallback = Path('uploads')
        fallback.mkdir(exist_ok=True)
        logger.warning(f"Using fallback uploads directory: {fallback}")
        return fallback
    
    def _find_test_videos_directory(self) -> Optional[Path]:
        """Find test videos directory"""
        for location in TEST_VIDEO_LOCATIONS:
            path = Path(location)
            if path.exists() and path.is_dir():
                return path
        return None
    
    def resolve_video_path(self, video_path: str) -> Optional[Path]:
        """
        Resolve video file path, checking multiple locations.
        
        Args:
            video_path: Video file path (can be relative, absolute, or just filename)
            
        Returns:
            Resolved Path object if found, None otherwise
        """
        # If absolute path and exists, return it
        path = Path(video_path)
        if path.is_absolute() and path.exists():
            return path
        
        # Try as relative path
        if path.exists():
            return path
        
        # Try in uploads directory
        uploads_path = self.uploads_dir / path.name
        if uploads_path.exists():
            return uploads_path
        
        # Try in test videos directory
        if self.test_videos_dir:
            test_path = self.test_videos_dir / path.name
            if test_path.exists():
                return test_path
        
        # Try all standard locations
        for location in VIDEO_STORAGE_LOCATIONS + TEST_VIDEO_LOCATIONS:
            test_path = Path(location) / path.name
            if test_path.exists():
                return test_path
        
        logger.warning(f"Video file not found: {video_path}")
        return None
    
    def find_all_videos(self, max_count: Optional[int] = None, 
                       extensions: List[str] = None) -> List[Path]:
        """
        Find all video files in standard locations.
        
        Args:
            max_count: Maximum number of videos to return (None for all)
            extensions: List of file extensions to search for (default: ['.mp4', '.avi', '.mov'])
            
        Returns:
            List of Path objects for found videos
        """
        if extensions is None:
            extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        
        videos = []
        searched_locations = set()
        
        # Search in uploads directory
        if self.uploads_dir.exists():
            for ext in extensions:
                found = list(self.uploads_dir.glob(f'*{ext}'))
                videos.extend(found)
                searched_locations.add(str(self.uploads_dir))
        
        # Search in test videos directory
        if self.test_videos_dir and self.test_videos_dir.exists():
            for ext in extensions:
                found = list(self.test_videos_dir.glob(f'*{ext}'))
                videos.extend(found)
                searched_locations.add(str(self.test_videos_dir))
        
        # Search in other standard locations
        for location in TEST_VIDEO_LOCATIONS:
            if location in searched_locations:
                continue
            path = Path(location)
            if path.exists() and path.is_dir():
                for ext in extensions:
                    found = list(path.glob(f'*{ext}'))
                    videos.extend(found)
                searched_locations.add(location)
        
        # Remove duplicates
        videos = list(set(videos))
        
        # Sort by modification time (newest first)
        videos.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
        
        if max_count:
            videos = videos[:max_count]
        
        logger.info(f"Found {len(videos)} videos in {len(searched_locations)} locations")
        return videos
    
    def get_uploads_directory(self) -> Path:
        """Get the uploads directory path"""
        return self.uploads_dir
    
    def ensure_uploads_directory(self) -> Path:
        """Ensure uploads directory exists and is writable"""
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        return self.uploads_dir


# Global instance
_video_path_manager = None

def get_video_path_manager() -> VideoPathManager:
    """Get or create global VideoPathManager instance"""
    global _video_path_manager
    if _video_path_manager is None:
        _video_path_manager = VideoPathManager()
    return _video_path_manager

