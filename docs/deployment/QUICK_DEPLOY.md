# ⚡ Quick Production Deployment

**The app should NOT run on your local PC for production.** This guide shows you how to deploy to a production server.

## 🎯 Choose Your Deployment Method

### Option 1: Docker (Fastest - 5 minutes) ⭐ Recommended

```bash
# 1. On your production server, clone the repo
git clone <your-repo-url>
cd SecureAI-DeepFake-Detection

# 2. Create .env file with production settings
cp .env.example .env
nano .env  # Edit with your settings

# 3. Build frontend
cd secureai-guardian && npm install && npm run build && cd ..

# 4. Deploy with Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# 5. Set up SSL
sudo certbot --nginx -d yourdomain.com
```

**Done!** Your app is now running at `https://yourdomain.com`

---

### Option 2: Automated Script (15 minutes)

```bash
# On your Ubuntu/Debian server
git clone <your-repo-url>
cd SecureAI-DeepFake-Detection

# Run automated deployment
sudo DOMAIN=yourdomain.com EMAIL=your@email.com ./deploy-production.sh
```

The script will:
- ✅ Install all dependencies
- ✅ Set up PostgreSQL and Redis
- ✅ Configure Nginx
- ✅ Set up SSL certificate
- ✅ Start all services

---

### Option 3: Cloud Platform (15-30 minutes)

#### AWS Elastic Beanstalk
```bash
pip install awsebcli
eb init -p python-3.11 secureai-app
eb create secureai-prod
eb deploy
```

#### Google Cloud Run
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/secureai
gcloud run deploy secureai --image gcr.io/PROJECT_ID/secureai
```

#### Azure App Service
```bash
az webapp create --resource-group secureai-rg --plan secureai-plan --name secureai-app
az webapp deployment source config-zip --resource-group secureai-rg --name secureai-app --src app.zip
```

---

## 📋 Prerequisites

### Server Requirements
- **OS**: Ubuntu 20.04+ or Debian 11+
- **RAM**: 8GB+ (16GB recommended)
- **CPU**: 4+ cores
- **Storage**: 100GB+
- **Domain**: Your domain name pointing to server IP

### Accounts Needed
- **Server**: VPS (DigitalOcean, Linode, AWS EC2, etc.) or Cloud Platform
- **Domain**: Domain name with DNS access
- **Optional**: AWS account (for S3 storage), Sentry account (for error tracking)

---

## 🔧 Quick Configuration

### 1. Environment Variables (.env)

```bash
# Required
SECRET_KEY=generate-with-openssl-rand-hex-32
DEBUG=false
FLASK_ENV=production

# Database
DATABASE_URL=postgresql://secureai:password@localhost:5432/secureai_db

# Redis
REDIS_URL=redis://localhost:6379/0

# CORS (your domain)
CORS_ORIGINS=https://yourdomain.com

# Optional: AWS S3
USE_LOCAL_STORAGE=false
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
S3_BUCKET_NAME=secureai-videos-prod
```

### 2. DNS Configuration

Point your domain to your server:
```
A Record: yourdomain.com → YOUR_SERVER_IP
A Record: www.yourdomain.com → YOUR_SERVER_IP
```

---

## ✅ Verify Deployment

```bash
# Check API health
curl https://yourdomain.com/api/health

# Check service status
sudo systemctl status secureai

# View logs
sudo journalctl -u secureai -f
```

---

## 🆘 Need Help?

- **Full Guide**: See `PRODUCTION_DEPLOYMENT_GUIDE.md`
- **Troubleshooting**: Check logs with `sudo journalctl -u secureai -n 50`
- **Docker Issues**: Check with `docker-compose logs secureai-backend`

---

## 🚀 Next Steps After Deployment

1. ✅ Set up monitoring (Sentry is already configured)
2. ✅ Configure backups
3. ✅ Set up uptime monitoring (UptimeRobot, Pingdom)
4. ✅ Configure log aggregation
5. ✅ Set up alerts

---

**Remember**: Production deployment means the app runs on a server, NOT on your local PC!

