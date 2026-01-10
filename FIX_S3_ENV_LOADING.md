# Fix S3 Environment Variable Loading

## Issue
The `.env` file has correct credentials, but the container isn't loading them properly.

## Solution: Recreate Container (Not Just Restart)

A simple `restart` might not reload environment variables. We need to recreate the container:

```bash
cd ~/secureai-deepfake-detection

# Stop and remove the container
docker compose -f docker-compose.https.yml stop secureai-backend
docker compose -f docker-compose.https.yml rm -f secureai-backend

# Recreate and start it (this will reload .env file)
docker compose -f docker-compose.https.yml up -d secureai-backend
```

## Alternative: Full Recreate

If the above doesn't work, recreate all services:

```bash
cd ~/secureai-deepfake-detection

# Down and up (this recreates containers)
docker compose -f docker-compose.https.yml down
docker compose -f docker-compose.https.yml up -d
```

## Verify After Recreate

```bash
# Check environment variables are loaded
docker exec secureai-backend env | grep AWS

# Should show:
# AWS_ACCESS_KEY_ID=your_access_key_id_here
# AWS_SECRET_ACCESS_KEY=your_secret_access_key_here
# AWS_DEFAULT_REGION=us-east-2
# S3_BUCKET_NAME=secureai-deepfake-videos
# S3_RESULTS_BUCKET_NAME=secureai-deepfake-results

# Check S3 connection in logs
docker logs secureai-backend --tail 50 | grep -iE "s3|aws"
```

## Expected Success Output

You should see:
- `✅ S3 connection established. Bucket: secureai-deepfake-videos`
- No more "AWS credentials not configured" warnings

