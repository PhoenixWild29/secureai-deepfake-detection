#!/bin/bash
# Test the upload endpoint to ensure it's accessible

echo "=========================================="
echo "🧪 Testing Upload Endpoint"
echo "=========================================="
echo ""

echo "1. Testing /api/analyze endpoint (OPTIONS preflight)..."
curl -X OPTIONS -v -k https://guardian.secureai.dev/api/analyze 2>&1 | grep -i "access-control\|204\|200" || echo "Preflight test"
echo ""
echo ""

echo "2. Testing /api/analyze endpoint (GET - should return method not allowed)..."
curl -X GET -s -k https://guardian.secureai.dev/api/analyze
echo ""
echo ""

echo "3. Checking CORS headers on /api/analyze..."
curl -X OPTIONS -s -I -k https://guardian.secureai.dev/api/analyze | grep -i "access-control" || echo "No CORS headers"
echo ""
echo ""

echo "4. Testing backend directly (should require POST with file)..."
docker exec secureai-backend curl -s -X GET http://localhost:8000/api/analyze
echo ""
echo ""

echo "5. Checking if frontend can reach backend (simulating browser request)..."
curl -s -k -H "Origin: https://guardian.secureai.dev" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: content-type" \
     -X OPTIONS \
     https://guardian.secureai.dev/api/analyze | head -5
echo ""
echo ""

echo "=========================================="
echo "✅ Upload endpoint test complete"
echo "=========================================="
echo ""
echo "If you see CORS headers and 204/200 responses,"
echo "the frontend should now be able to upload videos!"
echo "=========================================="
