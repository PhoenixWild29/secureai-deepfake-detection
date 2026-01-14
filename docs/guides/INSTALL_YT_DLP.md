# 📥 Install yt-dlp for URL Mode

## Quick Install

```bash
pip install yt-dlp
```

## What is yt-dlp?

`yt-dlp` is a command-line program to download videos from YouTube and many other sites. It's required for the STREAM_INTEL (URL mode) feature to work.

## Installation Steps

### 1. Install yt-dlp

**Windows (PowerShell/CMD):**
```bash
pip install yt-dlp
```

**Or install all requirements:**
```bash
pip install -r requirements.txt
```

### 2. Verify Installation

```bash
yt-dlp --version
```

Should output something like: `2023.12.30` or similar

### 3. Restart Backend

After installing, restart your backend server:

```bash
# Stop backend (Ctrl+C)
py api.py
```

## Troubleshooting

### "yt-dlp not found" Error

**Solution:** Install yt-dlp:
```bash
pip install yt-dlp
```

### "Command not recognized"

**Solution:** Make sure Python and pip are in your PATH, or use:
```bash
python -m pip install yt-dlp
```

### Permission Errors

**Solution:** Use `--user` flag:
```bash
pip install --user yt-dlp
```

## What yt-dlp Does

- Downloads videos from YouTube, Twitter/X, Vimeo, etc.
- Extracts video in best quality
- Converts to MP4 format
- Handles authentication for private videos (if credentials provided)

## After Installation

1. ✅ Install yt-dlp: `pip install yt-dlp`
2. ✅ Restart backend: `py api.py`
3. ✅ Test URL mode in frontend

---

**Once installed, URL mode (STREAM_INTEL) will be fully functional!** 🚀

