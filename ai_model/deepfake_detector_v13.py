#!/usr/bin/env python3
"""
DeepFake Detector V13 Integration
699M parameter ensemble model from Hugging Face
F1 Score: 0.9586 (95.86%) - Better than LAA-Net!
"""
import os
import sys
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Any, Optional
from PIL import Image
import cv2
import logging

logger = logging.getLogger(__name__)

# Force CPU mode if needed
if os.getenv('CUDA_VISIBLE_DEVICES') == '':
    os.environ['CUDA_VISIBLE_DEVICES'] = ''

try:
    from transformers import AutoModel, AutoImageProcessor
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers library not available. Install with: pip install transformers")

class DeepFakeDetectorV13:
    """
    DeepFake Detector V13 from Hugging Face
    Ensemble of ConvNeXt-Large, ViT-Large, Swin-Large
    699M parameters, F1: 0.9586
    """
    
    def __init__(self, device: Optional[str] = None):
        """
        Initialize DeepFake Detector V13
        
        Args:
            device: Device to use ('cuda', 'cpu', or None for auto)
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers library required. Install with: pip install transformers")
        
        # Force CPU if CUDA_VISIBLE_DEVICES is set to empty
        if os.getenv('CUDA_VISIBLE_DEVICES') == '':
            self.device = 'cpu'
        else:
            self.device = device if device else ('cuda' if torch.cuda.is_available() else 'cpu')
        
        logger.info(f"🔧 Initializing DeepFake Detector V13 on device: {self.device}")
        
        self.model = None
        self.processor = None
        self.model_loaded = False
        
        try:
            self._load_model()
        except Exception as e:
            logger.error(f"❌ Failed to load DeepFake Detector V13: {e}")
            logger.info("Continuing without V13 model")
            self.model_loaded = False
    
    def _load_model(self):
        """Load model from Hugging Face"""
        logger.info("📦 Loading DeepFake Detector V13 from Hugging Face...")
        logger.info("   Model: ash12321/deepfake-detector-v13")
        logger.info("   This may take a few minutes on first download...")
        
        try:
            # Load image processor
            self.processor = AutoImageProcessor.from_pretrained(
                "ash12321/deepfake-detector-v13",
                trust_remote_code=True
            )
            
            # Load model
            self.model = AutoModel.from_pretrained(
                "ash12321/deepfake-detector-v13",
                trust_remote_code=True,
                torch_dtype=torch.float32  # Use float32 for CPU compatibility
            )
            
            self.model.to(self.device)
            self.model.eval()
            
            self.model_loaded = True
            logger.info("✅ DeepFake Detector V13 loaded successfully!")
            logger.info(f"   Model size: ~699M parameters")
            logger.info(f"   F1 Score: 0.9586 (95.86%)")
            
        except Exception as e:
            logger.error(f"❌ Error loading DeepFake Detector V13: {e}")
            logger.info("   Make sure transformers and huggingface-hub are installed:")
            logger.info("   pip install transformers huggingface-hub")
            raise
    
    def preprocess_frame(self, frame: Image.Image) -> torch.Tensor:
        """
        Preprocess frame for V13 model
        
        Args:
            frame: PIL Image
            
        Returns:
            Preprocessed tensor
        """
        if not self.processor:
            raise RuntimeError("Model not loaded")
        
        # Convert PIL to numpy array
        frame_array = np.array(frame)
        
        # Process with AutoImageProcessor
        inputs = self.processor(frame_array, return_tensors="pt")
        
        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        return inputs
    
    def detect_frame(self, frame: Image.Image) -> float:
        """
        Detect deepfake probability for a single frame
        
        Args:
            frame: PIL Image
            
        Returns:
            Fake probability (0.0 = real, 1.0 = fake)
        """
        if not self.model_loaded or self.model is None:
            return 0.5  # Neutral if model not loaded
        
        try:
            with torch.no_grad():
                # Preprocess
                inputs = self.preprocess_frame(frame)
                
                # Forward pass
                outputs = self.model(**inputs)
                
                # Extract prediction
                # V13 model structure may vary - adjust based on actual output
                if hasattr(outputs, 'logits'):
                    logits = outputs.logits
                elif hasattr(outputs, 'prediction'):
                    logits = outputs.prediction
                elif isinstance(outputs, torch.Tensor):
                    logits = outputs
                else:
                    # Try to get first tensor from outputs
                    logits = outputs[0] if isinstance(outputs, (tuple, list)) else outputs
                
                # Convert to probability
                if logits.dim() > 1:
                    logits = logits.squeeze()
                
                # Apply sigmoid if needed
                if logits.numel() == 1:
                    prob = torch.sigmoid(logits).item()
                else:
                    # Multi-class: assume binary classification
                    prob = torch.softmax(logits, dim=0)[1].item() if logits.numel() == 2 else torch.sigmoid(logits[0]).item()
                
                return float(prob)
                
        except Exception as e:
            logger.warning(f"⚠️  Error in V13 detection: {e}")
            return 0.5  # Neutral on error
    
    def detect_frames(self, frames: List[Image.Image]) -> float:
        """
        Detect deepfake probability for multiple frames
        
        Args:
            frames: List of PIL Images
            
        Returns:
            Average fake probability
        """
        if not frames:
            return 0.5
        
        probs = []
        for frame in frames:
            prob = self.detect_frame(frame)
            probs.append(prob)
        
        return float(np.mean(probs))


# Global instance for singleton pattern
_v13_instance = None

def get_deepfake_detector_v13(device: Optional[str] = None) -> Optional[DeepFakeDetectorV13]:
    """
    Get or create global DeepFake Detector V13 instance (singleton)
    
    Args:
        device: Device to use
        
    Returns:
        DeepFakeDetectorV13 instance or None if not available
    """
    global _v13_instance
    
    if _v13_instance is None:
        try:
            _v13_instance = DeepFakeDetectorV13(device=device)
        except Exception as e:
            logger.warning(f"Could not create DeepFake Detector V13: {e}")
            return None
    
    return _v13_instance if _v13_instance.model_loaded else None
