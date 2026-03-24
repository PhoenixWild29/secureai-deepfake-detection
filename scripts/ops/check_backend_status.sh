#!/bin/bash
# Quick script to check backend status

echo "=========================================="
echo "🔍 Checking Backend Status"
echo "=========================================="
echo ""

echo "1. Checking Docker containers..."
docker ps --filter "name=secureai-backend" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "2. Checking backend health endpoint..."
docker exec secureai-backend curl -f http://localhost:8000/api/health 2>/dev/null || echo "❌ Backend health check failed"
echo ""

echo "3. Checking Nginx status..."
docker ps --filter "name=secureai-nginx" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "4. Testing from host (via Nginx)..."
curl -f https://guardian.secureai.dev/api/health 2>/dev/null || echo "❌ Nginx proxy not working"
echo ""

echo "5. Checking backend logs (last 20 lines)..."
docker logs secureai-backend --tail 20
echo ""

echo "=========================================="
echo "✅ Status check complete"
echo "=========================================="
