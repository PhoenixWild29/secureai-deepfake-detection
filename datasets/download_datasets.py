import os
import requests
from zipfile import ZipFile
import subprocess
import shutil
from pathlib import Path
import cv2
import numpy as np

def download_file(url, filename):
    """Download a file with progress indication"""
    print(f"Downloading {filename}...")
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))

    with open(filename, 'wb') as f:
        downloaded = 0
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress = (downloaded / total_size) * 100
                    print(f"\rProgress: {progress:.1f}%", end='', flush=True)
    print("\nDownload complete!")

def download_ffhq():
    """Download FFHQ dataset (high-quality faces for real images)"""
    print("Downloading FFHQ dataset for real face images...")

    # FFHQ thumbnails (smaller dataset for training)
    ffhq_url = "https://openaipublic.blob.core.windows.net/face-recognition-dataset/thumbnails128x128.zip"
    zip_path = "ffhq_thumbnails.zip"

    try:
        download_file(ffhq_url, zip_path)

        print("Extracting FFHQ dataset...")
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall("datasets/ffhq")

        os.remove(zip_path)
        print("FFHQ dataset ready!")

    except Exception as e:
        print(f"FFHQ download failed: {e}")
        print("Using synthetic data generation instead...")

def download_deepfake_samples():
    """Download sample deepfake videos for training"""
    print("Downloading sample deepfake detection dataset...")

    # Create directories
    os.makedirs("datasets/train/real", exist_ok=True)
    os.makedirs("datasets/train/fake", exist_ok=True)
    os.makedirs("datasets/val/real", exist_ok=True)
    os.makedirs("datasets/val/fake", exist_ok=True)

    # For demo purposes, we'll use some public sample videos
    # In production, you'd want larger datasets like FaceForensics++ or Celeb-DF

    sample_urls = [
        # These are placeholder URLs - in real implementation, use actual dataset URLs
        ("https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mpimport os
import requests
from zipfile import ZipFile
import subprocess
import shutil
from pathlib import Path
import cv2
import numpy as np

def download_file(url, filename):
    """Download a file with progress indication"""
    print(f"Downloading {filename}...")
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))

    with open(filename, 'wb') as f:
        downloaded = 0
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress = (downloaded / total_size) * 100
                    print(f"\rProgress: {progress:.1f}%", end='', flush=True)
    print("\nDownload complete!")

def download_ffhq():
    """Download FFHQ dataset (high-quality faces for real images)"""
    print("Downloading FFHQ dataset for real face images...")

    # FFHQ thumbnails (smaller dataset for training)
    ffhq_url = "https://openaipublic.blob.core.windows.net/face-recognition-dataset/thumbnails128x128.zip"
    zip_path = "ffhq_thumbnails.zip"

    try:
        download_file(ffhq_url, zip_path)

        print("Extracting FFHQ dataset...")
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall("datasets/ffhq")

        os.remove(zip_path)
        print("FFHQ dataset ready!")

    except Exception as e:
        print(f"FFHQ download failed: {e}")
        print("Using synthetic data generation instead...")

def download_deepfake_samples():
    """Download sample deepfake videos for training"""
    print("Downloading sample deepfake detection dataset...")

    # Create directories
    os.makedirs("datasets/train/real", exist_ok=True)
    os.makedirs("datasets/train/fake", exist_ok=True)
    os.makedirs("datasets/val/real", exist_ok=True)
    os.makedirs("datasets/val/fake", exist_ok=True)

    # For demo purposes, we'll use some public sample videos
    # In production, you'd want larger datasets like FaceForensics++ or Celeb-DF

    sample_urls = [
        # These are placeholder URLs - in real implementation, use actual dataset URLs
        ("https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp