# 🔄 How to Restart Backend Server

## Quick Method (Recommended)

### Step 1: Stop the Current Server
1. **Go to the backend terminal window** (where `py api.py` is running)
2. **Press `Ctrl+C`** to stop the server
3. Wait for it to fully stop (you'll see the command prompt return)

### Step 2: Restart the Server
In the same terminal window, run:
```bash
py api.py
```

---

## Alternative: Use the Batch Script

If you have `START_SERVER.bat` in the root directory:

1. **Stop the current server** (Ctrl+C)
2. **Double-click `START_SERVER.bat`** or run:
   ```bash
   START_SERVER.bat
   ```

---

## What Happens When You Restart

✅ Backend will:
- Load yt-dlp (newly installed)
- Initialize all models
- Start Flask server on port 5000
- Be ready to accept URL-based video analysis

---

## Verification

After restarting, you should see:
```
🚀 Starting SecureAI DeepFake Detection API...
📊 Web Interface: http://localhost:5000
🔗 API Endpoints: http://localhost:5000/api/*
```

---

## If You Get Errors

### "yt-dlp not found"
- Make sure yt-dlp is installed: `py -m pip install yt-dlp`
- Verify: `py -m yt_dlp --version`

### Port Already in Use
- Make sure you stopped the previous server (Ctrl+C)
- Check if another process is using port 5000
- Wait a few seconds after stopping before restarting

### Import Errors
- Make sure you're in the correct directory
- Check that `utils/video_downloader.py` exists

---

## Quick Restart Command

**In the backend terminal:**
1. Press `Ctrl+C` (to stop)
2. Press `↑` (up arrow) to get previous command
3. Press `Enter` (to restart)

Or simply type:
```bash
py api.py
```

---

**That's it!** After restarting, URL mode will be fully functional. 🚀

