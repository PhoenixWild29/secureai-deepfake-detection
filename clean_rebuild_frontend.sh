#!/bin/bash
# Clean rebuild frontend to ensure all changes are applied

echo "=========================================="
echo "🧹 Clean Rebuild Frontend"
echo "=========================================="
echo ""

cd ~/secureai-deepfake-detection/secureai-guardian || exit 1

echo "1. Removing all build artifacts and cache..."
rm -rf dist node_modules/.vite .vite .vite-cache
echo "   ✅ Cleaned"
echo ""

echo "2. Verifying source files..."
if grep -q "cdn.tailwindcss.com" index.html 2>/dev/null; then
    echo "   ⚠️  WARNING: Tailwind CDN still in source index.html!"
else
    echo "   ✅ No Tailwind CDN in source index.html"
fi

if [ -f "index.css" ]; then
    echo "   ✅ index.css exists"
else
    echo "   ❌ index.css missing!"
    exit 1
fi

if [ -f "public/favicon.svg" ]; then
    echo "   ✅ favicon.svg exists in public/"
else
    echo "   ❌ favicon.svg missing from public/!"
    exit 1
fi

if grep -q "import './index.css'" index.tsx 2>/dev/null; then
    echo "   ✅ index.css imported in index.tsx"
else
    echo "   ⚠️  index.css may not be imported in index.tsx"
fi
echo ""

echo "3. Installing dependencies..."
npm install --silent
echo ""

echo "4. Building frontend (production mode)..."
npm run build
echo ""

if [ ! -d "dist" ]; then
    echo "   ❌ Build failed - no dist folder"
    exit 1
fi

echo "5. Verifying build output..."
if grep -q "cdn.tailwindcss.com" dist/index.html 2>/dev/null; then
    echo "   ❌ ERROR: Tailwind CDN still in built index.html!"
    echo "   This should not happen. Checking source..."
    exit 1
else
    echo "   ✅ No Tailwind CDN in built index.html"
fi

if [ -f "dist/favicon.svg" ]; then
    echo "   ✅ favicon.svg exists in dist"
else
    echo "   ⚠️  favicon.svg not in dist (Vite should copy from public/)"
    echo "   Copying manually..."
    cp public/favicon.svg dist/favicon.svg 2>/dev/null || echo "   ❌ Copy failed"
fi

if [ -f "dist/index.html" ]; then
    echo "   ✅ index.html exists in dist"
    echo "   Checking for CSS import..."
    if grep -q "index.css" dist/index.html 2>/dev/null || grep -q "index-" dist/index.html 2>/dev/null; then
        echo "   ✅ CSS file referenced in built HTML"
    else
        echo "   ⚠️  CSS may not be included (check assets folder)"
    fi
else
    echo "   ❌ index.html missing from dist!"
    exit 1
fi
echo ""

echo "6. Restarting Nginx to serve new build..."
cd ..
docker compose -f docker-compose.https.yml restart nginx
echo ""

echo "7. Waiting for Nginx to start..."
sleep 5

echo "8. Testing frontend..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -k https://localhost/ 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ Frontend is accessible (HTTP $HTTP_CODE)"
else
    echo "   ⚠️  Frontend returned HTTP $HTTP_CODE"
fi
echo ""

echo "=========================================="
echo "✅ Clean rebuild complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Clear browser cache (Ctrl+Shift+Delete)"
echo "2. Hard refresh (Ctrl+F5)"
echo "3. Check browser console - should NOT see Tailwind CDN warning"
echo "4. Check browser console - should NOT see favicon 404"