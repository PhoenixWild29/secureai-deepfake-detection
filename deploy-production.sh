#!/bin/bash
# SecureAI Production Deployment Script
# This script automates the deployment to a production server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/opt/secureai"
DOMAIN="${DOMAIN:-}"
EMAIL="${EMAIL:-}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}SecureAI Production Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Step 1: System Preparation
log_info "Step 1: Preparing system..."
apt-get update
apt-get install -y python3 python3-pip python3-venv nginx postgresql redis-server \
    certbot python3-certbot-nginx git curl ffmpeg build-essential

# Install Node.js
if ! command -v node &> /dev/null; then
    log_info "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y nodejs
fi

# Step 2: Create Application Directory
log_info "Step 2: Creating application directory..."
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# Step 3: Clone or Update Repository
if [ -d ".git" ]; then
    log_info "Updating existing repository..."
    git pull
else
    log_warn "Repository not found. Please clone it manually:"
    log_warn "  git clone <your-repo-url> $APP_DIR"
    read -p "Press Enter after cloning the repository..."
fi

# Step 4: Set Up Python Environment
log_info "Step 4: Setting up Python environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn gevent

# Step 5: Configure Database
log_info "Step 5: Configuring PostgreSQL database..."
if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw secureai_db; then
    DB_PASSWORD=$(openssl rand -base64 32)
    sudo -u postgres psql << EOF
CREATE DATABASE secureai_db;
CREATE USER secureai WITH PASSWORD '$DB_PASSWORD';
ALTER ROLE secureai SET client_encoding TO 'utf8';
ALTER ROLE secureai SET default_transaction_isolation TO 'read committed';
ALTER ROLE secureai SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE secureai_db TO secureai;
\q
EOF
    log_info "Database created. Password saved to $APP_DIR/.db_password"
    echo "$DB_PASSWORD" > "$APP_DIR/.db_password"
    chmod 600 "$APP_DIR/.db_password"
else
    log_info "Database already exists"
    DB_PASSWORD=$(cat "$APP_DIR/.db_password" 2>/dev/null || echo "change-this")
fi

# Step 6: Configure Environment
log_info "Step 6: Configuring environment variables..."
if [ ! -f ".env" ]; then
    log_warn ".env file not found. Creating template..."
    cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=false
FLASK_ENV=production

DATABASE_URL=postgresql://secureai:${DB_PASSWORD}@localhost:5432/secureai_db
REDIS_URL=redis://localhost:6379/0

# AWS S3 Configuration (optional)
USE_LOCAL_STORAGE=true
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=
S3_RESULTS_BUCKET_NAME=

# Sentry (optional)
SENTRY_DSN=

# CORS
CORS_ORIGINS=https://${DOMAIN:-yourdomain.com}
EOF
    log_warn "Please edit .env file with your actual configuration"
    read -p "Press Enter after editing .env file..."
fi

# Step 7: Initialize Database Schema
log_info "Step 7: Initializing database schema..."
source .venv/bin/activate
python -c "from database.db_session import init_db; init_db()" 2>/dev/null || log_warn "Database initialization skipped (may already be initialized)"

# Step 8: Build Frontend
log_info "Step 8: Building frontend..."
cd secureai-guardian
npm install
npm run build
cd ..

# Step 9: Set Up Systemd Service
log_info "Step 9: Setting up systemd service..."
cat > /etc/systemd/system/secureai.service << EOF
[Unit]
Description=SecureAI DeepFake Detection API
After=network.target postgresql.service redis-server.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/gunicorn -c gunicorn_config.py api:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable secureai

# Step 10: Configure Nginx
log_info "Step 10: Configuring Nginx..."
if [ -z "$DOMAIN" ]; then
    read -p "Enter your domain name: " DOMAIN
fi

cat > /etc/nginx/sites-available/secureai << EOF
upstream secureai_backend {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    # Frontend static files
    location / {
        root $APP_DIR/secureai-guardian/dist;
        try_files \$uri \$uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://secureai_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # WebSocket endpoint
    location /socket.io {
        proxy_pass http://secureai_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/secureai /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t

# Step 11: Set Up SSL
if [ -n "$DOMAIN" ]; then
    log_info "Step 11: Setting up SSL certificate..."
    if [ -z "$EMAIL" ]; then
        read -p "Enter your email for SSL certificate: " EMAIL
    fi
    certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" --non-interactive --agree-tos --email "$EMAIL" || log_warn "SSL setup failed. You can run: sudo certbot --nginx -d $DOMAIN"
fi

# Step 12: Start Services
log_info "Step 12: Starting services..."
systemctl restart postgresql
systemctl restart redis-server
systemctl restart nginx
systemctl start secureai

# Wait for service to start
sleep 5

# Step 13: Verify Deployment
log_info "Step 13: Verifying deployment..."
if systemctl is-active --quiet secureai; then
    log_info "✅ SecureAI service is running"
else
    log_error "❌ SecureAI service failed to start"
    log_error "Check logs: sudo journalctl -u secureai -n 50"
    exit 1
fi

# Final Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Service Management:"
echo "  Start:   sudo systemctl start secureai"
echo "  Stop:    sudo systemctl stop secureai"
echo "  Restart: sudo systemctl restart secureai"
echo "  Status:  sudo systemctl status secureai"
echo "  Logs:    sudo journalctl -u secureai -f"
echo ""
if [ -n "$DOMAIN" ]; then
    echo "Access your application at:"
    echo "  http://$DOMAIN"
    echo "  https://$DOMAIN (if SSL configured)"
else
    echo "Configure your domain and SSL:"
    echo "  sudo certbot --nginx -d yourdomain.com"
fi
echo ""
echo "Next Steps:"
echo "  1. Edit $APP_DIR/.env with your production settings"
echo "  2. Configure AWS S3 (if using cloud storage)"
echo "  3. Set up monitoring (Sentry, etc.)"
echo "  4. Configure backups"
echo ""

