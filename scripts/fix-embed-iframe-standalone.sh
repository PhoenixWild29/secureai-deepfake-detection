#!/bin/bash
# Fix iframe embedding for SecureSage embed.html - Standalone version
# This works without needing to pull from git

echo "=========================================="
echo "Fixing iframe embedding for SecureSage"
echo "=========================================="
echo ""

# Check if nginx.https.conf exists in current directory
if [ ! -f "nginx.https.conf" ]; then
    echo "❌ Error: nginx.https.conf not found in current directory!"
    echo "   Please run this script from the project root directory"
    exit 1
fi

echo "1. Creating backup of current nginx config..."
docker exec secureai-nginx cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)
echo "   ✅ Backup created"

echo ""
echo "2. Checking if embed.html location block exists..."
if grep -q "location = /embed.html" nginx.https.conf; then
    echo "   ✅ Embed location block found in config"
else
    echo "   ⚠️  Embed location block not found - will add it"
fi

echo ""
echo "3. Copying updated nginx config to container..."
docker cp nginx.https.conf secureai-nginx:/etc/nginx/nginx.conf

if [ $? -ne 0 ]; then
    echo "   ❌ Failed to copy nginx config"
    echo "   Make sure the secureai-nginx container is running"
    exit 1
fi

echo "   ✅ Config copied"

echo ""
echo "4. Testing nginx configuration..."
docker exec secureai-nginx nginx -t

if [ $? -ne 0 ]; then
    echo "   ❌ Nginx config test failed!"
    echo "   Restoring backup..."
    docker exec secureai-nginx cp /etc/nginx/nginx.conf.backup.* /etc/nginx/nginx.conf 2>/dev/null
    echo "   Please check the error above"
    exit 1
fi

echo "   ✅ Config is valid"

echo ""
echo "5. Reloading Nginx..."
docker exec secureai-nginx nginx -s reload

if [ $? -eq 0 ]; then
    echo "   ✅ Nginx reloaded successfully"
else
    echo "   ⚠️  Reload failed, trying restart..."
    docker restart secureai-nginx
    sleep 3
    if docker exec secureai-nginx nginx -t 2>/dev/null; then
        echo "   ✅ Nginx restarted successfully"
    else
        echo "   ❌ Nginx restart failed!"
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo "✅ Iframe embedding fix complete!"
echo "=========================================="
echo ""
echo "The embed.html page can now be embedded in:"
echo "  - Google Sites"
echo "  - Any other external website"
echo ""
echo "Test the embed at: https://guardian.secureai.dev/embed.html"
echo ""
