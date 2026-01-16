#!/bin/bash
# Script to update X cookies file and restart backend
# Usage: ./update_x_cookies.sh /path/to/new/x_cookies.txt

set -e

if [ $# -lt 1 ]; then
    echo "Usage: $0 <path_to_new_cookies_file>"
    echo ""
    echo "Example:"
    echo "  1. Export cookies from browser extension"
    echo "  2. Upload to server: scp x_cookies.txt root@guardian.secureai.dev:/tmp/x_cookies.txt"
    echo "  3. Run: $0 /tmp/x_cookies.txt"
    exit 1
fi

NEW_COOKIES_FILE="$1"
COOKIES_DEST="/root/secureai-deepfake-detection/secrets/x_cookies.txt"

if [ ! -f "$NEW_COOKIES_FILE" ]; then
    echo "❌ Error: Cookies file not found: $NEW_COOKIES_FILE"
    exit 1
fi

echo "🔄 Updating X cookies..."
echo "=========================================="

# 1. Backup old cookies
if [ -f "$COOKIES_DEST" ]; then
    BACKUP_FILE="${COOKIES_DEST}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$COOKIES_DEST" "$BACKUP_FILE"
    echo "✔ Backed up old cookies to: $BACKUP_FILE"
fi

# 2. Copy new cookies
cp "$NEW_COOKIES_FILE" "$COOKIES_DEST"
echo "✔ Copied new cookies to: $COOKIES_DEST"

# 3. Set permissions
chmod 600 "$COOKIES_DEST"
chown 1000:1000 "$COOKIES_DEST"  # Match container app user
echo "✔ Set permissions (600, owner 1000:1000)"

# 4. Verify cookies file
echo ""
echo "📋 Verifying cookies file..."
python3 /root/secureai-deepfake-detection/scripts/check_cookie_expiration.py || echo "⚠️  Cookie check had warnings"

# 5. Restart backend
echo ""
echo "🔄 Restarting backend to use new cookies..."
cd /root/secureai-deepfake-detection
docker compose -f docker-compose.https.yml restart secureai-backend

# 6. Wait and verify
sleep 5
echo ""
echo "✅ Verifying backend is running..."
if docker ps | grep -q secureai-backend; then
    echo "✔ Backend is running"
    
    # Check if cookies are accessible in container
    if docker exec secureai-backend test -f /app/secrets/x_cookies.txt; then
        echo "✔ Cookies file accessible in container"
    else
        echo "⚠️  Warning: Cookies file not found in container"
    fi
else
    echo "❌ Backend is not running!"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ X cookies updated successfully!"
echo ""
echo "The backend has been restarted with new cookies."
echo "X link analysis should now work with the updated authentication."
