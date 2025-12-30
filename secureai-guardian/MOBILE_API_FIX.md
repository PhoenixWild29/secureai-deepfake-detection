# 📱 Mobile API Connection Fix

## Problem
When accessing the app from a mobile device, API calls fail with "Backend service unavailable" because the frontend tries to connect to `localhost:5000`, which on mobile refers to the phone itself, not your computer.

## Solution Applied

### ✅ Updated API Service to Use Relative URLs
- Changed `apiService.ts` to use relative URLs (`''`) in development mode
- This makes API calls go through the Vite proxy
- The Vite proxy forwards `/api` requests to your backend server
- Works from any device on the network!

### How It Works

**Before (Broken on Mobile):**
```
Phone → http://localhost:5000/api/analyze ❌ (tries to reach phone's localhost)
```

**After (Fixed):**
```
Phone → http://10.0.0.168:3000/api/analyze 
      → Vite Proxy (on your computer)
      → http://localhost:5000/api/analyze ✅ (reaches your computer's backend)
```

---

## What Changed

### `services/apiService.ts`
```typescript
// OLD (broken on mobile):
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

// NEW (works on mobile):
const API_BASE_URL = import.meta.env.DEV 
  ? '' // Use relative URLs in dev (goes through Vite proxy)
  : (import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000');
```

---

## Testing

1. **Restart the frontend server** (if it's running):
   ```cmd
   cd secureai-guardian
   npm run dev
   ```

2. **Refresh your phone browser**

3. **Try uploading a video** - it should now work!

---

## How to Verify

1. Open browser console on your phone (if possible)
2. Check network requests - they should go to `http://10.0.0.168:3000/api/...`
3. The Vite proxy will automatically forward to your backend

---

## Important Notes

- ✅ **Backend must be running** on your computer (port 5000)
- ✅ **Frontend must be running** on your computer (port 3000)
- ✅ **Vite proxy is configured** in `vite.config.ts` to forward `/api` requests
- ✅ **Both devices on same network** (phone and computer)

---

## If It Still Doesn't Work

1. **Check backend is running:**
   ```cmd
   py api.py
   ```

2. **Check frontend is running:**
   ```cmd
   cd secureai-guardian
   npm run dev
   ```

3. **Verify Vite proxy is working:**
   - On your phone, try: `http://10.0.0.168:3000/api/health`
   - Should return backend health status

4. **Check backend is accessible:**
   - On your computer, try: `http://localhost:5000/api/health`
   - Should return `{"status": "healthy"}`

---

**The fix is applied! Restart the frontend server and try again on your phone.** 📱✨

