# Quick Setup on Server - Step by Step

## Step 1: Pull Latest Changes ✅ (Already Done)
```bash
git pull origin master
```

## Step 2: Run Setup Script (Use python3)
```bash
# Use python3, not python
python3 setup_video_management.py
```

This will create all necessary directories.

## Step 3: Copy Files to Container ✅ (Already Done)
```bash
docker cp utils/video_paths.py secureai-backend:/app/utils/
docker cp test_ensemble_comprehensive.py secureai-backend:/app/
docker cp ai_model/detect.py secureai-backend:/app/ai_model/
docker cp api.py secureai-backend:/app/
```

## Step 4: Create Uploads Directory and Add Test Videos

### Option A: Create Uploads Directory First
```bash
# Create uploads directory on host
mkdir -p ~/secureai-deepfake-detection/uploads

# Verify it exists
ls -la ~/secureai-deepfake-detection/uploads/
```

### Option B: Find Existing Videos
```bash
# Search for any existing MP4 files
find ~/secureai-deepfake-detection -name "*.mp4" -type f | head -10

# If you find videos, copy them to uploads
# Example: cp /found/path/video.mp4 ~/secureai-deepfake-detection/uploads/
```

### Option C: Create a Simple Test Video
```bash
# Create a simple test video using ffmpeg (if available)
ffmpeg -f lavfi -i testsrc=duration=5:size=640x480:rate=15 -c:v libx264 -pix_fmt yuv420p ~/secureai-deepfake-detection/uploads/test_video_1.mp4

# Or use the Python script to create a test video
docker exec secureai-backend python3 /app/create_test_video.py
```

### Option D: Use Videos Already in Container
```bash
# Check if there are videos already in the container
docker exec secureai-backend find /app -name "*.mp4" -type f | head -10

# If videos exist, they should be accessible via VideoPathManager
```

## Step 5: Verify Setup

### Check VideoPathManager
```bash
docker exec secureai-backend python3 -c "
import sys
sys.path.insert(0, '/app')
from utils.video_paths import get_video_path_manager
pm = get_video_path_manager()
print(f'Uploads directory: {pm.get_uploads_directory()}')
videos = pm.find_all_videos(max_count=10)
print(f'Found {len(videos)} videos')
for v in videos[:5]:
    print(f'  - {v}')
"
```

### Run Test (Even Without Videos - Will Create One)
```bash
docker exec secureai-backend python3 /app/test_ensemble_comprehensive.py
```

The test script will automatically create a test video if none are found!

## Troubleshooting

### If uploads directory doesn't exist in container:
```bash
# Create it in container
docker exec secureai-backend mkdir -p /app/uploads

# Verify volume mount
docker inspect secureai-backend | grep -A 10 Mounts | grep uploads
```

### If no videos are found:
The test script will automatically create a simple test video if none are found. This is fine for testing the system.

