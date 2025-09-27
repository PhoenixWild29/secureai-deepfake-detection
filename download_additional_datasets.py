#!/usr/bin/env python3
"""
Download additional deepfake datasets for enhanced training
"""
import requests
import zipfile
import os
from pathlib import Path
import shutil

def download_file(url, filename, chunk_size=8192):
    """Download file with progress"""
    print(f"📥 Downloading {filename}...")

    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()

    total_size = int(response.headers.get('content-length', 0))

    with open(filename, 'wb') as f:
        downloaded = 0
        for chunk in response.iter_content(chunk_size=chunk_size):
            f.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                progress = (downloaded / total_size) * 100
                print(".1f", end='\r')

    print(f"✅ Downloaded {filename}")
    return filename

def extract_zip(zip_path, extract_to):
    """Extract zip file"""
    print(f"📦 Extracting {zip_path}...")

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

    print(f"✅ Extracted to {extract_to}")

def main():
    datasets_dir = Path('datasets')
    datasets_dir.mkdir(exist_ok=True)

    # Smaller datasets that might be available
    available_datasets = [
        {
            'name': 'celeb_deepfakeforensics',
            'url': 'https://github.com/yuezunli/celeb-deepfakeforensics/archive/master.zip',
            'description': 'Celeb-DF forensics dataset (smaller version)'
        }
    ]

    print("🚀 Downloading additional deepfake datasets...")
    print("=" * 60)

    for dataset in available_datasets:
        try:
            print(f"\n📁 Processing {dataset['name']}")
            print(f"   {dataset['description']}")

            # Download
            zip_filename = f"{dataset['name']}.zip"
            download_file(dataset['url'], zip_filename)

            # Extract
            extract_dir = datasets_dir / dataset['name']
            extract_zip(zip_filename, extract_dir)

            # Clean up
            os.remove(zip_filename)

            print(f"✅ Successfully added {dataset['name']}")

        except Exception as e:
            print(f"❌ Failed to download {dataset['name']}: {e}")

    print("\n📋 Advanced Dataset Instructions:")
    print("=" * 60)
    print("For Celeb-DF++ and FaceForensics++ (require manual download):")
    print("• Celeb-DF++ (50GB): https://github.com/OUC-VAS/Celeb-DF-PP")
    print("• FaceForensics++ (1TB): https://github.com/ondyari/FaceForensics")
    print("• Both require academic/research credentials and manual download")
    print("• Extract to datasets/celeb_df_pp/ and datasets/face_forensics_pp/ respectively")

    print("\n💡 After downloading, run:")
    print("   python ai_model/train_enhanced.py --epochs 10")

if __name__ == "__main__":
    main()