#!/usr/bin/env python3
"""
Diagnose ViT-Large hanging issue
Tests different approaches and checks system resources
"""
import os
import sys
import time
import logging
import torch
import psutil

os.environ['CUDA_VISIBLE_DEVICES'] = ''

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("=" * 70)
print("🔍 Diagnosing ViT-Large Hanging Issue")
print("=" * 70)
print()

# Check system resources
print("1️⃣  System Resources:")
print("-" * 70)
mem = psutil.virtual_memory()
print(f"   Total Memory: {mem.total / (1024**3):.1f} GB")
print(f"   Available Memory: {mem.available / (1024**3):.1f} GB")
print(f"   Used Memory: {mem.used / (1024**3):.1f} GB")
print(f"   Memory Percent: {mem.percent}%")
print()

if mem.available < 2 * 1024**3:  # Less than 2GB available
    print("   ⚠️  WARNING: Low memory! ViT-Large needs ~2-3GB")
    print("   This might cause swapping and hanging")
print()

try:
    import timm
    print(f"2️⃣  timm Version: {timm.__version__}")
    print()
    
    # Check available ViT models
    print("3️⃣  Available ViT-Large Models:")
    print("-" * 70)
    all_models = timm.list_models(pretrained=False)
    vit_models = [m for m in all_models if 'vit_large' in m.lower() and 'patch16' in m.lower()]
    
    print(f"   Found {len(vit_models)} ViT-Large patch16 models:")
    for model in vit_models[:10]:
        print(f"      - {model}")
    print()
    
    target_model = 'vit_large_patch16_224'
    if target_model not in all_models:
        print(f"   ❌ '{target_model}' not found!")
        print(f"   Trying alternatives...")
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
    else:
        print(f"   ✅ '{target_model}' exists")
    print()
    
    # Test different creation approaches
    print("4️⃣  Testing Model Creation Approaches:")
    print("-" * 70)
    
    approaches = [
        {
            'name': 'Standard (no pretrained)',
            'kwargs': {'pretrained': False, 'num_classes': 0, 'in_chans': 3}
        },
        {
            'name': 'With scriptable=True',
            'kwargs': {'pretrained': False, 'num_classes': 0, 'in_chans': 3, 'scriptable': True}
        },
        {
            'name': 'With exportable=True',
            'kwargs': {'pretrained': False, 'num_classes': 0, 'in_chans': 3, 'exportable': True}
        },
        {
            'name': 'With drop_rate=0.0',
            'kwargs': {'pretrained': False, 'num_classes': 0, 'in_chans': 3, 'drop_rate': 0.0}
        },
    ]
    
    for i, approach in enumerate(approaches, 1):
        print(f"   Approach {i}: {approach['name']}")
        try:
            start = time.time()
            print(f"      Creating model with {approach['kwargs']}...")
            
            # Set a 2-minute timeout per approach
            model = None
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Model creation timed out")
            
            # Use alarm for timeout (Unix only)
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(120)  # 2 minutes
            
            try:
                model = timm.create_model(target_model, **approach['kwargs'])
                elapsed = time.time() - start
                print(f"      ✅ SUCCESS! Created in {elapsed:.1f} seconds")
                del model  # Free memory
                torch.cuda.empty_cache() if torch.cuda.is_available() else None
                break  # Found working approach!
            except TimeoutError:
                elapsed = time.time() - start
                print(f"      ❌ TIMEOUT after {elapsed:.1f} seconds")
            except Exception as e:
                elapsed = time.time() - start
                print(f"      ❌ FAILED after {elapsed:.1f} seconds: {e}")
            finally:
                if hasattr(signal, 'SIGALRM'):
                    signal.alarm(0)  # Cancel alarm
                    
        except Exception as e:
            print(f"      ❌ ERROR: {e}")
        
        print()
        
        # Check memory after each attempt
        mem = psutil.virtual_memory()
        if mem.available < 1 * 1024**3:  # Less than 1GB
            print(f"      ⚠️  Low memory: {mem.available / (1024**3):.1f} GB available")
            print(f"      Consider freeing memory before next attempt")
        print()
    
    print("5️⃣  Summary:")
    print("-" * 70)
    print("   If all approaches timed out, ViT-Large is likely hanging in timm")
    print("   This is a known issue with large ViT models in some timm versions")
    print()
    print("   Possible solutions:")
    print("   1. Update timm: pip install --upgrade timm")
    print("   2. Try a different ViT variant (e.g., vit_large_patch14_224)")
    print("   3. Use a smaller model or different architecture")
    print("   4. Increase system memory")
    print()
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
