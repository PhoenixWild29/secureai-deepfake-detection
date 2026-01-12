#!/usr/bin/env python3
"""
Download LAA-Net pretrained weights from Dropbox
"""
import os
import sys
import requests
from pathlib import Path
import zipfile

def download_file(url, output_path):
    """Download a file from URL"""
    print(f"Downloading: {url}")
    print(f"To: {output_path}")
    
    try:
        response = requests.get(url, stream=True, allow_redirects=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\rProgress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='', flush=True)
        
        print(f"\n✅ Downloaded: {output_path}")
        return True
    except Exception as e:
        print(f"\n❌ Error downloading: {e}")
        return False

def main():
    """Download LAA-Net weights"""
    print("=" * 70)
    print("📥 Downloading LAA-Net Pretrained Weights")
    print("=" * 70)
    
    # Dropbox link from README
    dropbox_link = "https://www.dropbox.com/scl/fo/dzmldaytujdeuJe ky69d5x1/AIJrH2mit1hxnl1qzavM3vk?rlkey=nzzliincrfwejw2yr0ovldru1&st=z8ds7i17&dl=1"
    
    # Fix the link (replace spaces and ensure dl=1 for direct download)
    dropbox_link = dropbox_link.replace(" ", "").replace("dl=0", "dl=1")
    
    project_root = Path(__file__).parent
    weights_dir = project_root / "external" / "laa_net" / "weights"
    weights_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = weights_dir / "laa_net_weights.zip"
    
    print(f"\n📦 Downloading from Dropbox...")
    print(f"   Link: {dropbox_link}")
    print(f"   Output: {output_file}")
    
    # Download
    success = download_file(dropbox_link, str(output_file))
    
    if success and output_file.exists():
        file_size = output_file.stat().st_size / (1024 * 1024)  # MB
        print(f"\n✅ Download complete!")
        print(f"   File size: {file_size:.2f} MB")
        print(f"   Location: {output_file}")
        
        # Try to extract if it's a zip file
        if zipfile.is_zipfile(output_file):
            print(f"\n📦 Extracting zip file...")
            try:
                with zipfile.ZipFile(output_file, 'r') as zip_ref:
                    zip_ref.extractall(weights_dir)
                print(f"✅ Extraction complete!")
                print(f"\n📁 Files in weights directory:")
                for file in weights_dir.iterdir():
                    if file.is_file() and file.name != "laa_net_weights.zip":
                        size_mb = file.stat().st_size / (1024 * 1024)
                        print(f"   - {file.name} ({size_mb:.2f} MB)")
            except Exception as e:
                print(f"⚠️  Could not extract zip: {e}")
                print(f"   You may need to extract manually")
        
        print(f"\n✅ Weights downloaded to: {weights_dir}")
        print(f"\nNext steps:")
        print(f"1. Verify weight files are present")
        print(f"2. Share the list of files with me")
        print(f"3. I'll update the code to load LAA-Net")
    else:
        print(f"\n❌ Download failed")
        print(f"\nAlternative: Download manually from browser:")
        print(f"   {dropbox_link}")
        print(f"   Then upload to: {weights_dir}")

if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        print("❌ 'requests' library not found. Installing...")
        os.system(f"{sys.executable} -m pip install requests")
        import requests
    
    main()
