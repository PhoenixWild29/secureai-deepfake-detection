#!/usr/bin/env python3
"""
AIStore Integration for Distributed Video Storage
Provides blockchain-like distributed storage for video datasets
"""
import os
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List

# Try to import aistore, but make it optional
try:
    import aistore as ais
    AISTORE_AVAILABLE = True
except ImportError:
    AISTORE_AVAILABLE = False
    ais = None
    print("[WARNING] AIStore library not available. Running in local storage mode only.")

class AIStoreManager:
    """Manages distributed storage using AIStore"""

    def __init__(self, endpoint: str = "http://localhost:8080", bucket_name: str = "secureai-videos"):
        """
        Initialize AIStore connection

        Args:
            endpoint: AIStore endpoint URL
            bucket_name: Name of the bucket to use
        """
        self.endpoint = endpoint
        self.bucket_name = bucket_name
        self.client = None
        self.bucket = None

        # Try to connect to AIStore
        if AISTORE_AVAILABLE:
            try:
                self.client = ais.Client(endpoint)
                self.bucket = self.client.bucket(bucket_name)
                print(f"[OK] Connected to AIStore at {endpoint}")
            except Exception as e:
                print(f"[WARNING] AIStore not available: {e}")
                print("   Running in local storage mode only")
        else:
            print("[WARNING] AIStore library not installed. Running in local storage mode only.")

    def is_available(self) -> bool:
        """Check if AIStore is available"""
        return self.client is not None and self.bucket is not None

    def store_video(self, video_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Store a video file in distributed storage

        Args:
            video_path: Local path to video file
            metadata: Additional metadata to store

        Returns:
            Storage information including hash and distributed URLs
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Calculate video hash
        with open(video_path, 'rb') as f:
            video_hash = hashlib.sha256(f.read()).hexdigest()

        result = {
            'video_hash': video_hash,
            'original_path': video_path,
            'filename': os.path.basename(video_path),
            'file_size': os.path.getsize(video_path),
            'stored_distributed': False,
            'distributed_urls': [],
            'metadata': metadata or {}
        }

        if self.is_available():
            try:
                # Store in AIStore with hash as key
                object_name = f"{video_hash}_{os.path.basename(video_path)}"

                # Get object instance and upload file
                obj = self.bucket.object(object_name)
                obj.put_file(video_path)

                # Get object info
                object_info = obj.head()

                # Get distributed URLs (AIStore provides multiple replica URLs)
                distributed_urls = []

                # Try to get URLs from object properties
                try:
                    urls = obj.get_url()
                    if isinstance(urls, list):
                        distributed_urls = urls
                    else:
                        distributed_urls = [urls]
                except:
                    # Fallback: construct URL from known pattern
                    distributed_urls = [f"{self.endpoint}/v1/objects/{self.bucket_name}/{object_name}"]

                result.update({
                    'stored_distributed': True,
                    'distributed_urls': distributed_urls,
                    'aistore_object': object_name,
                    'storage_type': 'distributed'
                })

                print(f"✅ Stored video in AIStore: {object_name}")

            except Exception as e:
                print(f"⚠️  Failed to store in AIStore: {e}")
                result['storage_type'] = 'local_only'

        else:
            result['storage_type'] = 'local_only'
            print("ℹ️  AIStore not available, using local storage only")

        return result

    def retrieve_video(self, video_hash: str, local_path: str) -> bool:
        """
        Retrieve a video from distributed storage

        Args:
            video_hash: SHA256 hash of the video
            local_path: Where to save the retrieved video

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            print("❌ AIStore not available for retrieval")
            return False

        try:
            # Find object by hash pattern
            bucket_list = self.bucket.list_objects(prefix=f"{video_hash}_")
            if not bucket_list.entries:
                print(f"❌ Video not found in AIStore: {video_hash}")
                return False

            # Get the first matching object
            object_name = bucket_list.entries[0].name

            # Get object and download to local path
            obj = self.bucket.object(object_name)
            reader = obj.get_reader()
            content = reader.read_all()
            
            # Write content to file
            with open(local_path, 'wb') as f:
                f.write(content)

            print(f"✅ Retrieved video from AIStore: {object_name}")
            return True

        except Exception as e:
            print(f"❌ Failed to retrieve from AIStore: {e}")
            return False

    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about the storage system"""
        info = {
            'storage_type': 'local_only',
            'endpoint': None,
            'bucket': None,
            'available': False
        }

        if self.is_available():
            try:
                bucket_info = self.bucket.info()
                info.update({
                    'storage_type': 'distributed',
                    'endpoint': self.endpoint,
                    'bucket': self.bucket_name,
                    'available': True,
                    'bucket_info': bucket_info
                })
            except Exception as e:
                print(f"⚠️  Could not get bucket info: {e}")

        return info

    def list_videos(self) -> List[Dict[str, Any]]:
        """List videos stored in the system"""
        videos = []

        if self.is_available():
            try:
                objects = self.bucket.list_objects()
                for obj in objects.entries:
                    videos.append({
                        'name': obj.name,
                        'size': obj.size,
                        'hash': obj.name.split('_')[0] if '_' in obj.name else 'unknown',
                        'storage_type': 'distributed'
                    })
            except Exception as e:
                print(f"⚠️  Could not list distributed videos: {e}")

        # Also check local storage
        local_videos_dir = Path('uploads')
        if local_videos_dir.exists():
            for video_file in local_videos_dir.glob('*.mp4'):
                videos.append({
                    'name': video_file.name,
                    'size': video_file.stat().st_size,
                    'hash': 'local',
                    'storage_type': 'local'
                })

        return videos

# Global instance for easy access
aistore_manager = AIStoreManager()

def store_video_distributed(video_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience function to store video in distributed storage"""
    return aistore_manager.store_video(video_path, metadata)

def retrieve_video_distributed(video_hash: str, local_path: str) -> bool:
    """Convenience function to retrieve video from distributed storage"""
    return aistore_manager.retrieve_video(video_hash, local_path)

def get_storage_status() -> Dict[str, Any]:
    """Get current storage system status"""
    return aistore_manager.get_storage_info()

if __name__ == "__main__":
    # Test the integration
    print("🔍 Testing AIStore Integration...")

    # Check storage status
    status = get_storage_status()
    print(f"Storage Status: {status}")

    # List available videos
    videos = aistore_manager.list_videos()
    print(f"Available Videos: {len(videos)}")
    for video in videos[:5]:  # Show first 5
        print(f"  - {video['name']} ({video['storage_type']})")

    print("✅ AIStore integration test completed")