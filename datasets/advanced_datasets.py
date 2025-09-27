#!/usr/bin/env python3
"""
Advanced Dataset Integration
Download and integrate datasets from reviewed GitHub repositories
"""
import os
import requests
import zipfile
import tarfile
from pathlib import Path
import shutil
from typing import Dict, List, Optional
import subprocess
import sys

class DatasetManager:
    """Manager for downloading and integrating advanced deepfake datasets"""

    def __init__(self, base_dir: str = "datasets"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def download_file(self, url: str, filename: str, chunk_size: int = 8192) -> Path:
        """Download file with progress"""
        filepath = self.base_dir / filename

        print(f"📥 Downloading {filename}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))

        with open(filepath, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=chunk_size):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress = (downloaded / total_size) * 100
                    print(".1f", end='\r')

        print(f"✅ Downloaded {filename}")
        return filepath

    def extract_archive(self, filepath: Path, extract_to: Path) -> None:
        """Extract zip or tar archives"""
        print(f"📦 Extracting {filepath.name}...")

        extract_to.mkdir(exist_ok=True)

        if filepath.suffix == '.zip':
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
        elif filepath.suffixes in [['.tar', '.gz'], ['.tar', '.bz2']]:
            with tarfile.open(filepath, 'r:*') as tar_ref:
                tar_ref.extractall(extract_to)
        else:
            raise ValueError(f"Unsupported archive format: {filepath.suffix}")

        print(f"✅ Extracted to {extract_to}")

    def setup_celeb_df_pp(self) -> bool:
        """
        Setup Celeb-DF++ dataset (from OUC-VAS/Celeb-DF-PP)
        Large-scale video deepfake benchmark
        """
        try:
            print("🎬 Setting up Celeb-DF++ dataset...")

            # Note: This is a large dataset (~50GB)
            # In practice, you'd need to obtain this from the official source
            # For now, we'll create the structure

            dataset_dir = self.base_dir / "celeb_df_pp"
            dataset_dir.mkdir(exist_ok=True)

            # Create placeholder structure
            (dataset_dir / "videos").mkdir(exist_ok=True)
            (dataset_dir / "metadata").mkdir(exist_ok=True)

            print("ℹ️  Celeb-DF++ requires manual download from official source")
            print("   Visit: https://github.com/OUC-VAS/Celeb-DF-PP")
            print(f"   Extract videos to: {dataset_dir / 'videos'}")

            return True

        except Exception as e:
            print(f"❌ Failed to setup Celeb-DF++: {e}")
            return False

    def setup_face_forensics_pp(self) -> bool:
        """
        Setup FaceForensics++ dataset (from ondyari/FaceForensics)
        Comprehensive face manipulation dataset
        """
        try:
            print("🎭 Setting up FaceForensics++ dataset...")

            dataset_dir = self.base_dir / "face_forensics_pp"
            dataset_dir.mkdir(exist_ok=True)

            print("ℹ️  FaceForensics++ requires manual download")
            print("   Visit: https://github.com/ondyari/FaceForensics")
            print(f"   Extract to: {dataset_dir}")

            return True

        except Exception as e:
            print(f"❌ Failed to setup FaceForensics++: {e}")
            return False

    def setup_df40(self) -> bool:
        """
        Setup DF40 dataset (from YZY-stack/DF40)
        Next-generation deepfake detection with 40 techniques
        """
        try:
            print("🔬 Setting up DF40 dataset...")

            dataset_dir = self.base_dir / "df40"
            dataset_dir.mkdir(exist_ok=True)

            print("ℹ️  DF40 requires manual download from official source")
            print("   Visit: https://github.com/YZY-stack/DF40")
            print(f"   Extract to: {dataset_dir}")

            return True

        except Exception as e:
            print(f"❌ Failed to setup DF40: {e}")
            return False

    def setup_deeper_forensics(self) -> bool:
        """
        Setup DeeperForensics-1.0 dataset (from EndlessSora/DeeperForensics-1.0)
        Large-scale real-world face forgery detection
        """
        try:
            print("🔍 Setting up DeeperForensics-1.0 dataset...")

            dataset_dir = self.base_dir / "deeper_forensics"
            dataset_dir.mkdir(exist_ok=True)

            print("ℹ️  DeeperForensics requires manual download")
            print("   Visit: https://github.com/EndlessSora/DeeperForensics-1.0")
            print(f"   Extract to: {dataset_dir}")

            return True

        except Exception as e:
            print(f"❌ Failed to setup DeeperForensics: {e}")
            return False

    def setup_wild_deepfake(self) -> bool:
        """
        Setup WildDeepfake dataset (from deepfakeinthewild/deepfake-in-the-wild)
        Challenging real-world deepfake dataset
        """
        try:
            print("🌍 Setting up WildDeepfake dataset...")

            dataset_dir = self.base_dir / "wild_deepfake"
            dataset_dir.mkdir(exist_ok=True)

            print("ℹ️  WildDeepfake requires manual download")
            print("   Visit: https://github.com/deepfakeinthewild/deepfake-in-the-wild")
            print(f"   Extract to: {dataset_dir}")

            return True

        except Exception as e:
            print(f"❌ Failed to setup WildDeepfake: {e}")
            return False

    def setup_forgery_net(self) -> bool:
        """
        Setup ForgeryNet dataset (from yinanhe/forgerynet)
        Comprehensive forgery analysis benchmark
        """
        try:
            print("🎨 Setting up ForgeryNet dataset...")

            dataset_dir = self.base_dir / "forgery_net"
            dataset_dir.mkdir(exist_ok=True)

            print("ℹ️  ForgeryNet requires manual download")
            print("   Visit: https://github.com/yinanhe/forgerynet")
            print(f"   Extract to: {dataset_dir}")

            return True

        except Exception as e:
            print(f"❌ Failed to setup ForgeryNet: {e}")
            return False

    def setup_diffusion_datasets(self) -> bool:
        """
        Setup diffusion model datasets (DiFF, DiffFace, etc.)
        Critical for 2025 DM-aware detection
        """
        try:
            print("🎭 Setting up Diffusion Model datasets...")

            diffusion_dir = self.base_dir / "diffusion_datasets"
            diffusion_dir.mkdir(exist_ok=True)

            datasets = [
                ("DiFF", "xaCheng1996/DiFF"),
                ("DiffFace", "Rapisurazurite/DiffFace"),
                ("OpenRL-DeepFakeFace", "OpenRL-Lab/DeepFakeFace")
            ]

            for name, repo in datasets:
                dataset_subdir = diffusion_dir / name.lower().replace("-", "_")
                dataset_subdir.mkdir(exist_ok=True)

                print(f"ℹ️  {name} requires manual download")
                print(f"   Visit: https://github.com/{repo}")
                print(f"   Extract to: {dataset_subdir}")

            return True

        except Exception as e:
            print(f"❌ Failed to setup diffusion datasets: {e}")
            return False

    def create_unified_dataset(self) -> bool:
        """
        Create a unified dataset structure combining multiple sources
        """
        try:
            print("🔄 Creating unified dataset structure...")

            unified_dir = self.base_dir / "unified_deepfake"
            train_dir = unified_dir / "train"
            val_dir = unified_dir / "val"
            test_dir = unified_dir / "test"

            for split_dir in [train_dir, val_dir, test_dir]:
                (split_dir / "real").mkdir(parents=True, exist_ok=True)
                (split_dir / "fake").mkdir(parents=True, exist_ok=True)

            # Create symlinks or copy from individual datasets
            # This would be implemented based on available datasets

            print("✅ Unified dataset structure created")
            print(f"   Location: {unified_dir}")
            print("   Add your dataset files to real/ and fake/ subdirectories")

            return True

        except Exception as e:
            print(f"❌ Failed to create unified dataset: {e}")
            return False

    def setup_all_datasets(self) -> Dict[str, bool]:
        """
        Setup all available datasets
        Returns status of each dataset setup
        """
        print("🚀 Setting up all advanced deepfake datasets...")
        print("=" * 60)

        results = {}

        # Setup functions for each dataset
        datasets = [
            ("celeb_df_pp", self.setup_celeb_df_pp),
            ("face_forensics_pp", self.setup_face_forensics_pp),
            ("df40", self.setup_df40),
            ("deeper_forensics", self.setup_deeper_forensics),
            ("wild_deepfake", self.setup_wild_deepfake),
            ("forgery_net", self.setup_forgery_net),
            ("diffusion_datasets", self.setup_diffusion_datasets),
            ("unified_dataset", self.create_unified_dataset)
        ]

        for name, setup_func in datasets:
            print(f"\n📁 Setting up {name}...")
            results[name] = setup_func()
            print("-" * 40)

        # Summary
        successful = sum(results.values())
        total = len(results)

        print(f"\n📊 Dataset Setup Summary:")
        print(f"   ✅ Successful: {successful}/{total}")
        print(f"   ❌ Failed: {total - successful}/{total}")

        if successful > 0:
            print("\n🎯 Next Steps:")
            print("   1. Download datasets from the provided GitHub links")
            print("   2. Extract them to the appropriate directories")
            print("   3. Run training with: python ai_model/train_enhanced.py")
            print("   4. Test models on: python test_enhanced_models.py")

        return results

def main():
    """Main function for dataset setup"""
    print("🎬 SecureAI Advanced Dataset Manager")
    print("=" * 50)

    manager = DatasetManager()

    if len(sys.argv) > 1:
        # Setup specific dataset
        dataset_name = sys.argv[1]
        if hasattr(manager, f"setup_{dataset_name}"):
            func = getattr(manager, f"setup_{dataset_name}")
            success = func()
            sys.exit(0 if success else 1)
        else:
            print(f"❌ Unknown dataset: {dataset_name}")
            sys.exit(1)
    else:
        # Setup all datasets
        results = manager.setup_all_datasets()

        # Exit with success if at least one dataset was set up
        sys.exit(0 if any(results.values()) else 1)

if __name__ == "__main__":
    main()