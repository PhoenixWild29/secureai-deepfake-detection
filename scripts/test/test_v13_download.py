#!/usr/bin/env python3
"""
Test V13 model download with progress tracking
"""
import os
import sys
import logging

os.environ['CUDA_VISIBLE_DEVICES'] = ''

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("=" * 70)
print("🧪 Testing V13 Model Download")
print("=" * 70)
print()

# Check required packages
print("1️⃣  Checking required packages...")
required = ['timm', 'safetensors', 'huggingface_hub']
missing = []

for pkg in required:
    try:
        __import__(pkg)
        print(f"   ✅ {pkg}")
    except ImportError:
        print(f"   ❌ {pkg} - MISSING")
        missing.append(pkg)

if missing:
    print()
    print(f"⚠️  Missing packages: {', '.join(missing)}")
    print(f"   Install with: pip install {' '.join(missing)}")
    sys.exit(1)

print()
print("2️⃣  Testing Hugging Face access...")
try:
    from huggingface_hub import model_info
    info = model_info("ash12321/deepfake-detector-v13")
    print(f"   ✅ Model exists on Hugging Face")
    print(f"      ID: {info.id}")
    print(f"      Downloads: {info.downloads}")
except Exception as e:
    print(f"   ❌ Cannot access model: {e}")
    print("      Check internet connection and Hugging Face access")
    sys.exit(1)

print()
print("3️⃣  Testing V13 model loading...")
print("   This will download ~2-3GB of model files")
print("   It may take 5-10 minutes depending on your connection")
print()

try:
    from ai_model.deepfake_detector_v13 import get_deepfake_detector_v13
    
    print("   Starting download...")
    v13 = get_deepfake_detector_v13()
    
    if v13 and v13.model_loaded:
        print()
        print("   ✅ V13 loaded successfully!")
        print(f"      Models loaded: {len(v13.models)}/3")
        num_params = sum(sum(p.numel() for p in m.parameters()) for m in v13.models)
        print(f"      Total parameters: {num_params:,} ({num_params/1e6:.1f}M)")
    else:
        print()
        print("   ❌ V13 not loaded")
        sys.exit(1)
        
except KeyboardInterrupt:
    print()
    print("   ⚠️  Download interrupted by user")
    print("   You can resume later - files are cached")
    sys.exit(1)
except Exception as e:
    print()
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 70)
print("✅ V13 Model Test Complete!")
print("=" * 70)
