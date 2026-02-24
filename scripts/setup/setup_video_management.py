#!/usr/bin/env python3
"""
Long-Term Video Management Setup
Ensures all directories are created and configured properly.
Run this once to set up the video management system.
"""
import os
import sys
from pathlib import Path

def setup_video_directories():
    """Create all necessary directories for video management"""
    print("🔧 Setting up long-term video management system...")
    print("=" * 70)
    
    directories = [
        'uploads',
        'test_videos',
        'test_videos/real',
        'test_videos/fake',
        'results',
        'logs',
    ]
    
    created = []
    existing = []
    
    for directory in directories:
        path = Path(directory)
        if path.exists():
            existing.append(directory)
            print(f"   ✅ {directory}/ (already exists)")
        else:
            try:
                path.mkdir(parents=True, exist_ok=True)
                created.append(directory)
                print(f"   ✅ Created {directory}/")
            except Exception as e:
                print(f"   ❌ Failed to create {directory}/: {e}")
    
    print(f"\n📊 Summary:")
    print(f"   Created: {len(created)} directories")
    print(f"   Existing: {len(existing)} directories")
    
    # Set permissions (Unix-like systems)
    if sys.platform != 'win32':
        for directory in directories:
            try:
                os.chmod(directory, 0o755)
            except:
                pass
    
    return len(created) > 0

def verify_video_path_manager():
    """Verify VideoPathManager is working"""
    print("\n🔍 Verifying VideoPathManager...")
    print("-" * 70)
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
        from video_paths import get_video_path_manager
        
        path_manager = get_video_path_manager()
        uploads_dir = path_manager.get_uploads_directory()
        
        print(f"   ✅ VideoPathManager initialized")
        print(f"   📁 Uploads directory: {uploads_dir}")
        print(f"   📁 Directory exists: {uploads_dir.exists()}")
        
        # Test path resolution
        test_paths = ['test.mp4', 'uploads/test.mp4', '/app/uploads/test.mp4']
        print(f"\n   Testing path resolution:")
        for test_path in test_paths:
            resolved = path_manager.resolve_video_path(test_path)
            if resolved:
                print(f"      ✅ {test_path} -> {resolved}")
            else:
                print(f"      ⚠️  {test_path} -> Not found (expected if file doesn't exist)")
        
        return True
    except ImportError as e:
        print(f"   ❌ VideoPathManager not available: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error verifying VideoPathManager: {e}")
        return False

def check_docker_volumes():
    """Check if running in Docker and verify volumes"""
    print("\n🐳 Checking Docker configuration...")
    print("-" * 70)
    
    in_docker = os.path.exists('/.dockerenv') or os.path.exists('/app')
    
    if in_docker:
        print("   ✅ Running in Docker container")
        
        # Check if volumes are mounted
        uploads_path = Path('/app/uploads')
        if uploads_path.exists():
            print(f"   ✅ /app/uploads is accessible")
            try:
                # Try to list files
                files = list(uploads_path.glob('*.mp4'))
                print(f"   📹 Found {len(files)} video files in /app/uploads")
            except:
                print(f"   ⚠️  Cannot read /app/uploads (permissions issue?)")
        else:
            print(f"   ⚠️  /app/uploads does not exist (volume may not be mounted)")
    else:
        print("   ℹ️  Running on host (not in Docker)")
        print("   ℹ️  Volumes will be mounted when container starts")
    
    return True

def main():
    """Main setup function"""
    print("\n" + "=" * 70)
    print("🚀 SecureAI Video Management - Long-Term Setup")
    print("=" * 70)
    
    # Setup directories
    dirs_created = setup_video_directories()
    
    # Verify VideoPathManager
    manager_ok = verify_video_path_manager()
    
    # Check Docker
    docker_ok = check_docker_volumes()
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 Setup Summary")
    print("=" * 70)
    
    if dirs_created or manager_ok:
        print("✅ Video management system is ready!")
        print("\n📝 Next steps:")
        print("   1. Add videos to uploads/ or test_videos/ directories")
        print("   2. Run tests: python test_ensemble_comprehensive.py")
        print("   3. Videos will be automatically discovered and tested")
    else:
        print("⚠️  Some setup steps may need attention")
        print("   Check the output above for details")
    
    print("\n💡 For future testing:")
    print("   - Add videos to: uploads/ or test_videos/")
    print("   - Videos are automatically discovered")
    print("   - Use MAX_TEST_VIDEOS env var to control test size")
    print("   - See LONG_TERM_VIDEO_MANAGEMENT.md for details")

if __name__ == "__main__":
    main()

