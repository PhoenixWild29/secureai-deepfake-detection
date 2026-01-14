#!/bin/bash
# Test V13 after RAM upgrade to 8 GB

echo "=========================================="
echo "🧪 Testing V13 After RAM Upgrade"
echo "=========================================="
echo ""

# Step 1: Verify RAM upgrade
echo "1️⃣  Verifying RAM upgrade..."
free -h
echo ""

# Step 2: Pull latest code
echo "2️⃣  Pulling latest code..."
cd ~/secureai-deepfake-detection
git pull origin master
echo ""

# Step 3: Copy updated V13 code
echo "3️⃣  Copying updated V13 code to container..."
docker cp ai_model/deepfake_detector_v13.py secureai-backend:/app/ai_model/
echo ""

# Step 4: Copy test script
echo "4️⃣  Copying test script..."
docker cp test_v13_fixed.py secureai-backend:/app/
echo ""

# Step 5: Test V13 loading
echo "5️⃣  Testing V13 loading (this should work now with 8 GB RAM!)..."
echo "   Expected: All 3 models should load successfully"
echo ""
docker exec secureai-backend python3 test_v13_fixed.py
echo ""

# Step 6: Check V13 status
echo "6️⃣  Checking V13 status..."
docker cp check_v13_complete.py secureai-backend:/app/
docker exec secureai-backend python3 check_v13_complete.py
echo ""

echo "=========================================="
echo "✅ Test Complete!"
echo "=========================================="
