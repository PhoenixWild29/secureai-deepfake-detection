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
except ImportError:
    # Fallback for when called from root directory
    from ai_model.deepfake_classifier import DeepfakeClassifier, ResNetDeepfakeClassifier
    from ai_model.enhanced_detector import detect_fake_enhanced

def detect_fake(video_path: str, model_type: str = 'resnet') -> Dict[str, Any]:
    """
    Main detection function with multiple model options

    Args:
        video_path: Path to video file
        model_type: 'cnn', 'yolo', 'ensemble', or 'enhanced'

    Returns:
        Detection results dictionary
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    start_time = time.time()

    try:
        if model_type == 'enhanced':
            # Use the new ensemble SOTA detector
            result = detect_fake_enhanced(video_path)

        elif model_type == 'cnn':
            # Use our custom CNN classifier
            classifier = DeepfakeClassifier()
            result = classifier.predict_video(video_path)

        elif model_type == 'ensemble':
            # Use both CNN and enhanced detection
            try:
                # Try enhanced first
                result = detect_fake_enhanced(video_path)
            except Exception as e:
                print(f"Enhanced detection failed: {e}, falling back to CNN")
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
    return {
        'enhanced': 'Ensemble SOTA detector (LAA-Net + CLIP + DM-aware)',
        'cnn': 'Custom CNN classifier with YOLO face detection',
        'ensemble': 'Adaptive ensemble (enhanced with CNN fallback)',
        'resnet': 'ResNet-based deepfake classifier'
    }

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