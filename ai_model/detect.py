#!/usr/bin/env python3
"""
SecureAI DeepFake Detection
Main detection module with multiple model options
"""
import os
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

def detect_fake(video_path: str, model_type: str = 'resnet') -> Dict[str, Any]:
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
        if model_type == 'enhanced':
            # Use the new ensemble SOTA detector (CLIP + LAA-Net)
            result = detect_fake_enhanced(video_path)

        elif model_type == 'ensemble' or model_type == 'full_ensemble':
            # Use full ensemble: CLIP + ResNet50 + LAA-Net
            if detect_fake_ensemble:
                try:
                    result = detect_fake_ensemble(video_path)
                    # Map ensemble results to expected format
                    if 'ensemble_fake_probability' in result:
                        result['is_fake'] = result.get('is_deepfake', result['ensemble_fake_probability'] > 0.5)
                        result['confidence'] = result['ensemble_fake_probability']
                        result['authenticity_score'] = 1 - result['ensemble_fake_probability']
                except Exception as e:
                    print(f"Full ensemble failed: {e}, falling back to enhanced")
                    result = detect_fake_enhanced(video_path)
            else:
                # Fallback to enhanced if ensemble not available
                result = detect_fake_enhanced(video_path)

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
    models = {
        'enhanced': 'Ensemble SOTA detector (CLIP + LAA-Net)',
        'ensemble': 'Full ensemble (CLIP + ResNet50 + LAA-Net) - Recommended',
        'full_ensemble': 'Full ensemble (CLIP + ResNet50 + LAA-Net) - Recommended',
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
                print(".2%")
                print(".2f")
                print(f"  Method: {r.get('method', 'unknown')}")
            else:
                print(f"  Error: {result['error']}")
            print(".2f")
    else:
        print(f"Sample video not found at: {sample_video}")
        print("Available models:")
        for name, desc in get_available_models().items():
            print(f"- {name}: {desc}")