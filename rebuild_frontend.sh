#!/bin/bash
# Rebuild and deploy the frontend

echo "=========================================="
echo "🔨 Rebuilding Frontend"
echo "=========================================="
echo ""

cd secureai-guardian || exit 1

echo "1. Installing dependencies (if needed)..."
npm install --silent
echo ""

echo "2. Building frontend for production..."
npm run build
echo ""

if [ -d "dist" ]; then
    echo "3. Frontend built successfully!"
    echo "   Build output: $(du -sh dist | cut -f1)"
    echo ""
    
    echo "4. Copying build to Nginx container..."
    docker cp dist/. secureai-nginx:/usr/share/nginx/html/
    echo "   ✅ Frontend files copied to Nginx"
    echo ""
    
    echo "5. Verifying files in Nginx..."
    docker exec secureai-nginx ls -la /usr/share/nginx/html/ | head -10
    echo ""
    
    echo "=========================================="
    echo "✅ Frontend rebuild complete!"
    echo "=========================================="
    echo ""
    echo "Please:"
    echo "1. Clear your browser cache (Ctrl+Shift+Delete)"
    echo "2. Hard refresh the page (Ctrl+F5)"
    echo "3. Try uploading a video again"
    echo ""
else
    echo "❌ Build failed - dist folder not found"
    exit 1
fi
