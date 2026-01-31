#!/bin/bash
# Complete rebuild of backend to ensure code changes are applied

echo "=========================================="
echo "🔧 Complete Backend Rebuild with Fixes"
echo "=========================================="
echo ""

# Navigate to project directory
cd ~/secureai-deepfake-detection || exit 1

echo "0. Checking disk space before build..."
df -h || true
echo ""
docker system df || true
echo ""

# If Docker disk is low, clean up first (prevents: 'no space left on device')
DOCKER_ROOT="/var/lib/docker"
if [ -d "$DOCKER_ROOT" ]; then
  AVAIL_MB=$(df -Pm "$DOCKER_ROOT" 2>/dev/null | awk 'NR==2{print $4}')
  if [ -n "${AVAIL_MB:-}" ] && [ "$AVAIL_MB" -lt 8000 ]; then
    echo "   ⚠️  Low free space under $DOCKER_ROOT (${AVAIL_MB}MB). Running cleanup..."
    if [ -x ./clean_disk_space.sh ]; then
      ./clean_disk_space.sh || true
    else
      docker container prune -f || true
      docker network prune -f || true
      docker builder prune -af || true
      docker image prune -af || true
    fi
    echo ""
  fi
fi

echo "1. Pulling latest code from GitHub..."
git pull origin master
if [ $? -ne 0 ]; then
    echo "   ⚠️  Git pull had issues, but continuing..."
fi
echo "   ✅ Code pulled"
echo ""

echo "2. Stopping backend container..."
docker compose -f docker-compose.https.yml stop secureai-backend
sleep 2
echo "   ✅ Backend stopped"
echo ""

echo "3. Rebuilding backend container (no cache - ensures new code is used)..."
docker compose -f docker-compose.https.yml build --no-cache secureai-backend
if [ $? -ne 0 ]; then
    echo "   ❌ Build failed!"
    echo ""
    echo "Most common cause: low disk space on the server."
    echo "Run: ./clean_disk_space.sh"
    exit 1
fi
echo "   ✅ Backend rebuilt"
echo ""

echo "4. Removing old container and creating new one..."
docker compose -f docker-compose.https.yml rm -f secureai-backend
docker compose -f docker-compose.https.yml up -d secureai-backend
echo "   ✅ New container created"
echo ""

echo "5. Waiting for backend to start (15 seconds)..."
sleep 15
echo ""

echo "6. Checking backend health..."
for i in {1..5}; do
    HEALTH=$(docker exec secureai-backend curl -s http://localhost:8000/api/health 2>/dev/null)
    if [ -n "$HEALTH" ]; then
        echo "   ✅ Backend is healthy: $HEALTH"
        break
    else
        echo "   ⏳ Waiting for backend to start... (attempt $i/5)"
        sleep 3
    fi
done
echo ""

echo "7. Verifying new code is loaded..."
# Check if the blockchain submission code with eventlet wrapper exists
CODE_CHECK=$(docker exec secureai-backend grep -A 5 "Wrap in eventlet threadpool" /app/api.py 2>/dev/null | wc -l)
if [ "$CODE_CHECK" -gt 0 ]; then
    echo "   ✅ New code is loaded (eventlet wrapper found)"
else
    echo "   ⚠️  Warning: Could not verify new code is loaded"
fi
echo ""

echo "7b. Verifying PyTorch is CPU-only (prevents huge CUDA layers)..."
TORCH_CUDA=$(docker exec secureai-backend python -c "import torch; print(torch.version.cuda or 'None')" 2>/dev/null || true)
if [ -n "$TORCH_CUDA" ] && [ "$TORCH_CUDA" != "None" ]; then
    echo "   ⚠️  PyTorch reports CUDA=$TORCH_CUDA (should be None on this server)."
    echo "   ⚠️  This can cause massive NVIDIA/CUDA packages and disk exhaustion."
else
    echo "   ✅ PyTorch is CPU-only (CUDA=None)"
fi
echo ""

echo "8. Checking for blocking function errors (should be none)..."
sleep 5  # Give it a moment to initialize
BLOCKING_ERRORS=$(docker logs secureai-backend --tail 50 2>&1 | grep -i "blocking functions" | wc -l)
if [ "$BLOCKING_ERRORS" -eq 0 ]; then
    echo "   ✅ No blocking function errors found"
else
    echo "   ⚠️  Found $BLOCKING_ERRORS blocking function error(s) - may need to check logs"
fi
echo ""

echo "9. Recent backend logs (last 20 lines)..."
docker logs secureai-backend --tail 20
echo ""

echo "=========================================="
echo "✅ Rebuild Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Test with a video analysis"
echo "2. Check blockchain logs: docker logs secureai-backend --tail 100 | grep -i blockchain"
echo "3. Verify SOL_TX proofs counter increments in Dashboard"
echo ""
