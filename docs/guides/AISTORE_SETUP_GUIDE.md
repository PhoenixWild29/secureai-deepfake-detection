# AIStore Setup Guide

AIStore is a distributed object storage system that provides high-performance, scalable storage for video files and other large data.

## What is AIStore?

AIStore is an open-source, lightweight object storage system designed for AI/ML workloads. It provides:
- Distributed storage across multiple nodes
- High-performance data access
- S3-compatible API
- Replication and redundancy

## Current Status

Your application currently shows:
```
[WARNING] AIStore library not available. Running in local storage mode only.
```

This is **normal** if AIStore is not set up. The application will:
- ✅ Continue working with local storage
- ✅ Use AWS S3 if configured (which you already have)
- ✅ Automatically use AIStore if installed and configured

## Option 1: Use AWS S3 (Recommended - Already Configured)

Since you already have AWS S3 configured, you can use it as your distributed storage. The application will automatically use S3 for distributed storage when AIStore is not available.

**No additional setup needed** - your S3 configuration is already working!

## Option 2: Install AIStore Python Client

If you want to use AIStore specifically, you need:

1. **An AIStore cluster/server running** (separate from your app)
2. **The Python client library**

### Install Python Client

The AIStore Python client is available from GitHub:

```bash
pip install git+https://github.com/NVIDIA/aistore.git
```

Or add to `requirements.txt`:
```
# AIStore Python client (install from GitHub)
git+https://github.com/NVIDIA/aistore.git
```

### Configure Environment Variables

Add to your `.env` file:
```env
AISTORE_ENDPOINT=http://your-aistore-server:8080
AISTORE_BUCKET=secureai-videos
```

### Rebuild Docker Container

```bash
cd ~/secureai-deepfake-detection
docker compose -f docker-compose.https.yml build --no-cache secureai-backend
docker compose -f docker-compose.https.yml up -d
```

## Option 3: Set Up Your Own AIStore Cluster

### Quick Start with Docker

```bash
# Pull AIStore image
docker pull aistore/aisnode:latest

# Run AIStore cluster (single node for testing)
docker run -d \
  --name aistore \
  -p 8080:8080 \
  -p 5108:5108 \
  -v /tmp/ais:/ais \
  aistore/aisnode:latest
```

### Verify AIStore is Running

```bash
curl http://localhost:8080/v1/health
```

Should return: `{"status": "healthy"}`

### Create Bucket

```bash
curl -X PUT http://localhost:8080/v1/buckets/secureai-videos
```

## Installation Steps for Your Server

### Step 1: Install AIStore Python Client

On your server, inside the Docker container or locally:

```bash
# Option A: Install directly
pip install git+https://github.com/NVIDIA/aistore.git

# Option B: Add to requirements.txt and rebuild
# (We've already added a comment in requirements.txt)
```

### Step 2: Update .env File

Add these lines to your `.env` file on the server:

```env
# AIStore Configuration (optional - only if you have an AIStore cluster)
AISTORE_ENDPOINT=http://localhost:8080
AISTORE_BUCKET=secureai-videos
```

**Note:** If you don't have an AIStore cluster, leave these commented out or don't add them. The app will use S3 or local storage.

### Step 3: Rebuild and Restart

```bash
cd ~/secureai-deepfake-detection
git pull origin master
docker compose -f docker-compose.https.yml down
docker compose -f docker-compose.https.yml build --no-cache secureai-backend
docker compose -f docker-compose.https.yml up -d
```

## Verification

After setup, check the logs:
```bash
docker logs secureai-backend | grep -i aistore
```

**Success indicators:**
- `[OK] Connected to AIStore at http://...`
- No "AIStore library not available" warnings
- Videos are stored with `storage_type: 'distributed'`

**If AIStore is not available:**
- `[WARNING] AIStore library not available. Running in local storage mode only.`
- This is **OK** - the app will use S3 or local storage instead

## Troubleshooting

### "AIStore library not available"
**Solution:** Install the Python client:
```bash
pip install git+https://github.com/NVIDIA/aistore.git
```

Then rebuild the Docker container.

### "AIStore not available: Connection refused"
**Causes:**
- AIStore server is not running
- Wrong endpoint URL
- Network/firewall blocking connection

**Solutions:**
1. Check if AIStore server is running: `curl http://localhost:8080/v1/health`
2. Verify endpoint URL in `.env` file
3. Check Docker network connectivity
4. **Recommendation:** Use AWS S3 instead (already configured)

### "Failed to store in AIStore"
**Causes:**
- Bucket doesn't exist
- Permission issues
- Network connectivity

**Solutions:**
1. Create bucket: `curl -X PUT http://localhost:8080/v1/buckets/secureai-videos`
2. Check permissions
3. Verify endpoint is accessible from container

## Recommendation

**For production use, I recommend using AWS S3** (which you already have configured) instead of setting up a separate AIStore cluster. S3 provides:
- ✅ Already configured and working
- ✅ Enterprise-grade reliability
- ✅ Automatic backups and redundancy
- ✅ No additional infrastructure to manage
- ✅ Cost-effective for your use case

The AIStore integration is useful if you:
- Already have an AIStore cluster
- Need specific AIStore features
- Want to use on-premises storage

## Summary

- **Current status:** App works fine with local storage and S3
- **AIStore is optional:** Not required for the app to function
- **S3 is recommended:** Already configured and working
- **AIStore setup:** Only needed if you specifically want to use AIStore

The warnings you see are **informational only** - your application is fully functional without AIStore!

