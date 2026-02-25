# X Cookies Setup - Quick Start

## Quick Steps (5 minutes)

### 1. Export Cookies (2 min)

**Chrome:**
1. Install: https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc
2. Go to https://x.com (make sure you're logged in)
3. Click extension icon → "Export" button
4. Save the file (it may save as `x_cookies.txt.txt` - that's OK, we'll fix it)

**Firefox:**
1. Install: https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/
2. Go to https://x.com (make sure you're logged in)
3. Click extension icon → "Export" button
4. Save the file (it may save as `x_cookies.txt.txt` - that's OK, we'll fix it)

**Important:** Make sure you're logged into X before exporting!

### 2. Upload to Server (1 min)

**Your server:** `root@guardian.secureai.dev`

**Option A: Using SCP (from PowerShell)**

1. Open PowerShell
2. Navigate to your project folder:
   ```powershell
   cd "C:\Users\ssham\OneDrive\New Business - SecureAI\DeepFake Detection Model\SecureAI-DeepFake-Detection"
   ```

3. Upload the file (use the actual filename - it might be `x_cookies.txt.txt`):
   ```powershell
   # If file is named x_cookies.txt.txt:
   scp "secrets\x_cookies.txt.txt" root@guardian.secureai.dev:/root/secureai-deepfake-detection/secrets/x_cookies.txt
   
   # OR if file is named x_cookies.txt:
   scp "secrets\x_cookies.txt" root@guardian.secureai.dev:/root/secureai-deepfake-detection/secrets/x_cookies.txt
   ```

**Option B: Using DigitalOcean Console**

1. Go to DigitalOcean dashboard → Your droplet
2. Click "Access" → "Launch Droplet Console"
3. Run:
   ```bash
   cd ~/secureai-deepfake-detection
   mkdir -p secrets
   nano secrets/x_cookies.txt
   ```
4. Paste your cookies content
5. Press `Ctrl+X`, then `Y`, then `Enter` to save

### 3. Set Permissions (30 sec)

**SSH into your server:**
```bash
ssh root@guardian.secureai.dev
```

**Set permissions:**
```bash
cd ~/secureai-deepfake-detection
chmod 600 secrets/x_cookies.txt
```

### 4. Restart Backend (1 min)

**Still on the server, run:**
```bash
# Restart to pick up new cookies
docker compose -f docker-compose.https.yml restart secureai-backend

# Verify it's working
docker exec secureai-backend env | grep X_COOKIES_FILE
```

**Should show:** `X_COOKIES_FILE=/app/secrets/x_cookies.txt`

**Also verify file exists in container:**
```bash
docker exec secureai-backend ls -la /app/secrets/x_cookies.txt
```

### 5. Test (30 sec)

1. Go to https://guardian.secureai.dev
2. Click **"STREAM_INTEL"** tab
3. Paste an X link (e.g., `https://x.com/username/status/1234567890`)
4. Click **"Authorize Multi-Layer Analysis"**
5. Should work without errors! ✅

## Complete Verification Checklist

Run these on your server (`ssh root@guardian.secureai.dev`):

```bash
# 1. Check file exists on server
ls -la ~/secureai-deepfake-detection/secrets/x_cookies.txt

# 2. Check file exists in container
docker exec secureai-backend ls -la /app/secrets/x_cookies.txt

# 3. Check environment variable
docker exec secureai-backend env | grep X_COOKIES_FILE

# 4. Check file content (first few lines)
docker exec secureai-backend head -5 /app/secrets/x_cookies.txt
```

**All should succeed without errors!**

## Important Notes

- ⚠️ **Cookies expire after ~30 days** - re-export monthly
- 🔒 **Keep cookies file secure** - don't commit to git
- ✅ **Works for all users** - once configured, everyone can use X links

## Troubleshooting

**Still getting "X_AUTH_REQUIRED" error?**
```bash
# 1. Verify file exists
ls -la secrets/x_cookies.txt

# 2. Check env var in container
docker exec secureai-backend env | grep X_COOKIES

# 3. Restart backend
docker compose -f docker-compose.https.yml restart secureai-backend

# 4. Check logs
docker logs secureai-backend --tail 50
```

**Cookies expired?**
- Re-export from browser (make sure you're logged into X)
- Re-upload to server
- Restart backend

## Full Guide

For detailed instructions, see: `docs/deployment/X_COOKIES_SETUP.md`
