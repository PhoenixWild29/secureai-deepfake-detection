#!/usr/bin/env python3
"""
Simple Demo Script for SecureAI DeepFake Detection
Test the detection system quickly without starting the full web interface
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_single_video(video_path: str):
    """Test detection on a single video"""
    print("=" * 70)
    print("🎯 SecureAI DeepFake Detection - Simple Demo")
    print("=" * 70)
    print()
    
    if not os.path.exists(video_path):
        print(f"❌ Error: Video file not found: {video_path}")
        return False
    
    file_size = os.path.getsize(video_path) / (1024 * 1024)
    print(f"📹 Analyzing video: {video_path}")
    print(f"📊 File size: {file_size:.2f} MB")
    print()
    
    try:
        from ai_model.detect import detect_fake
        import time
        
        print("🔄 Starting analysis...")
        print("   This may take 30 seconds to 2 minutes depending on video length...")
        print()
        
        start_time = time.time()
        
        # Try ResNet model first (most reliable)
        result = detect_fake(video_path, model_type='resnet')
        
        elapsed = time.time() - start_time
        
        print("=" * 70)
        print("✓ ANALYSIS COMPLETE")
        print("=" * 70)
        print()
        
        # Display results
        is_fake = result.get('is_fake', False)
        confidence = result.get('confidence', 0) * 100
        authenticity = result.get('authenticity_score', 0) * 100
        
        if is_fake:
            print("🚨 VERDICT: DEEPFAKE DETECTED")
            print(f"   Confidence: {confidence:.1f}%")
        else:
            print("✓ VERDICT: AUTHENTIC VIDEO")
            print(f"   Authenticity: {authenticity:.1f}%")
        
        print()
        print("📊 Details:")
        print(f"   Method: {result.get('method', 'unknown')}")
        print(f"   Processing time: {elapsed:.2f} seconds")
        print(f"   Video hash: {result.get('video_hash', 'N/A')[:16]}...")
        
        if 'frames_analyzed' in result:
            print(f"   Frames analyzed: {result['frames_analyzed']}")
        
        print()
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return False

def find_test_videos():
    """Find available test videos"""
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
    test_videos = []
    
    # Check common locations
    locations = [
        '.',
        'uploads',
        'test_batch_videos'
    ]
    
    for location in locations:
        if not os.path.exists(location):
            continue
        
        if os.path.isfile(location):
            if any(location.endswith(ext) for ext in video_extensions):
                test_videos.append(location)
        else:
            for file in os.listdir(location):
                if any(file.endswith(ext) for ext in video_extensions):
                    full_path = os.path.join(location, file)
                    test_videos.append(full_path)
    
    return test_videos

def main():
    """Main entry point"""
    import sys
    
    # Check if video path provided as argument
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        test_single_video(video_path)
    else:
        # Find test videos
        test_videos = find_test_videos()
        
        if not test_videos:
            print("❌ No test videos found!")
            print()
            print("Usage:")
            print(f"  python {sys.argv[0]} path/to/video.mp4")
            print()
            print("Or place video files in one of these locations:")
            print("  - Current directory (*.mp4, *.avi, etc.)")
            print("  - uploads/ folder")
            print("  - test_batch_videos/ folder")
            return
        
        print("🎬 Found test videos:")
        for i, video in enumerate(test_videos[:10], 1):
            size = os.path.getsize(video) / (1024 * 1024)
            print(f"{i}. {video} ({size:.2f} MB)")
        
        if len(test_videos) > 10:
            print(f"... and {len(test_videos) - 10} more")
        
        print()
        
        try:
            choice = input("Enter video number to test (or 'q' to quit): ").strip()
            
            if choice.lower() == 'q':
                print("👋 Goodbye!")
                return
            
            idx = int(choice) - 1
            if 0 <= idx < len(test_videos):
                video_path = test_videos[idx]
                test_single_video(video_path)
            else:
                print("❌ Invalid selection")
        
        except (ValueError, KeyboardInterrupt):
            print("\n👋 Goodbye!")

if __name__ == '__main__':
    main()


