#!/usr/bin/env python3
"""
Dataset Acquisition Helper for SecureAI DeepFake Detection
===========================================================

Downloads and organizes benchmark deepfake datasets into the directory
structure expected by ai_model/train_enhanced.py:

    datasets/<name>/train/real/   *.jpg or *.mp4
    datasets/<name>/train/fake/
    datasets/<name>/val/real/
    datasets/<name>/val/fake/
    datasets/<name>/test/real/
    datasets/<name>/test/fake/

Usage:
    python scripts/setup/download_datasets.py --dataset celeb_df_v2
    python scripts/setup/download_datasets.py --dataset faceforensics
    python scripts/setup/download_datasets.py --dataset dfdc
    python scripts/setup/download_datasets.py --validate
"""

import argparse
import os
import sys
import shutil
import random
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _count_files(directory: Path, extensions=('.jpg', '.jpeg', '.png', '.mp4')) -> int:
    if not directory.exists():
        return 0
    return sum(1 for f in directory.rglob('*') if f.suffix.lower() in extensions)


def _organize_flat_into_splits(src: Path, dst: Path,
                                train_pct=0.70, val_pct=0.15, seed=42):
    """
    Split a flat real/ fake/ directory into train/val/test sub-splits.
    src must have:  src/real/  and  src/fake/
    Result placed at: dst/train/real, dst/train/fake, dst/val/*, dst/test/*
    """
    random.seed(seed)
    for label in ('real', 'fake'):
        files = sorted((src / label).glob('*'))
        files = [f for f in files if f.is_file()]
        random.shuffle(files)

        n = len(files)
        n_train = int(n * train_pct)
        n_val = int(n * val_pct)

        splits = {
            'train': files[:n_train],
            'val':   files[n_train:n_train + n_val],
            'test':  files[n_train + n_val:],
        }

        for split, split_files in splits.items():
            out_dir = _ensure_dir(dst / split / label)
            for f in split_files:
                shutil.copy2(f, out_dir / f.name)

        print(f"  {label}: {n_train} train / {n_val} val / {n - n_train - n_val} test")


# ---------------------------------------------------------------------------
# Celeb-DF v2
# ---------------------------------------------------------------------------

def download_celeb_df_v2():
    """
    Celeb-DF v2 is the most accessible benchmark dataset.

    Official page:  https://github.com/yuezunli/celeb-deepfakeforensics
    Paper:          https://arxiv.org/abs/1909.12962
    Downloads:      Google Drive (link on the GitHub repo's README)

    The dataset is ~1.7 GB compressed. It requires filling a short Google Form
    on the GitHub README to receive the download link (no manual verification).

    Steps:
    1.  Visit:  https://github.com/yuezunli/celeb-deepfakeforensics
    2.  Click the Google Drive link in the README → download Celeb-DF-v2.zip
    3.  Place the zip at:  datasets/celeb_df_v2.zip  (or any path)
    4.  Run this script with --organize-celeb  <path-to-zip>
    """
    print("""
================================================================
           Celeb-DF v2 -- Download Instructions
================================================================

1. Open:  https://github.com/yuezunli/celeb-deepfakeforensics
2. Find the Google Drive download link in the README
3. Download  Celeb-DF-v2.zip  (~1.7 GB)
4. Place the zip anywhere, then run:

   python scripts/setup/download_datasets.py --organize-celeb <path-to-zip>

The script will extract and organize it into:
   datasets/celeb_df_v2/train/real/
   datasets/celeb_df_v2/train/fake/
   datasets/celeb_df_v2/val/real/
   ...
""")


