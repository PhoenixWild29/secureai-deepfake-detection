# Check Videos in Container - Step by Step

## Step 1: Check if uploads directory exists

```bash
docker exec secureai-backend ls -la /app/ | grep uploads
```

## Step 2: Check what's in uploads (if it exists)

```bash
docker exec secureai-backend ls -la /app/uploads/ 2>/dev/null || echo "uploads directory doesn't exist"
```

## Step 3: Check if videos are mounted as a volume

```bash
# Check docker-compose volumes
docker inspect secureai-backend | grep -A 10 Mounts
```

## Step 4: Find videos on host machine

```bash
# On your server, check where videos are
ls -la ~/secureai-deepfake-detection/uploads/*.mp4 | head -5
```

## Step 5: Copy videos to container (if not mounted)

If videos aren't accessible in container, copy them:

```bash
# Copy videos from host to container
docker cp ~/secureai-deepfake-detection/uploads/. secureai-backend:/app/uploads/
```

## Step 6: Or create uploads directory and copy

```bash
# Create directory if it doesn't exist
docker exec secureai-backend mkdir -p /app/uploads

# Copy videos
docker cp ~/secureai-deepfake-detection/uploads/. secureai-backend:/app/uploads/
```

## Alternative: Use videos from host via volume mount

If docker-compose has a volume mount, videos should be accessible. Check the docker-compose file for volume configuration.

