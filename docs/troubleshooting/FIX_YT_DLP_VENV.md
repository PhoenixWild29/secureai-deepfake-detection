# 🔧 Fix: yt-dlp Not Found in Virtual Environment

## Problem
Error: `No module named yt_dlp`

The backend is running in a virtual environment (`.venv`), but `yt-dlp` is not installed there.

## Solution

### Option 1: Run the Installation Script (Easiest)

**Double-click:** `INSTALL_YT_DLP_IN_VENV.bat`

This will:
- Detect your virtual environment
- Install `yt-dlp` in the correct environment
- Verify the installation

### Option 2: Manual Installation

**If using virtual environment:**
```cmd
.venv\Scripts\python.exe -m pip install yt-dlp
```

**If NOT using virtual environment:**
```cmd
py -m pip install yt-dlp
```

---

## After Installation

### ⚠️ IMPORTANT: Restart Backend Server

1. **Stop the backend server** (press `Ctrl+C` in the backend terminal)

2. **Restart it:**
   ```cmd
   py api.py
   ```
   OR if using venv:
   ```cmd
   .venv\Scripts\python.exe api.py
   ```

3. **Try the video URL again**

---

## Code Fix Applied

The code now:
- ✅ Uses `sys.executable` first (same Python as backend)
- ✅ Automatically detects if `yt-dlp` is installed
- ✅ Falls back to other methods if needed

---

## Verify Installation

After installing, verify it works:
```cmd
.venv\Scripts\python.exe -m yt_dlp --version
```

Should show: `2025.12.08` (or similar version)

---

**Install yt-dlp in your venv, then restart the backend server!** 🔄

