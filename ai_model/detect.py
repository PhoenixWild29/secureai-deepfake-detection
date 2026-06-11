#!/usr/bin/env python3
"""
SecureAI DeepFake Detection
Main detection module with multiple model options
"""
import os

# GPU / CPU selection:
# By default, auto-detect GPU. Set FORCE_CPU=1 to pin to CPU (e.g. for low-memory servers).
if os.getenv('FORCE_CPU', '0') == '1':
    os.environ.setdefault('CUDA_VISIBLE_DEVICES', '')

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow log noise

import cv2
import torch

import numpy as np
import hashlib
from typing import Dict, Any
import time

# Import our models
try:
    from .deepfake_classifier import DeepfakeClassifier, ResNetDeepfakeClassifier
    from .enhanced_detector import detect_fake_enhanced
    from .ensemble_detector import detect_fake_ensemble
except ImportError:
    # Fallback for when called from root directory
    from ai_model.deepfake_classifier import DeepfakeClassifier, ResNetDeepfakeClassifier
    from ai_model.enhanced_detector import detect_fake_enhanced
    try:
        from ai_model.ensemble_detector import detect_fake_ensemble
    except ImportError:
        detect_fake_ensemble = None

def detect_fake(video_path: str, model_type: str = 'enhanced') -> Dict[str, Any]:
    """
    Main detection function with multiple model options

    Args:
        video_path: Path to video file
        model_type: 'cnn', 'yolo', 'ensemble', or 'enhanced'

    Returns:
        Detection results dictionary
    """
    # Use VideoPathManager for reliable path resolution
    try:
        from utils.video_paths import get_video_path_manager
        path_manager = get_video_path_manager()
        resolved_path = path_manager.resolve_video_path(video_path)

        if resolved_path is None:
            raise FileNotFoundError(
                f"Video file not found: {video_path}\n"
                f"Searched in: {path_manager.get_uploads_directory()}, test_videos, and standard locations"
            )

        video_path = str(resolved_path)
    except ImportError:
        # Fallback if VideoPathManager not available
        if not os.path.exists(video_path):
            # Try in uploads directory
            uploads_path = os.path.join('uploads', os.path.basename(video_path))
            if os.path.exists(uploads_path):
                video_path = uploads_path
            else:
                # Try absolute path in /app/uploads
                abs_uploads_path = os.path.join('/app/uploads', os.path.basename(video_path))
                if os.path.exists(abs_uploads_path):
                    video_path = abs_uploads_path
                else:
                    raise FileNotFoundError(f"Video file not found: {video_path} (also checked uploads/ and /app/uploads/)")

    start_time = time.time()

    try:
        if model_type in ('enhanced', 'ensemble', 'full_ensemble'):
            # PRODUCTION PATH (MODEL-HONESTY fix, task B1):
            # Route to EnhancedDetector (via detect_fake_enhanced), which loads the
            # TRAINED detectors -- resnet50_celeb_df_v2 (test AUC 0.906), convnext (0.915),
            # fft -- and combines them with the learned logistic ensemble
            # (trained_models/ensemble_weights.json, test AUC ~0.936).
            #
            # We deliberately do NOT use EnsembleDetector here: that path loads a
            # leakage-trained ResNet plus UNTRAINED random-head Xception/EfficientNet and
            # gives meaningful weight to chance-level CLIP/LAA (AUC ~0.49). EnsembleDetector
            # is kept for reference/back-compat only -- see its module docstring.
            result = detect_fake_enhanced(video_path)
            if result.get('method') in ('ensemble_unavailable', 'ensemble_error') or result.get('error'):
                raise ValueError(result.get('error', 'Detector unavailable. Restart the backend or retry.'))
            # detect_fake_enhanced already returns is_fake / confidence / fake_probability /
            # authenticity_score / detector_scores. Normalise the few legacy aliases the
            # API/frontend may still read so the response schema is unchanged.
            if 'ensemble_score' in result:
                result.setdefault('ensemble_fake_probability', result['ensemble_score'])
            if 'fake_probability' in result:
                result['is_fake'] = result.get('is_fake', result['fake_probability'] > 0.5)
                result.setdefault('confidence', result.get('confidence', result['fake_probability']))
                result.setdefault('authenticity_score', 1 - result['fake_probability'])

        elif model_type == 'cnn':
            # Use our custom CNN classifier
            classifier = DeepfakeClassifier()
            result = classifier.predict_video(video_path)

        elif model_type == 'resnet':
            # Use ResNet-based classifier
            classifier = ResNetDeepfakeClassifier()
            result = classifier.predict_video(video_path)

        else:
            raise ValueError(f"Unknown model type: {model_type}")

        # Add processing time
        result['processing_time'] = time.time() - start_time

        # Generate video hash if not present
        if 'video_hash' not in result:
            with open(video_path, 'rb') as f:
                result['video_hash'] = hashlib.sha256(f.read()).hexdigest()

        # Ensure authenticity_score is present
        if 'authenticity_score' not in result:
            result['authenticity_score'] = 1 - result.get('confidence', 0)

        # Ensure fake_probability is always set (frontend and API rely on it)
        if 'fake_probability' not in result:
            result['fake_probability'] = result.get(
                'ensemble_fake_probability',
                result.get('ensemble_score', result.get('confidence', 0.5))
            )

        return result

    except Exception as e:
        # Fallback error handling
        return {
            'is_fake': False,
            'confidence': 0.0,
            'error': str(e),
            'video_hash': hashlib.sha256(open(video_path, 'rb').read()).hexdigest(),
            'authenticity_score': 0.5,
            'processing_time': time.time() - start_time,
            'method': 'error_fallback'
        }

