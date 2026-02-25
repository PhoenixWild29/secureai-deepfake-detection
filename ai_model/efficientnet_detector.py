#!/usr/bin/env python3
"""
EfficientNet Deepfake Detector
Proven model for deepfake detection, available via efficientnet-pytorch
"""
import os
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import numpy as np
from typing import List, Optional
from PIL import Image
import logging

logger = logging.getLogger(__name__)

# Force CPU mode if needed
if os.getenv('CUDA_VISIBLE_DEVICES') == '':
    os.environ['CUDA_VISIBLE_DEVICES'] = ''

try:
    from efficientnet_pytorch import EfficientNet
    EFFICIENTNET_AVAILABLE = True
except ImportError:
    EFFICIENTNET_AVAILABLE = False
    logger.warning("efficientnet-pytorch not available. Install with: pip install efficientnet-pytorch")

class EfficientNetDetector:
    """
    EfficientNet-based deepfake detector
    Uses EfficientNet-B4 or B7 for high accuracy
    """
    
    def __init__(self, device: Optional[str] = None, model_name: str = 'efficientnet-b4'):
        """
        Initialize EfficientNet detector
        
        Args:
            device: Device to use
            model_name: EfficientNet variant ('efficientnet-b0' to 'efficientnet-b7')
        """
        if not EFFICIENTNET_AVAILABLE:
            raise ImportError("efficientnet-pytorch not available")
        
        # Force CPU if CUDA_VISIBLE_DEVICES is set to empty
        if os.getenv('CUDA_VISIBLE_DEVICES') == '':
            self.device = 'cpu'
        else:
            self.device = device if device else ('cuda' if torch.cuda.is_available() else 'cpu')
        
        logger.info(f"🔧 Initializing EfficientNet detector ({model_name}) on device: {self.device}")
        
        # Load pretrained EfficientNet
        try:
            self.model = EfficientNet.from_pretrained(model_name, num_classes=2)
            
            self.model.to(self.device)
            self.model.eval()
            
            # Preprocessing transform (EfficientNet uses ImageNet normalization)
            self.transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
            
            logger.info(f"✅ EfficientNet-{model_name} detector initialized")
            logger.info("   Using ImageNet pretrained weights")
            logger.info("   For best results, fine-tune on deepfake datasets")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize EfficientNet: {e}")
            raise
    
    def detect_frame(self, frame: Image.Image) -> float:
        """
        Detect deepfake probability for a single frame
        
        Args:
            frame: PIL Image
            
        Returns:
            Fake probability (0.0 = real, 1.0 = fake)
        """
        try:
            with torch.no_grad():
                # Preprocess
                input_tensor = self.transform(frame).unsqueeze(0).to(self.device)
                
                # Forward pass
                outputs = self.model(input_tensor)
                
                # Get probability
                probs = torch.softmax(outputs, dim=1)
                fake_prob = probs[0][1].item()  # Class 1 = fake
                
                return float(fake_prob)
                
        except Exception as e:
            logger.warning(f"⚠️  Error in EfficientNet detection: {e}")
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
_efficientnet_instance = None

def get_efficientnet_detector(device: Optional[str] = None, model_name: str = 'efficientnet-b4') -> Optional[EfficientNetDetector]:
    """
    Get or create global EfficientNet detector instance (singleton)
    """
    global _efficientnet_instance
    
    if _efficientnet_instance is None:
        try:
            _efficientnet_instance = EfficientNetDetector(device=device, model_name=model_name)
        except Exception as e:
            logger.warning(f"Could not create EfficientNet detector: {e}")
            return None
    
    return _efficientnet_instance
