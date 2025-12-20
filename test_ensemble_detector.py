#!/usr/bin/env python3
"""
Test script for the Enhanced Ensemble Detector
Tests CLIP-only detection with available sample videos
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_ensemble_detector():
    """Test the Enhanced Ensemble Detector."""
    print("=" * 70)
    print("Testing Enhanced Ensemble Detector (Priority 1 MVP)")
    print("=" * 70)
    print()
    
    try:
        from ai_model.enhanced_detector import EnhancedDetector
        print("✓ Successfully imported EnhancedDetector")
    except ImportError as e:
        print(f"✗ Failed to import EnhancedDetector: {e}")
        print("\nPlease install dependencies:")
        print("  python -m pip install open-clip-torch>=2.20.0")
        print("  python -m pip install mtcnn>=0.1.1")
        return False
    
    print("\nInitializing detector...")
    try:
        detector = EnhancedDetector()
        print(f"✓ Detector initialized on device: {detector.device}")
        print(f"✓ CLIP model: Loaded")
        print(f"✓ LAA-Net: {'Available' if detector.laa_available else 'Not available (submodule setup required)'}")
    except Exception as e:
        print(f"✗ Failed to initialize detector: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Find test videos
    test_videos = [
        "sample_video.mp4",
        "test_video_1.mp4",
        "test_video_2.mp4",
        "test_video_3.mp4"
    ]
    
    found_videos = []
    for video in test_videos:
        video_path = project_root / video
        if video_path.exists():
            found_videos.append(str(video_path))
    
    if not found_videos:
        print("\n" + "=" * 70)
        print("No test videos found in project directory.")
        print("The detector is ready to use, but no videos were found for testing.")
        print("\nTo test with your own video:")
        print("  from ai_model.enhanced_detector import EnhancedDetector")
        print("  detector = EnhancedDetector()")
        print("  result = detector.detect('path/to/your/video.mp4')")
        print("  print(result)")
        print("=" * 70)
        return True
    
    print(f"\nFound {len(found_videos)} test video(s)")
    print()
    
    # Test with each video
    for i, video_path in enumerate(found_videos, 1):
        print(f"Test {i}/{len(found_videos)}: {os.path.basename(video_path)}")
        print("-" * 70)
        
        try:
            result = detector.detect(video_path, num_frames=16)
            
            print(f"  Method: {result['method']}")
            print(f"  Is Deepfake: {result['is_deepfake']}")
            print(f"  Ensemble Probability: {result['ensemble_fake_probability']:.4f}")
            print(f"  CLIP Probability: {result['clip_fake_probability']:.4f}")
            print(f"  LAA-Net Probability: {result['laa_fake_probability']:.4f}")
            print(f"  Frames Analyzed: {result['num_frames_analyzed']}")
            print(f"  LAA-Net Available: {result['laa_available']}")
            print()
            
        except Exception as e:
            print(f"  ✗ Error during detection: {e}")
            import traceback
            traceback.print_exc()
            print()
            continue
    
    print("=" * 70)
    print("Testing complete!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = test_ensemble_detector()
    sys.exit(0 if success else 1)

