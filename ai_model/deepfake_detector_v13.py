#!/usr/bin/env python3
"""
DeepFake Detector V13 Integration
699M parameter ensemble model from Hugging Face
F1 Score: 0.9586 (95.86%) - Better than LAA-Net!

Model Structure:
- Ensemble of 3 models: ConvNeXt-Large, ViT-Large, Swin-Large
- Uses safetensors format
- Requires timm library for backbones
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
    import timm
    TIMM_AVAILABLE = True
except ImportError:
    TIMM_AVAILABLE = False
    logger.warning("timm library not available. Install with: pip install timm")

try:
    from safetensors.torch import load_file
    SAFETENSORS_AVAILABLE = True
except ImportError:
    SAFETENSORS_AVAILABLE = False
    logger.warning("safetensors library not available. Install with: pip install safetensors")

try:
    from huggingface_hub import hf_hub_download
    from huggingface_hub.utils import HfHubHTTPError
    HF_HUB_AVAILABLE = True
except ImportError:
    HF_HUB_AVAILABLE = False
    logger.warning("huggingface_hub not available. Install with: pip install huggingface-hub")

class DeepfakeDetector(nn.Module):
    """
    Deepfake detector model architecture
    Uses timm backbone with custom classifier
    """
    def __init__(self, backbone_name: str, dropout: float = 0.3):
        super().__init__()
        # Create backbone using timm with explicit error handling
        try:
            # Try creating model - this can be slow for large models
            self.backbone = timm.create_model(
                backbone_name, 
                pretrained=False, 
                num_classes=0,
                in_chans=3  # RGB input
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create timm model '{backbone_name}': {e}. "
                             f"Check if model name is correct: timm.list_models('*{backbone_name.split('_')[0]}*')")
        
        # Get feature dimension
        if hasattr(self.backbone, 'num_features'):
            feat_dim = self.backbone.num_features
        elif hasattr(self.backbone, 'head') and hasattr(self.backbone.head, 'in_features'):
            feat_dim = self.backbone.head.in_features
        else:
            # Fallback: try to infer from model
            with torch.no_grad():
                test_input = torch.zeros(1, 3, 224, 224)
                test_output = self.backbone(test_input)
                if isinstance(test_output, torch.Tensor):
                    feat_dim = test_output.shape[-1]
                else:
                    feat_dim = 1024  # Default for large models
                    logger.warning(f"Could not infer feature dim, using default {feat_dim}")
        
        # Custom classifier
        self.classifier = nn.Sequential(
            nn.Linear(feat_dim, 512),
            nn.BatchNorm1d(512),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.GELU(),
            nn.Dropout(dropout * 0.5),
            nn.Linear(128, 1)
        )

    def forward(self, x):
        features = self.backbone(x)
        return self.classifier(features).squeeze(-1)

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
        if not TIMM_AVAILABLE:
            raise ImportError("timm library required. Install with: pip install timm")
        if not SAFETENSORS_AVAILABLE:
            raise ImportError("safetensors library required. Install with: pip install safetensors")
        if not HF_HUB_AVAILABLE:
            raise ImportError("huggingface_hub required. Install with: pip install huggingface-hub")
        
        # Force CPU if CUDA_VISIBLE_DEVICES is set to empty
        if os.getenv('CUDA_VISIBLE_DEVICES') == '':
            self.device = 'cpu'
        else:
            self.device = device if device else ('cuda' if torch.cuda.is_available() else 'cpu')
        
        logger.info(f"🔧 Initializing DeepFake Detector V13 on device: {self.device}")
        
        self.models = []  # List of 3 ensemble models
        self.processor = None
        self.model_loaded = False
        
        try:
            self._load_model()
        except Exception as e:
            logger.error(f"❌ Failed to load DeepFake Detector V13: {e}")
            logger.info("Continuing without V13 model")
            self.model_loaded = False
    
    def _load_model(self):
        """Load ensemble models from Hugging Face"""
        logger.info("📦 Loading DeepFake Detector V13 from Hugging Face...")
        logger.info("   Model: ash12321/deepfake-detector-v13")
        logger.info("   This may take a few minutes on first download...")
        logger.info("   Ensemble: ConvNeXt-Large + ViT-Large + Swin-Large")
        
        model_name = "ash12321/deepfake-detector-v13"
        
        # Model configurations: backbone name and safetensors file
        # Note: Using timm model names - verify these match the actual model architecture
        model_configs = [
            {
                'backbone': 'convnext_large.fb_in22k_ft_in1k',
                'file': 'model_1.safetensors',
                'name': 'ConvNeXt-Large'
            },
            {
                'backbone': 'vit_large_patch16_224',  # ViT-Large
                'file': 'model_2.safetensors',
                'name': 'ViT-Large'
            },
            {
                'backbone': 'swin_large_patch4_window7_224',
                'file': 'model_3.safetensors',
                'name': 'Swin-Large'
            }
        ]
        
        try:
            for i, config in enumerate(model_configs, 1):
                logger.info(f"   Loading {config['name']} ({i}/3)...")
                logger.info(f"      Downloading {config['file']} (this may take several minutes)...")
                
                try:
                    # Download safetensors file with retry logic
                    max_retries = 3
                    safetensors_path = None
                    
                    for attempt in range(max_retries):
                        try:
                            logger.info(f"      Attempt {attempt + 1}/{max_retries}...")
                            logger.info(f"      Downloading from Hugging Face (this may take 2-5 minutes per file)...")
                            
                            # Download file (hf_hub_download shows progress automatically)
                            # Add timeout and better error handling
                            import time
                            start_time = time.time()
                            
                            logger.info(f"      Starting download of {config['file']}...")
                            logger.info(f"      (File size: ~700MB, may take 2-5 minutes)")
                            
                            safetensors_path = hf_hub_download(
                                repo_id=model_name,
                                filename=config['file'],
                                cache_dir=None,  # Use default cache
                                local_files_only=False  # Force download
                            )
                            
                            elapsed = time.time() - start_time
                            logger.info(f"      Download completed in {elapsed:.1f} seconds")
                            
                            # Verify file exists and has size
                            import os
                            if os.path.exists(safetensors_path):
                                file_size = os.path.getsize(safetensors_path) / (1024 * 1024)  # MB
                                logger.info(f"      File downloaded: {file_size:.1f}MB")
                            else:
                                raise RuntimeError(f"Downloaded file not found: {safetensors_path}")
                            
                            break  # Success!
                        except (HfHubHTTPError, ConnectionError, TimeoutError) as e:
                            if attempt < max_retries - 1:
                                logger.warning(f"      Download failed, retrying in 5 seconds... ({e})")
                                import time
                                time.sleep(5)
                            else:
                                raise
                    
                    if not safetensors_path:
                        raise RuntimeError(f"Failed to download {config['file']} after {max_retries} attempts")
                    
                    logger.info(f"      ✅ Downloaded {config['file']}")
                    logger.info(f"      Loading model weights...")
                    
                    # Create model with backbone
                    logger.info(f"      Creating {config['name']} architecture...")
                    logger.info(f"      Backbone: {config['backbone']}")
                    
                    try:
                        model = DeepfakeDetector(config['backbone'], dropout=0.3)
                        logger.info(f"      ✅ Architecture created")
                    except Exception as e:
                        logger.error(f"      ❌ Failed to create architecture: {e}")
                        raise
                    
                    # Load state dict from safetensors
                    logger.info(f"      Loading weights from safetensors...")
                    logger.info(f"      File: {safetensors_path}")
                    logger.info(f"      File size: {os.path.getsize(safetensors_path) / (1024*1024):.1f}MB")
                    
                    try:
                        state_dict = load_file(safetensors_path)
                        logger.info(f"      ✅ Safetensors loaded ({len(state_dict)} keys)")
                    except Exception as e:
                        logger.error(f"      ❌ Failed to load safetensors: {e}")
                        raise
                    
                    logger.info(f"      Loading state dict into model...")
                    try:
                        model.load_state_dict(state_dict)
                        logger.info(f"      ✅ State dict loaded")
                    except Exception as e:
                        logger.error(f"      ❌ Failed to load state dict: {e}")
                        logger.info(f"      This might be a model architecture mismatch")
                        raise
                    
                    logger.info(f"      Moving model to {self.device}...")
                    model.to(self.device)
                    model.eval()
                    
                    self.models.append(model)
                    logger.info(f"   ✅ {config['name']} loaded successfully!")
                    
                except Exception as e:
                    logger.error(f"   ❌ Failed to load {config['name']}: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                    # Don't use fallback - we need the actual trained weights
                    # If download fails, we should fail gracefully
                    raise RuntimeError(f"Failed to load {config['name']}: {e}. Make sure you have internet connection and Hugging Face access.")
            
            if not self.models:
                raise RuntimeError("No models loaded from ensemble")
            
            # Create image processor (use timm's default preprocessing)
            from torchvision import transforms
            self.processor = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
            
            self.model_loaded = True
            num_params = sum(sum(p.numel() for p in m.parameters()) for m in self.models)
            logger.info("✅ DeepFake Detector V13 loaded successfully!")
            logger.info(f"   Models loaded: {len(self.models)}/3")
            logger.info(f"   Total parameters: {num_params:,} ({num_params/1e6:.1f}M)")
            logger.info(f"   F1 Score: 0.9586 (95.86%)")
            
        except Exception as e:
            logger.error(f"❌ Error loading DeepFake Detector V13: {e}")
            logger.info("   Make sure timm, safetensors, and huggingface-hub are installed:")
            logger.info("   pip install timm safetensors huggingface-hub")
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
        
        # Process with transforms
        input_tensor = self.processor(frame).unsqueeze(0).to(self.device)
        return input_tensor
    
    def detect_frame(self, frame: Image.Image) -> float:
        """
        Detect deepfake probability for a single frame using ensemble
        
        Args:
            frame: PIL Image
            
        Returns:
            Fake probability (0.0 = real, 1.0 = fake)
        """
        if not self.model_loaded or not self.models:
            return 0.5  # Neutral if model not loaded
        
        try:
            with torch.no_grad():
                # Preprocess
                input_tensor = self.preprocess_frame(frame)
                
                # Get predictions from all models in ensemble
                predictions = []
                for model in self.models:
                    output = model(input_tensor)
                    # Apply sigmoid to get probability
                    prob = torch.sigmoid(output).item()
                    predictions.append(prob)
                
                # Ensemble: average predictions
                ensemble_prob = np.mean(predictions)
                
                return float(ensemble_prob)
                
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
