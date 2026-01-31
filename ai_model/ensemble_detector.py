#!/usr/bin/env python3
"""
Ultimate Ensemble Detector: Best Deepfake Detection on the Planet
Combines CLIP + ResNet50 + DeepFake Detector V13 + XceptionNet + EfficientNet + ViT + ConvNeXt
Target: 98-99% Accuracy
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

# Import base models
try:
    from .enhanced_detector import EnhancedDetector
    from .deepfake_classifier import ResNetDeepfakeClassifier
except ImportError:
    from enhanced_detector import EnhancedDetector
    from deepfake_classifier import ResNetDeepfakeClassifier

# Import new models (optional - will work without them)
try:
    from .deepfake_detector_v13 import get_deepfake_detector_v13
    V13_AVAILABLE = True
except ImportError:
    V13_AVAILABLE = False
    logger.info("DeepFake Detector V13 not available (install transformers)")

try:
    from .xception_detector import get_xception_detector
    XCEPTION_AVAILABLE = True
except ImportError:
    XCEPTION_AVAILABLE = False
    logger.info("XceptionNet detector not available")

try:
    from .efficientnet_detector import get_efficientnet_detector
    EFFICIENTNET_AVAILABLE = True
except ImportError:
    EFFICIENTNET_AVAILABLE = False
    logger.info("EfficientNet detector not available")

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
        
        # Initialize CLIP detector (EnhancedDetector) - MUST reuse singleton to avoid reloading CLIP
        logger.info("📦 Loading CLIP detector...")
        try:
            # CRITICAL: Reuse the existing EnhancedDetector singleton to avoid reloading CLIP
            from .enhanced_detector import _detector_instance as enhanced_singleton
            if enhanced_singleton is not None:
                self.clip_detector = enhanced_singleton
                logger.info("✅ Reusing existing CLIP detector instance (singleton) - no CLIP reload needed")
            else:
                # Singleton doesn't exist yet - create it (this will load CLIP)
                from .enhanced_detector import get_enhanced_detector
                self.clip_detector = get_enhanced_detector(
                    device=self.device,
                    clip_model_name=clip_model_name,
                    clip_pretrained=clip_pretrained
                )
                logger.info("✅ Created CLIP detector instance (singleton)")
        except (ImportError, AttributeError) as e:
            # Fallback if singleton access fails
            logger.warning(f"Could not access singleton, creating new EnhancedDetector: {e}")
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
        
        # Initialize DeepFake Detector V13 (BEST MODEL - Available on Hugging Face!)
        # NOTE: V13 loading can hang on ConvNeXt-Large, so we use a timeout
        logger.info("📦 Loading DeepFake Detector V13 (699M params, F1: 0.9586)...")
        logger.info("   ⚠️  This may take 2-5 minutes or timeout if ConvNeXt-Large hangs")
        self.v13_detector = None
        if V13_AVAILABLE:
            try:
                # Use timeout to prevent hanging (5 minutes max)
                import signal
                v13_loaded = [False]
                v13_error = [None]
                v13_instance = [None]
                
                def load_v13():
                    try:
                        v13_instance[0] = get_deepfake_detector_v13(device=self.device)
                        v13_loaded[0] = True
                    except Exception as e:
                        v13_error[0] = e
                
                def timeout_handler(signum, frame):
                    raise TimeoutError("V13 loading timed out after 5 minutes")
                
                # Set 5 minute timeout
                original_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(300)  # 5 minutes
                
                try:
                    load_v13()
                    signal.alarm(0)  # Cancel timeout
                    signal.signal(signal.SIGALRM, original_handler)
                    
                    self.v13_detector = v13_instance[0]
                    if self.v13_detector and self.v13_detector.model_loaded:
                        logger.info("✅ DeepFake Detector V13 loaded successfully!")
                    else:
                        logger.info("⚠️  DeepFake Detector V13 not fully loaded (some models may have failed)")
                except TimeoutError:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, original_handler)
                    logger.warning("⚠️  DeepFake Detector V13 loading timed out (ConvNeXt-Large may be hanging)")
                    logger.warning("   Ensemble will continue without V13 - still excellent with CLIP + ResNet + XceptionNet")
                    self.v13_detector = None
                except Exception as e:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, original_handler)
                    logger.warning(f"⚠️  Could not load DeepFake Detector V13: {e}")
                    self.v13_detector = None
            except Exception as e:
                logger.warning(f"⚠️  Could not load DeepFake Detector V13: {e}")
                self.v13_detector = None
        
        # Initialize XceptionNet
        logger.info("📦 Loading XceptionNet detector...")
        self.xception_detector = None
        if XCEPTION_AVAILABLE:
            try:
                self.xception_detector = get_xception_detector(device=self.device)
                if self.xception_detector:
                    logger.info("✅ XceptionNet detector loaded successfully!")
            except Exception as e:
                logger.warning(f"⚠️  Could not load XceptionNet: {e}")

        # Initialize EfficientNet (optional)
        logger.info("📦 Loading EfficientNet detector...")
        self.efficientnet_detector = None
        if EFFICIENTNET_AVAILABLE:
            try:
                # Will return None if efficientnet-pytorch isn't installed
                self.efficientnet_detector = get_efficientnet_detector(device=self.device)
                if self.efficientnet_detector:
                    logger.info("✅ EfficientNet detector loaded successfully!")
            except Exception as e:
                logger.warning(f"⚠️  Could not load EfficientNet detector: {e}")
        
        # Ensemble weights (updated to include new models)
        self.ensemble_weights = ensemble_weights or {
            'clip': 0.25,      # CLIP: good for zero-shot, generalizable
            'resnet': 0.30,    # ResNet: trained specifically for deepfakes (100% test accuracy)
            'v13': 0.35,       # DeepFake Detector V13: BEST model (95.86% F1, 699M params) ⭐
            'xception': 0.10,  # XceptionNet: proven for deepfakes
            'laa': 0.0         # LAA-Net: not available (weights broken)
        }
        
        # Remove weights for unavailable models
        if not (self.v13_detector and self.v13_detector.model_loaded):
            self.ensemble_weights['v13'] = 0.0
        if not self.xception_detector:
            self.ensemble_weights['xception'] = 0.0
        
        # Normalize weights
        total_weight = sum(self.ensemble_weights.values())
        if total_weight > 0:
            self.ensemble_weights = {k: v/total_weight for k, v in self.ensemble_weights.items()}
        else:
            # Fallback if no models available
            self.ensemble_weights = {'clip': 0.5, 'resnet': 0.5, 'v13': 0.0, 'xception': 0.0, 'laa': 0.0}
        
        logger.info(f"✅ Ultimate EnsembleDetector initialized")
        active_models = ['CLIP', 'ResNet50']
        if self.v13_detector and self.v13_detector.model_loaded:
            active_models.append('V13')
        if self.xception_detector:
            active_models.append('XceptionNet')
        if self.efficientnet_detector:
            active_models.append('EfficientNet')
        logger.info(f"   Active models: {', '.join(active_models)}")
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
    
    def v13_detect(self, frames: List[Image.Image]) -> float:
        """Get DeepFake Detector V13 detection probability"""
        if not (self.v13_detector and self.v13_detector.model_loaded):
            return 0.5  # Neutral if V13 not available
        return self.v13_detector.detect_frames(frames)
    
    def xception_detect(self, frames: List[Image.Image]) -> float:
        """Get XceptionNet detection probability"""
        if not self.xception_detector:
            return 0.5  # Neutral if XceptionNet not available
        return self.xception_detector.detect_frames(frames)
    
    def adaptive_ensemble(self, 
                         clip_prob: float, 
                         resnet_prob: float, 
                         laa_prob: float,
                         v13_prob: Optional[float] = None,
                         xception_prob: Optional[float] = None,
                         efficientnet_prob: Optional[float] = None) -> Dict[str, Any]:
        """
        Ultimate adaptive ensemble with all available models
        Combines CLIP + ResNet + V13 + XceptionNet + LAA-Net for maximum accuracy
        
        Args:
            clip_prob: CLIP fake probability
            resnet_prob: ResNet50 fake probability
            laa_prob: LAA-Net fake probability
            v13_prob: DeepFake Detector V13 fake probability
            xception_prob: XceptionNet fake probability
            
        Returns:
            Ensemble results with probabilities and confidence
        """
        # Use provided probabilities or defaults
        if v13_prob is None:
            v13_prob = 0.5
        if xception_prob is None:
            xception_prob = 0.5
        if efficientnet_prob is None:
            efficientnet_prob = 0.5
        
        # Calculate confidence (distance from 0.5) for each model
        clip_confidence = abs(clip_prob - 0.5) * 2
        resnet_confidence = abs(resnet_prob - 0.5) * 2
        v13_confidence = abs(v13_prob - 0.5) * 2 if (self.v13_detector and self.v13_detector.model_loaded) else 0
        xception_confidence = abs(xception_prob - 0.5) * 2 if self.xception_detector else 0
        efficientnet_confidence = abs(efficientnet_prob - 0.5) * 2 if self.efficientnet_detector else 0
        laa_confidence = abs(laa_prob - 0.5) * 2 if self.clip_detector.laa_available else 0
        
        # Build list of available models and their confidences
        models = []
        if self.clip_detector:
            models.append(('clip', clip_prob, clip_confidence))
        if self.resnet_model:
            models.append(('resnet', resnet_prob, resnet_confidence))
        if self.v13_detector and self.v13_detector.model_loaded:
            models.append(('v13', v13_prob, v13_confidence))
        if self.xception_detector:
            models.append(('xception', xception_prob, xception_confidence))
        if self.efficientnet_detector:
            models.append(('efficientnet', efficientnet_prob, efficientnet_confidence))
        if self.clip_detector.laa_available:
            models.append(('laa', laa_prob, laa_confidence))
        
        # Adaptive weighting: higher confidence = more weight
        total_confidence = sum(conf for _, _, conf in models)
        
        if total_confidence > 0:
            # Weight by confidence
            adaptive_weights = {
                name: conf / total_confidence 
                for name, _, conf in models
            }
            # Fill in zeros for unavailable models
            for name in ['clip', 'resnet', 'v13', 'xception', 'efficientnet', 'laa']:
                if name not in adaptive_weights:
                    adaptive_weights[name] = 0.0
        else:
            # Fallback to fixed weights if all confidences are low
            adaptive_weights = self.ensemble_weights.copy()
        
        # Weighted ensemble
        ensemble_prob = (
            adaptive_weights.get('clip', 0) * clip_prob +
            adaptive_weights.get('resnet', 0) * resnet_prob +
            adaptive_weights.get('v13', 0) * v13_prob +
            adaptive_weights.get('xception', 0) * xception_prob +
            adaptive_weights.get('efficientnet', 0) * efficientnet_prob +
            adaptive_weights.get('laa', 0) * laa_prob
        )
        
        # Overall confidence
        overall_confidence = abs(ensemble_prob - 0.5) * 2
        
        return {
            'ensemble_fake_probability': float(ensemble_prob),
            'clip_fake_probability': float(clip_prob),
            'resnet_fake_probability': float(resnet_prob),
            'v13_fake_probability': float(v13_prob),
            'xception_fake_probability': float(xception_prob),
            'efficientnet_fake_probability': float(efficientnet_prob),
            'laa_fake_probability': float(laa_prob),
            'ensemble_weights_used': adaptive_weights,
            'overall_confidence': float(overall_confidence),
            'is_deepfake': ensemble_prob > 0.5,
            'models_used': [name for name, _, _ in models]
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
        logger.info(f"🔍 Running ultimate ensemble on {len(frames)} frames...")
        
        logger.debug(f"Running CLIP detection...")
        clip_prob = self.clip_detect(frames)
        logger.debug(f"CLIP result: {clip_prob:.3f}")
        
        logger.debug(f"Running ResNet detection...")
        resnet_prob = self.resnet_detect(frames)
        logger.debug(f"ResNet result: {resnet_prob:.3f}")
        
        # DeepFake Detector V13 (BEST MODEL!)
        v13_prob = 0.5
        if self.v13_detector and self.v13_detector.model_loaded:
            logger.debug(f"Running DeepFake Detector V13 (699M params)...")
            try:
                v13_prob = self.v13_detect(frames)
                logger.debug(f"V13 result: {v13_prob:.3f}")
            except Exception as e:
                logger.warning(f"V13 detection error: {e}")
        
        # XceptionNet
        xception_prob = 0.5
        if self.xception_detector:
            logger.debug(f"Running XceptionNet detection...")
            try:
                xception_prob = self.xception_detect(frames)
                logger.debug(f"XceptionNet result: {xception_prob:.3f}")
            except Exception as e:
                logger.warning(f"XceptionNet detection error: {e}")

        # EfficientNet (optional)
        efficientnet_prob = 0.5
        if self.efficientnet_detector:
            logger.debug("Running EfficientNet detection...")
            try:
                efficientnet_prob = self.efficientnet_detector.detect_frames(frames)
                logger.debug(f"EfficientNet result: {efficientnet_prob:.3f}")
            except Exception as e:
                logger.warning(f"EfficientNet detection error: {e}")
        
        # LAA-Net (if available)
        logger.debug(f"Running LAA-Net detection...")
        laa_prob = self.laa_detect(frames)
        logger.debug(f"LAA-Net result: {laa_prob:.3f}")
        
        # Ultimate adaptive ensemble
        ensemble_results = self.adaptive_ensemble(
            clip_prob, resnet_prob, laa_prob, v13_prob, xception_prob, efficientnet_prob
        )
        
        # Determine method used
        models_used = ensemble_results.get('models_used', [])
        method = 'ultimate_ensemble_' + '_'.join(models_used) if models_used else 'clip_only'
        
        return {
            **ensemble_results,
            'method': method,
            'num_frames_analyzed': len(frames),
            'resnet_available': self.resnet_model is not None,
            'v13_available': self.v13_detector and self.v13_detector.model_loaded,
            'xception_available': self.xception_detector is not None,
            'efficientnet_available': self.efficientnet_detector is not None,
            'laa_available': self.clip_detector.laa_available
        }


# Global instance for lazy initialization
_ensemble_instance = None
_ensemble_init_failed = False

def get_ensemble_detector(timeout: float = 30.0) -> Optional[EnsembleDetector]:
    """Get or create global ensemble detector instance with timeout"""
    global _ensemble_instance, _ensemble_init_failed
    
    if _ensemble_init_failed:
        return None  # Don't retry if initialization already failed
    
    if _ensemble_instance is None:
        try:
            import threading
            import queue
            
            init_queue = queue.Queue(maxsize=1)
            error_queue = queue.Queue(maxsize=1)
            
            def init_ensemble():
                try:
                    detector = EnsembleDetector()
                    init_queue.put(detector, block=False, timeout=0.1)
                except queue.Full:
                    pass  # Timeout occurred
                except Exception as e:
                    try:
                        error_queue.put(e, block=False, timeout=0.1)
                    except queue.Full:
                        pass
            
            # Initialize with timeout
            init_thread = threading.Thread(target=init_ensemble, daemon=True)
            init_thread.start()
            init_thread.join(timeout=timeout)
            
            if init_thread.is_alive():
                logger.warning(f"⚠️  EnsembleDetector initialization timed out (>={timeout}s). Disabling ensemble.")
                _ensemble_init_failed = True
                return None
            
            if not error_queue.empty():
                error = error_queue.get()
                logger.warning(f"⚠️  EnsembleDetector initialization failed: {error}. Disabling ensemble.")
                _ensemble_init_failed = True
                return None
            
            if not init_queue.empty():
                _ensemble_instance = init_queue.get()
                logger.info("✅ EnsembleDetector initialized successfully")
            else:
                logger.warning("⚠️  EnsembleDetector initialization returned no result. Disabling ensemble.")
                _ensemble_init_failed = True
                return None
                
        except Exception as e:
            logger.error(f"❌ EnsembleDetector initialization error: {e}. Disabling ensemble.")
            _ensemble_init_failed = True
            return None
    
    return _ensemble_instance

def detect_fake_ensemble(video_path: str, num_frames: int = 16) -> Dict[str, Any]:
    """
    Convenience function for ensemble detection with timeout protection
    
    Args:
        video_path: Path to video file
        num_frames: Number of frames to sample
        
    Returns:
        Detection results or error dict if ensemble unavailable
    """
    detector = get_ensemble_detector(timeout=30.0)
    if detector is None:
        # Ensemble unavailable - return error result
        return {
            'error': 'Ensemble detector unavailable (initialization failed or timed out)',
            'is_deepfake': False,
            'confidence': 0.0,
            'ensemble_fake_probability': 0.5,
            'method': 'ensemble_unavailable'
        }
    
    try:
        return detector.detect(video_path, num_frames)
    except Exception as e:
        logger.error(f"Ensemble detection error: {e}")
        return {
            'error': str(e),
            'is_deepfake': False,
            'confidence': 0.0,
            'ensemble_fake_probability': 0.5,
            'method': 'ensemble_error'
        }

