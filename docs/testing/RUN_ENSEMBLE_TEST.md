# Quick Guide: Run Ensemble Test (No Videos Needed)

## Option 1: Create Test Videos First (Recommended)

If you don't have any videos, create simple test videos:

```bash
# Copy the video creation script
docker cp create_test_video.py secureai-backend:/app/

# Create test videos
docker exec secureai-backend python /app/create_test_video.py
```

This will create 3 test videos in the `uploads/` directory.

## Option 2: Run Ensemble Test (Will Create Videos If Needed)

The comprehensive test script can work even without videos - it will tell you what to do:

```bash
# Run the ensemble test
docker exec secureai-backend python /app/test_ensemble_comprehensive.py
```

If no videos are found, it will:
- Tell you where to place videos
- You can then create test videos using Option 1 above

## Option 3: Use Existing Images (Convert to Video)

If you have images in `datasets/train/` or `datasets/val/`, we can create a video from them:

```bash
# This will be added to the test script
# For now, use Option 1 to create test videos
```

## Quick Test Command

After creating test videos (Option 1), run:

```bash
# Test ensemble on the created videos
docker exec secureai-backend python /app/test_ensemble_comprehensive.py
```

The script will automatically find videos in `uploads/` and test them.

