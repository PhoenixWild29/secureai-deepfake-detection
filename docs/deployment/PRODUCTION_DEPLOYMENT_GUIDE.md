# 🚀 SecureAI Production Deployment Guide

This comprehensive guide covers deploying SecureAI DeepFake Detection to production environments. **The app should NOT depend on your local PC** - it needs to run on a production server.

## 📋 Table of Contents

1. [Quick Start - Choose Your Deployment Method](#quick-start)
2. [Docker Deployment (Recommended)](#docker-deployment)
3. [Cloud Provider Deployment](#cloud-provider-deployment)
   - [AWS EC2 / ECS / Elastic Beanstalk](#aws-deployment)
   - [Google Cloud Platform (GCP)](#gcp-deployment)
   - [Microsoft Azure](#azure-deployment)
4. [VPS Deployment (DigitalOcean, Linode, etc.)](#vps-deployment)
5. [CI/CD Automated Deployment](#cicd-deployment)
6. [Post-Deployment Verification](#verification)

---

## 🚀 Quick Start

### Option 1: Docker (Fastest - 5 minutes)
```bash
docker-compose up -d
```

### Option 2: Cloud Platform (15-30 minutes)
- **AWS**: Use Elastic Beanstalk or ECS
- **GCP**: Use Cloud Run or Compute Engine
- **Azure**: Use App Service or Container Instances

### Option 3: VPS Server (30-60 minutes)
- Deploy to DigitalOcean, Linode, or any VPS provider
- Use the automated deployment script

---

## 🐳 Docker Deployment

### Prerequisites
- Docker and Docker Compose installed
- 8GB+ RAM, 4+ CPU cores
- 50GB+ disk space

### Step 1: Prepare Environment

```bash
# Clone repository
git clone <your-repo-url>
cd SecureAI-DeepFake-Detection

# Create .env file
cp .env.example .env
nano .env  # Edit with your production settings
```

### Step 2: Configure Environment Variables

Edit `.env` file:

```bash
# Flask Configuration
SECRET_KEY=your-very-secure-random-key-here-generate-with-openssl-rand-hex-32
DEBUG=false
FLASK_ENV=production

# Database (PostgreSQL)
DATABASE_URL=postgresql://secureai:password@postgres:5432/secureai_db

# Redis
REDIS_URL=redis://redis:6379/0

# AWS S3 (for cloud storage)
USE_LOCAL_STORAGE=false
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=secureai-videos-prod
S3_RESULTS_BUCKET_NAME=secureai-results-prod

# Sentry (error tracking)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# CORS (your production domain)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Step 3: Update docker-compose.yml

Create a production-ready `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: secureai_db
      POSTGRES_USER: secureai
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U secureai"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  secureai-backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://secureai:${DB_PASSWORD}@postgres:5432/secureai_db
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    volumes:
      - ./uploads:/app/uploads
      - ./results:/app/results
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./secureai-guardian/dist:/usr/share/nginx/html
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - secureai-backend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Step 4: Build Frontend

```bash
cd secureai-guardian
npm install
npm run build
cd ..
```

### Step 5: Deploy

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f secureai-backend
```

### Step 6: Set Up SSL (HTTPS)

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal is set up automatically
```

---

## ☁️ Cloud Provider Deployment

### AWS Deployment

#### Option A: AWS Elastic Beanstalk (Easiest)

1. **Install EB CLI**:
```bash
pip install awsebcli
```

2. **Initialize EB**:
```bash
eb init -p python-3.11 secureai-app --region us-east-1
```

3. **Create environment**:
```bash
eb create secureai-prod --instance-type t3.large --envvars SECRET_KEY=your-key
```

4. **Deploy**:
```bash
eb deploy
```

#### Option B: AWS ECS (Container-based)

1. **Build and push Docker image**:
```bash
# Build image
docker build -t secureai:latest .

# Tag for ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker tag secureai:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/secureai:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/secureai:latest
```

2. **Create ECS Task Definition** (JSON):
```json
{
  "family": "secureai",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "containerDefinitions": [{
    "name": "secureai",
    "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/secureai:latest",
    "portMappings": [{
      "containerPort": 8000,
      "protocol": "tcp"
    }],
    "environment": [
      {"name": "SECRET_KEY", "value": "your-secret-key"},
      {"name": "DATABASE_URL", "value": "postgresql://..."}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/secureai",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "ecs"
      }
    }
  }]
}
```

3. **Create ECS Service** via AWS Console or CLI

#### Option C: AWS EC2 (Traditional VPS)

Follow the [VPS Deployment](#vps-deployment) section below.

---

### GCP Deployment

#### Option A: Cloud Run (Serverless Containers)

1. **Build and push to GCR**:
```bash
# Build image
docker build -t gcr.io/PROJECT_ID/secureai:latest .

# Push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/secureai:latest
```

2. **Deploy to Cloud Run**:
```bash
gcloud run deploy secureai \
  --image gcr.io/PROJECT_ID/secureai:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars SECRET_KEY=your-key,DATABASE_URL=...
```

#### Option B: Compute Engine (VPS)

Follow the [VPS Deployment](#vps-deployment) section.

---

### Azure Deployment

#### Option A: Azure App Service

1. **Create App Service**:
```bash
az webapp create \
  --resource-group secureai-rg \
  --plan secureai-plan \
  --name secureai-app \
  --runtime "PYTHON:3.11"
```

2. **Configure environment variables**:
```bash
az webapp config appsettings set \
  --resource-group secureai-rg \
  --name secureai-app \
  --settings SECRET_KEY=your-key DATABASE_URL=...
```

3. **Deploy**:
```bash
az webapp deployment source config-zip \
  --resource-group secureai-rg \
  --name secureai-app \
  --src app.zip
```

#### Option B: Azure Container Instances

```bash
az container create \
  --resource-group secureai-rg \
  --name secureai \
  --image your-registry.azurecr.io/secureai:latest \
  --cpu 2 \
  --memory 4 \
  --ports 8000 \
  --environment-variables SECRET_KEY=your-key
```

---

## 🖥️ VPS Deployment

### Prerequisites
- Ubuntu 20.04+ or Debian 11+ server
- 8GB+ RAM, 4+ CPU cores
- 100GB+ disk space
- Root or sudo access
- Domain name pointing to server IP

### Step 1: Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv nginx postgresql redis-server certbot python3-certbot-nginx git curl ffmpeg

# Install Node.js (for frontend build)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### Step 2: Clone and Setup Application

```bash
# Create application directory
sudo mkdir -p /opt/secureai
sudo chown $USER:$USER /opt/secureai
cd /opt/secureai

# Clone repository
git clone <your-repo-url> .

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn gevent
```

### Step 3: Configure Database

```bash
# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE secureai_db;
CREATE USER secureai WITH PASSWORD 'your-secure-password';
ALTER ROLE secureai SET client_encoding TO 'utf8';
ALTER ROLE secureai SET default_transaction_isolation TO 'read committed';
ALTER ROLE secureai SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE secureai_db TO secureai;
\q
EOF

# Initialize database schema
source .venv/bin/activate
python -c "from database.db_session import init_db; init_db()"
```

### Step 4: Configure Environment

```bash
# Create .env file
cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=false
FLASK_ENV=production

DATABASE_URL=postgresql://secureai:your-secure-password@localhost:5432/secureai_db
REDIS_URL=redis://localhost:6379/0

AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=secureai-videos-prod
S3_RESULTS_BUCKET_NAME=secureai-results-prod

SENTRY_DSN=your-sentry-dsn
CORS_ORIGINS=https://yourdomain.com
EOF
```

### Step 5: Build Frontend

```bash
cd secureai-guardian
npm install
npm run build
cd ..
```

### Step 6: Set Up Systemd Service

```bash
# Create service file
sudo tee /etc/systemd/system/secureai.service > /dev/null << EOF
[Unit]
Description=SecureAI DeepFake Detection API
After=network.target postgresql.service redis-server.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/secureai
Environment="PATH=/opt/secureai/.venv/bin"
EnvironmentFile=/opt/secureai/.env
ExecStart=/opt/secureai/.venv/bin/gunicorn -c gunicorn_config.py api:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable secureai
sudo systemctl start secureai
```

### Step 7: Configure Nginx

```bash
# Create Nginx configuration
sudo tee /etc/nginx/sites-available/secureai > /dev/null << 'EOF'
upstream secureai_backend {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Frontend static files
    location / {
        root /opt/secureai/secureai-guardian/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://secureai_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # WebSocket endpoint
    location /socket.io {
        proxy_pass http://secureai_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/secureai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 8: Set Up SSL

```bash
# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal is automatic, but test it
sudo certbot renew --dry-run
```

---

## 🔄 CI/CD Automated Deployment

### GitHub Actions Deployment

Create `.github/workflows/deploy-production.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install awsebcli
          # or install other deployment tools
      
      - name: Deploy to AWS Elastic Beanstalk
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: |
          eb init -p python-3.11 secureai-app --region us-east-1
          eb deploy secureai-prod
      
      # Or deploy to other platforms
      - name: Deploy to Cloud Run
        run: |
          gcloud builds submit --tag gcr.io/${{ secrets.GCP_PROJECT_ID }}/secureai:latest
          gcloud run deploy secureai --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/secureai:latest
```

### GitLab CI/CD

Create `.gitlab-ci.yml`:

```yaml
stages:
  - build
  - deploy

build:
  stage: build
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

deploy:
  stage: deploy
  script:
    - ssh user@production-server "cd /opt/secureai && git pull && docker-compose up -d"
  only:
    - main
```

---

## ✅ Post-Deployment Verification

### 1. Health Check

```bash
# Check API health
curl https://yourdomain.com/api/health

# Should return: {"status": "healthy"}
```

### 2. Service Status

```bash
# Check systemd service
sudo systemctl status secureai

# Check Nginx
sudo systemctl status nginx

# Check database
sudo systemctl status postgresql

# Check Redis
sudo systemctl status redis-server
```

### 3. Test Video Analysis

```bash
# Upload a test video
curl -X POST https://yourdomain.com/api/analyze \
  -F "video=@test_video.mp4" \
  -H "Authorization: Bearer your-token"
```

### 4. Monitor Logs

```bash
# Application logs
sudo journalctl -u secureai -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Docker logs (if using Docker)
docker-compose logs -f secureai-backend
```

### 5. Performance Testing

```bash
# Load test
ab -n 1000 -c 10 https://yourdomain.com/api/health
```

---

## 🔒 Security Checklist

- [ ] SSL/HTTPS configured and working
- [ ] Secret keys are strong and unique
- [ ] Database passwords are secure
- [ ] CORS configured for your domain only
- [ ] Rate limiting enabled
- [ ] Security headers configured
- [ ] Firewall rules set (only 80, 443 open)
- [ ] Regular security updates enabled
- [ ] Backups configured
- [ ] Monitoring and alerting set up

---

## 📊 Monitoring & Maintenance

### Set Up Monitoring

1. **Sentry** (already configured):
   - Error tracking
   - Performance monitoring

2. **Log Aggregation**:
   - Use CloudWatch (AWS), Stackdriver (GCP), or ELK stack

3. **Uptime Monitoring**:
   - Use UptimeRobot, Pingdom, or similar

### Regular Maintenance

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update application
cd /opt/secureai
git pull
source .venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart secureai

# Backup database
pg_dump secureai_db > backup_$(date +%Y%m%d).sql
```

---

## 🆘 Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u secureai -n 50

# Check configuration
sudo nginx -t

# Check ports
sudo netstat -tulpn | grep :5000
```

### Database Connection Issues

```bash
# Test connection
psql -U secureai -d secureai_db -h localhost

# Check PostgreSQL status
sudo systemctl status postgresql
```

### High Memory Usage

- Reduce Gunicorn workers in `gunicorn_config.py`
- Enable Redis caching
- Use S3 for file storage instead of local

---

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [AWS Elastic Beanstalk Guide](https://docs.aws.amazon.com/elasticbeanstalk/)
- [GCP Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Nginx Configuration Guide](https://nginx.org/en/docs/)

---

**Need Help?** Check the troubleshooting section or review the logs for specific error messages.

