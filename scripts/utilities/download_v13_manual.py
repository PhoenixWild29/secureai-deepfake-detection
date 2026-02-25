#!/usr/bin/env python3
"""
Manually download V13 models with visible progress and error handling
"""
import os
import sys
import time
import logging

os.environ['CUDA_VISIBLE_DEVICES'] = ''

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("=" * 70)
print("📥 Manual V13 Model Download")
print("=" * 70)
print()

try:
    from huggingface_hub import hf_hub_download
    from safetensors.torch import load_file
    import timm
    import torch
except ImportError as e:
    print(f"❌ Missing required package: {e}")
    print("   Install with: pip install huggingface-hub safetensors timm")
    sys.exit(1)

model_name = "ash12321/deepfake-detector-v13"
models = [
    {'file': 'model_1.safetensors', 'name': 'ConvNeXt-Large'},
    {'file': 'model_2.safetensors', 'name': 'ViT-Large'},
    {'file': 'model_3.safetensors', 'name': 'Swin-Large'},
]

print(f"Downloading from: {model_name}")
print(f"Total files: {len(models)}")
print(f"Estimated size: ~2.1GB")
print()
print("Starting download...")
print()

downloaded = []
failed = []

for i, model_info in enumerate(models, 1):
    file = model_info['file']
    name = model_info['name']
    
    print(f"[{i}/{len(models)}] Downloading {name} ({file})...")
    print(f"   File size: ~700MB")
    print(f"   Estimated time: 2-5 minutes")
    
    start_time = time.time()
    
    try:
        print(f"   Connecting to Hugging Face...")
        path = hf_hub_download(
            repo_id=model_name,
            filename=file,
            cache_dir=None,
            local_files_only=False
        )
        
        elapsed = time.time() - start_time
        
        # Verify file
        if os.path.exists(path):
            size = os.path.getsize(path) / (1024 * 1024)  # MB
            print(f"   ✅ Downloaded: {size:.1f}MB in {elapsed:.1f} seconds")
            print(f"   Location: {path}")
            downloaded.append((file, path, size))
        else:
            raise RuntimeError(f"File not found after download: {path}")
            
    except KeyboardInterrupt:
        print()
        print("   ⚠️  Download interrupted by user")
        print("   Files downloaded so far are cached")
        break
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"   ❌ Failed after {elapsed:.1f} seconds: {e}")
        failed.append((file, str(e)))
        import traceback
        traceback.print_exc()
    
    print()

# Summary
print("=" * 70)
print("📊 Download Summary")
print("=" * 70)
print(f"Downloaded: {len(downloaded)}/{len(models)}")
print()

if downloaded:
    print("✅ Successfully downloaded:")
    for file, path, size in downloaded:
        print(f"   - {file} ({size:.1f}MB)")
    print()

if failed:
    print("❌ Failed:")
    for file, error in failed:
        print(f"   - {file}: {error}")
    print()

if len(downloaded) == len(models):
    print("🎉 All models downloaded successfully!")
    print("   V13 should now work. Test with:")
    print("   python3 -c 'from ai_model.deepfake_detector_v13 import get_deepfake_detector_v13; v13 = get_deepfake_detector_v13(); print(\"✅ V13 loaded!\" if v13 and v13.model_loaded else \"❌ V13 failed\")'")
elif len(downloaded) > 0:
    print("⚠️  Partial download. Re-run this script to download remaining files.")
    print("   Already downloaded files will be skipped (cached).")
else:
    print("❌ No files downloaded. Check internet connection and Hugging Face access.")
