#!/bin/bash
# Setup automated cookie expiration checking and reminders
# This runs checks but requires manual cookie refresh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔧 Setting up X cookies automation..."
echo "=========================================="

# 1. Make scripts executable
chmod +x "$PROJECT_DIR/scripts/check_cookie_expiration.py"
chmod +x "$PROJECT_DIR/scripts/update_x_cookies.sh"
echo "✔ Scripts are executable"

# 2. Setup daily cookie expiration check (runs at 9 AM)
CRON_CHECK="0 9 * * * cd $PROJECT_DIR && /usr/bin/python3 scripts/check_cookie_expiration.py >> logs/cookie_check.log 2>&1"
(crontab -l 2>/dev/null | grep -v "check_cookie_expiration" || true; echo "$CRON_CHECK") | crontab -
echo "✔ Daily cookie expiration check configured (9 AM)"

# 3. Setup monthly reminder (1st of every month at 9 AM)
CRON_REMINDER="0 9 1 * * echo '⚠️  REMINDER: X cookies should be refreshed monthly. Run: scripts/check_cookie_expiration.py to check status' >> $PROJECT_DIR/logs/cookie_reminder.log 2>&1"
(crontab -l 2>/dev/null | grep -v "cookie_reminder" || true; echo "$CRON_REMINDER") | crontab -
echo "✔ Monthly reminder configured (1st of month, 9 AM)"

# 4. Create logs directory
mkdir -p "$PROJECT_DIR/logs"
echo "✔ Logs directory ready"

# 5. Test the check script
echo ""
echo "🧪 Testing cookie expiration check..."
cd "$PROJECT_DIR"
python3 scripts/check_cookie_expiration.py || echo "⚠️  Test had warnings (this is OK if cookies are expired)"

echo ""
echo "=========================================="
echo "✅ Cookie automation configured!"
echo ""
echo "Automated features:"
echo "  • Daily cookie expiration check (9 AM)"
echo "  • Monthly reminder to refresh cookies (1st of month, 9 AM)"
echo "  • Logs saved to: logs/cookie_check.log"
echo ""
echo "Manual steps (cannot be automated):"
echo "  1. Export cookies from browser extension (monthly)"
echo "  2. Upload to server: scp x_cookies.txt root@guardian.secureai.dev:/tmp/x_cookies.txt"
echo "  3. Run: scripts/update_x_cookies.sh /tmp/x_cookies.txt"
echo ""
echo "To check cookie status manually:"
echo "  python3 scripts/check_cookie_expiration.py"
echo ""
echo "To view cron jobs:"
echo "  crontab -l"
