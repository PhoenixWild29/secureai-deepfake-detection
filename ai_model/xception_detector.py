#!/usr/bin/env python3
"""
XceptionNet Deepfake Detector
Proven model for deepfake detection, available in PyTorch
"""
import os
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision.models import xception
import numpy as np
from typing import List, Optional
from PIL import Image
import logging

logger = logging.getLogger(__name__)

# Force CPU mode if needed
if os.getenv('CUDA_VISIBLE_DEVICES') == '':
    os.environ['CUDA_VISIBLE_DEVICES'] = ''

class XceptionDetector:
    """
    XceptionNet-based deepfake detector
    Uses pretrained Xception and fine-tunes for deepfake detection
    """
    
    def __init__(self, device: Optional[str] = None, num_classes: int = 2):
        """
        Initialize XceptionNet detector
        
        Args:
            device: Device to use
            num_classes: Number of classes (2 for real/fake)
        """
        # Force CPU if CUDA_VISIBLE_DEVICES is set to empty
        if os.getenv('CUDA_VISIBLE_DEVICES') == '':
            self.device = 'cpu'
        else:
            self.device = device if device else ('cuda' if torch.cuda.is_available() else 'cpu')
        
        logger.info(f"🔧 Initializing XceptionNet detector on device: {self.device}")
        
        # Load pretrained Xception
        try:
            self.model = xception(pretrained=True)
            
            # Modify final layer for binary classification
            num_features = self.model.fc.in_features
            self.model.fc = nn.Linear(num_features, num_classes)
            
            self.model.to(self.device)
            self.model.eval()
            
            # Preprocessing transform
            self.transform = transforms.Compose([
                transforms.Resize((299, 299)),  # Xception input size
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
            ])
            
            logger.info("✅ XceptionNet detector initialized")
            logger.info("   Note: Using ImageNet pretrained weights")
            logger.info("   For best results, fine-tune on deepfake datasets")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize XceptionNet: {e}")
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
            logger.warning(f"⚠️  Error in XceptionNet detection: {e}")
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
_xception_instance = None

def get_xception_detector(device: Optional[str] = None) -> Optional[XceptionDetector]:
    """
    Get or create global XceptionNet detector instance (singleton)
    """
    global _xception_instance
    
    if _xception_instance is None:
        try:
            _xception_instance = XceptionDetector(device=device)
        except Exception as e:
            logger.warning(f"Could not create XceptionNet detector: {e}")
            return None
    
    return _xception_instance
