#!/bin/bash
#################################################################
# SecureAI DeepFake Detection System - Quick Deployment Script
# This script automates the complete deployment process
#################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/opt/secureai-deepfake-detection"
DOMAIN="${DOMAIN:-secureai.yourdomain.com}"
USE_SSL="${USE_SSL:-true}"
DEPLOYMENT_TYPE="${DEPLOYMENT_TYPE:-production}"  # or 'testing'

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_system() {
    print_header "Checking System Requirements"
    
    # Check OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        print_success "OS: $NAME $VERSION"
    else
        print_error "Cannot determine OS version"
        exit 1
    fi
    
    # Check RAM
    TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$TOTAL_RAM" -lt 7 ]; then
        print_warning "RAM: ${TOTAL_RAM}GB (Recommended: 8GB+)"
    else
        print_success "RAM: ${TOTAL_RAM}GB"
    fi
    
    # Check disk space
    DISK_SPACE=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$DISK_SPACE" -lt 100 ]; then
        print_warning "Disk space: ${DISK_SPACE}GB (Recommended: 100GB+)"
    else
        print_success "Disk space: ${DISK_SPACE}GB"
    fi
    
    # Check CPU cores
    CPU_CORES=$(nproc)
    if [ "$CPU_CORES" -lt 4 ]; then
        print_warning "CPU cores: $CPU_CORES (Recommended: 4+)"
    else
        print_success "CPU cores: $CPU_CORES"
    fi
}

install_dependencies() {
    print_header "Installing System Dependencies"
    
    # Update system
    print_info "Updating system packages..."
    apt update -qq
    apt upgrade -y -qq
    
    # Install required packages
    print_info "Installing required packages..."
    apt install -y -qq \
        python3 \
        python3-pip \
        python3-venv \
        nginx \
        postgresql \
        postgresql-contrib \
        redis-server \
        ffmpeg \
        git \
        curl \
        wget \
        unzip \
        certbot \
        python3-certbot-nginx
    
    print_success "System dependencies installed"
}

setup_application() {
    print_header "Setting Up Application"
    
    # Create directories
    print_info "Creating application directories..."
    mkdir -p "$APP_DIR"
    mkdir -p /var/log/secureai
    mkdir -p /var/run/secureai
    
    # Copy application files
    if [ -d "." ] && [ -f "main.py" ]; then
        print_info "Copying application files..."
        cp -r . "$APP_DIR/"
        cd "$APP_DIR"
    else
        print_error "Application files not found in current directory"
        exit 1
    fi
    
    # Create Python virtual environment
    print_info "Creating Python virtual environment..."
    python3 -m venv .venv
    
    # Install Python dependencies
    print_info "Installing Python dependencies (this may take a few minutes)..."
    .venv/bin/pip install --upgrade pip -q
    .venv/bin/pip install -r requirements.txt -q
    .venv/bin/pip install gunicorn gevent -q
    
    # Create .env file
    print_info "Creating environment configuration..."
    if [ ! -f ".env" ]; then
        cat > .env << EOF
# Production Settings
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=false
FLASK_ENV=production
LOG_LEVEL=INFO

# Storage Configuration
USE_LOCAL_STORAGE=true
UPLOAD_FOLDER=./uploads
RESULTS_FOLDER=./results

# Database Configuration
DATABASE_URL=postgresql://secureai_admin:$(openssl rand -hex 16)@localhost:5432/secureai_production
REDIS_URL=redis://localhost:6379

# Application Settings
MAX_CONTENT_LENGTH=524288000
GUNICORN_WORKERS=4
GUNICORN_THREADS=2
GUNICORN_TIMEOUT=300

# Security Settings
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Strict

# Monitoring
ENABLE_PROMETHEUS=true
AUDIT_LOGGING=true

# Compliance
GDPR_ENABLED=true
CCPA_ENABLED=true
AI_ACT_COMPLIANCE=true
EOF
        print_success "Environment file created"
    else
        print_warning ".env file already exists, skipping creation"
    fi
    
    # Create required directories
    mkdir -p uploads results
    
    # Set permissions
    chown -R www-data:www-data "$APP_DIR"
    chmod 600 .env
    
    print_success "Application setup complete"
}