def get_available_models() -> Dict[str, str]:
    """Get available detection models and their descriptions"""
    # NOTE (B1): 'enhanced'/'ensemble'/'full_ensemble' all map to EnhancedDetector,
    # which runs the trained ResNet50 + ConvNeXt + FFT detectors combined with the
    # learned logistic ensemble (test AUC ~0.936 on Celeb-DF v2).
    models = {
        'enhanced': 'Trained ensemble: ResNet50 + ConvNeXt + FFT via learned logistic weights (Recommended)',
        'ensemble': 'Trained ensemble: ResNet50 + ConvNeXt + FFT via learned logistic weights (Recommended)',
        'full_ensemble': 'Trained ensemble: ResNet50 + ConvNeXt + FFT via learned logistic weights (Recommended)',
        'cnn': 'Custom CNN classifier with YOLO face detection',
        'resnet': 'ResNet-based deepfake classifier'
    }
    return models

def benchmark_models(video_path: str) -> Dict[str, Any]:
    """Benchmark all available models on a video"""
    results = {}
    models = get_available_models()

    for model_name, description in models.items():
        try:
            start_time = time.time()
            result = detect_fake(video_path, model_name)
            processing_time = time.time() - start_time

            results[model_name] = {
                'result': result,
                'processing_time': processing_time,
                'description': description,
                'success': True
            }
        except Exception as e:
            results[model_name] = {
                'error': str(e),
                'processing_time': time.time() - start_time,
                'description': description,
                'success': False
            }

    return results

if __name__ == "__main__":
    # Test the detection system
    print("SecureAI DeepFake Detection System")
    print("=" * 50)

    # Test with sample video
    sample_video = "../../sample_video.mp4"
    if os.path.exists(sample_video):
        print(f"Testing with: {sample_video}")
        print("\nAvailable models:")
        for name, desc in get_available_models().items():
            print(f"- {name}: {desc}")

        print("\nRunning benchmark...")
        benchmark_results = benchmark_models(sample_video)

        for model_name, result in benchmark_results.items():
            print(f"\n{model_name.upper()} Results:")
            if result['success']:
                r = result['result']
                print(f"  Fake probability: {r.get('fake_probability', 0):.2%}")
                print(f"  Confidence: {r.get('confidence', 0):.2f}")
                print(f"  Method: {r.get('method', 'unknown')}")
            else:
                print(f"  Error: {result['error']}")
            print(f"  Processing time: {result['processing_time']:.2f}s")
    else:
        print(f"Sample video not found at: {sample_video}")
        print("Available models:")
        for name, desc in get_available_models().items():
            print(f"- {name}: {desc}")
