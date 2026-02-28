#!/usr/bin/env python3
"""
Video Frame Extractor
Module for extracting frames from video files with GPU optimization and memory efficiency
"""

import os
import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple, Generator
from pathlib import Path
from datetime import datetime, timezone
import torch
import torchvision.transforms as transforms
from PIL import Image
import gc

logger = logging.getLogger(__name__)


class VideoFrameExtractor:
    """
    Video frame extractor with GPU optimization and memory efficiency.
    Supports various video formats and provides frame preprocessing capabilities.
    """
    
    def __init__(
        self,
        target_size: Tuple[int, int] = (224, 224),
        sampling_rate: int = 1,
        max_frames: int = 1000,
        enable_gpu: bool = True,
        gpu_memory_fraction: float = 0.8
    ):
        """
        Initialize video frame extractor.
        
        Args:
            target_size: Target frame size (width, height)
            sampling_rate: Frame sampling rate (1 = every frame, 2 = every 2nd frame, etc.)
            max_frames: Maximum number of frames to extract
            enable_gpu: Whether to use GPU acceleration
            gpu_memory_fraction: GPU memory fraction to use
        """
        self.target_size = target_size
        self.sampling_rate = sampling_rate
        self.max_frames = max_frames
        self.enable_gpu = enable_gpu
        self.gpu_memory_fraction = gpu_memory_fraction
        
        # GPU setup
        self.device = None
        if self.enable_gpu and torch.cuda.is_available():
            self.device = torch.device('cuda')
            torch.cuda.set_per_process_memory_fraction(self.gpu_memory_fraction)
            logger.info(f"GPU acceleration enabled: {torch.cuda.get_device_name()}")
        else:
            self.device = torch.device('cpu')
            logger.info("GPU acceleration disabled, using CPU")
        
        # Frame preprocessing transforms
        self.transform = transforms.Compose([
            transforms.Resize(self.target_size),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],  # ImageNet normalization
                std=[0.229, 0.224, 0.225]
            )
        ])
        
        # Supported video formats
        self.supported_formats = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']
        
        # Performance metrics
        self.extraction_metrics = {
            'total_frames_extracted': 0,
            'total_processing_time': 0.0,
            'average_frame_time': 0.0,
            'memory_usage_mb': 0.0
        }
    
    def validate_video_file(self, video_path: str) -> bool:
        """
        Validate video file format and accessibility.
        
        Args:
            video_path: Path to video file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return False
            
            # Check file extension
            file_ext = Path(video_path).suffix.lower()
            if file_ext not in self.supported_formats:
                logger.error(f"Unsupported video format: {file_ext}")
                return False
            
            # Try to open video file
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Cannot open video file: {video_path}")
                return False
            
            # Check if video has frames
            ret, frame = cap.read()
            cap.release()
            
            if not ret or frame is None:
                logger.error(f"Video file has no readable frames: {video_path}")
                return False
            
            logger.info(f"Video file validation successful: {video_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating video file: {str(e)}")
            return False
    
    def get_video_info(self, video_path: str) -> Optional[Dict[str, Any]]:
        """
        Get video file information.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Video information dictionary or None if error
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            video_info = {
                'file_path': video_path,
                'filename': os.path.basename(video_path),
                'file_size_mb': os.path.getsize(video_path) / (1024 * 1024),
                'duration_seconds': duration,
                'fps': fps,
                'frame_count': frame_count,
                'width': width,
                'height': height,
                'aspect_ratio': width / height if height > 0 else 0,
                'format': Path(video_path).suffix.lower()
            }
            
            logger.info(f"Video info extracted: {video_info['filename']}")
            return video_info
            
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            return None
    
    def extract_frames(
        self,
        video_path: str,
        start_frame: int = 0,
        end_frame: Optional[int] = None
    ) -> List[np.ndarray]:
        """
        Extract frames from video file.
        
        Args:
            video_path: Path to video file
            start_frame: Starting frame number
            end_frame: Ending frame number (None for all frames)
            
        Returns:
            List of extracted frames as numpy arrays
        """
        start_time = datetime.now()
        frames = []
        
        try:
            if not self.validate_video_file(video_path):
                return frames
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Cannot open video file: {video_path}")
                return frames
            
            # Set starting position
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            frame_number = start_frame
            extracted_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break
                
                # Check if we've reached the end frame
                if end_frame is not None and frame_number >= end_frame:
                    break
                
                # Check if we've reached max frames
                if extracted_count >= self.max_frames:
                    logger.warning(f"Reached maximum frames limit: {self.max_frames}")
                    break
                
                # Apply sampling rate
                if frame_number % self.sampling_rate == 0:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frames.append(frame_rgb)
                    extracted_count += 1
                
                frame_number += 1
            
            cap.release()
            
            # Update metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            self.extraction_metrics['total_frames_extracted'] += len(frames)
            self.extraction_metrics['total_processing_time'] += processing_time
            self.extraction_metrics['average_frame_time'] = (
                self.extraction_metrics['total_processing_time'] / 
                max(self.extraction_metrics['total_frames_extracted'], 1)
            )
            
            logger.info(f"Extracted {len(frames)} frames from {video_path} in {processing_time:.2f}s")
            return frames
            
        except Exception as e:
            logger.error(f"Error extracting frames: {str(e)}")
            return []
    
    def extract_frames_generator(
        self,
        video_path: str,
        batch_size: int = 32
    ) -> Generator[List[np.ndarray], None, None]:
        """
        Extract frames in batches using generator for memory efficiency.
        
        Args:
            video_path: Path to video file
            batch_size: Number of frames per batch
            
        Yields:
            Batches of frames as numpy arrays
        """
        try:
            if not self.validate_video_file(video_path):
                return
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Cannot open video file: {video_path}")
                return
            
            frame_batch = []
            frame_number = 0
            extracted_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break
                
                # Check if we've reached max frames
                if extracted_count >= self.max_frames:
                    break
                
                # Apply sampling rate
                if frame_number % self.sampling_rate == 0:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_batch.append(frame_rgb)
                    extracted_count += 1
                    
                    # Yield batch when full
                    if len(frame_batch) >= batch_size:
                        yield frame_batch
                        frame_batch = []
                        
                        # Force garbage collection for memory management
                        gc.collect()
                
                frame_number += 1
            
            # Yield remaining frames
            if frame_batch:
                yield frame_batch
            
            cap.release()
            
        except Exception as e:
            logger.error(f"Error in frame extraction generator: {str(e)}")
    
    def preprocess_frames(self, frames: List[np.ndarray]) -> torch.Tensor:
        """
        Preprocess frames for ML model input.
        
        Args:
            frames: List of frames as numpy arrays
            
        Returns:
            Preprocessed frames as PyTorch tensor
        """
        try:
            if not frames:
                return torch.empty(0)
            
            processed_frames = []
            
            for frame in frames:
                # Convert numpy array to PIL Image
                pil_image = Image.fromarray(frame)
                
                # Apply transforms
                processed_frame = self.transform(pil_image)
                processed_frames.append(processed_frame)
            
            # Stack frames into batch tensor
            batch_tensor = torch.stack(processed_frames)
            
            # Move to device if GPU is available
            if self.device.type == 'cuda':
                batch_tensor = batch_tensor.to(self.device)
            
            logger.debug(f"Preprocessed {len(frames)} frames to tensor shape: {batch_tensor.shape}")
            return batch_tensor
            
        except Exception as e:
            logger.error(f"Error preprocessing frames: {str(e)}")
            return torch.empty(0)
    
    def extract_and_preprocess_frames(
        self,
        video_path: str,
        batch_size: int = 32
    ) -> Generator[torch.Tensor, None, None]:
        """
        Extract and preprocess frames in batches for ML inference.
        
        Args:
            video_path: Path to video file
            batch_size: Number of frames per batch
            
        Yields:
            Batches of preprocessed frames as PyTorch tensors
        """
        try:
            for frame_batch in self.extract_frames_generator(video_path, batch_size):
                processed_batch = self.preprocess_frames(frame_batch)
                if processed_batch.numel() > 0:  # Check if tensor is not empty
                    yield processed_batch
                    
                    # Clear GPU memory if using GPU
                    if self.device.type == 'cuda':
                        torch.cuda.empty_cache()
                        
        except Exception as e:
            logger.error(f"Error in extract and preprocess: {str(e)}")
    
    def extract_key_frames(
        self,
        video_path: str,
        num_key_frames: int = 10
    ) -> List[np.ndarray]:
        """
        Extract key frames using scene detection.
        
        Args:
            video_path: Path to video file
            num_key_frames: Number of key frames to extract
            
        Returns:
            List of key frames as numpy arrays
        """
        try:
            if not self.validate_video_file(video_path):
                return []
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return []
            
            # Get total frame count
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Calculate frame indices for key frames
            if total_frames <= num_key_frames:
                # If video has fewer frames than requested, extract all
                frame_indices = list(range(total_frames))
            else:
                # Distribute key frames evenly
                frame_indices = [
                    int(i * total_frames / num_key_frames) 
                    for i in range(num_key_frames)
                ]
            
            key_frames = []
            
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    key_frames.append(frame_rgb)
            
            cap.release()
            
            logger.info(f"Extracted {len(key_frames)} key frames from {video_path}")
            return key_frames
            
        except Exception as e:
            logger.error(f"Error extracting key frames: {str(e)}")
            return []
    
    def get_frame_at_timestamp(
        self,
        video_path: str,
        timestamp_seconds: float
    ) -> Optional[np.ndarray]:
        """
        Extract frame at specific timestamp.
        
        Args:
            video_path: Path to video file
            timestamp_seconds: Timestamp in seconds
            
        Returns:
            Frame at timestamp or None if error
        """
        try:
            if not self.validate_video_file(video_path):
                return None
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None
            
            # Get FPS to calculate frame number
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                cap.release()
                return None
            
            # Calculate frame number
            frame_number = int(timestamp_seconds * fps)
            
            # Set frame position
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                logger.debug(f"Extracted frame at {timestamp_seconds}s from {video_path}")
                return frame_rgb
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting frame at timestamp: {str(e)}")
            return None
    
    def resize_frame(self, frame: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
        """
        Resize frame to target size.
        
        Args:
            frame: Input frame as numpy array
            target_size: Target size (width, height)
            
        Returns:
            Resized frame
        """
        try:
            return cv2.resize(frame, target_size, interpolation=cv2.INTER_LANCZOS4)
        except Exception as e:
            logger.error(f"Error resizing frame: {str(e)}")
            return frame
    
    def get_extraction_metrics(self) -> Dict[str, Any]:
        """
        Get frame extraction performance metrics.
        
        Returns:
            Performance metrics dictionary
        """
        return {
            'total_frames_extracted': self.extraction_metrics['total_frames_extracted'],
            'total_processing_time': self.extraction_metrics['total_processing_time'],
            'average_frame_time': self.extraction_metrics['average_frame_time'],
            'frames_per_second': (
                1.0 / self.extraction_metrics['average_frame_time'] 
                if self.extraction_metrics['average_frame_time'] > 0 else 0
            ),
            'device': str(self.device),
            'gpu_enabled': self.enable_gpu and torch.cuda.is_available(),
            'target_size': self.target_size,
            'sampling_rate': self.sampling_rate,
            'max_frames': self.max_frames
        }
    
    def reset_metrics(self):
        """Reset performance metrics."""
        self.extraction_metrics = {
            'total_frames_extracted': 0,
            'total_processing_time': 0.0,
            'average_frame_time': 0.0,
            'memory_usage_mb': 0.0
        }
    
    def cleanup(self):
        """Clean up resources and free memory."""
        try:
            # Clear GPU memory
            if self.device.type == 'cuda':
                torch.cuda.empty_cache()
            
            # Force garbage collection
            gc.collect()
            
            logger.info("Frame extractor cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")


# Global frame extractor instance
frame_extractor = VideoFrameExtractor()


# Utility functions for easy access
def extract_frames(video_path: str, **kwargs) -> List[np.ndarray]:
    """Extract frames from video file."""
    return frame_extractor.extract_frames(video_path, **kwargs)


def extract_frames_generator(video_path: str, batch_size: int = 32) -> Generator[List[np.ndarray], None, None]:
    """Extract frames in batches using generator."""
    return frame_extractor.extract_frames_generator(video_path, batch_size)


def extract_and_preprocess_frames(video_path: str, batch_size: int = 32) -> Generator[torch.Tensor, None, None]:
    """Extract and preprocess frames for ML inference."""
    return frame_extractor.extract_and_preprocess_frames(video_path, batch_size)


def get_video_info(video_path: str) -> Optional[Dict[str, Any]]:
    """Get video file information."""
    return frame_extractor.get_video_info(video_path)


def validate_video_file(video_path: str) -> bool:
    """Validate video file format and accessibility."""
    return frame_extractor.validate_video_file(video_path)


# Export
__all__ = [
    'VideoFrameExtractor',
    'frame_extractor',
    'extract_frames',
    'extract_frames_generator',
    'extract_and_preprocess_frames',
    'get_video_info',
    'validate_video_file'
]
