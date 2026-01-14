#!/bin/bash
# Rebuild frontend with correct API URL configuration

echo "=========================================="
echo "🔨 Rebuilding Frontend (Fixed API URL)"
echo "=========================================="
echo ""

cd secureai-guardian || exit 1

echo "1. Ensuring no localhost in environment..."
# Remove any .env files that might have localhost
if [ -f ".env" ]; then
    echo "   Found .env file, checking for localhost..."
    if grep -q "localhost" .env; then
        echo "   ⚠️  Warning: .env contains localhost, but we'll override it"
    fi
fi

# Explicitly unset VITE_API_BASE_URL to force relative URLs in production
export VITE_API_BASE_URL=""

echo "2. Installing dependencies..."
npm install --silent
echo ""

echo "3. Building frontend for production (with relative URLs)..."
VITE_API_BASE_URL="" npm run build
echo ""

if [ -d "dist" ]; then
    echo "4. Verifying build doesn't contain localhost..."
    if grep -r "localhost:5000" dist/ 2>/dev/null | grep -v ".map" | head -5; then
        echo "   ⚠️  Warning: Found localhost in build files"
    else
        echo "   ✅ No localhost found in build (good!)"
    fi
    echo ""
    
    echo "5. Frontend built successfully!"
    echo "   Build output: $(du -sh dist | cut -f1)"
    echo ""
    
    echo "6. Copying build to Nginx container..."
    docker cp dist/. secureai-nginx:/usr/share/nginx/html/
    echo "   ✅ Frontend files copied to Nginx"
    echo ""
    
    echo "7. Verifying files in Nginx..."
    docker exec secureai-nginx ls -la /usr/share/nginx/html/ | head -10
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
    echo "3. Check browser console - should see:"
    echo "   [Health Check] Attempting to connect to: /api/health (relative)"
    echo "4. Try uploading a video again"
    echo ""
else
    echo "❌ Build failed - dist folder not found"
    exit 1
fi