def organize_celeb_df_v2(zip_path: str):
    """Extract and organize Celeb-DF v2 zip into training splits."""
    import zipfile

    zip_path = Path(zip_path)
    if not zip_path.exists():
        print(f"ERROR: File not found: {zip_path}")
        sys.exit(1)

    staging = Path('datasets/_staging_celeb_df_v2')
    _ensure_dir(staging)

    print(f"Extracting {zip_path} ...")
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(staging)

    # Celeb-DF v2 structure after extraction:
    #   Celeb-DF-v2/
    #     Celeb-real/    real face videos
    #     Celeb-synthesis/  fake videos
    #     YouTube-real/  additional real videos
    real_dirs = list(staging.rglob('*real*'))
    fake_dirs = list(staging.rglob('*synthesis*')) + list(staging.rglob('*fake*'))

    staging_real = _ensure_dir(staging / '_flat' / 'real')
    staging_fake = _ensure_dir(staging / '_flat' / 'fake')

    for d in real_dirs:
        if d.is_dir():
            for f in d.glob('*.mp4'):
                shutil.copy2(f, staging_real / f.name)

    for d in fake_dirs:
        if d.is_dir():
            for f in d.glob('*.mp4'):
                shutil.copy2(f, staging_fake / f.name)

    real_count = _count_files(staging_real, ('.mp4',))
    fake_count = _count_files(staging_fake, ('.mp4',))
    print(f"Found {real_count} real videos, {fake_count} fake videos")

    dst = Path('datasets/celeb_df_v2')
    print(f"Organizing into train/val/test splits at {dst} ...")
    _organize_flat_into_splits(staging / '_flat', dst)

    shutil.rmtree(staging, ignore_errors=True)
    print(f"\n[OK] Celeb-DF v2 organized at: {dst}")
    _print_dataset_summary(dst)


# ---------------------------------------------------------------------------
# FaceForensics++
# ---------------------------------------------------------------------------

def download_faceforensics():
    """Instructions for FaceForensics++ (requires institutional access form)."""
    print("""
================================================================
         FaceForensics++ -- Download Instructions
================================================================

FaceForensics++ is the standard academic benchmark for deepfake detection.
Access requires filling a short form (automatic approval, no waiting).

1. Fill the access form:
   https://docs.google.com/forms/d/e/1FAIpQLSdRRR3L5zAv6tQ_CKxmK4W96tAab_pfBu2EKAgQbeDVhmXagg/viewform

2. You will receive an email with a download script (download_FaceForensics.py)

3. Download compressed (c23) version — ~30 GB total:
   python download_FaceForensics.py ./ -d all -c c23 --server EU

4. Organize with this script:
   python scripts/setup/download_datasets.py --organize-ff <downloaded-folder>

Dataset contains:
  - Deepfakes (DF)       — face-swap
  - Face2Face (F2F)      — expression transfer
  - FaceSwap (FS)        — identity swap
  - NeuralTextures (NT)  — neural rendering
  - FaceShifter (FSh)    — high-quality swap
  - original_sequences/  — real (c23/videos/)
""")


def organize_faceforensics(base_dir: str):
    """Organize downloaded FaceForensics++ into training splits."""
    base = Path(base_dir)
    if not base.exists():
        print(f"ERROR: Directory not found: {base}")
        sys.exit(1)

    staging_real = Path('datasets/_staging_ff/real')
    staging_fake = Path('datasets/_staging_ff/fake')
    _ensure_dir(staging_real)
    _ensure_dir(staging_fake)

    # Real videos
    for real_vid in (base / 'original_sequences' / 'youtube' / 'c23' / 'videos').rglob('*.mp4'):
        shutil.copy2(real_vid, staging_real / real_vid.name)

    # Fake videos (all manipulation types)
    for manip in ('Deepfakes', 'Face2Face', 'FaceSwap', 'NeuralTextures', 'FaceShifter'):
        for fake_vid in (base / 'manipulated_sequences' / manip / 'c23' / 'videos').rglob('*.mp4'):
            shutil.copy2(fake_vid, staging_fake / fake_vid.name)

    print(f"Real: {_count_files(staging_real, ('.mp4',))} videos")
    print(f"Fake: {_count_files(staging_fake, ('.mp4',))} videos")

    dst = Path('datasets/face_forensics_pp')
    print(f"Organizing into train/val/test splits at {dst} ...")
    _organize_flat_into_splits(Path('datasets/_staging_ff'), dst)

    shutil.rmtree('datasets/_staging_ff', ignore_errors=True)
    print(f"\n[OK] FaceForensics++ organized at: {dst}")
    _print_dataset_summary(dst)


# ---------------------------------------------------------------------------
# DFDC (DeepFake Detection Challenge)
# ---------------------------------------------------------------------------

