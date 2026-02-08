#!/usr/bin/env python3
"""
Enhanced DeepFake Detection Model - Priority 1 MVP Implementation
Combines CLIP zero-shot detection and LAA-Net for robust ensemble detection.

This implementation focuses on:
1. CLIP zero-shot detection - Highly generalizable, excellent for modern diffusion-based deepfakes
2. LAA-Net - Quality-agnostic artifact attention model (CVPR 2024)

The ensemble fuses their predictions for robust detection.
"""

import os
# CRITICAL: Force CPU mode BEFORE any imports (must be first)
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress all TensorFlow messages
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'false'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
# Disable TensorFlow GPU completely
os.environ['TF_GPU_ALLOCATOR'] = 'cuda_malloc_async'
os.environ['TF_USE_LEGACY_KERAS'] = '1'

import cv2
import torch
# Disable CUDA if explicitly requested
if os.getenv('CUDA_VISIBLE_DEVICES') == '':
    # Monkey patch to force CPU
    original_cuda_available = torch.cuda.is_available
    torch.cuda.is_available = lambda: False

# Suppress warnings before importing open_clip
import warnings
warnings.filterwarnings('ignore')

# Import open_clip with stderr suppression
import contextlib
import io
stderr_suppressor = io.StringIO()

try:
    with contextlib.redirect_stderr(stderr_suppressor):
        import open_clip
except Exception:
    # If import fails, try without suppression
    import open_clip
from PIL import Image
import numpy as np
import sys
from typing import Dict, List, Optional, Tuple, Any
import warnings
warnings.filterwarnings('ignore')

# LAA-Net: real inference via laa_net_loader when external/laa_net + weights exist
try:
    from ai_model.laa_net_loader import load_laa_net, run_laa_inference
    _LAA_LOADER_AVAILABLE = True
except ImportError:
    _LAA_LOADER_AVAILABLE = False
    load_laa_net = run_laa_inference = None

# Confidence calibration (optional temperature scaling; default = agreement strength)
try:
    from ai_model.confidence_calibration import confidence_from_ensemble, get_calibration_config
except ImportError:
    def get_calibration_config():
        return "agreement_strength", 1.5
    def confidence_from_ensemble(ensemble_prob, is_deepfake, calibration="agreement_strength", temperature=1.5):
        return abs(max(0, min(1, ensemble_prob)) - 0.5) * 2  # fallback: agreement strength

# Face detection - MTCNN will be lazy-loaded to prevent TensorFlow from importing at module level
# This prevents CUDA initialization errors on CPU-only servers
MTCNN_AVAILABLE = None  # Will be determined on first use


