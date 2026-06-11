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
# GPU / CPU selection: set FORCE_CPU=1 to pin to CPU (e.g. low-memory servers).
if os.getenv('FORCE_CPU', '0') == '1':
    os.environ.setdefault('CUDA_VISIBLE_DEVICES', '')

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow log noise

import cv2
import torch

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


# ---------------------------------------------------------------------------
# ResNet50 trained on Celeb-DF v2 (Kaggle, AUC 0.9065) — third ensemble member
# ---------------------------------------------------------------------------
def _build_resnet50_classifier():
    """Build the ResNet50 architecture that matches the Kaggle training head."""
    import torch.nn as nn
    from torchvision.models import resnet50
    model = resnet50(weights=None)
    model.fc = nn.Sequential(
        nn.Dropout(0.5),
        nn.Linear(2048, 512),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(512, 2),
    )
    return model


def _resnet50_val_transform():
    """Match the val transform used during Kaggle training (ImageNet norm, 224x224)."""
    import torchvision.transforms as transforms
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])


# ---------------------------------------------------------------------------
# ConvNeXt-Base trained on Celeb-DF v2 (Colab Pro, target AUC 0.95+) — fourth ensemble member
# ---------------------------------------------------------------------------
def _build_convnext_classifier(state_dict=None):
    """
    Build the ConvNeXt-Base architecture that matches a saved Colab checkpoint.

    Auto-detects between two architecture variants used across training runs:
      (A) Nested: model.classifier[2] = Sequential(Dropout, Linear, GELU, Dropout, Linear)
          → state_dict has classifier.0 (LayerNorm) and classifier.2.1 / classifier.2.4 (Linear)
      (B) Flat:   model.classifier = Sequential(Flatten, Dropout, Linear, GELU, Dropout, Linear)
          → state_dict has classifier.2 and classifier.5 (both Linear)

    Pass `state_dict` to pick the matching variant. Defaults to variant (A) — the
    "nested" form produced by train_convnext_colab.py.
    """
    import torch.nn as nn
    from torchvision.models import convnext_base
    model = convnext_base(weights=None)

    # Detect variant from state dict keys
    is_flat = False
    if state_dict is not None:
        is_flat = "classifier.5.weight" in state_dict

    if is_flat:
        model.classifier = nn.Sequential(
            nn.Flatten(1),            # 0: no params
            nn.Dropout(0.5),          # 1: no params
            nn.Linear(1024, 512),     # 2: classifier.2
            nn.GELU(),                # 3: no params
            nn.Dropout(0.3),          # 4: no params
            nn.Linear(512, 2),        # 5: classifier.5
        )
    else:
        # Nested variant — keep default LayerNorm2d + Flatten, replace classifier[2]
        model.classifier[2] = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(1024, 512),
            nn.GELU(),
            nn.Dropout(0.3),
            nn.Linear(512, 2),
        )
    return model


