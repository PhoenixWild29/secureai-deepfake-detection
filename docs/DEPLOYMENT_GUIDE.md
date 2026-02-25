# 🚀 SecureAI Guardian Deployment Guide

Complete guide for deploying SecureAI Guardian to production.

## Prerequisites

- Linux server (Ubuntu 20.04+ recommended)
- Domain name with DNS configured
- Root or sudo access
- Python 3.11+
- Node.js 18+
- PostgreSQL 12+ (optional, for database)
- Redis (optional, for caching)

## Quick Start

### 1. Server Setup

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y python3-pip python3-venv nginx postgresql redis-server
```

### 2. Clone and Setup

```bash
# Clone repository
git clone <your-repo-url>
cd SecureAI-DeepFake-Detection

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd secureai-guardian
npm install
cd ..
```

### 3. Configure Environment

Create `.env` file:

```bash
# Database (optional)
DATABASE_URL=postgresql://secureai:password@localhost:5432/secureai_db

# CORS
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com

# S3 Storage (optional)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET_NAME=your-bucket

# Monitoring (optional)
SENTRY_DSN=your-sentry-dsn
LOG_DIR=/var/log/secureai
LOG_LEVEL=INFO

# Redis (optional, for rate limiting)
REDIS_URL=redis://localhost:6379/0
```

### 4. Set Up Database (Optional)

```bash
chmod +x database/setup_database.sh
sudo ./database/setup_database.sh

# Migrate existing data
python database/migrate_from_files.py
```

### 5. Set Up HTTPS

```bash
chmod +x setup-https.sh
sudo ./setup-https.sh
```

### 6. Build Frontend

```bash
cd secureai-guardian
npm run build
sudo mkdir -p /var/www/secureai-guardian
sudo cp -r dist/* /var/www/secureai-guardian/
sudo chown -R www-data:www-data /var/www/secureai-guardian
cd ..
```

### 7. Set Up Production Server

```bash
chmod +x setup-production-server.sh
sudo ./setup-production-server.sh
```

### 8. Start Services

```bash
# Start backend
sudo systemctl start secureai-guardian
sudo systemctl enable secureai-guardian

# Restart Nginx
sudo systemctl restart nginx
```

## Verification

### Check Services

```bash
# Backend status
sudo systemctl status secureai-guardian

# Nginx status
sudo systemctl status nginx

# Check logs
sudo journalctl -u secureai-guardian -f
sudo tail -f /var/log/nginx/error.log
```

### Test Endpoints

```bash
# Health check
curl https://your-domain.com/api/health

# Dashboard stats
curl https://your-domain.com/api/dashboard/stats
```

## Maintenance

### Update Application

```bash
# Pull latest code
git pull

# Update dependencies
source .venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl restart secureai-guardian
```

### Backup Database

```bash
# Create backup
pg_dump -U secureai secureai_db > backup_$(date +%Y%m%d).sql

# Restore backup
psql -U secureai secureai_db < backup_20240101.sql
```

### Monitor Logs

```bash
# Application logs
sudo tail -f /var/log/secureai/secureai-guardian.log

# Error logs
sudo tail -f /var/log/secureai/secureai-guardian_error.log

# Nginx logs
sudo tail -f /var/log/nginx/secureai-access.log
sudo tail -f /var/log/nginx/secureai-error.log
```

## Troubleshooting

### Service Won't Start

```bash
# Check configuration
sudo systemctl status secureai-guardian
sudo journalctl -u secureai-guardian -n 50

# Test Gunicorn manually
cd /opt/secureai-guardian
source .venv/bin/activate
gunicorn -c gunicorn_config.py api:app
```

### Database Connection Issues

```bash
# Test connection
psql -U secureai -d secureai_db -c "SELECT 1;"

# Check PostgreSQL status
sudo systemctl status postgresql
```

### SSL Certificate Issues

```bash
# Check certificate
sudo certbot certificates

# Renew certificate
sudo certbot renew

# Test renewal
sudo certbot renew --dry-run
```

## Security Checklist

- [ ] HTTPS enabled and working
- [ ] Firewall configured (ports 80, 443 only)
- [ ] Database credentials secure
- [ ] API keys in environment variables
- [ ] Rate limiting active
- [ ] Security headers configured
- [ ] Regular backups scheduled
- [ ] Logs monitored
- [ ] Updates applied regularly

## Performance Tuning

### Database

```sql
-- Add indexes for common queries
CREATE INDEX idx_analyses_created_at ON analyses(created_at DESC);
CREATE INDEX idx_analyses_user_verdict ON analyses(user_id, verdict);
```

### Nginx

```nginx
# Increase worker processes
worker_processes auto;

# Increase connection limits
worker_connections 1024;
```

### Gunicorn

Adjust workers in `gunicorn_config.py`:
```python
workers = multiprocessing.cpu_count() * 2 + 1
```

## Scaling

### Horizontal Scaling

1. Set up load balancer (Nginx, HAProxy)
2. Deploy multiple backend instances
3. Use shared database and Redis
4. Configure session storage (Redis)

### Vertical Scaling

1. Increase server resources (CPU, RAM)
2. Optimize database queries
3. Add caching layer
4. Use CDN for static assets

## Support

For deployment issues:
1. Check logs: `/var/log/secureai/`
2. Review error messages
3. Verify configuration files
4. Test endpoints individually

