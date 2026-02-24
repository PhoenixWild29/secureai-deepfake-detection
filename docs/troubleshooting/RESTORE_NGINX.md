# Restore Nginx Container

## Problem
Nginx container doesn't exist - it was never created or was removed.

## Solution: Create and Start Nginx

Run these commands:

```bash
cd ~/secureai-deepfake-detection

# 1. Check if frontend is built
ls -la secureai-guardian/dist/ | head -5

# 2. If dist folder is missing or empty, rebuild frontend:
cd secureai-guardian
npm run build
cd ..

# 3. Create and start nginx container
docker compose -f docker-compose.https.yml up -d nginx

# 4. Verify nginx is now running
docker ps | grep nginx

# 5. Check nginx logs
docker logs secureai-nginx --tail 30
```

## If nginx fails to start, check:

```bash
# Check if frontend dist folder exists
ls -la secureai-guardian/dist/

# Check if nginx config file exists
ls -la nginx.https.conf

# Check if certs folder exists (for HTTPS)
ls -la certs/

# Try starting with verbose output
docker compose -f docker-compose.https.yml up nginx
```

## Alternative: Restart entire stack

If nginx still won't start, restart everything:

```bash
cd ~/secureai-deepfake-detection

# Restart all services
docker compose -f docker-compose.https.yml down
docker compose -f docker-compose.https.yml up -d

# Check all containers are running
docker ps
```

