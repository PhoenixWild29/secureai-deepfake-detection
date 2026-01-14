#!/usr/bin/env python3
"""
Download LAA-Net pretrained weights from Dropbox (fixed for shared folder links)
"""
import os
import sys
import requests
from pathlib import Path
import zipfile
import re

def get_dropbox_direct_link(shared_link):
    """
    Convert Dropbox shared folder link to direct download links
    For shared folders, we need to access individual files
    """
    # Extract the key from the shared link
    # Format: https://www.dropbox.com/scl/fo/<KEY>/...
    match = re.search(r'scl/fo/([^/]+)', shared_link)
    if match:
        folder_key = match.group(1)
        print(f"📁 Detected Dropbox shared folder (key: {folder_key})")
        print(f"⚠️  Shared folders require manual download or API access")
        return None
    
    # Try to convert to direct download
    direct_link = shared_link.replace('?dl=0', '?dl=1')
    return direct_link

def download_from_dropbox_folder():
    """
    Instructions for downloading from Dropbox shared folder
    """
    print("=" * 70)
    print("📥 LAA-Net Pretrained Weights Download")
    print("=" * 70)
    
    dropbox_link = "https://www.dropbox.com/scl/fo/dzmldaytujdeuJeky69d5x1/AIJrH2mit1hxnl1qzavM3vk?rlkey=nzzliincrfwejw2yr0ovldru1&st=z8ds7i17&dl=0"
    
    print(f"\n⚠️  Dropbox shared folder links require manual download")
    print(f"\n📋 Instructions:")
    print(f"1. Open this link in your browser:")
    print(f"   {dropbox_link}")
    print(f"\n2. In the Dropbox folder, you should see weight files like:")
    print(f"   - efn4_fpn_hm_adv_best.pth (BI model)")
    print(f"   - efn4_fpn_hm_adv_sbi_best.pth (SBI model)")
    print(f"   - Or similar checkpoint files")
    print(f"\n3. Download ALL weight files from the folder")
    print(f"\n4. Upload to your server:")
    print(f"   scp <downloaded_files> root@<your-server>:/root/secureai-deepfake-detection/external/laa_net/weights/")
    print(f"\n5. Or copy to Docker container:")
    print(f"   docker cp <local_files> secureai-backend:/app/external/laa_net/weights/")
    
    # Create weights directory
    project_root = Path(__file__).parent
    weights_dir = project_root / "external" / "laa_net" / "weights"
    weights_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n✅ Weights directory ready: {weights_dir}")
    print(f"\n📝 After downloading, run:")
    print(f"   docker exec secureai-backend ls -lah /app/external/laa_net/weights/")
    print(f"   to verify files are present")
    
    return False

def check_existing_weights():
    """Check if weights are already downloaded"""
    weights_dir = Path("/app/external/laa_net/weights")
    
    if not weights_dir.exists():
        return False
    
    # Look for .pth files
    pth_files = list(weights_dir.rglob("*.pth"))
    if pth_files:
        print(f"\n✅ Found existing weight files:")
        for pth_file in pth_files:
            size_mb = pth_file.stat().st_size / (1024 * 1024)
            print(f"   - {pth_file.name} ({size_mb:.2f} MB)")
        return True
    
    return False

if __name__ == "__main__":
    # Check if weights already exist
    if check_existing_weights():
        print("\n✅ Weights already downloaded!")
        sys.exit(0)
    
    # Provide manual download instructions
    download_from_dropbox_folder()
