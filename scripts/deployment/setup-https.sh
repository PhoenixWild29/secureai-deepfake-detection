#!/bin/bash

# HTTPS Setup Script for SecureAI Guardian
# This script helps automate the SSL certificate setup process

set -e

echo "=========================================="
echo "SecureAI Guardian - HTTPS Setup Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root for certbot
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run with sudo for certbot operations${NC}"
    echo "Usage: sudo bash setup-https.sh"
    exit 1
fi

# Get domain name
read -p "Enter your domain name (e.g., secureai.example.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}Error: Domain name is required${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Setting up HTTPS for: ${DOMAIN}${NC}"
echo ""

# Check if domain resolves to this server
echo "Checking DNS configuration..."
SERVER_IP=$(curl -s ifconfig.me || curl -s ipinfo.io/ip)
DOMAIN_IP=$(dig +short $DOMAIN | tail -n1)

if [ -z "$DOMAIN_IP" ]; then
    echo -e "${RED}Warning: Could not resolve $DOMAIN. Make sure DNS is configured.${NC}"
    read -p "Continue anyway? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        exit 1
    fi
elif [ "$DOMAIN_IP" != "$SERVER_IP" ]; then
    echo -e "${YELLOW}Warning: Domain $DOMAIN resolves to $DOMAIN_IP, but this server's IP is $SERVER_IP${NC}"
    read -p "Continue anyway? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ DNS is correctly configured${NC}"
fi

# Install certbot if not installed
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    apt update
    apt install -y certbot
else
    echo -e "${GREEN}✓ Certbot is already installed${NC}"
fi

# Stop nginx container
echo ""
echo "Stopping Nginx container for certificate verification..."
cd "$(dirname "$0")"
docker compose -f docker-compose.quick.yml stop nginx 2>/dev/null || true

# Get certificate
echo ""
echo "Requesting SSL certificate from Let's Encrypt..."
echo "You will be prompted for:"
echo "  - Email address (for renewal notifications)"
echo "  - Agreement to terms of service"
echo ""

certbot certonly --standalone -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN --preferred-challenges http

# Create certs directory
echo ""
echo "Setting up certificate directory..."
mkdir -p certs
chmod 755 certs

# Copy certificates
echo "Copying certificates..."
cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem certs/
cp /etc/letsencrypt/live/$DOMAIN/privkey.pem certs/

# Set permissions
chmod 644 certs/fullchain.pem
chmod 600 certs/privkey.pem

# Get the user who ran sudo
SUDO_USER=${SUDO_USER:-$USER}
if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
    chown $SUDO_USER:$SUDO_USER certs/*.pem
fi

echo -e "${GREEN}✓ Certificates copied to ./certs/${NC}"

# Create renewal hook
echo ""
echo "Setting up certificate auto-renewal..."
mkdir -p /etc/letsencrypt/renewal-hooks/deploy

cat > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh <<EOF
#!/bin/bash
# Auto-renewal hook for SecureAI Guardian
cd $(pwd)
cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem certs/
cp /etc/letsencrypt/live/$DOMAIN/privkey.pem certs/
chmod 644 certs/fullchain.pem
chmod 600 certs/privkey.pem
docker compose -f docker-compose.https.yml restart nginx
EOF

chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
echo -e "${GREEN}✓ Auto-renewal hook created${NC}"

# Test renewal
echo ""
echo "Testing certificate renewal (dry run)..."
certbot renew --dry-run

# Start services with HTTPS
echo ""
echo "Starting services with HTTPS configuration..."
docker compose -f docker-compose.https.yml up -d

echo ""
echo -e "${GREEN}=========================================="
echo "HTTPS Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "Your site should now be accessible at:"
echo -e "${GREEN}https://$DOMAIN${NC}"
echo ""
echo "Next steps:"
echo "1. Open https://$DOMAIN in your browser"
echo "2. Verify the padlock icon appears"
echo "3. Test the API: https://$DOMAIN/api/health"
echo ""
echo "Certificate auto-renewal is configured."
echo "Certificates will be renewed automatically 30 days before expiration."
echo ""
