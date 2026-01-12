#!/bin/bash
# Check pretrained and logs directories for LAA-Net weights

echo "=========================================="
echo "🔍 Checking Pretrained & Logs Directories"
echo "=========================================="
echo ""

cd ~/secureai-deepfake-detection/external/laa_net 2>/dev/null || {
    echo "❌ LAA-Net directory not found"
    exit 1
}

echo "1️⃣ Checking 'pretrained/' directory..."
echo "----------------------------------------"
if [ -d "pretrained" ]; then
    echo "✅ 'pretrained/' directory exists!"
    echo ""
    echo "Contents:"
    ls -lah pretrained/ 2>/dev/null | head -20
    echo ""
    echo "Looking for .pth files:"
    find pretrained/ -name "*.pth" -o -name "*.pkl" -o -name "*.ckpt" 2>/dev/null
    echo ""
    echo "File sizes:"
    find pretrained/ -type f -name "*.pth" -exec ls -lh {} \; 2>/dev/null
else
    echo "❌ 'pretrained/' directory does not exist"
    echo "   Creating it for future use..."
    mkdir -p pretrained
fi
echo ""

echo "2️⃣ Checking 'logs/' directory..."
echo "----------------------------------------"
if [ -d "logs" ]; then
    echo "✅ 'logs/' directory exists!"
    echo ""
    echo "Contents:"
    ls -lah logs/ 2>/dev/null | head -20
    echo ""
    echo "Looking for model weight files:"
    find logs/ -name "*model_best.pth" -o -name "*checkpoint*.pth" 2>/dev/null | head -10
    echo ""
    echo "File sizes:"
    find logs/ -type f -name "*.pth" -exec ls -lh {} \; 2>/dev/null | head -10
else
    echo "❌ 'logs/' directory does not exist (this is normal - created during training)"
fi
echo ""

echo "3️⃣ Checking config file weight paths..."
echo "----------------------------------------"
echo "Expected weight file from config:"
grep -h "pretrained:" configs/efn4_fpn_hm_adv.yaml configs/efn4_fpn_sbi_adv.yaml 2>/dev/null | grep -v "^#" | head -5
echo ""

echo "4️⃣ Checking if expected weight files exist..."
echo "----------------------------------------"
# Check for the specific weight file mentioned in config
EXPECTED_WEIGHT="pretrained/PoseEfficientNet_EFN_hm100_EFPN_NoBasedCLS_Focal_C3_256Cst100_8FXRayv2_SAM (Adam)_ADV_Eral_OutSigmoid_5e5_model_best.pth"
if [ -f "$EXPECTED_WEIGHT" ]; then
    echo "✅ Found expected weight file!"
    ls -lh "$EXPECTED_WEIGHT"
else
    echo "❌ Expected weight file not found: $EXPECTED_WEIGHT"
    echo ""
    echo "Looking for similar files:"
    find . -name "*PoseEfficientNet*" -o -name "*EFN*" -o -name "*model_best*" 2>/dev/null | head -10
fi
echo ""

echo "5️⃣ Summary of findings..."
echo "----------------------------------------"
PTH_COUNT=$(find . -name "*.pth" 2>/dev/null | wc -l)
echo "Total .pth files found: $PTH_COUNT"

if [ "$PTH_COUNT" -gt 0 ]; then
    echo ""
    echo "All .pth files:"
    find . -name "*.pth" -exec ls -lh {} \; 2>/dev/null | head -20
fi
echo ""

echo "✅ Check complete!"
echo ""
echo "📋 Next steps:"
if [ "$PTH_COUNT" -eq 0 ]; then
    echo "   ❌ No weight files found in repository"
    echo "   → Need to download from external source"
    echo "   → Check: Hugging Face, GitHub Releases, or contact maintainers"
else
    echo "   ✅ Found weight files!"
    echo "   → Verify file sizes (should be 50-200 MB)"
    echo "   → Copy to Docker container"
    echo "   → Update code to load LAA-Net"
fi
