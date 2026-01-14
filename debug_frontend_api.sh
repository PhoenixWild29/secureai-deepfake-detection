#!/bin/bash
# Debug what the frontend is actually trying to access

echo "=========================================="
echo "🔍 Debugging Frontend API Calls"
echo "=========================================="
echo ""

echo "1. Checking what URL the frontend should use..."
echo "   In production, API_BASE_URL should be empty (relative URLs)"
echo "   This means requests go to: /api/health"
echo ""

echo "2. Testing the exact URL the frontend would use..."
echo "   Testing: https://guardian.secureai.dev/api/health"
RESPONSE=$(curl -s -k https://guardian.secureai.dev/api/health)
echo "   Response: $RESPONSE"
echo ""

echo "3. Testing with CORS preflight (OPTIONS request)..."
curl -X OPTIONS -v -k \
  -H "Origin: https://guardian.secureai.dev" \
  -H "Access-Control-Request-Method: GET" \
  https://guardian.secureai.dev/api/health 2>&1 | grep -i "access-control\|204\|200" || echo "Preflight test"
echo ""

echo "4. Checking browser console simulation..."
echo "   Open browser DevTools (F12)"
echo "   Go to Network tab"
echo "   Try to upload a video"
echo "   Look for failed requests to /api/health"
echo ""

echo "5. Checking if there's a JavaScript error..."
echo "   In browser console, check for:"
echo "   - CORS errors"
echo "   - Network errors"
echo "   - 'Health check error' messages"
echo ""

echo "6. Testing from browser perspective (with Origin header)..."
curl -v -k \
  -H "Origin: https://guardian.secureai.dev" \
  -H "Referer: https://guardian.secureai.dev/" \
  https://guardian.secureai.dev/api/health 2>&1 | grep -E "HTTP|access-control|status" | head -10
echo ""

echo "=========================================="
echo "📋 Next Steps:"
echo "=========================================="
echo "1. Open browser DevTools (F12)"
echo "2. Go to Console tab - look for errors"
echo "3. Go to Network tab - look for /api/health request"
echo "4. Check if request is being made and what the response is"
echo "5. Share the error message from Console tab"
echo "=========================================="