setup_database() {
    print_header "Setting Up Database"
    
    # Start PostgreSQL
    systemctl start postgresql
    systemctl enable postgresql
    
    # Get database password from .env
    DB_PASSWORD=$(grep DATABASE_URL "$APP_DIR/.env" | cut -d':' -f3 | cut -d'@' -f1)
    
    # Create database and user
    print_info "Creating database and user..."
    sudo -u postgres psql -c "CREATE DATABASE secureai_production;" 2>/dev/null || true
    sudo -u postgres psql -c "CREATE USER secureai_admin WITH ENCRYPTED PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE secureai_production TO secureai_admin;" 2>/dev/null || true
    
    # Test connection
    if sudo -u postgres psql -d secureai_production -c "SELECT 1;" >/dev/null 2>&1; then
        print_success "Database setup complete"
    else
        print_error "Database setup failed"
        exit 1
    fi
}

setup_redis() {
    print_header "Setting Up Redis"
    
    # Configure Redis
    sed -i 's/^# maxmemory .*/maxmemory 2gb/' /etc/redis/redis.conf
    sed -i 's/^# maxmemory-policy .*/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf
    
    # Start Redis
    systemctl start redis-server
    systemctl enable redis-server
    
    # Test connection
    if redis-cli ping >/dev/null 2>&1; then
        print_success "Redis setup complete"
    else
        print_error "Redis setup failed"
        exit 1
    fi
}

setup_systemd_service() {
    print_header "Setting Up Systemd Service"
    
    # Create systemd service file
    cat > /etc/systemd/system/secureai.service << EOF
[Unit]
Description=SecureAI DeepFake Detection System
After=network.target postgresql.service redis-server.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin"
ExecStart=$APP_DIR/.venv/bin/gunicorn -c gunicorn.conf.py wsgi:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable and start service
    systemctl enable secureai
    systemctl start secureai
    
    # Wait for service to start
    sleep 5
    
    # Check if service is running
    if systemctl is-active --quiet secureai; then
        print_success "Systemd service configured and running"
    else
        print_error "Service failed to start. Check logs: journalctl -u secureai -n 50"
        exit 1
    fi
}