def download_dfdc():
    """Instructions for DFDC dataset via Kaggle."""
    print("""
================================================================
           DFDC -- Download Instructions (Kaggle)
================================================================

The Deepfake Detection Challenge dataset is hosted on Kaggle (~470 GB full,
~7 GB preview set).

Option A — Preview set (7 GB, good for initial testing):
   kaggle datasets download -d yakovlev/dfdc-preview-set

Option B — Full challenge set (470 GB):
   kaggle competitions download -c deepfake-detection-challenge

Prerequisites:
   pip install kaggle
   # Place ~/.kaggle/kaggle.json with your API key from:
   # https://www.kaggle.com/settings → API → Create New Token

After download, organize with:
   python scripts/setup/download_datasets.py --organize-dfdc <extracted-folder>
""")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _print_dataset_summary(path: Path):
    print(f"\n  Dataset summary: {path}")
    for split in ('train', 'val', 'test'):
        real = _count_files(path / split / 'real')
        fake = _count_files(path / split / 'fake')
        if real + fake > 0:
            ratio = fake / real if real else float('inf')
            print(f"    {split:5s}: {real:5d} real  {fake:5d} fake  (ratio: {ratio:.2f})")


def validate_datasets():
    """Scan all dataset directories and report counts and class balance."""
    datasets_root = Path('datasets')
    if not datasets_root.exists():
        print("No datasets/ directory found.")
        return

    dataset_dirs = sorted([
        d for d in datasets_root.iterdir()
        if d.is_dir() and not d.name.startswith('_')
    ])

    if not dataset_dirs:
        print("No dataset subdirectories found in datasets/")
        print("Run with --dataset <name> to get download instructions.")
        return

    total_train_real = total_train_fake = 0
    for d in dataset_dirs:
        _print_dataset_summary(d)
        total_train_real += _count_files(d / 'train' / 'real')
        total_train_fake += _count_files(d / 'train' / 'fake')

    print(f"\n  TOTAL training samples: {total_train_real} real, {total_train_fake} fake")
    if total_train_real > 0:
        balance = total_train_fake / total_train_real
        if 0.8 <= balance <= 1.25:
            print("  [OK] Class balance is good (ratio ~1.0)")
        elif balance < 0.5:
            print("  [!]  Dataset is real-heavy. Consider oversampling fakes or undersampling real.")
        else:
            print("  [!]  Dataset is fake-heavy. Consider balancing before training.")

    # Estimate training time (rough: 0.3 s/sample on CPU, 0.05 s/sample on GPU)
    total = total_train_real + total_train_fake
    if total > 0:
        cpu_hours = total * 0.3 / 3600
        gpu_hours = total * 0.05 / 3600
        print(f"\n  Estimated training time (50 epochs, batch=8):")
        print(f"    CPU: ~{cpu_hours * 50:.1f} hours")
        print(f"    GPU: ~{gpu_hours * 50:.1f} hours")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Dataset acquisition helper for SecureAI deepfake training',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--dataset', choices=['celeb_df_v2', 'faceforensics', 'dfdc'],
                        help='Show download instructions for a dataset')
    parser.add_argument('--organize-celeb', metavar='ZIP_PATH',
                        help='Extract and organize Celeb-DF v2 zip')
    parser.add_argument('--organize-ff', metavar='DIR_PATH',
                        help='Organize downloaded FaceForensics++ directory')
    parser.add_argument('--validate', action='store_true',
                        help='Scan datasets/ and report counts and class balance')

    args = parser.parse_args()

    if args.validate:
        validate_datasets()
    elif args.organize_celeb:
        organize_celeb_df_v2(args.organize_celeb)
    elif args.organize_ff:
        organize_faceforensics(args.organize_ff)
    elif args.dataset == 'celeb_df_v2':
        download_celeb_df_v2()
    elif args.dataset == 'faceforensics':
        download_faceforensics()
    elif args.dataset == 'dfdc':
        download_dfdc()
    else:
        parser.print_help()
        print("""
Examples:
  python scripts/setup/download_datasets.py --dataset celeb_df_v2
  python scripts/setup/download_datasets.py --dataset faceforensics
  python scripts/setup/download_datasets.py --validate
  python scripts/setup/download_datasets.py --organize-celeb ~/Downloads/Celeb-DF-v2.zip
""")


if __name__ == '__main__':
    main()
