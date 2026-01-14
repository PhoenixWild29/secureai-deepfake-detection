#!/usr/bin/env python3
"""
Quick V13 check - just see if models are in memory without loading
"""
import os
import sys

os.environ['CUDA_VISIBLE_DEVICES'] = ''

print("=" * 70)
print("🔍 Quick V13 Status Check")
print("=" * 70)
print()

# Check if V13 module exists
try:
    print("1. Checking if V13 module exists...")
    import ai_model.deepfake_detector_v13 as v13_module
    print("   ✅ V13 module found")
except ImportError as e:
    print(f"   ❌ V13 module not found: {e}")
    sys.exit(1)

# Check if models are already loaded (checking global state)
print()
print("2. Checking for loaded models...")
try:
    # Try to access any cached instances
    if hasattr(v13_module, '_v13_instance'):
        v13 = v13_module._v13_instance
        if v13:
            print(f"   ✅ Found V13 instance")
            print(f"      Models: {len(v13.models) if v13.models else 0}/3")
            if v13.model_loaded:
                print("      Status: Loaded")
            else:
                print("      Status: Not fully loaded")
        else:
            print("   ⚠️  V13 instance is None")
    else:
        print("   ⚠️  No cached V13 instance found")
        print("      V13 needs to be initialized")
except Exception as e:
    print(f"   ⚠️  Could not check instance: {e}")

# Check Hugging Face cache
print()
print("3. Checking Hugging Face cache...")
cache_path = "/home/app/.cache/huggingface/hub/models--ash12321--deepfake-detector-v13"
if os.path.exists(cache_path):
    print(f"   ✅ Cache directory exists: {cache_path}")
    
    # Check for model files
    import glob
    safetensors = glob.glob(f"{cache_path}/**/model_*.safetensors", recursive=True)
    if safetensors:
        print(f"   ✅ Found {len(safetensors)} model file(s):")
        for f in safetensors:
            size_mb = os.path.getsize(f) / (1024 * 1024)
            print(f"      - {os.path.basename(f)} ({size_mb:.1f} MB)")
    else:
        print("   ⚠️  No model files found in cache")
else:
    print(f"   ⚠️  Cache directory not found: {cache_path}")

print()
print("=" * 70)
print("💡 To load V13, run: python3 test_v13_simple.py")
print("=" * 70)
