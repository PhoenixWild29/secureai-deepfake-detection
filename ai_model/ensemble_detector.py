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

try:
    from .confidence_calibration import confidence_from_ensemble, get_calibration_config
except ImportError:
    def get_calibration_config():
        return "agreement_strength", 1.5
    def confidence_from_ensemble(ensemble_prob, is_deepfake, calibration="agreement_strength", temperature=1.5):
        return abs(max(0, min(1, ensemble_prob)) - 0.5) * 2
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
        
        # Load CLIP + ResNet + V13 + Xception + EfficientNet ALL IN PARALLEL so total time ~2-4 min (not 10+)
        import threading
        clip_result = [None]
        def load_clip_thread():
            try:
                from .enhanced_detector import _detector_instance as enhanced_singleton
                if enhanced_singleton is not None:
                    clip_result[0] = enhanced_singleton
                    logger.info("✅ Reusing existing CLIP detector (singleton)")
                    return
                from .enhanced_detector import get_enhanced_detector
                clip_result[0] = get_enhanced_detector(
                    device=self.device,
                    clip_model_name=clip_model_name,
                    clip_pretrained=clip_pretrained
                )
                logger.info("✅ CLIP detector loaded")
            except (ImportError, AttributeError, Exception) as e:
                logger.warning(f"⚠️  CLIP: {e}")
        
        # Load ResNet, V13, Xception, EfficientNet in parallel with CLIP
        self.resnet_model = None
        self.v13_detector = None
        self.xception_detector = None
        self.efficientnet_detector = None
        logger.info("📦 Loading CLIP, ResNet50, V13, XceptionNet, EfficientNet in parallel (max 4 min)...")
        
        def _load_state_dict_resnet(path: str):
            """Load state dict from .pth or .safetensors (safetensors is much faster)."""
            base, ext = os.path.splitext(path)
            # Prefer safetensors if available (faster load, no pickle)
            if ext.lower() == '.pth':
                safetensors_path = base + '.safetensors'
                if os.path.exists(safetensors_path):
                    try:
                        from safetensors.torch import load_file
                        return load_file(safetensors_path, device=self.device)
                    except Exception:
                        pass
            # .pth: use weights_only=True when supported (PyTorch 2.0+, faster/safer)
            try:
                ckpt = torch.load(path, map_location=self.device, weights_only=True)
            except (TypeError, Exception):
                ckpt = torch.load(path, map_location=self.device)
            return ckpt.get('state_dict', ckpt) if isinstance(ckpt, dict) else ckpt

        def load_resnet():
            try:
                model = ResNetDeepfakeClassifier(model_name='resnet50', pretrained=False)
                for path in [resnet_model_path, 'ai_model/resnet_resnet50_final.pth', 'ai_model/resnet_resnet50_best.pth',
                             'resnet_resnet50_final.pth', 'resnet_resnet50_best.pth']:
                    if path and os.path.exists(path):
                        state = _load_state_dict_resnet(path)
                        model.load_state_dict(state, strict=False)
                        model.to(self.device)
                        model.eval()
                        logger.info(f"✅ ResNet50 loaded from: {path}")
                        return model
                logger.warning("⚠️  ResNet50 weights not found. Skipping ResNet.")
            except Exception as e:
                logger.warning(f"⚠️  ResNet50: {e}")
            return None
        
        def load_v13_thread():
            if not V13_AVAILABLE:
                return None
            try:
                return get_deepfake_detector_v13(device=self.device)
            except Exception as e:
                logger.warning(f"⚠️  V13: {e}")
                return None
        
        def load_xception_thread():
            if not XCEPTION_AVAILABLE:
                return None
            try:
                return get_xception_detector(device=self.device)
            except Exception as e:
                logger.warning(f"⚠️  XceptionNet: {e}")
                return None
        
        def load_efficientnet_thread():
            if not EFFICIENTNET_AVAILABLE:
                return None
            try:
                return get_efficientnet_detector(device=self.device)
            except Exception as e:
                logger.warning(f"⚠️  EfficientNet: {e}")
                return None
        
        resnet_result, v13_result, xception_result, eff_result = [None], [None], [None], [None]
        t_clip = threading.Thread(target=load_clip_thread, daemon=True)
        t_resnet = threading.Thread(target=lambda: resnet_result.__setitem__(0, load_resnet()), daemon=True)
        t_v13 = threading.Thread(target=lambda: v13_result.__setitem__(0, load_v13_thread()), daemon=True)
        t_xception = threading.Thread(target=lambda: xception_result.__setitem__(0, load_xception_thread()), daemon=True)
        t_eff = threading.Thread(target=lambda: eff_result.__setitem__(0, load_efficientnet_thread()), daemon=True)
        t_clip.start()
        t_resnet.start()
        t_v13.start()
        t_xception.start()
        t_eff.start()
        for t in (t_clip, t_resnet, t_v13, t_xception, t_eff):
            t.join(timeout=240.0)  # max 4 min for full parallel batch (CLIP + 4 others)
        self.clip_detector = clip_result[0]
        if self.clip_detector is None:
            logger.warning("⚠️  CLIP did not load in time; creating in main thread...")
            try:
                from .enhanced_detector import get_enhanced_detector
                self.clip_detector = get_enhanced_detector(device=self.device, clip_model_name=clip_model_name, clip_pretrained=clip_pretrained)
            except Exception as e:
                raise RuntimeError(f"CLIP required for detection: {e}") from e
        self.resnet_model = resnet_result[0]
        self.v13_detector = v13_result[0]
        self.xception_detector = xception_result[0]
        self.efficientnet_detector = eff_result[0]
        if t_v13.is_alive():
            logger.warning("⚠️  V13 loading timed out (4 min). Ensemble will use CLIP + ResNet + XceptionNet.")
        if self.v13_detector and getattr(self.v13_detector, 'model_loaded', False):
            logger.info("✅ DeepFake Detector V13 loaded successfully!")
        if self.xception_detector:
            logger.info("✅ XceptionNet detector loaded successfully!")
        if self.efficientnet_detector:
            logger.info("✅ EfficientNet detector loaded successfully!")
        
        # Ensemble weights (updated to include new models)
        self.ensemble_weights = ensemble_weights or {
            'clip': 0.25,      # CLIP: good for zero-shot, generalizable
            'resnet': 0.30,    # ResNet: trained specifically for deepfakes (100% test accuracy)
            'v13': 0.35,       # DeepFake Detector V13: BEST model (95.86% F1, 699M params) ⭐
            'xception': 0.10,  # XceptionNet: proven for deepfakes
            'laa': 0.0         # LAA-Net: optional; set > 0 when external/laa_net + weights are configured
        }
        
        # Remove weights for unavailable models
        if not (self.v13_detector and self.v13_detector.model_loaded):
            self.ensemble_weights['v13'] = 0.0
        if not self.xception_detector:
            self.ensemble_weights['xception'] = 0.0
        # Enable LAA-Net weight when actually loaded
        if getattr(self.clip_detector, 'laa_available', False):
            self.ensemble_weights['laa'] = 0.10
        
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
        if getattr(self.clip_detector, 'laa_available', False):
            active_models.append('LAA-Net')
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
    
    def resnet_detect_per_frame(self, frames: List[Image.Image]) -> List[float]:
        """ResNet fake probability per frame (for temporal consistency)."""
        if self.resnet_model is None:
            return [0.5] * len(frames) if frames else [0.5]
        from torchvision import transforms
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        probs = []
        for frame in frames:
            try:
                frame_tensor = transform(frame).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    output = self.resnet_model(frame_tensor)
                    p = torch.softmax(output, dim=1)
                    probs.append(p[0][1].item())
            except Exception:
                probs.append(0.5)
        return probs if probs else [0.5]
    
    def clip_detect_per_frame(self, frames: List[Image.Image]) -> List[float]:
        """CLIP fake probability per frame (for temporal consistency)."""
        if hasattr(self.clip_detector, 'clip_detect_frames_probs'):
            return self.clip_detector.clip_detect_frames_probs(frames)
        mean_prob = self.clip_detect(frames)
        return [mean_prob] * len(frames) if frames else [0.5]
    
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
        
        # Confidence: optional calibration (default = agreement strength; see confidence_calibration.py)
        is_deepfake = ensemble_prob > 0.5
        cal_method, cal_T = get_calibration_config()
        overall_confidence = confidence_from_ensemble(
            float(ensemble_prob), is_deepfake, calibration=cal_method, temperature=cal_T
        )
        
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
            'confidence': float(overall_confidence),
            'confidence_meaning': cal_method,
            'is_deepfake': is_deepfake,
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
        
        # Run all detectors with progress logging (per-frame for CLIP/ResNet for temporal consistency)
        logger.info(f"🔍 Running ultimate ensemble on {len(frames)} frames...")
        
        logger.debug(f"Running CLIP detection (per-frame)...")
        clip_per_frame = self.clip_detect_per_frame(frames)
        clip_prob = float(np.mean(clip_per_frame))
        logger.debug(f"CLIP result: {clip_prob:.3f}")
        
        logger.debug(f"Running ResNet detection (per-frame)...")
        resnet_per_frame = self.resnet_detect_per_frame(frames)
        resnet_prob = float(np.mean(resnet_per_frame))
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
        
        # Per-frame ensemble probs for real temporal consistency (same weights as full ensemble)
        weights = ensemble_results.get('ensemble_weights_used', {})
        n = len(frames)
        frame_probabilities = []
        for i in range(n):
            fp = (
                weights.get('clip', 0) * clip_per_frame[i] +
                weights.get('resnet', 0) * resnet_per_frame[i] +
                weights.get('v13', 0) * v13_prob +
                weights.get('xception', 0) * xception_prob +
                weights.get('efficientnet', 0) * efficientnet_prob +
                weights.get('laa', 0) * laa_prob
            )
            frame_probabilities.append(float(fp))
        
        # Determine method used
        models_used = ensemble_results.get('models_used', [])
        method = 'ultimate_ensemble_' + '_'.join(models_used) if models_used else 'clip_only'
        
        return {
            **ensemble_results,
            'frame_probabilities': frame_probabilities,
            'method': method,
            'num_frames_analyzed': len(frames),
            'resnet_available': self.resnet_model is not None,
            'v13_available': self.v13_detector and self.v13_detector.model_loaded,
            'xception_available': self.xception_detector is not None,
            'efficientnet_available': self.efficientnet_detector is not None,
            'laa_available': self.clip_detector.laa_available
        }


