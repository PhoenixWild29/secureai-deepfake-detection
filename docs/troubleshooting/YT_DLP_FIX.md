# 🔧 Fix: yt-dlp Not Found Error

## Problem
When trying to analyze a video from X (Twitter) or other platforms, you get:
```
Video download failed: yt-dlp not found. Please install: pip install yt-dlp
```

## Solution Applied

### ✅ Updated Video Downloader to Find yt-dlp
The code now tries multiple methods to find and run `yt-dlp`:

1. **Direct command** (`yt-dlp`) - if in PATH
2. **Python module** (`python -m yt_dlp`) - if installed via pip
3. **Windows Python launcher** (`py -m yt_dlp`) - Windows-specific

### What Changed

**File:** `utils/video_downloader.py`

The code now:
- Checks if `yt-dlp` is available in multiple ways
- Uses the Python module form if the command isn't in PATH
- Provides better error messages

---

## Next Steps

### 1. Restart Backend Server

**IMPORTANT:** You must restart the backend server for the changes to take effect!

1. **Stop the backend server** (press `Ctrl+C` in the backend terminal)

2. **Restart it:**
   ```cmd
   py api.py
   ```

3. **Try the video URL again** on your desktop browser

---

## Verify yt-dlp is Installed

If you still get errors, verify `yt-dlp` is installed:

```cmd
py -m pip show yt-dlp
```

If it's not installed, install it:
```cmd
py -m pip install yt-dlp
```

---

## Testing

After restarting the backend:

1. Go to the **Forensics** page
2. Select **STREAM_INTEL** tab
3. Enter a video URL (e.g., from X/Twitter, YouTube)
4. Click **"Authorize Multi-Layer Analysis"**

It should now work! ✅

---

## If It Still Doesn't Work

1. **Check backend logs** - Look for error messages
2. **Verify yt-dlp installation:**
   ```cmd
   py -m yt_dlp --version
   ```
3. **Try installing yt-dlp again:**
   ```cmd
   py -m pip install --upgrade yt-dlp
   ```

---

**The fix is applied! Restart your backend server and try again.** 🔄

