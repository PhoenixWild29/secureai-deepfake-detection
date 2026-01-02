# Force Rebuild to Fix Jetson Message

## Problem
Container is using cached/old code. Need to rebuild, not just restart.

## Solution: Force Rebuild Container

The code is fixed, but the container needs to be **rebuilt** to load the new code:

```bash
cd ~/secureai-deepfake-detection

# 1. Pull latest code (make sure you have the fix)
git pull origin master

# 2. FORCE REBUILD the backend container (this is key!)
docker compose -f docker-compose.https.yml build --no-cache secureai-backend

# 3. Recreate the container with new image
docker compose -f docker-compose.https.yml up -d secureai-backend

# 4. Wait for container to start
sleep 10

# 5. Check logs - should now show new message
docker logs secureai-backend --tail 30 | grep -i jetson
```

## Expected Output

You should see:
- `💻 Running on CPU (real inference, not simulation)`

## Verify Inference is Real

The inference **IS already real** - it uses:
- `self.model(input_tensor)` - Real PyTorch model inference
- `torch.load()` - Real model loading
- `torch.softmax()` - Real probability calculations

**It's NOT simulated** - it's just not optimized for Jetson hardware (which is fine, you're running on CPU).

## If Still Shows Old Message

If you still see the old message after rebuilding:

```bash
# Check what code is actually in the container
docker exec secureai-backend grep -n "simulation mode" /app/ai_model/jetson_inference.py

# If it shows the old text, the rebuild didn't work - try:
docker compose -f docker-compose.https.yml down
docker compose -f docker-compose.https.yml build --no-cache secureai-backend
docker compose -f docker-compose.https.yml up -d
```