def _convnext_val_transform():
    """Match the val transform used during Colab training (same as ResNet50: 224x224, ImageNet norm)."""
    import torchvision.transforms as transforms
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])


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
                 clip_pretrained: str = 'laion2b_s34b_b79k',
                 resnet50_weights_path: Optional[str] = None,
                 convnext_weights_path: Optional[str] = None,
                 fft_weights_path: Optional[str] = None,
                 use_face_crop: bool = True):
        """
        Initialize the enhanced detector.

        Args:
            laa_weights_path: Path to LAA-Net pre-trained weights (optional)
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
            clip_model_name: CLIP model variant to use
            clip_pretrained: CLIP pretrained weights identifier
            use_face_crop: If True (default), detect and crop the face in each frame
                before running the detectors (B2). The trained ResNet50/ConvNeXt were
                trained on face crops, so this aligns inference with training. Falls
                back to the full frame whenever no face is found or face deps are missing.
        """
        # B2: face-cropping config. Stored before model setup so detect() can read it.
        self.use_face_crop = use_face_crop
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
            # Suppress stderr during model loading to hide any CUDA init noise
            import contextlib
            import io
            stderr_suppressor = io.StringIO()

            with contextlib.redirect_stderr(stderr_suppressor):
                self.clip_model, _, self.clip_preprocess = open_clip.create_model_and_transforms(
                    clip_model_name, pretrained=clip_pretrained
                )
                self.clip_model.to(self.device)
                self.clip_model.eval()

            # Optimized prompts for real vs. fake detection
            # Tuned for modern diffusion-based and traditional deepfakes
            texts = [
                "a real photograph of a human face taken by a camera",
                "a fake, manipulated, or AI-generated deepfake face, possibly from diffusion models"
            ]
            self.text_tokens = open_clip.tokenize(texts).to(self.device)
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
                        self.clip_model.to(self.device)
                        self.clip_model.eval()

                    texts = [
                        "a real photograph of a human face taken by a camera",
                        "a fake, manipulated, or AI-generated deepfake face, possibly from diffusion models"
                    ]
                    self.text_tokens = open_clip.tokenize(texts).to(self.device)
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

        # === ResNet50 (trained on Celeb-DF v2) Setup ===
        self.resnet50_model = None
        self.resnet50_transform = None
        self.resnet50_available = False

        if resnet50_weights_path is None:
            # Default path: ai_model/trained_models/resnet50_celeb_df_v2.pth
            _default = os.path.join(os.path.dirname(__file__), "trained_models", "resnet50_celeb_df_v2.pth")
            if os.path.isfile(_default):
                resnet50_weights_path = _default

        if resnet50_weights_path and os.path.isfile(resnet50_weights_path):
            try:
                logger.info("📦 Loading ResNet50 trained weights: %s", resnet50_weights_path)
                model = _build_resnet50_classifier()
                checkpoint = torch.load(resnet50_weights_path, map_location=self.device, weights_only=False)
                state_dict = checkpoint.get("model_state_dict", checkpoint)
                model.load_state_dict(state_dict)
                model.to(self.device)
                model.eval()
                self.resnet50_model = model
                self.resnet50_transform = _resnet50_val_transform()
                self.resnet50_available = True
                val_auc = checkpoint.get("val_auc") if isinstance(checkpoint, dict) else None
                logger.info("✅ ResNet50 loaded (val_auc=%s); ensemble now includes ResNet50.",
                            f"{val_auc:.4f}" if isinstance(val_auc, float) else "n/a")
            except Exception as e:
                logger.warning("⚠️  Could not load ResNet50 weights: %s. Falling back without ResNet50.", e)
        else:
            logger.info("ℹ️  ResNet50 weights not found; ensemble will skip ResNet50 component.")

        # === ConvNeXt-Base (trained on Celeb-DF v2) Setup ===
        self.convnext_model = None
        self.convnext_transform = None
        self.convnext_available = False

        if convnext_weights_path is None:
            # Prefer best_convnext_model.pth (from the latest 30-epoch Colab run) if present,
            # otherwise fall back to convnext_celeb_df_v2.pth.
            _models_dir = os.path.join(os.path.dirname(__file__), "trained_models")
            for _candidate in ("best_convnext_model.pth", "convnext_celeb_df_v2.pth"):
                _p = os.path.join(_models_dir, _candidate)
                if os.path.isfile(_p):
                    convnext_weights_path = _p
                    break

        if convnext_weights_path and os.path.isfile(convnext_weights_path):
            try:
                logger.info("📦 Loading ConvNeXt-Base trained weights: %s", convnext_weights_path)
                # PyTorch 2.6 defaults weights_only=True which fails on checkpoints with
                # metadata (epoch, val_auc, etc). These are trusted internal artifacts.
                checkpoint = torch.load(convnext_weights_path, map_location=self.device,
                                        weights_only=False)
                state_dict = checkpoint.get("model_state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
                # Build architecture variant matching the state_dict
                model = _build_convnext_classifier(state_dict=state_dict)
                model.load_state_dict(state_dict)
                model.to(self.device)
                model.eval()
                self.convnext_model = model
                self.convnext_transform = _convnext_val_transform()
                self.convnext_available = True
                val_auc = checkpoint.get("val_auc") if isinstance(checkpoint, dict) else None
                logger.info("✅ ConvNeXt-Base loaded (val_auc=%s); ensemble now includes ConvNeXt.",
                            f"{val_auc:.4f}" if isinstance(val_auc, float) else "n/a")
            except Exception as e:
                logger.warning("⚠️  Could not load ConvNeXt weights: %s. Falling back without ConvNeXt.", e)
        else:
            logger.info("ℹ️  ConvNeXt weights not found; ensemble will skip ConvNeXt component.")

        # === FFT frequency-domain detector (logistic regression on radial spectra) ===
        self.fft_model = None
        self.fft_available = False
        if fft_weights_path is None:
            _default = os.path.join(os.path.dirname(__file__), "trained_models", "fft_detector.pkl")
            if os.path.isfile(_default):
                fft_weights_path = _default

        if fft_weights_path and os.path.isfile(fft_weights_path):
            try:
                logger.info("📦 Loading FFT detector: %s", fft_weights_path)
                from ai_model.fft_detector import FFTDeepfakeDetector
                self.fft_model = FFTDeepfakeDetector().load(fft_weights_path)
                self.fft_available = True
                test_auc = self.fft_model.metadata.get("test_metrics", {}).get("auc")
                logger.info("✅ FFT detector loaded (test_auc=%s); ensemble now includes FFT.",
                            f"{test_auc:.4f}" if isinstance(test_auc, float) else "n/a")
            except Exception as e:
                logger.warning("⚠️  Could not load FFT detector: %s. Falling back without FFT.", e)
        else:
            logger.info("ℹ️  FFT detector weights not found; ensemble will skip FFT component.")

        # === Learned ensemble weights (optional; produced by learn_ensemble_weights.py) ===
        self.ensemble_weights = None
        _weights_path = os.path.join(os.path.dirname(__file__), "trained_models", "ensemble_weights.json")
        if os.path.isfile(_weights_path):
            try:
                import json as _json
                with open(_weights_path) as _f:
                    ew = _json.load(_f)
                # Validate: expected keys
                if "coefficients" in ew and "intercept" in ew and "detectors" in ew:
                    self.ensemble_weights = ew
                    coefs = ew["coefficients"]
                    logger.info("📏 Loaded learned ensemble weights: clip=%.3f laa=%.3f resnet50=%.3f intercept=%.3f",
                                coefs[0], coefs[1], coefs[2], ew["intercept"])
            except Exception as e:
                logger.warning("⚠️  Could not load ensemble weights: %s. Using unweighted mean.", e)

        logger.info("✅ EnhancedDetector initialization complete (LAA: %s, ResNet50: %s, ConvNeXt: %s, FFT: %s, weighted: %s)",
                    "enabled" if self.laa_available else "disabled",
                    "enabled" if self.resnet50_available else "disabled",
                    "enabled" if self.convnext_available else "disabled",
                    "enabled" if self.fft_available else "disabled",
                    "yes" if self.ensemble_weights else "no")

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

    def crop_faces(self, frames: List[Image.Image]) -> List[Image.Image]:
        """
        Face-crop each frame before inference (B2).

        The trained ResNet50/ConvNeXt detectors were trained on Celeb-DF v2 *face
        crops*, so feeding full frames is a train/inference mismatch. This wires the
        existing FaceDetector (MTCNN with OpenCV-Haar fallback) so each frame is
        cropped to the largest detected face before being handed to the detectors.

        Graceful degradation:
          - If self.use_face_crop is False, frames are returned unchanged.
          - If no face is detected in a frame (or face deps/MTCNN are unavailable),
            that frame falls back to the original full frame with a debug warning.
          - Any unexpected error is caught so detection never crashes on this step.
        CPU-safe: FaceDetector already falls back to OpenCV Haar cascades when MTCNN
        / TensorFlow is unavailable.
        """
        import logging
        _logger = logging.getLogger(__name__)

        if not self.use_face_crop or not frames:
            return frames

        # If neither MTCNN nor a Haar cascade is available, skip cropping entirely.
        fd = getattr(self, "face_detector", None)
        if fd is None or (fd.mtcnn is None and fd.haar_cascade is None):
            _logger.warning("⚠️  Face detector unavailable; using full frames (no face crop).")
            return frames

        cropped: List[Image.Image] = []
        n_cropped = 0
        for frame in frames:
            try:
                # FaceDetector works on numpy arrays. PIL frames are RGB.
                arr = np.array(frame)
                face = fd.crop_face(arr, target_size=(224, 224), padding=0.2)
                if face is not None and face.size > 0:
                    cropped.append(Image.fromarray(face))
                    n_cropped += 1
                else:
                    # No face found -> safe fallback to the full frame.
                    cropped.append(frame)
            except Exception as e:  # never let face cropping break detection
                _logger.debug("Face crop failed on a frame (%s); using full frame.", e)
                cropped.append(frame)

        if n_cropped == 0:
            _logger.info("ℹ️  No faces detected in any frame; using full frames for inference.")
        return cropped

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

    def laa_detect_frames_probs(self, frames: List[Image.Image]) -> List[float]:
        """
        Run LAA-Net per frame; return per-frame fake probabilities.
        Returns [0.5] if LAA-Net is unavailable.
        """
        if not self.laa_available or self.laa_model is None or self._laa_preprocess is None:
            return [0.5]
        if not run_laa_inference:
            return [0.5]

        import logging
        _logger = logging.getLogger(__name__)
        fake_probs = []
        for frame in frames:
            try:
                frame_np = np.array(frame)
                if frame_np.ndim == 2:
                    frame_bgr = cv2.cvtColor(frame_np, cv2.COLOR_GRAY2BGR)
                else:
                    frame_bgr = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
                prob = run_laa_inference(
                    self.laa_model, self._laa_preprocess, frame_bgr, device=self._laa_device,
                )
                fake_probs.append(float(prob))
            except Exception as e:
                _logger.debug("LAA-Net detection error on frame: %s", e)
                fake_probs.append(0.5)
        return fake_probs if fake_probs else [0.5]

    def laa_detect_frames(self, frames: List[Image.Image]) -> float:
        """Aggregate LAA-Net fake probability across frames (mean)."""
        probs = self.laa_detect_frames_probs(frames)
        return float(np.mean(probs)) if probs else 0.5

    def resnet50_detect_frames_probs(self, frames: List[Image.Image]) -> List[float]:
        """
        Run ResNet50 (trained on Celeb-DF v2) per-frame and return fake probabilities.
        Returns [0.5] if ResNet50 is unavailable.
        """
        if not self.resnet50_available or self.resnet50_model is None:
            return [0.5]
        probs = []
        for frame in frames:
            try:
                x = self.resnet50_transform(frame).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    logits = self.resnet50_model(x)
                    p = torch.softmax(logits, dim=1)[0, 1].item()  # index 1 = fake
                probs.append(float(p))
            except Exception:
                probs.append(0.5)
        return probs if probs else [0.5]

    def resnet50_detect_frames(self, frames: List[Image.Image]) -> float:
        """Aggregate ResNet50 fake probability across frames (mean)."""
        probs = self.resnet50_detect_frames_probs(frames)
        return float(np.mean(probs)) if probs else 0.5

    def convnext_detect_frames_probs(self, frames: List[Image.Image]) -> List[float]:
        """
        Run ConvNeXt-Base (trained on Celeb-DF v2) per-frame; return fake probs.
        Returns [0.5] if ConvNeXt is unavailable.
        """
        if not self.convnext_available or self.convnext_model is None:
            return [0.5]
        probs = []
        for frame in frames:
            try:
                x = self.convnext_transform(frame).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    logits = self.convnext_model(x)
                    p = torch.softmax(logits, dim=1)[0, 1].item()
                probs.append(float(p))
            except Exception:
                probs.append(0.5)
        return probs if probs else [0.5]

    def convnext_detect_frames(self, frames: List[Image.Image]) -> float:
        """Aggregate ConvNeXt fake probability across frames (mean)."""
        probs = self.convnext_detect_frames_probs(frames)
        return float(np.mean(probs)) if probs else 0.5

    def fft_detect_frames_probs(self, frames: List[Image.Image]) -> List[float]:
        """Run FFT frequency-domain detector per-frame."""
        if not self.fft_available or self.fft_model is None:
            return [0.5]
        try:
            return self.fft_model.predict_proba_batch(frames)
        except Exception:
            return [0.5] * len(frames)

    def fft_detect_frames(self, frames: List[Image.Image]) -> float:
        probs = self.fft_detect_frames_probs(frames)
        return float(np.mean(probs)) if probs else 0.5

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

        frames = self.extract_frames(video_path, num_frames)
        # B2: face-crop/align frames before inference (no-op if use_face_crop is False
        # or face deps are unavailable; falls back to full frame per-frame as needed).
        frames = self.crop_faces(frames)
        num = len(frames)

        # --- Per-detector per-frame probabilities (0.5 placeholder if unavailable) ---
        per_frame = {
            "clip":     self.clip_detect_frames_probs(frames),
            "laa":      self.laa_detect_frames_probs(frames) if self.laa_available else [0.5] * num,
            "resnet50": self.resnet50_detect_frames_probs(frames) if self.resnet50_available else [0.5] * num,
            "convnext": self.convnext_detect_frames_probs(frames) if self.convnext_available else [0.5] * num,
            "fft":      self.fft_detect_frames_probs(frames) if self.fft_available else [0.5] * num,
        }
        # Pad / truncate per-frame lists to length `num` so per-frame ensemble is well-defined
        for k, v in per_frame.items():
            if len(v) == 1 and num > 1:
                per_frame[k] = v * num
            elif len(v) < num:
                per_frame[k] = v + [v[-1]] * (num - len(v))
            elif len(v) > num:
                per_frame[k] = v[:num]

        # --- Per-detector aggregate probabilities ---
        agg = {k: float(np.mean(v)) for k, v in per_frame.items()}
        availability = {
            "clip": True,
            "laa": self.laa_available,
            "resnet50": self.resnet50_available,
            "convnext": self.convnext_available,
            "fft": self.fft_available,
        }

        # --- Ensemble combination (MODEL-HONESTY, task B3) ---
        # Production rule: prefer the LEARNED logistic ensemble
        # (trained_models/ensemble_weights.json, test AUC ~0.936). Its coefficients
        # already down-weight the chance-level detectors to ~0 (clip≈0.001, laa≈0.021)
        # and let the trained detectors dominate (resnet50≈1.09, convnext≈0.95, fft≈0.036).
        #
        # The learned weights are applied as long as at least one TRAINED detector
        # (resnet50/convnext/fft) is loaded. Any detector that is unavailable contributes
        # its neutral 0.5 placeholder; because clip/laa carry near-zero coefficients this
        # is effectively a no-op for them, so we do NOT require clip/laa to be present.
        TRAINED = ("resnet50", "convnext", "fft")  # detectors actually trained for this task
        method_parts = [k for k in ("clip", "laa", "resnet50", "convnext", "fft") if availability[k]]

        use_weighted = (
            self.ensemble_weights is not None
            and self.ensemble_weights.get("detectors")
            and any(availability.get(d, False) for d in TRAINED)
        )

        if use_weighted:
            detectors = self.ensemble_weights["detectors"]
            coefs     = self.ensemble_weights["coefficients"]
            intercept = self.ensemble_weights["intercept"]
            # agg[d] is 0.5 for any unavailable detector; combined with its near-zero
            # learned coefficient this contributes essentially nothing to the logit.
            logit = intercept + sum(coefs[i] * agg[d] for i, d in enumerate(detectors))
            ensemble_prob = float(1.0 / (1.0 + np.exp(-logit)))
            method_parts.append("weighted")

            frame_probabilities = []
            for i in range(num):
                logit_i = intercept + sum(coefs[j] * per_frame[d][i] for j, d in enumerate(detectors))
                frame_probabilities.append(float(1.0 / (1.0 + np.exp(-logit_i))))
        else:
            # Fallback (no learned weights, or no trained detector loaded): average ONLY the
            # trained detectors. We intentionally exclude chance-level clip/laa here so a
            # missing learned-weights file can never let an AUC~0.49 signal dominate the score.
            trained_available = [d for d in TRAINED if availability[d]]
            fallback_parts = trained_available if trained_available else method_parts
            available_probs = [agg[d] for d in fallback_parts]
            ensemble_prob = float(np.mean(available_probs)) if available_probs else 0.5

            frame_probabilities = []
            for i in range(num):
                vals = [per_frame[d][i] for d in fallback_parts]
                frame_probabilities.append(float(np.mean(vals)) if vals else 0.5)

        method = "ensemble_" + "_".join(method_parts) if len(method_parts) > 1 else "clip_only"

        return {
            "ensemble_fake_probability":  ensemble_prob,
            "clip_fake_probability":      agg["clip"],
            "laa_fake_probability":       agg["laa"],
            "resnet50_fake_probability":  agg["resnet50"],
            "convnext_fake_probability":  agg["convnext"],
            "fft_fake_probability":       agg["fft"],
            "frame_probabilities":        frame_probabilities,
            "is_deepfake":                ensemble_prob > 0.5,
            "method":                     method,
            "num_frames_analyzed":        num,
            "laa_available":              self.laa_available,
            "resnet50_available":         self.resnet50_available,
            "convnext_available":         self.convnext_available,
            "fft_available":              self.fft_available,
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
                'laa_net': result['laa_fake_probability'],
                'resnet50': result.get('resnet50_fake_probability', 0.5),
                'convnext': result.get('convnext_fake_probability', 0.5),
                'fft':      result.get('fft_fake_probability', 0.5),
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
                    'laa_net': result['laa_fake_probability'],
                    'resnet50': result.get('resnet50_fake_probability', 0.5),
                    'convnext': result.get('convnext_fake_probability', 0.5),
                    'fft':      result.get('fft_fake_probability', 0.5)
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