class FaceDetector:
    """Face detection and cropping utility for LAA-Net preprocessing."""
    
    def __init__(self, method: str = 'auto'):
        """
        Initialize face detector.
        
        Args:
            method: 'mtcnn', 'haar', or 'auto' (tries MTCNN first, falls back to Haar)
        """
        self.method = method
        self.mtcnn = None
        self.haar_cascade = None
        self._mtcnn_available = None
        
        # Try MTCNN only if requested, with complete TensorFlow suppression
        if method in ['auto', 'mtcnn']:
            self._try_mtcnn()
        
        # Fall back to Haar if MTCNN not available or failed
        if self.method == 'haar' or (method == 'auto' and self.mtcnn is None):
            self._init_haar()
    
    def _try_mtcnn(self):
        """Try to load MTCNN with complete TensorFlow/CUDA suppression."""
        global MTCNN_AVAILABLE
        
        # Check if we've already determined MTCNN availability
        if MTCNN_AVAILABLE is False:
            return  # Already tried and failed
        
        try:
            # CRITICAL: Suppress TensorFlow/CUDA errors during MTCNN import
            # Redirect both stderr and stdout to completely hide TensorFlow initialization
            import contextlib
            import io
            import sys
            
            old_stderr = sys.stderr
            old_stdout = sys.stdout
            suppress_io = io.StringIO()
            
            # Temporarily redirect all output
            sys.stderr = suppress_io
            sys.stdout = suppress_io
            
            try:
                # Set TensorFlow env vars before import
                os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
                os.environ['CUDA_VISIBLE_DEVICES'] = ''
                os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'false'
                
                # Now try to import MTCNN (this will import TensorFlow)
                from mtcnn import MTCNN
                
                # Restore output immediately after import
                sys.stderr = old_stderr
                sys.stdout = old_stdout
                
                # If import succeeded, try to create MTCNN instance
                try:
                    # Suppress output during MTCNN initialization too
                    sys.stderr = suppress_io
                    sys.stdout = suppress_io
                    self.mtcnn = MTCNN()
                    sys.stderr = old_stderr
                    sys.stdout = old_stdout
                    
                    self.method = 'mtcnn'
                    MTCNN_AVAILABLE = True
                    self._mtcnn_available = True
                    return  # Success!
                except Exception as init_e:
                    sys.stderr = old_stderr
                    sys.stdout = old_stdout
                    # MTCNN import succeeded but initialization failed
                    MTCNN_AVAILABLE = False
                    self._mtcnn_available = False
                    
            except ImportError:
                # Restore output before checking availability
                sys.stderr = old_stderr
                sys.stdout = old_stdout
                MTCNN_AVAILABLE = False
                self._mtcnn_available = False
            except Exception as e:
                # Restore output before handling error
                sys.stderr = old_stderr
                sys.stdout = old_stdout
                # Any other error during import (including CUDA errors from TensorFlow)
                MTCNN_AVAILABLE = False
                self._mtcnn_available = False
                
        except Exception as e:
            # Ultimate fallback - something went very wrong
            MTCNN_AVAILABLE = False
            self._mtcnn_available = False
            # Don't print error - we'll fall back to Haar silently
    
    def _init_haar(self):
        """Initialize Haar cascade face detector."""
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        if os.path.exists(cascade_path):
            self.haar_cascade = cv2.CascadeClassifier(cascade_path)
            self.method = 'haar'
        else:
            print("Warning: Haar cascade not found. Face detection may fail.")
    
    def detect_face(self, image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Detect face in image and return bounding box.
        
        Args:
            image: Input image as numpy array (RGB or BGR)
            
        Returns:
            (x, y, w, h) bounding box or None if no face detected
        """
        if image is None or image.size == 0:
            return None
        
        # Convert to RGB if needed
        if len(image.shape) == 3 and image.shape[2] == 3:
            # Assume BGR if using OpenCV, convert to RGB for MTCNN
            if self.method == 'mtcnn' and self.mtcnn is not None:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if image.dtype == np.uint8 else image
            else:
                image_rgb = image
        else:
            image_rgb = image
        
        if self.method == 'mtcnn' and self.mtcnn is not None:
            try:
                results = self.mtcnn.detect_faces(image_rgb)
                if results and len(results) > 0:
                    # Get the largest face
                    largest_face = max(results, key=lambda x: x['box'][2] * x['box'][3])
                    x, y, w, h = largest_face['box']
                    return (x, y, w, h)
            except Exception as e:
                print(f"MTCNN detection error: {e}")
        
        if self.method == 'haar' and self.haar_cascade is not None:
            try:
                # Convert to grayscale for Haar
                if len(image_rgb.shape) == 3:
                    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY) if image_rgb.shape[2] == 3 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                else:
                    gray = image_rgb
                
                faces = self.haar_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
                )
                if len(faces) > 0:
                    # Get the largest face
                    largest_face = max(faces, key=lambda x: x[2] * x[3])
                    x, y, w, h = largest_face
                    return (x, y, w, h)
            except Exception as e:
                print(f"Haar detection error: {e}")
        
        return None
    
    def crop_face(self, image: np.ndarray, bbox: Optional[Tuple[int, int, int, int]] = None, 
                  target_size: Tuple[int, int] = (224, 224), padding: float = 0.2) -> Optional[np.ndarray]:
        """
        Crop and resize face from image.
        
        Args:
            image: Input image
            bbox: Bounding box (x, y, w, h). If None, will detect face.
            target_size: Target size (width, height)
            padding: Padding factor around face (0.2 = 20% padding)
            
        Returns:
            Cropped and resized face image or None
        """
        if bbox is None:
            bbox = self.detect_face(image)
            if bbox is None:
                return None
        
        x, y, w, h = bbox
        
        # Add padding
        pad_w = int(w * padding)
        pad_h = int(h * padding)
        x = max(0, x - pad_w)
        y = max(0, y - pad_h)
        w = min(image.shape[1] - x, w + 2 * pad_w)
        h = min(image.shape[0] - y, h + 2 * pad_h)
        
        # Crop face
        face_crop = image[y:y+h, x:x+w]
        
        if face_crop.size == 0:
            return None
        
        # Resize to target size
        face_resized = cv2.resize(face_crop, target_size, interpolation=cv2.INTER_LINEAR)
        
        return face_resized


class EnhancedDetector:
    """
    Enhanced ensemble detector combining CLIP zero-shot and LAA-Net.
    
    This is the Priority 1 MVP implementation focusing on two strong,
    complementary components for effective deepfake detection.
    """
    
    def __init__(self, laa_weights_path: Optional[str] = None, 
                 device: Optional[str] = None,
                 clip_model_name: str = 'ViT-B-32',
                 clip_pretrained: str = 'laion2b_s34b_b79k'):
        """
        Initialize the enhanced detector.
        
        Args:
            laa_weights_path: Path to LAA-Net pre-trained weights (optional)
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
            clip_model_name: CLIP model variant to use
            clip_pretrained: CLIP pretrained weights identifier
        """
        # Default LAA-Net weights: env LAA_NET_WEIGHTS or first .pth in external/laa_net/weights/
        if laa_weights_path is None:
            laa_weights_path = os.getenv("LAA_NET_WEIGHTS")
        if not laa_weights_path or not os.path.isfile(laa_weights_path):
            _ext = os.path.join(os.path.dirname(__file__), "..", "external", "laa_net", "weights")
            if os.path.isdir(_ext):
                for _f in os.listdir(_ext):
                    if _f.endswith(".pth"):
                        laa_weights_path = os.path.join(_ext, _f)
                        break
        # Force CPU if CUDA_VISIBLE_DEVICES is set to empty
        if os.getenv('CUDA_VISIBLE_DEVICES') == '':
            self.device = 'cpu'
        else:
            self.device = device if device else ('cuda' if torch.cuda.is_available() else 'cpu')
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔧 Initializing EnhancedDetector on device: {self.device}")
        
        # Initialize face detector for LAA-Net preprocessing
        logger.info("🔍 Initializing face detector (MTCNN/OpenCV)...")
        self.face_detector = FaceDetector(method='auto')
        if self.face_detector.method == 'mtcnn':
            logger.info("✅ MTCNN face detection initialized successfully")
        else:
            logger.info("ℹ️  Using OpenCV Haar cascades for face detection (MTCNN unavailable or failed)")
        
        # Ensure Hugging Face token is visible to open_clip/huggingface_hub (higher rate limits, reliable CLIP downloads)
        _hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
        if _hf_token:
            os.environ["HF_TOKEN"] = _hf_token
            os.environ["HUGGING_FACE_HUB_TOKEN"] = _hf_token
            logger.info("🔑 Using Hugging Face token for CLIP (higher rate limits, best reliability)")
        
        # === CLIP Zero-Shot Setup ===
        logger.info("📦 Loading CLIP model (ViT-B-32)...")
        try:
            # Force CPU device explicitly to avoid CUDA errors
            self.device = 'cpu'
            
            # Suppress stderr during model loading to hide CUDA errors
            import contextlib
            import io
            stderr_suppressor = io.StringIO()
            
            with contextlib.redirect_stderr(stderr_suppressor):
                self.clip_model, _, self.clip_preprocess = open_clip.create_model_and_transforms(
                    clip_model_name, pretrained=clip_pretrained
                )
                self.clip_model.to('cpu')  # Explicitly use CPU
                self.clip_model.eval()
            
            # Optimized prompts for real vs. fake detection
            # Tuned for modern diffusion-based and traditional deepfakes
            texts = [
                "a real photograph of a human face taken by a camera",
                "a fake, manipulated, or AI-generated deepfake face, possibly from diffusion models"
            ]
            self.text_tokens = open_clip.tokenize(texts).to('cpu')
            with torch.no_grad():
                self.text_features = self.clip_model.encode_text(self.text_tokens)
                self.text_features /= self.text_features.norm(dim=-1, keepdim=True)
            
            logger.info("✅ CLIP model loaded successfully and ready for inference (CPU mode)")
        except Exception as e:
            # Check if it's a CUDA error - if so, try again with explicit CPU
            error_str = str(e).lower()
            if 'cuda' in error_str or 'cuinit' in error_str:
                logger.warning(f"⚠️  CUDA error during CLIP loading, retrying with explicit CPU mode...")
                try:
                    self.device = 'cpu'
                    import contextlib
                    import io
                    stderr_suppressor = io.StringIO()
                    
                    with contextlib.redirect_stderr(stderr_suppressor):
                        self.clip_model, _, self.clip_preprocess = open_clip.create_model_and_transforms(
                            clip_model_name, pretrained=clip_pretrained
                        )
                        self.clip_model.to('cpu')
                        self.clip_model.eval()
                    
                    texts = [
                        "a real photograph of a human face taken by a camera",
                        "a fake, manipulated, or AI-generated deepfake face, possibly from diffusion models"
                    ]
                    self.text_tokens = open_clip.tokenize(texts).to('cpu')
                    with torch.no_grad():
                        self.text_features = self.clip_model.encode_text(self.text_tokens)
                        self.text_features /= self.text_features.norm(dim=-1, keepdim=True)
                    
                    logger.info("✅ CLIP model loaded successfully in CPU mode after CUDA error")
                except Exception as e2:
                    logger.error(f"❌ Error loading CLIP model even in CPU mode: {e2}")
                    raise
            else:
                logger.error(f"❌ Error loading CLIP model: {e}")
                raise
        
        # === LAA-Net Setup (optional: requires external/laa_net clone + weights) ===
        self.laa_model = None
        self._laa_preprocess = None
        self._laa_device = self.device
        self.laa_available = False
        
        if _LAA_LOADER_AVAILABLE and load_laa_net and laa_weights_path and os.path.exists(laa_weights_path):
            try:
                logger.info("📦 Loading LAA-Net model...")
                laa_root = os.getenv("LAA_NET_ROOT")
                if not laa_root or not os.path.isdir(laa_root):
                    laa_root = os.path.join(os.path.dirname(__file__), "..", "external", "laa_net")
                laa_root = os.path.abspath(laa_root)
                if os.path.isdir(laa_root):
                    model, preprocess_fn, dev = load_laa_net(laa_root=laa_root, weights_path=laa_weights_path, device=self.device)
                    if model is not None and preprocess_fn is not None:
                        self.laa_model = model
                        self._laa_preprocess = preprocess_fn
                        self._laa_device = dev or self.device
                        self.laa_available = True
                        logger.info("✅ LAA-Net loaded; ensemble will use CLIP + LAA-Net.")
                if not self.laa_available:
                    logger.info("ℹ️  LAA-Net repo or config not found at %s. Using CLIP-only.", laa_root)
            except Exception as e:
                logger.warning("⚠️  Could not load LAA-Net: %s. Using CLIP-only.", e)
        else:
            if not _LAA_LOADER_AVAILABLE:
                logger.info("ℹ️  LAA-Net loader not available. Using CLIP-only detection.")
            elif not laa_weights_path:
                logger.info("ℹ️  LAA-Net weights path not provided. Using CLIP-only detection.")
            else:
                logger.info("ℹ️  LAA-Net weights not found at %s. Using CLIP-only detection.", laa_weights_path)
        
        logger.info("✅ EnhancedDetector initialization complete (LAA-Net optional, currently %s)", "enabled" if self.laa_available else "disabled")
        
        self.laa_transform = None  # Unused; preprocessing via _laa_preprocess
    
    def extract_frames(self, video_path: str, num_frames: int = 16) -> List[Image.Image]:
        """
        Extract evenly spaced frames from video.
        
        Args:
            video_path: Path to video file
            num_frames: Number of frames to extract
            
        Returns:
            List of PIL Images
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames == 0:
            cap.release()
            raise ValueError("Invalid video path or empty video.")
        
        interval = max(1, total_frames // num_frames)
        frames = []
        count = 0
        
        while cap.isOpened() and len(frames) < num_frames:
            ret, frame_bgr = cap.read()
            if not ret:
                break
            if count % interval == 0:
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                frames.append(Image.fromarray(frame_rgb))
            count += 1
        
        cap.release()
        
        if not frames:
            raise ValueError("No frames extracted from video.")
        
        return frames
    
    def clip_detect_frames(self, frames: List[Image.Image]) -> float:
        """
        Run CLIP zero-shot detection on frames and return average fake probability.
        
        Args:
            frames: List of PIL Images
            
        Returns:
            Average fake probability (0=real, 1=fake)
        """
        fake_probs = []
        
        for frame in frames:
            try:
                image_input = self.clip_preprocess(frame).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    image_features = self.clip_model.encode_image(image_input)
                    image_features /= image_features.norm(dim=-1, keepdim=True)
                    similarity = image_features @ self.text_features.T
                    probs = similarity.softmax(dim=-1)[0].cpu().numpy()
                    fake_prob = probs[1]  # Index 1 = fake prompt
                fake_probs.append(fake_prob)
            except Exception as e:
                print(f"CLIP detection error on frame: {e}")
                continue
        
        if not fake_probs:
            return 0.5  # Neutral if all frames failed
        
        return np.mean(fake_probs)
    
    def clip_detect_frames_probs(self, frames: List[Image.Image]) -> List[float]:
        """
        Run CLIP zero-shot on each frame and return per-frame fake probabilities.
        Used for real temporal consistency in forensic metrics.
        """
        probs = []
        for frame in frames:
            try:
                image_input = self.clip_preprocess(frame).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    image_features = self.clip_model.encode_image(image_input)
                    image_features /= image_features.norm(dim=-1, keepdim=True)
                    similarity = image_features @ self.text_features.T
                    p = similarity.softmax(dim=-1)[0].cpu().numpy()
                    probs.append(float(p[1]))
            except Exception:
                probs.append(0.5)
        return probs if probs else [0.5]
    
    def laa_detect_frames(self, frames: List[Image.Image]) -> float:
        """
        Run LAA-Net detection on frames.
        Uses real LAA-Net inference when laa_available else returns 0.5.
        """
        if not self.laa_available or self.laa_model is None or self._laa_preprocess is None:
            return 0.5
        if not run_laa_inference:
            return 0.5
        
        fake_probs = []
        for frame in frames:
            try:
                # PIL RGB -> numpy BGR (LAA-Net expects BGR like cv2.imread)
                frame_np = np.array(frame)
                if frame_np.ndim == 2:
                    frame_bgr = cv2.cvtColor(frame_np, cv2.COLOR_GRAY2BGR)
                else:
                    frame_bgr = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
                prob = run_laa_inference(
                    self.laa_model,
                    self._laa_preprocess,
                    frame_bgr,
                    device=self._laa_device,
                )
                fake_probs.append(prob)
            except Exception as e:
                logger.debug("LAA-Net detection error on frame: %s", e)
                continue
        if not fake_probs:
            return 0.5
        return float(np.mean(fake_probs))
    
    def detect(self, video_path: str, num_frames: int = 16) -> Dict[str, Any]:
        """
        Main detection method: Ensemble fake probability.
        
        Args:
            video_path: Path to video file
            num_frames: Number of frames to sample for detection
            
        Returns:
            Dictionary with detection results:
            - ensemble_fake_probability: Combined score (0=real, 1=fake)
            - clip_fake_probability: CLIP-only score
            - laa_fake_probability: LAA-Net score (or 0.5 if unavailable)
            - is_deepfake: Boolean prediction
            - method: Detection method used
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Extract frames
        frames = self.extract_frames(video_path, num_frames)
        
        # Run CLIP detection (and get per-frame probs for temporal consistency)
        clip_prob = self.clip_detect_frames(frames)
        clip_per_frame = self.clip_detect_frames_probs(frames)
        
        # Run LAA-Net detection (or placeholder)
        laa_prob = self.laa_detect_frames(frames)
        
        # Per-frame ensemble for real temporal consistency
        if self.laa_available:
            frame_probabilities = [(c + laa_prob) / 2.0 for c in clip_per_frame]
            ensemble_prob = (clip_prob + laa_prob) / 2.0
            method = 'ensemble_clip_laa'
        else:
            frame_probabilities = list(clip_per_frame)
            ensemble_prob = clip_prob
            method = 'clip_only'
        
        return {
            'ensemble_fake_probability': float(ensemble_prob),
            'clip_fake_probability': float(clip_prob),
            'laa_fake_probability': float(laa_prob),
            'frame_probabilities': frame_probabilities,
            'is_deepfake': ensemble_prob > 0.5,
            'method': method,
            'num_frames_analyzed': len(frames),
            'laa_available': self.laa_available
        }


# Global detector instance (lazy initialization)
_detector_instance = None
_detector_lock = None

# Backward compatibility: Keep the old function name for existing code
def detect_fake_enhanced(video_path: str, **kwargs) -> Dict[str, Any]:
    """
    Enhanced deepfake detection using ensemble of CLIP and LAA-Net.
    Backward compatibility wrapper for existing code.
    Uses singleton pattern to reuse detector instance across calls.
    """
    global _detector_instance, _detector_lock
    
    # Use singleton to avoid reloading CLIP model on every call
    if _detector_instance is None:
        try:
            _detector_instance = EnhancedDetector(**kwargs)
        except Exception as e:
            # If initialization fails, try again with explicit CPU
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"EnhancedDetector initialization failed: {e}, retrying with CPU...")
            os.environ['CUDA_VISIBLE_DEVICES'] = ''
            _detector_instance = EnhancedDetector(**kwargs)
    
    try:
        result = _detector_instance.detect(video_path)
        
        # Convert to expected format for backward compatibility (confidence = calibrated or agreement strength)
        ensemble_prob = result['ensemble_fake_probability']
        cal_method, cal_T = get_calibration_config()
        conf = confidence_from_ensemble(ensemble_prob, result['is_deepfake'], calibration=cal_method, temperature=cal_T)
        out = {
            'is_fake': result['is_deepfake'],
            'confidence': float(conf),
            'confidence_meaning': cal_method,
            'ensemble_score': ensemble_prob,
            'fake_probability': ensemble_prob,  # Explicit for API/frontend
            'authenticity_score': 1 - ensemble_prob,
            'detector_scores': {
                'clip_based': result['clip_fake_probability'],
                'laa_net': result['laa_fake_probability']
            },
            'method': result['method'],
            'video_hash': None,  # Can be added if needed
            'frame_count': result['num_frames_analyzed']
        }
        if result.get('frame_probabilities'):
            out['frame_probabilities'] = result['frame_probabilities']
        return out
    except Exception as e:
        # If detection fails, reset detector and retry once
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Detection failed: {e}, resetting detector and retrying...")
        _detector_instance = None  # Reset singleton
        try:
            _detector_instance = EnhancedDetector(**kwargs)
            result = _detector_instance.detect(video_path)
            ep = result['ensemble_fake_probability']
            cal_method, cal_T = get_calibration_config()
            conf = confidence_from_ensemble(ep, result['is_deepfake'], calibration=cal_method, temperature=cal_T)
            ret = {
                'is_fake': result['is_deepfake'],
                'confidence': float(conf),
                'confidence_meaning': cal_method,
                'ensemble_score': ep,
                'fake_probability': ep,
                'authenticity_score': 1 - ep,
                'detector_scores': {
                    'clip_based': result['clip_fake_probability'],
                    'laa_net': result['laa_fake_probability']
                },
                'method': result['method'],
                'video_hash': None,
                'frame_count': result['num_frames_analyzed']
            }
            if result.get('frame_probabilities'):
                ret['frame_probabilities'] = result['frame_probabilities']
            return ret
        except Exception as retry_e:
            # If retry also fails, raise the error
            logger.error(f"Detection failed even after retry: {retry_e}")
            raise retry_e


# Global detector instance for singleton pattern
_detector_instance = None

def get_enhanced_detector(**kwargs) -> EnhancedDetector:
    """Get or create enhanced detector instance (singleton)."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = EnhancedDetector(**kwargs)
    return _detector_instance


if __name__ == "__main__":
    # Example usage and testing
    print("Testing Enhanced DeepFake Detector (Priority 1 MVP)...")
    print("=" * 60)
    
    # Initialize detector
    detector = EnhancedDetector()
    print(f"Detector initialized on device: {detector.device}")
    print(f"CLIP model: Loaded")
    print(f"LAA-Net: {'Available' if detector.laa_available else 'Not available (submodule setup required)'}")
    print()
    
    # Test with sample video if available
    sample_videos = [
        "sample_video.mp4",
        "test_video_1.mp4",
        "test_video_2.mp4",
        "test_video_3.mp4"
    ]
    
    test_video = None
    for video in sample_videos:
        if os.path.exists(video):
            test_video = video
            break
    
    if test_video:
        print(f"Testing with {test_video}...")
        try:
            result = detector.detect(test_video, num_frames=16)
            print("\nDetection Results:")
            print(f"  Method: {result['method']}")
            print(f"  Is Deepfake: {result['is_deepfake']}")
            print(f"  Ensemble Probability: {result['ensemble_fake_probability']:.4f}")
            print(f"  CLIP Probability: {result['clip_fake_probability']:.4f}")
            print(f"  LAA-Net Probability: {result['laa_fake_probability']:.4f}")
            print(f"  Frames Analyzed: {result['num_frames_analyzed']}")
        except Exception as e:
            print(f"Error during detection: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("No sample video found. Enhanced detector is ready for use.")
        print("\nTo test:")
        print("  detector = EnhancedDetector()")
        print("  result = detector.detect('path/to/video.mp4')")
        print("  print(result)")
