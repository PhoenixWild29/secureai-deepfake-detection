# Step 4 Fix: Adding Videos for Testing

## The Issue
The command `cp /path/to/videos/*.mp4 ~/secureai-deepfake-detection/uploads/` failed because `/path/to/videos/` is a placeholder, not a real path.

## Solution: Create Test Videos

You don't need to copy videos from elsewhere. The system can create test videos automatically!

### Option 1: Let the Test Script Create Videos (Easiest)

The test script will automatically create a test video if none are found. Just run:

```bash
docker exec secureai-backend python3 /app/test_ensemble_comprehensive.py
```

It will detect no videos exist and create one automatically.

### Option 2: Create Test Videos Manually

```bash
# Copy the create_test_video.py script to container (if not already there)
docker cp create_test_video.py secureai-backend:/app/

# Run it to create test videos
docker exec secureai-backend python3 /app/create_test_video.py
```

This will create 3 test videos in the `uploads/` directory.

### Option 3: Create Uploads Directory and Use Existing Videos

If you have videos elsewhere on your server:

```bash
# 1. Create uploads directory on host
mkdir -p ~/secureai-deepfake-detection/uploads

# 2. Find existing videos on your server
find ~ -name "*.mp4" -type f 2>/dev/null | head -10

# 3. Copy them to uploads (replace /actual/path/to/videos with real path)
# Example:
# cp /home/user/videos/my_video.mp4 ~/secureai-deepfake-detection/uploads/
```

### Option 4: Check for Videos Already in Container

```bash
# Check if videos already exist in container
docker exec secureai-backend find /app -name "*.mp4" -type f | head -10

# If videos exist, they'll be automatically discovered
```

## Recommended: Use Option 1

The easiest approach is to just run the test script - it will handle everything automatically:

```bash
docker exec secureai-backend python3 /app/test_ensemble_comprehensive.py
```

The script will:
1. Look for existing videos
2. If none found, create a test video automatically
3. Run the ensemble test

No manual video copying needed!

