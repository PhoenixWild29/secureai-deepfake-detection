import os
import cv2
import numpy as np
from pathlib import Path

def create_synthetic_dataset():
    """Create synthetic training dataset from existing videos"""
    print("🎨 Creating synthetic training dataset...")

    # Create directories
    os.makedirs("datasets/train/real", exist_ok=True)
    os.makedirs("datasets/train/fake", exist_ok=True)
    os.makedirs("datasets/val/real", exist_ok=True)
    os.makedirs("datasets/val/fake", exist_ok=True)

    # Source videos
    source_videos = ["sample_video.mp4", "test_video_1.mp4", "test_video_2.mp4", "test_video_3.mp4"]

    frame_count = 0
    max_frames = 500  # Limit for demo training

    for video_file in source_videos:
        if os.path.exists(video_file) and frame_count < max_frames:
            print(f"📹 Processing {video_file}...")
            cap = cv2.VideoCapture(video_file)

            count = 0
            success = True
            while success and frame_count < max_frames:
                success, frame = cap.read()
                if success and count % 5 == 0:  # Extract every 5th frame
                    # Save as real image
                    real_path = f"datasets/train/real/frame_{frame_count:04d}.jpg"
                    cv2.imwrite(real_path, frame)

                    # Create synthetic "fake" by adding artifacts
                    fake_frame = apply_deepfake_artifacts(frame)
                    fake_path = f"datasets/train/fake/frame_{frame_count:04d}.jpg"
                    cv2.imwrite(fake_path, fake_frame)

                    frame_count += 1
                    if frame_count % 50 == 0:
                        print(f"   Processed {frame_count} frame pairs...")

                count += 1

            cap.release()

    # Split some data for validation
    import shutil
    real_files = os.listdir("datasets/train/real")
    fake_files = os.listdir("datasets/train/fake")

    # Move 20% to validation
    val_count = len(real_files) // 5
    for i in range(val_count):
        shutil.move(f"datasets/train/real/{real_files[i]}", f"datasets/val/real/{real_files[i]}")
        shutil.move(f"datasets/train/fake/{fake_files[i]}", f"datasets/val/fake/{fake_files[i]}")

    print(f"✅ Created dataset with {frame_count} real/fake image pairs")
    print(f"   Train: {len(os.listdir('datasets/train/real'))} real, {len(os.listdir('datasets/train/fake'))} fake")
    print(f"   Val: {len(os.listdir('datasets/val/real'))} real, {len(os.listdir('datasets/val/fake'))} fake")

def apply_deepfake_artifacts(frame):
    """Apply synthetic deepfake artifacts to create fake training samples"""
    fake_frame = frame.copy()

    # Simulate compression artifacts
    fake_frame = cv2.resize(fake_frame, (320, 240))
    fake_frame = cv2.resize(fake_frame, (640, 480))

    # Add subtle noise (common in deepfakes)
    noise = np.random.normal(0, 15, fake_frame.shape).astype(np.uint8)
    fake_frame = cv2.add(fake_frame, noise)

    # Add slight color distortion
    fake_frame = fake_frame.astype(np.float32)
    fake_frame *= 0.95  # Slightly darken
    fake_frame = np.clip(fake_frame, 0, 255).astype(np.uint8)

    # Add motion blur simulation (common artifact)
    kernel = np.ones((3, 3), np.float32) / 9
    fake_frame = cv2.filter2D(fake_frame, -1, kernel)

    return fake_frame

def update_data_yaml():
    """Update data.yaml for YOLO training"""
    yaml_content = """
train: datasets/train
val: datasets/val

nc: 2
names: ['real', 'fake']
"""

    with open("datasets/data.yaml", "w") as f:
        f.write(yaml_content.strip())

    print("📝 Updated data.yaml configuration")

if __name__ == "__main__":
    print("🚀 SecureAI Training Dataset Setup")
    print("=" * 40)

    create_synthetic_dataset()
    update_data_yaml()

    print("\n✅ Training dataset ready!")
    print("🎯 Run 'python ai_model/train_yolo.py' to start training")