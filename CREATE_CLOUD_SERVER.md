# 🌐 How to Create a Cloud Server - Step by Step

**This guide will help you create a cloud server where your app will run.**

## 🎯 Quick Overview

You need a **cloud server** (also called VPS - Virtual Private Server) to host your app. Think of it as a computer in the cloud that runs 24/7.

**Cost**: $12-24/month (about the price of Netflix)

---

## 🏆 Recommended: DigitalOcean (Easiest for Beginners)

DigitalOcean is the easiest to set up and perfect for getting started.

### Step 1: Sign Up for DigitalOcean

1. **Go to**: [https://www.digitalocean.com](https://www.digitalocean.com)
2. **Click**: "Sign Up" (top right)
3. **Enter**: Your email address
4. **Create password**
5. **Verify email**: Check your inbox and click the verification link

### Step 2: Add Payment Method

1. **Click**: "Billing" in the left menu
2. **Add credit card** or PayPal
3. **Don't worry**: You won't be charged until you create a server, and you can delete it anytime

### Step 3: Create Your Server (Droplet)

1. **Click**: "Create" button (top right) → "Droplets"

2. **Choose Region**:
   - Pick the closest to you (e.g., New York, San Francisco, London)
   - This affects speed slightly

3. **Choose Image**:
   - Select **"Ubuntu"**
   - Version: **22.04 (LTS)** or **24.04 (LTS)**
   - ✅ This is important - must be Ubuntu!

4. **Choose Plan**:
   - **Basic** plan (default)
   - **Regular Intel with SSD** (default)
   - **Size**: 
     - **$12/month** - 2GB RAM, 1 vCPU (minimum, might be slow)
     - **$24/month** - 4GB RAM, 2 vCPU ⭐ **RECOMMENDED**
     - **$48/month** - 8GB RAM, 4 vCPU (if you have budget)

5. **Authentication**:
   - **Option A: SSH Keys** (more secure, recommended)
     - If you have SSH keys, click "New SSH Key" and paste your public key
   - **Option B: Password** (easier for beginners)
     - Click "Password"
     - Enter a strong password (save it somewhere safe!)
     - You'll need this to log in

6. **Final Settings**:
   - **Hostname**: Leave default or name it "secureai-server"
   - **Backups**: Optional (costs extra)
   - **Monitoring**: Optional (free)

7. **Click**: "Create Droplet"

### Step 4: Wait for Server to Start

- Takes about 1-2 minutes
- You'll see a progress bar
- When done, you'll see your server IP address

### Step 5: Get Your Server IP Address

1. **In DigitalOcean dashboard**, you'll see your new droplet
2. **Copy the IP address** (looks like: `157.230.123.45`)
3. **Save this IP** - you'll need it to connect!

**Example IP**: `157.230.123.45`

---

## 🔌 Connect to Your Server

### On Windows:

#### Option A: Using PowerShell (Built-in)

1. **Open PowerShell** (search "PowerShell" in Windows)

2. **Connect**:
   ```powershell
   ssh root@your-server-ip
   ```
   
   **Replace `your-server-ip` with your actual IP**
   
   Example:
   ```powershell
   ssh root@157.230.123.45
   ```

3. **First time?** Type `yes` when asked about security

4. **Enter password**: Type the password you set (won't show as you type - that's normal!)

5. **Success!** You should see something like:
   ```
   root@secureai-server:~#
   ```

#### Option B: Using PuTTY (If PowerShell doesn't work)

1. **Download PuTTY**: [https://www.putty.org](https://www.putty.org)
2. **Install and open PuTTY**
3. **Enter**:
   - Host Name: `root@your-server-ip`
   - Port: `22`
   - Connection Type: `SSH`
4. **Click "Open"**
5. **Enter password** when prompted

---

## ✅ Verify Your Server is Ready

Once connected, run these commands to verify:

```bash
# Check Ubuntu version
lsb_release -a

# Check if you have root access
whoami
# Should show: root

# Update system (good practice)
apt update && apt upgrade -y
```

---

## 📋 What You Should Have Now

- ✅ DigitalOcean account
- ✅ Server created (Droplet)
- ✅ Server IP address (e.g., `157.230.123.45`)
- ✅ Password or SSH key
- ✅ Ability to connect via SSH

---

## 🚀 Next Steps: Install Docker

Once you're connected to your server, install Docker:

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

Then follow `GET_STARTED_DEPLOYMENT.md` to deploy your app!

---

## 🆘 Troubleshooting

### "Connection refused" or "Connection timed out"
- **Check**: Is your server running? (Check DigitalOcean dashboard)
- **Check**: Are you using the correct IP address?
- **Check**: Is port 22 (SSH) open? (Should be by default)

### "Permission denied"
- **Check**: Are you using the correct password?
- **Check**: If using SSH keys, make sure the key is added to DigitalOcean

### "Host key verification failed"
- **Solution**: Type `yes` when asked about security

### Can't remember password
- **Solution**: In DigitalOcean, go to your droplet → "Access" → "Reset Root Password"

---

## 💰 Cost Breakdown

- **DigitalOcean Droplet**: $12-24/month
- **Bandwidth**: Usually included (1TB free)
- **Total**: ~$12-24/month

**Tip**: You can delete the server anytime to stop charges!

---

## 🔄 Alternative Cloud Providers

If you prefer a different provider:

### AWS EC2 (More Complex)

1. Sign up at [aws.amazon.com](https://aws.amazon.com)
2. Go to EC2 → Launch Instance
3. Choose Ubuntu 22.04
4. Select t3.small or t3.medium
5. Create key pair
6. Launch instance
7. Get public IP from EC2 dashboard

### Linode (Similar to DigitalOcean)

1. Sign up at [linode.com](https://linode.com)
2. Create → Linode
3. Choose Ubuntu 22.04
4. Select plan ($12-24/month)
5. Create Linode
6. Get IP address

### Vultr (Similar to DigitalOcean)

1. Sign up at [vultr.com](https://vultr.com)
2. Products → Compute → Deploy Server
3. Choose Ubuntu 22.04
4. Select plan
5. Deploy
6. Get IP address

---

## 📝 Quick Reference

**Your Server Info:**
- **IP Address**: `_________________` (fill this in!)
- **Username**: `root` (usually)
- **Password**: `_________________` (save this!)
- **Provider**: DigitalOcean / AWS / Other

**Connection Command:**
```bash
ssh root@YOUR-IP-ADDRESS
```

---

## ✅ Checklist

Before moving to deployment:

- [ ] Created DigitalOcean account
- [ ] Added payment method
- [ ] Created Ubuntu server (Droplet)
- [ ] Got IP address
- [ ] Successfully connected via SSH
- [ ] Can run commands on server
- [ ] Installed Docker (next step)

---

**Once you have your server and can connect to it, you're ready to deploy your app!**

See `GET_STARTED_DEPLOYMENT.md` for the next steps.

