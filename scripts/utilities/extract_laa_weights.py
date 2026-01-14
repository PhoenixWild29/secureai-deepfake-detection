#!/usr/bin/env python3
"""
Extract and verify LAA-Net pretrained weights
"""
import os
import zipfile
from pathlib import Path

def extract_and_verify():
    """Extract zip file and list contents"""
    print("=" * 70)
    print("📦 Extracting LAA-Net Weights")
    print("=" * 70)
    
    weights_dir = Path("/app/external/laa_net/weights")
    zip_file = weights_dir / "laa_net_weights.zip"
    
    if not zip_file.exists():
        print(f"❌ Zip file not found: {zip_file}")
        return False
    
    print(f"\n📁 Checking zip file: {zip_file}")
    file_size = zip_file.stat().st_size / (1024 * 1024)  # MB
    print(f"   Size: {file_size:.2f} MB")
    
    if not zipfile.is_zipfile(zip_file):
        print(f"⚠️  File is not a zip file. Checking contents...")
        # List what's in the file
        with open(zip_file, 'rb') as f:
            content = f.read(1000)  # Read first 1000 bytes
            print(f"   First 200 bytes: {content[:200]}")
        return False
    
    print(f"\n📦 Extracting zip file...")
    try:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            # List contents first
            file_list = zip_ref.namelist()
            print(f"\n📋 Files in zip ({len(file_list)} files):")
            for file in file_list[:20]:  # Show first 20
                info = zip_ref.getinfo(file)
                size_mb = info.file_size / (1024 * 1024)
                print(f"   - {file} ({size_mb:.2f} MB)")
            
            if len(file_list) > 20:
                print(f"   ... and {len(file_list) - 20} more files")
            
            # Extract all
            zip_ref.extractall(weights_dir)
            print(f"\n✅ Extraction complete!")
            
            # List extracted files
            print(f"\n📁 Extracted files in {weights_dir}:")
            for file in sorted(weights_dir.iterdir()):
                if file.is_file() and file.name != "laa_net_weights.zip":
                    size_mb = file.stat().st_size / (1024 * 1024)
                    print(f"   ✅ {file.name} ({size_mb:.2f} MB)")
                elif file.is_dir():
                    print(f"   📁 {file.name}/")
                    # List files in subdirectory
                    for subfile in sorted(file.iterdir()):
                        if subfile.is_file():
                            size_mb = subfile.stat().st_size / (1024 * 1024)
                            print(f"      - {subfile.name} ({size_mb:.2f} MB)")
            
            # Look for .pth files (PyTorch model weights)
            pth_files = list(weights_dir.rglob("*.pth"))
            if pth_files:
                print(f"\n✅ Found PyTorch weight files (.pth):")
                for pth_file in pth_files:
                    size_mb = pth_file.stat().st_size / (1024 * 1024)
                    print(f"   ✅ {pth_file.relative_to(weights_dir)} ({size_mb:.2f} MB)")
            
            # Look for .pkl files
            pkl_files = list(weights_dir.rglob("*.pkl"))
            if pkl_files:
                print(f"\n✅ Found pickle files (.pkl):")
                for pkl_file in pkl_files:
                    size_mb = pkl_file.stat().st_size / (1024 * 1024)
                    print(f"   ✅ {pkl_file.relative_to(weights_dir)} ({size_mb:.2f} MB)")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Error extracting: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    extract_and_verify()
