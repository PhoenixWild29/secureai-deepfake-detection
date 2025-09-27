#!/usr/bin/env python3
"""
Test SecureAI detection system with multiple videos
"""
import os
import cv2
import numpy as np
from ai_model.detect import detect_fake
from integration.integrate import main as run_full_pipeline

def create_test_videos():
    """Create different test videos with varying characteristics"""
    videos = [
        {
            "name": "test_video_1.mp4",
            "description": "Simple moving pattern",
            "pattern": "diagonal"
        },
        {
            "name": "test_video_2.mp4",
            "description": "Complex animation",
            "pattern": "complex"
        },
        {
            "name": "test_video_3.mp4",
            "description": "Static with noise",
            "pattern": "noise"
        }
    ]

    for video_config in videos:
        create_video(video_config)

    return [v["name"] for v in videos]

def create_video(config):
    """Create a test video with specific characteristics"""
    width, height = 640, 480
    fps = 30
    duration = 3  # seconds

    fourcc = cv2.VideoWriter.fourcc(*'mp4v')
    out = cv2.VideoWriter(config["name"], fourcc, fps, (width, height))

    for frame_num in range(fps * duration):
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        if config["pattern"] == "diagonal":
            # Moving diagonal line
            x = (frame_num * 10) % (width + 100)
            cv2.line(frame, (x, 0), (x - 100, height), (255, 255, 255), 3)

        elif config["pattern"] == "complex":
            # Complex pattern with circles and text
            center_x = width // 2 + int(50 * np.sin(frame_num * 0.1))
            center_y = height // 2 + int(30 * np.cos(frame_num * 0.15))
            cv2.circle(frame, (center_x, center_y), 50, (0, 255, 0), -1)
            cv2.putText(frame, f"Frame {frame_num}", (50, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        elif config["pattern"] == "noise":
            # Static frame with random noise
            noise = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
            frame = cv2.addWeighted(frame, 0.1, noise, 0.9, 0)
            cv2.putText(frame, "SECURE AI TEST", (width//2 - 100, height//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        out.write(frame)

    out.release()
    print(f"📹 Created {config['name']}: {config['description']}")

def test_video_detection(video_path):
    """Test detection on a single video"""
    print(f"\n🔍 Testing: {video_path}")
    print("-" * 40)

    try:
        result = detect_fake(video_path)
        print("✅ Detection Results:")
        print(f"   Authenticity Score: {result['authenticity_score']}/100")
        print(f"   Classification: {'🚨 FAKE' if result['is_fake'] else '✅ AUTHENTIC'}")
        print(f"   Confidence: {result['confidence']:.2%}")
        print(f"   Video Hash: {result['video_hash'][:16]}...")
        return result
    except Exception as e:
        print(f"❌ Error processing {video_path}: {e}")
        return None

def run_comprehensive_test():
    """Run comprehensive tests on multiple videos"""
    print("🧪 COMPREHENSIVE VIDEO TESTING")
    print("=" * 60)

    # Create test videos
    print("📹 Creating test videos...")
    test_videos = create_test_videos()
    test_videos.insert(0, "sample_video.mp4")  # Include existing sample

    # Test each video individually
    results = []
    for video in test_videos:
        if os.path.exists(video):
            result = test_video_detection(video)
            if result:
                results.append((video, result))
        else:
            print(f"⚠️  Video {video} not found, skipping...")

    # Summary
    print("\n" + "=" * 60)
    print("📊 TESTING SUMMARY")
    print("=" * 60)
    print(f"Total videos tested: {len(results)}")

    fake_count = sum(1 for _, result in results if result['is_fake'])
    authentic_count = len(results) - fake_count

    print(f"🚨 Detected as Fake: {fake_count}")
    print(f"✅ Detected as Authentic: {authentic_count}")

    print("\n📋 Detailed Results:")
    for video, result in results:
        status = "FAKE" if result['is_fake'] else "AUTHENTIC"
        confidence = result['confidence']
        score = result['authenticity_score']
        print(f"   {video}: {status} ({confidence:.1%} confidence, score: {score})")

    # Test full pipeline with one video
    print("\n🔗 Testing Full AI + Blockchain Pipeline")
    print("-" * 50)
    if test_videos:
        print(f"Running complete pipeline with {test_videos[0]}...")
        try:
            run_full_pipeline(test_videos[0])
        except Exception as e:
            print(f"❌ Pipeline test failed: {e}")

if __name__ == "__main__":
    run_comprehensive_test()