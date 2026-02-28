#!/bin/bash
# Verification script for frontend rebuild

echo "=========================================="
echo "🔍 Verifying Frontend Rebuild"
echo "=========================================="
echo ""

cd ~/secureai-deepfake-detection || exit 1

echo "1. Checking Nginx container status..."
docker compose -f docker-compose.https.yml ps nginx
echo ""

echo "2. Checking Nginx logs (last 20 lines)..."
docker compose -f docker-compose.https.yml logs --tail=20 nginx
echo ""

echo "3. Testing if frontend is accessible..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -k https://localhost/ 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ Frontend is accessible (HTTP $HTTP_CODE)"
else
    echo "   ⚠️  Frontend returned HTTP $HTTP_CODE"
fi
echo ""

echo "4. Checking if dist folder exists..."
if [ -d "secureai-guardian/dist" ]; then
    echo "   ✅ dist folder exists"
    echo "   Files in dist:"
    ls -la secureai-guardian/dist/ | head -10
else
    echo "   ❌ dist folder missing!"
fi
echo ""

echo "5. Verifying Tailwind CDN removal..."
if grep -r "cdn.tailwindcss.com" secureai-guardian/dist/ 2>/dev/null | head -3; then
    echo "   ⚠️  WARNING: Tailwind CDN still found in build!"
else
    echo "   ✅ No Tailwind CDN found (good!)"
fi
echo ""

echo "6. Checking for favicon..."
if [ -f "secureai-guardian/dist/favicon.svg" ]; then
    echo "   ✅ Favicon exists in dist"
elif [ -f "secureai-guardian/public/favicon.svg" ]; then
    echo "   ⚠️  Favicon exists in public but not in dist (may need rebuild)"
else
    echo "   ❌ Favicon missing!"
fi
echo ""

echo "7. Checking files in Nginx container..."
docker compose -f docker-compose.https.yml exec nginx ls -la /usr/share/nginx/html/ 2>/dev/null | head -10 || echo "   ⚠️  Could not access Nginx container"
echo ""

echo "8. Checking if index.html exists in Nginx..."
if docker compose -f docker-compose.https.yml exec nginx test -f /usr/share/nginx/html/index.html 2>/dev/null; then
    echo "   ✅ index.html exists in Nginx"
else
    echo "   ❌ index.html missing in Nginx!"
fi
echo ""

echo "=========================================="
echo "✅ Verification complete!"
echo "=========================================="