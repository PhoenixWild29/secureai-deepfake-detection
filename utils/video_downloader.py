"""
Video download utility for URL-based video analysis
Supports YouTube, Twitter/X, and direct video URLs
"""
import os
import subprocess
import tempfile
import re
import socket
import ipaddress
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


def _is_blocked_ip(ip_str: str) -> bool:
    """
    SSRF GUARD: return True if an IP belongs to a private/internal/reserved range
    that must never be reachable from a user-supplied URL.

    Blocks (IPv4 and IPv6): loopback (127.0.0.0/8, ::1), private RFC1918
    (10/8, 172.16/12, 192.168/16), link-local (169.254/16, fe80::/10),
    unique-local IPv6 (fc00::/7), and other reserved/unspecified/multicast
    ranges. Explicitly blocks the cloud metadata IP 169.254.169.254.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        # Not parseable as an IP -> treat as unsafe.
        return True

    # Explicit cloud metadata endpoint (AWS/GCP/Azure/etc.).
    if ip_str == '169.254.169.254':
        return True

    # ipaddress flags cover loopback, private, link-local, reserved,
    # multicast, and unspecified for both IPv4 and IPv6.
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        return True

    # fc00::/7 (IPv6 unique-local) — covered by is_private, but be explicit.
    if isinstance(ip, ipaddress.IPv6Address) and ip in ipaddress.ip_network('fc00::/7'):
        return True

    return False


def _hostname_resolves_to_blocked(hostname: str) -> bool:
    """
    SSRF GUARD: resolve a hostname and reject if ANY resolved address falls in a
    blocked range. This prevents DNS-rebinding-style bypasses where a public
    hostname maps to an internal/loopback IP.
    """
    try:
        # getaddrinfo returns all A/AAAA records for the host.
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        # Unresolvable host -> reject.
        return True

    for info in infos:
        ip_str = info[4][0]
        if _is_blocked_ip(ip_str):
            return True
    return False


def is_valid_video_url(url: str) -> bool:
    """Validate if URL is a valid, SAFE video URL.

    SECURITY (SSRF hardening): in addition to format/platform checks, this now:
      * requires an http/https scheme (blocks file://, gopher://, etc.),
      * rejects URLs whose host is a private/loopback/link-local/reserved IP,
      * resolves hostnames and rejects them if they map to a blocked IP,
      * explicitly blocks the cloud metadata IP 169.254.169.254.

    Optional allowlist hook: set ALLOWED_DOWNLOAD_HOSTS (comma-separated host
    suffixes) to restrict downloads to specific hosts. Default behavior is to
    block private/internal targets but otherwise allow public hosts.
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url)

        # SECURITY: only allow web schemes; reject file/ftp/gopher/etc.
        if parsed.scheme not in ('http', 'https'):
            return False
        if not parsed.netloc or not parsed.hostname:
            return False

        hostname = parsed.hostname.lower()

        # Optional allowlist: if configured, host must match one of the suffixes.
        allowlist_raw = os.getenv('ALLOWED_DOWNLOAD_HOSTS', '').strip()
        if allowlist_raw:
            allowed = [h.strip().lower() for h in allowlist_raw.split(',') if h.strip()]
            if not any(hostname == a or hostname.endswith('.' + a) for a in allowed):
                logger.warning("URL host %s not in ALLOWED_DOWNLOAD_HOSTS", hostname)
                return False

        # SSRF GUARD: if the host is itself a literal IP, validate it directly.
        try:
            ipaddress.ip_address(hostname)
            if _is_blocked_ip(hostname):
                logger.warning("Blocked URL with private/internal IP host: %s", hostname)
                return False
        except ValueError:
            # Hostname (not a literal IP): resolve and reject if it maps internal.
            if _hostname_resolves_to_blocked(hostname):
                logger.warning("Blocked URL whose host resolves to internal IP: %s", hostname)
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

def download_video_from_url(
    url: str,
    output_dir: str = None,
    timeout_seconds: int = 300,
    cookies_file: str | None = None
) -> tuple[str, str]:
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

        # Optional cookies for sites that require auth (e.g., X/Twitter)
        if cookies_file:
            # Copy cookies to writable temp location to avoid read-only filesystem error
            # yt-dlp tries to save cookies back, so we need a writable copy
            import shutil
            temp_cookies = os.path.join(tempfile.gettempdir(), f"cookies_{unique_id}.txt")
            original_cookies = cookies_file
            try:
                # Ensure temp directory exists
                os.makedirs(os.path.dirname(temp_cookies), exist_ok=True)
                # Copy cookies file to writable location
                shutil.copy2(original_cookies, temp_cookies)
                # Verify copy succeeded
                if not os.path.exists(temp_cookies):
                    raise Exception(f"Failed to create temp cookies file: {temp_cookies}")
                cookies_file = temp_cookies
                logger.info(f"Copied cookies from {original_cookies} to {temp_cookies}")
            except Exception as e:
                logger.error(f"Could not copy cookies file to temp: {e}")
                # If copy fails, try without cookies (will likely fail for X, but better than crashing)
                logger.warning(f"Using original cookies file (may fail if read-only): {original_cookies}")
                cookies_file = original_cookies
            # Use cookies file - use temp copy so yt-dlp can write to it if needed
            # (temp file is writable, original is read-only)
            cmd = cmd[:-1] + ['--cookies', cookies_file] + [cmd[-1]]
        
        logger.info(f"Downloading video from URL: {url}")
        logger.info(f"Using command: {' '.join(cmd)}")
        if cookies_file and cookies_file != original_cookies:
            logger.info(f"Using temp cookies file: {cookies_file} (original: {original_cookies})")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds
        )
        
        # Clean up temp cookies file if we created one
        if cookies_file and cookies_file != original_cookies and os.path.exists(cookies_file):
            try:
                os.remove(cookies_file)
                logger.debug(f"Cleaned up temp cookies file: {cookies_file}")
            except Exception as e:
                logger.warning(f"Could not clean up temp cookies file: {e}")
        
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
        raise Exception(f"Video download timed out ({timeout_seconds} seconds)")
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

    # SECURITY (SSRF): validate the URL (scheme + private/internal IP block)
    # BEFORE issuing any outbound request to the user-supplied target.
    if not is_valid_video_url(url):
        raise ValueError(f"Invalid or disallowed video URL: {url}")

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

