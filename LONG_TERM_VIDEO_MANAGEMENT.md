# Long-Term Video Management Solution

## Overview

This document describes the comprehensive, long-term solution for video file management, testing, and path resolution in the SecureAI DeepFake Detection system.

## Components

### 1. VideoPathManager (`utils/video_paths.py`)

**Purpose**: Centralized, reliable video path resolution and discovery.

**Features**:
- Automatically finds or creates uploads directory
- Searches multiple standard locations
- Handles both relative and absolute paths
- Provides consistent API for video discovery
- Works in Docker containers and local environments

**Usage**:
```python
from utils.video_paths import get_video_path_manager

path_manager = get_video_path_manager()

# Resolve a video path
video_path = path_manager.resolve_video_path('my_video.mp4')

# Find all videos
all_videos = path_manager.find_all_videos(max_count=50)

# Get uploads directory
uploads_dir = path_manager.get_uploads_directory()
```

### 2. Updated `detect_fake()` Function

**Changes**:
- Uses VideoPathManager for path resolution
- Handles path resolution automatically
- Provides clear error messages
- Works consistently across environments

### 3. Updated Testing Framework

**Changes**:
- Uses VideoPathManager for video discovery
- Configurable via `MAX_TEST_VIDEOS` environment variable
- Supports labeled (real/fake) and unlabeled videos
- Shows where videos are found

### 4. Docker Configuration

**Dockerfile**:
- Creates `uploads/`, `results/`, `logs/`, `run/`, and `test_videos/` directories
- Sets proper permissions
- Ensures directories exist at build time

**docker-compose.https.yml**:
- Mounts `./uploads:/app/uploads` (persistent storage)
- Mounts `./test_videos:/app/test_videos` (test video storage)
- Ensures volumes are properly mounted

## Directory Structure

```
secureai-deepfake-detection/
├── uploads/              # User-uploaded videos (mounted to container)
├── test_videos/          # Test videos for benchmarking (mounted to container)
│   ├── real/            # Labeled real videos (optional)
│   └── fake/            # Labeled fake videos (optional)
├── results/              # Analysis results
├── datasets/             # Training/test datasets
│   ├── train/
│   ├── val/
│   └── unified_deepfake/
└── utils/
    └── video_paths.py    # VideoPathManager utility
```

## Adding Videos for Testing

### Method 1: Via Web Interface (Production)
1. Upload videos through the web interface
2. Videos are automatically saved to `uploads/` directory
3. Accessible via VideoPathManager

### Method 2: Direct File Copy (Testing)
```bash
# On your server
# Copy videos to uploads directory
cp /path/to/videos/*.mp4 ~/secureai-deepfake-detection/uploads/

# Or copy to test_videos directory
cp /path/to/videos/*.mp4 ~/secureai-deepfake-detection/test_videos/
```

### Method 3: Labeled Test Videos
```bash
# Create labeled test sets
mkdir -p ~/secureai-deepfake-detection/test_videos/real
mkdir -p ~/secureai-deepfake-detection/test_videos/fake

# Copy real videos
cp /path/to/real/*.mp4 ~/secureai-deepfake-detection/test_videos/real/

# Copy fake videos
cp /path/to/fake/*.mp4 ~/secureai-deepfake-detection/test_videos/fake/
```

## Running Tests

### Basic Test
```bash
# Test with default settings (up to 20 videos)
docker exec secureai-backend python /app/test_ensemble_comprehensive.py
```

### Custom Number of Videos
```bash
# Test with more videos
docker exec secureai-backend bash -c "MAX_TEST_VIDEOS=50 python /app/test_ensemble_comprehensive.py"
```

### With Error Suppression
```bash
# Suppress CUDA errors (harmless, but noisy)
docker exec secureai-backend bash -c "MAX_TEST_VIDEOS=20 python /app/test_ensemble_comprehensive.py 2>&1 | grep -v 'CUDA error' | grep -v 'cuInit' | grep -v 'stream_executor'"
```

## Environment Variables

- `MAX_TEST_VIDEOS`: Maximum number of videos to test (default: 20)
- `CUDA_VISIBLE_DEVICES`: Set to `""` to force CPU mode (set in Dockerfile)
- `TF_CPP_MIN_LOG_LEVEL`: Set to `2` or `3` to suppress TensorFlow messages

## Path Resolution Order

VideoPathManager searches in this order:
1. `/app/uploads` (container mount point)
2. `uploads` (relative path)
3. `./uploads` (current directory)
4. `~/secureai-deepfake-detection/uploads` (user home)
5. Test video locations (if applicable)

## Benefits of This Solution

1. **Reliability**: Works consistently across environments
2. **Flexibility**: Supports multiple storage locations
3. **Maintainability**: Centralized path management
4. **Scalability**: Easy to add new storage locations
5. **Future-proof**: Handles container and local environments
6. **User-friendly**: Automatic directory creation
7. **Testing-ready**: Built-in support for test videos

## Maintenance

### Adding New Storage Locations

Edit `utils/video_paths.py`:
```python
VIDEO_STORAGE_LOCATIONS = [
    '/app/uploads',
    'uploads',
    # Add your new location here
    '/custom/storage/path',
]
```

### Changing Default Test Video Count

Set environment variable in docker-compose:
```yaml
environment:
  - MAX_TEST_VIDEOS=50
```

## Troubleshooting

### Videos Not Found

1. Check if uploads directory exists:
   ```bash
   docker exec secureai-backend ls -la /app/uploads/
   ```

2. Verify volume mount:
   ```bash
   docker inspect secureai-backend | grep -A 5 Mounts
   ```

3. Check VideoPathManager logs:
   ```bash
   docker exec secureai-backend python -c "from utils.video_paths import get_video_path_manager; pm = get_video_path_manager(); print(f'Uploads: {pm.get_uploads_directory()}')"
   ```

### Adding Videos Doesn't Work

1. Ensure directory exists on host:
   ```bash
   mkdir -p ~/secureai-deepfake-detection/uploads
   ```

2. Restart container to remount:
   ```bash
   docker compose -f docker-compose.https.yml restart secureai-backend
   ```

3. Check permissions:
   ```bash
   ls -la ~/secureai-deepfake-detection/uploads/
   ```

## Future Enhancements

1. **S3 Integration**: VideoPathManager can be extended to check S3 buckets
2. **Database Tracking**: Track video locations in database
3. **Automatic Cleanup**: Remove old test videos automatically
4. **Video Validation**: Validate video files before processing
5. **Metadata Storage**: Store video metadata for faster discovery

