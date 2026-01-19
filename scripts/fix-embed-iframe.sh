#!/bin/bash
# Fix iframe embedding for SecureSage embed.html
# This updates Nginx to allow embedding from external sites like Google Sites

echo "=========================================="
echo "Fixing iframe embedding for SecureSage"
echo "=========================================="
echo ""

# Navigate to project directory (try multiple common paths)
if [ -d ~/secureai-deepfake-detection ]; then
    cd ~/secureai-deepfake-detection
elif [ -d /root/secureai-deepfake-detection ]; then
    cd /root/secureai-deepfake-detection
else
    echo "❌ Error: Project directory not found!"
    exit 1
fi

echo "1. Fixing git conflicts and pulling latest changes..."
# Check if there are local changes that would block the pull
if git diff --quiet scripts/fix-embed-iframe.sh 2>/dev/null; then
    # No local changes, safe to pull
    git pull origin master
else
    echo "   ⚠️  Local changes detected in scripts/fix-embed-iframe.sh"
    echo "   Discarding local changes to get latest version..."
    git checkout -- scripts/fix-embed-iframe.sh
    # Now pull should work
    git pull origin master
fi

if [ $? -ne 0 ]; then
    echo "   ❌ Git pull failed. Please check manually."
    exit 1
fi

echo "   ✅ Latest changes pulled successfully"

echo ""
echo "2. Verifying nginx config file exists..."
if [ ! -f "nginx.https.conf" ]; then
    echo "   ❌ nginx.https.conf not found in current directory"
    exit 1
fi

echo "   ✅ Config file found"

echo ""
echo "3. Restarting Nginx container to pick up config changes..."
# The nginx config is mounted as a volume from the host, so we just need to restart
docker restart secureai-nginx

if [ $? -ne 0 ]; then
    echo "   ❌ Failed to restart nginx container"
    exit 1
fi

# Wait for nginx to start
sleep 3

echo "   ✅ Nginx container restarted"

echo ""
echo "4. Testing nginx configuration..."
docker exec secureai-nginx nginx -t

if [ $? -ne 0 ]; then
    echo "   ❌ Nginx config test failed!"
    exit 1
fi

echo "   ✅ Config is valid"

echo ""
echo "5. Verifying Nginx is running..."
if docker exec secureai-nginx nginx -t > /dev/null 2>&1; then
    echo "   ✅ Nginx is running with valid config"
else
    echo "   ❌ Nginx config test failed!"
    exit 1
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
