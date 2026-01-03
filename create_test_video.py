#!/usr/bin/env python3
"""
Create a simple test video for ensemble testing
Generates a basic video file that can be used for testing
"""
import cv2
import numpy as np
import os
from pathlib import Path

def create_test_video(output_path: str = 'uploads/test_video.mp4', 
                      duration_seconds: int = 3,
                      fps: int = 30,
                      width: int = 640,
                      height: int = 480):
    """
    Create a simple test video with a face-like pattern
    
    Args:
        output_path: Where to save the video
        duration_seconds: Video length
        fps: Frames per second
        width: Video width
        height: Video height
    """
    # Create output directory if needed
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    
    # Video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    num_frames = duration_seconds * fps
    
    print(f"Creating test video: {output_path}")
    print(f"  Duration: {duration_seconds}s, FPS: {fps}, Resolution: {width}x{height}")
    
    for frame_num in range(num_frames):
        # Create a simple frame with a face-like pattern
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Background color (skin tone)
        frame[:, :] = [220, 180, 140]  # BGR format
        
        # Draw a simple face
        center_x, center_y = width // 2, height // 2
        
        # Face circle
        cv2.circle(frame, (center_x, center_y), 100, (200, 160, 120), -1)
        
        # Eyes
        cv2.circle(frame, (center_x - 40, center_y - 20), 15, (0, 0, 0), -1)
        cv2.circle(frame, (center_x + 40, center_y - 20), 15, (0, 0, 0), -1)
        
        # Nose
        cv2.ellipse(frame, (center_x, center_y + 10), (10, 20), 0, 0, 360, (150, 100, 80), -1))
        
        # Mouth
        cv2.ellipse(frame, (center_x, center_y + 50), (30, 15), 0, 0, 180, (0, 0, 0), 2)
        
        # Add some variation over time
        offset = int(10 * np.sin(frame_num * 0.1))
        cv2.circle(frame, (center_x + offset, center_y), 100, (200, 160, 120), 2)
        
        out.write(frame)
    
    out.release()
    print(f"✅ Test video created: {output_path}")
    return output_path

def create_multiple_test_videos():
    """Create a few test videos"""
    uploads_dir = Path('uploads')
    uploads_dir.mkdir(exist_ok=True)
    
    videos_created = []
    
    # Create a few test videos
    for i in range(3):
        video_path = uploads_dir / f'test_video_{i+1}.mp4'
        create_test_video(str(video_path), duration_seconds=2, fps=15)
        videos_created.append(str(video_path))
    
    print(f"\n✅ Created {len(videos_created)} test videos in uploads/")
    print("   These can be used for ensemble testing")
    
    return videos_created

if __name__ == "__main__":
    create_multiple_test_videos()

