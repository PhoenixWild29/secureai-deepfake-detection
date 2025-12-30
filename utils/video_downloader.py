"""
Video download utility for URL-based video analysis
Supports YouTube, Twitter/X, and direct video URLs
"""
import os
import subprocess
import tempfile
import re
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

def is_valid_video_url(url: str) -> bool:
    """Validate if URL is a valid video URL"""
    if not url or not isinstance(url, str):
        return False
    
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # Check for direct video file extensions
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']
        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in video_extensions):
            return True
        
        # Check for supported platforms
        supported_domains = [
            'youtube.com', 'youtu.be', 'm.youtube.com',
            'twitter.com', 'x.com', 'mobile.twitter.com',
            'vimeo.com', 'dailymotion.com', 'tiktok.com',
            'instagram.com', 'facebook.com', 'fb.com'
        ]
        
        domain = parsed.netloc.lower().replace('www.', '')
        return any(domain == sd or domain.endswith('.' + sd) for sd in supported_domains)
    except Exception as e:
        logger.error(f"URL validation error: {e}")
        return False

def download_video_from_url(url: str, output_dir: str = None) -> tuple[str, str]:
    """
    Download video from URL using yt-dlp
    
    Args:
        url: Video URL to download
        output_dir: Directory to save video (default: temp directory)
    
    Returns:
        tuple: (filepath, filename)
    
    Raises:
        Exception: If download fails
    """
    if not is_valid_video_url(url):
        raise ValueError(f"Invalid video URL: {url}")
    
    if output_dir is None:
        output_dir = tempfile.gettempdir()
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate unique filename
    import uuid
    unique_id = str(uuid.uuid4())
    output_template = os.path.join(output_dir, f"{unique_id}.%(ext)s")
    
    try:
        # Try to find yt-dlp executable
        # On Windows, it might not be in PATH, so try multiple methods
        import sys
        import shutil
        
        yt_dlp_cmd = None
        
        # Try 1: Use sys.executable first (same Python that's running the backend)
        # This ensures we use the same Python environment (including venv)
        try:
            # Test if yt_dlp module is available in current Python
            import yt_dlp
            yt_dlp_cmd = [sys.executable, '-m', 'yt_dlp']
        except ImportError:
            # Try 2: Direct command (if in PATH)
            if shutil.which('yt-dlp'):
                yt_dlp_cmd = 'yt-dlp'
            # Try 3: Python module form with system Python
            elif shutil.which('python'):
                yt_dlp_cmd = ['python', '-m', 'yt_dlp']
            # Try 4: Windows Python launcher
            elif shutil.which('py'):
                yt_dlp_cmd = ['py', '-m', 'yt_dlp']
            else:
                raise FileNotFoundError("yt-dlp not found. Please install: pip install yt-dlp")
        
        # Use yt-dlp to download video
        # Format: best video quality, prefer mp4
        if isinstance(yt_dlp_cmd, str):
            cmd = [
                yt_dlp_cmd,
                '--format', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '--merge-output-format', 'mp4',
                '--output', output_template,
                '--no-playlist',
                '--quiet',
                '--no-warnings',
                url
            ]
        else:
            cmd = yt_dlp_cmd + [
                '--format', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '--merge-output-format', 'mp4',
                '--output', output_template,
                '--no-playlist',
                '--quiet',
                '--no-warnings',
                url
            ]
        
        logger.info(f"Downloading video from URL: {url}")
        logger.info(f"Using command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            logger.error(f"yt-dlp error output: {error_msg}")
            raise Exception(f"Video download failed: {error_msg}")
        
        # Find the downloaded file
        # yt-dlp outputs the filename, but we need to find it
        # Check for files matching our pattern
        import glob
        pattern = os.path.join(output_dir, f"{unique_id}.*")
        files = glob.glob(pattern)
        
        if not files:
            # Try to get filename from yt-dlp output
            # Sometimes yt-dlp doesn't output the filename, so we check the directory
            all_files = [f for f in os.listdir(output_dir) if f.startswith(unique_id)]
            if all_files:
                filepath = os.path.join(output_dir, all_files[0])
            else:
                raise Exception("Downloaded file not found")
        else:
            filepath = files[0]
        
        if not os.path.exists(filepath):
            raise Exception("Downloaded file does not exist")
        
        filename = os.path.basename(filepath)
        logger.info(f"Successfully downloaded video: {filename}")
        
        return filepath, filename
        
    except subprocess.TimeoutExpired:
        raise Exception("Video download timed out (5 minutes)")
    except FileNotFoundError:
        raise Exception("yt-dlp not found. Please install: pip install yt-dlp")
    except Exception as e:
        logger.error(f"Video download error: {e}")
        raise Exception(f"Failed to download video: {str(e)}")

def download_direct_video(url: str, output_dir: str = None) -> tuple[str, str]:
    """
    Download direct video file from URL (for .mp4, .avi, etc.)
    
    Args:
        url: Direct video URL
        output_dir: Directory to save video
    
    Returns:
        tuple: (filepath, filename)
    """
    import requests
    import uuid
    
    if output_dir is None:
        output_dir = tempfile.gettempdir()
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Get file extension from URL
    parsed = urlparse(url)
    path = parsed.path.lower()
    ext = '.mp4'  # default
    for video_ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
        if path.endswith(video_ext):
            ext = video_ext
            break
    
    unique_id = str(uuid.uuid4())
    filename = f"{unique_id}{ext}"
    filepath = os.path.join(output_dir, filename)
    
    try:
        logger.info(f"Downloading direct video from URL: {url}")
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        if 'video' not in content_type.lower() and not path.endswith(tuple(['.mp4', '.avi', '.mov', '.mkv', '.webm'])):
            raise ValueError(f"URL does not appear to be a video (content-type: {content_type})")
        
        # Download with progress
        total_size = int(response.headers.get('content-length', 0))
        max_size = 500 * 1024 * 1024  # 500MB limit
        
        if total_size > max_size:
            raise ValueError(f"Video file too large: {total_size / (1024*1024):.1f}MB (max: 500MB)")
        
        with open(filepath, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0 and downloaded > max_size:
                        os.remove(filepath)
                        raise ValueError("Video file exceeds size limit during download")
        
        logger.info(f"Successfully downloaded direct video: {filename}")
        return filepath, filename
        
    except requests.exceptions.RequestException as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        raise Exception(f"Failed to download video: {str(e)}")
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        raise

