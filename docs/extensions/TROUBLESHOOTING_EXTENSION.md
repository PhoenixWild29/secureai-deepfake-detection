# Chrome Extension Troubleshooting Guide

## Common Errors

### "Failed to fetch" Error

This is the most common error and can have several causes:

#### 1. CORS Configuration Issue

**Symptoms:**
- Error: "Failed to fetch" or "NetworkError"
- Console shows CORS-related errors

**Solution:**
1. Check that the backend CORS is configured correctly:
   ```bash
   # On server, check CORS_ORIGINS environment variable
   docker exec secureai-backend env | grep CORS
   ```
   Should show: `CORS_ORIGINS=*` (allows all origins)

2. Check Nginx CORS headers:
   ```bash
   # Test CORS headers
   curl -I -X OPTIONS https://guardian.secureai.dev/api/analyze \
     -H "Origin: chrome-extension://your-extension-id" \
     -H "Access-Control-Request-Method: POST"
   ```
   Should return `Access-Control-Allow-Origin: *`

3. **If still failing**, the issue might be Content-Security-Policy. Check nginx config:
   ```nginx
   # In nginx.https.conf, the CSP should allow connections:
   add_header Content-Security-Policy "... connect-src 'self' ws: wss: https: ..." always;
   ```

#### 2. API Not Accessible

**Symptoms:**
- Error: "Cannot connect to https://guardian.secureai.dev"
- Health check fails

**Solution:**
1. Test API health endpoint:
   ```bash
   curl https://guardian.secureai.dev/api/health
   ```
   Should return: `{"status":"healthy",...}`

2. Check if server is running:
   ```bash
   # On server
   docker ps | grep secureai-backend
   ```

3. Check firewall/network:
   - Make sure port 443 is open
   - Check if SSL certificate is valid
   - Try accessing the API in a regular browser tab

#### 3. Video Download Failed

**Symptoms:**
- Error: "Failed to fetch video from X"
- Error: "Cannot download video from X"

**Solution:**
1. **Make sure you're logged into X:**
   - Open X in a new tab
   - Verify you're logged in
   - Try refreshing the X post page

2. **Check if video exists:**
   - Make sure the X post actually has a video (not just an image)
   - Try a different X post with a video

3. **X might be blocking the request:**
   - Try refreshing the X page
   - Log out and log back into X
   - Clear X cookies and log in again

#### 4. Extension Not Loading

**Symptoms:**
- Extension icon doesn't appear
- Popup doesn't open
- Service worker errors

**Solution:**
1. **Reload the extension:**
   - Go to `chrome://extensions/`
   - Find "SecureAI X Analyzer"
   - Click the reload icon (circular arrow)

2. **Check for errors:**
   - In `chrome://extensions/`, click "service worker" link
   - Check the console for errors
   - Right-click extension popup → Inspect → Check console

3. **Reinstall the extension:**
   - Remove the extension
   - Load unpacked again from `extensions/chrome-secureai-x-analyzer/`

## Debugging Steps

### Step 1: Check Extension Console

1. Open `chrome://extensions/`
2. Find "SecureAI X Analyzer"
3. Click "service worker" (or "background page" in Manifest V2)
4. Check console for errors

### Step 2: Check Popup Console

1. Right-click the extension icon
2. Select "Inspect popup"
3. Check console for errors

### Step 3: Test API Manually

1. Open browser DevTools (F12)
2. Go to Console tab
3. Run:
   ```javascript
   fetch('https://guardian.secureai.dev/api/health')
     .then(r => r.json())
     .then(console.log)
     .catch(console.error);
   ```
4. Should return: `{status: "healthy", ...}`

### Step 4: Test Video Extraction

1. Open an X post with a video
2. Open DevTools (F12)
3. Go to Console tab
4. Run:
   ```javascript
   // Check if video elements exist
   document.querySelectorAll('video').length
   
   // Check for video.twimg.com URLs
   document.documentElement.innerHTML.match(/video\.twimg\.com[^"'\s]+\.mp4/g)
   ```

### Step 5: Check Network Tab

1. Open DevTools (F12)
2. Go to Network tab
3. Try using the extension
4. Look for failed requests (red)
5. Click on failed request → Check Headers and Response

## Common Fixes

### Fix 1: Update Extension

If you've made code changes:
1. Go to `chrome://extensions/`
2. Click reload on the extension
3. Close and reopen the popup
4. Try again

### Fix 2: Clear Extension Storage

1. Go to `chrome://extensions/`
2. Find "SecureAI X Analyzer"
3. Click "Details"
4. Click "Clear storage" or "Remove"
5. Reload extension

### Fix 3: Check API Base URL

1. Open extension popup
2. Check the "API base" input field
3. Should be: `https://guardian.secureai.dev` (or your custom URL)
4. Make sure there's no trailing slash
5. Make sure it's `https://` not `http://`

### Fix 4: Test with Different X Post

1. Try a different X post with a video
2. Some posts might have different video formats
3. Some posts might be restricted/private

## Getting Help

If none of the above fixes work:

1. **Collect information:**
   - Extension version (check manifest.json)
   - Browser version (chrome://version)
   - Error message (exact text)
   - X post URL (if possible)
   - Screenshot of error

2. **Check logs:**
   - Extension service worker console
   - Backend logs: `docker logs secureai-backend`
   - Nginx logs: `docker logs secureai-nginx`

3. **Report issue with:**
   - All collected information
   - Steps to reproduce
   - Expected vs actual behavior

## Prevention

To avoid common issues:

1. **Keep extension updated** - Reload after code changes
2. **Keep backend updated** - Run `git pull` and redeploy
3. **Test regularly** - Try different X posts
4. **Monitor logs** - Check backend/nginx logs periodically
