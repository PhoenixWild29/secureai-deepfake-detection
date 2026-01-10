# Fix: No Space Left on Device

## Problem
Docker build failed because the server ran out of disk space.

## Solution: Free Up Disk Space

Run these commands on your server:

```bash
# 1. Check current disk usage
df -h

# 2. Check Docker disk usage
docker system df

# 3. Clean up Docker (removes unused images, containers, volumes, networks)
docker system prune -a --volumes -f

# 4. Remove old/unused Docker images
docker image prune -a -f

# 5. Remove stopped containers
docker container prune -f

# 6. Remove unused volumes
docker volume prune -f

# 7. Check disk space again
df -h

# 8. Now retry the build
cd ~/secureai-deepfake-detection
docker compose -f docker-compose.https.yml build --no-cache secureai-backend
```

## If Still Not Enough Space

If you still don't have enough space after cleaning Docker:

```bash
# Check what's using the most space
du -sh /* 2>/dev/null | sort -hr | head -10

# Clean up system logs (if safe)
sudo journalctl --vacuum-time=7d

# Remove old package cache
sudo apt-get clean
sudo apt-get autoremove -y

# Check space again
df -h
```

## Alternative: Build Without Cache (Uses Less Space)

If space is still tight, you can try building without the `--no-cache` flag (uses cached layers):

```bash
docker compose -f docker-compose.https.yml build secureai-backend
```

## After Freeing Space

Once you have space, retry:

```bash
cd ~/secureai-deepfake-detection
docker compose -f docker-compose.https.yml build --no-cache secureai-backend
docker compose -f docker-compose.https.yml up -d secureai-backend
```

