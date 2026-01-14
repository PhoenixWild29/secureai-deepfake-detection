#!/usr/bin/env python3
"""
Test ConvNeXt-Large loading individually to diagnose the hang
"""
import os
import sys
import signal
import logging

os.environ['CUDA_VISIBLE_DEVICES'] = ''

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Timeout handler
def timeout_handler(signum, frame):
    print("\n⚠️  ConvNeXt-Large creation timed out after 3 minutes")
    print("   This confirms the hang issue")
    sys.exit(1)

# Set 3 minute timeout
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(180)  # 3 minutes

try:
    print("=" * 70)
    print("🧪 Testing ConvNeXt-Large Creation")
    print("=" * 70)
    print()
    
    import torch
    import timm
    from safetensors.torch import load_file
    
    print("1. Checking if timm is available...")
    print(f"   ✅ timm version: {timm.__version__}")
    print()
    
    print("2. Checking if ConvNeXt-Large backbone exists...")
    backbones = timm.list_models('convnext*')
    convnext_large = [b for b in backbones if 'convnext_large' in b]
    print(f"   Found {len(convnext_large)} ConvNeXt-Large variants:")
    for b in convnext_large[:5]:  # Show first 5
        print(f"      - {b}")
    print()
    
    print("3. Testing ConvNeXt-Large creation...")
    print("   This is where it hangs...")
    
    # Try creating the model
    model = timm.create_model('convnext_large', pretrained=False, num_classes=0)
    signal.alarm(0)  # Cancel timeout
    
    print("   ✅ ConvNeXt-Large created successfully!")
    print(f"   Model type: {type(model)}")
    print()
    
    print("4. Testing with safetensors loading...")
    cache_path = "/home/app/.cache/huggingface/hub/models--ash12321--deepfake-detector-v13"
    model_file = f"{cache_path}/snapshots/*/model_1.safetensors"
    
    import glob
    files = glob.glob(model_file)
    if files:
        print(f"   Found model file: {files[0]}")
        print("   Loading weights...")
        state_dict = load_file(files[0])
        print(f"   ✅ Loaded {len(state_dict)} keys")
        print("   Loading into model...")
        model.load_state_dict(state_dict, strict=False)
        print("   ✅ Weights loaded!")
    else:
        print("   ⚠️  Model file not found")
    
    print()
    print("🎉 ConvNeXt-Large test completed successfully!")
    
except TimeoutError:
    print("\n❌ ConvNeXt-Large creation timed out - this is the hang issue")
    sys.exit(1)
except Exception as e:
    signal.alarm(0)
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
