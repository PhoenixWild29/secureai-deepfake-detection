#!/usr/bin/env python3
"""
Check V13 cache directory location and files
"""
import os
import sys

print("=" * 70)
print("🔍 Checking V13 Cache Directory")
print("=" * 70)
print()

# Try to find cache directory
try:
    from huggingface_hub import hf_hub_download
    import tempfile
    
    # Try to download a small file to find cache location
    print("Finding Hugging Face cache directory...")
    
    # Get cache directory
    cache_dir = os.path.expanduser("~/.cache/huggingface")
    print(f"Default cache: {cache_dir}")
    print(f"Exists: {os.path.exists(cache_dir)}")
    
    # Check as app user (in Docker)
    app_cache = "/home/app/.cache/huggingface"
    print(f"App cache: {app_cache}")
    print(f"Exists: {os.path.exists(app_cache)}")
    
    # Check model-specific cache
    model_cache = os.path.join(cache_dir, "hub", "models--ash12321--deepfake-detector-v13")
    print(f"Model cache: {model_cache}")
    print(f"Exists: {os.path.exists(model_cache)}")
    
    if os.path.exists(model_cache):
        print()
        print("Files in model cache:")
        for root, dirs, files in os.walk(model_cache):
            level = root.replace(model_cache, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    size = os.path.getsize(filepath) / (1024 * 1024)  # MB
                    print(f"{subindent}{file} ({size:.1f}MB)")
                except:
                    print(f"{subindent}{file}")
    
    # Check app user cache
    app_model_cache = os.path.join(app_cache, "hub", "models--ash12321--deepfake-detector-v13")
    print()
    print(f"App model cache: {app_model_cache}")
    print(f"Exists: {os.path.exists(app_model_cache)}")
    
    if os.path.exists(app_model_cache):
        print()
        print("Files in app model cache:")
        for root, dirs, files in os.walk(app_model_cache):
            level = root.replace(app_model_cache, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    size = os.path.getsize(filepath) / (1024 * 1024)  # MB
                    print(f"{subindent}{file} ({size:.1f}MB)")
                except:
                    print(f"{subindent}{file}")
    
    # Check for safetensors files
    print()
    print("Searching for .safetensors files...")
    safetensors_found = []
    for root, dirs, files in os.walk(cache_dir if os.path.exists(cache_dir) else app_cache):
        for file in files:
            if file.endswith('.safetensors'):
                filepath = os.path.join(root, file)
                try:
                    size = os.path.getsize(filepath) / (1024 * 1024)  # MB
                    safetensors_found.append((filepath, size))
                except:
                    safetensors_found.append((filepath, 0))
    
    if safetensors_found:
        print(f"Found {len(safetensors_found)} safetensors files:")
        for path, size in safetensors_found:
            print(f"  {path} ({size:.1f}MB)")
    else:
        print("  No safetensors files found")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
