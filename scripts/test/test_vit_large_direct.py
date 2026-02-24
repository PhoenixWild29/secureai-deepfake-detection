#!/usr/bin/env python3
"""
Test ViT-Large creation directly to find the hang
"""
import os
import sys
import time
import logging
import torch

os.environ['CUDA_VISIBLE_DEVICES'] = ''

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("=" * 70)
print("🔧 Testing ViT-Large Creation Directly")
print("=" * 70)
print()

try:
    import timm
    from ai_model.deepfake_detector_v13 import DeepfakeDetector
    
    backbone = 'vit_large_patch16_224'
    
    print(f"Testing backbone: {backbone}")
    print()
    
    # Test 1: Check if model exists
    print("1️⃣  Checking if model exists in timm...")
    all_models = timm.list_models(pretrained=False)
    if backbone in all_models:
        print(f"   ✅ Model '{backbone}' exists in timm")
    else:
        print(f"   ❌ Model '{backbone}' NOT found")
        sys.exit(1)
    print()
    
    # Test 2: Try creating with timm directly (simpler)
    print("2️⃣  Testing timm.create_model directly...")
    print("   (This is what DeepfakeDetector uses internally)")
    try:
        start = time.time()
        print("   Creating model...")
        backbone_model = timm.create_model(backbone, pretrained=False, num_classes=0, in_chans=3)
        elapsed = time.time() - start
        print(f"   ✅ Created in {elapsed:.1f} seconds")
        print(f"   Model type: {type(backbone_model)}")
        
        # Test forward pass
        print("   Testing forward pass...")
        test_input = torch.zeros(1, 3, 224, 224)
        with torch.no_grad():
            output = backbone_model(test_input)
        print(f"   ✅ Forward pass works")
        print(f"   Output shape: {output.shape if hasattr(output, 'shape') else type(output)}")
        
    except Exception as e:
        elapsed = time.time() - start if 'start' in locals() else 0
        print(f"   ❌ Failed after {elapsed:.1f} seconds: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    print()
    
    # Test 3: Try creating DeepfakeDetector
    print("3️⃣  Testing DeepfakeDetector creation...")
    try:
        start = time.time()
        print("   Creating DeepfakeDetector...")
        detector = DeepfakeDetector(backbone, dropout=0.3)
        elapsed = time.time() - start
        print(f"   ✅ Created in {elapsed:.1f} seconds")
        
        # Test forward pass
        print("   Testing forward pass...")
        test_input = torch.zeros(1, 3, 224, 224)
        with torch.no_grad():
            output = detector(test_input)
        print(f"   ✅ Forward pass works")
        print(f"   Output shape: {output.shape if hasattr(output, 'shape') else type(output)}")
        
    except Exception as e:
        elapsed = time.time() - start if 'start' in locals() else 0
        print(f"   ❌ Failed after {elapsed:.1f} seconds: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    print()
    
    # Test 4: Check memory
    print("4️⃣  Checking memory usage...")
    try:
        import psutil
        process = psutil.Process()
        mem_info = process.memory_info()
        print(f"   Memory used: {mem_info.rss / (1024*1024):.1f}MB")
        print(f"   Virtual memory: {mem_info.vms / (1024*1024):.1f}MB")
    except ImportError:
        print("   ⚠️  psutil not available (install with: pip install psutil)")
    except Exception as e:
        print(f"   ⚠️  Could not check memory: {e}")
    print()
    
    print("=" * 70)
    print("✅ ViT-Large creation test complete!")
    print("=" * 70)
    print()
    print("If this test works but V13 loading hangs, the issue is in the")
    print("threading/timeout mechanism, not the model creation itself.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
