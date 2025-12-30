#!/usr/bin/env python3
"""
Test Data Loader Utility
Handles loading and organizing test video datasets for DFDM validation
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import random


@dataclass
class TestVideo:
    """Container for test video metadata"""
    filepath: Path
    label: str  # 'real' or 'deepfake'
    category: str  # 'gan', 'diffusion', 'authentic', 'compressed', etc.
    expected_prediction: bool  # True for real, False for deepfake
    metadata: Dict  # Additional info (quality, compression, etc.)


class TestDataLoader:
    """
    Utility class for loading and organizing test datasets
    
    Expected directory structure:
    tests/test_data/
    ├── real/
    │   ├── authentic_1080p/
    │   ├── authentic_720p/
    │   ├── authentic_360p/
    │   ├── demographic_diverse/
    │   └── edge_cases/
    ├── deepfake/
    │   ├── gan_based/
    │   │   ├── deepfacelab/
    │   │   ├── faceswap/
    │   │   └── stylegan/
    │   ├── diffusion_based/
    │   │   ├── stable_diffusion/
    │   │   └── runway_gen2/
    │   ├── audio_visual/
    │   │   ├── wav2lip/
    │   │   └── voice_clone/
    │   ├── compressed/
    │   │   ├── compression_round_1/
    │   │   ├── compression_round_3/
    │   │   └── compression_round_5/
    │   └── adversarial/
    │       ├── pgd_attack/
    │       ├── fgsm_attack/
    │       └── patch_attack/
    """
    
    def __init__(self, base_path: str = "tests/test_data"):
        self.base_path = Path(base_path)
        self.test_videos = []
        
    def load_all_test_videos(self) -> List[TestVideo]:
        """
        Load all test videos from the directory structure
        Returns: List of TestVideo objects
        """
        if not self.base_path.exists():
            raise FileNotFoundError(f"Test data directory not found: {self.base_path}")
        
        self.test_videos = []
        
        # Load real/authentic videos
        real_path = self.base_path / "real"
        if real_path.exists():
            self._load_videos_from_directory(real_path, label='real', expected_prediction=True)
        
        # Load deepfake videos
        deepfake_path = self.base_path / "deepfake"
        if deepfake_path.exists():
            self._load_videos_from_directory(deepfake_path, label='deepfake', expected_prediction=False)
        
        return self.test_videos
    
    def _load_videos_from_directory(self, directory: Path, label: str, expected_prediction: bool):
        """
        Recursively load videos from directory structure
        """
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if Path(file).suffix.lower() in video_extensions:
                    filepath = Path(root) / file
                    
                    # Determine category from directory structure
                    relative_path = filepath.relative_to(self.base_path)
                    category = self._determine_category(relative_path, label)
                    
                    # Extract metadata
                    metadata = self._extract_metadata(relative_path, filepath)
                    
                    video = TestVideo(
                        filepath=filepath,
                        label=label,
                        category=category,
                        expected_prediction=expected_prediction,
                        metadata=metadata
                    )
                    self.test_videos.append(video)
    
    def _determine_category(self, relative_path: Path, label: str) -> str:
        """Determine video category from path structure"""
        path_parts = relative_path.parts
        
        if label == 'real':
            if 'authentic' in path_parts:
                # Extract resolution from path
                for part in path_parts:
                    if any(res in part for res in ['1080p', '720p', '360p']):
                        return f'authentic_{part}'
                return 'authentic'
            elif 'demographic' in path_parts:
                return 'demographic_diverse'
            elif 'edge_cases' in path_parts:
                return 'edge_cases'
            else:
                return 'real_unknown'
        
        else:  # deepfake
            path_str = str(relative_path).lower()
            
            if 'deepfacelab' in path_str:
                return 'deepfacelab'
            elif 'faceswap' in path_str:
                return 'faceswap'
            elif 'stylegan' in path_str:
                return 'stylegan'
            elif 'stable_diffusion' in path_str:
                return 'stable_diffusion'
            elif 'runway_gen2' in path_str or 'gen2' in path_str:
                return 'runway_gen2'
            elif 'wav2lip' in path_str:
                return 'wav2lip'
            elif 'voice_clone' in path_str:
                return 'voice_clone'
            elif 'compression' in path_str:
                # Extract compression round
                for part in path_parts:
                    if 'round' in part or 'pass' in part:
                        return f'compression_{part}'
                return 'compression'
            elif 'pgd_attack' in path_str:
                return 'adversarial_pgd'
            elif 'fgsm_attack' in path_str:
                return 'adversarial_fgsm'
            elif 'patch_attack' in path_str:
                return 'adversarial_patch'
            else:
                return 'deepfake_unknown'
    
    def _extract_metadata(self, relative_path: Path, filepath: Path) -> Dict:
        """Extract metadata from file path and size"""
        metadata = {
            'relative_path': str(relative_path),
            'filename': filepath.name,
            'size_mb': filepath.stat().st_size / (1024 * 1024),
        }
        
        # Extract quality/compression info
        path_str = str(relative_path).lower()
        
        # Resolution
        for res in ['1080p', '720p', '360p', '4k']:
            if res in path_str:
                metadata['resolution'] = res
                break
        
        # Compression level
        if 'compression' in path_str or 'round' in path_str:
            for i in range(1, 6):
                if f'round_{i}' in path_str or f'pass_{i}' in path_str:
                    metadata['compression_round'] = i
        
        # Attack epsilon
        if 'adversarial' in path_str:
            metadata['is_adversarial'] = True
        
        return metadata
    
    def get_test_subset(self, category: str, limit: Optional[int] = None) -> List[TestVideo]:
        """
        Get a subset of test videos by category
        """
        subset = [v for v in self.test_videos if v.category == category]
        
        if limit:
            subset = random.sample(subset, min(limit, len(subset)))
        
        return subset
    
    def get_label_split(self, label: str) -> List[TestVideo]:
        """Get all videos with a specific label"""
        return [v for v in self.test_videos if v.label == label]
    
    def summarize_dataset(self) -> Dict:
        """
        Generate summary statistics of loaded dataset
        """
        total = len(self.test_videos)
        real_count = sum(1 for v in self.test_videos if v.label == 'real')
        deepfake_count = sum(1 for v in self.test_videos if v.label == 'deepfake')
        
        categories = {}
        for video in self.test_videos:
            categories[video.category] = categories.get(video.category, 0) + 1
        
        return {
            'total_videos': total,
            'real_videos': real_count,
            'deepfake_videos': deepfake_count,
            'category_distribution': categories
        }
    
    def save_dataset_manifest(self, output_path: str = "tests/dataset_manifest.json"):
        """
        Save a manifest of all test videos for reference
        """
        manifest = {
            'total_videos': len(self.test_videos),
            'videos': [
                {
                    'filepath': str(video.filepath),
                    'label': video.label,
                    'category': video.category,
                    'expected_prediction': video.expected_prediction,
                    'metadata': video.metadata
                }
                for video in self.test_videos
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return output_path


# Convenience functions for quick access
def load_ci_test_set(loader: TestDataLoader, size: int = 50) -> List[TestVideo]:
    """
    Load a small representative set for CI/CD quick tests
    """
    # Mix of different categories
    categories = ['authentic', 'deepfacelab', 'faceswap', 'compression']
    ci_videos = []
    
    for category in categories:
        subset = loader.get_test_subset(category, limit=size // len(categories))
        ci_videos.extend(subset)
    
    # Add random sampling if we need more
    if len(ci_videos) < size:
        remaining = size - len(ci_videos)
        remaining_videos = [v for v in loader.test_videos if v not in ci_videos]
        ci_videos.extend(random.sample(remaining_videos, min(remaining, len(remaining_videos))))
    
    return ci_videos[:size]


def load_adversarial_test_set(loader: TestDataLoader) -> List[TestVideo]:
    """Load only adversarial test videos"""
    return loader.get_test_subset('adversarial_pgd', limit=100)


def load_performance_test_set(loader: TestDataLoader, size: int = 20) -> List[TestVideo]:
    """Load a representative set for performance testing"""
    # Mix of different quality levels
    categories = ['authentic_1080p', 'authentic_720p', 'authentic_360p', 
                  'deepfacelab', 'compression']
    
    perf_videos = []
    per_category = size // len(categories)
    
    for category in categories:
        subset = loader.get_test_subset(category, limit=per_category)
        perf_videos.extend(subset)
    
    return perf_videos[:size]


if __name__ == "__main__":
    # Demo usage
    loader = TestDataLoader(base_path="tests/test_data")
    videos = loader.load_all_test_videos()
    
    print(f"Loaded {len(videos)} test videos")
    summary = loader.summarize_dataset()
    print(json.dumps(summary, indent=2))