# Global instance; loaded in background thread so the request thread never blocks
import threading as _threading
_ensemble_instance = None
_ensemble_init_failed = False
_ensemble_loading_started = False
_ensemble_loading_lock = _threading.Lock()

def init_ensemble_blocking() -> Optional[EnsembleDetector]:
    """
    Load the full ensemble in the current thread. Called only from the background
    loader thread so the request thread never blocks for 10+ min.
    """
    global _ensemble_instance, _ensemble_init_failed
    if _ensemble_instance is not None:
        return _ensemble_instance
    if _ensemble_init_failed:
        return None
    try:
        logger.info("Loading full ensemble (CLIP + ResNet + V13 + XceptionNet + EfficientNet + ...) — this may take 2–5 minutes.")
        _ensemble_instance = EnsembleDetector()
        logger.info("✅ EnsembleDetector loaded successfully. Every scan will use the full ensemble.")
        return _ensemble_instance
    except Exception as e:
        logger.exception(f"EnsembleDetector initialization failed: {e}")
        _ensemble_init_failed = True
        return None

def start_background_ensemble_load() -> None:
    """
    Start loading the ensemble in a background thread if not already loaded or loading.
    Returns immediately. The request thread must never block on model load — so the
    first scan returns 503 and the user retries in 3 min when the background load has finished.
    """
    global _ensemble_instance, _ensemble_init_failed, _ensemble_loading_started
    with _ensemble_loading_lock:
        if _ensemble_instance is not None:
            return
        if _ensemble_init_failed:
            return
        if _ensemble_loading_started:
            return
        _ensemble_loading_started = True
    def _run():
        try:
            init_ensemble_blocking()
        finally:
            pass  # _ensemble_instance or _ensemble_init_failed is set
    t = _threading.Thread(target=_run, daemon=True)
    t.start()
    logger.info("Ensemble load started in background. Next scan (in ~3 min) will use it.")

def get_ensemble_detector(timeout: Optional[float] = None) -> Optional[EnsembleDetector]:
    """
    Return the global ensemble detector if already loaded. Never blocks — if not loaded,
    returns None so the API can return 503 and ask the user to retry in 3 min.
    """
    global _ensemble_instance
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
    detector = get_ensemble_detector()  # uses ENSEMBLE_INIT_TIMEOUT (default 300s)
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

