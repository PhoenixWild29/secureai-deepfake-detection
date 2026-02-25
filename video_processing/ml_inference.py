#!/usr/bin/env python3
"""
ML Inference Integration Module
Integration with ML models (ResNet50/CLIP) for generating ensemble embeddings from video frames
"""

import os
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from transformers import CLIPModel, CLIPProcessor
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timezone
import gc
import hashlib
import json

logger = logging.getLogger(__name__)


class ResNet50EmbeddingExtractor:
    """
    ResNet50-based embedding extractor for deepfake detection.
    Provides feature extraction capabilities for video frames.
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        device: Optional[torch.device] = None,
        pretrained: bool = True
    ):
        """
        Initialize ResNet50 embedding extractor.
        
        Args:
            model_path: Path to custom model weights
            device: Device to run inference on
            pretrained: Whether to use pretrained weights
        """
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_path = model_path
        self.pretrained = pretrained
        
        # Load model
        self.model = self._load_model()
        self.model.eval()
        
        # Move to device
        self.model = self.model.to(self.device)
        
        # Preprocessing transforms
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
        
        logger.info(f"ResNet50 embedding extractor initialized on {self.device}")
    
    def _load_model(self) -> nn.Module:
        """Load ResNet50 model."""
        try:
            if self.model_path and os.path.exists(self.model_path):
                # Load custom model
                model = models.resnet50(pretrained=False)
                model.load_state_dict(torch.load(self.model_path, map_location=self.device))
                logger.info(f"Loaded custom ResNet50 model from {self.model_path}")
            else:
                # Load pretrained model
                model = models.resnet50(pretrained=self.pretrained)
                logger.info("Loaded pretrained ResNet50 model")
            
            # Remove final classification layer to get embeddings
            model = nn.Sequential(*list(model.children())[:-1])
            
            return model
            
        except Exception as e:
            logger.error(f"Error loading ResNet50 model: {str(e)}")
            raise
    
    def extract_embeddings(self, frames: torch.Tensor) -> torch.Tensor:
        """
        Extract embeddings from video frames.
        
        Args:
            frames: Batch of preprocessed frames as tensor
            
        Returns:
            Extracted embeddings as tensor
        """
        try:
            with torch.no_grad():
                # Move frames to device
                frames = frames.to(self.device)
                
                # Extract embeddings
                embeddings = self.model(frames)
                
                # Flatten embeddings
                embeddings = embeddings.view(embeddings.size(0), -1)
                
                logger.debug(f"Extracted ResNet50 embeddings shape: {embeddings.shape}")
                return embeddings
                
        except Exception as e:
            logger.error(f"Error extracting ResNet50 embeddings: {str(e)}")
            raise
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return 2048  # ResNet50 feature dimension


class CLIPEmbeddingExtractor:
    """
    CLIP-based embedding extractor for deepfake detection.
    Provides multimodal feature extraction capabilities.
    """
    
    def __init__(
        self,
        model_name: str = 'openai/clip-vit-base-patch32',
        device: Optional[torch.device] = None
    ):
        """
        Initialize CLIP embedding extractor.
        
        Args:
            model_name: CLIP model name
            device: Device to run inference on
        """
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_name = model_name
        
        # Load CLIP model and processor
        self.model = CLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        
        # Move to device
        self.model = self.model.to(self.device)
        self.model.eval()
        
        logger.info(f"CLIP embedding extractor initialized on {self.device}")
    
    def extract_embeddings(self, frames: torch.Tensor) -> torch.Tensor:
        """
        Extract embeddings from video frames using CLIP.
        
        Args:
            frames: Batch of preprocessed frames as tensor
            
        Returns:
            Extracted embeddings as tensor
        """
        try:
            with torch.no_grad():
                # Convert tensor to PIL Images for CLIP processing
                # Assuming frames are normalized, convert back to [0, 1] range
                frames_denorm = frames * torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1).to(self.device)
                frames_denorm = frames_denorm + torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1).to(self.device)
                frames_denorm = torch.clamp(frames_denorm, 0, 1)
                
                # Convert to PIL Images
                pil_images = []
                for i in range(frames.size(0)):
                    img_tensor = frames_denorm[i]
                    img_array = img_tensor.permute(1, 2, 0).cpu().numpy()
                    img_array = (img_array * 255).astype(np.uint8)
                    
                    from PIL import Image
                    pil_img = Image.fromarray(img_array)
                    pil_images.append(pil_img)
                
                # Process with CLIP
                inputs = self.processor(images=pil_images, return_tensors="pt", padding=True)
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                # Extract image features
                image_features = self.model.get_image_features(**inputs)
                
                # Normalize features
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                
                logger.debug(f"Extracted CLIP embeddings shape: {image_features.shape}")
                return image_features
                
        except Exception as e:
            logger.error(f"Error extracting CLIP embeddings: {str(e)}")
            raise
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return 512  # CLIP ViT-B/32 feature dimension


class EnsembleEmbeddingGenerator:
    """
    Ensemble embedding generator combining ResNet50 and CLIP models.
    Provides comprehensive feature extraction for deepfake detection.
    """
    
    def __init__(
        self,
        resnet50_model_path: Optional[str] = None,
        clip_model_name: str = 'openai/clip-vit-base-patch32',
        ensemble_weights: Optional[Dict[str, float]] = None,
        device: Optional[torch.device] = None
    ):
        """
        Initialize ensemble embedding generator.
        
        Args:
            resnet50_model_path: Path to ResNet50 model weights
            clip_model_name: CLIP model name
            ensemble_weights: Weights for ensemble combination
            device: Device to run inference on
        """
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.ensemble_weights = ensemble_weights or {'resnet50': 0.6, 'clip': 0.4}
        
        # Initialize extractors
        self.resnet50_extractor = ResNet50EmbeddingExtractor(
            model_path=resnet50_model_path,
            device=self.device
        )
        
        self.clip_extractor = CLIPEmbeddingExtractor(
            model_name=clip_model_name,
            device=self.device
        )
        
        # Performance metrics
        self.inference_metrics = {
            'total_frames_processed': 0,
            'total_inference_time': 0.0,
            'average_inference_time': 0.0,
            'resnet50_inference_time': 0.0,
            'clip_inference_time': 0.0
        }
        
        logger.info(f"Ensemble embedding generator initialized on {self.device}")
        logger.info(f"Ensemble weights: {self.ensemble_weights}")
    
    def generate_embeddings(self, frames: torch.Tensor) -> Dict[str, Any]:
        """
        Generate ensemble embeddings from video frames.
        
        Args:
            frames: Batch of preprocessed frames as tensor
            
        Returns:
            Dictionary containing embeddings and metadata
        """
        start_time = datetime.now()
        
        try:
            # Extract ResNet50 embeddings
            resnet50_start = datetime.now()
            resnet50_embeddings = self.resnet50_extractor.extract_embeddings(frames)
            resnet50_time = (datetime.now() - resnet50_start).total_seconds()
            
            # Extract CLIP embeddings
            clip_start = datetime.now()
            clip_embeddings = self.clip_extractor.extract_embeddings(frames)
            clip_time = (datetime.now() - clip_start).total_seconds()
            
            # Combine embeddings with weights
            ensemble_embeddings = (
                self.ensemble_weights['resnet50'] * resnet50_embeddings +
                self.ensemble_weights['clip'] * clip_embeddings
            )
            
            # Calculate statistics
            total_time = (datetime.now() - start_time).total_seconds()
            num_frames = frames.size(0)
            
            # Update metrics
            self.inference_metrics['total_frames_processed'] += num_frames
            self.inference_metrics['total_inference_time'] += total_time
            self.inference_metrics['average_inference_time'] = (
                self.inference_metrics['total_inference_time'] / 
                max(self.inference_metrics['total_frames_processed'], 1)
            )
            self.inference_metrics['resnet50_inference_time'] += resnet50_time
            self.inference_metrics['clip_inference_time'] += clip_time
            
            # Create result
            result = {
                'ensemble_embeddings': ensemble_embeddings.cpu().numpy().tolist(),
                'resnet50_embeddings': resnet50_embeddings.cpu().numpy().tolist(),
                'clip_embeddings': clip_embeddings.cpu().numpy().tolist(),
                'metadata': {
                    'num_frames': num_frames,
                    'total_inference_time': total_time,
                    'resnet50_time': resnet50_time,
                    'clip_time': clip_time,
                    'ensemble_weights': self.ensemble_weights,
                    'device': str(self.device),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            }
            
            logger.info(f"Generated ensemble embeddings for {num_frames} frames in {total_time:.3f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error generating ensemble embeddings: {str(e)}")
            raise
    
    def generate_embeddings_batch(
        self,
        frame_batches: List[torch.Tensor]
    ) -> Dict[str, Any]:
        """
        Generate embeddings for multiple batches of frames.
        
        Args:
            frame_batches: List of frame batches as tensors
            
        Returns:
            Dictionary containing combined embeddings and metadata
        """
        try:
            all_ensemble_embeddings = []
            all_resnet50_embeddings = []
            all_clip_embeddings = []
            
            total_frames = 0
            total_time = 0.0
            
            for batch_idx, frames in enumerate(frame_batches):
                logger.debug(f"Processing batch {batch_idx + 1}/{len(frame_batches)}")
                
                batch_result = self.generate_embeddings(frames)
                
                all_ensemble_embeddings.extend(batch_result['ensemble_embeddings'])
                all_resnet50_embeddings.extend(batch_result['resnet50_embeddings'])
                all_clip_embeddings.extend(batch_result['clip_embeddings'])
                
                total_frames += batch_result['metadata']['num_frames']
                total_time += batch_result['metadata']['total_inference_time']
                
                # Clear GPU memory between batches
                if self.device.type == 'cuda':
                    torch.cuda.empty_cache()
            
            # Create combined result
            result = {
                'ensemble_embeddings': all_ensemble_embeddings,
                'resnet50_embeddings': all_resnet50_embeddings,
                'clip_embeddings': all_clip_embeddings,
                'metadata': {
                    'total_frames': total_frames,
                    'total_batches': len(frame_batches),
                    'total_inference_time': total_time,
                    'average_time_per_frame': total_time / max(total_frames, 1),
                    'ensemble_weights': self.ensemble_weights,
                    'device': str(self.device),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            }
            
            logger.info(f"Generated embeddings for {total_frames} frames across {len(frame_batches)} batches")
            return result
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            raise
    
    def get_inference_metrics(self) -> Dict[str, Any]:
        """
        Get inference performance metrics.
        
        Returns:
            Performance metrics dictionary
        """
        return {
            'total_frames_processed': self.inference_metrics['total_frames_processed'],
            'total_inference_time': self.inference_metrics['total_inference_time'],
            'average_inference_time': self.inference_metrics['average_inference_time'],
            'frames_per_second': (
                1.0 / self.inference_metrics['average_inference_time'] 
                if self.inference_metrics['average_inference_time'] > 0 else 0
            ),
            'resnet50_total_time': self.inference_metrics['resnet50_inference_time'],
            'clip_total_time': self.inference_metrics['clip_inference_time'],
            'device': str(self.device),
            'ensemble_weights': self.ensemble_weights
        }
    
    def reset_metrics(self):
        """Reset inference metrics."""
        self.inference_metrics = {
            'total_frames_processed': 0,
            'total_inference_time': 0.0,
            'average_inference_time': 0.0,
            'resnet50_inference_time': 0.0,
            'clip_inference_time': 0.0
        }
    
    def cleanup(self):
        """Clean up resources and free memory."""
        try:
            # Clear GPU memory
            if self.device.type == 'cuda':
                torch.cuda.empty_cache()
            
            # Force garbage collection
            gc.collect()
            
            logger.info("ML inference cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")


class DeepfakeDetector:
    """
    Deepfake detection model using ensemble embeddings.
    Provides confidence scoring and anomaly detection.
    """
    
    def __init__(
        self,
        ensemble_generator: EnsembleEmbeddingGenerator,
        threshold: float = 0.5
    ):
        """
        Initialize deepfake detector.
        
        Args:
            ensemble_generator: Ensemble embedding generator
            threshold: Detection threshold
        """
        self.ensemble_generator = ensemble_generator
        self.threshold = threshold
        
        logger.info(f"Deepfake detector initialized with threshold: {threshold}")
    
    def detect_deepfake(
        self,
        frames: torch.Tensor,
        return_embeddings: bool = False
    ) -> Dict[str, Any]:
        """
        Detect deepfake in video frames.
        
        Args:
            frames: Batch of preprocessed frames as tensor
            return_embeddings: Whether to return embeddings
            
        Returns:
            Detection results dictionary
        """
        try:
            # Generate embeddings
            embedding_result = self.ensemble_generator.generate_embeddings(frames)
            
            # Calculate confidence scores (placeholder logic)
            # In a real implementation, this would use a trained classifier
            ensemble_embeddings = torch.tensor(embedding_result['ensemble_embeddings'])
            
            # Simple anomaly detection based on embedding variance
            embedding_variance = torch.var(ensemble_embeddings, dim=0).mean().item()
            
            # Convert variance to confidence score (higher variance = more suspicious)
            confidence_score = min(embedding_variance * 10, 1.0)  # Scale and cap at 1.0
            
            # Determine if deepfake detected
            is_deepfake = confidence_score > self.threshold
            
            # Create result
            result = {
                'is_deepfake': is_deepfake,
                'confidence_score': confidence_score,
                'threshold': self.threshold,
                'embedding_variance': embedding_variance,
                'num_frames': frames.size(0),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            if return_embeddings:
                result['embeddings'] = embedding_result
            
            logger.info(f"Deepfake detection completed: {is_deepfake} (confidence: {confidence_score:.3f})")
            return result
            
        except Exception as e:
            logger.error(f"Error in deepfake detection: {str(e)}")
            raise


# Global instances
ensemble_generator = EnsembleEmbeddingGenerator()
deepfake_detector = DeepfakeDetector(ensemble_generator)


# Utility functions for easy access
def generate_embeddings(frames: torch.Tensor) -> Dict[str, Any]:
    """Generate ensemble embeddings from frames."""
    return ensemble_generator.generate_embeddings(frames)


def generate_embeddings_batch(frame_batches: List[torch.Tensor]) -> Dict[str, Any]:
    """Generate embeddings for multiple batches of frames."""
    return ensemble_generator.generate_embeddings_batch(frame_batches)


def detect_deepfake(frames: torch.Tensor, return_embeddings: bool = False) -> Dict[str, Any]:
    """Detect deepfake in video frames."""
    return deepfake_detector.detect_deepfake(frames, return_embeddings)


def get_inference_metrics() -> Dict[str, Any]:
    """Get inference performance metrics."""
    return ensemble_generator.get_inference_metrics()


def cleanup_ml_resources():
    """Clean up ML resources and free memory."""
    ensemble_generator.cleanup()


# Export
__all__ = [
    'ResNet50EmbeddingExtractor',
    'CLIPEmbeddingExtractor',
    'EnsembleEmbeddingGenerator',
    'DeepfakeDetector',
    'ensemble_generator',
    'deepfake_detector',
    'generate_embeddings',
    'generate_embeddings_batch',
    'detect_deepfake',
    'get_inference_metrics',
    'cleanup_ml_resources'
]
