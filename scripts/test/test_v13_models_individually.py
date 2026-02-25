#!/usr/bin/env python3
"""
Test each V13 model individually to find which one is causing the hang
"""
import os
import sys
import logging
import time

os.environ['CUDA_VISIBLE_DEVICES'] = ''

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("=" * 70)
print("🧪 Testing V13 Models Individually")
print("=" * 70)
print()

try:
    import timm
    from safetensors.torch import load_file
    from huggingface_hub import hf_hub_download
    from ai_model.deepfake_detector_v13 import DeepfakeDetector
    
    model_configs = [
        {
            'backbone': 'convnext_large.fb_in22k_ft_in1k',
            'file': 'model_1.safetensors',
            'name': 'ConvNeXt-Large'
        },
        {
            'backbone': 'vit_large_patch16_224',
            'file': 'model_2.safetensors',
            'name': 'ViT-Large'
        },
        {
            'backbone': 'swin_large_patch4_window7_224',
            'file': 'model_3.safetensors',
            'name': 'Swin-Large'
        }
    ]
    
    model_name = "ash12321/deepfake-detector-v13"
    
    for i, config in enumerate(model_configs, 1):
        print(f"[{i}/3] Testing {config['name']} ({config['backbone']})...")
        print("-" * 70)
        
        try:
            # Test 1: Check if backbone exists
            print("   Step 1: Checking if backbone exists in timm...")
            available = timm.list_models('*' + config['backbone'].split('.')[0] + '*', pretrained=False)
            if available:
                print(f"   ✅ Found {len(available)} similar models")
                if config['backbone'] in available:
                    print(f"   ✅ Exact match found: {config['backbone']}")
                else:
                    print(f"   ⚠️  Exact match not found, closest: {available[:3]}")
            else:
                print(f"   ❌ No similar models found")
            
            # Test 2: Try creating model
            print(f"   Step 2: Creating model architecture...")
            start = time.time()
            try:
                model = DeepfakeDetector(config['backbone'], dropout=0.3)
                elapsed = time.time() - start
                print(f"   ✅ Model created in {elapsed:.1f} seconds")
            except Exception as e:
                elapsed = time.time() - start
                print(f"   ❌ Model creation failed after {elapsed:.1f} seconds: {e}")
                import traceback
                traceback.print_exc()
                continue
            
            # Test 3: Try loading safetensors
            print(f"   Step 3: Loading safetensors file...")
            try:
                safetensors_path = hf_hub_download(
                    repo_id=model_name,
                    filename=config['file'],
                    cache_dir=None,
                    local_files_only=True  # Use cached file
                )
                print(f"   ✅ File found: {safetensors_path}")
                
                start = time.time()
                state_dict = load_file(safetensors_path)
                elapsed = time.time() - start
                print(f"   ✅ Safetensors loaded in {elapsed:.1f} seconds ({len(state_dict)} keys)")
                
                # Test 4: Try loading state dict
                print(f"   Step 4: Loading state dict into model...")
                start = time.time()
                model.load_state_dict(state_dict)
                elapsed = time.time() - start
                print(f"   ✅ State dict loaded in {elapsed:.1f} seconds")
                
                print(f"   ✅ {config['name']} fully loaded!")
                
            except Exception as e:
                print(f"   ❌ Failed to load weights: {e}")
                import traceback
                traceback.print_exc()
                continue
            
        except Exception as e:
            print(f"   ❌ Error testing {config['name']}: {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print("=" * 70)
    print("✅ Individual model tests complete!")
    print("=" * 70)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
