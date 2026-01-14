# 🚀 SecureAI DeepFake Detection - Deployment Instructions

## Quick Start - Choose Your Deployment Method

### ⚡ **Option 1: Automated One-Command Deployment** (Recommended)

```bash
# On your Ubuntu/Debian server
cd /path/to/secureai-deepfake-detection
sudo chmod +x quick-deploy.sh
sudo DOMAIN=secureai.yourdomain.com ./quick-deploy.sh
```

**That's it!** The script will automatically:
- ✅ Install all dependencies
- ✅ Set up database and Redis
- ✅ Configure Nginx reverse proxy
- ✅ Set up SSL certificate
- ✅ Configure firewall
- ✅ Start all services

**Time:** 10-15 minutes

---

### 🐳 **Option 2: Docker Deployment** (For Testing)

```bash
# Clone repository
git clone https://github.com/yourusername/secureai-deepfake-detection.git
cd secureai-deepfake-detection

# Create environment file
cp .env.example .env
nano .env  # Edit with your settings

# Deploy with Docker Compose
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f secureai
```

**Access:** http://localhost:8000

**Time:** 5 minutes

---

### 📖 **Option 3: Manual Step-by-Step Deployment**

See `COMPLETE_DEPLOYMENT_GUIDE.md` for detailed instructions.

**Time:** 30-60 minutes

---

## 📋 Prerequisites

Before you start, make sure you have:

### **1. Server Requirements**
- Ubuntu 20.04+ or similar Linux distribution
- 8GB+ RAM (16GB recommended)
- 4+ CPU cores
- 100GB+ disk space
- Public IP address

### **2. Domain Configuration**
- Domain name pointing to your server
- DNS A record configured
- Port 80 and 443 accessible

### **3. Accounts (Optional)**
- AWS account (for S3 storage)
- Domain email (for SSL certificate)

---

## ⚡ Quick Deployment (Fastest Way)

```bash
# 1. SSH into your server
ssh user@your-server-ip

# 2. Clone or upload the application
git clone https://github.com/yourusername/secureai-deepfake-detection.git
cd secureai-deepfake-detection

# 3. Make deployment script executable
sudo chmod +x quick-deploy.sh

# 4. Run automated deployment
sudo DOMAIN=secureai.yourdomain.com USE_SSL=true ./quick-deploy.sh

# 5. Wait for deployment to complete (10-15 minutes)

# 6. Access your application
# Open: https://secureai.yourdomain.com
```

### **What the Script Does:**

