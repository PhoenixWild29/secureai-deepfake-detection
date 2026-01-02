# Quick Guide: Enable AIStore

## Current Status

Your app shows: `[WARNING] AIStore library not available. Running in local storage mode only.`

This is **normal** - the app works fine without AIStore (uses S3 or local storage).

## To Enable AIStore

### Option 1: Install on Server (Recommended)

**On your cloud server**, run:

```bash
cd ~/secureai-deepfake-detection

# Pull latest code (includes AIStore installation in Dockerfile)
git pull origin master

# Rebuild backend container (will attempt to install AIStore)
docker compose -f docker-compose.https.yml down
docker compose -f docker-compose.https.yml build --no-cache secureai-backend
docker compose -f docker-compose.https.yml up -d

# Check if AIStore installed successfully
docker logs secureai-backend | grep -i aistore
```

**Expected result:**
- If AIStore installs: `[OK] Connected to AIStore at http://...`
- If it fails: `AIStore install failed (optional - will use S3/local storage)` - **This is OK!**

### Option 2: Manual Installation (If Option 1 Fails)

If the automatic installation fails, you can install manually:

```bash
# Enter the backend container
docker exec -it secureai-backend bash

# Install AIStore Python client
pip install git+https://github.com/NVIDIA/aistore.git

# Exit container
exit

# Restart container
docker compose -f docker-compose.https.yml restart secureai-backend
```

### Option 3: Use AWS S3 Instead (Already Working!)

**You don't need AIStore!** Your app already uses AWS S3 for distributed storage, which is:
- ✅ Already configured
- ✅ Enterprise-grade
- ✅ More reliable than setting up AIStore

The AIStore warning is **informational only** - your app is fully functional with S3.

## Important Notes

1. **AIStore requires a running AIStore server/cluster** - it's not just a Python library
2. **You already have S3 configured** - which works great for distributed storage
3. **The warning is harmless** - the app works perfectly without AIStore

## Recommendation

**Keep using AWS S3** - it's already working and doesn't require additional infrastructure!

If you specifically need AIStore features, you'll need to:
1. Set up an AIStore cluster (separate server/service)
2. Configure the endpoint in `.env`
3. Install the Python client (steps above)

But for most use cases, **S3 is the better choice**.

