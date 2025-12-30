#!/bin/bash
# Production Server Setup Script for SecureAI Guardian
# This script sets up Gunicorn, systemd service, and production configuration

set -e

echo "🚀 SecureAI Guardian Production Server Setup"
echo "============================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Get application directory
read -p "Enter application directory (default: /opt/secureai-guardian): " APP_DIR
APP_DIR=${APP_DIR:-/opt/secureai-guardian}

if [ ! -d "$APP_DIR" ]; then
    echo -e "${YELLOW}Creating application directory: $APP_DIR${NC}"
    mkdir -p $APP_DIR
fi

echo ""
echo -e "${YELLOW}Step 1: Installing system dependencies...${NC}"
apt-get update
apt-get install -y python3-pip python3-venv nginx

echo ""
echo -e "${YELLOW}Step 2: Installing Gunicorn...${NC}"
if [ -d "$APP_DIR/.venv" ]; then
    $APP_DIR/.venv/bin/pip install gunicorn
else
    echo -e "${RED}Virtual environment not found at $APP_DIR/.venv${NC}"
    echo "Please create it first: python3 -m venv $APP_DIR/.venv"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 3: Creating log directory...${NC}"
mkdir -p /var/log/secureai
chown www-data:www-data /var/log/secureai

echo ""
echo -e "${YELLOW}Step 4: Setting up systemd service...${NC}"
# Update service file with actual application directory
sed "s|/opt/secureai-guardian|$APP_DIR|g" secureai-guardian.service > /tmp/secureai-guardian.service
cp /tmp/secureai-guardian.service /etc/systemd/system/secureai-guardian.service

# Reload systemd
systemctl daemon-reload

echo ""
echo -e "${YELLOW}Step 5: Enabling and starting service...${NC}"
systemctl enable secureai-guardian.service

echo ""
echo -e "${GREEN}✅ Production server setup complete!${NC}"
echo ""
echo "Service management commands:"
echo "  Start:   sudo systemctl start secureai-guardian"
echo "  Stop:    sudo systemctl stop secureai-guardian"
echo "  Restart: sudo systemctl restart secureai-guardian"
echo "  Status:  sudo systemctl status secureai-guardian"
echo "  Logs:    sudo journalctl -u secureai-guardian -f"
echo ""
echo "Before starting the service, ensure:"
echo "1. Application code is in $APP_DIR"
echo "2. Virtual environment is set up at $APP_DIR/.venv"
echo "3. Dependencies are installed (pip install -r requirements.txt)"
echo "4. Environment variables are configured"
echo "5. Uploads and results directories exist and are writable"
echo ""

