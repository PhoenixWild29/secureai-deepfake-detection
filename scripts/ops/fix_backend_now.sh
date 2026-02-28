#!/bin/bash
# Quick fix for backend unavailable - run directly on server

echo "=========================================="
echo "🔧 Fixing Backend Service"
echo "=========================================="
echo ""

# Step 1: Check containers
echo "1. Checking containers..."
docker ps --filter "name=secureai" --format "table {{.Names}}\t{{.Status}}"
echo ""

# Step 2: Check if backend is running
echo "2. Checking backend container..."
if docker ps | grep -q "secureai-backend"; then
    echo "   ✅ Backend container is running"
    BACKEND_STATUS=$(docker ps --filter "name=secureai-backend" --format "{{.Status}}")
    echo "   Status: $BACKEND_STATUS"
else
    echo "   ❌ Backend container is NOT running"
    echo "   Starting backend..."
    docker-compose -f docker-compose.https.yml up -d secureai-backend
    echo "   Waiting 10 seconds for backend to start..."
    sleep 10
fi
echo ""

# Step 3: Test backend health directly
echo "3. Testing backend health (internal)..."
BACKEND_HEALTH=$(docker exec secureai-backend curl -s http://localhost:8000/api/health 2>/dev/null)
if [ -n "$BACKEND_HEALTH" ]; then
    echo "   ✅ Backend is healthy"
    echo "   Response: $BACKEND_HEALTH"
else
    echo "   ❌ Backend not responding"
    echo "   Checking backend logs..."
    docker logs secureai-backend --tail 30
    echo ""
    echo "   Attempting restart..."
    docker-compose -f docker-compose.https.yml restart secureai-backend
    sleep 10
    echo "   Retesting..."
    BACKEND_HEALTH=$(docker exec secureai-backend curl -s http://localhost:8000/api/health 2>/dev/null)
    if [ -n "$BACKEND_HEALTH" ]; then
        echo "   ✅ Backend is now healthy after restart"
    else
        echo "   ❌ Backend still not responding - check logs above"
    fi
fi
echo ""

# Step 4: Check Nginx
echo "4. Checking Nginx container..."
if docker ps | grep -q "secureai-nginx"; then
    echo "   ✅ Nginx container is running"
    NGINX_STATUS=$(docker ps --filter "name=secureai-nginx" --format "{{.Status}}")
    echo "   Status: $NGINX_STATUS"
else
    echo "   ❌ Nginx container is NOT running"
    echo "   Starting Nginx..."
    docker-compose -f docker-compose.https.yml up -d nginx
    sleep 5
fi
echo ""

# Step 5: Test Nginx proxy
echo "5. Testing Nginx proxy to backend..."
NGINX_TEST=$(curl -s -k https://localhost/api/health 2>/dev/null || curl -s http://localhost/api/health 2>/dev/null)
if [ -n "$NGINX_TEST" ]; then
    echo "   ✅ Nginx proxy working"
    echo "   Response: $NGINX_TEST"
else
    echo "   ❌ Nginx proxy not working"
    echo "   Checking Nginx logs..."
    docker logs secureai-nginx --tail 20
    echo ""
    echo "   Reloading Nginx config..."
    docker exec secureai-nginx nginx -t
    docker exec secureai-nginx nginx -s reload
fi
echo ""

# Step 6: Final summary
echo "=========================================="
echo "📊 Summary"
echo "=========================================="
echo "Backend container: $(docker ps --filter 'name=secureai-backend' --format '{{.Status}}' || echo 'NOT RUNNING')"
echo "Nginx container: $(docker ps --filter 'name=secureai-nginx' --format '{{.Status}}' || echo 'NOT RUNNING')"
echo ""
echo "Test from browser: https://guardian.secureai.dev/api/health"
echo "=========================================="
