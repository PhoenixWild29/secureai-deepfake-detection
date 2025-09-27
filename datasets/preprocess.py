import cv2
import os
import numpy as np

def extract_frames(video_path, output_dir, frame_rate=1):
    cap = cv2.VideoCapture(video_path)
    count = 0
    success = True
    while success:
        success, image = cap.read()
        if count % frame_rate == 0 and success:
            cv2.imwrite(os.path.join(output_dir, f"frame_{count}.jpg"), image)
        count += 1
    cap.release()

def preprocess_dataset(dataset_dir):
    for root, dirs, files in os.walk(dataset_dir):
        for file in files:
            if file.endswith(".mp4"):
                video_path = os.path.join(root, file)
                output_dir = os.path.join(root, file.split(".")[0] + "_frames")
                os.makedirs(output_dir, exist_ok=True)
                extract_frames(video_path, output_dir)

if __name__ == "__main__":
    preprocess_dataset("datasets/celeb_df")
    print("Preprocessing complete.")