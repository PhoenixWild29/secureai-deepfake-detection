#!/usr/bin/env python3
"""
Hash Generation Utilities
Utilities for generating content hashes for video files to enable deduplication
"""

import hashlib
import asyncio
import aiofiles
from typing import Optional, Dict, Any
from pathlib import Path


class HashGenerator:
    """
    Utility class for generating various types of content hashes.
    """
    
    @staticmethod
    async def generate_content_hash(
        content: bytes,
        algorithm: str = 'sha256',
        chunk_size: int = 8192
    ) -> str:
        """
        Generate hash for file content.
        
        Args:
            content: File content bytes
            algorithm: Hash algorithm (sha256, sha1, md5)
            chunk_size: Chunk size for processing large files
            
        Returns:
            Hexadecimal hash string
        """
        if algorithm not in ['sha256', 'sha1', 'md5']:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
        
        hash_func = getattr(hashlib, algorithm)()
        
        # Process content in chunks for memory efficiency
        start = 0
        while start < len(content):
            end = min(start + chunk_size, len(content))
            hash_func.update(content[start:end])
            start = end
        
        return hash_func.hexdigest()
    
    @staticmethod
    async def generate_file_hash(
        file_path: str,
        algorithm: str = 'sha256',
        chunk_size: int = 8192
    ) -> str:
        """
        Generate hash for a file on disk.
        
        Args:
            file_path: Path to the file
            algorithm: Hash algorithm (sha256, sha1, md5)
            chunk_size: Chunk size for reading file
            
        Returns:
            Hexadecimal hash string
        """
        if algorithm not in ['sha256', 'sha1', 'md5']:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
        
        hash_func = getattr(hashlib, algorithm)()
        
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                while chunk := await f.read(chunk_size):
                    hash_func.update(chunk)
            
            return hash_func.hexdigest()
            
        except Exception as e:
            raise IOError(f"Failed to read file {file_path}: {str(e)}")
    
    @staticmethod
    async def generate_video_hash(
        file_path: str,
        include_metadata: bool = False,
        sample_frames: bool = True,
        max_sample_frames: int = 10
    ) -> Dict[str, str]:
        """
        Generate comprehensive hash for video files.
        
        Args:
            file_path: Path to the video file
            include_metadata: Whether to include metadata in hash
            sample_frames: Whether to sample video frames for hash
            max_sample_frames: Maximum number of frames to sample
            
        Returns:
            Dictionary with different hash types
        """
        try:
            # Generate content hash (entire file)
            content_hash = await HashGenerator.generate_file_hash(file_path, 'sha256')
            
            result = {
                'content_hash': content_hash,
                'file_hash': content_hash  # Primary hash for deduplication
            }
            
            # Generate metadata hash if requested
            if include_metadata:
                metadata_hash = await HashGenerator._generate_metadata_hash(file_path)
                result['metadata_hash'] = metadata_hash
            
            # Generate frame sample hash if requested
            if sample_frames:
                frame_hash = await HashGenerator._generate_frame_sample_hash(
                    file_path, max_sample_frames
                )
                result['frame_hash'] = frame_hash
            
            return result
            
        except Exception as e:
            raise ValueError(f"Failed to generate video hash: {str(e)}")
    
    @staticmethod
    async def _generate_metadata_hash(file_path: str) -> str:
        """
        Generate hash based on video metadata.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            Hexadecimal hash string
        """
        try:
            import ffmpeg
            
            # Extract metadata
            probe = ffmpeg.probe(file_path)
            video_stream = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
                None
            )
            
            if not video_stream:
                raise ValueError("No video stream found")
            
            # Create metadata string for hashing
            metadata_fields = [
                video_stream.get('codec_name', ''),
                video_stream.get('width', ''),
                video_stream.get('height', ''),
                video_stream.get('duration', ''),
                video_stream.get('bit_rate', ''),
                video_stream.get('r_frame_rate', '')
            ]
            
            metadata_string = '|'.join(str(field) for field in metadata_fields)
            
            # Generate hash
            return hashlib.sha256(metadata_string.encode()).hexdigest()
            
        except ImportError:
            # Fallback if ffmpeg-python is not available
            return hashlib.sha256(file_path.encode()).hexdigest()
        except Exception as e:
            # Fallback on any error
            return hashlib.sha256(file_path.encode()).hexdigest()
    
    @staticmethod
    async def _generate_frame_sample_hash(
        file_path: str,
        max_frames: int = 10
    ) -> str:
        """
        Generate hash based on sampled video frames.
        
        Args:
            file_path: Path to the video file
            max_frames: Maximum number of frames to sample
            
        Returns:
            Hexadecimal hash string
        """
        try:
            import cv2
            
            # Open video
            cap = cv2.VideoCapture(file_path)
            
            if not cap.isOpened():
                raise ValueError("Failed to open video file")
            
            # Get total frame count
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if total_frames == 0:
                cap.release()
                raise ValueError("Video has no frames")
            
            # Calculate frame sampling interval
            sample_interval = max(1, total_frames // max_frames)
            
            frame_hashes = []
            
            for i in range(0, total_frames, sample_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    # Convert frame to grayscale and resize for consistency
                    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    resized_frame = cv2.resize(gray_frame, (64, 64))
                    
                    # Generate hash for frame
                    frame_bytes = resized_frame.tobytes()
                    frame_hash = hashlib.md5(frame_bytes).hexdigest()
                    frame_hashes.append(frame_hash)
                
                if len(frame_hashes) >= max_frames:
                    break
            
            cap.release()
            
            if not frame_hashes:
                raise ValueError("No frames could be extracted")
            
            # Combine frame hashes
            combined_hash = hashlib.sha256('|'.join(frame_hashes).encode()).hexdigest()
            return combined_hash
            
        except ImportError:
            # Fallback if OpenCV is not available
            return hashlib.sha256(file_path.encode()).hexdigest()
        except Exception as e:
            # Fallback on any error
            return hashlib.sha256(file_path.encode()).hexdigest()
    
    @staticmethod
    def generate_quick_hash(content: bytes) -> str:
        """
        Generate a quick hash for small content (synchronous).
        
        Args:
            content: Content bytes
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content).hexdigest()
    
    @staticmethod
    def generate_hash_for_deduplication(
        content: bytes,
        filename: Optional[str] = None,
        file_size: Optional[int] = None
    ) -> str:
        """
        Generate hash optimized for deduplication.
        
        This method creates a hash that can be used to identify duplicate files
        regardless of filename or metadata differences.
        
        Args:
            content: File content bytes
            filename: Optional filename (not used in hash calculation)
            file_size: Optional file size (not used in hash calculation)
            
        Returns:
            Hexadecimal hash string for deduplication
        """
        # Use SHA-256 for content-based deduplication
        return hashlib.sha256(content).hexdigest()


# Convenience functions
async def generate_content_hash(
    content: bytes,
    algorithm: str = 'sha256'
) -> str:
    """
    Generate hash for content bytes.
    
    Args:
        content: Content bytes
        algorithm: Hash algorithm
        
    Returns:
        Hexadecimal hash string
    """
    return await HashGenerator.generate_content_hash(content, algorithm)


async def generate_file_hash(
    file_path: str,
    algorithm: str = 'sha256'
) -> str:
    """
    Generate hash for a file.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm
        
    Returns:
        Hexadecimal hash string
    """
    return await HashGenerator.generate_file_hash(file_path, algorithm)


async def generate_video_hash(
    file_path: str,
    include_metadata: bool = False,
    sample_frames: bool = True
) -> Dict[str, str]:
    """
    Generate comprehensive hash for video files.
    
    Args:
        file_path: Path to the video file
        include_metadata: Whether to include metadata
        sample_frames: Whether to sample frames
        
    Returns:
        Dictionary with hash information
    """
    return await HashGenerator.generate_video_hash(
        file_path, include_metadata, sample_frames
    )


def generate_quick_hash(content: bytes) -> str:
    """
    Generate quick hash for small content.
    
    Args:
        content: Content bytes
        
    Returns:
        Hexadecimal hash string
    """
    return HashGenerator.generate_quick_hash(content)


def generate_hash_for_deduplication(content: bytes) -> str:
    """
    Generate hash for deduplication purposes.
    
    Args:
        content: File content bytes
        
    Returns:
        Hexadecimal hash string
    """
    return HashGenerator.generate_hash_for_deduplication(content)


# Export main components
__all__ = [
    'HashGenerator',
    'generate_content_hash',
    'generate_file_hash',
    'generate_video_hash',
    'generate_quick_hash',
    'generate_hash_for_deduplication'
]
