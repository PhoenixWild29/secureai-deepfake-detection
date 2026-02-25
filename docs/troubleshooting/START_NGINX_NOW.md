# Fix: Start Nginx Container

## Issue
Nginx container is not running - that's why the site is down.

## Quick Fix

Run this command on your server:

```bash
cd ~/secureai-deepfake-detection
docker compose -f docker-compose.https.yml up -d nginx
```

## Verify It's Running

```bash
# Check Nginx is now running
docker ps | grep nginx

# Check Nginx logs
docker logs secureai-nginx --tail 20

# Test site
curl -I http://localhost
```

## If Nginx Fails to Start

Check for errors:

```bash
# Try starting with verbose output to see errors
docker compose -f docker-compose.https.yml up nginx

# Check if frontend dist exists
ls -la secureai-guardian/dist/

# Check if nginx config exists
ls -la nginx.https.conf
```

## Common Issues

### Issue 1: Frontend dist folder missing
**Fix**:
```bash
cd secureai-guardian
npm run build
cd ..
docker compose -f docker-compose.https.yml up -d nginx
```

### Issue 2: Nginx config file missing
**Fix**: Check if `nginx.https.conf` exists, if not, we need to create it.

### Issue 3: Port conflict
**Fix**: Check if ports 80/443 are in use by another service.

---

## After Starting Nginx

The site should be back up! Test it:
- Visit your domain in browser
- Or: `curl http://localhost`
