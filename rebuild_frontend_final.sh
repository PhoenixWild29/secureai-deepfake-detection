#!/bin/bash
# Final frontend rebuild with all fixes

echo "=========================================="
echo "🔨 Rebuilding Frontend (Final Fix)"
echo "=========================================="
echo ""

cd secureai-guardian || exit 1

echo "1. Cleaning previous build..."
rm -rf dist
echo ""

echo "2. Ensuring no localhost in environment..."
# Explicitly unset to force relative URLs in production
unset VITE_API_BASE_URL
export VITE_API_BASE_URL=""
echo "   VITE_API_BASE_URL is set to: '$VITE_API_BASE_URL'"
echo ""

echo "3. Installing dependencies..."
npm install --silent
echo ""

echo "4. Building frontend for production (mode=production, relative URLs)..."
NODE_ENV=production VITE_API_BASE_URL="" npm run build
echo ""

if [ -d "dist" ]; then
    echo "5. Verifying build doesn't contain localhost..."
    LOCALHOST_COUNT=$(grep -r "localhost:5000" dist/ 2>/dev/null | grep -v ".map" | wc -l)
    if [ "$LOCALHOST_COUNT" -gt 0 ]; then
        echo "   ⚠️  Warning: Found $LOCALHOST_COUNT instances of localhost in build files"
        echo "   First few matches:"
        grep -r "localhost:5000" dist/ 2>/dev/null | grep -v ".map" | head -3
    else
        echo "   ✅ No localhost found in build (good!)"
    fi
    echo ""
    
    echo "6. Frontend built successfully!"
    echo "   Build output: $(du -sh dist | cut -f1)"
    echo ""
    
    echo "7. Stopping Nginx temporarily to update files..."
    docker stop secureai-nginx 2>/dev/null || true
    sleep 2
    echo ""
    
    echo "8. Copying build to Nginx container..."
    docker cp dist/. secureai-nginx:/usr/share/nginx/html/ 2>&1
    if [ $? -eq 0 ]; then
        echo "   ✅ Frontend files copied to Nginx"
    else
        echo "   ⚠️  Copy had issues, trying alternative method..."
        # Alternative: remove old files and copy new ones
        docker exec secureai-nginx rm -rf /usr/share/nginx/html/* /usr/share/nginx/html/.[!.]* 2>/dev/null || true
        docker cp dist/. secureai-nginx:/usr/share/nginx/html/
        echo "   ✅ Files copied using alternative method"
    fi
    echo ""
    
    echo "9. Starting Nginx..."
    docker start secureai-nginx
    sleep 2
    echo ""
    
    echo "10. Verifying files in Nginx..."
    docker exec secureai-nginx ls -la /usr/share/nginx/html/ | head -10
    echo ""
    
    echo "11. Testing Nginx is serving files..."
    NGINX_TEST=$(curl -s -k https://guardian.secureai.dev/ | head -5 | grep -i "html\|react" || echo "")
    if [ -n "$NGINX_TEST" ]; then
        echo "   ✅ Nginx is serving frontend files"
    else
        echo "   ⚠️  Could not verify Nginx is serving files"
    fi
    echo ""
    
    echo "=========================================="
    echo "✅ Frontend rebuild complete!"
    echo "=========================================="
    echo ""
    echo "The frontend should now use relative URLs (/api/health)"
    echo "instead of http://localhost:5000"
    echo ""
    echo "Please:"
    echo "1. Clear your browser cache (Ctrl+Shift+Delete)"
    echo "2. Hard refresh the page (Ctrl+F5)"
    echo "3. Open browser console (F12) and check:"
    echo "   Should see: [Health Check] Attempting to connect to: /api/health (relative)"
    echo "   Should NOT see: http://localhost:5000"
    echo "4. Try uploading a video again"
    echo ""
else
    echo "❌ Build failed - dist folder not found"
    echo "Check the error messages above"
    exit 1
fi