setup_nginx() {
    print_header "Setting Up Nginx"
    
    # Create Nginx configuration
    cat > /etc/nginx/sites-available/secureai << EOF
# Rate limiting
limit_req_zone \$binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone \$binary_remote_addr zone=upload_limit:10m rate=1r/s;

upstream secureai_backend {
    server 127.0.0.1:8000 fail_timeout=0;
}

server {
    listen 80;
    server_name $DOMAIN;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Large file uploads
    client_max_body_size 500M;
    client_body_timeout 300s;
    
    # Logs
    access_log /var/log/nginx/secureai-access.log;
    error_log /var/log/nginx/secureai-error.log;
    
    # Static files
    location /static {
        alias $APP_DIR/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # API with rate limiting
    location /api {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://secureai_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Health check
    location /health {
        proxy_pass http://secureai_backend;
        access_log off;
    }
    
    # Main application
    location / {
        proxy_pass http://secureai_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    
    # Enable site
    ln -sf /etc/nginx/sites-available/secureai /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Test configuration
    if nginx -t >/dev/null 2>&1; then
        print_success "Nginx configuration valid"
    else
        print_error "Nginx configuration invalid"
        nginx -t
        exit 1
    fi
    
    # Reload Nginx
    systemctl reload nginx
    print_success "Nginx configured and running"
}

setup_ssl() {
    if [ "$USE_SSL" = "true" ]; then
        print_header "Setting Up SSL Certificate"
        
        print_info "Obtaining SSL certificate for $DOMAIN"
        print_warning "Make sure DNS is pointing to this server!"
        
        # Obtain certificate
        if certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email admin@"$DOMAIN" --redirect; then
            print_success "SSL certificate obtained and configured"
        else
            print_warning "SSL certificate setup failed. You can run this manually later:"
            print_info "sudo certbot --nginx -d $DOMAIN"
        fi
    else
        print_info "Skipping SSL setup (USE_SSL=false)"
    fi
}

setup_firewall() {
    print_header "Configuring Firewall"
    
    # Configure UFW
    ufw --force enable
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow ssh
    ufw allow 'Nginx Full'
    
    print_success "Firewall configured"
}

run_health_checks() {
    print_header "Running Health Checks"
    
    # Service status
    print_info "Checking services..."
    systemctl is-active --quiet secureai && print_success "SecureAI service: RUNNING" || print_error "SecureAI service: STOPPED"
    systemctl is-active --quiet nginx && print_success "Nginx: RUNNING" || print_error "Nginx: STOPPED"
    systemctl is-active --quiet postgresql && print_success "PostgreSQL: RUNNING" || print_error "PostgreSQL: STOPPED"
    systemctl is-active --quiet redis-server && print_success "Redis: RUNNING" || print_error "Redis: STOPPED"
    
    # API health
    print_info "Checking API..."
    sleep 2
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        print_success "API health check: PASSED"
    else
        print_warning "API health check: FAILED (may need more time to start)"
    fi
    
    # Database connection
    print_info "Checking database..."
    if sudo -u postgres psql -d secureai_production -c "SELECT 1;" >/dev/null 2>&1; then
        print_success "Database connection: OK"
    else
        print_error "Database connection: FAILED"
    fi
    
    # Redis connection
    print_info "Checking Redis..."
    if redis-cli ping >/dev/null 2>&1; then
        print_success "Redis connection: OK"
    else
        print_error "Redis connection: FAILED"
    fi
}

print_summary() {
    print_header "Deployment Complete! 🎉"
    
    echo -e ""
    echo -e "${GREEN}Your SecureAI DeepFake Detection System is now running!${NC}"
    echo -e ""
    echo -e "${BLUE}Access Points:${NC}"
    if [ "$USE_SSL" = "true" ]; then
        echo -e "  Application:     ${GREEN}https://$DOMAIN${NC}"
        echo -e "  API Docs:        ${GREEN}https://$DOMAIN/api/docs${NC}"
        echo -e "  Health Check:    ${GREEN}https://$DOMAIN/health${NC}"
    else
        echo -e "  Application:     ${GREEN}http://$DOMAIN${NC}"
        echo -e "  API Docs:        ${GREEN}http://$DOMAIN/api/docs${NC}"
        echo -e "  Health Check:    ${GREEN}http://$DOMAIN/health${NC}"
    fi
    echo -e ""
    echo -e "${BLUE}Management Commands:${NC}"
    echo -e "  View logs:       ${YELLOW}sudo journalctl -u secureai -f${NC}"
    echo -e "  Restart service: ${YELLOW}sudo systemctl restart secureai${NC}"
    echo -e "  Check status:    ${YELLOW}sudo systemctl status secureai${NC}"
    echo -e "  Health check:    ${YELLOW}$APP_DIR/health-check.sh${NC}"
    echo -e ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo -e "  1. Configure AWS credentials in ${YELLOW}$APP_DIR/.env${NC}"
    echo -e "  2. Run validation tests: ${YELLOW}cd $APP_DIR && source .venv/bin/activate${NC}"
    echo -e "  3. Run performance tests: ${YELLOW}python performance_validator.py${NC}"
    echo -e "  4. Run security audit: ${YELLOW}python security_auditor.py${NC}"
    echo -e "  5. Run compliance assessment: ${YELLOW}python Compliance_Assessment_Tool.py --config compliance_config.yaml${NC}"
    echo -e ""
    echo -e "${BLUE}Documentation:${NC}"
    echo -e "  Complete guide:  ${YELLOW}$APP_DIR/COMPLETE_DEPLOYMENT_GUIDE.md${NC}"
    echo -e "  Troubleshooting: ${YELLOW}$APP_DIR/Troubleshooting_Guide.md${NC}"
    echo -e ""
}

#################################################################
# Main Deployment Flow
#################################################################

main() {
    print_header "SecureAI DeepFake Detection System - Quick Deployment"
    
    # Check if running as root
    check_root
    
    # Check system requirements
    check_system
    
    # Confirm deployment
    if [ "$DEPLOYMENT_TYPE" = "production" ]; then
        print_warning "This will deploy SecureAI in PRODUCTION mode"
        read -p "Continue? (yes/no): " -r
        if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
            print_info "Deployment cancelled"
            exit 0
        fi
    fi
    
    # Run deployment steps
    install_dependencies
    setup_application
    setup_database
    setup_redis
    setup_systemd_service
    setup_nginx
    setup_ssl
    setup_firewall
    
    # Health checks
    run_health_checks
    
    # Print summary
    print_summary
}

# Run main function
main "$@"
