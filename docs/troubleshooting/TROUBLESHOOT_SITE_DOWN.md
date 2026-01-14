# Troubleshoot Site Down - Quick Fix Guide

## Step 1: Check Container Status

Run these commands on your server:

```bash
# Check all running containers
docker ps

# Check all containers (including stopped)
docker ps -a

# Check specific containers
docker ps | grep secureai
```

**Expected**: Should see `secureai-nginx` and `secureai-backend` running

---

## Step 2: Check Container Logs

```bash
# Check Nginx logs
docker logs secureai-nginx --tail 50

# Check backend logs
docker logs secureai-backend --tail 50

# Check for errors
docker logs secureai-backend 2>&1 | grep -i error | tail -20
```

---

## Step 3: Common Issues & Fixes

### Issue 1: Nginx Container Not Running

**Symptoms**: `docker ps` shows no `secureai-nginx`

**Fix**:
```bash
cd ~/secureai-deepfake-detection
docker compose -f docker-compose.https.yml up -d nginx
```

### Issue 2: Backend Container Not Running

**Symptoms**: `docker ps` shows no `secureai-backend`

**Fix**:
```bash
cd ~/secureai-deepfake-detection
docker compose -f docker-compose.https.yml up -d secureai-backend
```

### Issue 3: Both Containers Stopped

**Fix**:
```bash
cd ~/secureai-deepfake-detection
docker compose -f docker-compose.https.yml up -d
```

### Issue 4: Port Conflicts

**Check**:
```bash
# Check if ports are in use
netstat -tulpn | grep -E "80|443|5000"
# OR
ss -tulpn | grep -E "80|443|5000"
```

**Fix**: Stop conflicting services or change ports in docker-compose

### Issue 5: Frontend Files Missing

**Check**:
```bash
# Check if frontend dist exists
ls -la secureai-guardian/dist/
```

**Fix**: Rebuild frontend if missing
```bash
cd secureai-guardian
npm run build
```

---

## Step 4: Restart Everything

If unsure, restart all services:

```bash
cd ~/secureai-deepfake-detection

# Stop all
docker compose -f docker-compose.https.yml down

# Start all
docker compose -f docker-compose.https.yml up -d

# Check status
docker ps
```

---

## Step 5: Verify Site is Up

```bash
# Check if site responds
curl -I http://localhost
# OR
curl -I https://localhost

# Check from outside (replace with your domain)
curl -I https://your-domain.com
```

---

## Quick Diagnostic Script

Run this to get full status:

```bash
cd ~/secureai-deepfake-detection

echo "=== Container Status ==="
docker ps -a | grep secureai

echo ""
echo "=== Nginx Status ==="
docker ps | grep nginx || echo "❌ Nginx not running"

echo ""
echo "=== Backend Status ==="
docker ps | grep backend || echo "❌ Backend not running"

echo ""
echo "=== Recent Backend Errors ==="
docker logs secureai-backend --tail 20 2>&1 | grep -i error || echo "No recent errors"

echo ""
echo "=== Recent Nginx Errors ==="
docker logs secureai-nginx --tail 20 2>&1 | grep -i error || echo "No recent errors"
```

---

## Most Common Fix

**90% of the time, this fixes it**:

```bash
cd ~/secureai-deepfake-detection
docker compose -f docker-compose.https.yml restart
```

Or if that doesn't work:

```bash
docker compose -f docker-compose.https.yml down
docker compose -f docker-compose.https.yml up -d
```

---

## Share Results

After running diagnostics, share:
1. Output of `docker ps`
2. Any error messages from logs
3. What you see when accessing the site

Then I'll provide specific fixes!
