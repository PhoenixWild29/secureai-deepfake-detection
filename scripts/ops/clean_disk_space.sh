#!/bin/bash
# Free up disk space on the server for Docker builds.
# Safe: does NOT delete volumes (so Postgres/Redis data remains).

set -euo pipefail

echo "=========================================="
echo "🧹 Cleaning Disk Space (Docker-safe)"
echo "=========================================="
echo ""

echo "1) Disk usage (before)"
df -h || true
echo ""

echo "2) Docker disk usage (before)"
docker system df || true
echo ""

echo "3) Pruning stopped containers..."
docker container prune -f || true
echo ""

echo "4) Pruning unused networks..."
docker network prune -f || true
echo ""

echo "5) Pruning build cache..."
docker builder prune -af || true
echo ""

echo "6) Pruning unused images..."
docker image prune -af || true
echo ""

echo "7) Docker disk usage (after)"
docker system df || true
echo ""

echo "8) Disk usage (after)"
df -h || true
echo ""

echo "=========================================="
echo "✅ Cleanup complete"
echo "=========================================="
