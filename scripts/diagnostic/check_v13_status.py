#!/usr/bin/env python3
"""
Check V13 download status - simple version that works in container
"""
import os
import sys

print("=" * 70)
print("🔍 Checking V13 Download Status")
print("=" * 70)
print()

# Check if Python process is running (download might be active)
print("1️⃣  Checking if download process is running...")
try:
    import subprocess
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    python_processes = [line for line in result.stdout.split('\n') if 'python' in line.lower() and 'v13' in line.lower()]
    if python_processes:
        print("   ⚠️  Python process found (download might be active):")
        for proc in python_processes[:3]:  # Show first 3
            print(f"      {proc}")
    else:
        print("   ✅ No active download process found")
except:
    print("   ⚠️  Could not check processes")

print()

# Check cache directories
print("2️⃣  Checking cache directories...")

cache_locations = [
    "/root/.cache/huggingface",
    "/home/app/.cache/huggingface", 
    os.path.expanduser("~/.cache/huggingface"),
    "/tmp/.cache/huggingface"
]

found_files = []
for cache_dir in cache_locations:
    if os.path.exists(cache_dir):
        print(f"   ✅ Found cache: {cache_dir}")
        # Search for safetensors files
        try:
            for root, dirs, files in os.walk(cache_dir):
                for file in files:
                    if 'model_' in file and file.endswith('.safetensors'):
                        filepath = os.path.join(root, file)
                        try:
                            size = os.path.getsize(filepath) / (1024 * 1024)  # MB
                            found_files.append((filepath, size))
                            print(f"      ✅ {file} ({size:.1f}MB)")
                        except:
                            found_files.append((filepath, 0))
                            print(f"      ✅ {file}")
        except PermissionError:
            print(f"      ⚠️  Permission denied in {cache_dir}")
        except Exception as e:
            print(f"      ⚠️  Error scanning: {e}")
    else:
        print(f"   ❌ Not found: {cache_dir}")

print()

# Summary
print("3️⃣  Summary:")
if found_files:
    print(f"   ✅ Found {len(found_files)} safetensors files")
    print("   Files:")
    for path, size in found_files:
        print(f"      - {os.path.basename(path)} ({size:.1f}MB)")
    
    # Check which models we have
    has_model_1 = any('model_1' in path for path, _ in found_files)
    has_model_2 = any('model_2' in path for path, _ in found_files)
    has_model_3 = any('model_3' in path for path, _ in found_files)
    
    print()
    print("   Model files:")
    print(f"      model_1.safetensors (ConvNeXt): {'✅' if has_model_1 else '❌'}")
    print(f"      model_2.safetensors (ViT): {'✅' if has_model_2 else '❌'}")
    print(f"      model_3.safetensors (Swin): {'✅' if has_model_3 else '❌'}")
    
    if has_model_1 and has_model_2 and has_model_3:
        print()
        print("   🎉 All 3 models downloaded! V13 should work now.")
    else:
        missing = []
        if not has_model_1: missing.append("model_1")
        if not has_model_2: missing.append("model_2")
        if not has_model_3: missing.append("model_3")
        print()
        print(f"   ⚠️  Missing: {', '.join(missing)}")
        print("   Need to download missing files")
else:
    print("   ❌ No safetensors files found")
    print("   Download may have failed or not started")

print()
print("=" * 70)
