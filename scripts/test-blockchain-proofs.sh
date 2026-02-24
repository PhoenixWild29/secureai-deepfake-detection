#!/bin/bash
# Test script to verify blockchain proofs are working

echo "=========================================="
echo "🧪 Testing Blockchain Proofs (SOL_TX)"
echo "=========================================="
echo ""

echo "1. Checking backend status..."
docker ps --filter "name=secureai-backend" --format "table {{.Names}}\t{{.Status}}"
echo ""

echo "2. Checking for blocking function errors (should be none)..."
BLOCKING_ERRORS=$(docker logs secureai-backend --tail 100 2>&1 | grep -i "blocking functions" | wc -l)
if [ "$BLOCKING_ERRORS" -eq 0 ]; then
    echo "   ✅ No blocking function errors found"
else
    echo "   ⚠️  Found $BLOCKING_ERRORS blocking function error(s)"
    docker logs secureai-backend --tail 100 2>&1 | grep -i "blocking functions" | tail -3
fi
echo ""

echo "3. Checking recent blockchain-related logs..."
docker logs secureai-backend --tail 50 2>&1 | grep -i "blockchain\|solana" | tail -10 || echo "   (No blockchain logs yet - will appear after analysis)"
echo ""

echo "4. Backend health check..."
docker exec secureai-backend curl -s http://localhost:8000/api/health | head -1
echo ""

echo "=========================================="
echo "📋 Next Steps:"
echo "=========================================="
echo ""
echo "1. Upload a video for analysis in the web interface"
echo "2. Wait for analysis to complete"
echo "3. Check the Dashboard - 'Proofs' counter should increment"
echo "4. Run this command to see blockchain logs:"
echo "   docker logs secureai-backend --tail 100 | grep -i blockchain"
echo ""
