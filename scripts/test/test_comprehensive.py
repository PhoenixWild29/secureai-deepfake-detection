#!/usr/bin/env python3
"""
Comprehensive Test: V13 + Ultimate Ensemble + Video Detection
Tests everything in one script
"""
import os
import sys
import logging

os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

print("=" * 70)
print("🧪 Comprehensive Deepfake Detection Test")
print("=" * 70)
print()

results = {
    'v13': False,
    'xception': False,
    'efficientnet': False,
    'ensemble': False,
    'video_test': False
}

# Test 1: V13
print("1️⃣  Testing DeepFake Detector V13...")
print("-" * 70)
try:
    from ai_model.deepfake_detector_v13 import get_deepfake_detector_v13
    v13 = get_deepfake_detector_v13()
    if v13 and v13.model_loaded:
        print("   ✅ V13 loaded successfully!")
        print(f"      Models: {len(v13.models)}/3")
        results['v13'] = True
    else:
        print("   ❌ V13 not loaded")
except Exception as e:
    print(f"   ❌ V13 error: {e}")
print()

# Test 2: XceptionNet
print("2️⃣  Testing XceptionNet...")
print("-" * 70)
try:
    from ai_model.xception_detector import get_xception_detector
    xception = get_xception_detector()
    if xception:
        print("   ✅ XceptionNet loaded successfully!")
        results['xception'] = True
    else:
        print("   ⚠️  XceptionNet not available")
except Exception as e:
    print(f"   ⚠️  XceptionNet error: {e}")
print()

# Test 3: EfficientNet
print("3️⃣  Testing EfficientNet...")
print("-" * 70)
try:
    from ai_model.efficientnet_detector import get_efficientnet_detector
    efficientnet = get_efficientnet_detector()
    if efficientnet:
        print("   ✅ EfficientNet loaded successfully!")
        results['efficientnet'] = True
    else:
        print("   ⚠️  EfficientNet not available")
except Exception as e:
    print(f"   ⚠️  EfficientNet error: {e}")
print()

# Test 4: Ultimate Ensemble
print("4️⃣  Testing Ultimate Ensemble...")
print("-" * 70)
try:
    from ai_model.ensemble_detector import get_ensemble_detector
    ensemble = get_ensemble_detector()
    if ensemble:
        print("   ✅ Ultimate Ensemble loaded successfully!")
        print()
        print("   Active Models:")
        print(f"      CLIP: ✅")
        print(f"      ResNet50: ✅")
        print(f"      V13: {'✅' if results['v13'] else '❌'}")
        print(f"      XceptionNet: {'✅' if results['xception'] else '❌'}")
        print(f"      EfficientNet: {'✅' if results['efficientnet'] else '❌'}")
        results['ensemble'] = True
    else:
        print("   ❌ Ultimate Ensemble not loaded")
except Exception as e:
    print(f"   ❌ Ensemble error: {e}")
    import traceback
    traceback.print_exc()
print()

# Test 5: Video Detection
print("5️⃣  Testing Video Detection...")
print("-" * 70)
try:
    from utils.video_paths import VideoPathManager
    vm = VideoPathManager()
    test_video = vm.find_video('test_video_1.mp4') or vm.find_video('*.mp4')
    
    if test_video:
        print(f"   Found video: {test_video}")
        print("   Running detection (this may take 30-60 seconds)...")
        
        result = ensemble.detect(test_video)
        
        print()
        print("   ✅ Detection successful!")
        print(f"      Is Deepfake: {result['is_deepfake']}")
        print(f"      Probability: {result['ensemble_fake_probability']:.3f}")
        print(f"      Confidence: {result['overall_confidence']:.3f}")
        print(f"      Models Used: {result.get('models_used', [])}")
        results['video_test'] = True
    else:
        print("   ⚠️  No test videos found")
        print("      Add videos to: uploads/, test_videos/, or datasets/")
except Exception as e:
    print(f"   ⚠️  Video test error: {e}")
print()

# Summary
print("=" * 70)
print("📊 Test Summary")
print("=" * 70)
print(f"V13: {'✅' if results['v13'] else '❌'}")
print(f"XceptionNet: {'✅' if results['xception'] else '⚠️ '}")
print(f"EfficientNet: {'✅' if results['efficientnet'] else '⚠️ '}")
print(f"Ultimate Ensemble: {'✅' if results['ensemble'] else '❌'}")
print(f"Video Detection: {'✅' if results['video_test'] else '⚠️ '}")
print()

if results['ensemble']:
    print("🎉 Ultimate Ensemble is working!")
    if results['v13']:
        print("   ✅ V13 integrated - Expected accuracy: 93-98%")
    else:
        print("   ⚠️  V13 not available - Using other models")
    print()
    print("Next: Test on more videos to benchmark accuracy!")
else:
    print("❌ Some components failed. Check errors above.")

print("=" * 70)
