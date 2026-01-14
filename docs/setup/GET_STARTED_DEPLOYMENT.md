# 🚀 Getting Started with Deployment

**Step-by-step guide to deploy your SecureAI app to the cloud**

## ⚠️ Important: You Need a Cloud Server First!

Before you can deploy, you need a **cloud server** (not your local PC). 

**👉 START HERE**: See `CREATE_CLOUD_SERVER.md` for detailed instructions on creating a server.

**Quick version**: See `DIGITALOCEAN_SETUP_GUIDE.md` for step-by-step DigitalOcean setup.

Here's a quick overview:

---

## Step 1: Get a Cloud Server

### Option A: DigitalOcean (Easiest - Recommended for Beginners)

1. **Sign up**: Go to [digitalocean.com](https://www.digitalocean.com)
2. **Create Droplet**:
   - Click "Create" → "Droplets"
   - Choose: **Ubuntu 22.04**
   - Plan: **$12/month** (2GB RAM) or **$24/month** (4GB RAM) - recommended
   - Region: Choose closest to you
   - Authentication: Add your SSH key or use password
   - Click "Create Droplet"
3. **Get your server IP**: 
   - After creation, you'll see an IP address like `157.230.123.45`
   - **This is your server!**

### Option B: AWS EC2

1. **Sign up**: Go to [aws.amazon.com](https://aws.amazon.com)
2. **Launch Instance**:
   - Go to EC2 → Launch Instance
   - Choose: **Ubuntu Server 22.04**
   - Instance type: **t3.small** (2GB RAM) or **t3.medium** (4GB RAM)
   - Create key pair for SSH access
   - Launch instance
3. **Get your server IP**: 
   - In EC2 dashboard, find "Public IPv4 address"
   - **This is your server!**

### Option C: Linode, Vultr, or Other VPS

- Similar process: Sign up, create server, get IP address

---

## Step 2: Connect to Your Server

### On Windows (using PowerShell or Command Prompt):

```bash
# Replace with your actual server IP and username
ssh root@your-server-ip

# Or if you created a user:
ssh username@your-server-ip
```

**Example:**
```bash
ssh root@157.230.123.45
```

**First time?** You'll see a security warning - type `yes` to continue.

**Password?** Enter the password you set when creating the server.

---

## Step 3: Install Docker and Docker Compose

Once connected to your server, run:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose (newer method - works with "docker compose")
sudo apt install docker-compose-plugin

# OR install standalone Docker Compose (older method)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add your user to docker group (so you don't need sudo)
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
# OR if using standalone: docker-compose --version
```

**Note**: Newer Docker installations use `docker compose` (with space), older ones use `docker-compose` (with hyphen). Both work!

---

## Step 4: Deploy Your App

### Option A: Automated (Easiest) ⭐

```bash
# Clone your repository
git clone <your-repo-url> ~/secureai
cd ~/secureai

# Make script executable
chmod +x quick-deploy-docker.sh

# Run deployment
./quick-deploy-docker.sh
```

### Option B: Manual Step-by-Step

Follow the instructions in `QUICK_DOCKER_DEPLOY.md`

---

## Step 5: Access Your App

After deployment, your app will be available at:

```
http://your-server-ip:8000
```

**Example:**
```
http://157.230.123.45:8000
```

**Health check:**
```
http://157.230.123.45:8000/api/health
```

---

## Step 6: Open Firewall Port

```bash
# Allow port 8000
sudo ufw allow 8000/tcp

# Enable firewall
sudo ufw enable
```

---

## 📋 Quick Checklist

- [ ] Created cloud server (DigitalOcean, AWS, etc.)
- [ ] Got server IP address
- [ ] Connected via SSH
- [ ] Installed Docker
- [ ] Installed Docker Compose
- [ ] Cloned repository
- [ ] Ran deployment script
- [ ] Opened firewall port
- [ ] Tested app at `http://your-ip:8000`

---

## 🆘 Troubleshooting

### "I don't have a server"
→ Go to Step 1 above and create one (DigitalOcean is easiest)

### "I can't connect via SSH"
→ Make sure:
- You're using the correct IP address
- Firewall allows SSH (port 22)
- You're using the correct username (usually `root` or `ubuntu`)

### "Docker command not found"
→ You need to install Docker (see Step 3)

### "docker-compose: command not found"
→ Try `docker compose` (with space) instead, or install Docker Compose (see Step 3)

### "Permission denied"
→ Add your user to docker group: `sudo usermod -aG docker $USER` then `newgrp docker`

---

## 📚 Next Steps

Once your app is running:

1. **Set up domain** (optional): Point your domain to server IP
2. **Configure SSL** (optional): Use Let's Encrypt for HTTPS
3. **Set up AWS S3** (optional): For cloud storage
4. **Configure monitoring** (optional): Set up Sentry

See `QUICK_DOCKER_DEPLOY.md` for detailed next steps.

---

## 🎯 Summary

1. **Get server** → DigitalOcean/AWS/etc.
2. **Connect** → `ssh root@your-ip`
3. **Install Docker** → Follow Step 3
4. **Deploy** → Run `quick-deploy-docker.sh`
5. **Access** → `http://your-ip:8000`

**That's it!** Your app is now in the cloud! 🎉

