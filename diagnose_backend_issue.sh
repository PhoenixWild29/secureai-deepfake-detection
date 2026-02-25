#!/bin/bash
# Comprehensive backend diagnosis

echo "=========================================="
echo "🔍 Backend Connection Diagnosis"
echo "=========================================="
echo ""

echo "1. Backend container health (direct)..."
docker exec secureai-backend curl -s http://localhost:8000/api/health | jq . || docker exec secureai-backend curl -s http://localhost:8000/api/health
echo ""
echo ""

echo "2. Testing Nginx -> Backend connectivity..."
docker exec secureai-nginx wget -qO- http://secureai-backend:8000/api/health 2>/dev/null || \
docker exec secureai-nginx curl -s http://secureai-backend:8000/api/health
echo ""
echo ""

echo "3. Testing external endpoint (via HTTPS)..."
EXTERNAL_RESPONSE=$(curl -s -k https://guardian.secureai.dev/api/health 2>&1)
if [ -n "$EXTERNAL_RESPONSE" ]; then
    echo "$EXTERNAL_RESPONSE"
else
    echo "❌ No response from external endpoint"
fi
echo ""
echo ""

echo "4. Testing external endpoint (via HTTP, should redirect)..."
HTTP_RESPONSE=$(curl -s -I http://guardian.secureai.dev/api/health 2>&1 | head -5)
echo "$HTTP_RESPONSE"
echo ""
echo ""

echo "5. Checking Nginx configuration..."
docker exec secureai-nginx nginx -t 2>&1
echo ""
echo ""

echo "6. Recent Nginx error logs..."
docker logs secureai-nginx --tail 30 2>&1 | grep -i "error\|failed\|denied" | tail -10 || echo "No errors found"
echo ""
echo ""

echo "7. Recent backend logs (last 20 lines)..."
docker logs secureai-backend --tail 20 2>&1 | tail -10
echo ""
echo ""

echo "8. Checking container network..."
docker network inspect secureai-network 2>/dev/null | grep -E "(Name|secureai)" | head -10 || echo "Network check failed"
echo ""
echo ""

echo "9. Testing CORS headers on health endpoint..."
curl -s -I -k https://guardian.secureai.dev/api/health | grep -i "access-control\|cors" || echo "No CORS headers in response"
echo ""
echo ""

echo "10. Checking if backend is listening on port 8000..."
docker exec secureai-backend netstat -tlnp 2>/dev/null | grep 8000 || docker exec secureai-backend ss -tlnp 2>/dev/null | grep 8000 || echo "Cannot check port (netstat/ss not available)"
echo ""
echo ""

echo "=========================================="
echo "📊 Summary"
echo "=========================================="
echo "If step 1 works but step 3 doesn't:"
echo "  → Nginx proxy issue"
echo ""
echo "If step 2 works but step 3 doesn't:"
echo "  → External access/firewall issue"
echo ""
echo "If all steps work but frontend still fails:"
echo "  → CORS or frontend configuration issue"
echo "=========================================="
