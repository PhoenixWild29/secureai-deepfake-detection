#!/bin/bash
# Test backend connection from multiple angles

echo "=========================================="
echo "🔍 Testing Backend Connection"
echo "=========================================="
echo ""

echo "1. Testing backend directly (inside container)..."
docker exec secureai-backend curl -s http://localhost:8000/api/health
echo ""
echo ""

echo "2. Testing backend via container network..."
docker exec secureai-nginx curl -s http://secureai-backend:8000/api/health
echo ""
echo ""

echo "3. Testing via Nginx proxy (localhost)..."
curl -s -k https://localhost/api/health || curl -s http://localhost/api/health
echo ""
echo ""

echo "4. Testing via Nginx proxy (external domain)..."
curl -s -k https://guardian.secureai.dev/api/health
echo ""
echo ""

echo "5. Checking Nginx error logs..."
docker logs secureai-nginx --tail 20 2>&1 | grep -i error || echo "No errors in Nginx logs"
echo ""

echo "6. Checking Nginx access logs..."
docker logs secureai-nginx --tail 10 2>&1 | grep -i "/api" || echo "No recent /api requests"
echo ""

echo "7. Testing CORS headers..."
curl -s -I -k https://guardian.secureai.dev/api/health | grep -i "access-control" || echo "No CORS headers found"
echo ""

echo "8. Checking if containers are on same network..."
docker network inspect secureai-network 2>/dev/null | grep -A 5 "Containers" || echo "Network check failed"
echo ""

echo "=========================================="
echo "✅ Connection test complete"
echo "=========================================="
