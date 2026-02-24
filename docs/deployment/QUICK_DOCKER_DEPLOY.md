# 🚀 Quick Docker Deployment Guide

Get your SecureAI app running in the cloud in **5 minutes**!

## Prerequisites

- **Docker** and **Docker Compose** installed
- **A cloud server** (DigitalOcean, AWS EC2, Linode, etc.) with:
  - Ubuntu 20.04+ or similar Linux
  - 8GB+ RAM
  - 4+ CPU cores
  - Docker installed

## Step-by-Step Deployment

### Step 1: Connect to Your Server

```bash
ssh user@your-server-ip
```

### Step 2: Install Docker (if not installed)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add your user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Step 3: Clone Repository

```bash
# Create app directory
mkdir -p ~/secureai
cd ~/secureai

# Clone your repository
git clone <your-repo-url> .

# Or upload files via SCP from your local machine:
# scp -r . user@your-server-ip:~/secureai/
```

### Step 4: Build Frontend

```bash
cd secureai-guardian
npm install
npm run build
cd ..
```

### Step 5: Create Environment File

```bash
# Copy example file
cp .env.example .env

# Generate a secure secret key
SECRET_KEY=$(openssl rand -hex 32)
echo "SECRET_KEY=$SECRET_KEY" >> .env

# Edit .env file (optional - defaults work for quick start)
nano .env
```

**Minimum required in `.env`:**
```bash
SECRET_KEY=your-generated-secret-key-here
DEBUG=false
FLASK_ENV=production
```

### Step 6: Deploy with Docker Compose

```bash
# Start all services
docker-compose -f docker-compose.quick.yml up -d

# Watch logs
docker-compose -f docker-compose.quick.yml logs -f
```

### Step 7: Verify Deployment

```bash
# Check if services are running
docker-compose -f docker-compose.quick.yml ps

# Test API health
curl http://localhost:8000/api/health

# Check logs
docker-compose -f docker-compose.quick.yml logs secureai-backend
```

### Step 8: Access Your App

Your app is now running at:
- **Backend API**: `http://your-server-ip:8000`
- **Health Check**: `http://your-server-ip:8000/api/health`

## Configure Firewall

```bash
# Allow HTTP and HTTPS
sudo ufw allow 8000/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
```

## Set Up Domain (Optional - for production)

### Option 1: Use Nginx as Reverse Proxy

```bash
# Install Nginx
sudo apt install nginx

# Create Nginx config
sudo nano /etc/nginx/sites-available/secureai
```

Add this configuration:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/secureai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Set up SSL
sudo certbot --nginx -d yourdomain.com
```

### Option 2: Use Cloud Provider Load Balancer

- **AWS**: Use Application Load Balancer
- **GCP**: Use Cloud Load Balancing
- **Azure**: Use Application Gateway

## Management Commands

```bash
# Start services
docker-compose -f docker-compose.quick.yml up -d

# Stop services
docker-compose -f docker-compose.quick.yml down

# Restart services
docker-compose -f docker-compose.quick.yml restart

# View logs
docker-compose -f docker-compose.quick.yml logs -f secureai-backend

# Update and redeploy
git pull
docker-compose -f docker-compose.quick.yml up -d --build

# Check service status
docker-compose -f docker-compose.quick.yml ps
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose -f docker-compose.quick.yml logs

# Check if ports are in use
sudo netstat -tulpn | grep :8000

# Restart Docker
sudo systemctl restart docker
```

### Database Connection Issues

```bash
# Check PostgreSQL container
docker-compose -f docker-compose.quick.yml logs postgres

# Test database connection
docker-compose -f docker-compose.quick.yml exec postgres psql -U secureai -d secureai_db
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Reduce workers in Dockerfile CMD (edit Dockerfile)
# Change: --workers 4
# To: --workers 2
```

## Next Steps

1. ✅ **Set up domain** (if you have one)
2. ✅ **Configure SSL** (use Let's Encrypt)
3. ✅ **Set up monitoring** (Sentry, etc.)
4. ✅ **Configure backups** (database, uploads)
5. ✅ **Set up AWS S3** (for cloud storage - see AWS deployment guide)

## Production Checklist

- [ ] Strong SECRET_KEY set in .env
- [ ] DEBUG=false in production
- [ ] Database password changed from default
- [ ] Firewall configured
- [ ] SSL certificate installed
- [ ] Domain configured
- [ ] Monitoring set up
- [ ] Backups configured

## Quick Commands Reference

```bash
# Full deployment in one go (automated script - RECOMMENDED)
git clone <repo> ~/secureai && cd ~/secureai
chmod +x quick-deploy-docker.sh
./quick-deploy-docker.sh

# OR manual deployment:
cd secureai-guardian && npm install && npm run build && cd ..
cp .env.example .env
echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env
docker-compose -f docker-compose.quick.yml up -d
```

---

**Your app is now live in the cloud!** 🎉

Access it at: `http://your-server-ip:8000`

