#!/usr/bin/env python3
"""
Enhanced Ensemble Detector: CLIP + ResNet50 + LAA-Net
Combines multiple models for superior deepfake detection
"""
import os
import sys
import torch
import numpy as np
from typing import Dict, List, Any, Optional
from PIL import Image
import cv2
import logging

logger = logging.getLogger(__name__)

# Import models
try:
    from .enhanced_detector import EnhancedDetector
    from .deepfake_classifier import ResNetDeepfakeClassifier
except ImportError:
    from enhanced_detector import EnhancedDetector
    from deepfake_classifier import ResNetDeepfakeClassifier

class EnsembleDetector:
    """
    Enhanced ensemble combining CLIP, ResNet50, and LAA-Net
    Provides superior accuracy through multi-model fusion
    """
    
    def __init__(self, 
                 clip_model_name: str = 'ViT-B-32',
                 clip_pretrained: str = 'laion2b_s34b_b79k',
                 resnet_model_path: Optional[str] = None,
                 device: Optional[str] = None,
                 ensemble_weights: Optional[Dict[str, float]] = None):
        """
        Initialize ensemble detector
        
        Args:
            clip_model_name: CLIP model variant
            clip_pretrained: CLIP pretrained weights
            resnet_model_path: Path to ResNet50 weights
            device: Device to use ('cuda', 'cpu', or None for auto)
            ensemble_weights: Custom weights for ensemble (default: adaptive)
        """
        # Force CPU if CUDA_VISIBLE_DEVICES is set to empty
        if os.getenv('CUDA_VISIBLE_DEVICES') == '':
            self.device = 'cpu'
        else:
            self.device = device if device else ('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"🔧 Initializing EnsembleDetector on device: {self.device}")
        
        # Initialize CLIP detector (EnhancedDetector)
        logger.info("📦 Loading CLIP detector...")
        self.clip_detector = EnhancedDetector(
            device=self.device,
            clip_model_name=clip_model_name,
            clip_pretrained=clip_pretrained
        )
        
        # Initialize ResNet50 (with timeout to prevent hanging)
        logger.info("📦 Loading ResNet50 detector...")
        self.resnet_model = None
        
        try:
            # Try to create ResNet classifier with timeout
            import threading
            resnet_created = [False]
            resnet_error = [None]
            
            def create_resnet():
                try:
                    resnet_created[0] = True
                    return ResNetDeepfakeClassifier(model_name='resnet50', pretrained=False)
                except Exception as e:
                    resnet_error[0] = e
                    return None
            
            # Create ResNet with 10 second timeout
            resnet_thread = threading.Thread(target=lambda: setattr(self, 'resnet_model', create_resnet()), daemon=True)
            resnet_thread.start()
            resnet_thread.join(timeout=10.0)
            
            if resnet_thread.is_alive():
                logger.warning("⚠️  ResNet50 creation timed out (>10s). Skipping ResNet.")
                self.resnet_model = None
            elif resnet_error[0]:
                logger.warning(f"⚠️  ResNet50 creation failed: {resnet_error[0]}. Skipping ResNet.")
                self.resnet_model = None
            elif self.resnet_model is None:
                logger.warning("⚠️  ResNet50 not created. Ensemble will use CLIP only.")
        except Exception as e:
            logger.warning(f"⚠️  ResNet50 initialization error: {e}. Skipping ResNet.")
            self.resnet_model = None
        
        # Load ResNet weights (only if model was created)
        if self.resnet_model is not None:
            resnet_paths = [
                resnet_model_path,
                'ai_model/resnet_resnet50_final.pth',
                'ai_model/resnet_resnet50_best.pth',
                'resnet_resnet50_final.pth',
                'resnet_resnet50_best.pth'
            ]
            
            resnet_loaded = False
            for path in resnet_paths:
                if path and os.path.exists(path):
                    try:
                        # Load with timeout
                        import threading
                        load_success = [False]
                        
                        def load_weights():
                            try:
                                self.resnet_model.load_state_dict(torch.load(path, map_location=self.device))
                                self.resnet_model.to(self.device)
                                self.resnet_model.eval()
                                load_success[0] = True
                            except Exception as e:
                                logger.warning(f"Failed to load weights: {e}")
                        
                        load_thread = threading.Thread(target=load_weights, daemon=True)
                        load_thread.start()
                        load_thread.join(timeout=10.0)
                        
                        if load_thread.is_alive():
                            logger.warning(f"⚠️  ResNet weight loading timed out for {path}")
                            continue
                        
                        if load_success[0]:
                            logger.info(f"✅ ResNet50 loaded from: {path}")
                            resnet_loaded = True
                            break
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to load ResNet from {path}: {e}")
                        continue
            
            if not resnet_loaded:
                logger.warning("⚠️  ResNet50 weights not loaded. Ensemble will use CLIP only.")
                self.resnet_model = None
        
        # Ensemble weights (can be adaptive based on confidence)
        self.ensemble_weights = ensemble_weights or {
            'clip': 0.4,      # CLIP: good for zero-shot, generalizable
            'resnet': 0.5,    # ResNet: trained specifically for deepfakes
            'laa': 0.1        # LAA-Net: when available, adds quality-agnostic detection
        }
        
        # Normalize weights
        total_weight = sum(self.ensemble_weights.values())
        self.ensemble_weights = {k: v/total_weight for k, v in self.ensemble_weights.items()}
        
        logger.info(f"✅ EnsembleDetector initialized")
        logger.info(f"   Ensemble weights: {self.ensemble_weights}")
    
    def extract_frames(self, video_path: str, num_frames: int = 16) -> List[Image.Image]:
        """Extract frames from video (reuse from EnhancedDetector)"""
        return self.clip_detector.extract_frames(video_path, num_frames)
    
    def clip_detect(self, frames: List[Image.Image]) -> float:
        """Get CLIP detection probability"""
        return self.clip_detector.clip_detect_frames(frames)
    
    def resnet_detect(self, frames: List[Image.Image]) -> float:
        """Get ResNet50 detection probability"""
        if self.resnet_model is None:
            return 0.5  # Neutral if ResNet not available
        
        from torchvision import transforms
        
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        fake_probs = []
        
        for frame in frames:
            try:
                # Convert PIL to tensor
                frame_tensor = transform(frame).unsqueeze(0).to(self.device)
                
                with torch.no_grad():
                    output = self.resnet_model(frame_tensor)
                    probs = torch.softmax(output, dim=1)
                    fake_prob = probs[0][1].item()  # Probability of fake (class 1)
                
                fake_probs.append(fake_prob)
            except Exception as e:
                logger.warning(f"ResNet detection error on frame: {e}")
                continue
        
        if not fake_probs:
            return 0.5  # Neutral if all frames failed
        
        return np.mean(fake_probs)
    
    def laa_detect(self, frames: List[Image.Image]) -> float:
        """Get LAA-Net detection probability"""
        return self.clip_detector.laa_detect_frames(frames)
    
    def adaptive_ensemble(self, 
                         clip_prob: float, 
                         resnet_prob: float, 
                         laa_prob: float) -> Dict[str, Any]:
        """
        Adaptive ensemble with confidence-based weighting
        
        Args:
            clip_prob: CLIP fake probability
            resnet_prob: ResNet50 fake probability
            laa_prob: LAA-Net fake probability
            
        Returns:
            Ensemble results with probabilities and confidence
        """
        # Calculate confidence (distance from 0.5)
        clip_confidence = abs(clip_prob - 0.5) * 2  # 0-1 scale
        resnet_confidence = abs(resnet_prob - 0.5) * 2
        laa_confidence = abs(laa_prob - 0.5) * 2 if self.clip_detector.laa_available else 0
        
        # Adaptive weights based on confidence
        if self.clip_detector.laa_available and laa_confidence > 0.3:
            # All three models available
            total_confidence = clip_confidence + resnet_confidence + laa_confidence
            if total_confidence > 0:
                adaptive_weights = {
                    'clip': clip_confidence / total_confidence,
                    'resnet': resnet_confidence / total_confidence,
                    'laa': laa_confidence / total_confidence
                }
            else:
                adaptive_weights = self.ensemble_weights
        else:
            # Only CLIP + ResNet
            total_confidence = clip_confidence + resnet_confidence
            if total_confidence > 0:
                adaptive_weights = {
                    'clip': clip_confidence / total_confidence,
                    'resnet': resnet_confidence / total_confidence,
                    'laa': 0.0
                }
            else:
                adaptive_weights = {'clip': 0.5, 'resnet': 0.5, 'laa': 0.0}
        
        # Weighted ensemble
        ensemble_prob = (
            adaptive_weights['clip'] * clip_prob +
            adaptive_weights['resnet'] * resnet_prob +
            adaptive_weights['laa'] * laa_prob
        )
        
        # Overall confidence
        overall_confidence = abs(ensemble_prob - 0.5) * 2
        
        return {
            'ensemble_fake_probability': float(ensemble_prob),
            'clip_fake_probability': float(clip_prob),
            'resnet_fake_probability': float(resnet_prob),
            'laa_fake_probability': float(laa_prob),
            'ensemble_weights_used': adaptive_weights,
            'overall_confidence': float(overall_confidence),
            'is_deepfake': ensemble_prob > 0.5
        }
    
    def detect(self, video_path: str, num_frames: int = 16) -> Dict[str, Any]:
        """
        Main detection method: Ensemble of CLIP + ResNet50 + LAA-Net
        
        Args:
            video_path: Path to video file
            num_frames: Number of frames to sample
            
        Returns:
            Detection results with ensemble probabilities
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Extract frames
        frames = self.extract_frames(video_path, num_frames)
        
        if not frames:
            return {
                'error': 'No frames extracted from video',
                'is_deepfake': False,
                'confidence': 0.0
            }
        
        # Run all detectors with progress logging
        logger.debug(f"Running CLIP detection on {len(frames)} frames...")
        clip_prob = self.clip_detect(frames)
        logger.debug(f"CLIP result: {clip_prob:.3f}")
        
        logger.debug(f"Running ResNet detection on {len(frames)} frames...")
        resnet_prob = self.resnet_detect(frames)
        logger.debug(f"ResNet result: {resnet_prob:.3f}")
        
        logger.debug(f"Running LAA-Net detection on {len(frames)} frames...")
        laa_prob = self.laa_detect(frames)
        logger.debug(f"LAA-Net result: {laa_prob:.3f}")
        
        # Adaptive ensemble
        ensemble_results = self.adaptive_ensemble(clip_prob, resnet_prob, laa_prob)
        
        # Determine method used
        if self.clip_detector.laa_available and self.resnet_model is not None:
            method = 'ensemble_clip_resnet_laa'
        elif self.resnet_model is not None:
            method = 'ensemble_clip_resnet'
        else:
            method = 'clip_only'
        
        return {
            **ensemble_results,
            'method': method,
            'num_frames_analyzed': len(frames),
            'resnet_available': self.resnet_model is not None,
            'laa_available': self.clip_detector.laa_available
        }


# Global instance for lazy initialization
_ensemble_instance = None

def get_ensemble_detector() -> EnsembleDetector:
    """Get or create global ensemble detector instance"""
    global _ensemble_instance
    if _ensemble_instance is None:
        _ensemble_instance = EnsembleDetector()
    return _ensemble_instance

def detect_fake_ensemble(video_path: str, num_frames: int = 16) -> Dict[str, Any]:
    """
    Convenience function for ensemble detection
    
    Args:
        video_path: Path to video file
        num_frames: Number of frames to sample
        
    Returns:
        Detection results
    """
    detector = get_ensemble_detector()
    return detector.detect(video_path, num_frames)

