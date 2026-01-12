#!/bin/bash
# Quick diagnostic script for site down issues

echo "=========================================="
echo "🔍 SecureAI Site Diagnostic"
echo "=========================================="
echo ""

cd ~/secureai-deepfake-detection 2>/dev/null || {
    echo "❌ Not in project directory"
    exit 1
}

echo "1️⃣ Checking Docker containers..."
echo "----------------------------------------"
docker ps -a | grep -E "secureai|nginx" || echo "❌ No SecureAI containers found"
echo ""

echo "2️⃣ Checking if containers are running..."
echo "----------------------------------------"
NGINX_RUNNING=$(docker ps | grep -c "secureai-nginx")
BACKEND_RUNNING=$(docker ps | grep -c "secureai-backend")

if [ "$NGINX_RUNNING" -eq 0 ]; then
    echo "❌ Nginx container NOT running"
else
    echo "✅ Nginx container is running"
fi

if [ "$BACKEND_RUNNING" -eq 0 ]; then
    echo "❌ Backend container NOT running"
else
    echo "✅ Backend container is running"
fi
echo ""

echo "3️⃣ Checking Nginx logs (last 20 lines)..."
echo "----------------------------------------"
docker logs secureai-nginx --tail 20 2>&1 || echo "⚠️  Could not read Nginx logs (container may not exist)"
echo ""

echo "4️⃣ Checking Backend logs (last 20 lines)..."
echo "----------------------------------------"
docker logs secureai-backend --tail 20 2>&1 || echo "⚠️  Could not read Backend logs (container may not exist)"
echo ""

echo "5️⃣ Checking for errors in backend logs..."
echo "----------------------------------------"
docker logs secureai-backend 2>&1 | grep -i error | tail -10 || echo "No recent errors found"
echo ""

echo "6️⃣ Checking frontend dist folder..."
echo "----------------------------------------"
if [ -d "secureai-guardian/dist" ]; then
    echo "✅ Frontend dist folder exists"
    FILE_COUNT=$(find secureai-guardian/dist -type f | wc -l)
    echo "   Files in dist: $FILE_COUNT"
    if [ -f "secureai-guardian/dist/index.html" ]; then
        echo "✅ index.html exists"
    else
        echo "❌ index.html NOT FOUND"
    fi
else
    echo "❌ Frontend dist folder NOT FOUND"
    echo "   → Need to rebuild frontend: cd secureai-guardian && npm run build"
fi
echo ""

echo "7️⃣ Checking port availability..."
echo "----------------------------------------"
if command -v netstat &> /dev/null; then
    netstat -tulpn | grep -E ":(80|443)" || echo "Ports 80/443 appear available"
elif command -v ss &> /dev/null; then
    ss -tulpn | grep -E ":(80|443)" || echo "Ports 80/443 appear available"
else
    echo "⚠️  Cannot check ports (netstat/ss not available)"
fi
echo ""

echo "8️⃣ Testing backend health endpoint..."
echo "----------------------------------------"
docker exec secureai-backend curl -f http://localhost:8000/api/health 2>/dev/null && echo "✅ Backend health check passed" || echo "❌ Backend health check failed"
echo ""

echo "9️⃣ Testing site from server..."
echo "----------------------------------------"
curl -I http://localhost 2>/dev/null | head -5 || echo "❌ Site not responding on http://localhost"
echo ""

echo "=========================================="
echo "✅ Diagnostic Complete!"
echo "=========================================="
echo ""
echo "📋 Quick Fixes:"
echo ""
if [ "$NGINX_RUNNING" -eq 0 ]; then
    echo "→ Start Nginx: docker compose -f docker-compose.https.yml up -d nginx"
fi
if [ "$BACKEND_RUNNING" -eq 0 ]; then
    echo "→ Start Backend: docker compose -f docker-compose.https.yml up -d secureai-backend"
fi
if [ ! -d "secureai-guardian/dist" ] || [ ! -f "secureai-guardian/dist/index.html" ]; then
    echo "→ Rebuild Frontend: cd secureai-guardian && npm run build"
fi
echo ""
echo "→ Restart All: docker compose -f docker-compose.https.yml restart"
echo "→ Or Full Restart: docker compose -f docker-compose.https.yml down && docker compose -f docker-compose.https.yml up -d"
