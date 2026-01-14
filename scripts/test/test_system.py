# Simple test script
import os
from integration.integrate import main

def create_sample_video():
    """Create a simple test video if none exists"""
    import cv2
    import numpy as np

    # Create a simple 5-second video with moving text
    width, height = 640, 480
    fps = 30
    duration = 5  # seconds

    fourcc = cv2.VideoWriter.fourcc(*'mp4v')
    out = cv2.VideoWriter('sample_video.mp4', fourcc, fps, (width, height))

    for frame_num in range(fps * duration):
        # Create a frame with moving text
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = [50, 50, 50]  # Dark background

        # Add some text
        text = f"SecureAI Test Frame {frame_num}"
        cv2.putText(frame, text, (50, height//2), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        out.write(frame)

    out.release()
    print("📹 Created sample_video.mp4 for testing")

def test_system():
    """Test the complete SecureAI system"""
    print("🧪 Testing SecureAI DeepFake Detection System")
    print("=" * 60)

    # Check if sample video exists
    if not os.path.exists("sample_video.mp4"):
        print("Creating sample video for testing...")
        create_sample_video()

    # Run the main pipeline
    try:
        main("sample_video.mp4")
        print("\n✅ System test completed successfully!")
        print("\n📋 Next steps:")
        print("   1. Replace sample_video.mp4 with real videos to test")
        print("   2. Deploy smart contract to Solana for real blockchain storage")
        print("   3. Train YOLO model with real deepfake datasets for production use")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

    return True

if __name__ == "__main__":
    test_system()