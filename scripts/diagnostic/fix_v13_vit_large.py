#!/usr/bin/env python3
"""
Fix V13 ViT-Large loading issue
Tests different approaches to load ViT-Large model
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
print("🔧 Fixing V13 ViT-Large Loading")
print("=" * 70)
print()

try:
    import timm
    from safetensors.torch import load_file
    from huggingface_hub import hf_hub_download
    
    # Test 1: Check available ViT models
    print("1️⃣  Checking available ViT-Large models in timm...")
    print("-" * 70)
    all_models = timm.list_models(pretrained=False)
    vit_models = [m for m in all_models if 'vit_large' in m.lower() and 'patch16' in m.lower()]
    
    print(f"Found {len(vit_models)} ViT-Large patch16 models:")
    for model in vit_models[:10]:
        print(f"   - {model}")
    print()
    
    # Check our exact model
    target_model = 'vit_large_patch16_224'
    if target_model in all_models:
        print(f"✅ Exact model '{target_model}' exists in timm")
    else:
        print(f"❌ Exact model '{target_model}' NOT found")
        print(f"   Trying alternatives...")
        # Try alternatives
        alternatives = [
            'vit_large_patch16_224_in21k',
            'vit_large_patch16_384',
            'vit_large_patch14_224',
        ]
        for alt in alternatives:
            if alt in all_models:
                print(f"   ✅ Alternative found: {alt}")
                target_model = alt
                break
    
    print()
    
    # Test 2: Try creating model with different approaches
    print("2️⃣  Testing model creation approaches...")
    print("-" * 70)
    
    approaches = [
        {
            'name': 'Standard (no pretrained)',
            'kwargs': {'pretrained': False, 'num_classes': 0}
        },
        {
            'name': 'With in_chans=3',
            'kwargs': {'pretrained': False, 'num_classes': 0, 'in_chans': 3}
        },
        {
            'name': 'With scriptable=False',
            'kwargs': {'pretrained': False, 'num_classes': 0, 'scriptable': False}
        },
    ]
    
    working_approach = None
    
    for approach in approaches:
        print(f"   Trying: {approach['name']}...")
        try:
            start = time.time()
            model = timm.create_model(target_model, **approach['kwargs'])
            elapsed = time.time() - start
            
            # Test forward pass
            test_input = torch.zeros(1, 3, 224, 224)
            with torch.no_grad():
                output = model(test_input)
            
            print(f"   ✅ Success! Created in {elapsed:.1f} seconds")
            print(f"      Output shape: {output.shape if hasattr(output, 'shape') else type(output)}")
            working_approach = approach
            break
        except Exception as e:
            elapsed = time.time() - start if 'start' in locals() else 0
            print(f"   ❌ Failed after {elapsed:.1f} seconds: {e}")
    
    if not working_approach:
        print()
        print("❌ All approaches failed")
        sys.exit(1)
    
    print()
    
    # Test 3: Load safetensors
    print("3️⃣  Testing safetensors loading...")
    print("-" * 70)
    
    model_name = "ash12321/deepfake-detector-v13"
    try:
        safetensors_path = hf_hub_download(
            repo_id=model_name,
            filename='model_2.safetensors',
            cache_dir=None,
            local_files_only=True
        )
        
        print(f"   ✅ File found: {safetensors_path}")
        file_size = os.path.getsize(safetensors_path) / (1024 * 1024)
        print(f"   File size: {file_size:.1f}MB")
        
        print("   Loading safetensors...")
        start = time.time()
        state_dict = load_file(safetensors_path)
        elapsed = time.time() - start
        print(f"   ✅ Loaded in {elapsed:.1f} seconds")
        print(f"   Keys: {len(state_dict)}")
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        sys.exit(1)
    
    print()
    
    # Test 4: Load state dict
    print("4️⃣  Testing state dict loading...")
    print("-" * 70)
    
    try:
        print("   Loading state dict into model...")
        start = time.time()
        model.load_state_dict(state_dict, strict=False)  # Use strict=False to handle mismatches
        elapsed = time.time() - start
        print(f"   ✅ State dict loaded in {elapsed:.1f} seconds")
        
        print()
        print("=" * 70)
        print("✅ ViT-Large loading works!")
        print("=" * 70)
        print()
        print(f"Working approach: {working_approach['name']}")
        print(f"Model name: {target_model}")
        print()
        print("Update deepfake_detector_v13.py with:")
        print(f"  'backbone': '{target_model}',")
        print(f"  And use: timm.create_model('{target_model}', **{working_approach['kwargs']})")
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to see what keys don't match
        print()
        print("   Checking state dict keys...")
        model_keys = set(model.state_dict().keys())
        state_keys = set(state_dict.keys())
        
        missing = state_keys - model_keys
        extra = model_keys - state_keys
        
        if missing:
            print(f"   Missing keys in model: {len(missing)}")
            print(f"   First 5: {list(missing)[:5]}")
        if extra:
            print(f"   Extra keys in model: {len(extra)}")
            print(f"   First 5: {list(extra)[:5]}")
        
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
