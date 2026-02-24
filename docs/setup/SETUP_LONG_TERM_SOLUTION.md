# Setup Long-Term Video Management Solution

## Overview

This is a **comprehensive, long-term solution** for video file management that will work reliably for all future testing and production use.

## What Was Implemented

### 1. VideoPathManager (`utils/video_paths.py`)
- **Centralized path resolution** - One place to manage all video paths
- **Automatic directory creation** - Creates directories if they don't exist
- **Multi-location search** - Finds videos in multiple standard locations
- **Container-aware** - Works in Docker and local environments
- **Future-proof** - Easy to extend with new storage locations

### 2. Updated Core Functions
- `detect_fake()` - Now uses VideoPathManager for reliable path resolution
- `test_ensemble_comprehensive.py` - Uses VideoPathManager for video discovery
- `api.py` - Integrated VideoPathManager for upload handling

### 3. Docker Configuration
- **Dockerfile**: Creates all necessary directories with proper permissions
- **docker-compose.https.yml**: Mounts `test_videos/` directory for test storage
- **Environment variables**: CUDA suppression at container level

### 4. Testing Framework
- Configurable via `MAX_TEST_VIDEOS` environment variable
- Supports labeled (real/fake) and unlabeled videos
- Shows where videos are found
- Progress tracking and detailed reporting

## Setup Steps (One-Time)

### Step 1: Pull Latest Changes
```bash
git pull origin master
```

### Step 2: Run Setup Script
```bash
# On your server (use python3, not python)
cd ~/secureai-deepfake-detection
python3 setup_video_management.py
```

This will:
- Create all necessary directories
- Verify VideoPathManager is working
- Check Docker configuration
- Set proper permissions

### Step 3: Rebuild Container (if needed)
```bash
# Rebuild to include new directories and VideoPathManager
docker compose -f docker-compose.https.yml build secureai-backend

# Restart to apply changes
docker compose -f docker-compose.https.yml up -d secureai-backend
```

### Step 4: Copy Updated Files to Container
```bash
# Copy VideoPathManager
docker cp utils/video_paths.py secureai-backend:/app/utils/

# Copy updated test script
docker cp test_ensemble_comprehensive.py secureai-backend:/app/

# Copy updated detect.py
docker cp ai_model/detect.py secureai-backend:/app/ai_model/
```

## Adding Videos for Future Testing

### Method 1: Via Web Interface (Recommended for Production)
1. Upload videos through the web interface
2. Videos automatically saved to `uploads/` directory
3. Accessible for testing immediately

### Method 2: Direct File Copy (For Testing)
```bash
# Copy videos to uploads (accessible to container via volume mount)
cp /path/to/videos/*.mp4 ~/secureai-deepfake-detection/uploads/

# Or copy to test_videos (dedicated test storage)
cp /path/to/videos/*.mp4 ~/secureai-deepfake-detection/test_videos/
```

### Method 3: Labeled Test Sets (For Accuracy Testing)
```bash
# Create labeled directories
mkdir -p ~/secureai-deepfake-detection/test_videos/real
mkdir -p ~/secureai-deepfake-detection/test_videos/fake

# Copy real videos
cp /path/to/real/*.mp4 ~/secureai-deepfake-detection/test_videos/real/

# Copy fake videos  
cp /path/to/fake/*.mp4 ~/secureai-deepfake-detection/test_videos/fake/
```

## Running Tests (Now and Future)

### Basic Test
```bash
docker exec secureai-backend python /app/test_ensemble_comprehensive.py
```

### Test with More Videos
```bash
docker exec secureai-backend bash -c "MAX_TEST_VIDEOS=50 python /app/test_ensemble_comprehensive.py"
```

### Test with Error Suppression
```bash
docker exec secureai-backend bash -c "MAX_TEST_VIDEOS=20 python /app/test_ensemble_comprehensive.py 2>&1 | grep -v 'CUDA error' | grep -v 'cuInit' | grep -v 'stream_executor'"
```

## How It Works

1. **Video Discovery**: VideoPathManager searches multiple locations automatically
2. **Path Resolution**: `detect_fake()` uses VideoPathManager to find videos
3. **Testing**: Test script uses VideoPathManager to discover all available videos
4. **Storage**: Videos persist in mounted volumes (survive container restarts)

## Benefits

✅ **Reliable**: Works consistently across environments  
✅ **Flexible**: Supports multiple storage locations  
✅ **Maintainable**: Centralized path management  
✅ **Scalable**: Easy to add new storage backends  
✅ **Future-proof**: Handles container and local environments  
✅ **User-friendly**: Automatic directory creation  
✅ **Testing-ready**: Built-in support for test videos  

## Maintenance

### Adding New Videos
Just copy videos to `uploads/` or `test_videos/` - they'll be automatically discovered.

### Changing Test Settings
Set `MAX_TEST_VIDEOS` environment variable (default: 20).

### Adding New Storage Locations
Edit `utils/video_paths.py` and add to `VIDEO_STORAGE_LOCATIONS` list.

## Verification

After setup, verify everything works:

```bash
# 1. Check VideoPathManager
docker exec secureai-backend python -c "
from utils.video_paths import get_video_path_manager
pm = get_video_path_manager()
print(f'Uploads: {pm.get_uploads_directory()}')
videos = pm.find_all_videos(max_count=5)
print(f'Found {len(videos)} videos')
"

# 2. Run test
docker exec secureai-backend python /app/test_ensemble_comprehensive.py
```

This solution will work reliably for all future testing and production use.

