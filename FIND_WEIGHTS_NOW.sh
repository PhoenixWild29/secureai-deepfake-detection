#!/bin/bash
# Comprehensive script to find LAA-Net weights - check EVERYTHING

echo "=========================================="
echo "🔍 COMPREHENSIVE LAA-NET WEIGHTS SEARCH"
echo "=========================================="
echo ""

cd ~/secureai-deepfake-detection/external/laa_net 2>/dev/null || {
    echo "❌ LAA-Net directory not found"
    exit 1
}

echo "1️⃣ Checking for weight files in repository..."
echo "----------------------------------------"
find . -name "*.pth" -o -name "*.pkl" -o -name "*.ckpt" -o -name "*weight*" -o -name "*pretrained*" 2>/dev/null | head -20
echo ""

echo "2️⃣ Checking scripts for download/weight references..."
echo "----------------------------------------"
grep -r -i "weight\|pretrained\|checkpoint\|download" scripts/ 2>/dev/null | head -20
echo ""

echo "3️⃣ Checking config files for weight paths..."
echo "----------------------------------------"
find . -name "*.yaml" -o -name "*.yml" | xargs grep -i "weight\|pretrained\|checkpoint" 2>/dev/null | head -20
echo ""

echo "4️⃣ Checking Python files for weight references..."
echo "----------------------------------------"
grep -r -i "pretrained.*path\|weight.*path\|checkpoint.*path" --include="*.py" . 2>/dev/null | head -20
echo ""

echo "5️⃣ Checking for Hugging Face references..."
echo "----------------------------------------"
grep -r -i "huggingface\|hf_hub\|from_pretrained" --include="*.py" . 2>/dev/null | head -10
echo ""

echo "6️⃣ Checking all URLs in repository..."
echo "----------------------------------------"
grep -roP 'https?://[^\s\)]+' . 2>/dev/null | grep -iE "dropbox|drive|weight|pretrained|download|huggingface" | head -20
echo ""

echo "7️⃣ Checking repository structure..."
echo "----------------------------------------"
ls -la | grep -i "weight\|pretrained\|checkpoint"
find . -maxdepth 2 -type d | grep -i "weight\|pretrained\|checkpoint"
echo ""

echo "✅ Search complete!"
echo ""
echo "📋 Next: Check these sources:"
echo "   - Hugging Face: https://huggingface.co/models?search=laa-net"
echo "   - GitHub Releases: https://github.com/10Ring/LAA-Net/releases"
echo "   - Paper: https://arxiv.org/pdf/2401.13856.pdf"
echo "   - Contact: dat.nguyen@uni.lu"
