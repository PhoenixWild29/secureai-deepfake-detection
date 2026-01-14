#!/usr/bin/env python3
"""
Simple test script to verify the deepfake detection system is working
Windows-compatible version without Unicode characters
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_dependencies():
    """Test if all required dependencies are installed"""
    print("Testing dependencies...")
    
    try:
        import torch
        print(f"[OK] PyTorch {torch.__version__}")
    except ImportError as e:
        print(f"[FAIL] PyTorch not found: {e}")
        return False
    
    try:
        import cv2
        print(f"[OK] OpenCV {cv2.__version__}")
    except ImportError as e:
        print(f"[FAIL] OpenCV not found: {e}")
        return False
    
    try:
        import flask
        print(f"[OK] Flask {flask.__version__}")
    except ImportError as e:
        print(f"[FAIL] Flask not found: {e}")
        return False
    
    try:
        import numpy
        print(f"[OK] NumPy {numpy.__version__}")
    except ImportError as e:
        print(f"[FAIL] NumPy not found: {e}")
        return False
    
    return True

def test_models():
    """Test if trained models are available"""
    print("\nTesting trained models...")
    
    models = [
        ("ai_model/resnet_resnet50_best.pth", "ResNet50"),
        ("ai_model/deepfake_classifier_best.pth", "CNN Classifier"),
        ("yolov8n.pt", "YOLO")
    ]
    
    all_found = True
    for model_path, name in models:
        if os.path.exists(model_path):
            size_mb = os.path.getsize(model_path) / (1024 * 1024)
            print(f"[OK] {name}: {model_path} ({size_mb:.1f} MB)")
        else:
            print(f"[FAIL] {name}: {model_path} not found")
            all_found = False
    
    return all_found

def test_detection():
    """Test if detection system works"""
    print("\nTesting detection system...")
    
    try:
        from ai_model.detect import detect_fake
        print("[OK] Detection module imported successfully")
        
        # Test with sample video
        if os.path.exists('sample_video.mp4'):
            print("[OK] Sample video found")
            result = detect_fake('sample_video.mp4', model_type='resnet')
            print("[OK] Detection successful!")
            print(f"  Result: {'FAKE' if result.get('is_fake') else 'AUTHENTIC'}")
            print(f"  Confidence: {result.get('confidence', 0)*100:.1f}%")
            print(f"  Processing time: {result.get('processing_time', 0):.2f}s")
            return True
        else:
            print("[FAIL] Sample video not found")
            return False
            
    except Exception as e:
        print(f"[FAIL] Detection test failed: {e}")
        return False

def test_flask_app():
    """Test if Flask app can be imported"""
    print("\nTesting Flask app...")
    
    try:
        from api import app
        print("[OK] Flask app imported successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Flask app import failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("SecureAI DeepFake Detection System - Verification")
    print("=" * 60)
    
    tests = [
        ("Dependencies", test_dependencies),
        ("Trained Models", test_models),
        ("Detection System", test_detection),
        ("Flask App", test_flask_app)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"[FAIL] {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{test_name:20} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED! System is ready to use!")
        print("\nNext steps:")
        print("1. Run: python api.py")
        print("2. Open browser to: http://localhost:5000")
        print("3. Upload a video and start detecting!")
    else:
        print("Some tests failed. Please check the errors above.")
    print("=" * 60)

if __name__ == '__main__':
    main()
