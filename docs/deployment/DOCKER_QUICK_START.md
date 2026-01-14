# 🚀 Docker Quick Start - Get Running in 5 Minutes

**This is the fastest way to get your SecureAI app running in the cloud!**

## Prerequisites

- A cloud server (DigitalOcean, AWS EC2, Linode, etc.)
- Docker and Docker Compose installed
- SSH access to your server

## One-Command Deployment

```bash
# On your cloud server
git clone <your-repo-url> ~/secureai && cd ~/secureai
chmod +x quick-deploy-docker.sh
./quick-deploy-docker.sh
```

**That's it!** The script will:
1. ✅ Build the frontend
2. ✅ Create `.env` file with secure keys
3. ✅ Start all Docker services (PostgreSQL, Redis, Backend)
4. ✅ Verify everything is working

## Access Your App

After deployment, your app is available at:
- **API**: `http://your-server-ip:8000`
- **Health Check**: `http://your-server-ip:8000/api/health`

## Open Firewall Port

```bash
sudo ufw allow 8000/tcp
```

## What Gets Deployed

- **PostgreSQL** - Database for storing analysis results
- **Redis** - Caching for performance
- **SecureAI Backend** - Your Flask API running on port 8000

## Next Steps

1. **Set up domain** (optional):
   ```bash
   # Point your domain to server IP
   # Then configure Nginx (see QUICK_DOCKER_DEPLOY.md)
   ```

2. **Set up SSL** (optional):
   ```bash
   sudo certbot --nginx -d yourdomain.com
   ```

3. **Configure AWS S3** (optional - for cloud storage):
   - Edit `.env` file
   - Add AWS credentials
   - Set `USE_LOCAL_STORAGE=false`

## Management Commands

```bash
# View logs
docker-compose -f docker-compose.quick.yml logs -f

# Stop services
docker-compose -f docker-compose.quick.yml down

# Restart services
docker-compose -f docker-compose.quick.yml restart

# Update deployment
git pull
docker-compose -f docker-compose.quick.yml up -d --build
```

## Troubleshooting

**Services won't start?**
```bash
docker-compose -f docker-compose.quick.yml logs
```

**Port already in use?**
```bash
sudo netstat -tulpn | grep :8000
# Change port in docker-compose.quick.yml if needed
```

**Out of memory?**
- Reduce workers in Dockerfile: `--workers 2` instead of `--workers 4`

---

**Need more details?** See `QUICK_DOCKER_DEPLOY.md` for complete guide.

