#!/bin/bash
# Check if frontend needs to be rebuilt

echo "=========================================="
echo "🔍 Checking Frontend Build Status"
echo "=========================================="
echo ""

echo "1. Checking if dist folder exists locally..."
if [ -d "secureai-guardian/dist" ]; then
    echo "   ✅ Local dist folder exists"
    echo "   Size: $(du -sh secureai-guardian/dist | cut -f1)"
    echo "   Last modified: $(stat -c %y secureai-guardian/dist 2>/dev/null || stat -f %Sm secureai-guardian/dist 2>/dev/null || echo 'unknown')"
else
    echo "   ❌ Local dist folder does NOT exist"
    echo "   → Frontend needs to be built"
fi
echo ""

echo "2. Checking files in Nginx container..."
NGINX_FILES=$(docker exec secureai-nginx ls -la /usr/share/nginx/html/ 2>/dev/null | wc -l)
if [ "$NGINX_FILES" -gt 3 ]; then
    echo "   ✅ Nginx has frontend files ($NGINX_FILES files)"
    docker exec secureai-nginx ls -la /usr/share/nginx/html/ | head -5
else
    echo "   ❌ Nginx container has no frontend files"
    echo "   → Frontend needs to be deployed"
fi
echo ""

echo "3. Checking if index.html exists in Nginx..."
if docker exec secureai-nginx test -f /usr/share/nginx/html/index.html; then
    echo "   ✅ index.html exists in Nginx"
    echo "   File size: $(docker exec secureai-nginx stat -c %s /usr/share/nginx/html/index.html 2>/dev/null || echo 'unknown') bytes"
else
    echo "   ❌ index.html NOT found in Nginx"
    echo "   → Frontend needs to be deployed"
fi
echo ""

echo "4. Testing if frontend is accessible..."
FRONTEND_TEST=$(curl -s -k https://guardian.secureai.dev/ | head -20 | grep -i "html\|react\|vite" || echo "No HTML content")
if [ -n "$FRONTEND_TEST" ]; then
    echo "   ✅ Frontend is accessible"
else
    echo "   ❌ Frontend not accessible or empty"
fi
echo ""

echo "=========================================="
echo "📊 Summary"
echo "=========================================="
echo "If dist folder is missing or old, run: ./rebuild_frontend.sh"
echo "=========================================="
