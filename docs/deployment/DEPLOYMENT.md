# SecureAI DeepFake Detection - Production Deployment Guide

This guide covers deploying the SecureAI DeepFake Detection system to production environments.

## 🚀 Quick Start

### Option 1: Docker Deployment (Recommended)

```bash
# Clone or copy the application
git clone <repository-url>
cd secureai-deepfake-detection

# Create environment file
cp .env.example .env
# Edit .env with your configuration

# Deploy with Docker Compose
docker-compose up -d

# Check logs
docker-compose logs -f secureai
```

### Option 2: Traditional Server Deployment

```bash
# On Ubuntu/Debian server
sudo ./deploy.sh

# Or manual installation
sudo apt update
sudo apt install python3 python3-pip nginx

# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# Configure environment
cp .env.example .env
# Edit .env file

# Start service
sudo systemctl start secureai
sudo systemctl enable secureai
```

## 📋 Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04+ or CentOS 7+
- **RAM**: Minimum 4GB, Recommended 8GB+
- **CPU**: Multi-core processor (4+ cores recommended)
- **Storage**: 50GB+ for video storage and processing
- **Python**: 3.11+

### Network Requirements
- **Ports**: 80 (HTTP), 443 (HTTPS), 8000 (Gunicorn)
- **Domain**: Configure DNS for your domain
- **SSL**: Let's Encrypt or commercial SSL certificate

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Flask Configuration
SECRET_KEY=your-secure-random-key-here
DEBUG=false

# AWS S3 Configuration (Optional)
USE_LOCAL_STORAGE=false
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=your-video-bucket
S3_RESULTS_BUCKET_NAME=your-results-bucket

# Application Settings
MAX_CONTENT_LENGTH=524288000  # 500MB in bytes
```

### AWS S3 Setup (Optional)

1. Create S3 buckets:
   ```bash
   aws s3 mb s3://your-video-bucket
   aws s3 mb s3://your-results-bucket
   ```

2. Configure CORS for video uploads:
   ```json
   [
       {
           "AllowedHeaders": ["*"],
           "AllowedMethods": ["GET", "PUT", "POST"],
           "AllowedOrigins": ["https://yourdomain.com"],
           "ExposeHeaders": []
       }
   ]
   ```

## 🐳 Docker Deployment

### Build and Run

```bash
# Build the image
docker build -t secureai .

# Run the container
docker run -d \
  --name secureai \
  -p 8000:8000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/results:/app/results \
  --env-file .env \
  secureai

# Or use Docker Compose
docker-compose up -d
```

### Docker Compose Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f secureai

# Stop services
docker-compose down

# Update deployment
docker-compose pull && docker-compose up -d
```

## 🖥️ Traditional Server Deployment

### 1. System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv nginx ffmpeg

# Install Node.js for frontend assets (if needed)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 2. Application Setup

```bash
# Create application directory
sudo mkdir -p /opt/secureai-deepfake-detection
sudo chown $USER:$USER /opt/secureai-deepfake-detection

# Copy application files
cp -r . /opt/secureai-deepfake-detection/
cd /opt/secureai-deepfake-detection

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn gevent
```

### 3. Configure Environment

```bash
# Copy and edit environment file
cp .env.example .env
nano .env  # Edit with your settings

# Create required directories
mkdir -p uploads results
```

### 4. Systemd Service Setup

```bash
# Copy service file
sudo cp secureai.service /etc/systemd/system/

# Edit service file with correct paths
sudo nano /etc/systemd/system/secureai.service

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl start secureai
sudo systemctl enable secureai

# Check status
sudo systemctl status secureai
```

### 5. Nginx Configuration

```bash
# Copy nginx configuration
sudo cp nginx.conf /etc/nginx/sites-available/secureai

# Edit configuration with correct paths and domain
sudo nano /etc/nginx/sites-available/secureai

# Enable site
sudo ln -s /etc/nginx/sites-available/secureai /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

## 🔒 Security Configuration

### SSL/TLS Setup with Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test renewal
sudo certbot renew --dry-run
```

### Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh
sudo ufw --force enable

# Or iptables
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
```

### File Permissions

```bash
# Set proper ownership
sudo chown -R www-data:www-data /opt/secureai-deepfake-detection
sudo chown -R www-data:www-data /var/log/secureai

# Secure sensitive files
sudo chmod 600 /opt/secureai-deepfake-detection/.env
sudo chmod 644 /etc/systemd/system/secureai.service
```

## 📊 Monitoring & Maintenance

### Log Management

```bash
# View application logs
sudo journalctl -u secureai -f

# View nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Log rotation (add to /etc/logrotate.d/secureai)
/var/log/secureai/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload secureai
    endscript
}
```

### Health Checks

```bash
# Application health
curl http://localhost:8000/api/health

# Nginx status
sudo systemctl status nginx

# Service status
sudo systemctl status secureai
```

### Backup Strategy

```bash
# Database backup (users and results)
tar -czf backup_$(date +%Y%m%d).tar.gz \
    users.json \
    results/ \
    uploads/

# Upload to S3
aws s3 cp backup_$(date +%Y%m%d).tar.gz s3://your-backup-bucket/
```

## 🔄 Updates & Scaling

### Application Updates

```bash
# Stop service
sudo systemctl stop secureai

# Backup current version
cp -r /opt/secureai-deepfake-detection /opt/secureai-backup-$(date +%Y%m%d)

# Update code
cd /opt/secureai-deepfake-detection
git pull  # or copy new files

# Install new dependencies
source .venv/bin/activate
pip install -r requirements.txt

# Run database migrations if needed
# (Add migration commands here)

# Start service
sudo systemctl start secureai
```

### Horizontal Scaling

```bash
# Use load balancer with multiple instances
# Configure Redis for session storage
# Set up database for user management
# Use shared storage (S3) for file uploads
```

## 🐛 Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   # Check logs
   sudo journalctl -u secureai -n 50

   # Check Python path
   sudo -u www-data /opt/secureai-deepfake-detection/.venv/bin/python --version
   ```

2. **Upload fails**
   ```bash
   # Check file permissions
   ls -la uploads/

   # Check disk space
   df -h

   # Check nginx client_max_body_size
   grep client_max_body_size /etc/nginx/sites-enabled/secureai
   ```

3. **High memory usage**
   ```bash
   # Monitor processes
   ps aux --sort=-%mem | head

   # Adjust Gunicorn workers
   # Edit gunicorn.conf.py
   workers = 2  # Reduce from 4
   ```

### Performance Tuning

```python
# gunicorn.conf.py adjustments
workers = min(2 * cpu_count() + 1, 8)  # Adaptive worker count
worker_class = "gevent"  # For I/O bound tasks
max_requests = 500  # Restart workers more frequently
```

## 📞 Support

For issues and questions:
- Check application logs: `sudo journalctl -u secureai -f`
- Review nginx logs: `sudo tail -f /var/log/nginx/error.log`
- Test API endpoints: `curl http://localhost:8000/api/health`

## 📝 Production Checklist

- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Firewall configured
- [ ] File permissions set correctly
- [ ] Log rotation configured
- [ ] Backup strategy implemented
- [ ] Monitoring alerts set up
- [ ] Domain DNS configured
- [ ] Health checks passing
- [ ] Performance tested under load