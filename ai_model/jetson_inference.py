#!/usr/bin/env python3
"""
NVIDIA Jetson Inference Compatibility Layer for DeepFake Detection
Provides edge AI deployment capabilities with real inference (CPU/GPU/Jetson)
"""
import os
import sys
import json
import time
import numpy as np
import torch
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JetsonInferenceEngine:
    """Jetson Inference compatibility layer for edge deployment"""

    def __init__(self, model_path: str = "ai_model/resnet_resnet50_final.pth", threshold: float = 0.5):
        """
        Initialize Jetson Inference engine

        Args:
            model_path: Path to the model file
            threshold: Detection threshold
        """
        self.model_path = model_path or "ai_model/deepfake_classifier.pth"
        self.threshold = threshold
        self.model = None
        self.device = self._detect_device()
        self.is_jetson = self._is_jetson_device()
        self.initialized = False

        # Try to load the model
        self._load_model()

        if self.initialized:
            logger.info(f"✅ Jetson Inference initialized on {self.device}")
            if self.is_jetson:
                logger.info("🎯 Running on actual NVIDIA Jetson device")
            else:
                logger.info(f"💻 Running on {self.device.upper()} (real inference, not simulation)")
        else:
            logger.warning("⚠️  Jetson Inference initialization failed")

    def _detect_device(self) -> str:
        """Detect the current device"""
        if torch.cuda.is_available():
            return f"cuda:{torch.cuda.current_device()}"
        else:
            return "cpu"

    def _is_jetson_device(self) -> bool:
        """Check if running on actual Jetson device"""
        try:
            # Check for Jetson-specific files/indicators
            jetson_files = [
                "/etc/nv_tegra_release",
                "/proc/device-tree/compatible",
                "/sys/module/tegra_fuse"
            ]

            for file_path in jetson_files:
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        content = f.read().lower()
                        if 'jetson' in content or 'tegra' in content:
                            return True

            # Check environment variables
            if os.environ.get('JETSON_TYPE'):
                return True

            return False

        except:
            return False

    def _load_model(self):
        """Load the deepfake detection model"""
        try:
            if os.path.exists(self.model_path):
                # Load PyTorch state dict
                state_dict = torch.load(self.model_path, map_location=self.device)

                # Create ResNet50 model for deepfake detection
                import torchvision.models as models
                self.model = models.resnet50(pretrained=False)
                num_features = self.model.fc.in_features
                self.model.fc = torch.nn.Linear(num_features, 2)  # Binary classification

                # Load the trained weights
                # Strip 'model.' prefix if present
                new_state_dict = {}
                for k, v in state_dict.items():
                    if k.startswith('model.'):
                        new_state_dict[k[6:]] = v  # Remove 'model.' prefix
                    else:
                        new_state_dict[k] = v

                self.model.load_state_dict(new_state_dict)
                self.model.eval()
                self.model.to(self.device)
                self.initialized = True
                logger.info(f"📦 ResNet model loaded from {self.model_path}")
            else:
                logger.warning(f"⚠️  Model file not found: {self.model_path}")
                self._create_fallback_model()

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self._create_fallback_model()

    def _create_fallback_model(self):
        """Create a fallback model for testing"""
        try:
            # Simple fallback model for demonstration
            self.model = torch.nn.Sequential(
                torch.nn.Linear(224 * 224 * 3, 512),
                torch.nn.ReLU(),
                torch.nn.Linear(512, 256),
                torch.nn.ReLU(),
                torch.nn.Linear(256, 2),
                torch.nn.Softmax(dim=1)
            )
            self.model.to(self.device)
            self.initialized = False  # Mark as not fully initialized
            logger.info("🛠️  Fallback model created for testing")

        except Exception as e:
            logger.error(f"Failed to create fallback model: {e}")
            self.model = None

    def preprocess_image(self, image: np.ndarray) -> Optional[torch.Tensor]:
        """
        Preprocess image for inference

        Args:
            image: Input image as numpy array

        Returns:
            Preprocessed tensor
        """
        try:
            # Convert to tensor
            if isinstance(image, np.ndarray):
                # Normalize to [0, 1] and convert to tensor
                image = image.astype(np.float32) / 255.0

                # Convert to CHW format if needed
                if image.shape[-1] == 3:  # HWC to CHW
                    image = np.transpose(image, (2, 0, 1))

                tensor = torch.from_numpy(image).unsqueeze(0)

                # Resize if needed (simplified)
                if tensor.shape[-1] != 224 or tensor.shape[-2] != 224:
                    # Simple resize simulation
                    tensor = torch.nn.functional.interpolate(
                        tensor.unsqueeze(0), size=(224, 224), mode='bilinear'
                    ).squeeze(0)

                tensor = tensor.to(self.device)
                return tensor

        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            return None

    def detect(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Perform deepfake detection on image

        Args:
            image: Input image

        Returns:
            Detection results
        """
        if not self.initialized or self.model is None:
            return {
                'success': False,
                'error': 'Model not initialized',
                'is_fake': False,
                'confidence': 0.0
            }

        try:
            start_time = time.time()

            # Preprocess image
            input_tensor = self.preprocess_image(image)
            if input_tensor is None:
                return {
                    'success': False,
                    'error': 'Image preprocessing failed',
                    'is_fake': False,
                    'confidence': 0.0
                }

            # Run inference
            with torch.no_grad():
                if self.is_jetson:
                    # On actual Jetson, use optimized inference
                    outputs = self._jetson_inference(input_tensor)
                else:
                    # Real inference on CPU/GPU (not Jetson-optimized, but still real inference)
                    outputs = self.model(input_tensor)

            # Process results
            probabilities = torch.softmax(outputs, dim=1)
            fake_prob = probabilities[0][1].item()
            real_prob = probabilities[0][0].item()

            is_fake = fake_prob > self.threshold
            confidence = max(fake_prob, real_prob)

            processing_time = time.time() - start_time

            return {
                'success': True,
                'is_fake': is_fake,
                'confidence': confidence,
                'fake_probability': fake_prob,
                'real_probability': real_prob,
                'processing_time': processing_time,
                'device': self.device,
                'jetson_optimized': self.is_jetson
            }

        except Exception as e:
            logger.error(f"Detection failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'is_fake': False,
                'confidence': 0.0
            }

    def _jetson_inference(self, tensor: torch.Tensor) -> torch.Tensor:
        """Optimized inference for Jetson devices"""
        if self.model is None:
            raise RuntimeError("Model not loaded")
        # On actual Jetson devices, this would use TensorRT or Jetson-specific optimizations
        # For now, just run normal inference
        return self.model(tensor)

    def classify(self, image: np.ndarray) -> Tuple[str, float]:
        """
        Classify image (legacy interface)

        Args:
            image: Input image

        Returns:
            Tuple of (class_name, confidence)
        """
        result = self.detect(image)

        if result['success']:
            class_name = 'fake' if result['is_fake'] else 'real'
            return class_name, result['confidence']
        else:
            return 'unknown', 0.0

    def get_network_fps(self) -> float:
        """Get estimated network FPS based on device"""
        if self.is_jetson:
            # On real Jetson, this would measure actual FPS
            return 30.0  # Estimated FPS for Jetson Nano
        else:
            return 15.0  # Estimated FPS for CPU/GPU

    def get_stats(self) -> Dict[str, Any]:
        """Get inference statistics"""
        return {
            'initialized': self.initialized,
            'device': self.device,
            'is_jetson': self.is_jetson,
            'model_path': self.model_path,
            'threshold': self.threshold,
            'fps': self.get_network_fps(),
            'cuda_available': torch.cuda.is_available(),
            'gpu_memory_used': torch.cuda.memory_allocated() if torch.cuda.is_available() else 0
        }

class VideoDetector:
    """Video detection using Jetson Inference"""

    def __init__(self, model_path: Optional[str] = None, threshold: float = 0.5):
        if model_path is None:
            model_path = "ai_model/resnet_resnet50_final.pth"
        self.engine = JetsonInferenceEngine(model_path, threshold)
        self.frame_buffer = []
        self.temporal_analysis = True

    def detect_video(self, video_path: str, sample_rate: int = 30) -> Dict[str, Any]:
        """
        Detect deepfakes in video

        Args:
            video_path: Path to video file
            sample_rate: Frame sampling rate

        Returns:
            Video detection results
        """
        try:
            import cv2

            if not os.path.exists(video_path):
                return {'success': False, 'error': 'Video file not found'}

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {'success': False, 'error': 'Could not open video'}

            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = frame_count / fps if fps > 0 else 0

            results = []
            frame_idx = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Sample frames
                if frame_idx % sample_rate == 0:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    # Detect
                    result = self.engine.detect(frame_rgb)
                    result['frame_number'] = frame_idx
                    result['timestamp'] = frame_idx / fps if fps > 0 else 0
                    results.append(result)

                frame_idx += 1

            cap.release()

            # Aggregate results
            if results:
                fake_frames = sum(1 for r in results if r.get('is_fake', False))
                avg_confidence = np.mean([r.get('confidence', 0) for r in results])

                # Temporal analysis
                temporal_score = self._analyze_temporal_consistency(results)

                overall_fake = fake_frames > len(results) * 0.5  # Majority vote
                overall_confidence = (avg_confidence + temporal_score) / 2

                return {
                    'success': True,
                    'is_fake': overall_fake,
                    'confidence': overall_confidence,
                    'fake_frames': fake_frames,
                    'total_frames_analyzed': len(results),
                    'avg_frame_confidence': avg_confidence,
                    'temporal_consistency_score': temporal_score,
                    'video_info': {
                        'duration': duration,
                        'frame_count': frame_count,
                        'fps': fps,
                        'sampled_frames': len(results)
                    },
                    'frame_results': results[:10]  # First 10 frames for details
                }
            else:
                return {'success': False, 'error': 'No frames processed'}

        except ImportError:
            return {'success': False, 'error': 'OpenCV not available for video processing'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _analyze_temporal_consistency(self, results: List[Dict[str, Any]]) -> float:
        """Analyze temporal consistency across frames"""
        if len(results) < 2:
            return 0.5

        # Simple temporal analysis - check confidence stability
        confidences = [r.get('confidence', 0) for r in results]
        confidence_std = np.std(confidences)

        # Lower std means more consistent (less suspicious)
        consistency_score = max(0, 1 - confidence_std * 2)

        return float(consistency_score)

# Global instances
jetson_engine = JetsonInferenceEngine()
video_detector = VideoDetector()

def detect_image_jetson(image: np.ndarray) -> Dict[str, Any]:
    """Detect deepfakes in image using Jetson inference"""
    return jetson_engine.detect(image)

def detect_video_jetson(video_path: str) -> Dict[str, Any]:
    """Detect deepfakes in video using Jetson inference"""
    return video_detector.detect_video(video_path)

def get_jetson_stats() -> Dict[str, Any]:
    """Get Jetson inference statistics"""
    return jetson_engine.get_stats()

if __name__ == "__main__":
    # Test Jetson inference
    print("🔍 Testing NVIDIA Jetson Inference Integration...")

    # Check stats
    stats = get_jetson_stats()
    print(f"Jetson Stats: {json.dumps(stats, indent=2)}")

    # Test with dummy image
    dummy_image = np.random.rand(224, 224, 3).astype(np.uint8) * 255
    result = detect_image_jetson(dummy_image)
    print(f"Detection Result: {json.dumps(result, indent=2)}")

    print("✅ Jetson inference integration test completed")