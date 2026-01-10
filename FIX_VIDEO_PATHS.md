# Fix Video Path Issues

## Problem
The script found 0 videos in `uploads/` even though there are 22 videos there. This is a path resolution issue inside the Docker container.

## Solution Applied
Updated the script to:
1. Check both `uploads/` and `/app/uploads/` paths
2. Fix path resolution in `detect_fake()` function
3. Show exactly where videos are found

## Test Again

```bash
# 1. Pull latest fix
git pull origin master

# 2. Copy updated files
docker cp test_ensemble_comprehensive.py secureai-backend:/app/
docker cp ai_model/detect.py secureai-backend:/app/ai_model/

# 3. First, verify videos exist in container
docker exec secureai-backend ls -la /app/uploads/*.mp4 | head -5

# 4. Run test again
docker exec secureai-backend bash -c "MAX_TEST_VIDEOS=10 python /app/test_ensemble_comprehensive.py 2>&1 | grep -v 'CUDA error' | grep -v 'cuInit' | grep -v 'stream_executor'"
```

## Expected Output
You should now see:
- "Found X videos in uploads/" (where X > 0)
- Videos being tested successfully
- Results for CLIP, ResNet, and Ensemble

