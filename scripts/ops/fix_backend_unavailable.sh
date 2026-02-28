#!/bin/bash
# Fix "Backend service unavailable" error

echo "=========================================="
echo "🔧 Fixing Backend Service Unavailable"
echo "=========================================="
echo ""

# Step 1: Check if containers are running
echo "1. Checking Docker containers..."
if ! docker ps | grep -q "secureai-backend"; then
    echo "   ❌ Backend container is NOT running"
    echo "   Starting backend container..."
    docker-compose -f docker-compose.https.yml up -d secureai-backend
    sleep 5
else
    echo "   ✅ Backend container is running"
fi

if ! docker ps | grep -q "secureai-nginx"; then
    echo "   ❌ Nginx container is NOT running"
    echo "   Starting Nginx container..."
    docker-compose -f docker-compose.https.yml up -d nginx
    sleep 3
else
    echo "   ✅ Nginx container is running"
fi

echo ""

# Step 2: Check backend health directly
echo "2. Testing backend health (direct)..."
BACKEND_HEALTH=$(docker exec secureai-backend curl -s http://localhost:8000/api/health 2>/dev/null)
if [ -z "$BACKEND_HEALTH" ]; then
    echo "   ❌ Backend not responding"
    echo "   Checking backend logs..."
    docker logs secureai-backend --tail 30
    echo ""
    echo "   Attempting to restart backend..."
    docker-compose -f docker-compose.https.yml restart secureai-backend
    sleep 10
else
    echo "   ✅ Backend is healthy: $BACKEND_HEALTH"
fi

echo ""

# Step 3: Check Nginx proxy
echo "3. Testing Nginx proxy..."
NGINX_HEALTH=$(curl -s https://guardian.secureai.dev/api/health 2>/dev/null)
if [ -z "$NGINX_HEALTH" ]; then
    echo "   ❌ Nginx proxy not working"
    echo "   Checking Nginx logs..."
    docker logs secureai-nginx --tail 20
    echo ""
    echo "   Reloading Nginx..."
    docker exec secureai-nginx nginx -s reload
else
    echo "   ✅ Nginx proxy working: $NGINX_HEALTH"
fi

echo ""

# Step 4: Verify network connectivity
echo "4. Verifying container network..."
docker network inspect secureai-network > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Network exists"
else
    echo "   ❌ Network missing, recreating..."
    docker-compose -f docker-compose.https.yml up -d
fi

echo ""

# Step 5: Final check
echo "5. Final health check..."
FINAL_CHECK=$(curl -s https://guardian.secureai.dev/api/health 2>/dev/null)
if [ -n "$FINAL_CHECK" ]; then
    echo "   ✅ Backend is now available!"
    echo "   Response: $FINAL_CHECK"
else
    echo "   ❌ Backend still unavailable"
    echo "   Please check logs:"
    echo "   - Backend: docker logs secureai-backend"
    echo "   - Nginx: docker logs secureai-nginx"
fi

echo ""
echo "=========================================="
echo "✅ Troubleshooting complete"
echo "=========================================="
