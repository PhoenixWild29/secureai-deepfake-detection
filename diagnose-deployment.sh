#!/bin/bash

echo "=== SecureAI Guardian Deployment Diagnostic ==="
echo ""

echo "1. Checking Docker containers..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "2. Checking if frontend build exists..."
if [ -d "secureai-guardian/dist" ]; then
    echo "✅ Frontend dist folder exists"
    echo "   Files in dist:"
    ls -la secureai-guardian/dist/ | head -10
    echo ""
    if [ -f "secureai-guardian/dist/index.html" ]; then
        echo "✅ index.html exists"
        echo "   First 20 lines of index.html:"
        head -20 secureai-guardian/dist/index.html
    else
        echo "❌ index.html NOT FOUND"
    fi
else
    echo "❌ Frontend dist folder NOT FOUND"
    echo "   You need to run: cd secureai-guardian && npm run build"
fi
echo ""

echo "3. Checking Nginx container logs..."
docker logs secureai-nginx --tail 20
echo ""

echo "4. Checking backend container logs..."
docker logs secureai-backend --tail 20
echo ""

echo "5. Testing backend health endpoint from inside nginx container..."
docker exec secureai-nginx wget -qO- --spider http://secureai-backend:8000/api/health 2>&1 | head -5
echo ""

echo "6. Checking Nginx configuration..."
docker exec secureai-nginx cat /etc/nginx/nginx.conf | grep -A 5 "location /"
echo ""

echo "7. Checking if frontend files are mounted in Nginx..."
docker exec secureai-nginx ls -la /usr/share/nginx/html/ | head -10
echo ""

echo "=== Diagnostic Complete ==="

