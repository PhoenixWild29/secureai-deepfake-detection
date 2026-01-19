#!/bin/bash
# Fix iframe embedding for SecureSage embed.html - Direct Docker approach
# This works regardless of where the project is located

echo "=========================================="
echo "Fixing iframe embedding for SecureSage"
echo "=========================================="
echo ""

# Find the project directory (try common locations)
PROJECT_DIR=""
for dir in /root/secureai-deepfake-detection /root/SecureAI-DeepFake-Detection ~/secureai-deepfake-detection /opt/secureai-deepfake-detection; do
    if [ -d "$dir" ] && [ -f "$dir/nginx.https.conf" ]; then
        PROJECT_DIR="$dir"
        echo "✅ Found project at: $PROJECT_DIR"
        break
    fi
done

if [ -z "$PROJECT_DIR" ]; then
    echo "⚠️  Project directory not found in common locations"
    echo "   Will update Nginx config directly from current directory"
    PROJECT_DIR="."
fi

# Check if nginx.https.conf exists
if [ ! -f "$PROJECT_DIR/nginx.https.conf" ]; then
    echo "❌ Error: nginx.https.conf not found!"
    echo "   Please run this script from the project directory"
    exit 1
fi

echo ""
echo "1. Copying updated nginx config to container..."
docker cp "$PROJECT_DIR/nginx.https.conf" secureai-nginx:/etc/nginx/nginx.conf

if [ $? -ne 0 ]; then
    echo "   ❌ Failed to copy nginx config"
    echo "   Make sure the secureai-nginx container is running"
    exit 1
fi

echo "   ✅ Config copied"

echo ""
echo "2. Testing nginx configuration..."
docker exec secureai-nginx nginx -t

if [ $? -ne 0 ]; then
    echo "   ❌ Nginx config test failed!"
    echo "   Check the error above"
    exit 1
fi

echo "   ✅ Config is valid"

echo ""
echo "3. Reloading Nginx..."
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