1. ✅ Checks system requirements
2. ✅ Installs Python, Nginx, PostgreSQL, Redis
3. ✅ Sets up Python virtual environment
4. ✅ Installs all dependencies
5. ✅ Configures database
6. ✅ Sets up Redis cache
7. ✅ Creates systemd service
8. ✅ Configures Nginx reverse proxy
9. ✅ Obtains SSL certificate (Let's Encrypt)
10. ✅ Configures firewall (UFW)
11. ✅ Runs health checks
12. ✅ Displays access information

---

## 🔧 Post-Deployment Steps

### **1. Run Validation Tests**

```bash
cd /opt/secureai-deepfake-detection
source .venv/bin/activate

# Performance validation
python performance_validator.py

# Security audit
python security_auditor.py

# Compliance assessment
python Compliance_Assessment_Tool.py --config compliance_config.yaml

# Enterprise integration tests
python Integration_Test_Runner.py --config integration_test_config.yaml
```

### **2. Configure AWS (Optional)**

```bash
# Edit environment file
sudo nano /opt/secureai-deepfake-detection/.env

# Update these values:
USE_LOCAL_STORAGE=false
AWS_ACCESS_KEY_ID=your_actual_key
AWS_SECRET_ACCESS_KEY=your_actual_secret
S3_BUCKET_NAME=your-bucket-name

# Restart service
sudo systemctl restart secureai
```

### **3. Set Up Monitoring**

```bash
# Access Grafana (if installed)
http://your-server-ip:3000
# Default: admin/admin

# Access Prometheus (if installed)
http://your-server-ip:9090

# View application logs
sudo journalctl -u secureai -f
```

---

## 🏥 Health Checks

### **Quick Health Check**

```bash
# Run automated health check
/opt/secureai-deepfake-detection/health-check.sh
```

### **Manual Checks**

```bash
# Check service status
sudo systemctl status secureai

# Check API health
curl https://secureai.yourdomain.com/health

# Check logs
sudo journalctl -u secureai -n 50

# Check Nginx
sudo systemctl status nginx

# Check database
sudo -u postgres psql -d secureai_production -c "SELECT 1;"

# Check Redis
redis-cli ping
```

---

## 🐛 Troubleshooting

### **Service Won't Start**

```bash
# Check logs
sudo journalctl -u secureai -n 100

# Check configuration
sudo nginx -t

# Restart services
sudo systemctl restart secureai
sudo systemctl restart nginx
```

### **SSL Certificate Issues**

```bash
# Check certificate
sudo certbot certificates

# Renew certificate
sudo certbot renew

# Test renewal
sudo certbot renew --dry-run
```

### **Database Connection Issues**

```bash
# Check PostgreSQL
sudo systemctl status postgresql

# Test connection
sudo -u postgres psql -d secureai_production

# Check credentials in .env file
grep DATABASE_URL /opt/secureai-deepfake-detection/.env
```

### **High Memory Usage**

```bash
# Check memory
free -h

# Check processes
ps aux --sort=-%mem | head

# Reduce Gunicorn workers
sudo nano /opt/secureai-deepfake-detection/gunicorn.conf.py
# Set: workers = 2

# Restart
sudo systemctl restart secureai
```

**For more troubleshooting**, see `Troubleshooting_Guide.md`

---

## 📊 Management Commands

```bash
# Service Management
sudo systemctl start secureai      # Start service
sudo systemctl stop secureai       # Stop service
sudo systemctl restart secureai    # Restart service
sudo systemctl status secureai     # Check status
sudo systemctl enable secureai     # Enable auto-start

# View Logs
sudo journalctl -u secureai -f     # Follow logs
sudo journalctl -u secureai -n 100 # Last 100 lines
sudo tail -f /var/log/nginx/secureai-access.log  # Nginx access
sudo tail -f /var/log/nginx/secureai-error.log   # Nginx errors

# Database Management
sudo -u postgres psql secureai_production  # Access database
sudo systemctl restart postgresql          # Restart database

# Redis Management
redis-cli                          # Access Redis CLI
sudo systemctl restart redis-server  # Restart Redis

# Nginx Management
sudo nginx -t                      # Test configuration
sudo systemctl reload nginx        # Reload configuration
sudo systemctl restart nginx       # Restart Nginx
```

---

## 🔄 Updating the Application

```bash
# Stop service
sudo systemctl stop secureai

# Backup current version
sudo cp -r /opt/secureai-deepfake-detection /opt/secureai-backup-$(date +%Y%m%d)

# Pull latest code
cd /opt/secureai-deepfake-detection
git pull

# Update dependencies
source .venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl start secureai

# Check status
sudo systemctl status secureai
```

---

## 📚 Documentation

- **Complete Deployment Guide**: `COMPLETE_DEPLOYMENT_GUIDE.md`
- **API Documentation**: `API_Documentation.md`
- **Administrator Guide**: `Administrator_Guide.md`
- **User Guides**: `User_Guide_*.md`
- **Security Guide**: `Security_Audit_Framework.md`
- **Compliance Guide**: `Regulatory_Compliance_Framework.md`
- **Troubleshooting**: `Troubleshooting_Guide.md`

---

## 🆘 Getting Help

### **Check These First:**
1. Application logs: `sudo journalctl -u secureai -f`
2. Nginx logs: `sudo tail -f /var/log/nginx/secureai-error.log`
3. Health check: `/opt/secureai-deepfake-detection/health-check.sh`
4. Troubleshooting guide: `Troubleshooting_Guide.md`

### **Common Issues:**
- Service won't start → Check logs
- Database connection errors → Verify PostgreSQL is running
- SSL certificate issues → Run `sudo certbot certificates`
- High memory usage → Reduce Gunicorn workers

### **Support:**
- Documentation: See all `*_Guide.md` files
- Issues: Check GitHub issues
- Email: support@secureai.com (if applicable)

---

## ✅ Production Checklist

Before going live, make sure you've completed:

- [ ] Deployed application successfully
- [ ] SSL certificate configured
- [ ] Firewall configured (ports 80, 443)
- [ ] Database backups configured
- [ ] Monitoring set up (Prometheus/Grafana)
- [ ] Logs rotation configured
- [ ] Health checks passing
- [ ] Performance tests passed
- [ ] Security audit passed
- [ ] Compliance assessment passed
- [ ] Enterprise integrations tested
- [ ] UAT completed
- [ ] Documentation reviewed
- [ ] Team trained on system

---

## 🎉 You're Ready!

Your SecureAI DeepFake Detection System is now deployed and ready to use!

**Next Steps:**
1. Run all validation tests
2. Configure enterprise integrations
3. Set up monitoring alerts
4. Train your team
5. Start detecting deepfakes!

**Access Your System:**
- Application: https://secureai.yourdomain.com
- API Docs: https://secureai.yourdomain.com/api/docs
- Health: https://secureai.yourdomain.com/health

---

*For questions or issues, refer to the comprehensive documentation or contact support.*
