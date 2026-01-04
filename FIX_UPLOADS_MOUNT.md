# Fix Uploads Directory Issue

## Problem
The container can't find videos in `/app/uploads/` even though docker-compose mounts `./uploads:/app/uploads`.

## Diagnosis Steps

### Step 1: Check if uploads exists on host
```bash
# On your server
ls -la ~/secureai-deepfake-detection/uploads/ | head -10
```

### Step 2: Check if directory exists in container
```bash
docker exec secureai-backend ls -la /app/ | grep uploads
```

### Step 3: Check if mount is working
```bash
# Check what's actually mounted
docker exec secureai-backend ls -la /app/uploads/ 2>&1
```

### Step 4: Check container mounts
```bash
docker inspect secureai-backend | grep -A 5 "Mounts" | grep uploads
```

## Solutions

### Solution 1: Create uploads directory on host (if missing)
```bash
# On your server
mkdir -p ~/secureai-deepfake-detection/uploads
chmod 755 ~/secureai-deepfake-detection/uploads
```

### Solution 2: Copy videos to host uploads directory
If videos are elsewhere, copy them:
```bash
# Find videos
find ~/secureai-deepfake-detection -name "*.mp4" -type f | head -5

# Copy to uploads (if found elsewhere)
# Example: cp /path/to/videos/*.mp4 ~/secureai-deepfake-detection/uploads/
```

### Solution 3: Restart container to remount
```bash
docker compose -f docker-compose.https.yml restart secureai-backend
```

### Solution 4: Use videos from root directory
The script found 4 videos in root directory (`test_video_*.mp4`). You can test with those:

```bash
# Test with the 4 videos found in root
docker exec secureai-backend bash -c "MAX_TEST_VIDEOS=4 python /app/test_ensemble_comprehensive.py 2>&1 | grep -v 'CUDA error' | grep -v 'cuInit' | grep -v 'stream_executor'"
```

## Quick Check Command
Run this to see what's happening:

```bash
# Check everything at once
echo "=== Host uploads ===" && ls -la ~/secureai-deepfake-detection/uploads/*.mp4 2>&1 | head -5
echo "=== Container uploads ===" && docker exec secureai-backend ls -la /app/uploads/*.mp4 2>&1 | head -5
echo "=== Container root videos ===" && docker exec secureai-backend ls -la /app/test_video*.mp4 2>&1 | head -5
```

