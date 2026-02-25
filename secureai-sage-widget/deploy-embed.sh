#!/bin/bash
# Deploy SecureSage embed.html to Nginx container

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Deploying SecureSage embed.html"
echo "=========================================="
echo ""

# Check if embed.html exists
if [ ! -f "${SCRIPT_DIR}/embed.html" ]; then
    echo "❌ Error: embed.html not found at ${SCRIPT_DIR}/embed.html"
    exit 1
fi

echo "1. Copying embed.html to Nginx container..."
docker cp "${SCRIPT_DIR}/embed.html" secureai-nginx:/usr/share/nginx/html/embed.html

if [ $? -eq 0 ]; then
    echo "   ✅ File copied successfully"
else
    echo "   ❌ Failed to copy file"
    exit 1
fi

echo ""
echo "2. Verifying file..."
docker exec secureai-nginx ls -la /usr/share/nginx/html/embed.html

echo ""
echo "=========================================="
echo "✅ Deployment complete!"
echo "=========================================="
echo ""
echo "Test the embed at: https://guardian.secureai.dev/embed.html"
echo ""
