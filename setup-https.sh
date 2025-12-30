#!/bin/bash
# HTTPS Setup Script for SecureAI Guardian
# This script sets up Let's Encrypt SSL certificate and configures Nginx

set -e

echo "🔒 SecureAI Guardian HTTPS Setup"
echo "================================"
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

# Get domain name
read -p "Enter your domain name (e.g., secureai.example.com): " DOMAIN
if [ -z "$DOMAIN" ]; then
    echo -e "${RED}Domain name is required${NC}"
    exit 1
fi

# Get email for Let's Encrypt
read -p "Enter your email for Let's Encrypt notifications: " EMAIL
if [ -z "$EMAIL" ]; then
    echo -e "${RED}Email is required${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 1: Installing Certbot and Nginx...${NC}"
apt-get update
apt-get install -y certbot python3-certbot-nginx nginx

echo ""
echo -e "${YELLOW}Step 2: Creating directory for Let's Encrypt challenges...${NC}"
mkdir -p /var/www/certbot

echo ""
echo -e "${YELLOW}Step 3: Updating Nginx configuration with your domain...${NC}"
# Update nginx.conf with actual domain
sed -i "s/your-domain.com/$DOMAIN/g" nginx.conf

# Copy nginx configuration
cp nginx.conf /etc/nginx/sites-available/secureai-guardian
ln -sf /etc/nginx/sites-available/secureai-guardian /etc/nginx/sites-enabled/

# Remove default nginx site if it exists
if [ -f /etc/nginx/sites-enabled/default ]; then
    rm /etc/nginx/sites-enabled/default
fi

echo ""
echo -e "${YELLOW}Step 4: Testing Nginx configuration...${NC}"
nginx -t

if [ $? -ne 0 ]; then
    echo -e "${RED}Nginx configuration test failed. Please check the configuration.${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 5: Starting Nginx...${NC}"
systemctl restart nginx
systemctl enable nginx

echo ""
echo -e "${YELLOW}Step 6: Obtaining SSL certificate from Let's Encrypt...${NC}"
certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email $EMAIL --redirect

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ SSL certificate obtained successfully!${NC}"
else
    echo -e "${RED}❌ Failed to obtain SSL certificate${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 7: Setting up automatic certificate renewal...${NC}"
# Test renewal
certbot renew --dry-run

# Add cron job for automatic renewal (certbot sets this up automatically, but we'll verify)
systemctl enable certbot.timer
systemctl start certbot.timer

echo ""
echo -e "${GREEN}✅ HTTPS setup complete!${NC}"
echo ""
echo "Your site should now be accessible at: https://$DOMAIN"
echo ""
echo "Next steps:"
echo "1. Build your frontend: cd secureai-guardian && npm run build"
echo "2. Copy build to /var/www/secureai-guardian/dist"
echo "3. Ensure backend is running on port 5000"
echo "4. Restart Nginx: sudo systemctl restart nginx"
echo ""

