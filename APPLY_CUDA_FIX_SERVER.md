# Apply CUDA Fix on Server - Complete Step-by-Step Guide

## Prerequisites

Make sure you're on your server (SSH into it if needed).

## Step-by-Step Instructions

### Step 1: Navigate to Project Directory and Pull Latest Changes

```bash
cd ~/secureai-deepfake-detection
git pull origin master
```

**Expected Output**: 
- Shows files updated (enhanced_detector.py, Dockerfile, test_ensemble_comprehensive.py, etc.)
- `Already up to date` or shows commit hash

### Step 2: Rebuild Docker Container (to apply Dockerfile changes)

```bash
cd ~/secureai-deepfake-detection
docker compose -f docker-compose.https.yml down
docker compose -f docker-compose.https.yml build --no-cache secureai-backend
docker compose -f docker-compose.https.yml up -d secureai-backend
```

**Expected Output**:
- Container stops and removes
- Build starts (may take a few minutes)
- `Successfully built <image-id>`
- Container starts: `secureai-backend`

**Note**: The `--no-cache` flag ensures Dockerfile changes are applied.

### Step 3: Copy Updated Files to Container

```bash
cd ~/secureai-deepfake-detection
docker cp ai_model/enhanced_detector.py secureai-backend:/app/ai_model/
docker cp test_ensemble_comprehensive.py secureai-backend:/app/
```

**Expected Output**:
- `Successfully copied <size> to secureai-backend:/app/ai_model/enhanced_detector.py`
- `Successfully copied <size> to secureai-backend:/app/test_ensemble_comprehensive.py`

### Step 4: Run Test

**Option A: Normal Run (CUDA errors suppressed, but may appear briefly)**
```bash
cd ~/secureai-deepfake-detection
docker exec secureai-backend python3 /app/test_ensemble_comprehensive.py
```

**Option B: Filtered Output (Clean output, no CUDA errors visible)**
```bash
cd ~/secureai-deepfake-detection
docker exec secureai-backend python3 /app/test_ensemble_comprehensive.py 2>&1 | grep -v -i 'cuda\|cuinit\|stream_executor\|xla\|tensorflow'
```

### Step 5: Verify Container is Running

```bash
cd ~/secureai-deepfake-detection
docker ps | grep secureai-backend
```

**Expected Output**:
- Container listed as `Up` with status `healthy` or `starting`

---

## Complete Command Sequence (Copy-Paste Ready)

If you want to run everything at once (copy-paste this entire block):

```bash
cd ~/secureai-deepfake-detection && \
git pull origin master && \
docker compose -f docker-compose.https.yml down && \
docker compose -f docker-compose.https.yml build --no-cache secureai-backend && \
docker compose -f docker-compose.https.yml up -d secureai-backend && \
docker cp ai_model/enhanced_detector.py secureai-backend:/app/ai_model/ && \
docker cp test_ensemble_comprehensive.py secureai-backend:/app/ && \
echo "✅ Setup complete! Waiting 10 seconds for container to start..." && \
sleep 10 && \
docker exec secureai-backend python3 /app/test_ensemble_comprehensive.py
```

---

## Troubleshooting

### If `cd ~/secureai-deepfake-detection` fails:

**Check current directory**:
```bash
pwd
```

**Find the correct path**:
```bash
find ~ -name "secureai-deepfake-detection" -type d 2>/dev/null
```

**Or check if it's in a different location**:
```bash
ls -la ~/
```

### If git pull fails:

**Check if you're in the right directory**:
```bash
ls -la | grep -E 'git|docker-compose'
```

**If not a git repository, clone it**:
```bash
cd ~
git clone https://github.com/PhoenixWild29/secureai-deepfake-detection.git
cd secureai-deepfake-detection
```

### If docker commands fail:

**Check if Docker is running**:
```bash
docker ps
```

**Check if you're in the correct directory**:
```bash
ls -la docker-compose.https.yml
```

**If file not found**:
```bash
find ~ -name "docker-compose.https.yml" 2>/dev/null
```

---

## Expected Results After Fix

✅ **No CUDA errors on module import**  
✅ **Face detection works (MTCNN or Haar fallback)**  
✅ **CLIP model loads without errors**  
✅ **Test completes successfully**  
✅ **All videos processed**  

---

## Quick Verification Commands

**Check environment variables are set**:
```bash
cd ~/secureai-deepfake-detection
docker exec secureai-backend env | grep -E 'CUDA|TF_'
```

**Expected output**:
```
CUDA_VISIBLE_DEVICES=
TF_CPP_MIN_LOG_LEVEL=3
TF_FORCE_GPU_ALLOW_GROWTH=false
TF_ENABLE_ONEDNN_OPTS=0
```

**Check if enhanced_detector.py was updated**:
```bash
cd ~/secureai-deepfake-detection
docker exec secureai-backend grep -n "def _try_mtcnn" /app/ai_model/enhanced_detector.py
```

**Expected output**: Should show line number where `_try_mtcnn` method is defined.

**Check container logs**:
```bash
cd ~/secureai-deepfake-detection
docker logs secureai-backend --tail 50 | grep -i -E 'cuda|error|clip|detector'
```

---

## Summary

The fix has been applied by:
1. ✅ Pulling latest code with CUDA fixes
2. ✅ Rebuilding container with updated Dockerfile
3. ✅ Copying updated Python files to container
4. ✅ Testing with comprehensive ensemble test

**Next**: Run the test and verify no CUDA errors appear!
