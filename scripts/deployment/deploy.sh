#!/bin/bash
# SecureAI DeepFake Detection - Production Deployment Script
# Run this script on your production server

set -e

echo "🚀 Starting SecureAI Production Deployment..."

# Configuration
APP_DIR="/opt/secureai-deepfake-detection"
LOG_DIR="/var/log/secureai"
RUN_DIR="/var/run/secureai"
USER="www-data"
GROUP="www-data"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root"
   exit 1
fi

# Create application directory
log_info "Creating application directory..."
mkdir -p "$APP_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$RUN_DIR"

# Set permissions
chown -R "$USER:$GROUP" "$APP_DIR"
chown -R "$USER:$GROUP" "$LOG_DIR"
chown -R "$USER:$GROUP" "$RUN_DIR"

# Copy application files (assuming they're in the current directory)
log_info "Copying application files..."
cp -r . "$APP_DIR/"

# Navigate to app directory
cd "$APP_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    log_info "Creating Python virtual environment..."
    sudo -u "$USER" python3 -m venv .venv
fi

# Install dependencies
log_info "Installing Python dependencies..."
sudo -u "$USER" .venv/bin/pip install --upgrade pip
sudo -u "$USER" .venv/bin/pip install -r requirements.txt
sudo -u "$USER" .venv/bin/pip install gunicorn

# Install additional production dependencies
sudo -u "$USER" .venv/bin/pip install gevent  # For async workers

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    log_warn ".env file not found. Creating template..."
    cat > .env << EOF
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=secureai-deepfake-videos
S3_RESULTS_BUCKET_NAME=secureai-deepfake-results

# Optional: Use local storage if S3 is not configured
USE_LOCAL_STORAGE=true

# Production settings
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=false
EOF
    log_warn "Please edit $APP_DIR/.env with your actual configuration values"
fi

# Create required directories
log_info "Creating required directories..."
mkdir -p uploads results

# Set proper permissions
chown -R "$USER:$GROUP" uploads results

# Install systemd service
log_info "Installing systemd service..."
cp secureai.service /etc/systemd/system/
systemctl daemon-reload

# Enable and start service
log_info "Enabling and starting service..."
systemctl enable secureai
systemctl start secureai

# Check service status
if systemctl is-active --quiet secureai; then
    log_info "Service started successfully!"
else
    log_error "Service failed to start. Check logs with: journalctl -u secureai"
    exit 1
fi

# Nginx configuration (optional)
if [ -f "nginx.conf" ]; then
    log_info "Nginx configuration found. To enable:"
    echo "1. Copy nginx.conf to /etc/nginx/sites-available/secureai"
    echo "2. Edit the configuration with correct paths and domain"
    echo "3. Create symlink: ln -s /etc/nginx/sites-available/secureai /etc/nginx/sites-enabled/"
    echo "4. Test configuration: nginx -t"
    echo "5. Reload nginx: systemctl reload nginx"
fi

log_info "🎉 Deployment completed successfully!"
log_info ""
log_info "Application is running at: http://localhost:8000"
log_info "Check status: systemctl status secureai"
log_info "View logs: journalctl -u secureai -f"
log_info ""
log_info "Next steps:"
log_info "1. Configure your .env file with production settings"
log_info "2. Set up SSL certificates for HTTPS"
log_info "3. Configure Nginx reverse proxy (optional)"
log_info "4. Set up monitoring and log rotation"
log_info "5. Configure firewall rules"

exit 0