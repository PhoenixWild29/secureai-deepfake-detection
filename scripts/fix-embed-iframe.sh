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
echo "2. Copying updated nginx config to container..."
# Copy to temp location first
docker cp nginx.https.conf secureai-nginx:/tmp/nginx.conf.new

if [ $? -ne 0 ]; then
    echo "   ❌ Failed to copy nginx config"
    exit 1
fi

# Use cat to overwrite the file (works even when file is in use)
docker exec secureai-nginx sh -c "cat /tmp/nginx.conf.new > /etc/nginx/nginx.conf"

if [ $? -ne 0 ]; then
    echo "   ❌ Failed to update nginx config"
    exit 1
fi

# Clean up temp file
docker exec secureai-nginx rm -f /tmp/nginx.conf.new

echo "   ✅ Config updated successfully"

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
