# Quick Fix: Site Not Working

## Problem
Nginx container is not running, so the site is not accessible.

## Immediate Fix

Run these commands on your server:

```bash
cd ~/secureai-deepfake-detection

# 1. Check if nginx container exists but stopped
docker ps -a | grep nginx

# 2. Check nginx logs if it exists
docker logs secureai-nginx 2>&1 | tail -50

# 3. Start nginx container
docker compose -f docker-compose.https.yml up -d nginx

# 4. Verify nginx is running
docker ps | grep nginx

# 5. Check if frontend dist folder exists
ls -la secureai-guardian/dist/ | head -10

# 6. If dist folder is missing, rebuild frontend
cd secureai-guardian
npm run build
cd ..

# 7. Restart nginx after frontend build
docker compose -f docker-compose.https.yml restart nginx

# 8. Check nginx logs for errors
docker logs secureai-nginx --tail 30
```

## If Nginx Still Won't Start

```bash
# Check nginx configuration
docker compose -f docker-compose.https.yml config

# Check if ports 80/443 are already in use
sudo netstat -tulpn | grep -E ':(80|443)'

# Restart entire stack
docker compose -f docker-compose.https.yml down
docker compose -f docker-compose.https.yml up -d

# Check all containers
docker ps
```

## Verify Site is Working

```bash
# Test from server
curl -I http://localhost
curl -I https://localhost

# Check nginx is serving frontend
curl http://localhost | head -20
```

