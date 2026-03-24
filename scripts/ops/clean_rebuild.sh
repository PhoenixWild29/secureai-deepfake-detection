#!/bin/bash
# Clean rebuild to fix any build issues

echo "=========================================="
echo "🧹 Clean Rebuild Frontend"
echo "=========================================="
echo ""

cd secureai-guardian || exit 1

echo "1. Removing all build artifacts..."
rm -rf dist node_modules/.vite .vite
echo "   ✅ Cleaned"
echo ""

echo "2. Ensuring production build uses relative URLs..."
unset VITE_API_BASE_URL
export VITE_API_BASE_URL=""
echo "   VITE_API_BASE_URL: '$VITE_API_BASE_URL' (empty = relative URLs)"
echo ""

echo "3. Installing dependencies (fresh install)..."
rm -rf node_modules package-lock.json
# IMPORTANT:
# - We must install devDependencies because Vite is a devDependency.
# - Do NOT set NODE_ENV=production during install, or npm may omit dev deps.
npm install --include=dev
echo ""

echo "4. Verifying vite is installed..."
if [ -f "node_modules/.bin/vite" ]; then
    echo "   ✅ Vite found in node_modules"
else
    echo "   ❌ Vite not found, installing..."
    npm install vite --save-dev
fi
echo ""

echo "5. Building frontend (production mode)..."
NODE_ENV=production VITE_API_BASE_URL="" npm run build
echo ""

if [ -d "dist" ]; then
    echo "6. Verifying build..."
    if [ -f "dist/index.html" ]; then
        echo "   ✅ index.html exists"
    else
        echo "   ❌ index.html missing!"
        exit 1
    fi
    
    if [ -d "dist/assets" ]; then
        ASSET_COUNT=$(ls dist/assets/*.js 2>/dev/null | wc -l)
        echo "   ✅ Found $ASSET_COUNT JavaScript files"
    else
        echo "   ❌ assets directory missing!"
        exit 1
    fi
    echo ""
    
    echo "7. Checking for localhost references..."
    LOCALHOST_FOUND=$(grep -r "localhost:5000" dist/ 2>/dev/null | grep -v ".map" | wc -l)
    if [ "$LOCALHOST_FOUND" -gt 0 ]; then
        echo "   ⚠️  Warning: Found $LOCALHOST_FOUND localhost references"
        echo "   First few:"
        grep -r "localhost:5000" dist/ 2>/dev/null | grep -v ".map" | head -3
    else
        echo "   ✅ No localhost found (good!)"
    fi
    echo ""
    
    echo "8. Restarting Nginx to pick up new dist/ (served via volume mount)..."
    # Prefer Docker Compose V2 CLI: `docker compose`
    if docker compose version >/dev/null 2>&1; then
        docker compose -f ../docker-compose.https.yml up -d --force-recreate nginx
    else
        echo "   ⚠️  'docker compose' not found. Trying legacy docker-compose..."
        docker-compose -f ../docker-compose.https.yml up -d --force-recreate nginx
    fi
    echo "   ✅ Nginx restarted"
    echo ""
    
    echo "9. Testing Nginx..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -k https://guardian.secureai.dev/)
    if [ "$HTTP_CODE" = "200" ]; then
        echo "   ✅ Nginx is serving files (HTTP $HTTP_CODE)"
    else
        echo "   ⚠️  Nginx returned HTTP $HTTP_CODE"
    fi
    echo ""
    
    echo "=========================================="
    echo "✅ Clean rebuild complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Clear browser cache completely"
    echo "2. Hard refresh (Ctrl+F5)"
    echo "3. Check console - should NOT see SyntaxError"
    echo "4. Check console - should see relative URLs"
    echo ""
else
    echo "❌ Build failed - no dist folder"
    exit 1
fi
