#!/bin/bash
# Fix iframe embedding for SecureSage embed.html
# This updates Nginx to allow embedding from external sites like Google Sites

echo "=========================================="
echo "Fixing iframe embedding for SecureSage"
echo "=========================================="
echo ""

# Navigate to project directory
cd /root/secureai-deepfake-detection || exit 1

echo "1. Pulling latest changes..."
git pull origin master

echo ""
echo "2. Copying updated nginx config to container..."
docker cp nginx.https.conf secureai-nginx:/etc/nginx/nginx.conf

if [ $? -ne 0 ]; then
    echo "   ❌ Failed to copy nginx config"
    exit 1
fi

echo "   ✅ Config copied"

echo ""
echo "3. Testing nginx configuration..."
docker exec secureai-nginx nginx -t

if [ $? -ne 0 ]; then
    echo "   ❌ Nginx config test failed!"
    exit 1
fi

echo "   ✅ Config is valid"

echo ""
echo "4. Reloading Nginx..."
docker exec secureai-nginx nginx -s reload

if [ $? -eq 0 ]; then
    echo "   ✅ Nginx reloaded successfully"
else
    echo "   ⚠️  Reload failed, trying restart..."
    docker restart secureai-nginx
    sleep 2
    docker exec secureai-nginx nginx -t
    if [ $? -eq 0 ]; then
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
