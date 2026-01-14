#!/bin/bash
# Script to check LAA-Net README for correct download links

echo "=========================================="
echo "Checking LAA-Net README for Download Links"
echo "=========================================="
echo ""

cd ~/secureai-deepfake-detection/external/laa_net 2>/dev/null || {
    echo "❌ LAA-Net directory not found"
    echo "Run: cd ~/secureai-deepfake-detection/external && git clone https://github.com/10Ring/LAA-Net laa_net"
    exit 1
}

echo "📄 Reading README.md..."
echo ""

# Search for pretrained weights section
echo "=== Searching for 'pretrained' or 'weight' mentions ==="
grep -i -n -A 10 -B 5 "pretrained\|weight\|download\|dropbox\|google.*drive" README.md | head -50
echo ""

# Search for URLs
echo "=== Searching for URLs ==="
grep -oP 'https?://[^\s\)]+' README.md | grep -i -E "dropbox|drive|weight|pretrained|download" | head -20
echo ""

# Check for releases or download sections
echo "=== Checking for download/release sections ==="
grep -i -n -A 20 "##.*download\|##.*release\|##.*pretrained\|##.*weight" README.md | head -50
echo ""

# Check scripts directory
echo "=== Checking scripts directory ==="
if [ -d scripts ]; then
    echo "Scripts found:"
    ls -la scripts/ | head -20
    echo ""
    echo "Checking for download commands in scripts:"
    grep -i "download\|wget\|curl\|dropbox\|weight" scripts/*.sh 2>/dev/null | head -20
fi
echo ""

# Check for any download scripts
echo "=== Searching for download scripts ==="
find . -maxdepth 2 -name "*download*" -o -name "*weight*" -o -name "*pretrained*" 2>/dev/null
echo ""

echo "✅ README check complete!"
echo ""
echo "📋 Next steps:"
echo "1. Review the URLs found above"
echo "2. Try accessing them in a browser"
echo "3. Share any working links with me"
